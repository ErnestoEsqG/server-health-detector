from pydantic import BaseModel, Field
from datetime import datetime

class TelemetryPayload(BaseModel):
    """
    Esquema de validacion para el payload de telemetria entrante.
    """
    server_id: str = Field(..., example="SRV-XEON-01", description="Identificador unico del servidor")
    cpu_utilization_pct: float = Field(..., ge=0.0, le=100.0, example=45.5, description="Uso de CPU en %")
    package_temp_c: float = Field(..., ge=0.0, le=120.0, example=58.2, description="Temperatura de empaque en C")
    dram_usage_gb: float = Field(..., ge=0.0, le=512.0, example=32.0, description="Memoria RAM utilizada en GB")
    pcie_error_count: int = Field(..., ge=0, example=0, description="Conteo de errores no corregibles de PCIe")

class HealthEvaluationResponse(BaseModel):
    """
    Esquema de respuesta devuelto por la API con el diagnostico de salud.
    """
    server_id: str
    status: str
    is_healthy: bool
    anomaly_score: float
    evaluated_at: datetime