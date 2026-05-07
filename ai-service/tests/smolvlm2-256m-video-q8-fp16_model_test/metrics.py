"""Pure Python binary classification metrics (no sklearn)."""

from __future__ import annotations

from typing import Any


def safe_div(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_binary_metrics(tp: int, fp: int, fn: int, tn: int) -> dict[str, float]:
    precision = safe_div(tp, tp + fp)
    recall = safe_div(tp, tp + fn)
    f1 = safe_div(2 * precision * recall, precision + recall)
    accuracy = safe_div(tp + tn, tp + tn + fp + fn)
    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "accuracy": accuracy,
    }


def round_metrics(metrics: dict[str, float], digits: int = 6) -> dict[str, float]:
    return {k: round(v, digits) for k, v in metrics.items()}


def confusion_matrix_counts(y_true: list[int], y_pred: list[int]) -> list[list[int]]:
    """cm[actual][prediction], classes 0 and 1."""
    cm = [[0, 0], [0, 0]]
    for truth, pred in zip(y_true, y_pred):
        cm[truth][pred] += 1
    return cm


def build_metrics(y_true: list[int], y_pred: list[int]) -> dict[str, Any]:
    cm = confusion_matrix_counts(y_true, y_pred)
    support_0 = cm[0][0] + cm[0][1]
    support_1 = cm[1][0] + cm[1][1]
    total = support_0 + support_1

    cls0 = compute_binary_metrics(tp=cm[0][0], fp=cm[1][0], fn=cm[0][1], tn=cm[1][1])
    cls1 = compute_binary_metrics(tp=cm[1][1], fp=cm[0][1], fn=cm[1][0], tn=cm[0][0])
    binary = cls0

    macro = {
        "precision": (cls0["precision"] + cls1["precision"]) / 2,
        "recall": (cls0["recall"] + cls1["recall"]) / 2,
        "f1": (cls0["f1"] + cls1["f1"]) / 2,
        "accuracy": safe_div(cm[0][0] + cm[1][1], total),
    }
    weighted = {
        "precision": safe_div(
            cls0["precision"] * support_0 + cls1["precision"] * support_1, total
        ),
        "recall": safe_div(cls0["recall"] * support_0 + cls1["recall"] * support_1, total),
        "f1": safe_div(cls0["f1"] * support_0 + cls1["f1"] * support_1, total),
        "accuracy": safe_div(cm[0][0] + cm[1][1], total),
    }

    return {
        "accuracy": round(safe_div(cm[0][0] + cm[1][1], total), 6),
        "confusion_matrix": cm,
        "fp_class0_positive": cm[1][0],
        "fn_class0_positive": cm[0][1],
        "classification_report": {
            "class_0_falling": {**round_metrics(cls0), "support": support_0},
            "class_1_random": {**round_metrics(cls1), "support": support_1},
            "macro_avg": {**round_metrics(macro), "support": total},
            "weighted_avg": {**round_metrics(weighted), "support": total},
        },
        "binary_metrics_positive_class_0": round_metrics(binary),
    }


def build_json_summary(
    timestamp: str,
    endpoint: str,
    class0_n: int,
    class1_n: int,
    samples_total: int,
    valid_n: int,
    invalid_n: int,
    metrics: dict[str, Any],
) -> dict[str, Any]:
    return {
        "timestamp": timestamp,
        "endpoint": endpoint,
        "dataset": {
            "class0_falling_total": class0_n,
            "class1_random_total": class1_n,
            "samples_total": samples_total,
            "valid_predictions": valid_n,
            "invalid_predictions": invalid_n,
        },
        "label_mapping": {
            "0": "falling_person",
            "1": "random_image",
            "prediction_fall_detected": 0,
            "prediction_no_fall": 1,
        },
        "metrics": metrics,
    }


def format_evaluation_report_tr(
    *,
    timestamp: str,
    endpoint: str,
    falling_0_dir: str,
    falling_1_dir: str,
    metrics: dict[str, Any],
    valid_predictions: int,
    invalid_predictions: int,
    samples_total: int,
) -> str:
    """Human-readable report in English; includes confusion matrix glossary."""
    cm = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
    acc = metrics.get("accuracy", 0.0)
    br = metrics.get("binary_metrics_positive_class_0", {})
    cr = metrics.get("classification_report", {})
    c0 = cr.get("class_0_falling", {})
    c1 = cr.get("class_1_random", {})
    macro = cr.get("macro_avg", {})
    weighted = cr.get("weighted_avg", {})

    c00, c01 = cm[0][0], cm[0][1]
    c10, c11 = cm[1][0], cm[1][1]
    fp = metrics.get("fp_class0_positive", c10)
    fn = metrics.get("fn_class0_positive", c01)

    lines = [
        "=" * 60,
        "GGUF VLM FALL DETECTION — EVALUATION REPORT",
        "=" * 60,
        "",
        f"Timestamp (run): {timestamp}",
        f"API endpoint: {endpoint}",
        "",
        "DATA SOURCES",
        f"  Class 0 (falling): {falling_0_dir}",
        f"  Class 1 (random): {falling_1_dir}",
        "",
        "SAMPLE COUNTS",
        f"  Total processed: {samples_total}",
        f"  Valid predictions (used for metrics): {valid_predictions}",
        f"  Invalid / request errors: {invalid_predictions}",
        "",
        "--- CONFUSION MATRIX (cm[actual_label][prediction]) ---",
        '  Label 0 = "falling", Label 1 = "random"',
        "",
        "                Pred=0   Pred=1",
        f"  Actual=0 (falling)  {c00:6d}     {c01:6d}",
        f"  Actual=1 (random) {c10:6d}     {c11:6d}",
        "",
        "GLOSSARY",
        f"  Actual falling and predicted falling (correct): {c00}",
        f"  Actual falling and predicted random/no_fall (incorrect): {c01}  <- missed fall (FN)",
        f"  Actual random and predicted falling (incorrect): {c10}  <- false alarm (FP)",
        f"  Actual random and predicted no_fall (correct): {c11}",
        "",
        "ERROR SUMMARY (positive class = falling = 0)",
        f"  False Positive (FP): {fp}  — random, falling was considered",
        f"  False Negative (FN): {fn}  — falling, no_fall was classified",
        "",
        f"ACCURACY: {acc:.6f}  ({acc * 100:.2f}%)",
        "",
        "--- CLASS 0 (falling) ---",
        f"  precision: {c0.get('precision', 0):.6f}",
        f"  recall:    {c0.get('recall', 0):.6f}",
        f"  f1:        {c0.get('f1', 0):.6f}",
        f"  support:   {c0.get('support', 0)}",
        "",
        "--- CLASS 1 (random) ---",
        f"  precision: {c1.get('precision', 0):.6f}",
        f"  recall:    {c1.get('recall', 0):.6f}",
        f"  f1:        {c1.get('f1', 0):.6f}",
        f"  support:   {c1.get('support', 0)}",
        "",
        "--- AVERAGES ---",
        f"  macro F1:     {macro.get('f1', 0):.6f}",
        f"  weighted F1:  {weighted.get('f1', 0):.6f}",
        f"  binary F1 (class0=falling): {br.get('f1', 0):.6f}",
        "",
        "--- QUICK INTERPRETATION ---",
        "In a balanced dataset (for example 200/200), accuracy around ~50% can happen",
        "when the model keeps predicting the same class (often prediction=1 / no_fall);",
        "this does not indicate a good model. If FN is high, falls are often missed.",
        "",
        "=" * 60,
    ]
    return "\n".join(lines)

