from __future__ import annotations

import re
import unicodedata
from typing import Any


_WHITESPACE_RE = re.compile(r'\s+')
_ZERO_WIDTH_RE = re.compile(r'[\u200b\u200c\u200d\ufeff]')


def canonicalize_text(value: Any) -> str:
    text = '' if value is None else str(value)
    text = unicodedata.normalize('NFKC', text)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = _ZERO_WIDTH_RE.sub('', text)
    text = text.strip()
    text = _WHITESPACE_RE.sub(' ', text)
    return text


def normalize_status(value: Any) -> str:
    return canonicalize_text(value).upper()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)

    if len(left) < len(right):
        left, right = right, left

    previous = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current[right_index - 1] + 1
            delete_cost = previous[right_index] + 1
            replace_cost = previous[right_index - 1] + (left_char != right_char)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def compute_workflow_metrics(
    *,
    input_text: Any,
    reference_status: Any,
    reference_text: Any,
    predicted_status: Any,
    predicted_clean_text: Any,
) -> dict[str, Any]:
    canonical_input = canonicalize_text(input_text)
    canonical_reference = canonicalize_text(reference_text)
    canonical_prediction = canonicalize_text(predicted_clean_text)
    normalized_reference_status = normalize_status(reference_status)
    normalized_prediction_status = normalize_status(predicted_status)

    status_match = normalized_prediction_status == normalized_reference_status
    text_match = canonical_prediction == canonical_reference
    workflow_success = status_match and text_match

    d_input = edit_distance(canonical_input, canonical_reference)
    d_pred = edit_distance(canonical_prediction, canonical_reference)
    if d_input == 0:
        refinement_gain = 1.0 if d_pred == 0 else 0.0
    else:
        refinement_gain = clamp((d_input - d_pred) / d_input, -1.0, 1.0)

    return {
        'canonical_input_text': canonical_input,
        'canonical_reference_text': canonical_reference,
        'canonical_predicted_clean_text': canonical_prediction,
        'normalized_reference_status': normalized_reference_status,
        'normalized_predicted_status': normalized_prediction_status,
        'status_match': status_match,
        'text_match': text_match,
        'workflow_success': workflow_success,
        'edit_distance_input_to_reference': d_input,
        'edit_distance_prediction_to_reference': d_pred,
        'refinement_gain': refinement_gain,
    }
