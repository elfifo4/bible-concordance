#!/usr/bin/env python3
"""Extract token-level records from locally checked-out MorphHB OSIS XML.

No external dependencies. Run against a pinned MorphHB checkout:
  python3 scripts/import_morphhb.py --input /path/to/morphhb/wlc --output build/morphhb-tokens.jsonl --revision <40-char-commit-sha>

This is a staging extract, NOT the final concordance occurrences format.
"""
import argparse
import json
import os
import tempfile
import re
import xml.etree.ElementTree as ET
from pathlib import Path

VERSE = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def iter_tokens(path, revision, stats=None):
    stats = stats if stats is not None else {}
    # OSIS may use nested verse elements or milestone sID/eID pairs.
    book = None
    chapter = None
    verse = None
    position = 0
    seen_verses = set()
    stack = []
    for event, element in ET.iterparse(path, events=("start", "end")):
        name = local_name(element.tag)
        if event == "start":
            stack.append((name, element.attrib.get("type")))
            if name == "div" and element.attrib.get("type") == "book":
                book = element.attrib.get("osisID") or book
            elif name == "chapter":
                chapter = element.attrib.get("osisID") or chapter
            elif name == "verse":
                if element.attrib.get("eID"):
                    if verse != element.attrib["eID"]:
                        raise ValueError(f"{path}: unmatched verse end {element.attrib['eID']}")
                    verse = None
                else:
                    new_verse = element.attrib.get("osisID") or element.attrib.get("sID")
                    if not new_verse or not VERSE.fullmatch(new_verse):
                        raise ValueError(f"{path}: invalid verse ID {new_verse!r}")
                    if verse is not None or new_verse in seen_verses:
                        raise ValueError(f"{path}: overlapping or duplicate verse {new_verse}")
                    verse = new_verse
                    seen_verses.add(verse)
                    stats["verses"] = stats.get("verses", 0) + 1
                    position = 0
            elif name == "w" and verse is None:
                raise ValueError(f"{path}: word outside verse")
            continue
        if name == "w" and verse:
            in_qere = any(tag == "rdg" and typ == "x-qere" for tag, typ in stack)
            in_note = any(tag == "note" for tag, _ in stack)
            if in_qere:
                stats["qereWords"] = stats.get("qereWords", 0) + 1
                stack.pop()
                element.clear()
                continue
            if in_note:
                raise ValueError(f"{path}: unrecognized word inside note at {verse}")
            if element.attrib.get("type") == "x-ketiv":
                stats["ketivWords"] = stats.get("ketivWords", 0) + 1
            match = VERSE.fullmatch(verse)
            if not match:
                raise ValueError(f"{path}: unexpected verse ID {verse!r}")
            position += 1
            form = "".join(element.itertext())
            token_id = element.attrib.get("id")
            if not token_id:
                raise ValueError(f"{path}: missing immutable word id at {verse} position {position}")
            yield {
                "tokenId": token_id,
                "verseId": verse,
                "tokenPosition": position,
                "form": form,
                "readingType": "ketiv" if element.attrib.get("type") == "x-ketiv" else "standard",
                "lemmaRaw": element.attrib.get("lemma"),
                "morphRaw": element.attrib.get("morph"),
                "source": {"dataset": "openscriptures/morphhb", "revision": revision, "sourceTokenId": token_id},
            }
        elif name == "verse" and not element.attrib.get("sID"):
            # Nested verse closure; milestone verse end is handled on start.
            verse = None
        stack.pop()
        if name in ("w", "verse", "note"):
            element.clear()
    if verse is not None:
        raise ValueError(f"{path}: unclosed verse {verse}")
    if not seen_verses:
        raise ValueError(f"{path}: no verses found")


def run(input_dir, output_path, revision, expected_books=39):
    if not SHA.fullmatch(revision):
        raise ValueError("--revision must be an exact 40-character lowercase Git commit SHA")
    sources = sorted(p for p in input_dir.glob("*.xml") if p.name != "VerseMap.xml")
    if len(sources) != expected_books:
        raise ValueError(f"Expected {expected_books} book XML files, found {len(sources)}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    count = 0
    fd, temp_name = tempfile.mkstemp(prefix=".morphhb-", suffix=".tmp", dir=output_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            for source in sources:
                stats = {"verses": 0}
                for token in iter_tokens(source, revision, stats):
                    if token["tokenId"] in seen:
                        raise ValueError(f"Duplicate tokenId {token['tokenId']}")
                    seen.add(token["tokenId"])
                    out.write(json.dumps(token, ensure_ascii=False) + "\n")
                    count += 1
                if stats["verses"] == 0:
                    raise ValueError(f"{source}: no verses")
        if not count:
            raise ValueError("No tokens extracted")
        os.replace(temp_name, output_path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    print(f"Extracted {count} tokens from {len(sources)} XML files to {output_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="MorphHB wlc directory")
    parser.add_argument("--output", type=Path, required=True, help="Staging JSONL path")
    parser.add_argument("--revision", required=True, help="Pinned MorphHB Git commit SHA")
    args = parser.parse_args()
    run(args.input, args.output, args.revision)


if __name__ == "__main__":
    main()
