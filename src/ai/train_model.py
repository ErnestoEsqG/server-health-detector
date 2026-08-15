import os
import joblib
import pandas as pd
from sklearn.ensemble import IsolationForest
from src.utils.telemetry_generator import IntelFleetTelemetryGenerator

class ServerHealthModelTrainer:
    """
    Entrenador de modelos de detección de anomalías para telemetría de servidores Intel Xeon.
    Aprende patrones multivariables de CPU, Temperatura, Memoria y Bus PCIe.
    """
    def __init__(self, contamination: float = 0.05, random_state: int = 42):
        """
        :param contamination: Proporción esperada de anomalías en el dataset (0.05 = 5%).
        :param random_state: Semilla para garantizar reproducibilidad en los árboles aleatorios.
        """
        self.contamination = contamination
        self.features = ['cpu_utilization_pct', 'package_temp_c', 'dram_usage_gb', 'pcie_error_count']
        
        # Instanciar el algoritmo de Isolation Forest
        self.model = IsolationForest(
            n_estimators=100,           # Cantidad de árboles en el bosque
            max_samples='auto',         # Muestras por árbol
            contamination=self.contamination,
            random_state=random_state,
            n_jobs=-1                   # Usa todos los núcleos del CPU para entrenar en paralelo
        )

    def train_and_save(self, n_samples: int = 5000, output_path: str = "src/ai/intel_health_model.pkl") -> None:
        """
        Genera telemetría sintética, extrae la matriz de características X,
        entrena el modelo y lo serializa a disco con joblib.
        """
        print(f"[AI Engine] Generando {n_samples} lecturas de telemetría de flota...")
        generator = IntelFleetTelemetryGenerator()
        df = generator.generate_fleet_data(n_samples=n_samples, anomaly_ratio=self.contamination)

        # 1. Matriz de características (Feature Matrix X)
        # Nota: Descartamos 'timestamp' e 'is_simulated_anomaly' porque es no supervisado
        X = df[self.features]

        print(f"[AI Engine] Entrenando Isolation Forest con {len(self.features)} variables...")
        self.model.fit(X)

        # 2. Serialización / Guardado del artefacto binario (.pkl)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        joblib.dump(self.model, output_path)
        print(f"[AI Engine] Modelo exportado exitosamente en: {output_path}")

        # 3. Test de validación funcional (Inferencia de prueba)
        self._run_sanity_check()

    def _run_sanity_check(self) -> None:
        """
        Prueba dos vectores sintéticos extremos para comprobar que el modelo infiere correctamente.
        """
        test_data = pd.DataFrame([
            [42.0, 52.0, 30.0, 0],    # Servidor Sano (CPU 42%, Temp 52°C, RAM 30GB, 0 PCIe errors)
            [99.0, 96.5, 122.0, 18]   # Servidor en Estrés/Falla (CPU 99%, Temp 96.5°C, RAM 122GB, 18 PCIe errors)
        ], columns=self.features)

        # scikit-learn Isolation Forest retorna: 1 para Inlier (Normal) y -1 para Outlier (Anomalía)
        predictions = self.model.predict(test_data)
        
        # decision_function retorna la puntuación (valores negativos indican mayor anomalía)
        scores = self.model.decision_function(test_data)

        print("\n--- Verificación Funcional del Modelo (Inferencia) ---")
        labels = {1: "NORMAL (Inlier)", -1: "ANOMALÍA DETECTADA (Outlier)"}
        
        for i, (pred, score) in enumerate(zip(predictions, scores)):
            status = labels[pred]
            tipo = "Servidor Sano" if i == 0 else "Servidor en Falla Crítica"
            print(f"[{tipo}] -> Diagnóstico: {status} | Score de Decisión: {score:.4f}")

if __name__ == "__main__":
    trainer = ServerHealthModelTrainer()
    trainer.train_and_save()