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

## 4. Rebuild eval-ready benchmark files with all prompt styles

The prompt benchmark now stores all distinct prompt styles per sample.
We no longer pre-sample 3 styles at benchmark-build time.

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/processed/benchmark_instances \
  --prompt-library data/processed/prompt_library/recipe_prompt_library.jsonl \
  --output-dir data/benchmark \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 3
```

## 5. Run inference

## 5.1 Run all available prompt styles for each sample

Example:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh --mode direct
```

This uses all prompt variants stored in the benchmark row.

## 5.2 Run a deterministic sampled `@3`

Example:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh --mode direct
```

This samples 3 prompt styles per sample deterministically using:

- `recipe_prompt_key`
- `instance_id`
- `PROMPT_VARIANT_SAMPLING_SEED`

You can also call infer mode explicitly:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer \
  --mode direct \
  --prompt-variant-sample-size 3 \
  --prompt-variant-sampling-seed 0
```

## 5.3 Run prompt baselines

Examples:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh --mode direct
bash scripts/eval/api/eval_gpt_5_4.sh --mode few_shot
bash scripts/eval/api/eval_gpt_5_4.sh --mode plan_first
bash scripts/eval/api/eval_gpt_5_4.sh --mode state_aware
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

If you also want prompt-track rebuild:

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/processed/benchmark_instances \
  --prompt-library data/processed/prompt_library/recipe_prompt_library.jsonl \
  --output-dir data/benchmark \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 3
```

## Notes

- `reference_text` is now the single early-stop ground truth text field.
- `reference_text_full_run` is the extra full-run reference used for `order_sensitivity` analysis.
- Old fields such as `intermediate_text_at_drop` are removed during refresh.
