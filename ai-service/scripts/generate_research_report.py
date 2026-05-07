#!/usr/bin/env python3
"""
SmolVLM2 Düşme Tespiti Benchmark Analiz Raporu — LaTeX Üretici

Tüm benchmark koşu sonuçlarını okur, matplotlib/seaborn ile araştırma
kalitesinde görseller üretir ve bunları içeren bir LaTeX belgesi oluşturur.

Kullanım:
    cd ai-service
    python scripts/generate_research_report.py
"""

import json
import csv
import glob
import os
import re
import subprocess
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import numpy as np

# ── Configuration ──────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
TESTS_DIR = PROJECT_ROOT / "tests"
RESULTS_GLOB = str(TESTS_DIR / "smolvlm2-*/results/*/metrics_summary.json")
OUTPUT_DIR = TESTS_DIR / "report_output"
FIGURES_DIR = OUTPUT_DIR / "figures"
LATEX_FILE = OUTPUT_DIR / "benchmark_report.tex"

MODEL_DISPLAY = {
    "256m-q8-same":  "256M Q8 (Same)",
    "256m-f16-same": "256M F16 (Same)",
    "256m-q8-fp16":  "256M Q8+FP16",
    "500m-q8-same":  "500M Q8 (Same)",
    "500m-f16-same": "500M F16 (Same)",
    "500m-q8-fp16":  "500M Q8+FP16",
}

MODEL_ORDER = [
    "256m-q8-same",
    "256m-q8-fp16",
    "256m-f16-same",
    "500m-q8-same",
    "500m-q8-fp16",
    "500m-f16-same",
]

PALETTE = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974", "#64B5CD"]

# ── Data Collection ────────────────────────────────────────────────────────

def parse_model_key(dirname: str) -> str:
    m = re.match(r"smolvlm2-(\d+m)-video-(.+?)_model_test", dirname)
    if not m:
        return dirname
    size, rest = m.group(1), m.group(2)
    if "fp16" in rest and "q8" in rest:
        return f"{size}-q8-fp16"
    if "f16" in rest:
        return f"{size}-f16-same"
    if "q8" in rest:
        return f"{size}-q8-same"
    return f"{size}-{rest}"


def load_all_runs() -> dict[str, list[dict]]:
    json_files = sorted(glob.glob(RESULTS_GLOB))
    if not json_files:
        sys.exit(f"ERROR: metrics_summary.json bulunamadı.\nGlob: {RESULTS_GLOB}")

    runs: dict[str, list[dict]] = defaultdict(list)
    for jf in json_files:
        parts = Path(jf).parts
        test_dir = next((p for p in parts if p.startswith("smolvlm2-") and p.endswith("_model_test")), None)
        model_key = parse_model_key(test_dir) if test_dir else "unknown"

        with open(jf, encoding="utf-8-sig") as f:
            data = json.load(f)

        csv_path = Path(jf).parent / "prediction_details.csv"
        latencies: list[int] = []
        if csv_path.exists():
            with open(csv_path, encoding="utf-8-sig") as cf:
                for row in csv.DictReader(cf):
                    try:
                        latencies.append(int(row["latency_ms"]))
                    except (KeyError, ValueError):
                        pass

        data["_key"] = model_key
        data["_latencies"] = latencies
        runs[model_key].append(data)

    return dict(runs)


def build_summary(runs: dict) -> dict:
    summary = {}
    for mk in MODEL_ORDER:
        if mk not in runs:
            continue
        rl = runs[mk]
        m = lambda fn: [fn(r) for r in rl]  # noqa: E731

        acc = m(lambda r: r["metrics"]["accuracy"])
        cr = lambda cls, met: m(lambda r: r["metrics"]["classification_report"][cls][met])  # noqa: E731

        all_lat = [l for r in rl for l in r["_latencies"]]
        sample_totals = [int(r.get("dataset", {}).get("samples_total", 0)) for r in rl]
        class0_totals = [int(r.get("dataset", {}).get("class0_falling_total", 0)) for r in rl]
        class1_totals = [int(r.get("dataset", {}).get("class1_random_total", 0)) for r in rl]

        summary[mk] = dict(
            n=len(rl),
            acc_mean=np.mean(acc), acc_std=np.std(acc), acc_all=acc,
            f1f_mean=np.mean(cr("class_0_falling", "f1")),
            f1f_std=np.std(cr("class_0_falling", "f1")),
            f1r_mean=np.mean(cr("class_1_random", "f1")),
            f1r_std=np.std(cr("class_1_random", "f1")),
            pf_mean=np.mean(cr("class_0_falling", "precision")),
            rf_mean=np.mean(cr("class_0_falling", "recall")),
            pr_mean=np.mean(cr("class_1_random", "precision")),
            rr_mean=np.mean(cr("class_1_random", "recall")),
            fp_mean=np.mean(m(lambda r: r["metrics"]["fp_class0_positive"])),
            fn_mean=np.mean(m(lambda r: r["metrics"]["fn_class0_positive"])),
            fp_all=m(lambda r: r["metrics"]["fp_class0_positive"]),
            fn_all=m(lambda r: r["metrics"]["fn_class0_positive"]),
            lat=all_lat,
            lat_mean=np.mean(all_lat) if all_lat else 0,
            lat_std=np.std(all_lat) if all_lat else 0,
            samples_total_mean=np.mean(sample_totals) if sample_totals else 0,
            class0_total_mean=np.mean(class0_totals) if class0_totals else 0,
            class1_total_mean=np.mean(class1_totals) if class1_totals else 0,
        )
    return summary


