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
SPLIT = re.compile(r"[\s־]+")              # whitespace and maqaf


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

    A token starts verse n+1 only when it is the unpointed numeral n+1 and it is the
    first token or follows a sof pasuq; this keeps short unpointed ketiv words from
    being read as verse numbers."""
    lines = text.lstrip("﻿").splitlines()[1:]          # drop the header line
    body = QERE.sub(" ", MARKER.sub(" ", " ".join(lines))).replace("׀", " ")
    verses, current, prev_end = {}, 0, True
    for tok in SPLIT.split(body):
        if not tok:
            continue
        if prev_end and gematria(tok) == current + 1:
            current += 1
            verses[current] = []
            prev_end = False
            continue
        if current == 0:
            continue
        word = tok.replace("׃", "")
        if consonants(word):
            verses[current].append(word)
        prev_end = tok.endswith("׃")
    return verses


def app_chapter_files(app_dir):
    out = {}
    for path in Path(app_dir).glob("_*.txt"):
        m = re.fullmatch(r"_(\d+)_(.+)-(\d+)\.txt", path.name)
        if m:
            out[(int(m.group(1)), int(m.group(3)))] = path
    return out


def read_app_text(app_dir):
    """-> {(book, chapter, verse): [word, …]} for the whole app Bible."""
    verses = {}
    for (book, chapter), path in sorted(app_chapter_files(app_dir).items()):
        for verse, words in parse_app_chapter(path.read_text(encoding="utf-16")).items():
            verses[(book, chapter, verse)] = words
    return verses


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


def check_alignment(tokens_path, app_dir, sample=40):
    """Report how every written MorphHB token maps onto the app's text."""
    app = read_app_text(app_dir)
    mhb = morphhb_written_tokens(tokens_path)
    mapping, stats = align(mhb, app)
    forms = {(k, pos): f for k, toks in mhb.items() for pos, f in toks}
    examples = defaultdict(list)
    for (key, pos), target in sorted(mapping.items()):
        word = forms[(key, pos)].replace("/", "")
        if target is None:
            kind, detail = "unmapped", {"morphhb": word}
        elif target != (key, pos):
            kind, detail = "placed-elsewhere", {"morphhb": word, "app": ref(*target)}
        else:
            continue
        if len(examples[kind]) < sample:
            examples[kind].append({"ref": ref(key, pos), **detail})
    total = len(mapping)
    return {
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
# The reverse index (word in the reader -> entry) is built in memory at load time.

FORMAT = "bible-concordance-app/1"
MAGIC = b"BCO1"


def pack_location(book, chapter, verse, position):
    assert 0 < position < 256 and 0 < verse < 256 and 0 < chapter < 256, (book, chapter, verse, position)
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


def export_app(alphabet_dir, tokens_path, app_dir, out_dir):
    """Write entries.json and occurrences.bin to out_dir. Returns a summary dict."""
    manifest, entries = load_entries(alphabet_dir)
    ids = Counter(e["lexiconEntryId"] for _, e in entries)
    dup = [k for k, n in ids.items() if n > 1 or not k]
    if dup:
        raise ValueError(f"lexiconEntryId must be unique and present: {dup[:5]}")
    mapping, _ = align(morphhb_written_tokens(tokens_path), read_app_text(app_dir))

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
        rows.append([e["lexiconEntryId"], e.get("strongNumber"), letter, e["headword"], e.get("definitionHe"),
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
