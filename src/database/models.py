from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from src.database.connection import Base

class Server(Base):
    """
    Tabla que almacena el inventario de servidores de la flota Intel.
    """
    __tablename__ = "servers"

    server_id = Column(String(50), primary_key=True, index=True)
    hostname = Column(String(100), nullable=False)
    processor_model = Column(String(100), default="Intel Xeon Scalable 4th Gen")
    rack_id = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relacion bidireccional con telemetry_records
    telemetry_logs = relationship("TelemetryRecord", back_populates="server", cascade="all, delete-orphan")


class TelemetryRecord(Base):
    """
    Tabla de hechos que almacena cada lectura de telemetria procesada por la IA.
    """
    __tablename__ = "telemetry_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    server_id = Column(String(50), ForeignKey("servers.server_id"), nullable=False, index=True)
    
    # Metricas de hardware
    cpu_utilization_pct = Column(Float, nullable=False)
    package_temp_c = Column(Float, nullable=False)
    dram_usage_gb = Column(Float, nullable=False)
    pcie_error_count = Column(Integer, nullable=False)

    # Diagnostico del modelo de IA
    status = Column(String(30), nullable=False)
    is_healthy = Column(Boolean, nullable=False)
    anomaly_score = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow)

    # Relacion inversa con el servidor
    server = relationship("Server", back_populates="telemetry_logs")