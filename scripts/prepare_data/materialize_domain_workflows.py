#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean
from typing import Any, Iterable

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from icdrbench.config import load_domains_config
from icdrbench.dj_operator_loader import Fields, create_operator
from icdrbench.domain_assignment import build_domain_execution_plan


FILTER_STATUS_RULES: dict[str, dict[str, Any]] = {
    'alphanumeric_filter': {
        'value_key': lambda params: 'alpha_token_ratio' if params.get('tokenization') else 'alnum_ratio',
        'min_key': 'min_ratio',
        'max_key': 'max_ratio',
    },
    'average_line_length_filter': {'value_key': 'avg_line_length', 'min_key': 'min_len', 'max_key': 'max_len'},
    'character_repetition_filter': {'value_key': 'char_rep_ratio', 'min_key': 'min_ratio', 'max_key': 'max_ratio'},
    'flagged_words_filter': {'value_key': 'flagged_words_ratio', 'min_key': 'min_ratio', 'max_key': 'max_ratio'},
    'maximum_line_length_filter': {'value_key': 'max_line_length', 'min_key': 'min_len', 'max_key': 'max_len'},
    'stopwords_filter': {'value_key': 'stopwords_ratio', 'min_key': 'min_ratio', 'max_key': 'max_ratio'},
    'text_length_filter': {'value_key': 'text_len', 'min_key': 'min_len', 'max_key': 'max_len'},
    'word_repetition_filter': {'value_key': 'word_rep_ratio', 'min_key': 'min_ratio', 'max_key': 'max_ratio'},
    'words_num_filter': {'value_key': 'num_words', 'min_key': 'min_num', 'max_key': 'max_num'},
}

SAFE_MAX_CHARS_FOR_EXPENSIVE_MAPPERS = 80_000
EXPENSIVE_LONG_TEXT_MAPPERS = {
    'remove_repeat_sentences_mapper',
    'remove_words_with_incorrect_substrings_mapper',
}


def iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open('r', encoding='utf-8') as f:
        for lineno, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                preview = line[:200]
                raise ValueError(
                    f'Invalid JSONL record in {path} at line {lineno}: {exc.msg}. Line preview: {preview!r}'
                ) from exc


def _call_optional_context(method, payload):
    try:
        return method(payload, context=True)
    except TypeError:
        return method(payload)


def _build_batch(text: str, suffix: str) -> dict[str, Any]:
    return {
        'text': [text],
        Fields.stats: [{}],
        Fields.context: [{}],
        Fields.meta: [{}],
        Fields.suffix: [suffix],
    }


def _build_sample(text: str, suffix: str) -> dict[str, Any]:
    return {
        'text': text,
        Fields.stats: {},
        Fields.context: {},
        Fields.meta: {},
        Fields.suffix: suffix,
    }


def _infer_suffix(record: dict[str, Any]) -> str:
    source_name = record.get('source_name')
    if isinstance(source_name, str) and source_name:
        suffix = Path(source_name).suffix
        if suffix:
            return suffix

    url = record.get('url')
    if isinstance(url, str) and url:
        suffix = Path(url).suffix
        if suffix:
            return suffix

    text = str(record.get('text', ''))
    lowered = text.lower()
    if '\\begin{document}' in lowered or '\\section' in lowered:
        return '.tex'
    if '<html' in lowered or '</html>' in lowered:
        return '.html'
    return ''


def _apply_mapper_text(op_name: str, text: str, params: dict[str, Any], suffix: str) -> tuple[str, dict[str, Any]]:
    if op_name in EXPENSIVE_LONG_TEXT_MAPPERS and len(text) > SAFE_MAX_CHARS_FOR_EXPENSIVE_MAPPERS:
        return text, {
            'active': False,
            'skipped': 'text_too_long_for_expensive_mapper',
            'output_length': len(text),
            'delta_chars': 0,
        }

    op = create_operator(op_name, **params)
    if hasattr(op, 'process_batched') and op.is_batched_op():
        result = op.process_batched(_build_batch(text, suffix))
        output_text = result['text'][0]
    else:
        result = op.process_single(_build_sample(text, suffix))
        output_text = result['text']

    return output_text, {
        'active': output_text != text,
        'output_length': len(output_text),
        'delta_chars': len(output_text) - len(text),
    }


