import time
import requests
import numpy as np

API_URL = "http://127.0.0.1:8000/api/v1/telemetry/ingest"
SERVERS = ["SRV-XEON-01", "SRV-XEON-02", "SRV-XEON-03", "SRV-XEON-04", "SRV-XEON-05"]

def generate_server_reading(server_id: str, inject_failure: bool = False):
    """
    Genera una lectura de telemetria simulando operacion normal 
    o un incidente critico de hardware.
    """
    if inject_failure:
        return {
            "server_id": server_id,
            "cpu_utilization_pct": float(np.round(np.random.uniform(92.0, 99.9), 2)),
            "package_temp_c": float(np.round(np.random.uniform(89.0, 101.5), 2)),
            "dram_usage_gb": float(np.round(np.random.uniform(110.0, 126.0), 2)),
            "pcie_error_count": int(np.random.randint(5, 20))
        }
    return {
        "server_id": server_id,
        "cpu_utilization_pct": float(np.round(np.random.normal(45.0, 10.0), 2)),
        "package_temp_c": float(np.round(np.random.normal(54.0, 5.0), 2)),
        "dram_usage_gb": float(np.round(np.random.normal(32.0, 4.0), 2)),
        "pcie_error_count": int(np.random.poisson(0.02))
    }

def run_simulation(total_requests: int = 150):
    print(f"==================================================")
    print(f"[Simulator] Iniciando envio de {total_requests} lecturas de flota a la API...")
    print(f"==================================================")
    successful = 0

    for i in range(total_requests):
        srv = str(np.random.choice(SERVERS))
        # 10% de probabilidad de inyectar falla
        is_failing = bool(np.random.rand() < 0.10)
        payload = generate_server_reading(srv, inject_failure=is_failing)

        try:
            res = requests.post(API_URL, json=payload, timeout=2.0)
            if res.status_code == 200:
                data = res.json()
                status_icon = "🟢 NORMAL" if data['status'] == "NORMAL" else "🔴 ANOMALIA"
                print(f"[{i+1:03d}/{total_requests}] {srv} -> {status_icon} (Score: {data['anomaly_score']:.4f})")
                successful += 1
            else:
                print(f"[{i+1:03d}/{total_requests}] Error {res.status_code}: {res.text}")
        except Exception as e:
            print(f"Error critico de conexion con la API: {e}")
            print("Asegurate de que Uvicorn este corriendo en http://127.0.0.1:8000")
            break

        time.sleep(0.04) # 40 ms de pausa entre envios

    print(f"==================================================")
    print(f"[Simulator] Simulacion finalizada exitosamente.")
    print(f"[Simulator] {successful}/{total_requests} lecturas procesadas y persistidas en SQL.")
    print(f"==================================================")

if __name__ == "__main__":
    run_simulation(150)