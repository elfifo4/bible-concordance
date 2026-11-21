#!/usr/bin/env python3
"""Resolve MorphHB lemma references against the CC BY 4.0 OSHB Hebrew Lexicon.

AugIndex aug -> LexicalIndex entry ID is preferred; a Strong fallback is
accepted only when uniquely mapped. Unresolved/ambiguous references are kept.
"""
import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET

def local(tag):
    return tag.rsplit("}", 1)[-1]

def consonants(word):
    return "".join(ch for ch in unicodedata.normalize("NFD", word)
                   if "\u05d0" <= ch <= "\u05ea")

def load_lexicon(directory):
    entries = {}
    strong_index = defaultdict(set)
    for _, element in ET.iterparse(directory / "LexicalIndex.xml", events=("end",)):
        if local(element.tag) != "entry":
            continue
        entry_id = element.get("id")
        headword = next(("".join(w.itertext()).strip() for w in element
                         if local(w.tag) == "w"), None)
        refs = [w for w in element if local(w.tag) == "xref"]
        if entry_id and headword:
            entries[entry_id] = headword
            for xref in refs:
                for strong in re.findall(r"\d+", xref.get("strong") or ""):
                    strong_index[str(int(strong))].add(entry_id)
        element.clear()
    aug = {}
    for _, element in ET.iterparse(directory / "AugIndex.xml", events=("end",)):
        if local(element.tag) == "w" and element.get("aug"):
            aug[element.get("aug")] = (element.text or "").strip()
        element.clear()
    return entries, strong_index, aug

def resolve(candidates, entries, strong_index, aug):
    result = []
    for row in candidates:
        number = str(int(row["strongNumber"]))
        ids = set()
        method = None
        if number in aug and aug[number] in entries:
            ids = {aug[number]}
            method = "aug-index"
        elif number in strong_index and len(strong_index[number]) == 1:
            ids = strong_index[number]
            method = "unique-strong"
        for entry_id in sorted(ids):
            headword = entries[entry_id]
            if consonants(headword).startswith("ו"):
                result.append({**row, "headword": headword, "initialLetter": "ו",
                               "lexiconEntryId": entry_id, "joinMethod": method,
                               "reviewStatus": "needs-human-review"})
    return result

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidates", type=Path, required=True)
    p.add_argument("--lexicon", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    entries, strong_index, aug = load_lexicon(args.lexicon)
    candidates = json.loads(args.candidates.read_text(encoding="utf-8"))["entries"]
    resolved = resolve(candidates, entries, strong_index, aug)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({"letter": "ו", "status": "needs-human-review",
       "source": "openscriptures/HebrewLexicon", "license": "CC BY 4.0",
       "entries": resolved}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Resolved {len(resolved)} preliminary ו headwords (human review required)")

if __name__ == "__main__":
    main()
