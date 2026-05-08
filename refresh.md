# Refresh Workflow

This file collects the commands needed to refresh benchmark references, rebuild the `main` subset, and regenerate prompt-track files after the recent pipeline changes.

Path conventions used below:

- `data/benchmark_full` is a track-root directory, for example:
  - `data/benchmark_full/atomic_ops/atomic_ops.jsonl`
  - `data/benchmark_full/main/main.jsonl`
  - `data/benchmark_full/order_sensitivity/order_sensitivity.jsonl`
- `data/processed/prompt_library` is also a track-root directory, for example:
  - `data/processed/prompt_library/atomic_ops/recipe_prompt_library.jsonl`
  - `data/processed/prompt_library/main/recipe_prompt_library.jsonl`
  - `data/processed/prompt_library/order_sensitivity/recipe_prompt_library.jsonl`

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

## 2. Attach all prompt styles to `benchmark_full` first

If you want subset selection to use prompt-style availability, the current supported path is:

1. refresh `benchmark_full`
2. write `prompt_variants` onto `benchmark_full`
3. select the engineering subset from that prompt-aware full benchmark

This is required before using `--min-prompt-variants K` in the subset builders.

Here `--benchmark-dir` and `--prompt-library` should both point to the directory roots above, not to a single `.jsonl` file.

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark_full \
  --prompt-library data/processed/prompt_library \
  --output-dir data/benchmark_full \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1
```

If your refreshed full benchmark is in a separate directory, use that instead:

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark_full_refreshed \
  --prompt-library data/processed/prompt_library \
  --output-dir data/benchmark_full_refreshed \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1
```

## 3. Rebuild the engineering `main` subset

Current logic keeps only:

- `clean-only`
- `clean-then-filter`

It no longer keeps `filter-then-clean`.

By default, this step does **not** filter by prompt-style count.

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

If you want the final subset itself to guarantee support for `@k`, do it here.
For example, for `@5`, select only rows with at least 5 prompt variants:

```bash
bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full/main \
  --output-dir data/benchmark/main \
  --min-prompt-variants 5
```

When `--min-prompt-variants > 0`, the builder still uses the original `processed-summary` logic to decide which `clean-only` and `clean-then-filter` variants are preferred. The new part is that prompt-style availability is added as an eligibility filter, so the builder will skip variants whose surviving rows do not have enough `prompt_variants` and fall through to the next eligible candidate when needed.

## 4. Rebuild the engineering `order_sensitivity` subset

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

For an `@5`-ready order subset:

```bash
bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full/order_sensitivity \
  --output-dir data/benchmark/order_sensitivity \
  --min-prompt-variants 5
```

The same rule applies here: summary-based family selection is still used first, but `prompt_variants` availability is added as an eligibility constraint so only families with enough surviving prompt-rich groups remain selectable.

If you also want the atomic subset to be `@5`-ready:

```bash
bash scripts/build_engineering_atomic_subset.sh \
  --source-dir data/benchmark_full/atomic_ops \
  --output-dir data/benchmark/atomic_ops \
  --min-prompt-variants 5
```

## 5. Attach all prompt styles to the selected benchmark subset

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
  --prompt-library data/processed/prompt_library \
  --output-dir data/benchmark \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1
```

This step is still useful even if you already attached styles to `benchmark_full`:

- it rewrites the final selected subset in `data/benchmark`
- it keeps all prompt styles available on the selected rows
- it should not do another round of benchmark filtering

So the current recommended split is:

- Step 2: attach styles to `benchmark_full`
- Step 3 / Step 4: optionally enforce `--min-prompt-variants K` while selecting the subset
- Step 5: attach styles to the final selected subset in `data/benchmark`

## 6. Run inference

## 6.1 Run all available prompt styles for each sample

Example:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

This uses all prompt variants stored in the benchmark row.

Default predictions filename:

- `predictions_direct.jsonl`

## 6.2 Run a deterministic sampled style subset at infer time

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

## 6.3 Score from a full-style predictions file without re-inference

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

## 6.4 Run a deterministic sampled `@3` directly at infer time

This is the cheapest way to quickly test a model before deciding whether to run full-style inference.

Example:

```bash
PROMPT_VARIANT_SAMPLE_SIZE=3 \
PROMPT_VARIANT_SAMPLING_SEED=0 \
bash scripts/eval/api/eval_gpt_5_4.sh infer --mode direct
```

## 6.5 Run prompt baselines

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

## 7. Recommended minimal run order

If you just want the shortest safe path:

```bash
bash scripts/refresh_benchmark_references.sh

PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark_full \
  --prompt-library data/processed/prompt_library \
  --output-dir data/benchmark_full \
  --tracks atomic_ops main order_sensitivity \
  --min-prompt-variants-per-sample 1

bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full/main \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/main

bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full/order_sensitivity \
  --processed-summary-dir data/processed/benchmark_instances \
  --output-dir data/benchmark/order_sensitivity
```

If you want a subset that is explicitly ready for `@5`, use:

```bash
bash scripts/build_engineering_main_subset.sh \
  --source-dir data/benchmark_full/main \
  --output-dir data/benchmark/main \
  --min-prompt-variants 5

bash scripts/build_engineering_order_subset.sh \
  --source-dir data/benchmark_full/order_sensitivity \
  --output-dir data/benchmark/order_sensitivity \
  --min-prompt-variants 5

bash scripts/build_engineering_atomic_subset.sh \
  --source-dir data/benchmark_full/atomic_ops \
  --output-dir data/benchmark/atomic_ops \
  --min-prompt-variants 5
```

Then attach styles to the final selected subset:

```bash
PYTHONPATH=src python3 -m cdrbench.prompting.build_eval_prompt_tracks \
  --benchmark-dir data/benchmark \
  --prompt-library data/processed/prompt_library \
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
- If you care about `@5`, first attach styles to `benchmark_full`, then enforce `--min-prompt-variants 5` during subset selection from that prompt-aware full benchmark.
- The final prompt-track rebuild on `data/benchmark` is for carrying all styles into the selected subset, not for another round of benchmark filtering.
- Infer-time sampling and score-time `@k` sampling are deterministic and seed-controlled.
