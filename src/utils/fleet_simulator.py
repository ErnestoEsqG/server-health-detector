"""Simulador de flota: envía lecturas a la API como lo haría un agente de telemetría.

Ejemplos:
    python -m src.utils.fleet_simulator                         # 150 lecturas, 10 % críticas
    python -m src.utils.fleet_simulator --subtle-rate 0.10      # añade degradaciones sutiles
    python -m src.utils.fleet_simulator -n 500 --spread-hours 48 --delay 0
"""
import argparse
import time
from datetime import datetime, timedelta, timezone

import numpy as np
import requests

from src.utils.telemetry_generator import CRITICAL_SCENARIOS, SUBTLE_SCENARIOS, sample_readings

DEFAULT_API_URL = "http://127.0.0.1:8000"
SERVER_RACKS = {
    "SRV-XEON-01": "RACK-ZAP-01",
    "SRV-XEON-02": "RACK-ZAP-01",
    "SRV-XEON-03": "RACK-ZAP-01",
    "SRV-XEON-04": "RACK-ZAP-02",
    "SRV-XEON-05": "RACK-ZAP-02",
}
SERVERS = list(SERVER_RACKS)
ICONS = {"NORMAL": "🟢 NORMAL", "ANOMALY_DETECTED": "🔴 ANOMALIA"}


def generate_server_reading(server_id: str, scenario: str = "normal", rng: np.random.Generator = None) -> dict:
    """Genera el payload de una lectura para el escenario indicado."""
    rng = rng or np.random.default_rng()
    row = sample_readings(scenario, 1, rng).iloc[0]
    return {
        "server_id": server_id,
        "rack_id": SERVER_RACKS.get(server_id),
        "cpu_utilization_pct": float(row["cpu_utilization_pct"]),
        "package_temp_c": float(row["package_temp_c"]),
        "dram_usage_gb": float(row["dram_usage_gb"]),
        "pcie_error_count": int(row["pcie_error_count"]),
    }


def pick_scenario(rng: np.random.Generator, failure_rate: float, subtle_rate: float) -> str:
    draw = rng.random()
    if draw < failure_rate:
        return str(rng.choice(CRITICAL_SCENARIOS))
    if draw < failure_rate + subtle_rate:
        return str(rng.choice(SUBTLE_SCENARIOS))
    return "normal"


def run_simulation(
    total_requests: int = 150,
    api_url: str = DEFAULT_API_URL,
    failure_rate: float = 0.10,
    subtle_rate: float = 0.0,
    delay: float = 0.04,
    spread_hours: float = 0.0,
    seed: int = None,
) -> dict:
    """Envía `total_requests` lecturas y devuelve el conteo por escenario y por diagnóstico."""
    rng = np.random.default_rng(seed)
    endpoint = f"{api_url.rstrip('/')}/api/v1/telemetry/ingest"
    start = datetime.now(timezone.utc) - timedelta(hours=spread_hours)
    step = timedelta(hours=spread_hours) / max(total_requests, 1)
    summary = {"sent": 0, "ok": 0, "by_scenario": {}}

    print(f"[Simulator] Enviando {total_requests} lecturas a {endpoint}")
    with requests.Session() as session:
        for i in range(total_requests):
            server = str(rng.choice(SERVERS))
            scenario = pick_scenario(rng, failure_rate, subtle_rate)
            payload = generate_server_reading(server, scenario, rng)
            if spread_hours:
                # Reparte las mediciones en el tiempo para que el tablero muestre una tendencia.
                payload["recorded_at"] = (start + step * i).isoformat()

            try:
                res = session.post(endpoint, json=payload, timeout=5.0)
            except requests.RequestException as exc:
                print(f"[Simulator] Sin conexión con la API: {exc}")
                print(f"[Simulator] Verifica que Uvicorn esté corriendo en {api_url}")
                break

            summary["sent"] += 1
            counts = summary["by_scenario"].setdefault(scenario, {"sent": 0, "flagged": 0})
            counts["sent"] += 1
            if res.status_code != 200:
                print(f"[{i + 1:04d}/{total_requests}] Error {res.status_code}: {res.text}")
                continue

            data = res.json()
            summary["ok"] += 1
            counts["flagged"] += data["status"] != "NORMAL"
            print(f"[{i + 1:04d}/{total_requests}] {server} {scenario:<22} -> "
                  f"{ICONS.get(data['status'], data['status'])} (score: {data['anomaly_score']:.4f})")
            if delay:
                time.sleep(delay)

    print(f"[Simulator] {summary['ok']}/{total_requests} lecturas procesadas y guardadas en SQL.")
    for scenario, counts in sorted(summary["by_scenario"].items()):
        print(f"  {scenario:<22} enviadas: {counts['sent']:>4}  marcadas como anomalía: {counts['flagged']:>4}")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulador de telemetría de flota")
    parser.add_argument("-n", "--requests", type=int, default=150, help="lecturas a enviar")
    parser.add_argument("--url", default=DEFAULT_API_URL, help="URL base de la API")
    parser.add_argument("--failure-rate", type=float, default=0.10, help="proporción de fallas críticas")
    parser.add_argument("--subtle-rate", type=float, default=0.0, help="proporción de degradaciones sutiles")
    parser.add_argument("--delay", type=float, default=0.04, help="pausa entre envíos, en segundos")
    parser.add_argument("--spread-hours", type=float, default=0.0,
                        help="reparte las marcas de tiempo en las últimas N horas")
    parser.add_argument("--seed", type=int, default=None, help="semilla para repetir la simulación")
    args = parser.parse_args()
    run_simulation(args.requests, args.url, args.failure_rate, args.subtle_rate,
                   args.delay, args.spread_hours, args.seed)


if __name__ == "__main__":
    main()