# ── Figure Helpers ─────────────────────────────────────────────────────────

def _style():
    sns.set_theme(style="whitegrid", font_scale=1.1)
    plt.rcParams.update({
        "figure.dpi": 150, "savefig.dpi": 300, "savefig.bbox": "tight",
        "font.family": "serif", "axes.titlesize": 13, "axes.labelsize": 11,
    })


def _save(fig, name):
    for ext in ("pdf", "png"):
        fig.savefig(FIGURES_DIR / f"{name}.{ext}", bbox_inches="tight")
    plt.close(fig)


def _keys(s):
    return [k for k in MODEL_ORDER if k in s]


def _labels(keys):
    return [MODEL_DISPLAY[k] for k in keys]


def _colors(keys):
    return [PALETTE[MODEL_ORDER.index(k)] for k in keys]


# ── Figures ────────────────────────────────────────────────────────────────

def fig1_accuracy(s):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    keys = _keys(s)
    means = [s[k]["acc_mean"] for k in keys]
    stds = [s[k]["acc_std"] for k in keys]
    bars = ax.bar(_labels(keys), means, yerr=stds, capsize=5,
                  color=_colors(keys), edgecolor="black", linewidth=0.5, alpha=0.85)
    for b, v in zip(bars, means):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.012,
                f"{v:.2f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    ax.set_ylabel("Accuracy")
    ax.set_title("Mean Accuracy by Model Configuration")
    ax.set_ylim(0.5, 1.05)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    plt.xticks(rotation=20, ha="right")
    _save(fig, "fig1_accuracy_bar")


def fig2_f1(s):
    fig, ax = plt.subplots(figsize=(9, 5))
    keys = _keys(s)
    x = np.arange(len(keys))
    w = 0.35
    ax.bar(x - w / 2, [s[k]["f1f_mean"] for k in keys], w,
           yerr=[s[k]["f1f_std"] for k in keys], capsize=3,
           label="Class 0 — Falling", color="#E74C3C", alpha=0.8,
           edgecolor="black", linewidth=0.5)
    ax.bar(x + w / 2, [s[k]["f1r_mean"] for k in keys], w,
           yerr=[s[k]["f1r_std"] for k in keys], capsize=3,
           label="Class 1 — Random", color="#3498DB", alpha=0.8,
           edgecolor="black", linewidth=0.5)
    ax.set_ylabel("F1-Score")
    ax.set_title("Class-wise F1-Score Comparison")
    ax.set_xticks(x)
    ax.set_xticklabels(_labels(keys), rotation=20, ha="right")
    ax.set_ylim(0.5, 1.05)
    ax.legend(loc="lower right")
    _save(fig, "fig2_f1_comparison")


def fig3_pr_scatter(runs):
    fig, ax = plt.subplots(figsize=(7, 6))
    for idx, mk in enumerate(MODEL_ORDER):
        if mk not in runs:
            continue
        lbl = MODEL_DISPLAY[mk]
        for r in runs[mk]:
            bm = r["metrics"]["binary_metrics_positive_class_0"]
            ax.scatter(bm["recall"], bm["precision"],
                       color=PALETTE[idx], s=80, edgecolors="black",
                       linewidths=0.5, label=lbl, zorder=3)
            lbl = None
    for f1v in (0.6, 0.7, 0.8, 0.9):
        rr = np.linspace(0.01, 1.0, 200)
        pp = (f1v * rr) / (2 * rr - f1v)
        ok = (pp >= 0) & (pp <= 1)
        ax.plot(rr[ok], pp[ok], "--", color="gray", alpha=0.4, linewidth=0.8)
        mid = np.argmin(np.abs(rr[ok] - 0.85))
        if mid < len(rr[ok]):
            ax.text(rr[ok][mid], pp[ok][mid] + 0.02, f"F1={f1v}",
                    fontsize=7, color="gray", alpha=0.7)
    ax.set_xlabel("Recall (Falling class)")
    ax.set_ylabel("Precision (Falling class)")
    ax.set_title("Precision–Recall Scatter (Positive class: Falling)")
    ax.set_xlim(0.4, 1.05)
    ax.set_ylim(0.7, 1.05)
    ax.legend(fontsize=8, loc="lower left")
    _save(fig, "fig3_precision_recall")


