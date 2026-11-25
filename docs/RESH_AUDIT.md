# ר — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by a Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ר --write` | 352→410 entries (+58 homograph entries via AugIndex), 6,354→9,058 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ר --width 80` | 410 rows; Strong found 410, BDB found 410 |
| `python3 scripts/concordance.py enrich --letter ר --drafts data/drafts/ר.txt` | 410/410 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ר` | 0 violations |
| `python3 scripts/concordance.py audit --letter ר` | PASS: 9,058/9,058 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 410 drafts, 28 hedged as `uncertain`. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 410.
