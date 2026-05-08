# Refresh Workflow

This file collects the commands needed to refresh benchmark references, rebuild the `main` subset, and regenerate prompt-track files after the recent pipeline changes.

## 0. Install strict DJ dependencies

These are now required for exact execution of `fix_unicode_mapper` and `token_num_filter`.

```bash
pip install ftfy transformers sentencepiece
```

## 1. Refresh existing `benchmark_full` ground truth in place

This recomputes deterministic references from the existing benchmark rows.

- Recomputes:
  - `reference_status`
  - `reference_text`
  - `reference_trace`
- For `order_sensitivity`, also adds:
  - `reference_text_full_run`
  - `full_run_reference_trace`
- Backfills missing recipe-level fields from `recipe_library` when needed:
  - `operator_sequence`
  - `filter_params_by_name`
  - `filter_name`
  - `recipe_type`
  - `benchmark_track`
  - `order_slot`
  - `order_family_id`

### Refresh in place

```bash
bash scripts/refresh_benchmark_references.sh
```

### Refresh only `main` and `order_sensitivity`

```bash
bash scripts/refresh_benchmark_references.sh \
  --tracks main,order_sensitivity
```

### Refresh into a new directory instead of overwriting

```bash
bash scripts/refresh_benchmark_references.sh \
  --benchmark-root data/benchmark_full \
  --output-root data/benchmark_full_refreshed
```

## 2. Rebuild the engineering `main` subset

Current logic keeps only:

- `clean-only`
- `clean-then-filter`

It no longer keeps `filter-then-clean`.

```bash
bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full/main \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/main
```

If you refreshed into a separate directory, use that instead:

```bash
bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full_refreshed/main \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/main
```

## 3. Rebuild the engineering `order_sensitivity` subset

```bash
bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full/order_sensitivity \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/order_sensitivity
```

If you refreshed into a separate directory, use that instead:

```bash
bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full_refreshed/order_sensitivity \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/order_sensitivity
```

## 4. Attach all prompt styles to the selected benchmark subset

At this stage, the engineering subset in `data/benchmark` is already fixed.
So this step should only attach all distinct prompt styles to the selected rows.
It should not do another round of sample filtering just because some rows have fewer styles.

For that reason:

- use `--benchmark-dir data/benchmark`
- keep `--min-prompt-variants-per-sample 1`

This preserves the selected benchmark rows and stores all available styles for each row.
Later, infer-time or score-time sampling will control `@k`.

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark \
  --prompt-library data/processed/prompt_library/recipe_prompt_library.jsonl \
  --output-dir data/benchmark \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1
```

If you later decide to make prompt availability part of benchmark selection itself, the cleaner conceptual order is:

1. attach or inspect prompt availability on `benchmark_full`
2. select the final engineering subset from that prompt-aware full benchmark
3. attach all styles to the final subset without further filtering

The command above follows the current practical workflow: keep the subset fixed, then attach prompt styles.

## 5. Run inference

## 5.1 Run all available prompt styles for each sample

Example:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

This uses all prompt variants stored in the benchmark row.

Default predictions filename:

- `predictions_direct.jsonl`

## 5.2 Run a deterministic sampled style subset at infer time

This is useful when you do **not** want to pay for full-style inference.
For example, you can first try GPT with a deterministic 3-style subset for one seed.

Example:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

This samples 3 prompt styles per sample deterministically using:

- `recipe_prompt_key`
- `instance_id`
- `PROMPT_VARIANT_SAMPLING_SEED`

Default predictions filename for this run:

- `predictions_direct_k3_seed0.jsonl`

If you change the seed, the output filename changes too, so runs do not overwrite each other:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=1 \
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

Default predictions filename:

- `predictions_direct_k3_seed1.jsonl`

You can also call the shared CLI arguments explicitly:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer \
  --mode direct \
  --prompt-variant-sample-size 3 \
  --prompt-variant-sampling-seed 0
```

## 5.3 Score from a full-style predictions file without re-inference

If you already ran full-style inference once, you can compute `@k` offline from the saved full predictions.
This avoids re-running inference for `@2`, `@3`, `@4`, etc.

Example: compute `@3` with seed 0 from a full predictions file:

```bash
SCORE_PROMPT_VARIANT_SAMPLE_SIZE=3 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct
```

Default score directory:

- `score_direct_k3_seed0/`

Compute `@2`:

```bash
SCORE_PROMPT_VARIANT_SAMPLE_SIZE=2 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct
```

Default score directory:

- `score_direct_k2_seed0/`

Compute `@4`:

```bash
SCORE_PROMPT_VARIANT_SAMPLE_SIZE=4 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct
```

Default score directory:

- `score_direct_k4_seed0/`

This score-time sampling is deterministic and does **not** re-run inference.

## 5.4 Run a deterministic sampled `@3` directly at infer time

This is the cheapest way to quickly test a model before deciding whether to run full-style inference.

Example:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

## 5.5 Run prompt baselines

Examples:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode few_shot
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode plan_first
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode state_aware
```

Outputs are automatically separated by mode, for example:

- `predictions_direct.jsonl`
- `predictions_few_shot.jsonl`
- `predictions_plan_first.jsonl`
- `predictions_state_aware.jsonl`

and matching score directories:

- `score_direct/`
- `score_few_shot/`
- `score_plan_first/`
- `score_state_aware/`

If infer-time sampling is enabled, filenames and score directories also include `_k{K}_seed{S}` automatically.

## 6. Recommended minimal run order

If you just want the shortest safe path:

```bash
bash scripts/refresh_benchmark_references.sh

bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full/main \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/main

bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full/order_sensitivity \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/order_sensitivity
```

If you also want prompt-track rebuild on the already selected subset:

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark \
  --prompt-library data/processed/prompt_library/recipe_prompt_library.jsonl \
  --output-dir data/benchmark \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1
```

If you want a cheap first GPT smoke test with deterministic 3-style inference:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

If you later decide to run full-style GPT inference once and derive `@k` offline:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct

SCORE_PROMPT_VARIANT_SAMPLE_SIZE=2 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct

SCORE_PROMPT_VARIANT_SAMPLE_SIZE=3 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct

SCORE_PROMPT_VARIANT_SAMPLE_SIZE=4 \
SCORE_PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh score --mode direct
```

## Notes

- `reference_text` is now the single early-stop ground truth text field.
- `reference_text_full_run` is the extra full-run reference used for `order_sensitivity` analysis.
- Old fields such as `intermediate_text_at_drop` are removed during refresh.
- `build_eval_prompt_tracks` now stores all distinct prompt styles per sample.
- The current recommended prompt-track rebuild attaches styles to the already selected subset in `data/benchmark`; it does not intentionally re-filter the subset by prompt count.
- Infer-time sampling and score-time `@k` sampling are deterministic and seed-controlled.
