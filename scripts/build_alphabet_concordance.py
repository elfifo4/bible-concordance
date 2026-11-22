#!/usr/bin/env python3
"""Generate source-traceable concordance files for all 22 Hebrew initial letters.

Only unambiguous AugIndex -> LexicalIndex joins are classified. Ambiguous and
unmapped Strong references are reported separately, never silently discarded.
The coverage is the pinned MorphHB written (Ketiv/standard) token stream;
Qere variants require a separate alignment and are not silently conflated.
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
from scripts.build_letter_vav_occurrences import lemma_numbers
from scripts.resolve_letter_vav import load_lexicon, consonants

LETTERS = "אבגדהוזחטיכלמנסעפצקרשת"

def generate(tokens, lexicon, letter):
    if letter not in LETTERS or len(letter) != 1:
        raise ValueError("Expected one of 22 Hebrew letters")
    entries, strong_index, aug = load_lexicon(lexicon)
    occurrences = defaultdict(list)
    unresolved = defaultdict(lambda: {"tokenCount": 0, "exampleVerse": None, "reason": None})
    observed = set()
    for line in tokens.open(encoding="utf-8"):
        if not line.strip():
            continue
        token = json.loads(line)
        if token["tokenId"] in observed:
            raise ValueError("Duplicate tokenId: " + token["tokenId"])
        observed.add(token["tokenId"])
        for number in sorted(lemma_numbers(token.get("lemmaRaw")), key=int):
            lex_id = aug.get(number)
            if lex_id not in entries:
                if number in strong_index and len(strong_index[number]) == 1:
                    lex_id = next(iter(strong_index[number]))
                    method = "unique-strong-fallback"
                else:
                    row = unresolved[number]
                    row["tokenCount"] += 1
                    row["exampleVerse"] = row["exampleVerse"] or token["verseId"]
                    row["reason"] = "ambiguous-strong" if len(strong_index.get(number, ())) > 1 else "unmapped-strong"
                    continue
            else:
                method = "aug-index"
            headword = entries[lex_id]
            first = consonants(headword)[:1]
            if first != letter:
                continue
            occurrences[(number, lex_id, headword, method)].append({
                "tokenId": token["tokenId"],
                "verseId": token["verseId"],
                "tokenPosition": token["tokenPosition"],
                "form": token["form"],
                "readingType": token["readingType"],
                "lemmaRaw": token.get("lemmaRaw"),
                "morphRaw": token.get("morphRaw"),
                "source": token["source"],
            })
    rows = []
    for (number, lex_id, headword, method), tokens_for_entry in sorted(
        occurrences.items(), key=lambda kv: (consonants(kv[0][2]), int(kv[0][0]), kv[0][1])
    ):
        rows.append({"strongNumber": number, "lexiconEntryId": lex_id,
                     "headword": headword, "joinMethod": method,
                     "reviewStatus": "needs-human-review",
                     "occurrenceCount": len(tokens_for_entry),
                     "occurrences": tokens_for_entry})
    return {"letter": letter, "status": "machine-generated-needs-human-review",
            "scope": "MorphHB-attested-headwords-standard-and-ketiv-only",
            "source": {"morphhbRevision": "db6c5c9b46b8f39346f10915ddb1a70dcd429901",
                       "hebrewLexiconRevision": "21c9add13bc727d3a951361778e97e3ff7afd1ce",
                       "license": "CC BY 4.0"},
            "limitations": [
                "Attested MorphHB Strong references only; not a complete dictionary of unattested lexemes",
                "Unmapped or ambiguous Strong references cannot be assigned to an initial letter",
                "Qere alternatives excluded pending explicit Ketiv-Qere alignment",
                "Machine lexicon joins and headwords are not independently scholarly reviewed"
            ],
            "entryCount": len(rows),
            "totalOccurrences": sum(x["occurrenceCount"] for x in rows),
            "entries": rows}, unresolved

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tokens", required=True, type=Path)
    p.add_argument("--lexicon", required=True, type=Path)
    p.add_argument("--letter", required=True)
    p.add_argument("--output", required=True, type=Path)
    p.add_argument("--unresolved-output", type=Path)
    args = p.parse_args()
    result, unresolved = generate(args.tokens, args.lexicon, args.letter)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.unresolved_output:
        args.unresolved_output.parent.mkdir(parents=True, exist_ok=True)
        args.unresolved_output.write_text(json.dumps(
            {"status": "unassigned-to-letter", "entries": [
                {"strongNumber": k, **v} for k, v in sorted(unresolved.items(), key=lambda kv: int(kv[0]))
            ]}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{args.letter}: {result['entryCount']} headwords, {result['totalOccurrences']} occurrences")

if __name__ == "__main__":
    main()
