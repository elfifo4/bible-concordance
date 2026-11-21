#!/usr/bin/env python3
"""Generate *candidates* for letter ו from MorphHB lemma references.

A Hebrew surface form starting with ו is not evidence of a ו headword.
Strong numbers are provisional keys; Hebrew headwords require a licensed lexicon.
"""
import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

LEMMA = re.compile(r"^((?:[a-z]+/)*)(\d+)$", re.I)

def candidates(records):
    counts = defaultdict(Counter)
    examples = {}
    for record in records:
        raw = record.get("lemmaRaw") or ""
        for part in raw.split():
            match = LEMMA.fullmatch(part)
            if not match:
                continue
            prefixes, number = match.groups()
            # Strong H-numbers are not a Hebrew-letter lookup. Retain as
            # references only; a later lexicon join resolves headword letters.
            counts[number]["tokens"] += 1
            if "c" in prefixes.rstrip("/").split("/"):
                counts[number]["conjunctionPrefixTokens"] += 1
            examples.setdefault(number, record["verseId"])
    return [
        {"strongNumber": key, "tokenCount": value["tokens"],
         "conjunctionPrefixTokens": value["conjunctionPrefixTokens"],
         "exampleVerse": examples[key], "headword": None,
         "initialLetter": None, "reviewStatus": "needs-lexicon-join"}
        for key, value in sorted(counts.items(), key=lambda item: int(item[0]))
    ]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--tokens", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    with args.tokens.open(encoding="utf-8") as handle:
        items = candidates(json.loads(line) for line in handle if line.strip())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"status": "candidate-lemma-index-not-letter-vav",
        "entries": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Indexed {len(items)} provisional Strong references; no letter-vav completeness claim")

if __name__ == "__main__":
    main()
