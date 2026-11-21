#!/usr/bin/env python3
"""Independent OSIS source audit, comparing verse IDs and written-word IDs to staging."""
import argparse
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

def name(tag):
    return tag.rsplit("}", 1)[-1]

def audit(source_dir, output):
    actual = {}
    for path in sorted(source_dir.glob("*.xml")):
        if path.name == "VerseMap.xml":
            continue
        verses = set()
        words = set()
        current = None
        inside_note = 0
        for event, elem in ET.iterparse(path, events=("start", "end")):
            tag = name(elem.tag)
            if event == "start":
                if tag == "note":
                    inside_note += 1
                if tag == "verse":
                    if elem.get("eID"):
                        current = None
                    else:
                        current = elem.get("osisID") or elem.get("sID")
                        if current:
                            verses.add(current)
                if tag == "w" and current and not inside_note:
                    word_id = elem.get("id")
                    if not word_id:
                        raise ValueError(f"{path}: missing written word ID")
                    if word_id in words:
                        raise ValueError(f"{path}: duplicate written word ID {word_id}")
                    words.add(word_id)
            else:
                if tag == "note":
                    inside_note -= 1
                if tag == "verse" and not elem.get("sID"):
                    current = None
                elem.clear()
        actual[path.stem] = {"verses": verses, "words": words}
    if len(actual) != 39:
        raise ValueError(f"Expected 39 books, got {len(actual)}")
    extracted = {}
    with output.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            book = row["verseId"].split(".")[0]
            group = extracted.setdefault(book, {"verses": set(), "words": set()})
            group["verses"].add(row["verseId"])
            group["words"].add(row["tokenId"])
    for book, expected in actual.items():
        got = extracted.get(book)
        if not got:
            raise ValueError(f"Missing book {book}")
        for field in ("verses", "words"):
            missing = expected[field] - got[field]
            extra = got[field] - expected[field]
            if missing or extra:
                raise ValueError(f"{book} {field}: missing {len(missing)}, extra {len(extra)}; samples {list(sorted(missing))[:3]}")
        print(f"{book}: {len(expected['verses'])} verses, {len(expected['words'])} written tokens verified")
    if set(extracted) != set(actual):
        raise ValueError(f"Unexpected books: {set(extracted) - set(actual)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    audit(args.input, args.output)
