# ק — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ק --write` | 283→334 entries (+51 homograph entries via AugIndex), 5,174→7,237 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ק --width 80` | 334 rows; Strong found 334, BDB found 334 |
| `python3 scripts/concordance.py enrich --letter ק --drafts data/drafts/ק.txt` | 334/334 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ק` | 0 violations (1 fixed: קַל hidden in משקל) |
| `python3 scripts/concordance.py audit --letter ק` | PASS: 7,237/7,237 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` + 3 Node tests | 35 tests OK; 3/3 Node tests pass |

Glosses: 334 drafts, 34 marked `definitionConfidence: "uncertain"` (hedged rare words, dubious readings and identifications, e.g. 6906 קבע, 6957 קַו in Isa 28:10, 6978 קַוְקָו, 6985 קָט, 7053 קִלְּשׁוֹן, 7082 קסס, 7171 קֶרֶץ, 7189 קֹשֶׁט "bow"). 23 Strong numbers split into two or three lexicon entries each (e.g. 6957 קַו mimicry/line, 6960 קָוָה wait/collect, 7049 קָלַע carve/sling, 7050 קֶלַע curtain/sling, 7097 קֵצֶה/קָצֶה, 7105 קָצִיר harvest/boughs, 7110 קֶצֶף wrath/splinter, 7114 קָצֵר short/reap, 7136 קָרָה meet/beam, 7189 קֹשְׁטְ truth/קֹשֶׁט bow); each entry has its own gloss. Near-homographs (קוֹל / קֹל / קַל / קָל, קוּם / קוֹמָה / קָמָה, קָרָא / קָרָה / קָרֶה / קֹרֵא, קֵץ / קָצֶה / קָצָה / קָצַץ / קְצָת, קֶרֶן verb/noun/Aramaic, קַשׁ / קָשָׁה / קָשֶׁה) have distinct glosses. Entries filed by the LexicalIndex under another headword's Strong number, kept as given: 5356 `ldy` (קֵהָיוֹן, BDB conjecture for Amos 4:6), 4723 `lem` (קֹוֶה, Kue), 6892 `lgh` (קִיא), 6979 `lnq`/`lnr` (קָרַר), 7161 `lne` (קַרְנַיִם). Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 334.
