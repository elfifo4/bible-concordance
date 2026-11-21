# Contributing and change workflow

## Mandatory Pull Requests

**Every change to this repository must be submitted through a Pull Request (PR).**

1. Create a feature/fix/docs branch from the current `main`.
2. Commit changes only to that branch; never push directly to `main`.
3. Open a PR targeting `main` and describe scope, data sources, license implications, and validation performed.
4. Wait for the repository owner's explicit approval before merging. Opening a PR does not authorize merging it.
5. After approval, merge through GitHub and delete the feature branch when appropriate.

This applies to all files, including README, licenses, documentation, scripts, generated data, and one-line fixes.

**Enforcement:** This document is a team policy, not a technical lock. Configure a GitHub branch ruleset for `main` requiring a pull request before merging. If GitHub plan/settings allow it, require status checks and prevent bypass, including by administrators.

## Data provenance

Before adding third-party data, document its source revision, license, attribution, transformations, and validation. Do not import data whose redistribution rights are unclear.
