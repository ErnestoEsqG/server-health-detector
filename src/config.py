"""Configuración central del proyecto.

Todos los valores pueden sobrescribirse con variables de entorno (prefijo SHD_),
lo que permite ejecutar el mismo código en local, en pruebas y en Docker.
"""
import os

DATABASE_URL: str = os.getenv("SHD_DATABASE_URL", "sqlite:///./telemetry.db")
MODEL_PATH: str = os.getenv("SHD_MODEL_PATH", "src/ai/intel_health_model.pkl")
DATALAKE_DIR: str = os.getenv("SHD_DATALAKE_DIR", "data/datalake")
PROCESSED_DIR: str = os.getenv("SHD_PROCESSED_DIR", "data/processed")
DEFAULT_RACK_ID: str = os.getenv("SHD_DEFAULT_RACK_ID", "RACK-ZAP-01")

# Orden de las variables con el que se entrena y se consulta el modelo.
FEATURES = ["cpu_utilization_pct", "package_temp_c", "dram_usage_gb", "pcie_error_count"]

# Hiperparámetros del Isolation Forest.
IFOREST_N_ESTIMATORS: int = 100
IFOREST_CONTAMINATION: float = 0.05
IFOREST_RANDOM_STATE: int = 42
TRAINING_SAMPLES: int = 5000

# Línea base de monitoreo tradicional: una alerta se dispara cuando CUALQUIER
# métrica supera su umbral fijo. Se usa solo para comparar contra el modelo.
STATIC_THRESHOLDS = {
    "cpu_utilization_pct": 90.0,
    "package_temp_c": 85.0,
    "dram_usage_gb": 110.0,
    "pcie_error_count": 5,
}
