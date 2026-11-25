# ת — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter ת --write` | 287→319 entries (+32 homograph entries via AugIndex), 3,831→4,054 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter ת --width 80` | 319 rows; Strong found 319, BDB found 319 |
| `python3 scripts/concordance.py enrich --letter ת --drafts data/drafts/ת.txt` | 319/319 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter ת` | 0 violations (8 fixed: headword repeated, mostly hidden in a longer word, e.g. תאר in בתיאור/מתאר, תהלוכה, תור, תחלה in התחלה, תימן in תימני) |
| `python3 scripts/concordance.py audit --letter ת` | PASS: 4,054/4,054 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` + 3 Node tests | 35 tests OK; 3/3 Node tests pass |

Glosses: 319 drafts, 41 marked `definitionConfidence: "uncertain"` (hedged rare words, dubious readings and identifications, e.g. 8377 תאו, 8437 תולל, 8534 תלתלים, 8580 תנשמת, 8601 תפינים, 8649 תרמה, 8662 תרתק). 15 Strong numbers split into two lexicon entries each (e.g. 8385 תאנה/תֹּאֲנָה, 8433 תוכחה/תוכחת, 8438 תולע/תולעה, 8556 תמנת חרס/תמנת סרח, 8615 תקוה hope/cord); each entry has its own gloss. Near-homographs (תּוֹר / תֹּר, תָּמָר / תֹּמֶר / תִּמֹרָה, תֵּבֵל / תֶּבֶל, תָּם / תֹּם / תָּמִים / תֻּמִּים, תָּא / תָּאָה) have distinct glosses. Two entries are filed by the LexicalIndex under another headword's Strong number, kept as given: 8453 `nyj` (תִּשְׁבֶּה, Elijah's home) and 5774 `nvp` (תְּעֻפָה). Status `source-checked-pending-editorial-review`; `editoriallyApproved: false` for all 319.
