# Verse text strategy

> **Update (2026-11-25):** the "הראשון בחידון" app shows its own bundled Bible text, and the
> verified alignment layer described below now exists for it: see [APP_EXPORT.md](APP_EXPORT.md).

## Decision: keep concordance data separate from displayed verse text

The distributable concordance dataset will store lexical entries, senses,
morphology, token-level occurrence references, and verse identifiers.
**Do not duplicate complete verse texts in each occurrence or ship a
`data/verses/` corpus by default.**

## Proposed verse display provider: Sefaria

The app can retrieve Hebrew verse text from Sefaria when a user opens an
occurrence. Keep the verse provider behind an interface so it can be
replaced or supplemented later. Verify Sefaria API availability, text
version, usage policies, attribution, and caching terms before production
integration. This is an architectural proposal, not a completed integration.

## Alignment and correctness

- MorphHB is the morphological source used for word-level indexing.
- Preserve the original source token ID, book/chapter/verse, token position,
  and source text version/revision for each occurrence.
- Sefaria's displayed Hebrew text may differ in spelling, cantillation,
  segmentation, verse numbering, or textual edition.
- Never assume a MorphHB token offset can highlight the corresponding
  Sefaria word without a verified alignment layer.
- If alignment fails, show the verse without highlighting, rather than
  highlighting the wrong word.
- Some offline functionality may require an explicitly licensed,
  versioned local text cache or bundled corpus later.

## Initial proposed layout

```text
data/
  entries/
  occurrences/
  manifest.json
schemas/
scripts/
docs/
  VERSE_PROVIDER.md
```

The ingestion pipeline may use temporary or cached source texts without
committing a duplicate verse corpus to this repository.
