#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cdrbench.eval.run_benchmark_infer import (  # noqa: E402
    DEFAULT_PROMPT_CONFIG,
    _build_infer_backend,
    _default_system_prompt,
    _extract_prediction_fields,
    _extract_prediction_payload,
    _final_user_prompt,
    _is_retryable_prediction_error,
    _load_yaml,
    _retry_request_error,
    _select_prompt_variant,
    _tagged_output_hint,
)


DEFAULT_EVAL_PATH = REPO_ROOT / 'data' / 'benchmark' / 'main' / 'main.jsonl'
DEFAULT_TIMEOUT_SECONDS = 300.0
DEFAULT_MAX_RETRIES = 4

MODEL_PATTERN = re.compile(r'^MODEL="\$\{MODEL:-(.+)\}"$')
BASE_URL_PATTERN = re.compile(r'^BASE_URL="\$\{BASE_URL:-(.+)\}"$')


@dataclass(frozen=True)
class ScriptModelConfig:
    script_path: Path
    script_name: str
    model: str
    base_url: str


def _read_jsonl_first_row(path: Path) -> dict[str, Any]:
    with path.open('r', encoding='utf-8') as handle:
        for line in handle:
            if line.strip():
                return json.loads(line)
    raise RuntimeError(f'No non-empty row found in {path}.')


def _parse_default_value(path: Path, pattern: re.Pattern[str]) -> str:
    for line in path.read_text(encoding='utf-8').splitlines():
        match = pattern.match(line.strip())
        if match:
            return match.group(1)
    raise RuntimeError(f'Failed to parse default value from {path}.')


def load_script_model_configs(scripts_dir: Path) -> list[ScriptModelConfig]:
    configs: list[ScriptModelConfig] = []
    for script_path in sorted(scripts_dir.glob('infer_*.sh')):
        configs.append(
            ScriptModelConfig(
                script_path=script_path,
                script_name=script_path.name,
                model=_parse_default_value(script_path, MODEL_PATTERN),
                base_url=_parse_default_value(script_path, BASE_URL_PATTERN),
            )
        )
    if not configs:
        raise RuntimeError(f'No infer_*.sh scripts found under {scripts_dir}.')
    return configs


def build_messages(eval_row: dict[str, Any], prompt_config_path: Path, prompt_variant_index: int, model: str) -> list[dict[str, str]]:
    prompt_cfg = _load_yaml(prompt_config_path)
    system_prompt = _default_system_prompt(prompt_cfg)
    output_hint = _tagged_output_hint(prompt_cfg)
    prompt_variant = _select_prompt_variant(eval_row, prompt_variant_index)
    user_requirement = str(prompt_variant.get('user_requirement') or '').strip()
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': _final_user_prompt(eval_row, user_requirement, output_hint, model)},
    ]


