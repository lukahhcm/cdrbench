#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


TRACKS = ('atomic_ops', 'main', 'order_sensitivity')


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open('r', encoding='utf-8') as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f'invalid JSONL in {path} at line {line_no}: {exc}') from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _resolve_benchmark_path(benchmark_root: Path, track: str) -> Path:
    filename = f'{track}.jsonl'
    nested = benchmark_root / track / filename
    flat = benchmark_root / filename
    if nested.exists():
        return nested
    if flat.exists():
        return flat
    raise FileNotFoundError(f'missing benchmark file for track={track}: {nested} or {flat}')


def _iter_prediction_files(root: Path, patterns: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(files)


def _infer_track_from_path(path: Path) -> str | None:
    for part in reversed(path.parts[:-1]):
        if part in TRACKS:
            return part
    return None


def _variant_prediction_completed_successfully(variant: dict[str, Any] | None) -> bool:
    if not isinstance(variant, dict):
        return False
    if bool(variant.get('valid_prediction')):
        return True
    prediction_error = str(variant.get('prediction_error') or '')
    if prediction_error.startswith('non_scoring_refusal:'):
        return True
    if variant.get('prediction_error') is None:
        return True
    predicted_status = '' if variant.get('predicted_status') is None else str(variant.get('predicted_status')).strip()
    predicted_clean_text = '' if variant.get('predicted_clean_text') is None else str(variant.get('predicted_clean_text'))
    return bool(predicted_status) and bool(predicted_clean_text)


def _prediction_completeness(benchmark_rows: list[dict[str, Any]], prediction_rows: list[dict[str, Any]]) -> dict[str, Any]:
    benchmark_ids = [str(row.get('instance_id') or '') for row in benchmark_rows if str(row.get('instance_id') or '')]
    benchmark_id_set = set(benchmark_ids)

    prediction_ids: list[str] = []
    rows_missing_instance_id = 0
    incomplete_variant_rows = 0

    for row in prediction_rows:
        instance_id = str(row.get('instance_id') or '')
        if instance_id:
            prediction_ids.append(instance_id)
        else:
            rows_missing_instance_id += 1

        selected_indices = row.get('selected_prompt_variant_indices')
        if not isinstance(selected_indices, list) or not selected_indices:
            continue
        variant_map: dict[int, dict[str, Any]] = {}
        for variant in row.get('variant_predictions') or []:
            if isinstance(variant, dict):
                variant_map[int(variant.get('prompt_variant_index', 0) or 0)] = variant
        if any(not _variant_prediction_completed_successfully(variant_map.get(index)) for index in selected_indices):
            incomplete_variant_rows += 1

    prediction_id_set = set(prediction_ids)
    duplicate_prediction_rows = len(prediction_ids) - len(prediction_id_set)
    missing_ids = sorted(benchmark_id_set - prediction_id_set)
    extra_ids = sorted(prediction_id_set - benchmark_id_set)

    is_complete = (
        rows_missing_instance_id == 0
        and duplicate_prediction_rows == 0
        and not missing_ids
        and not extra_ids
        and incomplete_variant_rows == 0
    )

    return {
        'is_complete': is_complete,
        'benchmark_rows': len(benchmark_rows),
        'prediction_rows': len(prediction_rows),
        'prediction_unique_instance_ids': len(prediction_id_set),
        'rows_missing_instance_id': rows_missing_instance_id,
        'duplicate_prediction_rows': duplicate_prediction_rows,
        'missing_instance_count': len(missing_ids),
        'extra_instance_count': len(extra_ids),
        'incomplete_variant_rows': incomplete_variant_rows,
        'missing_instance_examples': missing_ids[:5],
        'extra_instance_examples': extra_ids[:5],
    }


def _derive_score_dirname(predictions_path: Path, sample_size: int, sample_seed: int) -> str:
    stem = predictions_path.stem
    suffix = ''
    if stem.startswith('predictions_'):
        suffix = stem[len('predictions_') :]
    elif stem.startswith('prediction_'):
        suffix = stem[len('prediction_') :]

    if suffix:
        if '_k' in suffix and '_seed' in suffix:
            suffix = suffix.split('_k', 1)[0]
        base = f'score_{suffix}'
    else:
        base = 'score'

    if sample_size > 0:
        return f'{base}_k{sample_size}_seed{sample_seed}'
    return base


def _run_score(
    *,
    python_bin: str,
    predictions_path: Path,
    output_dir: Path,
    sample_size: int,
    sample_seed: int,
    progress_every: int,
    resume: bool,
    clean_output_dir: bool,
) -> int:
    if clean_output_dir and output_dir.exists():
        shutil.rmtree(output_dir)

    cmd = [
        python_bin,
        '-m',
        'cdrbench.eval.run_benchmark_score',
        '--predictions-path',
        str(predictions_path),
        '--output-dir',
        str(output_dir),
        '--prompt-variant-sample-size',
        str(sample_size),
        '--prompt-variant-sampling-seed',
        str(sample_seed),
        '--progress-every',
        str(progress_every),
        '--write-csv-slices',
    ]
    if resume:
        cmd.append('--resume')
    return subprocess.run(cmd, cwd=REPO_ROOT, check=False).returncode


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Recursively scan an evaluation tree, score complete prediction files, and report incomplete ones.'
    )
    parser.add_argument('--benchmark-root', required=True, help='Root containing <track>.jsonl files.')
    parser.add_argument('--predictions-root', default='data/evaluation', help='Evaluation root to scan recursively.')
    parser.add_argument('--tracks', default='atomic_ops,main,order_sensitivity', help='Comma-separated tracks to consider.')
    parser.add_argument(
        '--prediction-glob',
        action='append',
        default=None,
        help='Glob pattern to scan recursively. Can repeat. Default: prediction*.jsonl and predictions*.jsonl',
    )
    parser.add_argument('--score-dirname', default=None, help='Optional fixed score dirname for every matched prediction file.')
    parser.add_argument('--prompt-variant-sample-size', type=int, default=3)
    parser.add_argument('--prompt-variant-sampling-seed', type=int, default=0)
    parser.add_argument('--progress-every', type=int, default=20)
    parser.add_argument('--resume-score', action='store_true', help='Resume score outputs instead of recomputing from scratch.')
    parser.add_argument(
        '--keep-existing-score-dir',
        action='store_true',
        help='Do not remove an existing score directory before scoring.',
    )
    parser.add_argument('--dry-run', action='store_true', help='Print what would be scored without running scoring.')
    args = parser.parse_args()

    benchmark_root = Path(args.benchmark_root).expanduser().resolve()
    predictions_root = Path(args.predictions_root).expanduser().resolve()
    if not benchmark_root.exists():
        raise SystemExit(f'benchmark root does not exist: {benchmark_root}')
    if not predictions_root.exists():
        raise SystemExit(f'predictions root does not exist: {predictions_root}')

    tracks = [track.strip() for track in args.tracks.split(',') if track.strip()]
    unsupported = [track for track in tracks if track not in TRACKS]
    if unsupported:
        raise SystemExit(f'unsupported tracks: {unsupported}')

    benchmark_rows_by_track = {
        track: _read_jsonl(_resolve_benchmark_path(benchmark_root, track))
        for track in tracks
    }

    patterns = args.prediction_glob or ['prediction*.jsonl', 'predictions*.jsonl']
    prediction_files = _iter_prediction_files(predictions_root, patterns)
    if not prediction_files:
        raise SystemExit(f'no prediction files found under {predictions_root} matching {patterns}')

    python_bin = str((REPO_ROOT / '.venv-ops' / 'bin' / 'python').resolve())
    if not Path(python_bin).exists():
        python_bin = sys.executable

    scanned = 0
    scored = 0
    incomplete = 0
    failed = 0
    skipped_unknown_track = 0

    for predictions_path in prediction_files:
        track = _infer_track_from_path(predictions_path)
        if track is None or track not in benchmark_rows_by_track:
            print(f'[skip] track_unknown predictions={predictions_path}')
            skipped_unknown_track += 1
            continue

        scanned += 1
        prediction_rows = _read_jsonl(predictions_path)
        completeness = _prediction_completeness(benchmark_rows_by_track[track], prediction_rows)
        score_dirname = args.score_dirname or _derive_score_dirname(
            predictions_path,
            sample_size=args.prompt_variant_sample_size,
            sample_seed=args.prompt_variant_sampling_seed,
        )
        output_dir = predictions_path.parent / score_dirname

        if not completeness['is_complete']:
            incomplete += 1
            print(
                '[incomplete] '
                f'track={track} predictions={predictions_path} '
                f'benchmark_rows={completeness["benchmark_rows"]} '
                f'prediction_rows={completeness["prediction_rows"]} '
                f'unique_ids={completeness["prediction_unique_instance_ids"]} '
                f'missing_ids={completeness["missing_instance_count"]} '
                f'extra_ids={completeness["extra_instance_count"]} '
                f'duplicate_rows={completeness["duplicate_prediction_rows"]} '
                f'rows_missing_instance_id={completeness["rows_missing_instance_id"]} '
                f'incomplete_variant_rows={completeness["incomplete_variant_rows"]}'
            )
            if completeness['missing_instance_examples']:
                print(f'  missing_examples={completeness["missing_instance_examples"]}')
            if completeness['extra_instance_examples']:
                print(f'  extra_examples={completeness["extra_instance_examples"]}')
            continue

        print(f'[score] track={track} predictions={predictions_path} output_dir={output_dir}')
        if args.dry_run:
            scored += 1
            continue

        returncode = _run_score(
            python_bin=python_bin,
            predictions_path=predictions_path,
            output_dir=output_dir,
            sample_size=args.prompt_variant_sample_size,
            sample_seed=args.prompt_variant_sampling_seed,
            progress_every=args.progress_every,
            resume=args.resume_score,
            clean_output_dir=not args.keep_existing_score_dir and not args.resume_score,
        )
        if returncode == 0:
            scored += 1
        else:
            failed += 1
            print(f'[failed] track={track} predictions={predictions_path} exit_code={returncode}')

    print(
        '[complete] '
        f'scanned={scanned} scored={scored} incomplete={incomplete} failed={failed} '
        f'skipped_unknown_track={skipped_unknown_track} predictions_root={predictions_root}'
    )


if __name__ == '__main__':
    main()
