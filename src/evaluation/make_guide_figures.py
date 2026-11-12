"""Genera las figuras explicativas de la guía del proyecto (docs/GUIA.md).

    python -m src.evaluation.make_guide_figures
"""
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle

from src import config
from src.ai.train_model import load_or_train_model
from src.utils.telemetry_generator import ALL_SCENARIOS, sample_readings

ASSETS = "docs/assets"
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
GOOD, CRITICAL = "#0ca30c", "#d03b3b"
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": GRID,
    "axes.labelcolor": MUTED, "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.spines.top": False, "axes.spines.right": False, "axes.titlecolor": INK,
    "axes.titleweight": "bold", "axes.titlesize": 11, "axes.titlelocation": "left",
    "figure.facecolor": "white", "savefig.dpi": 200, "savefig.bbox": "tight",
})

NAMES = {
    "normal": "Operación normal",
    "thermal_spike": "Pico térmico",
    "pcie_degradation": "Degradación PCIe crítica",
    "resource_exhaustion": "Agotamiento de recursos",
    "subtle_degradation": "Degradación sutil",
    "subtle_thermal_drift": "Deriva térmica sutil",
}
KIND_COLOR = {"normal": GOOD, "thermal_spike": CRITICAL, "pcie_degradation": CRITICAL,
              "resource_exhaustion": CRITICAL, "subtle_degradation": ORANGE,
              "subtle_thermal_drift": ORANGE}


def reading_journey() -> None:
    """El recorrido de una lectura, de la petición a la respuesta."""
    steps = [
        ("1. Lectura", "El servidor envía\nCPU, temperatura,\nmemoria y errores PCIe", ORANGE),
        ("2. Validación", "Pydantic rechaza\nvalores imposibles\n(error 422)", BLUE),
        ("3. Diagnóstico", "Isolation Forest\ncalcula el score\ny la etiqueta", AQUA),
        ("4. Registro", "La lectura y su\ndiagnóstico se guardan\nen SQLite", BLUE),
        ("5. Respuesta", "NORMAL o\nANOMALY_DETECTED\nen ~10 ms", ORANGE),
    ]
    fig, ax = plt.subplots(figsize=(11, 2.9))
    ax.set_xlim(0, 110)
    ax.set_ylim(0, 26)
    ax.axis("off")
    for i, (title, text, color) in enumerate(steps):
        x = 1 + i * 22
        ax.add_patch(FancyBboxPatch((x, 3), 18, 19, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    fc="white", ec=color, lw=1.8))
        ax.text(x + 9, 18.5, title, ha="center", va="center", fontsize=10.5, fontweight="bold", color=INK)
        ax.text(x + 9, 9.8, text, ha="center", va="center", fontsize=7.8, color=MUTED)
        if i < len(steps) - 1:
            ax.annotate("", xy=(x + 22 - 0.6, 12.5), xytext=(x + 18.6, 12.5),
                        arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.4))
    fig.savefig(f"{ASSETS}/guia_recorrido_lectura.png")
    plt.close(fig)


def _isolate(points: np.ndarray, target: np.ndarray, rng: np.random.Generator, bounds):
    """Aplica cortes aleatorios hasta dejar sola a `target`; devuelve los cortes."""
    cuts = []
    (x0, x1), (y0, y1) = bounds
    subset = points
    while len(subset) > 1:
        axis = int(rng.integers(0, 2))
        lo, hi = subset[:, axis].min(), subset[:, axis].max()
        if lo == hi:
            continue
        split = rng.uniform(lo, hi)
        cuts.append((axis, split, (x0, x1, y0, y1)))
        keep_low = target[axis] < split
        subset = subset[(subset[:, axis] < split) == keep_low]
        if axis == 0:
            x0, x1 = (x0, split) if keep_low else (split, x1)
        else:
            y0, y1 = (y0, split) if keep_low else (split, y1)
    return cuts


def isolation_intuition() -> None:
    """Por qué una anomalía se aísla con menos cortes que una lectura normal."""
    rng = np.random.default_rng(5)
    normal = sample_readings("normal", 160, rng)[["package_temp_c", "cpu_utilization_pct"]].values
    anomaly = np.array([75.0, 15.0])
    typical = normal[np.argmin(np.abs(normal - normal.mean(axis=0)).sum(axis=1))]
    points = np.vstack([normal, anomaly])
    bounds = ((36, 82), (0, 86))

    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.3), sharey=True)
    cases = [(anomaly, CRITICAL, "Lectura anómala", 3),
             (typical, BLUE, "Lectura normal", 11)]
    for ax, (target, color, label, seed) in zip(axes, cases):
        cuts = _isolate(points, target, np.random.default_rng(seed), bounds)
        ax.scatter(normal[:, 0], normal[:, 1], s=10, color="#b9b8b2", linewidths=0)
        ax.scatter(*anomaly, s=10, color="#b9b8b2", linewidths=0)
        for axis, split, (x0, x1, y0, y1) in cuts:
            if axis == 0:
                ax.plot([split, split], [y0, y1], color=color, lw=1.1, alpha=0.8)
            else:
                ax.plot([x0, x1], [split, split], color=color, lw=1.1, alpha=0.8)
        ax.scatter(*target, s=80, color=color, edgecolors="white", linewidths=1.2, zorder=5)
        ax.set_title(f"{label}: queda sola con {len(cuts)} cortes")
        ax.set_xlim(*bounds[0])
        ax.set_ylim(*bounds[1])
        ax.set_xlabel("Temperatura (°C)")
    axes[0].set_ylabel("Uso de CPU (%)")
    fig.suptitle("Isolation Forest: lo raro queda solo con pocos cortes aleatorios",
                 x=0.07, ha="left", fontweight="bold", fontsize=12.5, color=INK)
    fig.tight_layout()
    fig.savefig(f"{ASSETS}/guia_isolation_forest.png")
    plt.close(fig)


