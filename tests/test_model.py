import numpy as np
import pytest

from src import config
from src.evaluation.model_benchmark import predict_model, predict_thresholds, run_benchmark
from src.utils.telemetry_generator import (
    ALL_SCENARIOS,
    FEATURES,
    IntelFleetTelemetryGenerator,
    sample_readings,
)


def test_generator_is_reproducible_and_labeled():
    a = IntelFleetTelemetryGenerator(seed=1).generate_fleet_data(500, 0.1)
    b = IntelFleetTelemetryGenerator(seed=1).generate_fleet_data(500, 0.1)
    assert a[FEATURES].equals(b[FEATURES])
    assert a["is_simulated_anomaly"].sum() == 50
    assert (a.loc[a["is_simulated_anomaly"] == 0, "anomaly_type"] == "normal").all()


@pytest.mark.parametrize("scenario", ALL_SCENARIOS)
def test_scenarios_respect_api_contract(scenario):
    df = sample_readings(scenario, 200, np.random.default_rng(0))
    assert df["cpu_utilization_pct"].between(0, 100).all()
    assert df["package_temp_c"].between(0, 120).all()
    assert (df["pcie_error_count"] >= 0).all()


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        sample_readings("meteorito", 1, np.random.default_rng(0))


def test_subtle_degradation_stays_below_static_thresholds():
    df = sample_readings("subtle_degradation", 500, np.random.default_rng(0))
    assert predict_thresholds(df).sum() == 0


def test_model_beats_thresholds_on_subtle_degradation(client):
    """Criterio central de la hipótesis: detectar lo que las reglas fijas no ven."""
    results = run_benchmark(n_mixed=4000, n_per_scenario=500)
    subtle = results["detection_rate_by_scenario"]["subtle_degradation"]
    assert subtle["isolation_forest"] >= 0.90
    assert subtle["static_thresholds"] == 0.0
    assert results["mixed_fleet"]["isolation_forest"]["f1"] >= 0.90
    assert results["detection_rate_by_scenario"]["normal"]["isolation_forest"] <= 0.10


def test_model_uses_configured_features(client):
    model = client.app.state.model
    assert list(model.feature_names_in_) == config.FEATURES
    healthy = sample_readings("normal", 300, np.random.default_rng(3))
    assert predict_model(model, healthy).mean() < 0.15
