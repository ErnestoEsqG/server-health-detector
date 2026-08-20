import os
import joblib
import pandas as pd
from datetime import datetime
from typing import List
from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy.orm import Session

from src.api.schemas import TelemetryPayload, HealthEvaluationResponse
from src.database.connection import engine, Base, get_db
from src.database.models import Server, TelemetryRecord

# 1. Crear tablas en la base de datos SQL automaticamente al iniciar
Base.metadata.create_all(bind=engine)

# 2. Instanciar la aplicacion FastAPI
app = FastAPI(
    title="Intel Server Fleet Health API",
    description="REST API para ingestion de telemetria en tiempo real, evaluacion con IA y persistencia en SQL.",
    version="1.1.0"
)

# 3. Cargar el modelo en memoria
MODEL_PATH = "src/ai/intel_health_model.pkl"
if not os.path.exists(MODEL_PATH):
    raise RuntimeError(f"Error critico: No se encontro el archivo de modelo en '{MODEL_PATH}'.")

model = joblib.load(MODEL_PATH)
features = ['cpu_utilization_pct', 'package_temp_c', 'dram_usage_gb', 'pcie_error_count']

# 4. Endpoints

@app.get("/health", tags=["System"])
def health_check():
    return {"status": "ONLINE", "model_loaded": True, "database": "CONNECTED", "timestamp": datetime.now()}

@app.post("/api/v1/telemetry/ingest", response_model=HealthEvaluationResponse, tags=["Fleet Telemetry"])
def evaluate_and_store_telemetry(payload: TelemetryPayload, db: Session = Depends(get_db)):
    """
    Recibe telemetria, ejecuta inferencia con IA y guarda el resultado en la base de datos SQL.
    """
    try:
        # Inferencia con IA
        input_data = pd.DataFrame([[
            payload.cpu_utilization_pct,
            payload.package_temp_c,
            payload.dram_usage_gb,
            payload.pcie_error_count
        ]], columns=features)

        prediction = model.predict(input_data)[0]
        score = float(model.decision_function(input_data)[0])
        is_healthy = True if prediction == 1 else False
        status_label = "NORMAL" if is_healthy else "ANOMALY_DETECTED"

        # Persistencia en SQL: Verificar si el servidor ya existe en el inventario
        server_entry = db.query(Server).filter(Server.server_id == payload.server_id).first()
        if not server_entry:
            server_entry = Server(
                server_id=payload.server_id,
                hostname=f"xeon-node-{payload.server_id.lower()}",
                rack_id="RACK-ZAP-01"
            )
            db.add(server_entry)
            db.commit()

        # Guardar el registro de telemetria evaluado
        record = TelemetryRecord(
            server_id=payload.server_id,
            cpu_utilization_pct=payload.cpu_utilization_pct,
            package_temp_c=payload.package_temp_c,
            dram_usage_gb=payload.dram_usage_gb,
            pcie_error_count=payload.pcie_error_count,
            status=status_label,
            is_healthy=is_healthy,
            anomaly_score=round(score, 4),
            recorded_at=datetime.utcnow()
        )
        db.add(record)
        db.commit()
        db.refresh(record)

        return HealthEvaluationResponse(
            server_id=payload.server_id,
            status=status_label,
            is_healthy=is_healthy,
            anomaly_score=round(score, 4),
            evaluated_at=record.recorded_at
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno procesando persistencia: {str(e)}")

@app.get("/api/v1/servers/{server_id}/history", tags=["Fleet Telemetry"])
def get_server_history(server_id: str, limit: int = 10, db: Session = Depends(get_db)):
    """
    Consulta en SQL los ultimos registros de telemetria y estado de salud de un servidor especifico.
    """
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