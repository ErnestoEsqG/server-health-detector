"""API de ingesta de telemetría, inferencia y consulta."""
import logging
import time
from contextlib import asynccontextmanager
from datetime import timezone
from typing import List

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from src import config
from src.ai.train_model import load_or_train_model
from src.api.schemas import (
    HealthEvaluationResponse,
    ServerKpi,
    TelemetryPayload,
    TelemetryRecordOut,
)
from src.database.analytics_views import QUERY_KPIS
from src.database.connection import Base, engine, get_db
from src.database.models import Server, TelemetryRecord, utcnow
from src.services.cloud_exporter import CloudDataLakeExporter

logger = logging.getLogger("server_health_detector")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Crea las tablas y carga el modelo una sola vez, al arrancar el servicio."""
    Base.metadata.create_all(bind=engine)
    app.state.model = load_or_train_model(config.MODEL_PATH)
    yield


app = FastAPI(
    title="Server Health Detector API",
    description="Ingesta de telemetría de hardware, detección de anomalías con "
                "Isolation Forest y persistencia en SQL.",
    version="1.2.0",
    lifespan=lifespan,
)
exporter = CloudDataLakeExporter()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Expone el tiempo de procesamiento del servidor en cada respuesta."""
    start = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.2f}"
    return response


@app.get("/health", tags=["System"])
def health_check(request: Request, db: Session = Depends(get_db)):
    """Comprueba que el modelo está en memoria y que la base de datos responde."""
    model_loaded = getattr(request.app.state, "model", None) is not None
    try:
        db.execute(text("SELECT 1"))
        database_ok = True
    except SQLAlchemyError:
        database_ok = False

    healthy = model_loaded and database_ok
    body = {
        "status": "ONLINE" if healthy else "DEGRADED",
        "model_loaded": model_loaded,
        "database": "CONNECTED" if database_ok else "UNAVAILABLE",
        "timestamp": utcnow().isoformat(),
    }
    return JSONResponse(body, status_code=200 if healthy else 503)


# Las rutas se declaran con `def`: la inferencia y SQLAlchemy son bloqueantes, y así
# FastAPI las ejecuta en su pool de hilos sin detener el bucle de eventos ASGI.
@app.post("/api/v1/telemetry/ingest", response_model=HealthEvaluationResponse, tags=["Fleet Telemetry"])
def evaluate_and_store_telemetry(payload: TelemetryPayload, request: Request, db: Session = Depends(get_db)):
    """Recibe una lectura, la evalúa con el modelo y guarda el resultado en SQL."""
    model = request.app.state.model
    features = pd.DataFrame(
        [[getattr(payload, name) for name in config.FEATURES]], columns=config.FEATURES
    )
    is_healthy = bool(model.predict(features)[0] == 1)
    score = round(float(model.decision_function(features)[0]), 4)
    status_label = "NORMAL" if is_healthy else "ANOMALY_DETECTED"

    recorded_at = payload.recorded_at or utcnow()
    if recorded_at.tzinfo is not None:
        recorded_at = recorded_at.astimezone(timezone.utc).replace(tzinfo=None)

    try:
        _ensure_server(db, payload)
        record = TelemetryRecord(
            server_id=payload.server_id,
            cpu_utilization_pct=payload.cpu_utilization_pct,
            package_temp_c=payload.package_temp_c,
            dram_usage_gb=payload.dram_usage_gb,
            pcie_error_count=payload.pcie_error_count,
            status=status_label,
            is_healthy=is_healthy,
            anomaly_score=score,
            recorded_at=recorded_at,
        )
        db.add(record)
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        logger.exception("No se pudo guardar la lectura de %s", payload.server_id)
        raise HTTPException(status_code=503, detail="No se pudo guardar la lectura en la base de datos.")

    return HealthEvaluationResponse(
        server_id=payload.server_id,
        status=status_label,
        is_healthy=is_healthy,
        anomaly_score=score,
        evaluated_at=recorded_at,
    )


def _ensure_server(db: Session, payload: TelemetryPayload) -> None:
    """Registra el servidor en el inventario la primera vez que envía telemetría."""
    if db.get(Server, payload.server_id) is not None:
        return
    db.add(Server(
        server_id=payload.server_id,
        hostname=f"xeon-node-{payload.server_id.lower()}",
        rack_id=payload.rack_id or config.DEFAULT_RACK_ID,
    ))
    try:
        db.commit()
    except IntegrityError:
        # Otra petición concurrente registró el mismo servidor primero.
        db.rollback()


@app.get("/api/v1/servers/{server_id}/history", response_model=List[TelemetryRecordOut], tags=["Fleet Telemetry"])
def get_server_history(
    server_id: str,
    limit: int = Query(10, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Devuelve las lecturas más recientes de un servidor con su diagnóstico."""
    records = (
        db.query(TelemetryRecord)
        .filter(TelemetryRecord.server_id == server_id)
        .order_by(TelemetryRecord.recorded_at.desc())
        .limit(limit)
        .all()
    )
    if not records:
        raise HTTPException(status_code=404, detail=f"No se encontraron registros para el servidor '{server_id}'.")
    return records


@app.get("/api/v1/fleet/summary", response_model=List[ServerKpi], tags=["Fleet Telemetry"])
def get_fleet_summary(db: Session = Depends(get_db)):
    """KPIs por servidor, calculados con la misma consulta que alimenta a Power BI."""
    return [dict(row) for row in db.execute(text(QUERY_KPIS)).mappings()]


@app.post("/api/v1/cloud/export-datalake", tags=["Cloud Data Lake"])
def trigger_datalake_export(limit: int = Query(50, ge=1, le=10000), db: Session = Depends(get_db)):
    """Exporta al data lake particionado (year/month/day) los registros aún no exportados."""
    return exporter.export_batch_from_db(db=db, limit=limit)
