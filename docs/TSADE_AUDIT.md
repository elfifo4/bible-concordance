# צ — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter צ --write` | 237→302 entries (+65 homograph entries via AugIndex), 3,224→4,295 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter צ --width 80` | 302 rows; Strong found 302, BDB found 302 |
| `python3 scripts/concordance.py enrich --letter צ --drafts data/drafts/צ.txt` | 302/302 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter צ` | 0 violations (2 fixed: headword repeated inside a longer word, צוקה in מצוקה and צר in מבצר) |
| `python3 scripts/concordance.py audit --letter צ` | PASS: 4,295/4,295 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` + 3 Node tests | 35 tests OK; 3/3 Node tests pass |

Glosses: 302 drafts, 28 marked `definitionConfidence: "uncertain"` (hedged rare words, dubious readings and identifications, e.g. 6731 ציץ in Jer 48:9, 6795 צנח, 6852 צפר, 6861 צקלון, 6888 צררה). 27 Strong numbers split into several lexicon entries (6887 into five; 6767 and 6862 into four; 6696, 6735, 6793 and 6872 into three); each entry has its own gloss. One entry, 6887 `krz` (headword צוּר), is filed under Strong 6887 by the LexicalIndex, kept as given. Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 302.
