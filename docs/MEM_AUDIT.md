# מ — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by one Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter מ --write` | 974→1,091 entries (+117 homograph entries via AugIndex, incl. מִן), 20,743→23,481 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter מ --width 80` | 1,091 rows; Strong found 1,091, BDB found 1,091 |
| `python3 scripts/concordance.py enrich --letter מ --drafts data/drafts/מ.txt` | 1,091/1,091 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter מ` | 0 violations on the first run |
| `python3 scripts/concordance.py audit --letter מ` | PASS: 23,481/23,481 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 1,091 drafts, 68 hedged as `uncertain`. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 1,091. With מ, every letter that had no glosses now has verified drafts; ו/ה/ל/ט/ז/כ still carry the pre-CLI data and await the regeneration round.
