# Claude Code — Bible Concordance project onboarding

> **Read this document first.** It captures the project's goals, data provenance, past work, decisions, and a read-only assessment assignment. Verify all historical details against the current repository before treating them as facts.


> **Update 2026-11-25.** The per-letter builders (`scripts/build-*-dictionary.cjs`), the `data/*-hebrew-drafts.txt` files and `data/kaf-audit/` described below were replaced by the general CLI `scripts/concordance.py` and `data/drafts/<letter>.txt`, and have been deleted. All 22 letters are regenerated, glossed and audited; see `docs/STATUS.md`, `docs/DATA_MODEL.md` (tokenPosition decision) and the per-letter `docs/*_AUDIT.md`. The historical sections below are kept as context.

## Your immediate assignment

Become familiar with the repository and prepare to complete the remaining Hebrew alphabet letters in future sessions. **For this first assignment, investigate only:** do not edit source/data files, create commits or PRs, merge branches, or re-enable GitHub Actions. You may run genuinely read-only local tests. Write your assessment in your response; prepare the contents of `PROJECT_ASSESSMENT.md` for approval rather than committing or creating it without permission.

Repository: https://github.com/elfifo4/bible-concordance
Default branch: `main`.

## Product vision

Build a trustworthy Hebrew Bible concordance spanning all 22 Hebrew letters. Each lexeme should have its distinct Strong identifier, Hebrew headword, readable Hebrew definition, source provenance, and a complete list of biblical occurrences. The website should show full verses, highlight the attested word/phrase, link to Sefaria, and distinguish homographs and different lexical senses. Source correctness matters more than the appearance of completeness.

## Source-of-truth datasets

1. **MorphHB** (`openscriptures/morphhb`) supplies token-level attestation: `tokenId`, `verseId`, `tokenPosition`, `form`, `lemmaRaw`, `morphRaw`, and Ketiv/Qere considerations. Pinned revision used in existing work: `db6c5c9b46b8f39346f10915ddb1a70dcd429901`.
2. **Open Scriptures HebrewLexicon** supplies Strong and Brown–Driver–Briggs (BDB), via `HebrewStrong.xml`, `LexicalIndex.xml`, and `BrownDriverBriggs.xml`. Pinned revision: `21c9add13bc727d3a951361778e97e3ff7afd1ce`.
3. **Sefaria** supplies full verse text for display. MorphHB and Sefaria may tokenize differently: never assume their word indices correspond exactly. Ambiguous highlights should not be guessed.

Respect the provenance, license and pinned revisions. If changing source revisions, explain the migration and re-audit the data.

## Repository orientation

- `data/alphabet/`: per-letter JSON datasets, including occurrences and metadata.
- `docs/index.html`: existing concordance frontend, verse rendering and highlighting.
- `docs/*AUDIT.md`: source and letter-specific audit reports.
- `data/*-hebrew-drafts.txt`: Hebrew gloss drafts where available.
- `scripts/`: importers, builders, lexicon enrichment and audit utilities.
- `tests/`: local unit/integration and JS tests.
- `.github/workflows/`: GitHub workflows; review them but do not change or re-enable automatic validation.
- Check README, git history, open PRs, and actual file contents rather than assuming this list is exhaustive.

## Desired lifecycle for each letter

1. **Assemble lexemes and occurrences.** Preserve distinct Strong numbers even for identically spelled headwords; record `tokenId`, `verseId`, `form`, `lemmaRaw`, `morphRaw`, and `tokenPosition`. Verify entry and occurrence totals.
2. **Draft Hebrew definitions.** Write clear, concise, biblically and linguistically defensible glosses. Distinguish common nouns, verbs, proper names, place names, peoples, homographs, and uncertain readings. Mark genuine uncertainty; never invent definitions.
3. **Cross-check lexicons.** Match Strong and BDB through the pinned lexical index; preserve English source excerpts, entry identifiers, source links, revisions, and any exceptional mappings. Do not claim a direct BDB match where none exists.
4. **Audit MorphHB tokens.** Validate every occurrence's immutable token ID, verse, form, lemma, morphology and position against source XML, including note/Qere and other tricky indexing behavior. A matching occurrence count alone is insufficient.
5. **Validate output and frontend.** Check JSON integrity, counts, lexical completeness, source flags, display, word/phrase highlighting, Hebrew diacritics, prefixes, homographs, and Ketiv/Qere cases. Preserve existing functionality.
6. **Editorial review.** Distinguish a Hebrew gloss being *written*, *source-cross-checked*, and *editorially approved*. These are separate states. Never set `editoriallyApproved: true` without the agreed editorial process.

