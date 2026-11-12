FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SHD_DATABASE_URL=sqlite:////app/data/telemetry.db \
    SHD_MODEL_PATH=/app/data/model/intel_health_model.pkl \
    SHD_DATALAKE_DIR=/app/data/datalake \
    SHD_PROCESSED_DIR=/app/data/processed

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src

# Usuario sin privilegios; /app/data guarda la base, el modelo y las exportaciones.
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser /app
USER appuser
VOLUME ["/app/data"]

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
