#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from cdrbench.prepare_data.build_benchmark_release import RELEASE_FIELD_ORDER


DEFAULT_PATTERNS = (
    'prediction*.json',
    'prediction*.jsonl',
    'predictions*.json',
    'predictions*.jsonl',
)

METADATA_PATTERNS = (
    '*summary.json',
    '*manifest.json',
    '*config.json',
    '*args.json',
    '*metadata.json',
)

EXCLUDED_METADATA_KEYWORDS = (
    'score',
    'scored',
    'metric',
    'metrics',
    'result',
    'results',
    'table',
    'tables',
    'analysis',
)

PREDICTION_FIELD_ORDER = [
    'request_model',
    'request_base_url',
    'prompt_mode',
    'selected_prompt_variant_indices',
    'variant_predictions',
]


def _iter_prediction_files(root: Path, patterns: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(files)


def _is_score_like_metadata(path: Path) -> bool:
    parts = [part.lower() for part in path.parts]
    name = path.name.lower()
    if any(keyword in name for keyword in EXCLUDED_METADATA_KEYWORDS):
        return True
    return any(part in EXCLUDED_METADATA_KEYWORDS for part in parts)


def _iter_metadata_files(root: Path, patterns: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in patterns:
        files.update(path for path in root.rglob(pattern) if path.is_file())
    return sorted(path for path in files if not _is_score_like_metadata(path))


def _ordered_prediction_row(row: dict[str, Any]) -> dict[str, Any]:
    ordered: dict[str, Any] = {}
    for key in RELEASE_FIELD_ORDER:
        if key in row:
            ordered[key] = row[key]
    for key in PREDICTION_FIELD_ORDER:
        if key in row and key not in ordered:
            ordered[key] = row[key]
    for key, value in row.items():
        if key not in ordered:
            ordered[key] = value
    return ordered


def _normalize_payload(payload: Any) -> Any:
    if isinstance(payload, dict):
        return _ordered_prediction_row(payload)
    if isinstance(payload, list):
        return [_ordered_prediction_row(item) if isinstance(item, dict) else item for item in payload]
    return payload


def _copy_or_normalize_jsonl(source_path: Path, output_path: Path, *, normalize_fields: bool) -> None:
    if not normalize_fields:
        shutil.copy2(source_path, output_path)
        return
    with source_path.open('r', encoding='utf-8') as source, output_path.open('w', encoding='utf-8') as output:
        for line_no, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise SystemExit(f'invalid JSONL in {source_path} at line {line_no}: {exc}') from exc
            output.write(json.dumps(_normalize_payload(payload), ensure_ascii=False) + '\n')


def _copy_or_normalize_json(source_path: Path, output_path: Path, *, normalize_fields: bool) -> None:
    if not normalize_fields:
        shutil.copy2(source_path, output_path)
        return
    try:
        payload = json.loads(source_path.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise SystemExit(f'invalid JSON in {source_path}: {exc}') from exc
    output_path.write_text(
        json.dumps(_normalize_payload(payload), ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )


def _copy_prediction_file(source_path: Path, output_path: Path, *, normalize_fields: bool) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = output_path.with_suffix(output_path.suffix + '.tmp')
    if source_path.suffix == '.jsonl':
        _copy_or_normalize_jsonl(source_path, tmp_path, normalize_fields=normalize_fields)
    elif source_path.suffix == '.json':
        _copy_or_normalize_json(source_path, tmp_path, normalize_fields=normalize_fields)
    else:
        shutil.copy2(source_path, tmp_path)
    tmp_path.replace(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Copy prediction artifacts to a new evaluation tree while leaving score outputs behind.'
    )
    parser.add_argument('--source-root', required=True, help='Existing evaluation directory containing predictions.')
    parser.add_argument('--output-root', required=True, help='Destination directory for copied prediction artifacts.')
    parser.add_argument(
        '--pattern',
        action='append',
        default=None,
        help='Glob pattern to copy. Can be passed multiple times. Default: prediction*.json/jsonl and predictions*.json/jsonl.',
    )
    parser.add_argument(
        '--include-metadata',
        action=argparse.BooleanOptionalAction,
        default=False,
        help='Also copy non-score summary/manifest/config metadata JSON files. Default: false.',
    )
    parser.add_argument(
        '--metadata-pattern',
        action='append',
        default=None,
        help='Metadata glob pattern to copy when --include-metadata is enabled. Can be passed multiple times.',
    )
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing destination files.')
    parser.add_argument(
        '--no-normalize-fields',
        action='store_true',
        help='Copy files byte-for-byte instead of rewriting prediction rows with release fields first.',
    )
    parser.add_argument('--dry-run', action='store_true', help='Print planned copies without writing files.')
    args = parser.parse_args()

    source_root = Path(args.source_root).expanduser().resolve()
    output_root = Path(args.output_root).expanduser().resolve()
    patterns = args.pattern or list(DEFAULT_PATTERNS)

    if not source_root.exists():
        raise SystemExit(f'source root does not exist: {source_root}')

    prediction_files = _iter_prediction_files(source_root, patterns)
    metadata_patterns = args.metadata_pattern or list(METADATA_PATTERNS)
    metadata_files = _iter_metadata_files(source_root, metadata_patterns) if args.include_metadata else []
    prediction_file_set = set(prediction_files)
    files_to_copy = [
        *prediction_files,
        *(path for path in metadata_files if path not in prediction_file_set),
    ]
    copied = 0
    skipped = 0
    copied_predictions = 0
    copied_metadata = 0
    for source_path in files_to_copy:
        relative_path = source_path.relative_to(source_root)
        output_path = output_root / relative_path
        if output_path.exists() and not args.overwrite:
            print(f'skip existing: {output_path}')
            skipped += 1
            continue
        artifact_kind = 'prediction' if source_path in prediction_file_set else 'metadata'
        print(f'copy {artifact_kind}: {source_path} -> {output_path}')
        if not args.dry_run:
            if artifact_kind == 'prediction':
                _copy_prediction_file(
                    source_path,
                    output_path,
                    normalize_fields=not bool(args.no_normalize_fields),
                )
            else:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, output_path)
        copied += 1
        if artifact_kind == 'prediction':
            copied_predictions += 1
        else:
            copied_metadata += 1

    mode = 'planned' if args.dry_run else 'copied'
    print(
        f'{mode} artifacts: total={copied}; predictions={copied_predictions}; metadata={copied_metadata}; '
        f'skipped_existing={skipped}; include_metadata={bool(args.include_metadata)}; '
        f'normalize_fields={not bool(args.no_normalize_fields)}; '
        f'source_root={source_root}; output_root={output_root}'
    )


if __name__ == '__main__':
    main()
