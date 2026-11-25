# ג — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session, glosses only by a Claude Opus session.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ג --write` | 314→339 entries (+25 homograph entries via AugIndex), 4,400→5,764 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ג --width 80` | 339 rows; Strong found 339, BDB found 339 |
| `python3 scripts/concordance.py enrich --letter ג --drafts data/drafts/ג.txt` | 339/339 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ג` | 0 violations (1 fixed: גִּמְזוֹ repeated the headword in its identification) |
| `python3 scripts/concordance.py audit --letter ג` | PASS: 5,764/5,764 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 339 drafts, 23 marked `definitionConfidence: "uncertain"`. Doubtful readings noted by the writer: גה (1454), גרל (1632), גשם (1656), גזרי (1511); mappings that look off: 1350 cbv, 1388, 1394, 1402. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 339.
