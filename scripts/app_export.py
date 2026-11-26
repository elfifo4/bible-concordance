"""Export the concordance for the "הראשון בחידון" app, and check it against the app's Bible text.

Two jobs, both deterministic and offline:

  export_app()      data/alphabet/*.json -> entries.json + occurrences.bin, the small
                    files the app ships as assets (format below). Occurrences are in
                    the APP's coordinates (book, chapter, verse, word index). No verse
                    text and no word forms: the app shows its own text and finds the
                    word by its position.

  check_alignment() maps every written MorphHB token onto the app's chapter files
                    (allChapters/*.txt, UTF-16) and reports what did not map 1:1.

App text format (as of 2026-11-25): one file per chapter, `_<n>_<slug>-<cc>.txt`; first
line is a header; verses start with an unpointed Hebrew numeral; words are split by
spaces and maqaf; a ketiv is printed bare and followed by its qere in parentheses
"הוצא (הַיְצֵ֣א)"; `׀` (paseq) and `{פ}`/`{ס}`/`{1}`-style markers are not words.
"""

import gzip
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

# (OSIS code, app file slug, Hebrew name), in the app's order: the index + 1 is the
# number in the app's file names (_1_bereshit … _39_divrei_hayamim_b).
BOOKS = [
    ("Gen", "bereshit", "בראשית"), ("Exod", "shemot", "שמות"), ("Lev", "vayikra", "ויקרא"),
    ("Num", "bamidbar", "במדבר"), ("Deut", "devarim", "דברים"), ("Josh", "yehoshua", "יהושע"),
    ("Judg", "shoftim", "שופטים"), ("1Sam", "shemuel_a", "שמואל א"), ("2Sam", "shemuel_b", "שמואל ב"),
    ("1Kgs", "melachim_a", "מלכים א"), ("2Kgs", "melachim_b", "מלכים ב"), ("Isa", "yeshaaya", "ישעיהו"),
    ("Jer", "yirmeyah", "ירמיהו"), ("Ezek", "yechezkel", "יחזקאל"), ("Hos", "hoshea", "הושע"),
    ("Joel", "yoel", "יואל"), ("Amos", "amos", "עמוס"), ("Obad", "ovadia", "עובדיה"),
    ("Jonah", "yona", "יונה"), ("Mic", "micha", "מיכה"), ("Nah", "nachum", "נחום"),
    ("Hab", "havakuk", "חבקוק"), ("Zeph", "tzefania", "צפניה"), ("Hag", "haggai", "חגי"),
    ("Zech", "zecharia", "זכריה"), ("Mal", "malachi", "מלאכי"), ("Ps", "tehilim", "תהלים"),
    ("Prov", "mishley", "משלי"), ("Job", "iyov", "איוב"), ("Song", "shir_hashirim", "שיר השירים"),
    ("Ruth", "ruth", "רות"), ("Lam", "eicha", "איכה"), ("Eccl", "koheleth", "קהלת"),
    ("Esth", "ester", "אסתר"), ("Dan", "daniel", "דניאל"), ("Ezra", "ezra", "עזרא"),
    ("Neh", "nechemia", "נחמיה"), ("1Chr", "divrei_hayamim_a", "דברי הימים א"),
    ("2Chr", "divrei_hayamim_b", "דברי הימים ב"),
]
BOOK_NO = {osis: i + 1 for i, (osis, _, _) in enumerate(BOOKS)}

GEMATRIA = dict(zip("אבגדהוזחטיכלמנסעפצקרשת",
                    [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 200, 300, 400]))
POINTS = re.compile(r"[֑-ׇ]")          # cantillation + niqqud
CANTILLATION = re.compile(r"[֑-ֽ֯׀׃׆]")  # te'amim, meteg, paseq, sof pasuq, nun hafukha
MARKER = re.compile(r"\{[^}]*\}")
QERE = re.compile(r"\([^)]*\)")
# Exactly these separate words (Kotlin/JVM `\s` does not match NBSP, so name them):
# tab, LF, CR, space, NBSP (the only separator in Deut 32:6 "הַ לְיְהֹוָה") and maqaf.
SPLIT = re.compile("[\t\n\r  ־]+")
NOT_WORDS = "׀׆"                        # paseq ׀ and inverted nun ׆ (Num 10:35-36, Ps 107)


