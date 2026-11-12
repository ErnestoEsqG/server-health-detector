"""Genera las figuras de docs/assets a partir de los resultados de evaluación.

    python -m src.evaluation.model_benchmark
    python -m src.evaluation.latency_benchmark      # requiere la API en ejecución
    python -m src.database.analytics_views
    python -m src.evaluation.make_figures
"""
import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src import config

ASSETS = "docs/assets"
RESULTS = "docs/results"
BLUE, ORANGE = "#2a78d6", "#eb6834"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlesize": 12, "axes.titlelocation": "left",
    "figure.facecolor": "white", "savefig.dpi": 200, "savefig.bbox": "tight",
})

SCENARIO_LABELS = {
    "normal": "Operación normal\n(falsas alarmas)",
    "thermal_spike": "Pico térmico",
    "pcie_degradation": "Degradación PCIe\ncrítica",
    "resource_exhaustion": "Agotamiento de\nrecursos",
    "subtle_degradation": "Degradación sutil\n(térmica + PCIe)",
    "subtle_thermal_drift": "Deriva térmica\nsutil (sin PCIe)",
}


def model_comparison() -> None:
    with open(f"{RESULTS}/model_benchmark.json", encoding="utf-8") as f:
        rates = json.load(f)["detection_rate_by_scenario"]
    scenarios = list(SCENARIO_LABELS)
    width = 0.38
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for offset, key, color, label in ((-width / 2, "isolation_forest", BLUE, "Isolation Forest"),
                                      (width / 2, "static_thresholds", ORANGE, "Umbrales fijos")):
        values = [rates[s][key] * 100 for s in scenarios]
        bars = ax.bar([i + offset for i in range(len(scenarios))], values, width - 0.03,
                      color=color, label=label)
        ax.bar_label(bars, labels=[f"{v:.1f}%" for v in values], padding=2, fontsize=8, color=INK)
    ax.set_xticks(range(len(scenarios)), [SCENARIO_LABELS[s] for s in scenarios], fontsize=8.5)
    ax.set_ylim(0, 112)
    ax.set_ylabel("Lecturas marcadas como anomalía (%)")
    ax.yaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.set_title("Tasa de detección por escenario: modelo frente a umbrales fijos")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2)
    fig.savefig(f"{ASSETS}/model_comparison.png")
    plt.close(fig)


def latency_histogram() -> None:
    with open(f"{RESULTS}/latency_benchmark.json", encoding="utf-8") as f:
        data = json.load(f)
    stats = data["client_latency_ms"]
    labels = ["Media", "p50", "p95", "p99", "Máximo"]
    values = [stats[k] for k in ("mean", "p50", "p95", "p99", "max")]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    bars = ax.barh(labels[::-1], values[::-1], color=BLUE, height=0.55)
    ax.bar_label(bars, labels=[f"{v:.1f} ms" for v in values[::-1]], padding=4, fontsize=9, color=INK)
    ax.axvline(100, color=CRITICAL, linewidth=1.5, linestyle="--")
    ax.text(98.5, 2, "Objetivo: 100 ms", color=INK, ha="right", va="center", fontsize=9)
    ax.set_xlim(0, 112)
    ax.set_xlabel("Latencia de extremo a extremo (ms)")
    ax.xaxis.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.set_title(f"Latencia del endpoint de ingesta ({data['requests']} peticiones)")
    fig.savefig(f"{ASSETS}/latency_benchmark.png")
    plt.close(fig)


def telemetry_scatter() -> None:
    path = os.path.join(config.PROCESSED_DIR, "fleet_master_telemetry.csv")
    df = pd.read_csv(path)
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    normal = df[df["status"] == "NORMAL"]
    anomalous = df[df["status"] != "NORMAL"]
    ax.scatter(normal["package_temp_c"], normal["cpu_utilization_pct"], s=14, color=GOOD,
               alpha=0.55, linewidths=0, label=f"NORMAL ({len(normal)})")
    ax.scatter(anomalous["package_temp_c"], anomalous["cpu_utilization_pct"], s=30, color=CRITICAL,
               marker="X", linewidths=0.4, edgecolors="white",
               label=f"ANOMALY_DETECTED ({len(anomalous)})")
    ax.axvline(config.STATIC_THRESHOLDS["package_temp_c"], color=MUTED, linewidth=1, linestyle=":")
    ax.axhline(config.STATIC_THRESHOLDS["cpu_utilization_pct"], color=MUTED, linewidth=1, linestyle=":")
    ax.text(85.6, 3, "umbral 85 °C", fontsize=8, color=MUTED, rotation=90, va="bottom")
    ax.text(36, 91, "umbral 90 % CPU", fontsize=8, color=MUTED, va="bottom")
    ax.set_xlabel("Temperatura del encapsulado (°C)")
    ax.set_ylabel("Uso de CPU (%)")
    ax.set_xlim(34, 105)
    ax.set_ylim(0, 104)
    ax.grid(True, color=GRID)
    ax.set_axisbelow(True)
    ax.set_title("Lecturas clasificadas por el modelo: CPU frente a temperatura")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.15), ncol=2)
    fig.savefig(f"{ASSETS}/telemetry_scatter.png")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    model_comparison()
    latency_histogram()
    telemetry_scatter()
    print(f"Figuras generadas en {ASSETS}/")
