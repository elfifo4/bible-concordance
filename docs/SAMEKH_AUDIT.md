# ס — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ס --write` | 194→239 entries (+45 homograph entries via AugIndex), 2,201→2,941 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ס` | 239 rows; Strong found 239, BDB found 239 |
| `python3 scripts/concordance.py enrich --letter ס --drafts data/drafts/ס.txt` | 239/239 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ס` | 0 violations |
| `python3 scripts/concordance.py audit --letter ס` | PASS: 2,941/2,941 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 239 drafts, 45 marked `definitionConfidence: "uncertain"` (hedged rare words and names). Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 239.
