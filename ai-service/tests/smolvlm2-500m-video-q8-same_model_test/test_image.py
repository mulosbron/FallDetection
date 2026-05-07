"""
GGUF VLM fall detection evaluation — SmolVLM2-500M-Video-Instruct (Q8) test_image.py stylenda:
  - log file under logs/
  - terminal summary + confusion matrix
  - fall_detection_results.csv (Image, True Label, Predicted Label, Predicted Text)
  - results/<timestamp>/evaluation_report.txt (English, readable)
  - metrics_summary.json, prediction_details.csv (full details)

Default dataset: tests/dataset (all harness folders use the same dataset).

Run example (from ai-service root, service running):
  python tests/smolvlm2-500m-video-q8_model_test/test_image.py \\
    --endpoint http://localhost:8200/v1/inference/fall-detection
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import mimetypes
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from metrics import (
    build_json_summary,
    build_metrics,
    format_evaluation_report_tr,
)

SUPPORTED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff"}
SCRIPT_DIR = Path(__file__).resolve().parent
# Shared image set: tests/dataset (Q8/F16 same folder).
_SHARED_DATASET_ROOT = (SCRIPT_DIR.parent / "dataset").resolve()


@dataclass
class RowDetail:
    filename: str
    image_path: str
    true_label: int
    predicted_label: int | None
    prediction_text: str
    raw_output: str
    latency_ms: int | None
    status: str


def setup_logging() -> Path:
    log_dir = SCRIPT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"vlm_eval_{ts}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )
    print(f"Log file: {log_file}")
    return log_file


def list_images(folder: Path) -> list[Path]:
    if not folder.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")
    files = [
        p
        for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return sorted(files)


def _mime_for_image(path: Path) -> str:
    mime, _ = mimetypes.guess_type(path.name)
    if mime and mime.startswith("image/"):
        return mime
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".bmp": "image/bmp",
        ".tiff": "image/tiff",
    }.get(ext, "image/jpeg")


def normalize_prediction(payload: dict[str, Any]) -> tuple[int | None, str, str]:
    result_field = str(payload.get("result", "")).strip().lower()
    raw_output = str(payload.get("raw_output", "")).strip()
    if result_field == "fall_detected":
        return 0, "fall_detected", raw_output
    if result_field == "no_fall":
        return 1, "no_fall", raw_output
    merged = f"{result_field} {raw_output}".lower()
    if "fall_detected" in merged and "no_fall" not in merged:
        return 0, "fall_detected", raw_output
    if "no_fall" in merged:
        return 1, "no_fall", raw_output
    if "yes" in merged and "no" not in merged:
        return 0, "yes", raw_output
    if "no" in merged:
        return 1, "no", raw_output
    return None, "invalid", raw_output


def call_inference(
    endpoint: str,
    image_path: Path,
    timeout_seconds: int,
    prompt: str | None,
) -> dict[str, Any]:
    mime = _mime_for_image(image_path)
    with image_path.open("rb") as file_handle:
        files = {"file": (image_path.name, file_handle, mime)}
        data: dict[str, str] = {}
        if prompt:
            data["prompt"] = prompt
        response = requests.post(
            endpoint, files=files, data=data, timeout=timeout_seconds
        )
    if not response.ok:
        logging.error(
            "API %s: %s",
            response.status_code,
            (response.text or "")[:2500],
        )
    response.raise_for_status()
    return response.json()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="GGUF VLM fall detection test (image multipart). SmolVLM2-500M test_image.py style output."
    )
    p.add_argument(
        "--falling-0-dir",
        type=str,
        default=str(_SHARED_DATASET_ROOT / "falling_0"),
        help="Class 0 (falling) folder (default: tests/dataset)",
    )
    p.add_argument(
        "--falling-1-dir",
        type=str,
        default=str(_SHARED_DATASET_ROOT / "falling_1"),
        help="Class 1 (random) folder (default: tests/dataset)",
    )
    p.add_argument(
        "--endpoint",
        type=str,
        default="http://localhost:8000/v1/inference/fall-detection",
        help="POST /v1/inference/fall-detection (multipart)",
    )
    p.add_argument("--prompt", type=str, default=None, help="Optional form prompt")
    p.add_argument("--timeout-seconds", type=int, default=300)
    p.add_argument(
        "--max-per-class",
        type=int,
        default=0,
        help="Max samples per class (0=all)",
    )
    return p.parse_args()


def print_first_csv_rows(csv_path: Path, n: int = 10) -> None:
    try:
        with csv_path.open(encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = []
            for i, row in enumerate(reader):
                rows.append(row)
                if i >= n:
                    break
    except OSError as e:
        print(f"CSV could not be read: {e}")
        return
    print(f"\nCSV first rows (max {n + 1} satir): {csv_path.name}")
    for row in rows:
        print(" ", row)


def main() -> int:
    args = parse_args()
    log_path = setup_logging()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = SCRIPT_DIR / "results" / ts
    run_dir.mkdir(parents=True, exist_ok=True)

    falling_0 = Path(args.falling_0_dir)
    falling_1 = Path(args.falling_1_dir)
    if not falling_0.is_absolute():
        falling_0 = (SCRIPT_DIR / falling_0).resolve()
    else:
        falling_0 = falling_0.resolve()
    if not falling_1.is_absolute():
        falling_1 = (SCRIPT_DIR / falling_1).resolve()
    else:
        falling_1 = falling_1.resolve()

    class0_files = list_images(falling_0)
    class1_files = list_images(falling_1)
    if args.max_per_class > 0:
        class0_files = class0_files[: args.max_per_class]
        class1_files = class1_files[: args.max_per_class]

    samples = [(0, p) for p in class0_files] + [(1, p) for p in class1_files]
    n_total = len(samples)

    print(
        f"\nTotal samples: {n_total} (falling={len(class0_files)}, random={len(class1_files)})"
    )
    print(f"Output folder: {run_dir}")
    logging.info("Run started: %s sample, endpoint=%s", n_total, args.endpoint)

    details: list[RowDetail] = []
    y_true: list[int] = []
    y_pred: list[int] = []
    successful = 0

    results_csv = run_dir / "fall_detection_results.csv"
    with results_csv.open("w", newline="", encoding="utf-8") as rf:
        w = csv.writer(rf)
        w.writerow(["Image", "True Label", "Predicted Label", "Predicted Text"])

    for i, (true_label, image_path) in enumerate(samples, start=1):
        fn = image_path.name
        pred_text_for_csv = ""
        pred_label: int | None = None
        try:
            started = time.perf_counter()
            payload = call_inference(
                args.endpoint,
                image_path,
                args.timeout_seconds,
                args.prompt,
            )
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            pred_label, pred_txt, raw_out = normalize_prediction(payload)
            lat = payload.get("latency_ms", elapsed_ms)
            st = "ok" if pred_label is not None else "invalid_prediction"
            pred_text_for_csv = payload.get("result", pred_txt) or pred_txt

            details.append(
                RowDetail(
                    filename=fn,
                    image_path=str(image_path),
                    true_label=true_label,
                    predicted_label=pred_label,
                    prediction_text=pred_txt,
                    raw_output=raw_out,
                    latency_ms=int(lat) if isinstance(lat, (int, float)) else None,
                    status=st,
                )
            )
            if pred_label is not None:
                y_true.append(true_label)
                y_pred.append(pred_label)
                successful += 1
                with results_csv.open("a", newline="", encoding="utf-8") as rf:
                    csv.writer(rf).writerow(
                        [fn, true_label, pred_label, pred_text_for_csv]
                    )
            else:
                with results_csv.open("a", newline="", encoding="utf-8") as rf:
                    csv.writer(rf).writerow([fn, true_label, "", pred_txt])
        except Exception as exc:
            logging.exception("Error: %s", fn)
            details.append(
                RowDetail(
                    filename=fn,
                    image_path=str(image_path),
                    true_label=true_label,
                    predicted_label=None,
                    prediction_text="error",
                    raw_output=str(exc),
                    latency_ms=None,
                    status="request_error",
                )
            )
            with results_csv.open("a", newline="", encoding="utf-8") as rf:
                csv.writer(rf).writerow([fn, true_label, "", f"error: {exc}"])

        if i % 50 == 0 or i == n_total:
            print(f"Progress: {i}/{n_total}")

    invalid_n = len([d for d in details if d.status != "ok"])
    metrics = build_metrics(y_true, y_pred) if y_true else {}
    summary = build_json_summary(
        ts,
        args.endpoint,
        len(class0_files),
        len(class1_files),
        n_total,
        len(y_true),
        invalid_n,
        metrics,
    )

    pred_details = run_dir / "prediction_details.csv"
    with pred_details.open("w", newline="", encoding="utf-8") as pf:
        dw = csv.writer(pf)
        dw.writerow(
            [
                "filename",
                "image_path",
                "true_label",
                "predicted_label",
                "prediction_text",
                "raw_output",
                "latency_ms",
                "status",
            ]
        )
        for d in details:
            dw.writerow(
                [
                    d.filename,
                    d.image_path,
                    d.true_label,
                    d.predicted_label,
                    d.prediction_text,
                    d.raw_output,
                    d.latency_ms,
                    d.status,
                ]
            )

    metrics_json = run_dir / "metrics_summary.json"
    with metrics_json.open("w", encoding="utf-8") as jf:
        json.dump(summary, jf, ensure_ascii=False, indent=2)

    report_path = run_dir / "evaluation_report.txt"
    if metrics:
        report_body = format_evaluation_report_tr(
            timestamp=ts,
            endpoint=args.endpoint,
            falling_0_dir=str(falling_0),
            falling_1_dir=str(falling_1),
            metrics=metrics,
            valid_predictions=len(y_true),
            invalid_predictions=invalid_n,
            samples_total=n_total,
        )
    else:
        report_body = (
            f"Metrics could not be calculated (no valid predictions).\n"
            f"invalid_predictions={invalid_n}, total={n_total}\n"
        )
    report_path.write_text(report_body, encoding="utf-8")

    # --- Terminal summary (SmolVLM2 style; ANALYSIS RESULTS) ---
    print("\n" + "=" * 50)
    print("ANALYSIS RESULTS")
    print("=" * 50)
    print(f"Total images: {n_total}")
    print(f"Successful predictions (for metrics): {successful}")
    if metrics:
        acc = metrics.get("accuracy", 0.0)
        cm = metrics.get("confusion_matrix", [[0, 0], [0, 0]])
        print(f"Accuracy: {acc:.2%}")
        print("\nConfusion matrix  cm[actual][prediction]  (0=falling, 1=random)")
        print("             Pred_0    Pred_1")
        print(f"  Actual_0   {cm[0][0]:7d}   {cm[0][1]:7d}")
        print(f"  Actual_1   {cm[1][0]:7d}   {cm[1][1]:7d}")
        br = metrics.get("binary_metrics_positive_class_0", {})
        print(f"\nF1 (falling = positive class): {br.get('f1', 0):.4f}")
    print(f"\nFull text report: {report_path}")
    print(f"SmolVLM2 style CSV: {results_csv}")
    print(f"Details CSV: {pred_details}")
    print(f"JSON: {metrics_json}")
    print(f"Log: {log_path}")

    print_first_csv_rows(results_csv, n=10)

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

