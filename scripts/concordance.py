#!/usr/bin/env python3
"""One CLI for all 22 letters of the Hebrew Bible concordance.

Script-first, LLM-last: every bulk step (fetching pinned sources, importing
MorphHB, generating letters, auditing every occurrence, reporting status) is
deterministic and idempotent. Full results go to build/reports/*.json; the
terminal gets a short summary and the exceptions.

Sub-commands
  fetch-sources   shallow-fetch the pinned MorphHB and HebrewLexicon revisions
                  into build/sources/<name>-<rev>/ (skipped when complete)
  import          MorphHB wlc/*.xml -> build/tokens-<rev>.jsonl (+ qere sidecar),
                  then the independent verse/word-id audit
  generate        build letter files from the token stream and the lexicon,
                  preserving definition fields of existing entries;
                  --dry-run reports the delta without writing anything
  audit           compare every stored occurrence and every stored Strong/BDB
                  excerpt with the pinned sources, offline from the cache
  worksheet       build/worksheets/<letter>.tsv: one compact line per entry
                  (the only input the LLM reads to write Hebrew glosses)
  enrich          join data/drafts/<letter>.txt (strong|lexId|gloss) with the
                  Strong/BDB excerpts and fill the definition* fields
  lint            report glosses that are missing, repeat the headword, are too
                  long, or are proper names without context
  status          22-letter status table (markdown), optionally to a file

tokenPosition semantics (decision of 2026-11-22): 1-based index in the WRITTEN
token stream of the verse. Qere words inside <note> never take a position.
See docs/DATA_MODEL.md.
"""
import argparse
import json
import re
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from scripts import import_morphhb, audit_morphhb  # noqa: E402

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"
MORPHHB_REV = "db6c5c9b46b8f39346f10915ddb1a70dcd429901"
LEXICON_REV = "21c9add13bc727d3a951361778e97e3ff7afd1ce"
MORPHHB_URL = "https://github.com/openscriptures/morphhb.git"
LEXICON_URL = "https://github.com/openscriptures/HebrewLexicon.git"
LICENSE = "CC BY 4.0"
LEMMA_REF = re.compile(r"(\d+)\s?([a-z])?")
EXCEPTIONS_PATH = ROOT / "data" / "lexicon-exceptions.json"

# ----------------------------------------------------------------- helpers

def log(msg):
    print(msg, flush=True)

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json_if_changed(path, obj):
    text = json.dumps(obj, ensure_ascii=False, indent=2) + "\n"
    path = Path(path)
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True

def consonants(word):
    return "".join(ch for ch in unicodedata.normalize("NFD", word) if "א" <= ch <= "ת")

def strip_points(s):
    return re.sub(r"[֑-ׇ]", "", s)

def lemma_refs(raw):
    """MorphHB lemma -> list of (strongNumber, augKey).

    'c/5921 a' -> [('5921', '5921a')]; '1121' -> [('1121', '1121')];
    prefix-only lemmas such as 'l' or 'c' -> []."""
    if not raw:
        return []
    out = []
    for number, suffix in LEMMA_REF.findall(raw):
        number = str(int(number))
        out.append((number, number + (suffix or "")))
    return out

def paths(build):
    build = Path(build)
    return {
        "build": build,
        "morphhb": build / "sources" / f"morphhb-{MORPHHB_REV}",
        "lexicon": build / "sources" / f"hebrewlexicon-{LEXICON_REV}",
        "tokens": build / f"tokens-{MORPHHB_REV}.jsonl",
        "qere": build / f"qere-{MORPHHB_REV}.jsonl",
        "reports": build / "reports",
    }

# ----------------------------------------------------------- fetch-sources

def shallow_fetch(url, rev, dest):
    marker = dest / ".complete"
    if marker.exists() and marker.read_text().strip() == rev:
        log(f"cached   {dest.name}")
        return False
    dest.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(["git", "-C", str(dest), *a], check=True, capture_output=True, text=True)
    if not (dest / ".git").exists():
        run("init", "-q")
        run("remote", "add", "origin", url)
    run("fetch", "-q", "--depth", "1", "origin", rev)
    run("checkout", "-q", "--detach", "FETCH_HEAD")
    head = run("rev-parse", "HEAD").stdout.strip()
    if head != rev:
        raise SystemExit(f"{dest}: checked out {head}, expected {rev}")
    marker.write_text(rev + "\n")
    log(f"fetched  {dest.name}")
    return True

def cmd_fetch_sources(args):
    p = paths(args.build)
    shallow_fetch(MORPHHB_URL, MORPHHB_REV, p["morphhb"])
    shallow_fetch(LEXICON_URL, LEXICON_REV, p["lexicon"])

# ------------------------------------------------------------------ import

def cmd_import(args):
    p = paths(args.build)
    wlc = p["morphhb"] / "wlc"
    if not wlc.is_dir():
        raise SystemExit("MorphHB cache missing; run fetch-sources first")
    if p["tokens"].exists() and not args.force:
        log(f"cached   {p['tokens'].name} ({sum(1 for _ in p['tokens'].open(encoding='utf-8'))} tokens)")
    else:
        import_morphhb.run(wlc, p["tokens"], MORPHHB_REV, qere_output=p["qere"])
    audit_morphhb.audit(wlc, p["tokens"])
    log("PASS independent verse/word-id audit of the token stream")

