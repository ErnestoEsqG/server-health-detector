import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class IntelFleetTelemetryGenerator:
    """
    Generador de telemetria sintetica para flotas de servidores Intel Xeon.
    Simula comportamiento operativo normal y eventos anómalos de estrés.
    """
    def __init__(self, seed: int = 42):
        np.random.seed(seed)

    def generate_fleet_data(self, n_samples: int = 1000, anomaly_ratio: float = 0.05) -> pd.DataFrame:
        # 1. Generación de datos bajo operación NORMAL
        cpu = np.random.normal(loc=45.0, scale=12.0, size=n_samples)
        temp = np.random.normal(loc=55.0, scale=6.0, size=n_samples)
        dram = np.random.normal(loc=32.0, scale=5.0, size=n_samples)
        pcie_errors = np.random.poisson(lam=0.05, size=n_samples)

        # Truncar valores dentro de límites físicos reales
        cpu = np.clip(cpu, 5.0, 100.0)
        temp = np.clip(temp, 35.0, 105.0)
        dram = np.clip(dram, 4.0, 128.0)

        df = pd.DataFrame({
            'timestamp': [datetime.now() - timedelta(minutes=i) for i in range(n_samples)],
            'cpu_utilization_pct': np.round(cpu, 2),
            'package_temp_c': np.round(temp, 2),
            'dram_usage_gb': np.round(dram, 2),
            'pcie_error_count': pcie_errors,
            'is_simulated_anomaly': 0  # 0 = Normal, 1 = Anómalo
        })

        # 2. Inyección controlada de ANOMALÍAS
        n_anomalies = int(n_samples * anomaly_ratio)
        anomaly_indices = np.random.choice(n_samples, size=n_anomalies, replace=False)

        for idx in anomaly_indices:
            anomaly_type = np.random.choice(['thermal_spike', 'pcie_degradation', 'resource_exhaustion'])
            
            if anomaly_type == 'thermal_spike':
                df.loc[idx, 'package_temp_c'] = np.random.uniform(88.0, 102.0)
                df.loc[idx, 'cpu_utilization_pct'] = np.random.uniform(90.0, 100.0)
            elif anomaly_type == 'pcie_degradation':
                df.loc[idx, 'pcie_error_count'] = np.random.randint(8, 25)
            elif anomaly_type == 'resource_exhaustion':
                df.loc[idx, 'cpu_utilization_pct'] = np.random.uniform(95.0, 100.0)
                df.loc[idx, 'dram_usage_gb'] = np.random.uniform(115.0, 128.0)
            
            df.loc[idx, 'is_simulated_anomaly'] = 1

        return df

if __name__ == "__main__":
    generator = IntelFleetTelemetryGenerator()
    data = generator.generate_fleet_data(n_samples=100)
    print("--- Muestra de Telemetría Generada ---")
    print(data.head(10))
    print("\n--- Conteo de Registros por Clase ---")
    print(data['is_simulated_anomaly'].value_counts())