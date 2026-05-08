from __future__ import annotations

import re
from typing import Any

import editdistance

STOP_AWARE_RG_LAMBDA = 1.0
STOP_AWARE_RG_EPSILON = 1e-6


def normalize_status(value: Any) -> str:
    text = '' if value is None else str(value)
    return text.strip().upper()


def edit_distance(left: str, right: str) -> int:
    return int(editdistance.eval(left, right))


def normalize_text_for_match(value: Any) -> str:
    text = '' if value is None else str(value)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n(?:[ \t]*\n)+', '\n\n', text)
    return text.strip()


def normalize_text_for_norm_match(value: Any) -> str:
    text = '' if value is None else str(value)
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r' +([,.;:!?])', r'\1', text)
    text = re.sub(r'[ \t]+\n', '\n', text)
    text = re.sub(r'\n(?:[ \t]*\n)+', '\n\n', text)
    return text.strip()


def compute_recipe_metrics(
    *,
    input_text: Any,
    reference_status: Any,
    reference_text: Any,
    reference_text_full_run: Any = None,
    predicted_status: Any,
    predicted_clean_text: Any,
) -> dict[str, Any]:
    raw_input = '' if input_text is None else str(input_text)
    raw_reference = '' if reference_text is None else str(reference_text)
    raw_reference_full_run = '' if reference_text_full_run is None else str(reference_text_full_run)
    raw_prediction = '' if predicted_clean_text is None else str(predicted_clean_text)

    normalized_reference_status = normalize_status(reference_status)
    normalized_prediction_status = normalize_status(predicted_status)
    normalized_reference_text = normalize_text_for_match(raw_reference)
    normalized_prediction_text = normalize_text_for_match(raw_prediction)
    norm_reference_text = normalize_text_for_norm_match(raw_reference)
    norm_prediction_text = normalize_text_for_norm_match(raw_prediction)

    status_match = normalized_prediction_status == normalized_reference_status
    text_exact_match = raw_prediction == raw_reference
    normalized_text_exact_match = normalized_prediction_text == normalized_reference_text
    norm_text_exact_match = norm_prediction_text == norm_reference_text
    recipe_success = status_match and text_exact_match
    normalized_recipe_success = status_match and normalized_text_exact_match
    norm_recipe_success = status_match and norm_text_exact_match

    d_input = edit_distance(raw_input, raw_reference)
    d_pred_stop = edit_distance(raw_prediction, raw_reference)
    denominator = d_input + d_pred_stop + STOP_AWARE_RG_EPSILON
    drop_penalty = 0.0
    if normalized_reference_status == 'DROP' and raw_reference_full_run:
        d_pred_full = edit_distance(raw_prediction, raw_reference_full_run)
        drop_penalty = STOP_AWARE_RG_LAMBDA * float(d_pred_stop - d_pred_full)
    else:
        d_pred_full = None
    refinement_gain = (float(d_input - d_pred_stop) - drop_penalty) / denominator

    return {
        'normalized_reference_status': normalized_reference_status,
        'normalized_predicted_status': normalized_prediction_status,
        'normalized_reference_text': normalized_reference_text,
        'normalized_predicted_text': normalized_prediction_text,
        'norm_reference_text': norm_reference_text,
        'norm_predicted_text': norm_prediction_text,
        'status_match': status_match,
        'text_exact_match': text_exact_match,
        'normalized_text_exact_match': normalized_text_exact_match,
        'norm_text_exact_match': norm_text_exact_match,
        'recipe_success': recipe_success,
        'normalized_recipe_success': normalized_recipe_success,
        'norm_recipe_success': norm_recipe_success,
        'text_match': text_exact_match,
        'edit_distance_input_to_reference': d_input,
        'edit_distance_prediction_to_reference': d_pred_stop,
        'edit_distance_prediction_to_full_run_reference': d_pred_full,
        'reference_text_full_run': raw_reference_full_run,
        'stop_aware_rg_lambda': STOP_AWARE_RG_LAMBDA,
        'stop_aware_rg_epsilon': STOP_AWARE_RG_EPSILON,
        'refinement_gain': refinement_gain,
    }