# ----------------------------------------------------------------- lexicon

def load_lexicon(directory):
    """LexicalIndex + AugIndex -> (entries{id: headword}, strong_index{num: {ids}},
    aug{key: id}, bdb_by_entry{id: bdbId})."""
    import xml.etree.ElementTree as ET
    local = lambda tag: tag.rsplit("}", 1)[-1]
    entries, bdb_by_entry, strong_index = {}, {}, defaultdict(set)
    for _, el in ET.iterparse(directory / "LexicalIndex.xml", events=("end",)):
        if local(el.tag) != "entry":
            continue
        entry_id = el.get("id")
        headword = next(("".join(w.itertext()).strip() for w in el if local(w.tag) == "w"), None)
        if entry_id and headword:
            entries[entry_id] = headword
            for xref in (x for x in el if local(x.tag) == "xref"):
                for strong in re.findall(r"\d+", xref.get("strong") or ""):
                    strong_index[str(int(strong))].add(entry_id)
                if xref.get("bdb"):
                    bdb_by_entry[entry_id] = xref.get("bdb")
        el.clear()
    aug = {}
    for _, el in ET.iterparse(directory / "AugIndex.xml", events=("end",)):
        if local(el.tag) == "w" and el.get("aug"):
            aug[el.get("aug")] = (el.text or "").strip()
        el.clear()
    return entries, strong_index, aug, bdb_by_entry

def resolve(aug_key, number, entries, strong_index, aug):
    """-> (lexiconEntryId, joinMethod) or (None, reason)."""
    for key, method in ((aug_key, "aug-index"), (number, "aug-index")):
        lex_id = aug.get(key)
        if lex_id in entries:
            return lex_id, method
    ids = strong_index.get(number, ())
    if len(ids) == 1:
        return next(iter(ids)), "unique-strong-fallback"
    return None, ("ambiguous-strong" if len(ids) > 1 else "unmapped-strong")

# ---------------------------------------------------------------- generate

