# CDR-Bench

**CDR-Bench: Benchmarking LLMs for Compositional Data Refinement**

This repository builds CDR-Bench data from raw JSONL corpora using a repo-local Data-Juicer checkout. The current pipeline downloads raw data, tags operator activity, mines domain recipes, materializes recipe variants, and generates deterministic references for the main, order-sensitivity, and atomic calibration sets.

The repository and package are now named `cdrbench`.

## Pipeline

Run the full construction flow in this order:

1. Download raw JSONL files into `data/raw/`.
2. Run Data-Juicer CLI tagging with `tag_and_assign_domains.py`.
3. Mine per-domain recipe candidates with `mine_domain_recipes.py`.
4. Materialize recipe libraries with `materialize_domain_recipes.py`.
5. Generate benchmark instances and deterministic references with `materialize_benchmark_instances.py`.

The final benchmark files are written under `data/benchmark/`.

## 1. Clone

```bash
git clone https://github.com/lukahhcm/cdrbench.git
cd cdrbench
```

## 2. Environment

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create a small project environment:

```bash
uv venv .venv-ops --python 3.11
uv pip install --python .venv-ops/bin/python -e .
uv pip install --python .venv-ops/bin/python -U huggingface_hub py-data-juicer
```

The repository already vendors `data-juicer/`, including the customized operators used by CDR-Bench. The preparation scripts prefer:

```bash
python data-juicer/tools/process_data.py
python data-juicer/tools/analyze_data.py
```

Only if `./data-juicer` is unavailable do they fall back to system `dj-process` / `dj-analyze`.

## 3. Download Raw Data

```bash
HF_TOKEN=<your_hf_token_if_needed> \
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.release.download_hf_jsonl \
  --repo-id lukahh/cdrbench-raw \
  --repo-root .
```

The manifest downloads JSONL files into `data/raw/`, including arXiv, Common Crawl, Wikipedia/help-style text, government reports, and PII corpora.

## 4. Tag Operators and Assign Domains

Small smoke test:

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.tag_and_assign_domains --max-records 200
```

Full resumable run:

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.tag_and_assign_domains --resume
```

Useful overrides:

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.tag_and_assign_domains \
  --dj-repo-root /path/to/data-juicer \
  --dj-python /usr/bin/python3 \
  --resume