def consonants(word):
    return "".join(ch for ch in unicodedata.normalize("NFD", word) if "א" <= ch <= "ת")


def display_form(form):
    """MorphHB form -> pointed word without cantillation or morpheme slashes."""
    return unicodedata.normalize("NFC", CANTILLATION.sub("", form.replace("/", "")))


def parse_verse_id(verse_id):
    book, chapter, verse = verse_id.split(".")
    return BOOK_NO[book], int(chapter), int(verse)


# --------------------------------------------------------------- app text

def gematria(token):
    if not token or POINTS.search(token) or any(ch not in GEMATRIA for ch in token):
        return None
    return sum(GEMATRIA[ch] for ch in token)


def parse_app_chapter(text):
    """App chapter text -> {verse number: [word, …]} (qere and markers dropped).

    The exact rule the app must reproduce (docs/APP_EXPORT.md):
      1. drop a leading BOM and everything up to the first line break (the header);
      2. replace each {…} marker, each (…) qere, paseq ׀ and inverted nun ׆ with a space;
      3. split on SPLIT (tab, LF, CR, space, NBSP, maqaf); ZWJ stays inside the word;
      4. a token is the number of the next verse when it is the unpointed numeral
         current + 1 and nothing but letterless tokens stands between it and the start
         of the chapter or the last token that ended with sof pasuq ׃;
      5. any other token: strip ׃; keep it as a word if a Hebrew letter is left; if it
         ended with ׃ (a lone ׃ after a qere included) the next numeral may start a verse;
         a letterless token without ׃ changes nothing."""
    text = text.lstrip("\ufeff")
    nl = text.find("\n")
    body = "" if nl < 0 else text[nl + 1:]
    body = QERE.sub(" ", MARKER.sub(" ", body))
    for ch in NOT_WORDS:
        body = body.replace(ch, " ")
    verses, current, prev_end = {}, 0, True
    for tok in SPLIT.split(body):
        if not tok:
            continue
        if prev_end and gematria(tok) == current + 1:
            current += 1
            verses[current] = []
            prev_end = False
            continue
        word = tok.replace("׃", "")
        if current and consonants(word):
            verses[current].append(word)
        if tok.endswith("׃"):
            prev_end = True
        elif consonants(word):
            prev_end = False
    return verses


CHAPTER_COUNT = 929


def app_chapter_files(app_dir, expected=CHAPTER_COUNT):
    """-> {(book, chapter): path}. Fails loudly on a wrong directory or a renamed book."""
    out = {}
    for path in Path(app_dir).glob("_*.txt"):
        m = re.fullmatch(r"_(\d+)_(.+)-(\d+)\.txt", path.name)
        if not m:
            continue
        book, slug = int(m.group(1)), m.group(2)
        if not 1 <= book <= len(BOOKS) or BOOKS[book - 1][1] != slug:
            raise ValueError(f"{path.name}: unknown book number or slug")
        out[(book, int(m.group(3)))] = path
    if len(out) != expected:
        raise ValueError(f"{app_dir}: found {len(out)} chapter files, expected {expected}")
    return out


def read_app_text(app_dir, expected_chapters=CHAPTER_COUNT):
    """-> {(book, chapter, verse): [word, …]} for the whole app Bible."""
    verses = {}
    for (book, chapter), path in sorted(app_chapter_files(app_dir, expected_chapters).items()):
        for verse, words in parse_app_chapter(path.read_text(encoding="utf-16")).items():
            verses[(book, chapter, verse)] = words
    return verses


def verse_count_mismatches(app_dir, app):
    """Compare parsed verse counts with the app's own verses_per_chapter.csv (next to
    allChapters/). -> list of "file: parsed X, csv Y"; empty when all match."""
    raw = (Path(app_dir).parent / "verses_per_chapter.csv").read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    parsed = Counter((k[0], k[1]) for k in app)
    out = []
    for line in text.splitlines()[1:]:
        if not line.strip():
            continue
        name, n = line.rsplit(",", 1)
        m = re.fullmatch(r"_(\d+)_.+-(\d+)\.txt", name.strip())
        got = parsed.get((int(m.group(1)), int(m.group(2))), 0)
        if got != int(n):
            out.append(f"{name.strip()}: parsed {got}, csv {int(n)}")
    return out


