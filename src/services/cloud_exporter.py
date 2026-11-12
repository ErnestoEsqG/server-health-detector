import json
import os
from typing import Any, Dict

from sqlalchemy.orm import Session

from src import config
from src.database.models import ExportCheckpoint, TelemetryRecord, utcnow


class CloudDataLakeExporter:
    """Exporta lotes de telemetría desde SQL a un data lake particionado por fecha.

    El destino es el sistema de archivos local, con el mismo esquema de
    particiones (year=/month=/day=) que usaría un almacenamiento de objetos,
    de modo que migrar a S3 o Azure Blob solo requiere cambiar la escritura.
    """

    def __init__(self, base_export_dir: str = config.DATALAKE_DIR):
        self.base_export_dir = base_export_dir

    def export_batch_from_db(self, db: Session, limit: int = 100) -> Dict[str, Any]:
        """Exporta hasta `limit` registros que todavía no se han enviado al data lake."""
        checkpoint = db.get(ExportCheckpoint, 1)
        last_id = checkpoint.last_record_id if checkpoint else 0

        records = (
            db.query(TelemetryRecord)
            .filter(TelemetryRecord.id > last_id)
            .order_by(TelemetryRecord.id)
            .limit(limit)
            .all()
        )
        if not records:
            return {"status": "SKIPPED", "message": "No hay registros nuevos para exportar."}

        payload = [
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
                "recorded_at": r.recorded_at.isoformat(),
            }
            for r in records
        ]

        now = utcnow()
        partition = f"year={now.year}/month={now.month:02d}/day={now.day:02d}"
        partition_path = os.path.join(self.base_export_dir, *partition.split("/"))
        os.makedirs(partition_path, exist_ok=True)
        file_path = os.path.join(
            partition_path, f"telemetry_batch_{now.strftime('%Y%m%d_%H%M%S_%f')}.json"
        )
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # El checkpoint avanza solo después de escribir el archivo.
        if checkpoint is None:
            checkpoint = ExportCheckpoint(id=1)
            db.add(checkpoint)
        checkpoint.last_record_id = records[-1].id
        db.commit()

        return {
            "status": "SUCCESS",
            "exported_records": len(payload),
            "first_record_id": records[0].id,
            "last_record_id": records[-1].id,
            "storage_backend": "local",
            "lake_partition": partition,
            "file_path": file_path,
            "exported_at": now.isoformat(),
        }