```

Outputs:

- `data/processed/domain_tags/*.jsonl`
- `data/processed/domain_filtered/*.jsonl`
- `data/processed/domain_filtered/all.jsonl`
- `data/processed/domain_operator_catalog.csv`
- `data/processed/domain_labeling_summary.csv`
- `data/processed/dj_cli_tagging/`

Notes:

- Most text-cleaning mappers run through `dj-process`.
- Meta/stat filters run through `dj-analyze`.
- Mappers used in the final benchmark should preserve one input row to one output row.
- `extract_tables_from_html_mapper` writes deterministic TSV text back into `text`.
- `latex_figure_context_extractor_mapper` writes merged figure-context text back into `text`.

## 5. Mine Recipe Candidates

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.mine_domain_recipes \
  --tagged-dir data/processed/domain_tags \
  --output-dir data/processed/recipe_mining
```

By default, a concrete recipe candidate needs at least `5` supporting samples. Adjust this with `--min-recipe-support`.

Key outputs:

- `data/processed/recipe_mining/<domain>/recipe_families.csv`
- `data/processed/recipe_mining/<domain>/selected_recipes.csv`
- `data/processed/recipe_mining/<domain>/recipe_candidates.yaml`
- `data/processed/recipe_mining/domain_recipe_mining_summary.csv`

Quick inspection:

```bash
column -s, -t < data/processed/recipe_mining/domain_recipe_mining_summary.csv | less -S
column -s, -t < data/processed/recipe_mining/web/selected_recipes.csv | less -S
sed -n '1,160p' data/processed/recipe_mining/web/recipe_candidates.yaml
```

Fallback recipe candidates are kept for inspection but excluded from benchmark materialization.

## 6. Materialize Recipe Libraries

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.materialize_domain_recipes \
  --recipe-mining-dir data/processed/recipe_mining \
  --filtered-path data/processed/domain_filtered/all.jsonl \
  --output-dir data/processed/recipe_library \
  --resume
```

This step:

- orders mined clean/operator sets into deterministic clean sequences
- replays clean prefixes to build `S0, S1, ..., Sfinal` checkpoints
- scans filter statistics at each checkpoint
- produces main-track variants and order-sensitivity families

Main-track recipe types:

- `clean-only`
- `filter-then-clean`
- `clean-then-filter`

Order-sensitivity families:

- `front`: `filter-then-clean`
- `middle`: `clean-filter-clean`
- `end`: `clean-then-filter`

Key outputs:

- `data/processed/recipe_library/<domain>/recipe_library.yaml`
- `data/processed/recipe_library/<domain>/recipe_variants.csv`
- `data/processed/recipe_library/<domain>/filter_attachments.csv`
- `data/processed/recipe_library/<domain>/checkpoint_filter_stats.csv`
- `data/processed/recipe_library/<domain>/order_sensitivity_families.csv`
- `data/processed/recipe_library/recipe_library_summary.csv`

Useful checks:

```bash
column -s, -t < data/processed/recipe_library/recipe_library_summary.csv | less -S
column -s, -t < data/processed/recipe_library/web/recipe_variants.csv | less -S
column -s, -t < data/processed/recipe_library/web/checkpoint_filter_stats.csv | less -S
```

## 7. Generate Benchmark Instances and GT

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.prepare_data.materialize_benchmark_instances \
  --recipe-library-dir data/processed/recipe_library \
  --filtered-path data/processed/domain_filtered/all.jsonl \
  --output-dir data/benchmark \
  --target-drop-rate 0.5 \
  --max-candidate-records 0 \
  --max-input-chars 50000 \
  --min-positive-ratio-threshold 0.001 \
  --zero-ratio-threshold-policy min-positive \
  --max-instances-per-variant 50 \
  --max-order-groups-per-family 30 \
  --max-atomic-candidate-records 1000 \
  --max-atomic-instances-per-op 10 \
  --min-keep 5 \
  --min-drop 5 \
  --min-order-sensitive-groups 5 \
  --min-atomic-keep 3 \
  --min-atomic-drop 3 \
  --resume
```

This step does not generate prompts yet. It selects samples and runs deterministic references.

Outputs:

- `data/benchmark/main.jsonl`
- `data/benchmark/order_sensitivity.jsonl`
- `data/benchmark/atomic_ops.jsonl`
- `data/benchmark/main_summary.csv`
- `data/benchmark/order_sensitivity_summary.csv`
- `data/benchmark/atomic_ops_summary.csv`

Target scale:

- main track: about `5k` instances
- order-sensitivity track: about `1k` order groups, or `3k` variant instances
- atomic calibration: about `1k` instances, up to 10 per operator

Important parameters:

- `--target-drop-rate 0.5`: calibrate filter tasks toward 50% `KEEP` and 50% `DROP`
- `--max-candidate-records 0`: scan all eligible candidate samples per recipe variant or order family; set a positive number such as `2000` for a faster capped run
- `--max-input-chars 50000`: skip raw inputs above 50k characters before GT materialization, keeping tasks within a practical prompt budget for recent strong models; use `0` to disable
- `--min-positive-ratio-threshold 0.001`: when a calibrated ratio threshold is exactly `0`, first try a small positive threshold instead of creating an unnatural zero-ratio task
- `--max-instances-per-variant 50`: cap main-track instances per recipe variant
- `--max-order-groups-per-family 30`: cap order groups per order family
- `--max-atomic-candidate-records 1000`: scan at most 1000 candidates per atomic operator
- `--max-atomic-instances-per-op 10`: cap atomic instances per operator
- `--min-keep / --min-drop`: skip main filter variants without enough keep/drop candidates
- `--min-order-sensitive-groups`: skip order families without enough genuinely order-sensitive groups
- `--min-atomic-keep / --min-atomic-drop`: skip atomic filters without enough keep/drop candidates
- `--zero-ratio-threshold-policy min-positive`: use `0.001` for degenerate calibrated ratio thresholds and let normal keep/drop balance checks decide whether to keep the variant; use `skip` to drop such variants immediately
- `--resume`: reuse per-variant cache shards in `data/benchmark/_materialize_cache_v2/` after an interrupted run

Thresholds are recalibrated during materialization. Length/count thresholds are rounded to human-readable values such as 5, 10, 50, 100, and 1000. Ratios usually use a 0.01 grid, while very small ratios may keep finer 0.001 or 0.0001 grids. Final row selection is best-effort diversity-aware: rows from source records that have already been selected by earlier recipes are deprioritized.

## 8. How to Read the Outputs

Main benchmark:

- `main.jsonl` contains one task per row.
- `recipe_type` tells whether the row is `clean-only`, `filter-then-clean`, or `clean-then-filter`.
- `reference_status` and `reference_text` are the deterministic GT.
- Workflow length can be recovered from the operator sequence fields in each row.
- `input_length_chars` and `input_length_bucket` support difficulty analysis without splitting the main benchmark by length.

Order-sensitivity benchmark:

- `order_sensitivity.jsonl` contains `front / middle / end` variant rows.
- Rows with the same `order_group_instance_id` belong together.
- Group success requires all three slots to be correct.

Atomic calibration:

- `atomic_ops.jsonl` is keyed by global operator.
- `source_domain` is diagnostic only.
- Use it to estimate atomic operator difficulty and compositional gaps.

Evaluation metrics:

- `status_match = predicted_status == reference_status`
- `text_exact_match = predicted_clean_text == reference_text`
- `recipe_success = status_match AND text_exact_match`
- `refinement_gain` (`rg`) is a bounded edit-distance improvement score from input toward the reference:

```text
d_input = edit_distance(input_text, reference_text)
d_pred  = edit_distance(predicted_clean_text, reference_text)

if d_input + d_pred == 0:
    refinement_gain = 1.0
else:
    refinement_gain = (d_input - d_pred) / (d_input + d_pred)
```

This keeps `rg` in `[-1, 1]`: `1` means fully correct, `0` means no net improvement, and negative values mean the prediction moved farther from the reference.

The main evaluator uses raw-string exact match for `recipe_success`.

Benchmark composition visualization:

If you want a quick paper-style overview of what the benchmark is made of, generate the composition plots:

```bash
PYTHONPATH=src .venv-ops/bin/python -m cdrbench.reporting.plot_benchmark_composition \
  --benchmark-dir data/benchmark \
  --recipe-library-dir data/processed/recipe_library \
  --output-dir data/paper_stats/plots
```

Outputs:

- `data/paper_stats/plots/benchmark_composition_overview.png`
- `data/paper_stats/plots/benchmark_composition_overview.pdf`
- `data/paper_stats/plots/benchmark_composition_summary.json`

The overview figure shows:

- recipe-library domain composition
- main-track domain composition
- main-track recipe-type composition
- main-variant `kept / skipped` status composition
- order-sensitive group composition by domain
- order-family `kept / skipped` status composition
- atomic-track source-domain composition
- atomic-operator `kept / skipped` status composition

## 9. Generate Model Prompts

Prompt generation is intentionally separate from GT construction, so prompt wording can be revised without rerunning Data-Juicer references.

Use the bundled orchestration script to run the full prompt pipeline for all three tracks in order:

- `atomic_ops`
- `main`
- `order_sensitivity`

The script performs three steps for each track:

1. generate recipe-level prompt candidates
2. judge and keep only accepted prompts
3. combine the accepted prompt pool with benchmark rows to build eval-ready files

Default run:

```bash
./scripts/run_prompt_pipeline_all_tracks.sh
```

This default uses the repo's current LLM defaults:

- base URL: `http://123.57.212.178:3333/v1`
- model: `gpt-5.4`
- recipe-level resume cache: enabled

Set an API key before running:

```bash
export OPENAI_API_KEY="your_key"
```

If needed, you can still override the model endpoint explicitly:

```bash
./scripts/run_prompt_pipeline_all_tracks.sh \
  --base-url http://123.57.212.178:3333/v1 \
  --model gpt-5.4 \
  --judge-base-url http://123.57.212.178:3333/v1 \
  --judge-model gpt-5.4
```

Useful overrides:

```bash
./scripts/run_prompt_pipeline_all_tracks.sh --tracks atomic_ops
./scripts/run_prompt_pipeline_all_tracks.sh --prompt-source template
./scripts/run_prompt_pipeline_all_tracks.sh --no-resume
```

## 10. Evaluation

Evaluation now uses unified per-model `eval` wrappers under:

- `scripts/eval/api/`
- `scripts/eval/vllm/`

The old per-model `scripts/eval/infer/*` and `scripts/eval/score/*` wrappers have been removed.

Each wrapper supports three modes:

- `infer`: inference only
- `score`: scoring only
- default: run `infer` first, then `score`

Behavior:

- `infer` resumes from existing `predictions.jsonl`
- when resuming, only rows whose previous result completed successfully are skipped
- if any sample ends with a non-null `prediction_error`, inference stops immediately after writing the latest snapshot
- `score` always deletes the old `score/` directory and recomputes all metrics from scratch

### API Models

API wrappers now follow the same routing rules as `api_test`:

- endpoint URL is auto-selected from the model name
- request payload shape is auto-selected per model family
- if `API_KEY` is empty, the wrapper will prompt you for it before inference

Example: run full evaluation for `gpt-5.4`:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh
```

Inference only:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh infer
```

Score only:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh score
```

Useful examples for current API roster:

```bash
bash scripts/eval/api/eval_gpt_5_4.sh
bash scripts/eval/api/eval_gpt_5_4_pro.sh
bash scripts/eval/api/eval_claude_sonnet_4_6.sh
bash scripts/eval/api/eval_claude_opus_4_5.sh
bash scripts/eval/api/eval_claude_opus_4_6.sh
bash scripts/eval/api/eval_gemini_3_1_pro_preview.sh
bash scripts/eval/api/eval_grok_4_1_fast_reasoning.sh
bash scripts/eval/api/eval_glm_5.sh
bash scripts/eval/api/eval_kimi_k2_6.sh
bash scripts/eval/api/eval_qwen3_6_max_preview.sh
bash scripts/eval/api/eval_qwen3_6_plus.sh
bash scripts/eval/api/eval_deepseek_v4_pro.sh
bash scripts/eval/api/eval_deepseek_v4_flash.sh
```

Common overrides:

```bash
TRACKS=atomic_ops bash scripts/eval/api/eval_gpt_5_4.sh
TRACKS=main,order_sensitivity bash scripts/eval/api/eval_qwen3_6_plus.sh infer
MAX_SAMPLES=100 bash scripts/eval/api/eval_deepseek_v4_pro.sh
CONCURRENCY=1 bash scripts/eval/api/eval_claude_opus_4_5.sh
API_KEY=<your_key> bash scripts/eval/api/eval_gpt_5_4.sh
```

### Local vLLM Models

Start a local OpenAI-compatible server first, for example:

```bash
bash scripts/start_vllm.sh /path/to/local/model local-model 8904 4,5,6,7 4
```

Then run an eval wrapper:

```bash
bash scripts/eval/vllm/eval_qwen3_5_9b.sh
bash scripts/eval/vllm/eval_qwen3_6_27b.sh infer
bash scripts/eval/vllm/eval_gemma4.sh score
```

Current vLLM wrappers:

- `eval_gemma4.sh`
- `eval_llama_3_3_70b_instruct.sh`
- `eval_llama_4_scout_17b_16e_instruct.sh`
- `eval_qwen3_5_9b.sh`
- `eval_qwen3_6_27b.sh`
- `eval_qwen3_6_35b_a3b.sh`

### Outputs

Per-track outputs are written under the wrapper's `OUTPUT_ROOT`, for example:

- `data/evaluation/infer/gpt_5_4/atomic_ops/`
- `data/evaluation/infer/gpt_5_4/main/`
- `data/evaluation/infer/gpt_5_4/order_sensitivity/`

Each track contains:

- `predictions.jsonl`
- `summary.json`
- `score/paper_metrics.json`
- `score/report.txt`
- `score/instance_metrics.jsonl`
- `score/scored_variant_predictions.jsonl`
- `score/by_*.csv` slice reports

### Direct Driver

If you want to compose your own wrapper or launch ad hoc runs, use the common driver directly:

```bash
MODEL=openai.gpt-5.4-2026-03-05 \
OUTPUT_ROOT=data/evaluation/infer/gpt_5_4_manual \
PROMPT_API_KEY=true \
bash scripts/eval/run_model_eval.sh
```

Modes with the common driver:

```bash
bash scripts/eval/run_model_eval.sh infer
bash scripts/eval/run_model_eval.sh score
bash scripts/eval/run_model_eval.sh all
```

To render paper-ready LaTeX result tables for `atomic_ops`, `main`, and `order_sensitivity` together, run:

```bash
PYTHONPATH=src python -m cdrbench.reporting.render_benchmark_results_tables \
  --predictions-root data/eval_runs \
  --output-dir data/eval_runs/reports
```

This writes:

- `data/eval_runs/reports/atomic_ops_results_table.tex`
- `data/eval_runs/reports/main_results_table.tex`
- `data/eval_runs/reports/order_sensitivity_results_table.tex`

## 11. Troubleshooting Data-Juicer Imports

If tagging fails with errors such as:

- `No module named 'data_juicer.core.data'`
- the same Python command worked before but now fails

Run:

```bash
PYTHONPATH=src python -m cdrbench.debug_tools.debug_data_juicer_env
```

This checks:

- current Python executable and version
- whether the system `data_juicer` package is shadowing the repo-local checkout
- whether vendored `data-juicer/` imports correctly
- whether `process_data.py` and `analyze_data.py` import cleanly

Paste the full output when debugging the server environment.
