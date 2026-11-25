# א — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by one Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter א --write` | 832→899 entries (+67 homograph entries via AugIndex, incl. אֲשֶׁר, אִם, אַתָּה), 52,808→61,891 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter א --width 80` | 899 rows; Strong found 899, BDB found 899 |
| `python3 scripts/concordance.py enrich --letter א --drafts data/drafts/א.txt` | 899/899 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter א` | 0 violations on the first run |
| `python3 scripts/concordance.py audit --letter א` | PASS: 61,891/61,891 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 899 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 899. Note: `data/alphabet/א.json` is now 26 MB; splitting or compressing the large letter files for the site remains an open item.
