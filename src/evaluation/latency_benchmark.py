"""Mide la latencia del endpoint de ingesta contra una API en ejecución.

    uvicorn src.api.main:app            # en otra terminal
    python -m src.evaluation.latency_benchmark --requests 1000
"""
import argparse
import json
import os
import platform
import time

import numpy as np
import requests

from src.utils.fleet_simulator import DEFAULT_API_URL, SERVERS, generate_server_reading


def run_benchmark(api_url: str = DEFAULT_API_URL, total_requests: int = 1000, warmup: int = 20) -> dict:
    endpoint = f"{api_url.rstrip('/')}/api/v1/telemetry/ingest"
    rng = np.random.default_rng(7)
    client_ms, server_ms, errors = [], [], 0

    with requests.Session() as session:
        for i in range(warmup + total_requests):
            payload = generate_server_reading(str(rng.choice(SERVERS)), "normal", rng)
            start = time.perf_counter()
            res = session.post(endpoint, json=payload, timeout=10.0)
            elapsed = (time.perf_counter() - start) * 1000
            if i < warmup:
                continue
            if res.status_code != 200:
                errors += 1
                continue
            client_ms.append(elapsed)
            if "X-Process-Time-Ms" in res.headers:
                server_ms.append(float(res.headers["X-Process-Time-Ms"]))

    def stats(values):
        if not values:
            return None
        arr = np.array(values)
        p50, p95, p99 = np.percentile(arr, [50, 95, 99])
        return {"mean": round(float(arr.mean()), 2), "p50": round(float(p50), 2),
                "p95": round(float(p95), 2), "p99": round(float(p99), 2),
                "max": round(float(arr.max()), 2)}

    return {
        "endpoint": endpoint,
        "requests": total_requests,
        "errors": errors,
        "under_100ms_pct": round(float(np.mean(np.array(client_ms) < 100) * 100), 2) if client_ms else None,
        "client_latency_ms": stats(client_ms),
        "server_latency_ms": stats(server_ms),
        "environment": {"python": platform.python_version(), "machine": platform.machine(),
                        "system": platform.system(), "cpu_count": os.cpu_count()},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de latencia de la ingesta")
    parser.add_argument("--url", default=DEFAULT_API_URL)
    parser.add_argument("--requests", type=int, default=1000)
    parser.add_argument("--output", default="docs/results/latency_benchmark.json")
    args = parser.parse_args()

    results = run_benchmark(args.url, args.requests)
    print(json.dumps(results, indent=2))
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResultados guardados en {args.output}")


if __name__ == "__main__":
    main()
