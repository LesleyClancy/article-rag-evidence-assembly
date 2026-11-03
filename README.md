# Numerical records and code for evidence assembly under context budgets

## Status and associated study

Release package, version 2. No DOI is assigned in this package. Code is offered under MIT and author-owned numerical records under CC BY 4.0; see `LICENSE` and `DATA_LICENSE.md`.

Associated manuscript: *Beyond Passage Retrieval: Traceable Evidence Assembly for Retrieval-Augmented Generation over Industrial Manuals under Context Budgets*.

The package contains de-identified numerical records and author-owned code supporting selected aggregate computations. It contains no manual body text or full generated answers. Original records remain in a separate local archive. All outcomes within the included cohorts are retained, including adverse outcomes and final score corrections.

## Quick start

Use Python 3.10 or later; no third-party packages, network access or credentials are required for these checks.

```text
python recompute.py
python verify_package.py
```

`recompute.py` checks recorded scores and identifier-based evidence delivery and prints summaries. `verify_package.py` verifies file hashes, compares the recomputed summary with the included reference, and runs 62 synthetic core-code checks. These tests do not re-evaluate human semantic judgments.

## Files

- `data/ratings.json`: 293 logical rating positions, including response reuse; these are not 293 independent samples.
- `data/v20_delivery.json`: 675 original-question and cross-page follow-up positions across V20 methods and budgets.
- `data/listed_packages.json`: necessary-fact and alternative-source identifier mappings, including the documented incomplete Q04 annotation.
- `data/original24_pair_identity.json`: 24 original V20 pairs and identical-request flags.
- `data/answer_identity_and_usage.json`: 78 pilot, diagnostic and V90 response identities, selected/cited unit IDs and provider token usage.
- `CASE_INDEX.json`: lookup locations for selected illustrative cases; no source or answer excerpts are included.
- `DATA_DICTIONARY.md`: field meanings, units and missing-value conventions.
- `AUDIT_NOTES.md`: necessary interpretation notes, score revisions and endpoint distinctions.
- `code/`: core V20 assembly implementations and provenance hashes. Not a full end-to-end RAG distribution.
- `recompute.py`, `recomputed_summary.json`: calculation script and reference output.
- `checks.json`: results of the 62 synthetic checks.
- `manifest.json`: file sizes, SHA-256 hashes, source version and release status.

## Manuscript coverage

| Evidence | Included records | Limits |
| --- | --- | --- |
| Table 2 | 90 ACS580/ATV320 rating positions | Historical core labels are not recoded as completion |
| Table 3 | 48 original V20 rating positions and 24 pair identities | Earlier page-local structure is not later B2 grouping |
| Tables 4 and 7 | Original V20 delivery grid | Listed-unit metric, not semantic relevance |
| Table 5 | 28 rating positions across three rounds | Selected cohorts remain separate |
| Table 6 | 36 pilot ratings and recorded API usage | B1 supported completion 5/6 then 6/6; B1A/B2 6/6 in each round |
| Table 8 | 18 diagnostic ratings | Final support 2 on 14/18; supported completion 12/18 |
| Table 9 | 24 V90 ratings | One output per condition; all six questions same-page sufficient |
| Supplementary Table S1 | 49 logical ATV320 follow-up positions | Some physical responses reused; separate 18-question offline replay excluded |
| Supplementary Tables S2–S3 | CF delivery and original-question missing-ID lists | Distinct endpoints, not pooled |

Table mappings refer to the associated manuscript and its supplementary information. The package does not reproduce retrieval, reconstruct full-text inputs, regenerate model answers, independently validate semantic ratings or reproduce every statistic. V90's complete 48-position offline trace is not included. See the data dictionary and interpretation notes before combining cohorts.

## Sources and identifiers

Source-unit identifiers retain the document/revision label, physical PDF page and local unit number where present. Hashes identify retained requests and outputs without disclosing their text. They are integrity checks, not public access links or independent evidence that a score is correct. Full input reconstruction requires separately obtained matching manuals and processed source data.

R_ACS and R_OTHER denote different designated raters with non-overlapping device assignments. There are no paired independent ratings. Personal identities and contact details are excluded from this package; repository-level creator metadata must be completed separately before publication.

## Release scope

This package supports selected numerical recomputation, not complete independent semantic verification. Excluding full answers and source text is the chosen release scope, not an assertion that all such material is confidential or legally unshareable. Both positive and negative cases follow the same exclusion rule. No public DOI is claimed.

## Recreate the figures

`make_figures.py` draws the four manuscript figures from `data/figure_data.json`. The plotting file is adapted from the original figure script: local paths and the external panel-alignment helper were removed; drawing content and source values are retained. `verify_figure_data.py` checks its V20 delivery and paired counts and the 24 V90 rows against this package. This does not independently verify semantic ratings.

The pinned plotting dependencies require Python 3.11 or later.

```text
python -m pip install -r requirements-figures.txt
python verify_figure_data.py
python make_figures.py
```

Outputs appear in `generated_figures/`, ignored by Git. The original plots used Matplotlib 3.10.6 and NumPy 2.3.5; font availability and platform can change layout or bytes. The independent layout-check helper and original manual/output text are not distributed.
