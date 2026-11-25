# ד — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ד --write` | 202→225 entries (+23 homograph entries via AugIndex), 7,071→7,251 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ד --width 80` | 225 rows; Strong found 225, BDB found 225 |
| `python3 scripts/concordance.py enrich --letter ד --drafts data/drafts/ד.txt` | 225/225 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ד` | 0 violations (3 fixed: 1 headword repeat, 2 place names without context) |
| `python3 scripts/concordance.py audit --letter ד` | PASS: 7,251/7,251 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 225 drafts, 23 marked `definitionConfidence: "uncertain"` (hedged rare words, places and identifications). Nine Strong numbers split into several lexicon entries (1699, 1713, 1760, 1793, 1799, 1803, 1826, 1861; 1817 into three); each entry has its own gloss. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 225.
