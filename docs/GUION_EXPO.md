# Guion de exposición: Server Health Detector

Guion para una presentación de 5 minutos con demostración en vivo, más una versión de 1 minuto para quien se acerque al stand. Los tiempos son aproximados; conviene ensayarlo con cronómetro.

La explicación detallada de cada concepto está en [GUIA.md](GUIA.md).

---

## Antes de empezar (preparación, 5 minutos antes)

1. Iniciar la API: `uvicorn src.api.main:app`
2. Abrir en el navegador http://127.0.0.1:8000/docs y dejar desplegado *POST /api/v1/telemetry/ingest*.
3. Tener una segunda terminal lista, con el entorno activado y letra grande.
4. Tener Power BI abierto con el tablero ya actualizado.
5. Tener a la mano la imagen `docs/assets/guia_punto_ciego.png` (impresa en el cartel o en pantalla).
6. Plan B si algo falla: las capturas de `docs/assets/` cuentan la misma historia sin ejecutar nada.

---

## Versión de 5 minutos

### 1. El gancho (30 segundos)

> "Imaginen un servidor que casi no está trabajando: su procesador va al 15 %. Pero está a 70 grados y de vez en cuando reporta errores de comunicación interna. Para un sistema de monitoreo tradicional, todo está en verde: ningún número rebasa su límite. Y sin embargo, ese servidor nos está avisando que algo anda mal. Nuestro proyecto escucha ese aviso."

### 2. El problema (45 segundos)

*Mostrar la imagen del punto ciego.*

> "El monitoreo tradicional usa umbrales fijos: avisa si la CPU pasa de 90 % o la temperatura de 85 grados. Esta zona azul es todo lo que esas reglas consideran seguro. Las fallas graves, arriba a la derecha, sí las detectan, pero cuando el daño ya está en curso. Este otro grupo, abajo, es una degradación que apenas empieza: está dentro de la zona segura, así que las reglas no la ven. Según el Uptime Institute, más de la mitad de las interrupciones graves en centros de datos cuestan arriba de cien mil dólares. Detectar antes vale dinero."

### 3. La solución (60 segundos)

*Mostrar el diagrama de arquitectura.*

> "Server Health Detector tiene cuatro piezas. Primera: una API hecha con FastAPI que recibe las mediciones de cada servidor: CPU, temperatura, memoria y errores del bus PCIe. Segunda: un modelo de aprendizaje automático llamado Isolation Forest, que analiza las cuatro métricas juntas. Tercera: una base de datos donde queda guardada cada lectura con su diagnóstico. Y cuarta: un tablero en Power BI para el equipo de operaciones."

> "¿Cómo decide el modelo? No le enseñamos qué es una falla, porque casi nunca hay ejemplos de fallas etiquetadas. Lo que hace es medir qué tan fácil es separar una lectura de las demás con cortes al azar. Una lectura normal está rodeada de otras parecidas y cuesta muchos cortes aislarla. Una lectura rara queda sola con dos o tres. Lo raro se delata solo."

### 4. Demostración en vivo (90 segundos)

**Paso 1: un servidor sano.** En `/docs`, pegar y ejecutar:

```json
{"server_id": "SRV-DEMO", "cpu_utilization_pct": 45, "package_temp_c": 55, "dram_usage_gb": 32, "pcie_error_count": 0}
```

> "Un servidor sano. Responde NORMAL, con puntuación positiva."

**Paso 2: el servidor del inicio.** Pegar y ejecutar:

```json
{"server_id": "SRV-DEMO", "cpu_utilization_pct": 15, "package_temp_c": 70, "dram_usage_gb": 32, "pcie_error_count": 2}
```

> "Ahora el servidor del que hablamos al principio: CPU al 15 %, 70 grados, dos errores. Ningún umbral se cruza. Y el modelo responde ANOMALÍA DETECTADA, en unos diez milisegundos."

**Paso 3: la flota completa.** En la terminal:

```bash
python -m src.utils.fleet_simulator -n 100 --subtle-rate 0.15 --delay 0.03
```

> "Esto simula una flota de cinco servidores enviando lecturas. Cada línea es una lectura diagnosticada y guardada en el momento. Al final vemos el resumen por tipo de escenario."

**Paso 4: el tablero.** Cambiar a Power BI.

> "Y esto es lo que ve el equipo de operaciones: el porcentaje de lecturas saludables, el total de incidentes, qué servidor está peor y cómo se separan las anomalías del comportamiento normal."