def blind_zone() -> None:
    """La zona que los umbrales consideran segura y donde vive la degradación sutil."""
    rng = np.random.default_rng(8)
    model = load_or_train_model()
    groups = {
        "Operación normal": sample_readings("normal", 500, rng),
        "Degradación sutil": sample_readings("subtle_degradation", 60, rng),
        "Pico térmico": sample_readings("thermal_spike", 40, rng),
    }
    fig, ax = plt.subplots(figsize=(8.2, 5))
    t_temp = config.STATIC_THRESHOLDS["package_temp_c"]
    t_cpu = config.STATIC_THRESHOLDS["cpu_utilization_pct"]
    ax.add_patch(Rectangle((34, 0), t_temp - 34, t_cpu, fc="#eef4fc", ec="none", zorder=0))
    ax.text(35.5, 88.5, "Zona que los umbrales fijos consideran segura", fontsize=9, color=MUTED, va="top")
    for name, df in groups.items():
        flagged = model.predict(df[config.FEATURES]) == -1
        for mask, color, marker, size in ((~flagged, GOOD, "o", 14), (flagged, CRITICAL, "X", 34)):
            ax.scatter(df.loc[mask, "package_temp_c"], df.loc[mask, "cpu_utilization_pct"], s=size,
                       color=color, marker=marker, linewidths=0.4, edgecolors="white", alpha=0.75)
    ax.axvline(t_temp, color=MUTED, lw=1, ls=":")
    ax.axhline(t_cpu, color=MUTED, lw=1, ls=":")
    ax.annotate("Degradación sutil:\nlos umbrales no la ven,\nel modelo sí", xy=(68.5, 15), xytext=(36, 4),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.annotate("Falla crítica:\nla detectan ambos", xy=(93, 94), xytext=(88, 68),
                fontsize=9, color=INK, arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.scatter([], [], s=14, color=GOOD, label="El modelo dice NORMAL")
    ax.scatter([], [], s=34, color=CRITICAL, marker="X", label="El modelo dice ANOMALÍA")
    ax.set_xlim(34, 105)
    ax.set_ylim(0, 104)
    ax.set_xlabel("Temperatura del encapsulado (°C)")
    ax.set_ylabel("Uso de CPU (%)")
    ax.set_title("El punto ciego de los umbrales fijos")
    ax.legend(frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.13), ncol=2)
    fig.savefig(f"{ASSETS}/guia_punto_ciego.png")
    plt.close(fig)


def scenario_ranges() -> None:
    """Rango de cada métrica en cada escenario, frente a su umbral fijo."""
    rng = np.random.default_rng(2)
    metrics = [("cpu_utilization_pct", "Uso de CPU (%)"), ("package_temp_c", "Temperatura (°C)"),
               ("dram_usage_gb", "Memoria en uso (GB)"), ("pcie_error_count", "Errores PCIe")]
    data = {s: sample_readings(s, 1000, rng) for s in ALL_SCENARIOS}
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.6), sharey=True)
    for ax, (column, title) in zip(axes, metrics):
        for i, scenario in enumerate(ALL_SCENARIOS):
            lo, mid, hi = np.percentile(data[scenario][column], [5, 50, 95])
            ax.plot([lo, hi], [i, i], color=KIND_COLOR[scenario], lw=5, solid_capstyle="round")
            ax.scatter([mid], [i], s=26, color="white", edgecolors=KIND_COLOR[scenario], linewidths=1.5, zorder=3)
        ax.axvline(config.STATIC_THRESHOLDS[column], color=INK, lw=1, ls="--")
        ax.set_title(title)
        ax.xaxis.grid(True, color=GRID)
        ax.set_axisbelow(True)
        ax.tick_params(length=0)
    axes[0].set_yticks(range(len(ALL_SCENARIOS)), [NAMES[s] for s in ALL_SCENARIOS])
    axes[0].invert_yaxis()
    for label in axes[0].get_yticklabels():
        label.set_color(INK)
    handles = [plt.Line2D([], [], color=c, lw=5) for c in (GOOD, CRITICAL, ORANGE)]
    handles.append(plt.Line2D([], [], color=INK, lw=1, ls="--"))
    fig.legend(handles, ["Normal", "Falla crítica", "Degradación sutil", "Umbral fijo"], frameon=False,
               loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.1))
    fig.suptitle("Qué valores produce cada escenario (rango del 5 al 95 %; el punto es la mediana)",
                 x=0.02, ha="left", fontweight="bold", fontsize=12, color=INK)
    fig.tight_layout()
    fig.savefig(f"{ASSETS}/guia_escenarios.png")
    plt.close(fig)


if __name__ == "__main__":
    os.makedirs(ASSETS, exist_ok=True)
    reading_journey()
    isolation_intuition()
    blind_zone()
    scenario_ranges()
    print(f"Figuras de la guía generadas en {ASSETS}/")
