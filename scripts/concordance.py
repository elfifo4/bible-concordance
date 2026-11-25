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
    s = sub.add_parser("status"); s.add_argument("--write", metavar="PATH"); s.set_defaults(fn=cmd_status)
    args = ap.parse_args(argv)
    return args.fn(args) or 0

if __name__ == "__main__":
    sys.exit(main())