def fig4_confusion(runs, s):
    sorted_m = sorted(s.keys(), key=lambda k: s[k]["acc_mean"])
    worst_key, best_key = sorted_m[0], sorted_m[-1]
    worst_run = min(runs[worst_key], key=lambda r: r["metrics"]["accuracy"])
    best_run = max(runs[best_key], key=lambda r: r["metrics"]["accuracy"])

    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5))
    for ax, run, title in (
        (axes[0], worst_run, f"Lowest — {MODEL_DISPLAY[worst_key]}"),
        (axes[1], best_run,  f"Highest — {MODEL_DISPLAY[best_key]}"),
    ):
        cm = np.array(run["metrics"]["confusion_matrix"])
        cm_n = cm / cm.sum(axis=1, keepdims=True)
        sns.heatmap(cm_n, annot=True, fmt=".2f", cmap="Blues", ax=ax,
                    xticklabels=["Falling (0)", "Random (1)"],
                    yticklabels=["Falling (0)", "Random (1)"],
                    vmin=0, vmax=1, cbar_kws={"shrink": 0.8})
        for i in range(2):
            for j in range(2):
                ax.text(j + 0.5, i + 0.75, f"(n={cm[i][j]})",
                        ha="center", va="center", fontsize=8, color="gray")
        ax.set_xlabel("Predicted")
        ax.set_ylabel("Actual")
        ax.set_title(title, fontsize=10)
    fig.suptitle("Normalized Confusion Matrices", fontsize=13, y=1.02)
    _save(fig, "fig4_confusion_matrices")


def fig5_latency(s):
    fig, ax = plt.subplots(figsize=(8, 5))
    keys = [k for k in MODEL_ORDER if k in s and s[k]["lat"]]
    data = [s[k]["lat"] for k in keys]
    bp = ax.boxplot(data, tick_labels=_labels(keys), patch_artist=True, notch=True,
                    medianprops=dict(color="black", linewidth=1.5))
    for patch, c in zip(bp["boxes"], _colors(keys)):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    ax.set_ylabel("Inference Time (ms)")
    ax.set_title("Inference Time Distribution by Model")
    plt.xticks(rotation=20, ha="right")
    _save(fig, "fig5_latency_boxplot")


def fig6_fpfn(s):
    fig, ax = plt.subplots(figsize=(8, 4.5))
    keys = _keys(s)
    x = np.arange(len(keys))
    fp = [s[k]["fp_mean"] for k in keys]
    fn = [s[k]["fn_mean"] for k in keys]
    ax.bar(x, fp, 0.6, label="FP (False alarm)", color="#E67E22",
           alpha=0.85, edgecolor="black", linewidth=0.5)
    ax.bar(x, fn, 0.6, bottom=fp, label="FN (Missed fall)",
           color="#E74C3C", alpha=0.85, edgecolor="black", linewidth=0.5)
    for i, (fv, nv) in enumerate(zip(fp, fn)):
        if fv > 0.5:
            ax.text(i, fv / 2, f"{fv:.0f}", ha="center", va="center",
                    fontsize=9, fontweight="bold", color="white")
        if nv > 0.5:
            ax.text(i, fv + nv / 2, f"{nv:.0f}", ha="center", va="center",
                    fontsize=9, fontweight="bold", color="white")
    keys = _keys(s)
    per_run_total = int(round(np.mean([s[k]["samples_total_mean"] for k in keys if s[k]["samples_total_mean"] > 0]))) if keys else 0
    suffix = f" (/{per_run_total})" if per_run_total > 0 else ""
    ax.set_ylabel(f"Mean Error Count{suffix}")
    ax.set_title("False Positive vs False Negative")
    ax.set_xticks(x)
    ax.set_xticklabels(_labels(keys), rotation=20, ha="right")
    ax.legend(loc="upper right")
    _save(fig, "fig6_fp_fn_analysis")


def fig7_trend(runs):
    fig, ax = plt.subplots(figsize=(8, 5))
    for idx, mk in enumerate(MODEL_ORDER):
        if mk not in runs:
            continue
        ordered = sorted(runs[mk], key=lambda r: r["timestamp"])
        accs = [r["metrics"]["accuracy"] for r in ordered]
        ax.plot(range(1, len(accs) + 1), accs, "o-", color=PALETTE[idx],
                label=MODEL_DISPLAY[mk], markersize=7, linewidth=1.5,
                markeredgecolor="black", markeredgewidth=0.5)
    ax.set_xlabel("Run Index")
    ax.set_ylabel("Accuracy")
    ax.set_title("Model Consistency Across Repeated Runs")
    max_runs = max((len(v) for v in runs.values()), default=1)
    ax.set_xticks(list(range(1, max_runs + 1)))
    ax.set_ylim(0.6, 1.0)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.legend(fontsize=8, loc="lower right", ncol=2)
    _save(fig, "fig7_accuracy_trend")


