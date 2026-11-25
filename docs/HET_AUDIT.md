# ח — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by one Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ח --write` | 568→692 entries (+124 homograph entries via AugIndex), 8,141→10,921 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ח --width 80` | 692 rows; Strong found 692, BDB found 692 |
| `python3 scripts/concordance.py enrich --letter ח --drafts data/drafts/ח.txt` | 692/692 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ח` | 0 violations (4 root repeats fixed) |
| `python3 scripts/concordance.py audit --letter ח` | PASS: 10,921/10,921 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 692 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 692.
