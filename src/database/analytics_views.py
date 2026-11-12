"""Consultas analíticas en SQL y exportación de los CSV que consume Power BI."""
import os

import pandas as pd
from sqlalchemy import text

from src import config
from src.database.connection import engine

# Dataset maestro: cada lectura con los datos de su servidor.
QUERY_MASTER = """
SELECT
    t.id AS record_id,
    t.server_id,
    s.hostname,
    s.rack_id,
    s.processor_model,
    t.cpu_utilization_pct,
    t.package_temp_c,
    t.dram_usage_gb,
    t.pcie_error_count,
    t.status,
    t.is_healthy,
    t.anomaly_score,
    t.recorded_at
FROM telemetry_records t
INNER JOIN servers s ON t.server_id = s.server_id
ORDER BY t.recorded_at DESC;
"""

# KPIs por servidor. `uptime_pct` es la proporción de lecturas clasificadas como normales.
QUERY_KPIS = """
SELECT
    s.server_id,
    s.rack_id,
    COUNT(t.id) AS total_readings,
    COALESCE(SUM(CASE WHEN t.is_healthy = 1 THEN 1 ELSE 0 END), 0) AS healthy_readings,
    COALESCE(SUM(CASE WHEN t.is_healthy = 0 THEN 1 ELSE 0 END), 0) AS anomaly_incidents,
    ROUND(SUM(CASE WHEN t.is_healthy = 1 THEN 1.0 ELSE 0.0 END) / COUNT(t.id) * 100, 2) AS uptime_pct,
    ROUND(AVG(t.cpu_utilization_pct), 2) AS avg_cpu_pct,
    ROUND(AVG(t.package_temp_c), 2) AS avg_temp_c,
    MAX(t.package_temp_c) AS max_temp_c,
    SUM(t.pcie_error_count) AS total_pcie_errors
FROM servers s
LEFT JOIN telemetry_records t ON s.server_id = t.server_id
GROUP BY s.server_id, s.rack_id
ORDER BY s.server_id;
"""


def fetch_master(conn) -> pd.DataFrame:
    return pd.read_sql(text(QUERY_MASTER), conn)


def fetch_kpis(conn) -> pd.DataFrame:
    return pd.read_sql(text(QUERY_KPIS), conn)


def generate_bi_export(output_dir: str = config.PROCESSED_DIR) -> dict:
    """Escribe fleet_master_telemetry.csv y fleet_server_kpis.csv y devuelve sus rutas."""
    os.makedirs(output_dir, exist_ok=True)
    with engine.connect() as conn:
        df_master = fetch_master(conn)
        df_kpis = fetch_kpis(conn)

    paths = {
        "master": os.path.join(output_dir, "fleet_master_telemetry.csv"),
        "kpis": os.path.join(output_dir, "fleet_server_kpis.csv"),
    }
    df_master.to_csv(paths["master"], index=False)
    df_kpis.to_csv(paths["kpis"], index=False)
    return {"paths": paths, "kpis": df_kpis, "rows": len(df_master)}


if __name__ == "__main__":
    result = generate_bi_export()
    print("\n=== Resumen de la flota (SQL Analytics) ===")
    print(result["kpis"].to_string(index=False))
    print(f"\n[BI Engine] {result['rows']} lecturas exportadas en:")
    for path in result["paths"].values():
        print(f" - {path}")