def run_single_test(
    *,
    config: ScriptModelConfig,
    messages: list[dict[str, str]],
    api_key: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout_seconds: float,
    max_retries: int,
) -> dict[str, Any]:
    args = argparse.Namespace(
        concurrency=1,
        max_tokens=max_tokens,
        temperature=temperature,
        top_p=top_p,
        retry_sleep_seconds=2.0,
    )
    backend = _build_infer_backend(args, config.model, config.base_url, api_key)
    if hasattr(backend, 'timeout'):
        backend.timeout = timeout_seconds

    started = time.time()
    initial_result = backend.infer_one(messages)
    result, request_attempts = _retry_request_error(
        infer_backend=backend,
        initial_result=initial_result,
        messages=messages,
        track_name='api_test_main_first_row',
        instance_id='main_first_row',
        prompt_variant_index=0,
        max_request_tries=max(1, max_retries + 1),
    )

    response_text = result.text
    prediction_payload = None
    prediction_error = None
    retry_attempted = request_attempts > 1

    if result.error is not None:
        prediction_error = f'request_error: {result.error}'
    else:
        prediction_payload, prediction_error = _extract_prediction_payload(response_text)

    if _is_retryable_prediction_error(prediction_error):
        retry_attempted = True
        retry_result = backend.infer_one(messages)
        response_text = retry_result.text
        if retry_result.error is not None:
            prediction_payload = None
            prediction_error = f'request_error: {retry_result.error}'
        else:
            prediction_payload, prediction_error = _extract_prediction_payload(response_text)

    predicted_status, predicted_clean_text = _extract_prediction_fields(prediction_payload)
    elapsed = round(time.time() - started, 2)
    response_preview = (response_text or '').strip().replace('\n', ' ')
    if len(response_preview) > 200:
        response_preview = response_preview[:200] + '...'

    return {
        'script': config.script_name,
        'model': config.model,
        'base_url': config.base_url,
        'success': prediction_error is None,
        'elapsed': elapsed,
        'request_attempts': request_attempts,
        'retry_attempted': retry_attempted,
        'prediction_error': prediction_error,
        'predicted_status': predicted_status,
        'predicted_clean_text_preview': predicted_clean_text[:200],
        'response_preview': response_preview,
        'raw_response': response_text,
        'parsed_response': prediction_payload,
        'timeout_seconds': timeout_seconds,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description='Test API models using the same logic as scripts/eval/infer/api.')
    parser.add_argument('--api-key', required=True, help='API key passed through to the inference backend.')
    parser.add_argument('--scripts-dir', default=str(REPO_ROOT / 'scripts' / 'eval' / 'infer' / 'api'))
    parser.add_argument('--eval-path', default=str(DEFAULT_EVAL_PATH), help='Path to main track JSONL. The first row will be used.')
    parser.add_argument('--prompt-config', default=str(DEFAULT_PROMPT_CONFIG))
    parser.add_argument('--prompt-variant-index', type=int, default=0)
    parser.add_argument('--temperature', type=float, default=0.0)
    parser.add_argument('--top-p', type=float, default=0.0)
    parser.add_argument('--max-tokens', type=int, default=0)
    parser.add_argument('--timeout-seconds', type=float, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument('--max-retries', type=int, default=DEFAULT_MAX_RETRIES)
    parser.add_argument('--output', default=None, help='Optional JSON output path.')
    args = parser.parse_args()

    scripts_dir = Path(args.scripts_dir).resolve()
    eval_path = Path(args.eval_path).resolve()
    prompt_config_path = Path(args.prompt_config).resolve()

    if not scripts_dir.is_dir():
        raise SystemExit(f'Scripts directory not found: {scripts_dir}')
    if not eval_path.is_file():
        raise SystemExit(
            f'Main track file not found: {eval_path}\n'
            'Pass --eval-path /path/to/main.jsonl or set EVAL_PATH when running api_test/run_test.sh.'
        )
    if not prompt_config_path.is_file():
        raise SystemExit(f'Prompt config not found: {prompt_config_path}')

    script_configs = load_script_model_configs(scripts_dir)
    eval_row = _read_jsonl_first_row(eval_path)

    results: list[dict[str, Any]] = []
    total = len(script_configs)
    print('=' * 72)
    print('API inference smoke test')
    print(f'Scripts dir : {scripts_dir}')
    print(f'Eval row    : {eval_path} (first row only)')
    print(f'Prompt cfg  : {prompt_config_path}')
    print(f'Models      : {total}')
    print('=' * 72)

    for index, config in enumerate(script_configs, start=1):
        messages = build_messages(eval_row, prompt_config_path, args.prompt_variant_index, config.model)
        print(f'[{index}/{total}] {config.script_name} -> {config.model}', end=' ', flush=True)
        try:
            result = run_single_test(
                config=config,
                messages=messages,
                api_key=args.api_key,
                temperature=args.temperature,
                top_p=args.top_p,
                max_tokens=args.max_tokens,
                timeout_seconds=args.timeout_seconds,
                max_retries=args.max_retries,
            )
        except Exception as exc:
            result = {
                'script': config.script_name,
                'model': config.model,
                'base_url': config.base_url,
                'success': False,
                'elapsed': 0.0,
                'request_attempts': 0,
                'retry_attempted': False,
                'prediction_error': f'unhandled_error: {exc}',
                'predicted_status': '',
                'predicted_clean_text_preview': '',
                'response_preview': '',
                'raw_response': '',
                'parsed_response': None,
                'timeout_seconds': args.timeout_seconds,
            }
        results.append(result)

        if result['success']:
            print(f'✅ success ({result["elapsed"]}s)')
        else:
            print('❌ failed')
            print(f'    error: {result["prediction_error"]}')
        if result['response_preview']:
            print(f'    preview: {result["response_preview"]}')
        print()

    success_models = [item['model'] for item in results if item['success']]
    failed_models = [item['model'] for item in results if not item['success']]

    print('=' * 72)
    print(f'Summary: {len(success_models)}/{total} succeeded')
    print('Successful models:')
    for model in success_models:
        print(f'  - {model}')
    print('Failed models:')
    for model in failed_models:
        print(f'  - {model}')

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'scripts_dir': str(scripts_dir),
            'eval_path': str(eval_path),
            'prompt_config': str(prompt_config_path),
            'num_models': total,
            'num_success': len(success_models),
            'successful_models': success_models,
            'failed_models': failed_models,
            'results': results,
        }
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(f'Results saved to: {output_path}')

    return 0 if not failed_models else 1


if __name__ == '__main__':
    raise SystemExit(main())
