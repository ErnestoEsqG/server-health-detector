"""Entrenamiento y carga del modelo Isolation Forest."""
import logging
import os

import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest

from src import config
from src.utils.telemetry_generator import IntelFleetTelemetryGenerator

logger = logging.getLogger(__name__)


class ServerHealthModelTrainer:
    """Entrena un Isolation Forest sobre telemetría multivariable sin usar etiquetas."""

    def __init__(
        self,
        contamination: float = config.IFOREST_CONTAMINATION,
        random_state: int = config.IFOREST_RANDOM_STATE,
    ):
        self.contamination = contamination
        self.features = config.FEATURES
        self.model = IsolationForest(
            n_estimators=config.IFOREST_N_ESTIMATORS,
            max_samples="auto",  # min(256, n_muestras) por árbol
            contamination=self.contamination,
            random_state=random_state,
            n_jobs=-1,
        )

    def train(self, n_samples: int = config.TRAINING_SAMPLES) -> IsolationForest:
        """Genera telemetría sintética y ajusta el modelo solo con las métricas."""
        df = IntelFleetTelemetryGenerator().generate_fleet_data(
            n_samples=n_samples, anomaly_ratio=self.contamination
        )
        self.model.fit(df[self.features])
        return self.model

    def train_and_save(
        self, n_samples: int = config.TRAINING_SAMPLES, output_path: str = config.MODEL_PATH
    ) -> IsolationForest:
        logger.info("Entrenando Isolation Forest con %d lecturas y %d variables",
                    n_samples, len(self.features))
        self.train(n_samples)
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        joblib.dump(self.model, output_path)
        logger.info("Modelo guardado en %s", output_path)
        return self.model

    def sanity_check(self) -> pd.DataFrame:
        """Evalúa dos vectores extremos para comprobar que el modelo responde como se espera."""
        cases = pd.DataFrame(
            [[42.0, 52.0, 30.0, 0], [99.0, 96.5, 122.0, 18]], columns=self.features
        )
        cases["prediction"] = self.model.predict(cases[self.features])  # 1 normal, -1 anomalía
        cases["score"] = self.model.decision_function(cases[self.features])
        return cases


def load_or_train_model(path: str = config.MODEL_PATH) -> IsolationForest:
    """Carga el modelo serializado; si no existe, lo entrena y lo guarda.

    El artefacto .pkl no se versiona, así que un clon nuevo del repositorio
    arranca sin pasos manuales.
    """
    if os.path.exists(path):
        return joblib.load(path)
    logger.warning("No se encontró el modelo en %s; se entrena uno nuevo.", path)
    return ServerHealthModelTrainer().train_and_save(output_path=path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[AI Engine] %(message)s")
    trainer = ServerHealthModelTrainer()
    trainer.train_and_save()
    print("\n--- Verificación funcional del modelo ---")
    for label, (_, row) in zip(("Servidor sano", "Servidor en falla crítica"),
                               trainer.sanity_check().iterrows()):
        status = "NORMAL" if row["prediction"] == 1 else "ANOMALÍA DETECTADA"
        print(f"[{label}] -> {status} | score de decisión: {row['score']:.4f}")
