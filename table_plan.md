# Table and Figure Plan

This file reorganizes the paper presentation plan around our actual experimental goals and the main concerns raised by prior feedback:

- make the benchmark contribution look like a real benchmark paper, not just a dataset note
- separate the main capability claims from diagnostic / ablation analysis
- make `order_sensitivity` a first-class result rather than a side metric
- avoid overcrowded mega-tables
- use figures where trend or variance matters more than exact numbers

The guiding principle is:

1. Main results should answer: "Can current LLMs execute deterministic data-refinement recipes?"
2. Diagnostic analysis should answer: "Where do they fail, and why?"
3. Ablations should answer: "How much do domain, prompt style, and K-style prompting matter?"


## 1. Core Paper Story

The paper should be organized around three empirical claims:

1. Atomic execution is much easier than compositional execution.
2. Order-sensitive recipe execution is substantially harder and exposes a distinct failure mode.
3. Prompt diversity helps, but does not eliminate the compositional and order-sensitive gap.

Everything in the tables/figures should support one of these three claims.


## 2. Main Results Section

We should split the current single large main-results table into two main tables.

### Table 1. Atomic + Compositional Main Results

Purpose:
- establish the core gap between atomic operator execution and compositional recipe execution
- keep the first main table compact and easy to read

Recommended columns:
- `Atomic RS`
- `Atomic RS@K`
- `Atomic RG`
- `Compositional RS`
- `Compositional RS@K`
- `Compositional RG`

Rows:
- all main compared models
- group into closed-source and open-source blocks

Why this table exists:
- it gives the cleanest first takeaway: atomic competence does not transfer to multi-step recipe execution

Notes:
- if width becomes tight, `RG` can be moved to appendix and main table can keep only `RS` / `RS@K`
- if we keep `RG`, we should explicitly note that it is a secondary soft-progress metric


### Table 2. Order-Sensitive Main Results

Purpose:
- make order-sensitive evaluation a primary result rather than a small appendage
- show both overall performance and order-slot breakdown

Recommended columns:
- `RS`
- `RS@K`
- `RG`
- `OCS`
- `OCS@K`
- `RS_pre`
- `RS_mid`
- `RS_post`

Optional extended columns if space allows:
- `RS_pre@K`
- `RS_mid@K`
- `RS_post@K`

Rows:
- same model list as Table 1

Why this table exists:
- `OCS` alone is too black-boxed
- adding `pre/mid/post` shows whether models specifically fail when filters appear earlier in the recipe

Important interpretation:
- `KEEP/DROP` should not be in the main order table, because that will make it too wide
- `KEEP/DROP` is better reserved for a diagnostic follow-up table or appendix


### Table 3. Prompting Strategy Comparison

Purpose:
- answer the likely reviewer question: "Is the benchmark just sensitive to prompt engineering?"

Recommended scope:
- 2 representative models only
  - one strong closed-source model
  - one strong open-source model

Rows:
- `Direct`
- `Few-Shot`
- `Plan-First`
- `State-Aware`

Recommended columns:
- keep the same track grouping style as the current draft
- use:
  - Atomic: `RS`, `RS@K`, `RG`
  - Compositional: `RS`, `RS@K`, `RG`
  - Order: `RS`, `RS@K`, `RG`, `OCS`, `OCS@K`

Why this table exists:
- to show that stronger prompting can help, but the benchmark still reveals persistent capability gaps


## 3. Figures We Should Prefer Over Tables

Some comparisons are better shown as figures because they emphasize trend, spread, or interaction rather than one-shot exact values.

### Figure 1. K-Scaling Curves (`@k` curves)

Purpose:
- show how performance changes as the number of prompt styles increases
- answer: "How much benefit do we get from prompt diversity?"

Recommended design:
- x-axis: `k = 1, 2, 3, 5, all`
- y-axis:
  - Atomic / Compositional: `RS@k`
  - Order: `OCS@k` and optionally `RS@k`
- 3 panels:
  - Atomic
  - Compositional
  - Order
- each line = one representative model

Why figure, not table:
- `@k` is fundamentally a trend
- slope matters more than the exact number in one cell

Companion note:
- if needed, we can pair this figure with a tiny support table reporting only `k=1`, `k=3`, `k=5`, `all`


### Figure 2. Style-Level Heatmap

Purpose:
- show whether some prompt styles are systematically easier/harder than others
- answer: "Is performance sensitive to prompt wording?"