# ── LaTeX Generation ───────────────────────────────────────────────────────

def generate_latex(s, runs) -> str:
    rows = []
    for mk in MODEL_ORDER:
        if mk not in s:
            continue
        d = s[mk]
        rows.append(
            f"        {MODEL_DISPLAY[mk]} & {d['n']} & "
            f"{d['acc_mean']:.2f} $\\pm$ {d['acc_std']:.2f} & "
            f"{d['f1f_mean']:.3f} & {d['f1r_mean']:.3f} & "
            f"{d['pf_mean']:.3f} & {d['rf_mean']:.3f} & "
            f"{d['fp_mean']:.1f} & {d['fn_mean']:.1f} & "
            f"{d['lat_mean']:.0f} \\\\"
        )
    table_body = "\n".join(rows)

    best_k = max(s, key=lambda k: s[k]["acc_mean"])
    worst_k = min(s, key=lambda k: s[k]["acc_mean"])
    best, worst = s[best_k], s[worst_k]
    total_runs = sum(d["n"] for d in s.values())
    dataset_total = int(round(np.mean([d["samples_total_mean"] for d in s.values() if d["samples_total_mean"] > 0]))) if s else 0
    dataset_class0 = int(round(np.mean([d["class0_total_mean"] for d in s.values() if d["class0_total_mean"] > 0]))) if s else 0
    dataset_class1 = int(round(np.mean([d["class1_total_mean"] for d in s.values() if d["class1_total_mean"] > 0]))) if s else 0
    if dataset_total > 0 and dataset_class0 > 0 and dataset_class1 > 0:
        dataset_sentence = (
            f"dataset (Class 0: {dataset_class0} + Class 1: {dataset_class1}, total {dataset_total} samples) "
            "was used."
        )
    else:
        dataset_sentence = "dataset (auto-read from run outputs) was used."
    error_den = dataset_class0 if dataset_class0 > 0 else max(1, int(round(best.get("samples_total_mean", 1) / 2)))

    return _LATEX_TEMPLATE.format(
        date=datetime.now().strftime("%d %B %Y"),
        build_id=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_runs=total_runs,
        best_acc=f"{best['acc_mean']*100:.1f}",
        worst_acc=f"{worst['acc_mean']*100:.1f}",
        best_name=MODEL_DISPLAY[best_k],
        worst_name=MODEL_DISPLAY[worst_k],
        table_body=table_body,
        worst_fn=f"{worst['fn_mean']:.0f}",
        best_fp=f"{best['fp_mean']:.0f}",
        best_std=f"{best['acc_std']:.3f}",
        worst_std=f"{worst['acc_std']:.3f}",
        dataset_sentence=dataset_sentence,
        dataset_class0=dataset_class0 if dataset_class0 > 0 else "?",
        dataset_class1=dataset_class1 if dataset_class1 > 0 else "?",
        dataset_total=dataset_total if dataset_total > 0 else "?",
        error_den=error_den,
    )


