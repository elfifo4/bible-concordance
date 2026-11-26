# App export: the concordance inside "הראשון בחידון"

The full dataset (`data/alphabet/*.json`, about 153 MB) keeps source and audit fields on every
occurrence. The app needs none of them. `export-app` writes two small files that the app
(`BibleContestMultiPlatformApp`) ships as assets and reads offline on every target: Android,
iOS, desktop and web (JS).

```bash
python3 scripts/concordance.py fetch-sources && python3 scripts/concordance.py import   # once
python3 scripts/concordance.py check-app-text --strict   # map MorphHB onto the app's text, report
python3 scripts/concordance.py export-app                # -> build/app/entries.json, occurrences.bin
```

Both commands read the app's Bible text from
`~/AndroidStudioProjects/BibleContestMultiPlatformApp/shared/src/commonMain/moko-resources/assets/allChapters`
by default (`--app-text DIR` to override). The report goes to `build/reports/app-alignment.json`.

Both commands refuse to run on a wrong text. They fail when:
- the directory does not hold exactly 929 chapter files, or a book number and slug don't match;
- any chapter parses to a verse count that differs from the app's own `verses_per_chapter.csv`;
- (`export-app` only) fewer than 99.98% of MorphHB's words map onto the app text.

`check-app-text --strict` exits 1 in the same cases, so CI can run it.

Sizes on 2026-11-26 (9,241 entries, 299,536 occurrences):

| File | Size | gzip |
|---|---|---|
| `entries.json` | 1.38 MB | 0.38 MB |
| `occurrences.bin` | 0.75 MB | 0.61 MB |

## Why the app's coordinates, not MorphHB's

The app shows its own Bible text, not MorphHB's. Each of MorphHB's 305,507 written words falls
into exactly one of these kinds:

| Kind | Words | Example |
|---|---|---|
| Same consonants | 304,553 | |
| Spelling variant, mapped 1:1 | 815 | הַטְּהוֹרָה / הַטְּהֹרָה, הִיא / הִוא |
| Two MorphHB words written as one word in the app | 104 | פְּדָה צוּר → פְּדָהצוּר, רַב שָׁקֵה → רַבְשָׁקֵה |
| Not placed | 35 | Josh 21:35#7–21:37 (20 words the app does not have), פַּתְבַּג → פת בג (Dan 1), 2 Kgs 18:19, Ps 149:7 |

Separately, 2,288 of the placed words sit at a different verse or position in the app. Most come
from different verse numbering (the Decalogue's ta'am elyon in Exod 20 and Deut 5, Num 25:19 →
26:1, 1 Sam 23:29 → 24:1, Jer 30:25 → 31:1, Josh 21). The rest are the shift by one position
after a joined word (Isa 36, Jer 39).

So the exporter does not trust MorphHB's `tokenPosition` for the app. `align()` lines up every
book of both texts on consonants (difflib) and stores each occurrence at the word the app
actually shows. 99.989% of the words are placed. The 35 that are not placed stay in their
entry's `unplaced` list, so counts stay honest.

`check-app-text` lists, under `examples.low-similarity`, the placed words whose consonants differ
a lot from MorphHB's. Read them whenever the app text changes. Today there are 4, all correct:
Ps 68:27 (the app reads אֲדֹנָי where MorphHB reads יְהוָה), and three joins (Job 38:1, Song 8:6,
1 Chr 15:13).

## How the app must split a verse into words

`position` is the 1-based index of a word in the app's verse. The app's Kotlin must split
exactly as `parse_app_chapter()` in `scripts/app_export.py` does:

1. Drop a leading BOM (U+FEFF), then everything up to and including the first `\n`: the header
   line. The files are CRLF.
2. Replace each of these with a single space:
   - every `{…}` marker (`{פ}`, `{ס}`, `{1}`, `{ל}` …);
   - every qere in parentheses `(…)` (the bare ketiv before it is the word);
   - every paseq `׀` (U+05C0);
   - every inverted nun `׆` (U+05C6; Num 10:35–36, Ps 107).
3. Split on runs of exactly these characters: tab U+0009, LF U+000A, CR U+000D, space U+0020,
   **NBSP U+00A0**, maqaf `־` U+05BE.
   - Do not use Kotlin/Java `\s`: on the JVM it does not match NBSP, which is the only separator
     in Deut 32:6 (`הַ` + `לְיְהֹוָה`).
   - ZWJ (U+200D) is not a separator. It stays inside the word.
4. Walk the tokens with `current = 0` (the verse number so far) and `afterSofPasuq = true`:

