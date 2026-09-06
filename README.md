# Server Health Detector: Fleet Telemetry & Unsupervised Anomaly Detection

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Scikit-Learn](https://img.shields.io/badge/Scikit--Learn-Isolation%20Forest-F7931E?style=flat&logo=scikit-learn&logoColor=white)](https://scikit-learn.org/)
[![Power BI](https://img.shields.io/badge/Power%20BI-PBIP%20Versioned-F2C811?style=flat&logo=powerbi&logoColor=black)](https://powerbi.microsoft.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg?style=flat)](LICENSE)

An end-to-end data engineering, telemetry ingestion, and machine learning monitoring platform. The system ingests streaming hardware telemetry (CPU utilization, package thermal metrics, and PCIe transaction error counters), detects multivariate operational degradation using an unsupervised Isolation Forest model, persists structured logs into a local datalake/SQLite store, and surfaces operational health via an enterprise-grade Power BI Network Operations Center (NOC) dashboard versioned through `.pbip`.

---

## 📸 System Previews

| Network Operations Center (NOC) Dashboard | Real-Time API Inference (FastAPI Swagger UI) |
| :---: | :---: |
| ![NOC Dashboard](docs/assets/dashboard_overview.png) | ![FastAPI Docs](docs/assets/fastapi_docs.png) |

---

## 🏛 System Architecture & Workflow

The architecture handles the lifecycle from low-level hardware simulation to executive visual diagnostics:

```text
[Synthetic Telemetry Agent]
         │ (Package Temp, CPU %, PCIe Errors, Server Metadata)
         ▼
[FastAPI Ingestion Endpoint] ──> [Scikit-Learn Isolation Forest]
         │                                   │ (Anomaly Score / Status)
         ▼                                   ▼
[Relational Database (SQLite)] ──> [Partitioned JSON Datalake Layer]
         │
         ▼
[Analytical SQL Views / CSV Export]
         │
         ▼
[Power BI NOC Dashboard (.pbip)]
```

1. **Hardware Telemetry Simulation (`src/utils/`):** Generates realistic multivariate time-series data reflecting server behavior under standard compute loads as well as severe hardware failure scenarios (thermal throttling, fan failure, bus error saturation).
2. **Unsupervised ML Engine (`src/ai/`):** Utilizes an Isolation Forest algorithm to detect anomalous hardware states without requiring manual static thresholds or pre-labeled operational incidents.
3. **RESTful Service Layer (`src/api/`):** Asynchronous API built with FastAPI providing payload schema validation via Pydantic, low-latency model inference, and persistence handling.
4. **Storage & Datalake (`data/` & `src/database/`):** Implements a two-tier storage layer:
   * **Transactional:** SQLite instance storing validated telemetry, scoring results, and server hardware metadata.
   * **Analytical:** Partitioned JSON datalake (`year=YYYY/month=MM/day=DD`) and processed CSV views (`fleet_master_telemetry.csv`, `fleet_server_kpis.csv`).
5. **Modern Power BI Integration (`dashboard/`):** Fully versioned dashboard using Microsoft Power BI Project (`.pbip`) format, separating semantic modeling (`.SemanticModel`) from visual definitions (`.Report`) for transparent Git source control.

---

## 🛠 Tech Stack

* **Programming Language:** Python 3.10+
* **Machine Learning & Data Science:** Scikit-Learn (Isolation Forest), NumPy, Pandas
* **API Development:** FastAPI, Uvicorn, Pydantic
* **Persistence & Modeling:** SQLite, SQLAlchemy, Partitioned JSON Datalake
* **Business Intelligence:** Microsoft Power BI Desktop (PBIP Git-integrated format)
* **Environment & Tools:** Git, GitHub, Virtualenv

---

## 📁 Repository Structure

```text
server-health-detector/
├── .gitignore                      # Git exclusion rules for virtual environments, caches, and DBs
├── README.md                       # Comprehensive architecture and usage documentation
├── requirements.txt                # Pinned production and development dependencies
├── telemetry.db                    # [Git-Ignored] Local SQLite relational database instance
├── .venv/                          # [Git-Ignored] Python virtual environment binaries & packages
├── config/                         # Pipeline thresholds and environment configurations
├── docs/
│   └── assets/                     # Architecture previews and documentation media
│       ├── dashboard_overview.png  # NOC Power BI interface overview screenshot
│       └── fastapi_docs.png        # Interactive Swagger UI endpoint screenshot
├── data/                           # [Git-Ignored] Raw and transformed data storage
│   ├── datalake/                   # Daily partitioned streaming telemetry (year=YYYY/month=MM/day=DD)
│   │   └── year=2026/month=08/day=24/
│   │       └── telemetry_batch_20260824_232803.json
│   └── processed/                  # Analytical batch exports for business intelligence
│       ├── fleet_master_telemetry.csv
│       └── fleet_server_kpis.csv
├── server-health-detector/         # Power BI Project (PBIP) Git-versioned artifacts
│   ├── .gitignore                  # Power BI desktop local cache exclusion rules
│   ├── fleet_health_dashboard.pbip # Main entry point for Power BI Desktop
│   ├── fleet_health_dashboard.Report/         # Visual layouts, themes, and page configurations
│   └── fleet_health_dashboard.SemanticModel/  # TMDL schemas, data relationships, and DAX measures
├── src/
│   ├── ai/                         # Machine learning model pipeline
│   │   ├── __pycache__/            # [Git-Ignored] Compiled Python bytecode (.pyc)
│   │   ├── intel_health_model.pkl  # [Git-Ignored] Serialized scikit-learn Isolation Forest model
│   │   └── train_model.py          # Isolation Forest unsupervised training & serialization
│   ├── api/                        # REST API routing and inference service
│   │   ├── __pycache__/            # [Git-Ignored] Compiled Python bytecode (.pyc)
│   │   ├── main.py                 # FastAPI application, routing, and scoring endpoints
│   │   └── schemas.py              # Pydantic data contracts and validation models
│   ├── database/                   # Storage orchestration and relational models
│   │   ├── __init__.py
│   │   ├── __pycache__/            # [Git-Ignored] Compiled Python bytecode (.pyc)
│   │   ├── analytics_views.py      # Analytical SQL aggregation queries and KPI views
│   │   ├── connection.py           # Database engine setup and session management
│   │   └── models.py               # SQLAlchemy ORM table definitions
│   ├── services/                   # Background data processing services
│   │   ├── __init__.py
│   │   ├── __pycache__/            # [Git-Ignored] Compiled Python bytecode (.pyc)
│   │   └── cloud_exporter.py       # Batch data lake export and aggregation service
│   └── utils/                      # Simulation and mock telemetry generators
│       ├── __pycache__/            # [Git-Ignored] Compiled Python bytecode (.pyc)
│       ├── fleet_simulator.py      # Real-time streaming load simulator for API stress testing
│       └── telemetry_generator.py  # Synthetic telemetry generator injecting hardware degradation
└── tests/                          # Automated unit and integration test suite
    └── .pytest_cache/              # [Git-Ignored] Pytest runtime cache and status records