Aim for a reusable, resumable per-letter workflow with consistent reports, not a growing collection of copy-pasted scripts.

## Historical work and known state (verify current data)

| Letter | Lexemes | Known historical state |
|---|---:|---|
| ו | 10 | Source audits, including 31 occurrences; two token-position fixes |
| ט | 95 | Source audits, including 990 occurrences; 27 token-position fixes |
| ל | 145 | Dictionary generation and verification work; inspect current status |
| ה | 156 | 156 Hebrew glosses, Strong/BDB source cross-check and 9,669 MorphHB occurrences; **no editorial approval** |
| ז | 169 | 169 Hebrew draft glosses integrated, 4,505 occurrences; source-audit builder created but **not successfully run/verified** |

Other letters may have baseline generated data; do not infer they are complete.

### Letter ה

Inspect `data/alphabet/ה.json`, `data/he-hebrew-drafts.txt`, `scripts/build-he-dictionary.cjs`, `docs/HE_AUDIT.md`. Historically 156/156 definitions were drafted and checked against pinned Strong/BDB, with 9,669 occurrence checks and 218 token-position corrections. Editorial approval remained pending. A known lexicon exception: Strong H2007 is not directly indexed; an H2004-related BDB excerpt was used, explicitly documented as indirect.

### Letter ז

Inspect `data/alphabet/ז.json`, `data/zayin-hebrew-drafts.txt`, `scripts/build-zayin-dictionary.cjs`, `docs/ZAYIN_AUDIT.md`. The 169 Hebrew definitions are **drafts**, not verified glosses. The source-audit script was added but has not been run successfully. The JSON verification flags should remain false until checks actually pass. Review the script carefully before running: it was adapted from the ה builder and may encounter lexicon exceptions or token indexing differences.

### PR history

