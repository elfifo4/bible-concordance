# MorphHB corpus audit and reading variants

## Status
The PR now includes a full-corpus integration job that clones upstream MorphHB, records the checked-out commit SHA and runs the importer across the WLC XML directory. **A successful run has not yet been verified.** The integration test currently checks that 39 book XML files are present, each has verses, and the extracted JSONL exceeds 100,000 records; this is a smoke test, **not an independent verse-by-verse completeness proof**.

## Ketiv / Qere
MorphHB uses `<w type="x-ketiv">` for written readings and `<note type="variant"><rdg type="x-qere"><w>...</w></rdg></note>` for alternative readings. Qere may have a different number of words than ketiv, or occur without a directly paired written token.

The importer now labels written ketiv records and **does not count Qere note words as additional written-token occurrences**. It does **not yet persist Qere alternatives**, pair their tokens to ketiv spans, or classify their lexical senses. Those are separate requirements before a concordance can claim to cover both reading traditions. In particular, never silently discard Qere when building a final released concordance.

## Remaining release gates
1. Run CI integration against real MorphHB and fix failures.
2. Compare per-book verse IDs and token counts with an independently generated reference baseline, not merely a nonzero count.
3. Persist Qere variant records, including unpaired variants and one-to-many alignments.
4. Pin the exact upstream revision in the workflow instead of following the floating default branch.
5. Check missing IDs, multiple words per written token, and source-specific segmentation.

## Letter ו pilot
Start lemma extraction only after real-source import succeeds. Do not select all surface forms beginning with ו: many are words with the conjunction prefix and belong to another headword.