### 5. Resultados (45 segundos)

*Mostrar `docs/assets/model_comparison.png`.*

> "Lo medimos contra una línea base de umbrales fijos, con miles de lecturas que el modelo nunca había visto. En degradaciones sutiles, nuestro modelo detectó el 99.7 %; los umbrales, cero. Las falsas alarmas fueron del 0.1 %. Y la respuesta tarda menos de 12 milisegundos, cuando nuestro objetivo era 100."

> "También encontramos algo que vale la pena decir: en las fallas graves, los umbrales fijos funcionan igual o mejor. Así que nuestra conclusión no es reemplazarlos, sino complementarlos."

### 6. Cierre (30 segundos)

> "El proyecto se alinea con los ODS 9 y 12: detectar a tiempo alarga la vida del hardware y evita desperdicio de energía y de equipos. Todo está hecho con software libre, corre en una laptop o en un contenedor de Docker, y tiene pruebas automatizadas. El siguiente paso es probarlo con telemetría de servidores reales. Gracias."

---

## Versión de 1 minuto (para el stand)

> "Los servidores avisan antes de fallar, pero el monitoreo tradicional solo revisa si un número rebasa un límite. Nosotros construimos un sistema que analiza varias métricas al mismo tiempo con aprendizaje automático. Por ejemplo, este servidor *(ejecutar la lectura sutil en `/docs`)* tiene el procesador casi sin carga pero está caliente y con errores: ningún límite se rebasa, y aun así el sistema lo marca como anomalía en diez milisegundos. En nuestras pruebas detectó el 99.7 % de estas degradaciones tempranas, contra cero de las reglas tradicionales. Todo se guarda y se ve en este tablero."

---

## Reparto sugerido para cuatro personas

| Parte | Duración | Quién |
| :--- | :--- | :--- |
| Gancho y problema | 1:15 | Integrante 1 |
| Solución y modelo | 1:00 | Integrante 2 |
| Demostración en vivo | 1:30 | Integrante 3 (quien mejor conozca el código) |
| Resultados y cierre | 1:15 | Integrante 4 |

---

## Preguntas probables y cómo responderlas

**¿Los datos son reales?**
No. Toda la telemetría es simulada con distribuciones estadísticas. Se eligió así porque provocar fallas reales de hardware es costoso y riesgoso, y porque al simular se sabe con certeza qué lecturas son anómalas, lo que permite medir. Validarlo con servidores reales es el siguiente paso.

**¿Por qué Isolation Forest y no una red neuronal?**
Porque no necesita ejemplos etiquetados de fallas, es rápido (tiempo lineal), requiere pocos datos y es fácil de explicar. Una red neuronal necesitaría muchos más datos y sería más difícil de justificar para este volumen.

**¿Qué pasa si el modelo se equivoca?**
Hay dos tipos de error. Falsas alarmas: 0.1 % en operación normal. Fallas no detectadas: en degradación PCIe crítica detecta 92.8 %, y en deriva térmica sin errores PCIe solo 48.9 %. Por eso se recomienda usarlo junto con umbrales fijos.

**¿Por qué dicen que es "tiempo real" si Power BI usa archivos?**
El diagnóstico sí es inmediato: cada lectura se evalúa y se guarda en unos 10 ms. El tablero se actualiza por lotes a partir de archivos exportados. Conectarlo directamente a la base de datos es trabajo futuro.

**¿Cómo sabe el modelo qué es "normal"?**
Lo aprende de 5,000 lecturas de entrenamiento sin etiquetas. Se le indica que alrededor del 5 % podrían ser anómalas (parámetro de contaminación) y con eso fija su umbral de decisión.

**¿Funcionaría con cualquier servidor?**
Tal cual, no. El modelo aprendió el comportamiento de la flota simulada. Para otro hardware hay que reentrenarlo con lecturas de esos equipos, lo cual toma segundos.

**¿Qué son los errores PCIe?**
PCIe es el bus que conecta la tarjeta madre con tarjetas de red, discos NVMe y tarjetas gráficas. Cuando un enlace empieza a degradarse reporta errores, y un conteo creciente suele anteceder a la falla del componente.

**¿Cuánto costó?**
En efectivo, casi nada: todo el software es libre o gratuito. El presupuesto del protocolo estima el valor del trabajo del equipo y la depreciación del equipo de cómputo.

**¿Qué fue lo más difícil?**
*(Respuesta personal de cada integrante; conviene prepararla.)*
