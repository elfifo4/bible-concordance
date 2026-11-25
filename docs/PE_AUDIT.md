# פ — audit (2026-11-25)

Pinned sources: MorphHB `db6c5c9b`, HebrewLexicon `21c9add1`. All commands run locally. Split process: mechanical steps by script from the main session; glosses drafted by a Claude **Sonnet** session as a cost experiment, then 40 sampled glosses graded by a Claude Opus session (random 20: A 11 / B 8 / C 1; hedged 20: A 15 / B 5 / C 0; no factual errors) and the 14 B/C corrections applied.

| Command | Result |
|---|---|
| `python3 scripts/concordance.py generate --letter פ --write` | 320→366 entries (+46 homograph entries via AugIndex), 6,564→7,449 occurrences, 0 position changes |
| `python3 scripts/concordance.py worksheet --letter פ --width 80` | 366 rows; Strong found 366, BDB found 366 |
| `python3 scripts/concordance.py enrich --letter פ --drafts data/drafts/פ.txt` | 366/366 enriched, 0 source exceptions, occurrence count checked |
| `python3 scripts/concordance.py lint --letter פ` | 0 violations (4 fixed: 2 root repeats in פָּרַשׁ/פְּרַשׁ, 2 names without context) |
| `python3 scripts/concordance.py audit --letter פ` | PASS: 7,449/7,449 occurrences, 0 Strong/BDB excerpt failures |
| `python3 -m unittest discover -s tests` | 35 tests OK |

Glosses: 366 drafts, 42 hedged. Known limits of the Sonnet drafts (from the review): wording occasionally stiff; verse context for some proper names (פְּדָיָהוּ, פִּלְטִי, פֶּלֶט, פַּלְטִיאֵל, פְּלַטְיָהוּ, פְּלָאיָה, Haman's sons, פּוֹטִי פֶרַע, פִּינְחָס, פַּרְעֹה נְכֹה) was added from memory beyond the worksheet and should get editorial attention. `editoriallyApproved: false` for all 366.
