# י — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by a Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter י --write` | 520→544 entries (+24 homograph entries via AugIndex), 28,154→28,622 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter י --width 80` | 544 rows; Strong found 544, BDB found 544 |
| `python3 scripts/concordance.py enrich --letter י --drafts data/drafts/י.txt` | 544/544 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter י` | 0 violations (5 fixed: 2 root repeats, 3 place/person names without context) |
| `python3 scripts/concordance.py audit --letter י` | PASS: 28,622/28,622 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 544 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 544.
