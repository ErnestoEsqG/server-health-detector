from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from src.database.connection import Base


def utcnow() -> datetime:
    """Hora UTC sin zona, el formato en que SQLite guarda los DateTime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Server(Base):
    """Inventario de servidores de la flota."""
    __tablename__ = "servers"

    server_id = Column(String(50), primary_key=True, index=True)
    hostname = Column(String(100), nullable=False)
    processor_model = Column(String(100), default="Intel Xeon Scalable 4th Gen")
    rack_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=utcnow)

    telemetry_logs = relationship("TelemetryRecord", back_populates="server", cascade="all, delete-orphan")


class TelemetryRecord(Base):
    """Tabla de hechos: cada lectura de telemetría con el diagnóstico del modelo."""
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_id = Column(String(50), ForeignKey("servers.server_id"), nullable=False, index=True)

    # Métricas de hardware
    cpu_utilization_pct = Column(Float, nullable=False)
    package_temp_c = Column(Float, nullable=False)
    dram_usage_gb = Column(Float, nullable=False)
    pcie_error_count = Column(Integer, nullable=False)

    # Diagnóstico del modelo
    status = Column(String(30), nullable=False)
    is_healthy = Column(Boolean, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=utcnow)

    server = relationship("Server", back_populates="telemetry_logs")


class ExportCheckpoint(Base):
    """Último registro enviado al data lake, para no exportar dos veces la misma lectura."""
    __tablename__ = "export_checkpoints"

    id = Column(Integer, primary_key=True)
    last_record_id = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)
