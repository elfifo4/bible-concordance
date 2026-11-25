# ב — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by a Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ב --write` | 448→487 entries (+39 homograph entries via AugIndex, incl. בֵּן and בַּיִת), 10,626→18,712 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ב --width 80` | 487 rows; Strong found 487, BDB found 487 |
| `python3 scripts/concordance.py enrich --letter ב --drafts data/drafts/ב.txt` | 487/487 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ב` | 0 violations |
| `python3 scripts/concordance.py audit --letter ב` | PASS: 18,712/18,712 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 487 drafts. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 487.
