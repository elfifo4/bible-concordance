# App export: the concordance inside "הראשון בחידון"

The full dataset (`data/alphabet/*.json`, about 153 MB) keeps source and audit fields on every
occurrence. The app needs none of them. `export-app` writes two small files that the app
(`BibleContestMultiPlatformApp`) ships as assets and reads offline on every target: Android,
iOS, desktop and web (JS).

```bash
python3 scripts/concordance.py fetch-sources && python3 scripts/concordance.py import   # once
python3 scripts/concordance.py check-app-text     # map MorphHB onto the app's text, report
python3 scripts/concordance.py export-app         # -> build/app/entries.json, occurrences.bin
```

Both commands read the app's Bible text from
`~/AndroidStudioProjects/BibleContestMultiPlatformApp/shared/src/commonMain/moko-resources/assets/allChapters`
by default (`--app-text DIR` to override). The report goes to `build/reports/app-alignment.json`.

Sizes on 2026-11-25 (9,241 entries, 299,536 occurrences):

| File | Size | gzip |
|---|---|---|
| `entries.json` | 1.39 MB | 0.38 MB |
| `occurrences.bin` | 0.75 MB | 0.61 MB |

## Why the app's coordinates, not MorphHB's

The app shows its own Bible text, not MorphHB's. The two differ in places:

| What | Count (written tokens) | Example |
|---|---|---|
| Same word, same verse and position | 304,553 | |
| Different verse numbering (the Decalogue's ta'am elyon, chapter boundaries) | 2,307 placed elsewhere | Exod 20, Deut 5, Num 25:19 → 26:1, 1 Sam 23:29 → 24:1, Jer 30:25 → 31:1 |
| Spelling variants (plene/defective, הִוא/הִיא) | 815 | הַטְּהוֹרָה / הַטְּהֹרָה |
| Two MorphHB words written as one word in the app | 104 | פְּדָה צוּר → פְּדָהצוּר, רַב שָׁקֵה → רַבְשָׁקֵה |
| Not in the app's text, or split differently | 35 | Josh 21:36–37 (missing from the app), פַּתְבַּג → פת בג |

So the exporter does not trust MorphHB's `tokenPosition` for the app. `align()` lines up every
book of both texts on consonants (difflib) and stores each occurrence at the word the app
actually shows. 99.989% of the words are placed. The 35 that are not placed stay in their
entry's `unplaced` list, so occurrence counts remain honest.

## How the app must split a verse into words

`position` is the 1-based index of a word in the app's verse, split exactly as
`parse_app_chapter()` in `scripts/app_export.py` does it. The app's Kotlin must do the same:

1. Drop the chapter file's first line (the header).
2. Drop `{…}` markers (`{פ}`, `{ס}`, `{1}`, `{ל}` …) and the paseq `׀`.
3. Drop every qere in parentheses `(…)`. The bare ketiv before it is the word.
4. Split on whitespace and on maqaf (`־`, U+05BE).
5. A token starts a new verse only if it is the unpointed Hebrew numeral of the next verse and
   it opens the chapter or follows a token ending in sof pasuq `׃`. This stops a short
   unpointed ketiv from being read as a verse number.
6. Strip `׃` from the word, and drop tokens that have no Hebrew letter.

If the app's chapter files change, rerun `check-app-text` and `export-app`, and ship both
together.

## File format (`bible-concordance-app/1`)

### `entries.json`

```json
{
  "format": "bible-concordance-app/1",
  "meta": {"status": "…", "editoriallyApproved": false, "sourceRevisions": {…},
           "entryCount": 9241, "occurrenceCount": 299536, "coordinates": "…"},
  "books": [["Gen", "בראשית", "bereshit"], …],
  "definitionStatuses": ["source-checked-pending-editorial-review"],
  "fields": ["lexiconId", "strong", "letter", "headword", "definitionHe",
             "definitionStatus", "occurrenceCount", "unplaced"],
  "entries": [["dew", "2061", "ז", "זְאֵב", "בעל חיים טורף.", 0, 7, []], …]
}
```

- `books[i]` is book number `i + 1`: the number in the app's file names (`_1_bereshit` …
  `_39_divrei_hayamim_b`).
- `definitionStatus` is an index into `definitionStatuses`.
- `occurrenceCount` counts every occurrence. Usually it equals the number of locations in
  `occurrences.bin`. It is higher when some occurrences are `unplaced` (MorphHB refs such as
  `"Josh.21.36#4"`), or when two tokens of one entry are one word in the app (40 cases).
- **`meta.editoriallyApproved` is `false`**: every Hebrew definition is still a draft. The app
  must label definitions as drafts until it is `true`.

### `occurrences.bin`

```
"BCO1"                                     4 bytes
for each entry, in entries.json order:
  varint n                                 number of locations
  n varints                                ascending locations, delta-coded (first absolute)
```

- varint = unsigned LEB128 (7 bits per byte, low bits first, high bit = "more").
- location = `book << 24 | chapter << 16 | verse << 8 | position` (each field fits in 8 bits;
  the longest verse has 43 words).

The reference decoder is `read_occurrences()` in `scripts/app_export.py`. A Kotlin port is
about 20 lines. The app builds the reverse index (location → entry, for "tap a word in the
reader") in memory at load time: 299k ints, about 1.2 MB.

## Not exported (yet)

- **Word forms.** The app reads the form from its own text at the stored position, so the UI
  shows exactly the word in front of the reader.
- **Morphology, roots, senses.** Add them to the format (and bump `format`) when the UI needs
  them.