Recommended design:
- 3 separate heatmaps or 3 horizontal panels:
  - Atomic
  - Compositional
  - Order
- rows: representative models
- columns: 11 prompt styles
- color value: single-style `RS`

Why this matters:
- it explains why `RS@K` improves
- if style performance is flat, then K-scaling is unsurprising
- if style gaps are large, we can claim prompt sensitivity is substantial

Important:
- this should use single-style metrics, not `@k`


### Figure 3. Recipe Length Breakdown

Purpose:
- directly support the main claim that performance drops as compositional depth increases
- answer: "Is the main difficulty really composition depth?"

Recommended design:
- x-axis: recipe length
  - `1`, `2`, `3`, `4`, `5+`
- y-axis: `RS`
- panels:
  - at minimum `Compositional`
  - optionally `Order`
- lines: representative models

Why this should be in the main paper:
- this is not a minor ablation
- it is one of the cleanest explanations for the atomic-to-compositional gap
- it helps turn the paper from "benchmark with low scores" into "benchmark revealing a scaling failure mode"

Important interpretation:
- this analysis should be framed as a **recipe-complexity** analysis
- it should not be mixed with input-length effects
- the main question here is whether failure grows with the number of executed steps


### Figure 4. Domain Breakdown Bar Plot

Purpose:
- show whether benchmark difficulty varies by domain
- answer: "Is this only a web-cleaning benchmark, or are there genuine cross-domain differences?"

Recommended design:
- 3 panels by track
- x-axis: `web`, `arxiv`, `knowledge_base`, `pii`
- y-axis:
  - Atomic / Compositional: `RS`
  - Order: `OCS` or `RS`
- bars: 2 to 4 representative models

Alternative:
- if we need exact values in the main paper, use a small table instead


### Figure 5. Seed Variance Plot

Purpose:
- show whether `@k` metrics are stable under different style-sampling seeds
- answer: "Are reported `RS@K` / `OCS@K` reliable?"

Recommended design:
- x-axis: `k`
- y-axis: `RS@k` or `OCS@k`
- each point averaged across multiple seeds
- error bars / band = variance across seeds

Scope:
- only for 1 or 2 representative models

Why figure:
- variance is visually easier to interpret than in a big table


## 4. Diagnostic Analysis Tables

These tables should come after the main results, not before.

### Table 4. Order Keep/Drop Breakdown

Purpose:
- explain where order difficulty comes from
- answer: "Are failures concentrated in drop-triggered early-stop cases?"

Recommended columns:
- `RS_keep_pre`
- `RS_drop_pre`
- `RS_keep_mid`
- `RS_drop_mid`
- `RS_keep_post`
- `RS_drop_post`

Simpler fallback:
- just two blocks:
  - `KEEP`: `RS_pre`, `RS_mid`, `RS_post`
  - `DROP`: `RS_pre`, `RS_mid`, `RS_post`

Why this table exists:
- our `StopAwareRG` discussion strongly suggests that `DROP-pre` and `DROP-mid` are the most diagnostic cases

Recommendation:
- this can be main text if space allows, but appendix is acceptable


### Table 5. Style Variance Summary

Purpose:
- quantify prompt-style sensitivity more compactly than a heatmap

Recommended columns:
- `Best Style RS`
- `Worst Style RS`
- `Gap`
- `Std Across Styles`

Rows:
- representative models, possibly per track

Why this table exists:
- gives one sentence-ready result:
  - "The best-to-worst style gap reaches X points on compositional recipes."

This can go in the appendix if the heatmap already appears in the main paper.


### Table 6. StopAwareRG vs Old RG

Purpose:
- justify the metric update
- show whether the new metric meaningfully changes conclusions on difficult `DROP` cases

Recommended columns:
- `Atomic RG_old`
- `Atomic RG_stopaware`
- `Comp RG_old`
- `Comp RG_stopaware`
- `Order RG_old`
- `Order RG_stopaware`

Simpler version:
- only compare `Compositional` and `Order`

Recommendation:
- this is probably appendix unless a reviewer is clearly likely to challenge the metric


## 5. Appendix / Extra Material

These are useful if we have time, but they are not the first thing to optimize.

### Figure 6 / Table 5. Input Length Breakdown

Purpose:
- separately analyze whether long raw inputs hurt recipe execution even when recipe structure is held fixed
- answer: "Is the model failing because the recipe is hard, or because the source text is long?"

