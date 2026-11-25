# נ — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by a Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter נ --write` | 388→475 entries (+87 homograph entries via AugIndex), 11,455→12,554 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter נ --width 80` | 475 rows; Strong found 475, BDB found 475 |
| `python3 scripts/concordance.py enrich --letter נ --drafts data/drafts/נ.txt` | 475/475 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter נ` | 0 violations |
| `python3 scripts/concordance.py audit --letter נ` | PASS: 12,554/12,554 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 475 drafts, 30 hedged as `uncertain`. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 475.
