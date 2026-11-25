# ע — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session; glosses by two Claude Opus sessions (rows 1–345, 346–690).

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ע --write` | 581→690 entries (+109 homograph entries via AugIndex, incl. עַל, עָשָׂה, עַם, עִיר), 12,778→28,196 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ע --width 80` | 690 rows; Strong found 690, BDB found 690 |
| `python3 scripts/concordance.py enrich --letter ע --drafts data/drafts/ע.txt` | 690/690 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ע` | 0 violations (5 fixed: 3 spelling-variant mentions of the headword, 2 names without context) |
| `python3 scripts/concordance.py audit --letter ע` | PASS: 28,196/28,196 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 690 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 690.