def iter_tokens(path):
    with Path(path).open(encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                yield json.loads(line)

def generate_all(tokens_path, lexicon_dir):
    """One pass over the token stream -> {letter: entries rows}, unresolved, stats."""
    entries, strong_index, aug, _ = load_lexicon(lexicon_dir)
    occurrences = defaultdict(list)
    unresolved = defaultdict(lambda: {"tokenCount": 0, "exampleVerse": None, "reason": None})
    stats = Counter()
    seen = set()
    for token in iter_tokens(tokens_path):
        if token["tokenId"] in seen:
            raise ValueError("Duplicate tokenId: " + token["tokenId"])
        seen.add(token["tokenId"])
        stats["tokens"] += 1
        refs = lemma_refs(token.get("lemmaRaw"))
        if not refs:
            stats["tokensWithoutStrong"] += 1
            continue
        for number, aug_key in sorted(refs, key=lambda r: int(r[0])):
            lex_id, method = resolve(aug_key, number, entries, strong_index, aug)
            if lex_id is None:
                row = unresolved[aug_key]
                row["tokenCount"] += 1
                row["exampleVerse"] = row["exampleVerse"] or token["verseId"]
                row["reason"] = method
                stats["unresolvedRefs"] += 1
                continue
            headword = entries[lex_id]
            letter = consonants(headword)[:1]
            if letter not in LETTERS:
                stats["headwordWithoutHebrewInitial"] += 1
                continue
            occurrences[(letter, number, lex_id, headword, method)].append({
                "tokenId": token["tokenId"], "verseId": token["verseId"],
                "tokenPosition": token["tokenPosition"], "form": token["form"],
                "readingType": token["readingType"], "lemmaRaw": token.get("lemmaRaw"),
                "morphRaw": token.get("morphRaw"), "source": token["source"]})
            stats["assignedRefs"] += 1
    by_letter = defaultdict(list)
    for (letter, number, lex_id, headword, method), toks in sorted(
            occurrences.items(), key=lambda kv: (kv[0][0], consonants(kv[0][3]), int(kv[0][1]), kv[0][2])):
        by_letter[letter].append({"strongNumber": number, "lexiconEntryId": lex_id, "headword": headword,
                                  "joinMethod": method, "reviewStatus": "needs-human-review",
                                  "occurrenceCount": len(toks), "occurrences": toks})
    return by_letter, dict(unresolved), stats

PRESERVED_ENTRY_KEYS = ("reviewStatus",)  # plus every definition* key

def merge_letter(letter, rows, existing):
    """New rows + existing file -> merged file dict and a delta record."""
    old_entries = {(e["strongNumber"], e["lexiconEntryId"]): e for e in (existing or {}).get("entries", [])}
    merged, delta = [], {"letter": letter, "entriesAdded": [], "entriesRemoved": [], "occurrencesAdded": 0,
                         "occurrencesRemoved": 0, "positionChanges": [], "entriesOld": len(old_entries),
                         "entriesNew": len(rows), "occurrencesOld": sum(len(e["occurrences"]) for e in old_entries.values()),
                         "occurrencesNew": sum(len(r["occurrences"]) for r in rows)}
    for row in rows:
        key = (row["strongNumber"], row["lexiconEntryId"])
        old = old_entries.pop(key, None)
        if old is None:
            delta["entriesAdded"].append({"strong": row["strongNumber"], "headword": row["headword"], "occurrences": len(row["occurrences"])})
            merged.append(row)
            continue
        keep = {k: v for k, v in old.items() if k in PRESERVED_ENTRY_KEYS or k.startswith("definition")}
        old_tok = {o["tokenId"]: o for o in old["occurrences"]}
        new_tok = {o["tokenId"] for o in row["occurrences"]}
        delta["occurrencesAdded"] += len(new_tok - old_tok.keys())
        delta["occurrencesRemoved"] += len(old_tok.keys() - new_tok)
        for o in row["occurrences"]:
            prev = old_tok.get(o["tokenId"])
            if prev and prev["tokenPosition"] != o["tokenPosition"]:
                delta["positionChanges"].append({"tokenId": o["tokenId"], "verseId": o["verseId"],
                                                 "old": prev["tokenPosition"], "new": o["tokenPosition"]})
        entry = dict(row)
        entry.update(keep)
        merged.append(entry)
    for old in old_entries.values():
        delta["entriesRemoved"].append({"strong": old["strongNumber"], "headword": old["headword"], "occurrences": len(old["occurrences"])})
    summary = letter_summary(merged)
    out = {k: v for k, v in (existing or {}).items() if k not in ("entries", "entryCount", "totalOccurrences", "status", "summary")}
    out.update({
        "letter": letter, "status": letter_status(summary),
        "scope": "MorphHB-attested-headwords-standard-and-ketiv-only",
        "source": {"morphhbRevision": MORPHHB_REV, "hebrewLexiconRevision": LEXICON_REV, "license": LICENSE},
        "tokenPositionSemantics": "1-based index in the written token stream of the verse; Qere note words take no position",
        "limitations": [
            "Attested MorphHB Strong references only; not a complete dictionary of unattested lexemes",
            "Unmapped or genuinely ambiguous Strong references cannot be assigned to an initial letter",
            "Qere alternatives excluded pending explicit Ketiv-Qere alignment",
            "Machine lexicon joins and headwords are not independently scholarly reviewed"],
        "entryCount": len(merged), "totalOccurrences": sum(len(e["occurrences"]) for e in merged),
        "summary": summary, "entries": merged})
    # keep key order stable: letter, status, scope, source, ... then extras, then entries last
    ordered = {k: out[k] for k in ("letter", "status", "scope", "source", "tokenPositionSemantics", "limitations",
                                   "entryCount", "totalOccurrences", "summary")}
    ordered.update({k: v for k, v in out.items() if k not in ordered and k != "entries"})
    ordered["entries"] = merged
    return ordered, delta

def letter_summary(entries):
    v = lambda e, k: bool((e.get("definitionVerification") or {}).get(k))
    return {"entries": len(entries),
            "withDefinitionHe": sum(1 for e in entries if e.get("definitionHe")),
            "strongSourceChecked": sum(1 for e in entries if v(e, "strongSourceChecked")),
            "bdbSourceChecked": sum(1 for e in entries if v(e, "bdbSourceChecked")),
            "occurrenceCountChecked": sum(1 for e in entries if v(e, "occurrenceCountChecked")),
            "editoriallyApproved": sum(1 for e in entries if v(e, "editoriallyApproved"))}

def letter_status(s):
    n = s["entries"]
    if n and s["editoriallyApproved"] == n:
        return "editorially-approved"
    if n and s["withDefinitionHe"] == n and s["strongSourceChecked"] == n and s["bdbSourceChecked"] == n:
        return "source-cross-checked-pending-editorial-review"
    if n and s["withDefinitionHe"] == n:
        return "hebrew-glosses-drafted-pending-source-and-editorial-review"
    if s["withDefinitionHe"]:
        return "partially-defined-needs-human-review"
    return "machine-generated-needs-human-review"

def cmd_generate(args):
    p = paths(args.build)
    letters = LETTERS if args.all else "".join(args.letter or "")
    if not letters:
        raise SystemExit("give --letter X [--letter Y] or --all")
    for ch in letters:
        if ch not in LETTERS:
            raise SystemExit(f"not a Hebrew letter: {ch}")
    if not p["tokens"].exists():
        raise SystemExit("token stream missing; run import first")
    by_letter, unresolved, stats = generate_all(p["tokens"], p["lexicon"])
    alphabet = ROOT / "data" / "alphabet"
    deltas, written = [], []
    for letter in letters:
        existing_path = alphabet / f"{letter}.json"
        existing = read_json(existing_path) if existing_path.exists() else None
        merged, delta = merge_letter(letter, by_letter.get(letter, []), existing)
        deltas.append(delta)
        if args.write and write_json_if_changed(existing_path, merged):
            written.append(existing_path.name)
    if args.write and "ו" in letters:
        sync_vav_pilot_positions(alphabet / "ו.json")
    unresolved_doc = {"status": "unassigned-to-letter", "note": "Strong references with no unambiguous lexicon join, over the whole corpus",
                      "entries": [{"lemmaRef": k, **v} for k, v in sorted(unresolved.items(), key=lambda kv: -kv[1]["tokenCount"])]}
    manifest = {"status": "machine-generated-needs-human-review",
                "sourceRevisions": {"morphhb": MORPHHB_REV, "hebrewLexicon": LEXICON_REV},
                "tokenPositionSemantics": "written-stream-no-qere",
                "letters": [], "totalEntries": 0, "totalOccurrences": 0}
    for letter in LETTERS:
        f = alphabet / f"{letter}.json"
        if letter in letters:
            d = merge_letter(letter, by_letter.get(letter, []), read_json(f) if f.exists() else None)[0]
        else:
            d = read_json(f)
        manifest["letters"].append({"letter": letter, "entryCount": d["entryCount"], "occurrenceCount": d["totalOccurrences"]})
        manifest["totalEntries"] += d["entryCount"]; manifest["totalOccurrences"] += d["totalOccurrences"]
    if args.write:
        if write_json_if_changed(alphabet / "unresolved.json", unresolved_doc): written.append("unresolved.json")
        if write_json_if_changed(alphabet / "manifest.json", manifest): written.append("manifest.json")
    p["reports"].mkdir(parents=True, exist_ok=True)
    report = {"mode": "write" if args.write else "dry-run", "stats": dict(stats), "deltas": deltas,
              "unresolvedTop": unresolved_doc["entries"][:25], "written": written}
    (p["reports"] / "generate-delta.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # compact terminal summary
    log(f"tokens {stats['tokens']:,} | assigned refs {stats['assignedRefs']:,} | unresolved refs {stats['unresolvedRefs']:,} "
        f"({len(unresolved)} lemma refs) | tokens without Strong {stats['tokensWithoutStrong']:,}")
    log("L | entries old→new (+added −removed) | occurrences old→new | position changes")
    for d in deltas:
        log(f"{d['letter']} | {d['entriesOld']}→{d['entriesNew']} (+{len(d['entriesAdded'])} −{len(d['entriesRemoved'])}) | "
            f"{d['occurrencesOld']:,}→{d['occurrencesNew']:,} | {len(d['positionChanges'])}")
    log(f"total entries {manifest['totalEntries']:,}, occurrences {manifest['totalOccurrences']:,}; "
        f"{'written: ' + ', '.join(written) if args.write else 'DRY RUN, nothing written'}; "
        f"full report build/reports/generate-delta.json")

def sync_vav_pilot_positions(vav_path):
    pilot = ROOT / "data" / "letter-vav-occurrences.json"
    if not pilot.exists():
        return
    positions = {o["tokenId"]: o["tokenPosition"] for e in read_json(vav_path)["entries"] for o in e["occurrences"]}
    doc = read_json(pilot)
    for e in doc["entries"]:
        for o in e["occurrences"]:
            if o["tokenId"] in positions:
                o["tokenPosition"] = positions[o["tokenId"]]
    write_json_if_changed(pilot, doc)

# ------------------------------------------------------------------- audit

def xml_entry(xml, entry_id):
    m = re.search(r'<entry\b[^>]*\bid="' + re.escape(entry_id) + r'"[^>]*>([\s\S]*?)</entry>', xml)
    return m.group(1) if m else None

def xml_field(body, tag):
    m = re.search(r"<" + tag + r"(?:\s[^>]*)?>([\s\S]*?)</" + tag + ">", body)
    return m.group(1) if m else None

def xml_plain(s):
    s = re.sub(r"<[^>]*>", "", s)
    s = s.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&quot;", '"')
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    return re.sub(r"\s+", " ", s).strip()

def load_exceptions():
    return read_json(EXCEPTIONS_PATH) if EXCEPTIONS_PATH.exists() else {}

def cmd_audit(args):
    p = paths(args.build)
    letters = LETTERS if args.all else "".join(args.letter or "")
    if not letters:
        raise SystemExit("give --letter X or --all")
    if not p["tokens"].exists():
        raise SystemExit("token stream missing; run import first")
    tokens = {t["tokenId"]: t for t in iter_tokens(p["tokens"])}
    # newline="" keeps the source's CRLF line endings: stored excerpts are byte-exact copies of the XML.
    strong_xml = (p["lexicon"] / "HebrewStrong.xml").open(encoding="utf-8", newline="").read()
    bdb_xml = (p["lexicon"] / "BrownDriverBriggs.xml").open(encoding="utf-8", newline="").read()
    _, _, _, bdb_by_entry = load_lexicon(p["lexicon"])
    exceptions = load_exceptions()
    p["reports"].mkdir(parents=True, exist_ok=True)
    failed_total = 0
    log("L | entries | occurrences | occ failures (pos/form/lemma/morph/missing) | Strong/BDB excerpt failures | approved flags")
    for letter in letters:
        d = read_json(ROOT / "data" / "alphabet" / f"{letter}.json")
        rep = {"letter": letter, "checkedOccurrences": 0, "occurrenceFailures": [], "lexiconFailures": [], "flagFailures": []}
        kinds = Counter()
        for e in d["entries"]:
            for o in e["occurrences"]:
                rep["checkedOccurrences"] += 1
                t = tokens.get(o["tokenId"])
                if t is None:
                    kinds["missing"] += 1; rep["occurrenceFailures"].append({"tokenId": o["tokenId"], "kind": "missing-token"}); continue
                for field, kind in (("verseId", "verse"), ("tokenPosition", "pos"), ("form", "form"), ("lemmaRaw", "lemma"), ("morphRaw", "morph")):
                    if t.get(field) != o.get(field):
                        kinds[kind] += 1
                        rep["occurrenceFailures"].append({"tokenId": o["tokenId"], "verseId": o["verseId"], "kind": kind,
                                                          "stored": o.get(field), "source": t.get(field)})
            orig = e.get("definitionOriginalEnglish") or {}
            sid = "H" + e["strongNumber"]
            if orig.get("strong"):
                body = xml_entry(strong_xml, sid)
                if body is None:
                    rep["lexiconFailures"].append({"entry": sid, "kind": "strong-missing"})
                else:
                    for tag in ("source", "meaning", "usage"):
                        src = xml_field(body, tag)
                        stored = orig["strong"].get(tag + "Xml")
                        if stored is not None and (src or "") != stored:
                            rep["lexiconFailures"].append({"entry": sid, "kind": f"strong-{tag}-xml-differs"})
            if orig.get("bdb"):
                bid = orig["bdb"].get("entryId")
                via = exceptions.get(sid, {}).get("indexVia", sid)
                expected_bid = bdb_by_entry_for_strong(via, bdb_by_entry, p["lexicon"])
                if expected_bid and bid != expected_bid:
                    rep["lexiconFailures"].append({"entry": sid, "kind": "bdb-id-not-in-index", "stored": bid, "index": expected_bid})
                body = xml_entry(bdb_xml, bid) if bid else None
                excerpt = body.split("<status", 1)[0].strip() if body else None
                if excerpt is None:
                    rep["lexiconFailures"].append({"entry": sid, "kind": "bdb-missing", "stored": bid})
                elif excerpt != orig["bdb"].get("entryBodyXml"):
                    rep["lexiconFailures"].append({"entry": sid, "kind": "bdb-excerpt-differs"})
            ver = e.get("definitionVerification") or {}
            if ver.get("editoriallyApproved") and e.get("definitionReviewStatus") != "approved":
                rep["flagFailures"].append({"entry": sid, "kind": "approved-flag-without-approved-status"})
        rep["occurrenceFailureKinds"] = dict(kinds)
        rep["pass"] = not (rep["occurrenceFailures"] or rep["lexiconFailures"] or rep["flagFailures"])
        failed_total += 0 if rep["pass"] else 1
        (p["reports"] / f"audit-{letter}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        log(f"{letter} | {len(d['entries'])} | {rep['checkedOccurrences']:,} | {len(rep['occurrenceFailures'])} "
            f"({kinds['pos']}/{kinds['form']}/{kinds['lemma']}/{kinds['morph']}/{kinds['missing']}) | "
            f"{len(rep['lexiconFailures'])} | {len(rep['flagFailures'])} {'PASS' if rep['pass'] else 'FAIL'}")
    log(f"{len(letters) - failed_total}/{len(letters)} letters pass; reports in build/reports/audit-<letter>.json")
    return 1 if failed_total else 0

_strong_to_entry_cache = {}

def bdb_by_entry_for_strong(strong_id, bdb_by_entry, lexicon_dir):
    """Strong id ('H2053') -> BDB id through LexicalIndex xref strong=..., None if ambiguous/absent."""
    if not _strong_to_entry_cache:
        _, strong_index, _, _ = load_lexicon(lexicon_dir)
        _strong_to_entry_cache.update(strong_index)
    ids = _strong_to_entry_cache.get(strong_id.lstrip("H"), ())
    bdbs = {bdb_by_entry.get(i) for i in ids} - {None}
    return next(iter(bdbs)) if len(bdbs) == 1 else None

# --------------------------------------------- worksheet / enrich / lint

FINALS = str.maketrans("ךםןףץ", "כמנפצ")
HEDGES = ("כנראה", "ייתכן", "אינו ודאי", "אינה ודאית", "לא ודאי", "לא ודאית", "מסופק", "מסופקת")
PREFIXES = "והבכלמש"
STRONG_RAW = f"https://raw.githubusercontent.com/openscriptures/HebrewLexicon/{LEXICON_REV}/HebrewStrong.xml"
BDB_RAW = f"https://raw.githubusercontent.com/openscriptures/HebrewLexicon/{LEXICON_REV}/BrownDriverBriggs.xml"
VERIFY_METHOD = ("Strong and BDB XML matched against pinned revisions; Hebrew definitions are drafts pending "
                 "editorial review. MorphHB token fields checked directly.")

def letter_path(letter):
    return ROOT / "data" / "alphabet" / f"{letter}.json"

def read_xml_exact(path):
    # newline="" keeps CRLF: stored excerpts must be byte-exact copies of the XML.
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return fh.read()

def morph_pos(occ, number):
    """Part-of-speech code of the segment of morphRaw that carries Strong `number`:
    'Nc', 'Np' + type (Npm/Npf/Npl), 'Vq' (verb + stem), 'Aa', 'R' ...; Aramaic gets 'A:'."""
    lem, morph = (occ.get("lemmaRaw") or "").split("/"), occ.get("morphRaw") or ""
    if not morph:
        return "?"
    lang, segs = morph[0], morph[1:].split("/")
    idx = next((i for i, s in enumerate(lem) if re.match(r"\s*0*" + number + r"\b", s)), len(lem) - 1)
    seg = segs[idx] if idx < len(segs) else segs[-1]
    code = seg[:3] if seg.startswith("Np") else seg[:2] if seg[:1] in "NVAP" else seg[:1]
    return ("A:" if lang == "A" else "") + code

def entry_pos(entry):
    c = Counter(morph_pos(o, entry["strongNumber"]) for o in entry["occurrences"])
    return c.most_common(1)[0][0] if c else "?"

class Sources:
    """Pinned Strong + BDB XML and the LexicalIndex xref map, loaded once."""
    def __init__(self, lexicon_dir):
        self.strong_xml = read_xml_exact(lexicon_dir / "HebrewStrong.xml")
        self.bdb_xml = read_xml_exact(lexicon_dir / "BrownDriverBriggs.xml")
        self.entries, self.strong_index, _, self.bdb_by_entry = load_lexicon(lexicon_dir)

    def strong(self, number):
        body = xml_entry(self.strong_xml, "H" + number)
        if body is None:
            return None
        w = re.search(r'<w\b[^>]*\bpos="([^"]*)"', body)
        raw = {tag: xml_field(body, tag) or "" for tag in ("source", "meaning", "usage")}
        return {"pos": w.group(1) if w else "", "raw": raw, "plain": {k: xml_plain(v) for k, v in raw.items()}}

    def bdb(self, lex_id):
        bid = self.bdb_by_entry.get(lex_id)
        body = xml_entry(self.bdb_xml, bid) if bid else None
        if body is None:
            return None
        return {"entryId": bid, "entryBodyXml": body.split("<status", 1)[0].strip()}

def tsv_cell(s, limit=None):
    s = re.sub(r"\s+", " ", s or "").strip()
    return s[:limit - 1] + "…" if limit and len(s) > limit else s

def cmd_worksheet(args):
    p = paths(args.build)
    src = Sources(p["lexicon"])
    d = read_json(letter_path(args.letter))
    out = p["build"] / "worksheets" / f"{args.letter}.tsv"
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = ["strong\tlexId\theadword\tpos\tcount\tmeaning\tusage\tbdb\tverse"]
    missing = Counter()
    for e in d["entries"]:
        st, bdb = src.strong(e["strongNumber"]), src.bdb(e["lexiconEntryId"])
        missing["strong"] += st is None
        missing["bdb"] += bdb is None
        pos = entry_pos(e) + ("|" + st["pos"] if st and st["pos"] else "")
        lines.append("\t".join([e["strongNumber"], e["lexiconEntryId"], e["headword"], pos, str(len(e["occurrences"])),
                                tsv_cell(st and st["plain"]["meaning"], args.width),
                                tsv_cell(st and st["plain"]["usage"], args.width),
                                tsv_cell(bdb and xml_plain(bdb["entryBodyXml"]), args.bdb_width),
                                e["occurrences"][0]["verseId"] if e["occurrences"] else ""]))
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"{args.letter}: {len(d['entries'])} rows -> {out.relative_to(p['build'].parent) if out.is_relative_to(p['build'].parent) else out} "
        f"(no Strong {missing['strong']}, no BDB {missing['bdb']})")

def parse_drafts(path):
    """'strong|lexId|gloss' lines -> {(strong, lexId): gloss}; '#' comments and blanks ignored."""
    drafts, errors = {}, []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        parts = [x.strip() for x in line.split("|", 2)]
        if len(parts) != 3 or not parts[0].isdigit() or not parts[1] or not parts[2]:
            errors.append(f"line {n}: malformed")
            continue
        key = (str(int(parts[0])), parts[1])
        if key in drafts:
            errors.append(f"line {n}: duplicate {key}")
        drafts[key] = parts[2]
    return drafts, errors

def audit_passed(p, letter, total):
    f = p["reports"] / f"audit-{letter}.json"
    if not f.exists():
        return False
    rep = read_json(f)
    return bool(rep.get("pass")) and rep.get("checkedOccurrences") == total

def build_definition(entry, gloss, strong, bdb, occ_checked, exception=None):
    """Definition fields in the format of the ה/ו letters. Flags are true only for sources actually found."""
    number = entry["strongNumber"]
    hedged = any(h in gloss for h in HEDGES)
    both = strong is not None and bdb is not None
    fields = {
        "definitionHe": gloss,
        "definitionEn": strong["plain"]["meaning"] if strong else "",
        "definitionSource": {"name": "Strong’s Hebrew Dictionary (via Open Scriptures HebrewLexicon)",
                             "url": "https://github.com/openscriptures/HebrewLexicon",
                             "strongUrl": f"https://biblehub.com/hebrew/{number}.htm", "strongNumber": number},
        "definitionReviewStatus": "source-checked-pending-editorial-review" if both else "draft",
        "definitionConfidence": "uncertain" if hedged else "source-based",
        "definitionVerification": {
            "sources": [f"https://biblehub.com/hebrew/{number}.htm"],
            "dictionaries": [n for n, s in (("Strong", strong), ("Brown-Driver-Briggs", bdb)) if s is not None],
            "method": VERIFY_METHOD, "editoriallyApproved": False,
            "strongSourceChecked": strong is not None, "bdbSourceChecked": bdb is not None,
            "occurrenceCountChecked": bool(occ_checked)},
        "definitionOriginalEnglish": {},
    }
    if exception:
        fields["definitionNote"] = exception
    if strong:
        fields["definitionOriginalEnglish"]["strong"] = {
            **strong["plain"], "sourceUrl": STRONG_RAW, "entryId": "H" + number, "license": LICENSE,
            "format": "plain-text extraction of XML source, meaning and usage nodes", "verifiedAgainstSource": True,
            "sourceXml": strong["raw"]["source"], "meaningXml": strong["raw"]["meaning"],
            "usageXml": strong["raw"]["usage"], "sourceRevision": LEXICON_REV}
    if bdb:
        fields["definitionOriginalEnglish"]["bdb"] = {
            "entryId": bdb["entryId"], "entryBodyXml": bdb["entryBodyXml"], "sourceUrl": BDB_RAW, "license": LICENSE,
            "verifiedAgainstSource": True, "sourceFormat": "BDB XML entry body excluding status tag",
            "sourceRevision": LEXICON_REV, "verificationNote": "Matched pinned LexicalIndex and BDB source excerpt.",
            "scope": "lexical-opening-excerpt"}
    return fields

def cmd_enrich(args):
    p = paths(args.build)
    path = letter_path(args.letter)
    d = read_json(path)
    occ_before = json.dumps([e["occurrences"] for e in d["entries"]], ensure_ascii=False)
    n_entries, n_occ = len(d["entries"]), sum(len(e["occurrences"]) for e in d["entries"])
    drafts, errors = parse_drafts(args.drafts)
    src = Sources(p["lexicon"])
    exceptions = load_exceptions()
    occ_checked = audit_passed(p, args.letter, n_occ)
    keys = {(e["strongNumber"], e["lexiconEntryId"]) for e in d["entries"]}
    errors += [f"draft for unknown entry {k}" for k in sorted(set(drafts) - keys)]
    rep = {"letter": args.letter, "occurrenceCountChecked": occ_checked, "errors": errors,
           "exceptions": [], "withoutDraft": [], "enriched": 0}
    for e in d["entries"]:
        key = (e["strongNumber"], e["lexiconEntryId"])
        if key not in drafts:
            rep["withoutDraft"].append(f"{key[0]}|{key[1]}|{e['headword']}")
            continue
        strong, bdb = src.strong(e["strongNumber"]), src.bdb(e["lexiconEntryId"])
        note = None
        if strong is None or bdb is None:
            exc = exceptions.get("H" + e["strongNumber"])
            missing = [n for n, s in (("Strong", strong), ("BDB", bdb)) if s is None]
            note = (f"{' and '.join(missing)} entry not found for H{e['strongNumber']} / {e['lexiconEntryId']} "
                    f"in the pinned lexicon; no mapping was invented."
                    + (f" Documented exception: {exc['reason']}" if exc else ""))
            rep["exceptions"].append({"entry": "H" + e["strongNumber"], "lexiconEntryId": e["lexiconEntryId"],
                                      "headword": e["headword"], "missing": missing})
        for k in [k for k in e if k.startswith("definition")]:
            del e[k]
        e.update(build_definition(e, drafts[key], strong, bdb, occ_checked, note))
        rep["enriched"] += 1
    assert len(d["entries"]) == n_entries, "entry count changed"
    assert sum(len(e["occurrences"]) for e in d["entries"]) == n_occ, "occurrence count changed"
    assert json.dumps([e["occurrences"] for e in d["entries"]], ensure_ascii=False) == occ_before, "occurrences changed"
    summary = letter_summary(d["entries"])
    d["summary"], d["status"] = summary, letter_status(summary)
    p["reports"].mkdir(parents=True, exist_ok=True)
    (p["reports"] / f"enrich-{args.letter}.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if errors:
        for err in errors[:10]:
            log("ERROR " + err)
        raise SystemExit(f"{len(errors)} draft errors; nothing written (build/reports/enrich-{args.letter}.json)")
    changed = write_json_if_changed(path, d)
    log(f"{args.letter}: enriched {rep['enriched']}/{n_entries}, without draft {len(rep['withoutDraft'])}, "
        f"source exceptions {len(rep['exceptions'])}, occurrenceCountChecked={occ_checked}; "
        f"{'written' if changed else 'unchanged'}; status {d['status']}")
    for x in rep["exceptions"][:10]:
        log(f"  exception {x['entry']} {x['lexiconEntryId']} {x['headword']}: missing {'/'.join(x['missing'])}")

def norm_cons(word):
    return consonants(word).translate(FINALS)

def repeats_headword(gloss, headword):
    head = norm_cons(headword)
    if len(head) < 2:
        return False
    head_m = head[0] + head[1:].replace("ו", "").replace("י", "")
    for word in re.findall(r"[֐-׿]+", gloss):
        w = norm_cons(word)
        cands = {w}
        while len(w) > len(head) and w[0] in PREFIXES:
            w = w[1:]
            cands.add(w)
        if head in cands:
            return True
        if len(head_m) >= 3 and any(c[0] + c[1:].replace("ו", "").replace("י", "") == head_m for c in cands if c):
            return True
    return False

def sentence_count(gloss):
    return len([s for s in re.split(r"[.!?](?:\s|$)", gloss) if s.strip()])

def lint_entry(e):
    gloss = (e.get("definitionHe") or "").strip()
    if not gloss:
        return ["missing"]
    issues = []
    if repeats_headword(gloss, e["headword"]):
        issues.append("repeats-headword")
    if sentence_count(gloss) > 2:
        issues.append("more-than-two-sentences")
    if len(gloss) > 160:
        issues.append("over-160-chars")
    if "Np" in entry_pos(e) and len(re.findall(r"[֐-׿]+", gloss)) < 4:
        issues.append("proper-name-without-context")
    return issues

def cmd_lint(args):
    d = read_json(letter_path(args.letter))
    bad = [(e, lint_entry(e)) for e in d["entries"]]
    bad = [(e, i) for e, i in bad if i]
    for e, issues in bad[:args.max]:
        log(f"{e['strongNumber']}|{e['lexiconEntryId']}|{e['headword']}: {','.join(issues)} :: {e.get('definitionHe', '')}")
    log(f"{args.letter}: {len(bad)} of {len(d['entries'])} entries with lint violations")
    return 1 if bad else 0

# ------------------------------------------------------------------ status

def cmd_status(args):
    alphabet = ROOT / "data" / "alphabet"
    rows, totals = [], Counter()
    for letter in LETTERS:
        d = read_json(alphabet / f"{letter}.json")
        s = letter_summary(d["entries"])
        occ = sum(len(e["occurrences"]) for e in d["entries"])
        rows.append((letter, s["entries"], occ, s["withDefinitionHe"], s["strongSourceChecked"], s["bdbSourceChecked"],
                     s["occurrenceCountChecked"], s["editoriallyApproved"], d.get("status", "-")))
        for k, v in s.items():
            totals[k] += v
        totals["occurrences"] += occ
    lines = ["| אות | ערכים | היקרויות | פירוש עברי | Strong נבדק | BDB נבדק | טוקנים נבדקו | מאושר עריכתית | סטטוס |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    lines += [f"| {r[0]} | {r[1]} | {r[2]:,} | {r[3]} | {r[4]} | {r[5]} | {r[6]} | {r[7]} | {r[8]} |" for r in rows]
    lines.append(f"| **סה״כ** | **{totals['entries']:,}** | **{totals['occurrences']:,}** | **{totals['withDefinitionHe']}** | "
                 f"**{totals['strongSourceChecked']}** | **{totals['bdbSourceChecked']}** | **{totals['occurrenceCountChecked']}** | "
                 f"**{totals['editoriallyApproved']}** | |")
    table = "\n".join(lines)
    if args.write:
        from datetime import date
        doc = (f"# מצב 22 האותיות\n\nנוצר אוטומטית על ידי `python3 scripts/concordance.py status --write` "
               f"({date.today().isoformat()}). אין לערוך ידנית.\n\n{table}\n")
        changed = Path(args.write).write_text(doc, encoding="utf-8")
        log(f"wrote {args.write}")
    else:
        log(table)

# -------------------------------------------------------------------- main

def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--build", default=str(ROOT / "build"), help="cache/report directory (gitignored)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch-sources").set_defaults(fn=cmd_fetch_sources)
    s = sub.add_parser("import"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_import)
    for name, fn in (("generate", cmd_generate), ("audit", cmd_audit)):
        s = sub.add_parser(name)
        s.add_argument("--letter", action="append", help="Hebrew letter (repeatable)")
        s.add_argument("--all", action="store_true")
        if name == "generate":
            g = s.add_mutually_exclusive_group()
            g.add_argument("--dry-run", action="store_true", help="report the delta only (default)")
            g.add_argument("--write", action="store_true", help="write data/alphabet files")
        s.set_defaults(fn=fn)
    s = sub.add_parser("worksheet", help="compact TSV per entry: the only input for writing glosses")
    s.add_argument("--letter", required=True); s.add_argument("--width", type=int, default=140)
    s.add_argument("--bdb-width", type=int, default=200); s.set_defaults(fn=cmd_worksheet)
    s = sub.add_parser("enrich", help="join drafts with Strong/BDB excerpts and fill definition fields")
    s.add_argument("--letter", required=True); s.add_argument("--drafts", required=True); s.set_defaults(fn=cmd_enrich)
    s = sub.add_parser("lint", help="report missing/circular/too-long glosses")
    s.add_argument("--letter", required=True); s.add_argument("--max", type=int, default=40); s.set_defaults(fn=cmd_lint)
    s = sub.add_parser("status"); s.add_argument("--write", metavar="PATH"); s.set_defaults(fn=cmd_status)
    args = ap.parse_args(argv)
    return args.fn(args) or 0

if __name__ == "__main__":
    sys.exit(main())
