#!/usr/bin/env python3
"""Build complete, reproducible Ketiv/standard occurrence records for checked ו headwords."""
import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

PART = re.compile(r"^(?:[a-z]+/)*(\d+)$", re.I)

def lemma_numbers(raw):
    if not raw:
        return set()
    result = set()
    for part in raw.split():
        match = PART.fullmatch(part)
        if match:
            result.add(str(int(match.group(1))))
    return result

def build(tokens_path, inventory):
    entries = inventory["entries"]
    wanted = {e["strongNumber"]: e for e in entries}
    found = defaultdict(list)
    seen = set()
    with tokens_path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            token = json.loads(line)
            token_id = token["tokenId"]
            if token_id in seen:
                raise ValueError(f"Duplicate source token: {token_id}")
            seen.add(token_id)
            for number in sorted(lemma_numbers(token.get("lemmaRaw")) & wanted.keys()):
                found[number].append({
                    "tokenId": token_id,
                    "verseId": token["verseId"],
                    "tokenPosition": token["tokenPosition"],
                    "form": token["form"],
                    "readingType": token["readingType"],
                    "lemmaRaw": token.get("lemmaRaw"),
                    "morphRaw": token.get("morphRaw"),
                    "source": token["source"],
                })
    for number, entry in wanted.items():
        if len(found[number]) != entry["tokenCount"]:
            raise ValueError(f"{entry['headword']}: expected {entry['tokenCount']} tokens, got {len(found[number])}")
        if entry["exampleVerse"] not in {x["verseId"] for x in found[number]}:
            raise ValueError(f"{entry['headword']}: missing checked example verse")
    return {
        "letter": "ו",
        "status": "source-cross-checked",
        "scope": "standard-and-ketiv-morphhb-tokens",
        "source": inventory["source"],
        "totalOccurrences": sum(len(v) for v in found.values()),
        "entries": [{
            "strongNumber": e["strongNumber"],
            "lexiconEntryId": e["lexiconEntryId"],
            "headword": e["headword"],
            "occurrenceCount": len(found[e["strongNumber"]]),
            "occurrences": found[e["strongNumber"]],
        } for e in entries],
    }

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tokens", required=True, type=Path)
    p.add_argument("--inventory", required=True, type=Path)
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    result = build(args.tokens, inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Verified {result['totalOccurrences']} occurrences for {len(result['entries'])} headwords")

if __name__ == "__main__":
    main()
