#!/usr/bin/env python3
"""Fail CI if the source-derived letter-vav result diverges from checked data."""
import argparse
import json
import unicodedata
from pathlib import Path

FIELDS = ("strongNumber", "headword", "tokenCount", "exampleVerse", "lexiconEntryId")

def compare(generated, checked):
    expected = {e["strongNumber"]: e for e in checked["entries"]}
    actual = {e["strongNumber"]: e for e in generated["entries"]}
    if len(expected) != len(checked["entries"]) or len(actual) != len(generated["entries"]):
        raise ValueError("Duplicate Strong number")
    if expected.keys() != actual.keys():
        raise ValueError(f"Different keys: missing={sorted(expected.keys()-actual.keys())}; extra={sorted(actual.keys()-expected.keys())}")
    for key in sorted(expected):
        for field in FIELDS:
            a, b = expected[key][field], actual[key][field]
            if field == "headword":
                a, b = unicodedata.normalize("NFC", a), unicodedata.normalize("NFC", b)
            if a != b:
                raise ValueError(f"{key}: {field}: expected {a!r}, got {b!r}")
        if actual[key]["conjunctionPrefixTokens"]:
            raise ValueError(f"{key}: unexpected conjunction prefix tokens")
        if actual[key]["joinMethod"] != "aug-index":
            raise ValueError(f"{key}: non-authoritative fallback join")
    return len(expected)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--generated", type=Path, required=True)
    p.add_argument("--checked", type=Path, required=True)
    args = p.parse_args()
    n = compare(json.loads(args.generated.read_text(encoding="utf-8")),
                json.loads(args.checked.read_text(encoding="utf-8")))
    print(f"PASS: {n} source-cross-checked vav entries match pinned corpus and lexicon")

if __name__ == "__main__":
    main()
