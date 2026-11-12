"""Compara el Isolation Forest contra una línea base de umbrales fijos.

Evalúa ambos detectores sobre telemetría sintética etiquetada que el modelo no
vio al entrenar, separando fallas críticas y degradaciones sutiles.

    python -m src.evaluation.model_benchmark
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix, precision_recall_fscore_support

from src import config
from src.ai.train_model import load_or_train_model
from src.utils.telemetry_generator import (
    CRITICAL_SCENARIOS,
    SUBTLE_SCENARIOS,
    IntelFleetTelemetryGenerator,
    sample_readings,
)

EVAL_SEED = 2026


def predict_model(model, df: pd.DataFrame) -> np.ndarray:
    return (model.predict(df[config.FEATURES]) == -1).astype(int)


def predict_thresholds(df: pd.DataFrame) -> np.ndarray:
    """Alerta cuando cualquier métrica supera su umbral fijo."""
    alerts = np.zeros(len(df), dtype=bool)
    for column, limit in config.STATIC_THRESHOLDS.items():
        alerts |= (df[column] > limit).values
    return alerts.astype(int)


def classification_metrics(y_true, y_pred) -> dict:
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "false_positive_rate": round(float(fp / (fp + tn)), 4) if fp + tn else 0.0,
    }


def run_benchmark(n_mixed: int = 20000, n_per_scenario: int = 2000) -> dict:
    model = load_or_train_model()
    detectors = {
        "isolation_forest": lambda df: predict_model(model, df),
        "static_thresholds": predict_thresholds,
    }

    # 1. Flota mixta: operación normal con 5 % de fallas críticas.
    mixed = IntelFleetTelemetryGenerator(seed=EVAL_SEED).generate_fleet_data(
        n_samples=n_mixed, anomaly_ratio=0.05, anomaly_scenarios=CRITICAL_SCENARIOS
    )
    results = {
        "config": {
            "features": config.FEATURES,
            "n_estimators": config.IFOREST_N_ESTIMATORS,
            "contamination": config.IFOREST_CONTAMINATION,
            "training_samples": config.TRAINING_SAMPLES,
            "static_thresholds": config.STATIC_THRESHOLDS,
            "eval_seed": EVAL_SEED,
        },
        "mixed_fleet": {
            "n_samples": n_mixed,
            "n_anomalies": int(mixed["is_simulated_anomaly"].sum()),
            **{name: classification_metrics(mixed["is_simulated_anomaly"], fn(mixed))
               for name, fn in detectors.items()},
        },
        "detection_rate_by_scenario": {},
    }

    # 2. Tasa de detección por escenario (todas las lecturas son anomalías reales).
    rng = np.random.default_rng(EVAL_SEED)
    for scenario in ("normal",) + CRITICAL_SCENARIOS + SUBTLE_SCENARIOS:
        batch = sample_readings(scenario, n_per_scenario, rng)
        results["detection_rate_by_scenario"][scenario] = {
            "n_samples": n_per_scenario,
            **{name: round(float(fn(batch).mean()), 4) for name, fn in detectors.items()},
        }
    return results


def format_report(results: dict) -> str:
    lines = [f"Flota mixta (5 % de fallas críticas, {results['mixed_fleet']['n_samples']} lecturas)"]
    for name in ("isolation_forest", "static_thresholds"):
        m = results["mixed_fleet"][name]
        lines.append(f"  {name:<18} precisión {m['precision']:.3f}  recall {m['recall']:.3f}  "
                     f"F1 {m['f1']:.3f}  FP {m['fp']}  FN {m['fn']}")
    lines.append("\nProporción de lecturas marcadas como anomalía por escenario")
    lines.append(f"  {'escenario':<22} {'isolation_forest':>17} {'static_thresholds':>18}")
    for scenario, row in results["detection_rate_by_scenario"].items():
        lines.append(f"  {scenario:<22} {row['isolation_forest']:>16.1%} {row['static_thresholds']:>17.1%}")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluación del modelo contra umbrales fijos")
    parser.add_argument("--output", default="docs/results/model_benchmark.json")
    args = parser.parse_args()

    results = run_benchmark()
    print(format_report(results))
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nResultados guardados en {args.output}")


if __name__ == "__main__":
    main()
