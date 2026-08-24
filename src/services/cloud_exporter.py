import os
import json
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from src.database.models import TelemetryRecord

class CloudDataLakeExporter:
    """
    Servicio encargado de empaquetar lotes de telemetria desde SQL
    y sincronizarlos hacia el Data Lake (Local o AWS S3 / Azure Blob).
    """
    def __init__(self, base_export_dir: str = "data/datalake", bucket_name: str = "intel-telemetry-datalake"):
        self.base_export_dir = base_export_dir
        self.bucket_name = bucket_name

    def export_batch_from_db(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """
        Extrae los registros mas recientes de la base de datos SQL y los guarda
        en la estructura particionada del Data Lake.
        """
        records = db.query(TelemetryRecord).order_by(TelemetryRecord.recorded_at.desc()).limit(limit).all()

        if not records:
            return {"status": "SKIPPED", "message": "No hay registros disponibles para exportar."}

        # Convertir modelos SQLAlchemy a diccionarios
        data_payload = [
            {
                "id": r.id,
                "server_id": r.server_id,
                "cpu_utilization_pct": r.cpu_utilization_pct,
                "package_temp_c": r.package_temp_c,
                "dram_usage_gb": r.dram_usage_gb,
                "pcie_error_count": r.pcie_error_count,
                "status": r.status,
                "is_healthy": r.is_healthy,
                "anomaly_score": r.anomaly_score,
                "recorded_at": r.recorded_at.isoformat()
            }
            for r in records
        ]

        # Particionamiento temporal estándar en Data Lakes: year=YYYY/month=MM/day=DD
        now = datetime.utcnow()
        partition_path = os.path.join(
            self.base_export_dir,
            f"year={now.year}",
            f"month={now.month:02d}",
            f"day={now.day:02d}"
        )
        os.makedirs(partition_path, exist_ok=True)

        filename = f"telemetry_batch_{now.strftime('%Y%m%d_%H%M%S')}.json"
        full_file_path = os.path.join(partition_path, filename)

        with open(full_file_path, "w", encoding="utf-8") as f:
            json.dump(data_payload, f, indent=2)

        return {
            "status": "SUCCESS",
            "exported_records": len(data_payload),
            "target_bucket": self.bucket_name,
            "lake_partition": f"year={now.year}/month={now.month:02d}/day={now.day:02d}",
            "file_path": full_file_path,
            "exported_at": now.isoformat()
        }