#!/usr/bin/env python3
"""Flag potentially circular Hebrew definitions; no data changes."""
import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIXES = ("", "ו", "ה", "ב", "כ", "ל", "מ", "ש", "וה", "וב", "וכ", "ול", "ומ", "וש", "בה", "לה", "מה")
SUFFIXES = ("", "ים", "ות", "י", "ו", "ה", "ך", "יו", "יהם", "יה", "נו")
FINAL = str.maketrans("ךםןףץ", "כמנפצ")

def words(value):
    return re.findall(r"[א-ת]+", re.sub(r"[\u0591-\u05bd\u05bf-\u05c7]", "", value))

def skeleton(value):
    return value.translate(FINAL).replace("ו", "").replace("י", "")

def classify(head, token):
    if head == token:
        return "exact"
    if any(p and p + head == token for p in PREFIXES):
        return "prefix"
    if len(skeleton(head)) >= 2 and skeleton(head) == skeleton(token):
        return "possible-plene"
    if len(head) >= 3 and any(
        (p or s) and (p + head + s).translate(FINAL) == token.translate(FINAL)
        for p in PREFIXES for s in SUFFIXES
    ):
        return "possible-inflection"
    return None

def audit():
    for path in sorted((ROOT / "data/alphabet").glob("?.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        for entry in data["entries"]:
            definition = entry.get("definitionHe") or ""
            heads = words(entry.get("headword") or "")
            if not definition or not heads:
                continue
            # Phrase headwords: flag the whole phrase, not every constituent.
            tokens = words(definition)
            if len(heads) > 1:
                if any(tokens[i:i+len(heads)] == heads for i in range(len(tokens))):
                    yield [path.stem, entry["strongNumber"], entry["headword"], definition, "exact-phrase"]
                continue
            matches = sorted({(token, kind) for token in tokens if (kind := classify(heads[0], token))})
            if matches:
                yield [path.stem, entry["strongNumber"], entry["headword"], definition, "; ".join(f"{t}:{k}" for t,k in matches)]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    findings = list(audit())
    if args.json:
        print(json.dumps(findings, ensure_ascii=False, indent=2))
    else:
        for row in findings:
            print("\t".join(map(str, row)))
        print(f"Candidates: {len(findings)} (manual lexical review required)")