def _evaluate_filter(op_name: str, text: str, params: dict[str, Any], suffix: str) -> dict[str, Any]:
    op = create_operator(op_name, **params)
    if hasattr(op, 'compute_stats_batched') and op.is_batched_op():
        batch = _call_optional_context(op.compute_stats_batched, _build_batch(text, suffix))
        keep_iter = op.process_batched(batch)
        keep = list(keep_iter)[0] if not isinstance(keep_iter, list) else keep_iter[0]
        stats = batch[Fields.stats][0]
    else:
        sample = _build_sample(text, suffix)
        if hasattr(op, 'compute_stats_single'):
            sample = _call_optional_context(op.compute_stats_single, sample)
        keep = op.process_single(sample)
        stats = sample[Fields.stats]

    return {
        'keep': bool(keep),
        'status': 'KEEP' if keep else 'DROP',
        'stats': stats,
    }


def _resolve_status_value_key(op_name: str, params: dict[str, Any]) -> str | None:
    rule = FILTER_STATUS_RULES.get(op_name)
    if rule is None:
        return None
    value_key = rule['value_key']
    return value_key(params) if callable(value_key) else value_key


def _parse_operator_set(blob: str) -> list[str]:
    return [item.strip() for item in blob.split(' | ') if item.strip()]


def _labeling_meta(record: dict[str, Any]) -> dict[str, Any]:
    meta = record.get('meta')
    if not isinstance(meta, dict):
        return {}
    payload = meta.get('icdrbench_domain_labeling')
    return payload if isinstance(payload, dict) else {}


def _workflow_rows_for_domain(domain_dir: Path) -> list[dict[str, Any]]:
    workflow_csv = domain_dir / 'selected_workflows.csv'
    if not workflow_csv.exists():
        return []
    df = pd.read_csv(workflow_csv)
    return df.to_dict(orient='records')