def morphhb_written_tokens(tokens_path):
    """-> {(book, chapter, verse): [(position, form), …]} from build/tokens-<rev>.jsonl."""
    out = defaultdict(list)
    with open(tokens_path, encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            out[parse_verse_id(t["verseId"])].append((t["tokenPosition"], t["form"]))
    return out


JOIN_MIN_RATIO = 0.8


def best_join(m, i1, i2, word):
    """The contiguous run of >= 2 tokens in m[i1:i2] whose consonants best spell `word`
    (ratio >= JOIN_MIN_RATIO), as a range of indexes into m; empty if none does."""
    best, best_ratio = range(0), JOIN_MIN_RATIO
    for start in range(i1, i2 - 1):
        for end in range(start + 2, i2 + 1):
            r = SequenceMatcher(None, "".join(t[2] for t in m[start:end]), word, autojunk=False).ratio()
            if r > best_ratio or (r == best_ratio and not best):
                best, best_ratio = range(start, end), r
    return best


def align(mhb, app):
    """Map every written MorphHB token to the app word that shows it.

    Whole books are aligned on consonant sequences (difflib), so a verse that the app
    numbers differently (the Decalogue, Num 25:19 / 26:1 …) still maps to the right
    word. Equal runs map 1:1; a replaced run of the same length maps 1:1 (spelling
    variants such as הַטְּהוֹרָה / הַטְּהֹרָה); a run that the app writes as one word
    (פְּדָה צוּר -> פדהצור) maps the tokens that spell that word (best_join) to it.
    Anything else is unmapped.

    Returns ({(verseKey, position): (appVerseKey, appPosition) | None}, Counter)."""
    mapping, stats = {}, Counter()
    for book in range(1, len(BOOKS) + 1):
        a = [(k, i + 1, consonants(w)) for k in sorted(x for x in app if x[0] == book)
             for i, w in enumerate(app[k])]
        m = [(k, pos, consonants(f)) for k in sorted(x for x in mhb if x[0] == book)
             for pos, f in sorted(mhb[k])]
        sm = SequenceMatcher(None, [t[2] for t in m], [t[2] for t in a], autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            joined = best_join(m, i1, i2, a[j1][2]) if op == "replace" and j2 - j1 == 1 else range(0)
            for x in range(i1, i2):
                if op == "equal":
                    kind, y = "same", j1 + x - i1
                elif op == "replace" and i2 - i1 == j2 - j1:
                    kind, y = "spelling-variant", j1 + x - i1
                elif x in joined:
                    kind, y = "joined-in-app", j1
                else:
                    kind, y = "unmapped", None
                stats[kind] += 1
                tok = m[x]
                if y is None:
                    mapping[(tok[0], tok[1])] = None
                    continue
                mapping[(tok[0], tok[1])] = (a[y][0], a[y][1])
                if (a[y][0], a[y][1]) != (tok[0], tok[1]):
                    stats["placed-elsewhere"] += 1
    return mapping, stats


def ref(key, pos=None):
    s = "%s.%d.%d" % (BOOKS[key[0] - 1][0], key[1], key[2])
    return s if pos is None else f"{s}#{pos}"


LOW_RATIO = 0.5
MIN_MAPPED_PCT = 99.98     # 99.989% on 2026-11-26; below this the app text or the parser changed


def check_alignment(tokens_path, app_dir, sample=40, expected_chapters=CHAPTER_COUNT):
    """Report how every written MorphHB token maps onto the app's text."""
    app = read_app_text(app_dir, expected_chapters)
    mhb = morphhb_written_tokens(tokens_path)
    mapping, stats = align(mhb, app)
    forms = {(k, pos): f for k, toks in mhb.items() for pos, f in toks}
    examples = defaultdict(list)
    for (key, pos), target in sorted(mapping.items()):
        word = forms[(key, pos)].replace("/", "")
        if target is None:
            kind, detail = "unmapped", {"morphhb": word}
        else:
            got = app[target[0]][target[1] - 1]
            ratio = SequenceMatcher(None, consonants(word), consonants(got), autojunk=False).ratio()
            if ratio < LOW_RATIO:
                # placed on a word that looks quite different: a textual variant or a join;
                # read these whenever the app text changes
                kind, detail = "low-similarity", {"morphhb": word, "app": ref(*target), "appWord": got,
                                                  "ratio": round(ratio, 2)}
            elif target != (key, pos):
                kind, detail = "placed-elsewhere", {"morphhb": word, "app": ref(*target)}
            else:
                continue
        stats["low-similarity"] += kind == "low-similarity"
        if len(examples[kind]) < sample:
            examples[kind].append({"ref": ref(key, pos), **detail})
    total = len(mapping)
    return {
        "verseCountMismatches": verse_count_mismatches(app_dir, app),
        "verses": {"app": len(app), "morphhb": len(mhb),
                   "onlyInApp": [ref(k) for k in sorted(set(app) - set(mhb))],
                   "onlyInMorphhb": [ref(k) for k in sorted(set(mhb) - set(app))]},
        "tokens": total,
        "mapped": total - stats["unmapped"],
        "mappedPct": round(100 * (total - stats["unmapped"]) / total, 3) if total else None,
        "kinds": dict(stats.most_common()),
        "examples": dict(examples),
    }


# --------------------------------------------------------------- export
#
# Two files, readable with plain code on every Kotlin target (Android, iOS, desktop, JS):
#
# entries.json      {"format", "meta", "books", "definitionStatuses", "fields", "entries"}
#                   entries[i] = [lexiconId, strong, letter, headword, definitionHe,
#                                 definitionStatusIndex, occurrenceCount, unplaced]
#                   occurrenceCount counts every occurrence; `unplaced` lists the MorphHB
#                   refs ("Josh.21.36#4") of the few whose word is not in the app's text.
#
# occurrences.bin   "BCO1", then for each entry in entries.json order:
#                   varint n, then n locations, ascending, delta-coded (first one
#                   absolute) as unsigned LEB128 varints.
#                   location = book << 24 | chapter << 16 | verse << 8 | position, in
#                   the APP's coordinates: position is the 1-based index of the word in
#                   the app's verse as parse_app_chapter() splits it.
#
# The reverse index (word in the reader -> LIST of entries: 11 app words belong to two
# entries) is built in memory at load time. The exact format is in docs/APP_EXPORT.md.

FORMAT = "bible-concordance-app/1"
MAGIC = b"BCO1"


def pack_location(book, chapter, verse, position):
    if not (0 < book <= len(BOOKS) and 0 < chapter < 256 and 0 < verse < 256 and 0 < position < 256):
        raise ValueError(f"location out of range: {(book, chapter, verse, position)}")
    return book << 24 | chapter << 16 | verse << 8 | position


def unpack_location(loc):
    return loc >> 24, (loc >> 16) & 0xFF, (loc >> 8) & 0xFF, loc & 0xFF


def varint(n):
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        if n:
            out.append(b | 0x80)
        else:
            out.append(b)
            return bytes(out)


def read_occurrences(data):
    """occurrences.bin -> [[location, …] per entry] (the reference decoder)."""
    if data[:4] != MAGIC:
        raise ValueError("not an occurrences.bin file")
    pos, out = 4, []

    def next_varint():
        nonlocal pos
        shift = value = 0
        while True:
            b = data[pos]
            pos += 1
            value |= (b & 0x7F) << shift
            if b < 0x80:
                return value
            shift += 7

    while pos < len(data):
        n, prev, locs = next_varint(), 0, []
        for _ in range(n):
            prev += next_varint()
            locs.append(prev)
        out.append(locs)
    return out


def load_entries(alphabet_dir):
    manifest = json.loads((Path(alphabet_dir) / "manifest.json").read_text(encoding="utf-8"))
    entries = []
    for item in manifest["letters"]:
        data = json.loads((Path(alphabet_dir) / f"{item['letter']}.json").read_text(encoding="utf-8"))
        for e in data["entries"]:
            entries.append((item["letter"], e))
    return manifest, entries


def export_app(alphabet_dir, tokens_path, app_dir, out_dir, expected_chapters=CHAPTER_COUNT,
               min_mapped_pct=MIN_MAPPED_PCT):
    """Write entries.json and occurrences.bin to out_dir. Returns a summary dict."""
    manifest, entries = load_entries(alphabet_dir)
    ids = Counter(e["lexiconEntryId"] for _, e in entries)
    dup = [k for k, n in ids.items() if n > 1 or not k]
    if dup:
        raise ValueError(f"lexiconEntryId must be unique and present: {dup[:5]}")
    app = read_app_text(app_dir, expected_chapters)
    bad = verse_count_mismatches(app_dir, app)
    if bad:
        raise ValueError(f"app text parsed wrong (verses_per_chapter.csv): {bad[:5]}")
    mapping, stats = align(morphhb_written_tokens(tokens_path), app)
    pct = 100 * (len(mapping) - stats["unmapped"]) / len(mapping)
    if pct < min_mapped_pct:
        raise ValueError(f"only {pct:.3f}% of MorphHB tokens map onto the app text (< {min_mapped_pct}%)")

    statuses = sorted({e.get("definitionReviewStatus") or "" for _, e in entries})
    rows, blob = [], bytearray(MAGIC)
    placed_total = unplaced_total = joined = 0
    for letter, e in entries:
        occs = e["occurrences"]
        if len(occs) != e["occurrenceCount"]:
            raise ValueError(f"{e['lexiconEntryId']}: occurrenceCount {e['occurrenceCount']} != {len(occs)}")
        locs, unplaced = set(), []
        for o in occs:
            key = parse_verse_id(o["verseId"])
            if (key, o["tokenPosition"]) not in mapping:
                raise ValueError(f"{o['verseId']}#{o['tokenPosition']} is not in the MorphHB token stream")
            target = mapping[(key, o["tokenPosition"])]
            if target is None:
                unplaced.append(f"{o['verseId']}#{o['tokenPosition']}")
                continue
            loc = pack_location(*target[0], target[1])
            joined += loc in locs      # two tokens of this entry written as one word in the app
            locs.add(loc)
        rows.append([e["lexiconEntryId"], e.get("strongNumber"), letter, display_form(e["headword"]), e.get("definitionHe"),
                     statuses.index(e.get("definitionReviewStatus") or ""), len(occs), sorted(unplaced)])
        blob += varint(len(locs))
        prev = 0
        for loc in sorted(locs):
            blob += varint(loc - prev)
            prev = loc
        placed_total += len(locs)
        unplaced_total += len(unplaced)

    doc = {
        "format": FORMAT,
        "meta": {
            "status": manifest.get("status", ""),
            "editoriallyApproved": False,
            "sourceRevisions": manifest.get("sourceRevisions", {}),
            "coordinates": "app-text: book, chapter, verse, 1-based word index (see occurrences.bin)",
            "entryCount": len(rows),
            "occurrenceCount": sum(r[6] for r in rows),
            # lets the loader check that occurrences.bin belongs to this entries.json
            "occurrencesBytes": len(blob),
            "occurrencesSha256": hashlib.sha256(bytes(blob)).hexdigest(),
        },
        "books": [[osis, he, slug] for osis, slug, he in BOOKS],
        "definitionStatuses": statuses,
        "fields": ["lexiconId", "strong", "letter", "headword", "definitionHe",
                   "definitionStatus", "occurrenceCount", "unplaced"],
        "entries": rows,
    }
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    entries_bytes = (json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    (out_dir / "entries.json").write_bytes(entries_bytes)
    (out_dir / "occurrences.bin").write_bytes(bytes(blob))
    return {
        "dir": str(out_dir),
        "entries": len(rows),
        "occurrences": placed_total,
        "unplaced": unplaced_total,
        "joinedSameEntry": joined,
        "files": {name: {"bytes": len(b), "gzipBytes": len(gzip.compress(b, 9, mtime=0))}
                  for name, b in (("entries.json", entries_bytes), ("occurrences.bin", bytes(blob)))},
    }
