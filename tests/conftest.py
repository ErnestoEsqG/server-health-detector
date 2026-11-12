import os
import tempfile

# La configuración se lee al importar `src`, así que el entorno aislado se
# prepara antes de cualquier importación del proyecto.
_TMP = tempfile.mkdtemp(prefix="shd-tests-")
os.environ["SHD_DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["SHD_MODEL_PATH"] = f"{_TMP}/model.pkl"
os.environ["SHD_DATALAKE_DIR"] = f"{_TMP}/datalake"
os.environ["SHD_PROCESSED_DIR"] = f"{_TMP}/processed"

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.database.connection import Base, engine


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:  # ejecuta el lifespan: crea tablas y entrena el modelo
        yield test_client


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield


@pytest.fixture
def healthy_payload():
    return {"server_id": "SRV-TEST-01", "cpu_utilization_pct": 45.5, "package_temp_c": 55.0,
            "dram_usage_gb": 32.0, "pcie_error_count": 0}


@pytest.fixture
def critical_payload():
    return {"server_id": "SRV-TEST-01", "cpu_utilization_pct": 99.0, "package_temp_c": 96.5,
            "dram_usage_gb": 122.0, "pcie_error_count": 18}
