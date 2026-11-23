# Kaf audit

- 273 Hebrew draft glosses integrated into `data/alphabet/כ.json`.
- All 273 Strong IDs match exactly; 11,708 occurrence records and 11,708 unique token IDs retained. The uploaded Git blob was read back and parsed successfully.
- Compact JSON was used to avoid the transport limit; original occurrence data was not modified.
- Strong/BDB pinned-source comparison, MorphHB token verification and editorial review remain pending. No source or editorial approval is claimed.
- Run `node scripts/build-kaf-dictionary.cjs` locally to perform source verification and generate the final data; `--check-only` avoids writing output. Do not enable automatic CI; per project decision, execute locally on the MacBook.