def _ordered_mapper_sequence(
    domain: str,
    operator_set: list[str],
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    domain_profile = plan['domain_profiles'][domain]
    variants_by_key = plan['execution_variants_by_key']
    wanted = set(operator_set)
    ordered: list[dict[str, Any]] = []
    for key in domain_profile['mapper_keys']:
        variant = variants_by_key[key]
        if variant['name'] in wanted:
            ordered.append(variant)
    seen = {variant['name'] for variant in ordered}
    for op_name in operator_set:
        if op_name in seen:
            continue
        for variant in plan['execution_variants']:
            if variant['kind'] == 'mapper' and variant['name'] == op_name:
                ordered.append(variant)
                break
    return ordered


def _domain_filter_variants(domain: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    domain_profile = plan['domain_profiles'][domain]
    variants_by_key = plan['execution_variants_by_key']
    return [variants_by_key[key] for key in domain_profile['filter_keys']]


def _supporting_records(
    records: list[dict[str, Any]],
    operator_set: list[str],
    max_records: int,
) -> list[dict[str, Any]]:
    wanted = set(operator_set)
    supported = []
    for record in records:
        meta = _labeling_meta(record)
        active = set(meta.get('active_mapper_names', []))
        if wanted.issubset(active):
            supported.append(record)
    return supported[:max_records]


def _replay_mapper_checkpoints(
    record: dict[str, Any],
    ordered_mappers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    suffix = _infer_suffix(record)
    current_text = str(record.get('text', ''))
    checkpoints = [
        {
            'checkpoint_id': 'S0',
            'step_index': 0,
            'after_operator': None,
            'text': current_text,
        }
    ]
    for idx, variant in enumerate(ordered_mappers, start=1):
        current_text, mapper_result = _apply_mapper_text(variant['name'], current_text, dict(variant.get('params', {})), suffix)
        checkpoints.append(
            {
                'checkpoint_id': f'S{idx}',
                'step_index': idx,
                'after_operator': variant['name'],
                'text': current_text,
                'mapper_result': mapper_result,
            }
        )
    return checkpoints


def _summarize_filter_attachment(
    filter_variant: dict[str, Any],
    checkpoint: dict[str, Any],
    evaluations: list[dict[str, Any]],
) -> dict[str, Any]:
    keep_count = sum(1 for item in evaluations if item['keep'])
    drop_count = sum(1 for item in evaluations if not item['keep'])
    total = len(evaluations)
    keep_rate = keep_count / total if total else 0.0
    value_key = _resolve_status_value_key(filter_variant['name'], dict(filter_variant.get('params', {})))
    values = [
        item['stats'].get(value_key)
        for item in evaluations
        if value_key is not None and isinstance(item.get('stats', {}).get(value_key), (int, float))
    ]
    balanced_support = min(keep_count, drop_count)
    return {
        'filter_name': filter_variant['name'],
        'filter_params': dict(filter_variant.get('params', {})),
        'checkpoint_id': checkpoint['checkpoint_id'],
        'attach_after_step': checkpoint['step_index'],
        'attach_after_operator': checkpoint['after_operator'],
        'support_records': total,
        'keep_count': keep_count,
        'drop_count': drop_count,
        'keep_rate': round(keep_rate, 6),
        'drop_rate': round(1.0 - keep_rate, 6),
        'balanced_support': balanced_support,
        'status_value_key': value_key,
        'status_value_mean': round(mean(values), 6) if values else None,
        'status_value_min': round(min(values), 6) if values else None,
        'status_value_max': round(max(values), 6) if values else None,
        'selection_score': (
            1 if keep_count > 0 and drop_count > 0 else 0,
            balanced_support,
            total,
            checkpoint['step_index'],
        ),
    }


def _select_filter_attachments(
    ordered_mappers: list[dict[str, Any]],
    filter_variants: list[dict[str, Any]],
    support_records: list[dict[str, Any]],
    min_filter_support: int,
    max_filters_per_workflow: int,
) -> list[dict[str, Any]]:
    if not support_records:
        return []

    per_filter_best: list[dict[str, Any]] = []
    for filter_variant in filter_variants:
        best_summary = None
        for checkpoint_idx in range(1, len(ordered_mappers) + 1):
            evaluations = []
            for record in support_records:
                checkpoints = _replay_mapper_checkpoints(record, ordered_mappers[:checkpoint_idx])
                checkpoint = checkpoints[-1]
                suffix = _infer_suffix(record)
                try:
                    evaluation = _evaluate_filter(
                        filter_variant['name'],
                        checkpoint['text'],
                        dict(filter_variant.get('params', {})),
                        suffix,
                    )
                except Exception as exc:
                    evaluation = {
                        'keep': False,
                        'status': 'ERROR',
                        'stats': {},
                        'error': f'{type(exc).__name__}: {exc}',
                    }
                evaluations.append(evaluation)

            if len(evaluations) < min_filter_support:
                continue
            summary = _summarize_filter_attachment(filter_variant, checkpoint, evaluations)
            if best_summary is None or summary['selection_score'] > best_summary['selection_score']:
                best_summary = summary

        if best_summary is not None:
            per_filter_best.append(best_summary)

    per_filter_best.sort(
        key=lambda row: (
            -row['selection_score'][0],
            -row['selection_score'][1],
            -row['selection_score'][2],
            -row['attach_after_step'],
            row['filter_name'],
        )
    )
    return per_filter_best[:max_filters_per_workflow]


def _materialize_variants(
    workflow_id: str,
    ordered_mappers: list[dict[str, Any]],
    attachments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    mapper_names = [variant['name'] for variant in ordered_mappers]
    variants = [
        {
            'workflow_variant_id': f'{workflow_id}__base',
            'variant_type': 'mapper_only',
            'operator_sequence': mapper_names,
        }
    ]
    for idx, attachment in enumerate(attachments, start=1):
        attach_after_step = int(attachment['attach_after_step'])
        sequence = [
            *mapper_names[:attach_after_step],
            attachment['filter_name'],
            *mapper_names[attach_after_step:],
        ]
        variants.append(
            {
                'workflow_variant_id': f'{workflow_id}__filter_{idx:02d}',
                'variant_type': 'single_filter_attachment',
                'operator_sequence': sequence,
                'filter_name': attachment['filter_name'],
                'attach_after_step': attach_after_step,
                'attach_after_operator': attachment['attach_after_operator'],
                'filter_params': attachment['filter_params'],
            }
        )
    return variants


def main() -> None:
    parser = argparse.ArgumentParser(
        description='Materialize benchmark-ready workflow drafts by ordering mapper workflows and attaching supported filters.'
    )
    parser.add_argument('--domains-config', default='configs/domains.yaml')
    parser.add_argument('--workflow-mining-dir', default='data/processed/workflow_mining')
    parser.add_argument('--filtered-path', default='data/processed/domain_filtered/all.jsonl')
    parser.add_argument('--output-dir', default='data/processed/workflow_library')
    parser.add_argument('--max-support-records', type=int, default=128)
    parser.add_argument('--min-filter-support', type=int, default=5)
    parser.add_argument('--max-filters-per-workflow', type=int, default=3)
    args = parser.parse_args()

    root = ROOT
    domains_cfg = load_domains_config(root / args.domains_config)
    plan = build_domain_execution_plan(domains_cfg)
    workflow_mining_dir = (root / args.workflow_mining_dir).resolve()
    filtered_path = (root / args.filtered_path).resolve()
    output_dir = (root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if not filtered_path.exists():
        raise SystemExit(f'filtered corpus not found: {filtered_path}')
    if not workflow_mining_dir.exists():
        raise SystemExit(f'workflow mining dir not found: {workflow_mining_dir}')

    records_by_domain: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in iter_jsonl(filtered_path):
        domain = record.get('domain')
        if domain:
            records_by_domain[str(domain)].append(record)

    summary_rows: list[dict[str, Any]] = []
    global_yaml = {'domains': {}}

    for domain_dir in sorted(path for path in workflow_mining_dir.iterdir() if path.is_dir()):
        domain = domain_dir.name
        workflow_rows = _workflow_rows_for_domain(domain_dir)
        if not workflow_rows:
            continue

        domain_records = records_by_domain.get(domain, [])
        ordered_filter_variants = _domain_filter_variants(domain, plan)
        domain_yaml = {'domain': domain, 'workflows': []}
        attachment_rows: list[dict[str, Any]] = []
        variant_rows: list[dict[str, Any]] = []

        for row in workflow_rows:
            workflow_id = str(row['workflow_id'])
            operator_set = _parse_operator_set(str(row['operators']))
            ordered_mappers = _ordered_mapper_sequence(domain, operator_set, plan)
            support_records = _supporting_records(
                domain_records,
                operator_set,
                max_records=args.max_support_records,
            )
            attachments = _select_filter_attachments(
                ordered_mappers=ordered_mappers,
                filter_variants=ordered_filter_variants,
                support_records=support_records,
                min_filter_support=args.min_filter_support,
                max_filters_per_workflow=args.max_filters_per_workflow,
            )
            variants = _materialize_variants(workflow_id, ordered_mappers, attachments)
            recommended_variant = variants[1] if len(variants) > 1 else variants[0]

            for attachment in attachments:
                attachment_rows.append(
                    {
                        'domain': domain,
                        'workflow_id': workflow_id,
                        'mapper_sequence': ' -> '.join(variant['name'] for variant in ordered_mappers),
                        **{k: v for k, v in attachment.items() if k != 'selection_score'},
                    }
                )

            for variant in variants:
                variant_rows.append(
                    {
                        'domain': domain,
                        'workflow_id': workflow_id,
                        'workflow_variant_id': variant['workflow_variant_id'],
                        'variant_type': variant['variant_type'],
                        'operator_sequence': ' -> '.join(variant['operator_sequence']),
                        'length': len(variant['operator_sequence']),
                        'filter_name': variant.get('filter_name'),
                        'attach_after_step': variant.get('attach_after_step'),
                    }
                )

            domain_yaml['workflows'].append(
                {
                    'workflow_id': workflow_id,
                    'family_id': row.get('family_id'),
                    'selection_source': row.get('selection_source', 'bottom_up_exact_signature'),
                    'support': int(row.get('support', 0) or 0),
                    'support_ratio': float(row.get('support_ratio', 0.0) or 0.0),
                    'mapper_operator_set': operator_set,
                    'ordered_mapper_sequence': [variant['name'] for variant in ordered_mappers],
                    'support_records_used_for_filter_attachment': len(support_records),
                    'recommended_filter_attachments': [
                        {k: v for k, v in attachment.items() if k != 'selection_score'} for attachment in attachments
                    ],
                    'workflow_variants': variants,
                    'recommended_workflow_variant_id': recommended_variant['workflow_variant_id'],
                    'recommended_operator_sequence': recommended_variant['operator_sequence'],
                    'curation_status': 'draft_workflow_ready_for_threshold_and_prompt_curation',
                }
            )

            summary_rows.append(
                {
                    'domain': domain,
                    'workflow_id': workflow_id,
                    'support': int(row.get('support', 0) or 0),
                    'mapper_length': len(ordered_mappers),
                    'num_filter_attachments': len(attachments),
                    'num_materialized_variants': len(variants),
                    'recommended_variant_type': recommended_variant['variant_type'],
                    'recommended_workflow_variant_id': recommended_variant['workflow_variant_id'],
                }
            )

        global_yaml['domains'][domain] = domain_yaml
        domain_out_dir = output_dir / domain
        domain_out_dir.mkdir(parents=True, exist_ok=True)
        with (domain_out_dir / 'workflow_library.yaml').open('w', encoding='utf-8') as f:
            yaml.safe_dump(domain_yaml, f, sort_keys=False, allow_unicode=True)
        pd.DataFrame(variant_rows).to_csv(domain_out_dir / 'workflow_variants.csv', index=False)
        pd.DataFrame(attachment_rows).to_csv(domain_out_dir / 'filter_attachments.csv', index=False)

    with (output_dir / 'workflow_library.yaml').open('w', encoding='utf-8') as f:
        yaml.safe_dump(global_yaml, f, sort_keys=False, allow_unicode=True)
    pd.DataFrame(summary_rows).to_csv(output_dir / 'workflow_library_summary.csv', index=False)

    print(f'wrote workflow library -> {output_dir}')


if __name__ == '__main__':
    main()
