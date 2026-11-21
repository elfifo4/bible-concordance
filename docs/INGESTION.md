# MorphHB ingestion foundation

This is the first reproducible extraction step, **not a finished concordance**.

## Source and license
- Source: https://github.com/openscriptures/morphhb
- Morphological/lemma annotations: CC BY 4.0; biblical WLC text: public domain, as stated in upstream README and LICENSE.md.
- Required upstream attribution: "Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb".
- Pin an exact source commit and preserve it in each extracted record.

## Run
```sh
git clone https://github.com/openscriptures/morphhb.git /tmp/morphhb
cd /tmp/morphhb
git rev-parse HEAD  # copy this exact SHA
cd -
python3 scripts/import_morphhb.py --input /tmp/morphhb/wlc --output build/morphhb-tokens.jsonl --revision <SHA>
python3 -m unittest discover -s tests -v
```

Do not commit the generated `build/` files. This first pass preserves raw lemma/morphology and token IDs; it does **not** derive Hebrew headwords, classify senses, or claim full-corpus coverage.

## Known limitations and QA gates
- Validate actual upstream XML against the parser before production use; the included test covers a synthetic OSIS milestone sample.
- Verify nested verse structures, qere/ketiv, note text, word segments, source book codes, and uniqueness against the full corpus.
- Source verse IDs (e.g. `Gen.1.1`) are retained as-is in staging. Canonical `GEN.1.1` conversion belongs to a separately tested mapping layer.
- Word-level OSIS IDs are the primary source identifiers; do not substitute character offsets in Sefaria.
- No alphabet-letter filtering until lexical normalization strips prefixes and resolves lemmas.

Next: run against a pinned MorphHB revision, inspect coverage/edge cases, then implement lemma normalization and a letter-ו pilot.

## Red-team hardening (PR #3)

- Import rejects input with other than 39 top-level WLC XML files (the Hebrew Bible's book count).
- Verse milestone mismatches, overlapping verses, duplicate verse IDs within a file, unanchored words and missing IDs fail fast.
- Output is written to a temporary file and atomically replaced only after successful extraction.
- Pull-request CI runs the synthetic unit tests.

**Remaining release blockers:** These checks are not a proof of complete verse/token coverage. Run against a pinned real MorphHB revision and compare per-book verse and token counts against a separately established baseline. Verify qere/ketiv, nested word elements, and XML notes before treating the staging output as production data. The synthetic unit tests do not replace corpus-level validation.