- [PR #13](https://github.com/elfifo4/bible-concordance/pull/13) concerned full Sefaria verses and occurrence highlighting. It was closed because a more advanced implementation already existed on `main`; do not resurrect the older code.
- [PR #37](https://github.com/elfifo4/bible-concordance/pull/37) audited ו/ט source tokens. Its useful changes were integrated manually into `main` without merging an automatic CI hook, and the PR was closed. Historical source audit results: 31/31 for ו and 990/990 for ט.
- Related fixes in `main` addressed the biblical place-name Lo-debar phrase highlighting, including attached prefixes, and preservation of MorphHB token positions when skipping words embedded in notes. Review the relevant tests.

## CI and deployment decision — important

**Do not turn automatic GitHub CI back on.** Automatic test/build runs generated repeated failure emails. We decided Claude Code should run validation **locally on the user's MacBook**. Automatic push/PR triggers were removed from these five workflows, retaining manual dispatch:

- `generate-alphabet.yml`
- `he-build.yml`
- `lamed-build.yml`
- `tests.yml`
- `vav-audit.yml`

The GitHub Pages publishing workflow (`pages.yml`) was deliberately kept active. Do not disable site publishing as a side effect. Do not add new automatic Actions triggers without explicit authorization.

## Token efficiency and automation policy — mandatory

**Script-first, LLM-last.** Treat model tokens, context-window space and repeated tool calls as scarce resources. Use Claude primarily to design reusable code, investigate exceptions and make semantic judgments; use deterministic scripts for bulk processing.

1. **Never process large lists record by record in the conversation.** For thousands of occurrences, write/run a local program that reads the JSON/XML, validates everything, and emits only a compact summary and a machine-readable exception report.
2. **Batch I/O and parsing.** Download each pinned source once per revision, cache it locally, parse it once, and reuse indexes/maps across all letters. Do not request the same file repeatedly or fetch one verse/entry at a time when bulk parsing is possible.
3. **Inspect selectively.** Start with file sizes, schemas, counts, sampled entries, tests and `git diff --stat`. Use targeted searches or small excerpts rather than printing multi-megabyte JSON/XML or entire logs into model context.
4. **Automate repeatable tasks.** Counting entries/occurrences, checking missing definitions, joining Strong/BDB, comparing MorphHB token fields, validating JSON, detecting duplicate IDs, producing reports and testing regressions must be scripted.
5. **Use the LLM only where it adds value.** Linguistic interpretation, ambiguous glosses, genuinely exceptional source mappings, architecture choices and review of flagged outliers. Do not ask the model to rewrite hundreds of mechanically generated records.
6. **Prefer one general CLI** (e.g. `--letter ז --audit --report`) over one bespoke script per letter; make it resumable, idempotent and able to operate on all 22 letters.
7. **Keep output compact.** Report totals, pass/fail counts, file paths and at most a few representative exceptions. Save full logs and per-token differences to local files; open only relevant slices for diagnosis.
8. **Avoid unnecessary LLM subagents and redundant investigations.** Delegate to parallel agents only when the expected benefit clearly exceeds the token and coordination cost.
9. **Never confuse token efficiency with skipping verification.** The script must validate **all** records even when Claude reads only aggregate results and anomalies.
10. **Before any large task, estimate scale and choose the cheapest reliable method.** If a simple Python/Node program can do it exactly, do not spend model tokens doing it manually.

For Hebrew definitions, prefer a source-derived structured extraction and deterministic coverage checks, then use focused LLM review for uncertain meanings and edge cases. Mark unreviewed definitions as drafts, never as editorially approved.

In the initial assessment, explicitly identify the top opportunities to reduce LLM token consumption and estimate which existing per-letter operations can be consolidated into one script. Do not implement changes during this read-only phase.

## Safety and collaboration rules

- First inspect `git status`, current branch, existing work, relevant PRs and documentation. Do not overwrite uncommitted changes.
- Never silently change pinned source revisions or remove verified records.
- Do not invent data, silently collapse Strong entries, or mark drafts as approved.
- Record exceptional lexicon mappings and uncertain interpretations.
- Prefer local reproducible checks, with clear pass/fail counts and exact commands.
- Do not merge, push, open PRs, or modify CI without permission.
- Treat historical descriptions here as leads, not proof; current source files and executed tests are authoritative.

## Read-only assessment task

1. Read the repository's code, data, documentation, tests, workflows and relevant history.
2. Produce a **22-letter status table**: lexeme count, occurrence count, Hebrew definitions present, source-check status, occurrence-audit status, editorial approval status, blockers and next action. Compute these from actual data and mark unknowns as unknown.
3. Review the build pipeline: per-letter scripts versus a reusable general builder; identify duplicated logic, inconsistent schema/flags, source-mapping issues and data risks.
4. Run safe, read-only local tests where possible. Before running a generator that writes files or downloads large corpora, explain its side effects and seek permission. Inspect the Zayin builder in particular.
5. Propose a repeatable command/workflow to complete any given letter end-to-end, with idempotency, checkpoints, provenance, tests, exceptions and reporting.
6. Recommend an order for completing the remaining letters and a concrete editorial-review process.

### Expected report

Prepare a Hebrew assessment titled `PROJECT_ASSESSMENT.md` covering architecture, 22-letter status, *actual* tests executed and their outcomes, bugs/risks, proposed generic workflow, completion roadmap, and decisions requiring the owner's approval. Distinguish verified findings from assumptions and recommendations. **Do not write or commit this file yet without approval**; present the draft report in your response.

Finish with a short Hebrew executive summary and await instructions before implementation.