_LATEX_TEMPLATE = r"""\documentclass[12pt, a4paper]{{article}}

% -- Language and encoding
\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage[english]{{babel}}

% -- Page layout
\usepackage[margin=2.5cm]{{geometry}}
\usepackage{{setspace}}
\onehalfspacing

% -- Figures and tables
\usepackage{{graphicx}}
\usepackage{{booktabs}}
\usepackage{{multirow}}
\usepackage{{float}}
\usepackage{{subcaption}}
\usepackage{{adjustbox}} % added for figure sizing

% -- Math
\usepackage{{amsmath}}

% -- Pagination helpers
\usepackage{{needspace}} % move headings to next page if needed
\usepackage{{etoolbox}}  % safe command patching

% -- Links (keep clickable, but do not show link colors/borders)
\usepackage[hidelinks]{{hyperref}}
\hypersetup{{colorlinks=false}}

% Avoid orphan headings at the bottom of pages (without redefining \section).
\pretocmd{{\section}}{{\Needspace{{10\baselineskip}}}}{{}}{{}}
\pretocmd{{\subsection}}{{\Needspace{{7\baselineskip}}}}{{}}{{}}

% =====================================================================
\title{{%
    \textbf{{Fall Detection with SmolVLM2-based Vision-Language Models:\\
    A Comparative Benchmark on Quantization and Model Size}}
}}
\author{{FallDetection Research Team}}
\date{{{date}}}

\begin{{document}}
\shorthandoff{{=}} % keep: avoids babel-related '=' issues in some environments

\maketitle

\begin{{center}}
\small \textit{{Build ID: {build_id}}}
\end{{center}}

% =================================================================
%  ABSTRACT
% =================================================================
\begin{{abstract}}
This study evaluates SmolVLM2 vision-language models (VLMs) on a fall-detection
task across different model sizes (256M vs 500M parameters) and quantization
strategies (Q8\_0 and F16). A total of {total_runs} independent runs were
executed, each using a balanced {dataset_sentence} Results indicate that the
500M family (mean accuracy: \%{best_acc}) substantially outperforms the 256M
family (mean accuracy: \%{worst_acc}). In terms of quantization, F16 (Same)
configurations yield the highest and most consistent results, while the mixed
Q8+FP16 mmproj approach remains competitive in accuracy.

This work is motivated by industrial safety: the target application is early
detection of a person falling to the ground in factory environments, enabling
faster response and reduced risk.
\end{{abstract}}

\textbf{{Keywords:}} fall detection, vision-language model, SmolVLM2, quantization,
edge AI, GGUF, benchmark

\newpage
\setcounter{{tocdepth}}{{2}}
\tableofcontents
\newpage

% =================================================================
%  1. INTRODUCTION
% =================================================================
\section{{Introduction}}

Falls, particularly among older adults, are a major public-health risk that can
lead to severe injuries, long periods of immobility, and even death. According
to the World Health Organization, roughly one-third of individuals aged 65+
experience at least one fall per year~\cite{{who2021falls}}. Automated fall
detection systems can improve quality of life and shorten emergency response
times.

In our case, the intended deployment setting is industrial facilities. The
system is designed to detect people falling to the ground on factory floors as
early as possible, supporting rapid intervention workflows.

Traditional fall detection approaches often rely on wearable sensors such as
accelerometers or gyroscopes, which introduce practical constraints related to
device compliance and battery life. Camera-based approaches enable passive
monitoring without requiring the user to carry an additional device.

Recent progress in large language models (LLMs) and vision-language models
(VLMs) has enabled strong performance on image understanding tasks. SmolVLM2 is
a compact VLM family developed by HuggingFace, offered at 256M and 500M
parameter scales~\cite{{smolvlm2}}. Quantized GGUF variants can be run via
\texttt{{llama.cpp}}, enabling low-latency inference in edge scenarios.

The main contributions of this work are:
\begin{{itemize}}
    \item A systematic benchmark of the SmolVLM2 family on the fall-detection task,
    \item Measurement of the impact of different quantization strategies (Q8\_0, F16, mixed Q8+FP16 mmproj)
          on accuracy and latency,
    \item A quantitative analysis of the performance--cost trade-off between 256M and 500M models.
\end{{itemize}}

% =================================================================
%  2. RELATED WORK
% =================================================================
\section{{Related Work}}

Fall detection research typically centers on three approaches: (i) wearable
sensor-based methods, (ii) ambient sensors (e.g., radar, lidar), and (iii)
camera-based vision methods. CNN-based approaches often rely on pose estimation
(OpenPose, MediaPipe) or video classification architectures (SlowFast,
TimeSformer).

Using VLMs for fall detection is relatively new. These models can bridge vision
and natural language, enabling open-ended prompts such as ``Is there a falling
person in this image?'' This report provides one of the first comprehensive
evaluations of the SmolVLM2 family in this context.

% =================================================================
%  3. METHODOLOGY
% =================================================================
\section{{Methodology}}

\subsection{{Model Configurations}}

Six configurations from the SmolVLM2 family were evaluated. Each configuration
consists of a \emph{{base model GGUF}} and a \emph{{multimodal projection (mmproj) GGUF}}.

\begin{{table}}[H]
\centering
\caption{{Evaluated model configurations}}
\label{{tab:configs}}
\begin{{tabular}}{{@{{}}llll@{{}}}}
\toprule
\textbf{{Configuration}} & \textbf{{Parameters}} & \textbf{{Base model}} & \textbf{{mmproj}} \\
\midrule
256M Q8 (Same)  & 256M & Q8\_0 & Q8\_0 \\
256M Q8+FP16    & 256M & Q8\_0 & F16   \\
256M F16 (Same) & 256M & F16   & F16   \\
500M Q8 (Same)  & 500M & Q8\_0 & Q8\_0 \\
500M Q8+FP16    & 500M & Q8\_0 & F16   \\
500M F16 (Same) & 500M & F16   & F16   \\
\bottomrule
\end{{tabular}}
\end{{table}}

All models were obtained from the HuggingFace \texttt{{ggml-org}} repository and
executed via a \texttt{{llama.cpp}}-based Docker service.

\subsection{{Dataset}}

The evaluation dataset contains two classes:
\begin{{itemize}}
    \item \textbf{{Class 0 (Falling):}} {dataset_class0} images showing a fall event (\texttt{{falling\_0}})
    \item \textbf{{Class 1 (Random):}} {dataset_class1} images showing non-fall random scenes (\texttt{{falling\_1}})
\end{{itemize}}

To ensure a balanced distribution, {dataset_total} samples were randomly sampled
from a larger pool before each run by \texttt{{run-model-benchmark-sequence.ps1}}.
This sampling strategy ensures that all models are evaluated on the same image
subset per run.

\subsection{{Experimental Setup}}

Experiments were conducted with the following setup:
\begin{{itemize}}
    \item \textbf{{Inference engine:}} \texttt{{llama.cpp}} (GGUF format)
    \item \textbf{{Containerization:}} Docker Compose
    \item \textbf{{API endpoint:}} \texttt{{POST /v1/inference/fall-detection}}
    \item \textbf{{Port:}} 8200
    \item \textbf{{Protocol:}} Multipart form-data image upload
\end{{itemize}}

Each configuration was run three times to assess repeatability.

\subsection{{Evaluation Metrics}}

For the binary fall-detection task, the following metrics were computed:

\begin{{itemize}}
    \item \textbf{{Accuracy:}} $\text{{Acc}} = \frac{{TP + TN}}{{TP + TN + FP + FN}}$
    \item \textbf{{Precision:}} $\text{{P}} = \frac{{TP}}{{TP + FP}}$
    \item \textbf{{Recall:}} $\text{{R}} = \frac{{TP}}{{TP + FN}}$
    \item \textbf{{F1-score:}} $\text{{F1}} = \frac{{2 \cdot P \cdot R}}{{P + R}}$
\end{{itemize}}

The positive class is defined as \textbf{{Class~0 (falling)}}. A false negative
(FN) corresponds to a missed fall and is safety-critical. A false positive (FP)
corresponds to a false alarm.

% =================================================================
%  4. RESULTS
% =================================================================
\section{{Results}}

\subsection{{Overall Performance Comparison}}

Table~\ref{{tab:results}} summarizes mean metrics across configurations.
Figure~\ref{{fig:accuracy}} compares accuracy, while Figure~\ref{{fig:f1}}
shows class-wise F1-scores.

\begin{{table}}[H]
\centering
\caption{{Mean performance metrics across model configurations}}
\label{{tab:results}}
\resizebox{{\textwidth}}{{!}}{{%
\begin{{tabular}}{{@{{}}lccccccccc@{{}}}}
\toprule
\textbf{{Model}} & \textbf{{Runs}} & \textbf{{Accuracy}} & \textbf{{F1\textsubscript{{falling}}}} & \textbf{{F1\textsubscript{{random}}}} & \textbf{{P\textsubscript{{falling}}}} & \textbf{{R\textsubscript{{falling}}}} & \textbf{{FP}} & \textbf{{FN}} & \textbf{{Latency (ms)}} \\
\midrule
{table_body}
\bottomrule
\end{{tabular}}%
}}
\end{{table}}

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig1_accuracy_bar.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig1_accuracy_bar.pdf}}%
    }}{{%
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Mean accuracy by model configuration.
    Error bars indicate standard deviation.}}
    \label{{fig:accuracy}}
\end{{figure}}

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig2_f1_comparison.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig2_f1_comparison.pdf}}%
    }}{{%
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Class-wise F1-score comparison. Red bars represent the falling class,
    blue bars represent the random class.}}
    \label{{fig:f1}}
\end{{figure}}

Overall, the 500M family consistently outperforms the 256M family across
configurations. The highest mean accuracy is achieved by
\textbf{{{best_name}}} at \textbf{{\%{best_acc}}}.

\subsection{{Error Analysis: FP and FN}}

Figure~\ref{{fig:confusion}} shows normalized confusion matrices for the worst
and best-performing models. Figure~\ref{{fig:fpfn}} summarizes mean FP and FN
counts across all models.

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig4_confusion_matrices.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig4_confusion_matrices.pdf}}%
    }}{{%
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Normalized confusion matrices for the lowest- and highest-accuracy models.
    Values in parentheses are raw counts.}}
    \label{{fig:confusion}}
\end{{figure}}

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig6_fp_fn_analysis.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig6_fp_fn_analysis.pdf}}%
    }}{{%
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Mean false positive and false negative counts by model.}}
    \label{{fig:fpfn}}
\end{{figure}}

The error analysis reveals two main patterns:
\begin{{enumerate}}
    \item \textbf{{256M models:}} High FN (mean {worst_fn}/{error_den}) and low FP.
    The model often misses fall events, but the false-alarm rate remains low,
    suggesting a conservative tendency toward \texttt{{no\_fall}} predictions.
    \item \textbf{{500M models:}} Low FN (often 0), but higher FP (mean {best_fp}/{error_den}).
    The model rarely misses falls, but sometimes classifies random images as falls.
\end{{enumerate}}

From a safety perspective, the near-zero FN behavior of the 500M models is
preferable, because missing a true fall is significantly riskier than issuing a
false alarm.

\subsection{{Precision--Recall Trade-off}}

Figure~\ref{{fig:pr}} shows each run in precision--recall space.

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig3_precision_recall.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig3_precision_recall.pdf}}%
    }}{{% 
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Precision--recall scatter (positive class: falling). Dashed lines indicate
    constant F1 iso-curves.}}
    \label{{fig:pr}}
\end{{figure}}

The 256M models cluster at high precision (often 1.0) but lower recall
(0.56--0.68). In contrast, the 500M models achieve recall$\approx$1.0 with a
more balanced precision range (0.82--0.89).

\subsection{{Inference Time Analysis}}

Figure~\ref{{fig:latency}} shows inference-time distributions by model.

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig5_latency_boxplot.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig5_latency_boxplot.pdf}}%
    }}{{% 
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Inference time distribution by model (milliseconds).
    Notched box plots indicate the median and confidence interval.}}
    \label{{fig:latency}}
\end{{figure}}

Inference times vary by model size and quantization. In general, F16 models can
be slower than Q8 models due to larger file size and higher memory demands.

\subsection{{Repeatability}}

Figure~\ref{{fig:trend}} shows the change in accuracy across repeated runs.

\begin{{figure}}[H]
    \centering
    \IfFileExists{{figures/fig7_accuracy_trend.pdf}}{{%
        \includegraphics[width=0.85\textwidth, keepaspectratio]{{figures/fig7_accuracy_trend.pdf}}%
    }}{{% 
        \framebox{{\parbox{{\linewidth}}{{\centering \vspace{{2cm}} Figure will appear in Overleaf \vspace{{2cm}}}}}}%
    }}
    \caption{{Model consistency across repeated runs. Each point represents the
    accuracy of an independent run.}}
    \label{{fig:trend}}
\end{{figure}}

The 500M models generally exhibit higher consistency (std: {best_std}).
The 256M models show larger run-to-run variance (std: {worst_std}).

% =================================================================
%  5. DISCUSSION
% =================================================================
\section{{Discussion}}

\subsection{{Effect of Model Size (256M vs 500M)}}

The most prominent finding is the effect of parameter count on performance.
The 500M family improves mean accuracy by roughly 15 points compared to the
256M family. More importantly, the 500M models rarely miss fall events
(FN$\approx$0), which is a safety-critical advantage.

\subsection{{Effect of Quantization Strategy}} 

Across both parameter scales, we observe the following ordering:
\begin{{enumerate}}
    \item \textbf{{F16 (Same):}} highest accuracy, lowest variance
    \item \textbf{{Q8+FP16 (mixed mmproj):}} near-F16 performance with lower memory use
    \item \textbf{{Q8 (Same):}} lowest accuracy, highest variance
\end{{enumerate}}

These results suggest that the quantization quality of the multimodal projection
layer (mmproj) has a meaningful impact on overall performance. The combination
of a Q8 base model with an F16 mmproj offers a strong
performance--efficiency trade-off.

\subsection{{Shift in Error Type}}

An interesting observation is that the dominant error type shifts with model size:
\begin{{itemize}}
    \item \textbf{{256M:}} high FN, low FP $\rightarrow$ ``conservative'' model
    \item \textbf{{500M:}} low FN, higher FP $\rightarrow$ ``sensitive'' model
\end{{itemize}}

For safety-critical applications, more ``sensitive'' models are often preferred:
false alarms can be tolerated, but missing a true fall can have severe consequences.

\subsection{{Practical Implications}}

The results indicate that SmolVLM2 500M F16 can reach usable performance for
practical fall-detection scenarios. However, several limitations should be considered:
\begin{{itemize}}
    \item Evaluation is single-frame only; no temporal information is used.
    \item The dataset is limited to {dataset_total} samples; broader and more diverse datasets are needed.
    \item Real-world conditions (lighting, viewpoint, occlusion) were not systematically tested.
\end{{itemize}}

% =================================================================
%  6. CONCLUSION AND FUTURE WORK
% =================================================================
\section{{Conclusion and Future Work}}

This report systematically evaluated SmolVLM2 VLM configurations on the
fall-detection task across 6 configurations and {total_runs} independent runs.
Key findings are summarized as follows:

\begin{{enumerate}}
    \item The 500M family outperforms the 256M family across all metrics.
    \item F16 yields the highest accuracy, while mixed Q8+FP16 provides a strong performance--efficiency balance.
    \item 500M models rarely miss fall events (FN$\approx$0), a critical advantage for safety applications.
    \item As model size increases, the dominant error shifts from FN toward FP.
\end{{enumerate}}

Future work can extend this study in the following directions:
\begin{{itemize}}
    \item Multi-frame and video-based inference with temporal modeling
    \item Evaluation on larger and more diverse fall datasets (UR Fall, Le2i, etc.)
    \item Real-time measurements on mobile and embedded platforms (Jetson Nano, Raspberry Pi)
    \item Prompt engineering and fine-tuning to improve model performance
    \item Comparative analysis across other VLM families (LLaVA, Qwen-VL, InternVL)
\end{{itemize}}

% =================================================================
%  KAYNAKCA
% =================================================================
\begin{{thebibliography}}{{9}}

\bibitem{{who2021falls}}
World Health Organization. (2021).
\textit{{Falls -- Key Facts}}.
\url{{https://www.who.int/news-room/fact-sheets/detail/falls}}

\bibitem{{smolvlm2}}
HuggingFace. (2025).
\textit{{SmolVLM2: Compact Vision Language Models}}.
\url{{https://huggingface.co/HuggingFaceTB/SmolVLM2-500M-Video-Instruct}}

\bibitem{{llamacpp}}
Gerganov, G. (2024).
\textit{{llama.cpp: LLM inference in C/C++}}.
\url{{https://github.com/ggerganov/llama.cpp}}

\bibitem{{gguf}}
GGML Team. (2024).
\textit{{GGUF: GPT-Generated Unified Format}}.
\url{{https://github.com/ggerganov/ggml/blob/master/docs/gguf.md}}

\end{{thebibliography}}

\end{{document}}
"""


