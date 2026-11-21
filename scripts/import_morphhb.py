#!/usr/bin/env python3
"""Extract token-level records from locally checked-out MorphHB OSIS XML.

No external dependencies. Run against a pinned MorphHB checkout:
  python3 scripts/import_morphhb.py --input /path/to/morphhb/wlc --output build/morphhb-tokens.jsonl --revision <40-char-commit-sha>

This is a staging extract, NOT the final concordance occurrences format.
"""
import argparse
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

VERSE = re.compile(r"^([A-Za-z0-9]+)\.(\d+)\.(\d+)$")
SHA = re.compile(r"^[0-9a-f]{40}$")


def local_name(tag):
    return tag.rsplit("}", 1)[-1]


def iter_tokens(path, revision):
    # OSIS may use nested verse elements or milestone sID/eID pairs.
    book = None
    chapter = None
    verse = None
    position = 0
    for event, element in ET.iterparse(path, events=("start", "end")):
        name = local_name(element.tag)
        if event == "start":
            if name == "div" and element.attrib.get("type") == "book":
                book = element.attrib.get("osisID") or book
            elif name == "chapter":
                chapter = element.attrib.get("osisID") or chapter
            elif name == "verse":
                if element.attrib.get("eID"):
                    verse = None
                else:
                    verse = element.attrib.get("osisID") or element.attrib.get("sID")
                    position = 0
            continue
        if name == "w" and verse:
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
                "lemmaRaw": element.attrib.get("lemma"),
                "morphRaw": element.attrib.get("morph"),
                "source": {"dataset": "openscriptures/morphhb", "revision": revision, "sourceTokenId": token_id},
            }
        elif name == "verse" and not element.attrib.get("sID"):
            # Nested verse closure; milestone verse end is handled on start.
            verse = None
        if name in ("w", "verse"):
            element.clear()


def run(input_dir, output_path, revision):
    if not SHA.fullmatch(revision):
        raise ValueError("--revision must be an exact 40-character lowercase Git commit SHA")
    sources = sorted(input_dir.glob("*.xml"))
    if not sources:
        raise ValueError(f"No XML files in {input_dir}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    seen = set()
    count = 0
    with output_path.open("w", encoding="utf-8") as out:
        for source in sources:
            for token in iter_tokens(source, revision):
                if token["tokenId"] in seen:
                    raise ValueError(f"Duplicate tokenId {token['tokenId']}")
                seen.add(token["tokenId"])
                out.write(json.dumps(token, ensure_ascii=False) + "\n")
                count += 1
    if not count:
        raise ValueError("No tokens extracted; check OSIS XML structure")
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
