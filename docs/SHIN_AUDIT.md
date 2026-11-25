# ש — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by one Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ש --write` | 744→855 entries (+111 homograph entries via AugIndex), 20,468→22,449 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ש --width 80` | 855 rows; Strong found 855, BDB found 855 |
| `python3 scripts/concordance.py enrich --letter ש --drafts data/drafts/ש.txt` | 855/855 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ש` | 0 violations (5 root repeats fixed) |
| `python3 scripts/concordance.py audit --letter ש` | PASS: 22,449/22,449 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 855 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 855.
