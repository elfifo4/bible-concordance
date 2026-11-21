# Pilot: letter ו (Vav)

## First milestone
Build a reproducible lemma-reference index from the pinned MorphHB token staging output. This is **not yet** a list of Hebrew headwords beginning with ו.

## Critical distinction
- Surface `וַיֹּאמֶר` starts with a conjunction prefix but belongs to a verb lemma, not necessarily a ו entry.
- A raw MorphHB `lemma` value may contain Strong references with prefix segments (`c/`, `b/`, etc.). A Strong number is not itself a Hebrew headword.
- Headword-initial filtering is permitted only after joining a verified, licensed Hebrew headword lexicon, and distinguishing homographs and proper names.
- Unknown or ambiguous lexicon matches must remain unresolved, never guessed.

## Run
```sh
python scripts/letter_vav_candidates.py --tokens build/morphhb-tokens.jsonl --output build/lemma-candidates.json
```

## Lexicon join implemented
`scripts/resolve_letter_vav.py` joins the provisional Strong index with
Open Scriptures Hebrew Lexicon's `AugIndex.xml` and `LexicalIndex.xml`.
It outputs candidate headwords with consonantal initial ו, preserving the
source lexicon entry ID and marking every entry for human review. Ambiguous
Strong-only matches are not guessed. The lexicon is CC BY 4.0: attribute the
Open Scriptures Hebrew Bible Project. The resulting candidate list is not
yet a complete, reviewed concordance.

## Next milestones
1. Pin the exact HebrewLexicon revision and audit unmatched/ambiguous lemma references.
2. Review candidate ו headwords and homographs manually.
3. Attach token occurrences and preserve sense uncertainty.
4. Generate the first per-entry JSON shards with provenance and tests.

**Status:** First milestone implemented, not yet verified against a generated real corpus artifact.

## Checked inventory

The checked, reproducible output is `data/letter-vav-verified.json`.
It contains ten Hebrew headwords with 31 standard/Ketiv tokens in the
pinned MorphHB extract. Each headword was matched to an OSHB LexicalIndex
entry through AugIndex, not inferred from a surface ו prefix. The full
CI run regenerates the candidates from the pinned source revisions and
compares **all ten** headwords, source IDs, example verses and counts.

This is a **source-verified inventory** within the scope of *attested
MorphHB Strong/AugIndex-linked entries*, not a claim that every possible
Hebrew lexeme, alternative Qere reading, or individual sense has been
reviewed by a scholar. In particular, apparent headword ו may be
lexically or text-critically disputed; preserve the upstream headword
and review such cases before assigning senses.

Source attribution: Open Scriptures MorphHB (CC BY 4.0 annotations,
WLC text public domain); Open Scriptures Hebrew Lexicon (CC BY 4.0).
