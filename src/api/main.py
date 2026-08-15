import os
import joblib
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from src.api.schemas import TelemetryPayload, HealthEvaluationResponse

# 1. Instanciar la aplicacion FastAPI
app = FastAPI(
    title="Intel Server Fleet Health API",
    description="REST API para ingestion de telemetria en tiempo real y evaluacion de anomalias en hardware.",
    version="1.0.0"
)

# 2. Cargar el modelo serializado en memoria
MODEL_PATH = "src/ai/intel_health_model.pkl"

if not os.path.exists(MODEL_PATH):
    raise RuntimeError(f"Error critico: No se encontro el archivo de modelo en '{MODEL_PATH}'.")

model = joblib.load(MODEL_PATH)
features = ['cpu_utilization_pct', 'package_temp_c', 'dram_usage_gb', 'pcie_error_count']

# 3. Endpoints

@app.get("/health", tags=["System"])
def health_check():
    """Verifica que el servicio y el modelo esten en linea."""
    return {"status": "ONLINE", "model_loaded": True, "timestamp": datetime.now()}

@app.post("/api/v1/telemetry/ingest", response_model=HealthEvaluationResponse, tags=["Fleet Telemetry"])
def evaluate_telemetry(payload: TelemetryPayload):
    """
    Recibe la telemetria de un servidor, ejecuta la inferencia con Isolation Forest
    y devuelve el diagnostico de salud en tiempo real.
    """
    try:
        # Formatear el vector de entrada con las caracteristicas esperadas
        input_data = pd.DataFrame([[
            payload.cpu_utilization_pct,
            payload.package_temp_c,
            payload.dram_usage_gb,
            payload.pcie_error_count
        ]], columns=features)

        # Inferencia
        prediction = model.predict(input_data)[0]            # 1 = Normal, -1 = Anomalia
        score = float(model.decision_function(input_data)[0])

        is_healthy = True if prediction == 1 else False
        status_label = "NORMAL" if is_healthy else "ANOMALY_DETECTED"

        return HealthEvaluationResponse(
            server_id=payload.server_id,
            status=status_label,
            is_healthy=is_healthy,
            anomaly_score=round(score, 4),
            evaluated_at=datetime.now()
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno procesando telemetria: {str(e)}")