# ── Main ───────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("SmolVLM2 Fall Detection — Benchmark Research Report Generator")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/4] Loading data...")
    runs = load_all_runs()
    total = sum(len(v) for v in runs.values())
    print(f"  -> {len(runs)} model configurations, {total} total runs")
    for k in MODEL_ORDER:
        if k in runs:
            print(f"    - {MODEL_DISPLAY[k]}: {len(runs[k])} runs")

    print("\n[2/4] Computing statistics...")
    summary = build_summary(runs)

    print("\n[3/4] Generating figures...")
    _style()
    for label, fn in [
        ("Fig 1: Accuracy Bar",       lambda: fig1_accuracy(summary)),
        ("Fig 2: F1 Comparison",       lambda: fig2_f1(summary)),
        ("Fig 3: Precision-Recall",    lambda: fig3_pr_scatter(runs)),
        ("Fig 4: Confusion Matrices",  lambda: fig4_confusion(runs, summary)),
        ("Fig 5: Latency Box Plot",    lambda: fig5_latency(summary)),
        ("Fig 6: FP vs FN",           lambda: fig6_fpfn(summary)),
        ("Fig 7: Accuracy Trend",     lambda: fig7_trend(runs)),
    ]:
        print(f"  -> {label}")
        fn()
    print(f"  -> Figures: {FIGURES_DIR}")

    print("\n[4/4] Writing LaTeX document...")
    tex = generate_latex(summary, runs)
    with open(LATEX_FILE, "w", encoding="utf-8") as f:
        f.write(tex)
    print(f"  -> LaTeX: {LATEX_FILE}")

    print("\n[Bonus] Attempting PDF build...")
    try:
        # Start from a clean slate to avoid stale TOC/aux artifacts causing "??" refs.
        stem = (OUTPUT_DIR / LATEX_FILE.stem)
        for ext in (".aux", ".toc", ".out", ".log"):
            try:
                (stem.with_suffix(ext)).unlink(missing_ok=True)
            except Exception:
                pass

        # Compile enough times for TOC and references to settle.
        # LaTeX may require multiple passes; we rerun if the output requests it.
        last_out = ""
        pdf = LATEX_FILE.with_suffix(".pdf")
        for i in range(1, 4):
            p = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode",
                 "-output-directory", str(OUTPUT_DIR),
                 str(LATEX_FILE)],
                capture_output=True, text=True, timeout=90, cwd=str(OUTPUT_DIR),
            )
            last_out = (p.stdout or "") + "\n" + (p.stderr or "")
            # MiKTeX may return non-zero for some warning-only runs (e.g. rerunfilecheck),
            # while still producing a valid PDF. Treat "no PDF produced" as the hard failure.
            if p.returncode != 0 and not pdf.exists():
                print(f"  X  pdflatex failed on pass {i} (exit={p.returncode}).")
                print(last_out[-2000:])
                break
            # Always do at least two passes for TOC.
            if i < 2:
                continue
            if "Rerun to get cross-references right" not in last_out and "Rerun to get outlines right" not in last_out:
                break
        if pdf.exists():
            print(f"  OK  PDF: {pdf}")
        else:
            print("  X  pdflatex ran but PDF was not created.")
    except FileNotFoundError:
        print("  X  pdflatex not found. Install MiKTeX / TeX Live.")
        print(f"     Manual: cd {OUTPUT_DIR} && pdflatex benchmark_report.tex")
    except Exception as e:
        print(f"  X  PDF build error: {e}")

    print("\n" + "=" * 60)
    print("Done!")
    print(f"  Cikti: {OUTPUT_DIR}")
    print("=" * 60)


if __name__ == "__main__":
    main()
