import os
import pandas as pd
from sqlalchemy import text
from src.database.connection import engine

def generate_bi_export():
    """
    Ejecuta consultas analíticas avanzadas en SQL para extraer el dataset maestro
    y calcular los KPIs de disponibilidad para Power BI.
    """
    os.makedirs("data/processed", exist_ok=True)

    # 1. Consulta Maestra (Join de Servidores y Telemetría)
    query_master = """
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

    # 2. Consulta de Agregación de KPIs por Servidor
    query_kpis = """
    SELECT 
        s.server_id,
        s.rack_id,
        COUNT(t.id) AS total_readings,
        SUM(CASE WHEN t.is_healthy = 1 THEN 1 ELSE 0 END) AS healthy_readings,
        SUM(CASE WHEN t.is_healthy = 0 THEN 1 ELSE 0 END) AS anomaly_incidents,
        ROUND((CAST(SUM(CASE WHEN t.is_healthy = 1 THEN 1 ELSE 0 END) AS FLOAT) / COUNT(t.id)) * 100, 2) AS uptime_pct,
        ROUND(AVG(t.cpu_utilization_pct), 2) AS avg_cpu_pct,
        ROUND(AVG(t.package_temp_c), 2) AS avg_temp_c,
        MAX(t.package_temp_c) AS max_temp_c,
        SUM(t.pcie_error_count) AS total_pcie_errors
    FROM servers s
    LEFT JOIN telemetry_records t ON s.server_id = t.server_id
    GROUP BY s.server_id, s.rack_id;
    """

    with engine.connect() as conn:
        df_master = pd.read_sql(text(query_master), conn)
        df_kpis = pd.read_sql(text(query_kpis), conn)

    # Guardar CSVs procesados para consumo directo en Power BI
    master_path = "data/processed/fleet_master_telemetry.csv"
    kpi_path = "data/processed/fleet_server_kpis.csv"

    df_master.to_csv(master_path, index=False)
    df_kpis.to_csv(kpi_path, index=False)

    print("\n=======================================================")
    print("📊 RESUMEN EJECUTIVO DE LA FLOTA (SQL Analytics)")
    print("=======================================================")
    print(df_kpis.to_string(index=False))
    print("=======================================================")
    print(f"\n[BI Engine] Archivos analíticos exportados exitosamente en:")
    print(f" - {master_path}")
    print(f" - {kpi_path}\n")

if __name__ == "__main__":
    generate_bi_export()