```
for tok in tokens:
    if afterSofPasuq and tok is an unpointed Hebrew numeral == current + 1:
        current += 1; start verse current; afterSofPasuq = false; continue
    word = tok without "׃"
    if current > 0 and word has a Hebrew letter (א–ת): append word to verse current
    if tok ends with "׃":       afterSofPasuq = true     # a lone "׃" after a qere included
    else if word has a letter:  afterSofPasuq = false    # letterless tokens change nothing
```

An unpointed numeral contains only letters from א to ת and no niqqud or cantillation
(U+0591–U+05C7). Its value is the sum of the letters (טו = 15, טז = 16). The "after sof pasuq"
condition stops a short unpointed ketiv (such as ב) from being read as a verse number.

A port is correct when every chapter parses to the verse count in the app's
`verses_per_chapter.csv`. That is the check `RealAppTextTest` makes here, and the app's own tests
should make the same check. If the app's chapter files change, rerun `check-app-text` and
`export-app`, and ship both files together.

## File format (`bible-concordance-app/1`)

### `entries.json`

```json
{
  "format": "bible-concordance-app/1",
  "meta": {"status": "…", "editoriallyApproved": false, "sourceRevisions": {…},
           "entryCount": 9241, "occurrenceCount": 299536, "coordinates": "…",
           "occurrencesBytes": 749046, "occurrencesSha256": "6c09…"},
  "books": [["Gen", "בראשית", "bereshit"], …],
  "definitionStatuses": ["source-checked-pending-editorial-review"],
  "fields": ["lexiconId", "strong", "letter", "headword", "definitionHe",
             "definitionStatus", "occurrenceCount", "unplaced"],
  "entries": [["dew", "2061", "ז", "זְאֵב", "בעל חיים טורף.", 0, 7, []], …]
}
```

- `books[i]` is book number `i + 1`: the number in the app's file names (`_1_bereshit` …
  `_39_divrei_hayamim_b`).
- `headword` is pointed, without cantillation.
  - 2,019 entries share their headword with another entry (homographs such as אָדָם).
    Distinguish them by the definition, or by `strong`.
  - There is no unpointed form; compute it in the app (keep only the letters א–ת) for search
    and sorting.
- `strong` and `definitionHe` may be `null`.
- `definitionStatus` is an index into `definitionStatuses`.
- **`meta.editoriallyApproved` is `false`**: every Hebrew definition is still a draft. The app
  must label definitions as drafts until it is `true`.
- **Counts and lists:**
  - `occurrenceCount` counts MorphHB occurrences.
  - The number of locations in `occurrences.bin` can be lower, in 31 entries:
    - 35 occurrences are `unplaced`. These are MorphHB refs such as `"Josh.21.36#4"`, in 21
      entries. The app cannot open them in its reader; show them as a note.
    - In 40 cases, two occurrences of one entry are a single word in the app, as with מַלְכִּישׁוּעַ.
  - In the UI, show the number of locations, or explain the difference.

### `occurrences.bin`

```
"BCO1"                                     4 bytes (ASCII)
for each entry, in entries.json order:
  varint n                                 number of locations; 0 is allowed
  n varints                                locations, delta-coded: the first is absolute,
                                           each next one is (location - previous location)
```

- **varint:** unsigned LEB128, 7 bits per byte, low bits first; a set high bit means another
  byte follows. At most 5 bytes. There is no endianness issue.
- **location:** `book << 24 | chapter << 16 | verse << 8 | position`.
  - Each field is 1–255; the longest verse has 43 words.
  - Every value fits a signed 32-bit `Int`.
  - Within an entry, locations are strictly ascending, with no duplicates.
- **No entry count or trailer:** the file is read to its end. A loader must check that:
  - the number of lists equals `entries.size`;
  - the file's length and SHA-256 equal `meta.occurrencesBytes` and `meta.occurrencesSha256`.

  This catches a `.bin` and an `entries.json` that come from different exports.

The reference decoder is `read_occurrences()` in `scripts/app_export.py`. A Kotlin port is
about 20 lines.

**Reverse index** (tap a word in the reader → entry): build it in memory at load time, about 1.2
MB for 299k ints. It must be **location → list of entries**. 11 app words belong to two entries,
where the app writes two words as one (2 Sam 2:30#15, Ps 57:10#5, Ps 108:4#5, Jer 29:23#18 …).

About 2% of the app's words have no entry at all: the parts of the text that no lexicon entry
covers. A tap on such a word must show "no entry", not fail.

## Not exported (yet)

- **Word forms.** The app reads the form from its own text at the stored position, so the UI
  shows exactly the word in front of the reader.
- **`definitionEn`, the row-level `reviewStatus`, and the Strong/BDB excerpts.** Only the Hebrew
  definition and its status are exported.
- **Morphology, roots, senses.** Add them to the format (and bump `format`) when the UI needs
  them.
