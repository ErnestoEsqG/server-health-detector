from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TelemetryPayload(BaseModel):
    """Contrato de entrada de una lectura de telemetría."""
    server_id: str = Field(..., min_length=1, max_length=50, examples=["SRV-XEON-01"],
                           description="Identificador único del servidor")
    cpu_utilization_pct: float = Field(..., ge=0.0, le=100.0, examples=[45.5], description="Uso de CPU en %")
    package_temp_c: float = Field(..., ge=0.0, le=120.0, examples=[58.2], description="Temperatura del encapsulado en °C")
    dram_usage_gb: float = Field(..., ge=0.0, le=512.0, examples=[32.0], description="Memoria RAM utilizada en GB")
    pcie_error_count: int = Field(..., ge=0, examples=[0], description="Errores del bus PCIe en el intervalo")
    rack_id: Optional[str] = Field(None, max_length=50, examples=["RACK-ZAP-01"],
                                   description="Rack del servidor; solo se usa al registrarlo por primera vez")
    recorded_at: Optional[datetime] = Field(None, description="Momento de la medición (UTC). Si se omite, se usa la hora de recepción")


class HealthEvaluationResponse(BaseModel):
    """Diagnóstico devuelto por la API para una lectura."""
    server_id: str
    status: str
    is_healthy: bool
    anomaly_score: float
    evaluated_at: datetime


class TelemetryRecordOut(BaseModel):
    """Registro histórico de telemetría."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: str
    cpu_utilization_pct: float
    package_temp_c: float
    dram_usage_gb: float
    pcie_error_count: int
    status: str
    is_healthy: bool
    anomaly_score: float
    recorded_at: datetime


class ServerKpi(BaseModel):
    """Indicadores agregados por servidor."""
    server_id: str
    rack_id: str
    total_readings: int
    healthy_readings: int
    anomaly_incidents: int
    uptime_pct: Optional[float]
    avg_cpu_pct: Optional[float]
    avg_temp_c: Optional[float]
    max_temp_c: Optional[float]
    total_pcie_errors: Optional[int]