Recommended design:
- prefer a small main-text figure if space allows
- otherwise use a compact table
- x-axis or columns:
  - `short`
  - `medium`
  - `long`
- y-axis or cell values:
  - `RS`
  - optionally `RS@K`

Recommended framing:
- keep this analysis explicitly separate from recipe-length analysis
- describe it as an **input-scale** analysis rather than a compositionality analysis
- if possible, report it for the compositional track first, and optionally for order

Why this matters:
- reviewers may otherwise argue that compositional errors are actually just long-context failures
- a separate input-length analysis lets us show whether recipe complexity and input length are distinct sources of difficulty


### Appendix Table A1. Expanded Input Length Breakdown

Purpose:
- provide the full numeric counterpart to the main input-length analysis

Columns:
- `short`
- `medium`
- `long`

Recommendation:
- keep this as appendix if the main paper already contains a compact input-length figure/table
- expand by track and possibly by representative model


### Appendix Table A2. Extra Prompting Baselines

Purpose:
- preserve full prompting-baseline results even if the main paper only shows a subset of models

Recommended contents:
- 4 prompting modes:
  - `Direct`
  - `Few-Shot`
  - `Plan-First`
  - `State-Aware`
- for all models we actually run

Role in paper:
- the main paper should include a compact prompting-baseline table for representative models
- the appendix can hold the full expanded version if we run more models later


### Appendix Figure A1. Error Taxonomy

Purpose:
- categorize failures into:
  - wrong keep/drop
  - correct operator set, wrong order
  - partial application
  - over-cleaning
  - under-cleaning
  - output format violation

This is valuable, but we should not prioritize it above the main result and main analysis figures.


## 6. Recommended Final Presentation Structure

If we want a clean paper narrative, the presentation order should be:

1. **Table 1**: Atomic + Compositional Main Results
2. **Table 2**: Order Main Results
3. **Table 3**: Prompting Strategy Comparison
4. **Figure 1**: K-Scaling Curves
5. **Figure 2**: Style-Level Heatmap
6. **Figure 3**: Recipe Length Breakdown
7. **Figure 4**: Domain Breakdown
8. **Figure 5 / Table 5**: Input Length Breakdown
9. **Table 4**: Order Keep/Drop Breakdown
10. **Appendix**: StopAwareRG comparison, expanded input-length tables, error taxonomy


## 7. Priority Tiers

### P0: Must Have

- Table 1: Atomic + Compositional Main Results
- Table 2: Order Main Results
- Table 3: Prompting Strategy Comparison
- Figure 1: K-Scaling Curves
- Figure 2: Style-Level Heatmap
- Figure 3: Recipe Length Breakdown

These six are enough to support the central benchmark story.


### P1: Strongly Recommended

- Figure 4: Domain Breakdown
- Figure 5 / Table 5: Input Length Breakdown
- Table 4: Order Keep/Drop Breakdown

These make the analysis substantially more convincing.


### P2: Nice to Have / Appendix

- Table 5: Style Variance Summary
- Table 6: StopAwareRG vs Old RG
- expanded input-length breakdown
- error taxonomy


## 8. What We Should Not Do

- Do not keep one giant everything-table combining atomic, compositional, order, prompting, and slot breakdowns.
- Do not put `KEEP/DROP` and `pre/mid/post` and `@K` all into one order table unless we are forced by page limits.
- Do not use tables for K-scaling trends if a figure is available.
- Do not hide order-specific analysis entirely in appendix; order is one of the benchmark's core claims.
- Do not bury recipe-length effects in appendix; composition depth is one of the benchmark's main scientific messages.
- Do not merge recipe-length and input-length into one overloaded ablation; they should be discussed as different axes of difficulty.


## 9. Immediate Next Step

The immediate deliverable should be:

1. lock the schemas for:
   - Table 1
   - Table 2
   - Table 3
2. decide the representative models for:
    - prompting comparison
    - style heatmap
    - K-scaling figure
    - recipe-length figure
    - input-length figure/table
3. ensure evaluation exports can produce:
    - overall `RS`, `RS@K`, `RG`
    - `OCS`, `OCS@K`
    - `RS_pre`, `RS_mid`, `RS_post`
    - per-style single-style `RS`
    - per-length `RS`
    - per-input-bucket `RS`
    - by-domain summaries
    - by-seed `@k` results

Once those are fixed, the rest of the plotting and table fill-in becomes mechanical.
