"""Generador de telemetría sintética para flotas de servidores.

Define los escenarios operativos del proyecto en un solo lugar, de modo que el
entrenamiento, el simulador de flota y la evaluación usen las mismas
distribuciones.
"""
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

FEATURES = ["cpu_utilization_pct", "package_temp_c", "dram_usage_gb", "pcie_error_count"]

# Fallas críticas: al menos una métrica llega a valores extremos.
CRITICAL_SCENARIOS = ("thermal_spike", "pcie_degradation", "resource_exhaustion")
# Degradaciones sutiles: ninguna métrica supera los umbrales fijos habituales.
SUBTLE_SCENARIOS = ("subtle_degradation", "subtle_thermal_drift")
ALL_SCENARIOS = ("normal",) + CRITICAL_SCENARIOS + SUBTLE_SCENARIOS


def sample_readings(scenario: str, n: int, rng: np.random.Generator) -> pd.DataFrame:
    """Devuelve `n` lecturas del escenario indicado.

    Toda lectura parte de la operación normal y cada escenario sobrescribe
    únicamente las métricas que degrada.
    """
    if scenario not in ALL_SCENARIOS:
        raise ValueError(f"Escenario desconocido: {scenario!r}. Opciones: {ALL_SCENARIOS}")

    cpu = np.clip(rng.normal(45.0, 12.0, n), 5.0, 100.0)
    temp = np.clip(rng.normal(55.0, 6.0, n), 35.0, 105.0)
    dram = np.clip(rng.normal(32.0, 5.0, n), 4.0, 128.0)
    pcie = rng.poisson(0.05, n)

    if scenario == "thermal_spike":
        temp = rng.uniform(88.0, 102.0, n)
        cpu = rng.uniform(90.0, 100.0, n)
    elif scenario == "pcie_degradation":
        pcie = rng.integers(8, 25, n)
    elif scenario == "resource_exhaustion":
        cpu = rng.uniform(95.0, 100.0, n)
        dram = rng.uniform(115.0, 128.0, n)
    elif scenario == "subtle_degradation":
        # Carga baja + temperatura elevada + errores PCIe esporádicos:
        # el caso descrito en el planteamiento del problema.
        cpu = rng.uniform(10.0, 25.0, n)
        temp = rng.uniform(68.0, 80.0, n)
        pcie = rng.integers(1, 5, n)
    elif scenario == "subtle_thermal_drift":
        # Igual que el anterior pero sin errores de bus: solo CPU y temperatura
        # dejan de guardar su relación habitual.
        cpu = rng.uniform(10.0, 25.0, n)
        temp = rng.uniform(68.0, 80.0, n)
        pcie = np.zeros(n, dtype=int)

    return pd.DataFrame({
        "cpu_utilization_pct": np.round(cpu, 2),
        "package_temp_c": np.round(temp, 2),
        "dram_usage_gb": np.round(dram, 2),
        "pcie_error_count": pcie.astype(int),
    })


class IntelFleetTelemetryGenerator:
    """Genera conjuntos de telemetría con operación normal y anomalías inyectadas."""

    def __init__(self, seed: int = 42):
        self.rng = np.random.default_rng(seed)

    def generate_fleet_data(
        self,
        n_samples: int = 1000,
        anomaly_ratio: float = 0.05,
        anomaly_scenarios: tuple = CRITICAL_SCENARIOS,
    ) -> pd.DataFrame:
        """Devuelve un DataFrame con las métricas, la etiqueta real y el tipo de escenario.

        Las columnas `is_simulated_anomaly` y `anomaly_type` existen solo para
        evaluar: el modelo nunca las ve durante el entrenamiento.
        """
        df = sample_readings("normal", n_samples, self.rng)
        df["anomaly_type"] = "normal"

        n_anomalies = int(n_samples * anomaly_ratio)
        if n_anomalies:
            idx = self.rng.choice(n_samples, size=n_anomalies, replace=False)
            kinds = self.rng.choice(anomaly_scenarios, size=n_anomalies)
            for kind in set(kinds):
                rows = idx[kinds == kind]
                df.loc[rows, FEATURES] = sample_readings(kind, len(rows), self.rng).values
                df.loc[rows, "anomaly_type"] = kind

        df["pcie_error_count"] = df["pcie_error_count"].astype(int)
        df["is_simulated_anomaly"] = (df["anomaly_type"] != "normal").astype(int)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        df.insert(0, "timestamp", [now - timedelta(minutes=i) for i in range(n_samples)])
        return df


if __name__ == "__main__":
    data = IntelFleetTelemetryGenerator().generate_fleet_data(n_samples=100)
    print("--- Muestra de telemetría generada ---")
    print(data.head(10))
    print("\n--- Conteo de registros por escenario ---")
    print(data["anomaly_type"].value_counts())
