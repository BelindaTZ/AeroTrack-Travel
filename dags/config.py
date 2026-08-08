"""
AeroTrack Travel — Configuración centralizada de los DAGs de Airflow
=====================================================================
Detecta si el proceso corre dentro de Docker y selecciona
automáticamente las URLs correctas (nombres de servicio vs localhost).

Esta instancia de Airflow es NUEVA y separada de la de AeroTrack
Analytics (proyecto anterior, minio-elt): se conecta a su propia
PocketBase (pocketbase-travel) y a su propia instancia de MinIO
(minio-travel) — 100% independiente, no depende de minio-elt.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga .env desde la raíz del proyecto Travel (no-op si no existe, p.ej. en Docker)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

IN_DOCKER = os.path.exists("/.dockerenv")

# ── MinIO: instancia PROPIA de Travel (minio-travel), no la de minio-elt ──
MINIO_ENDPOINT = (
    os.getenv("MINIO_TRAVEL_URL_DOCKER", "minio-travel:9000")
    if IN_DOCKER
    else os.getenv("MINIO_TRAVEL_URL", "localhost:9002")
)
MINIO_ACCESS = os.getenv("MINIO_TRAVEL_ACCESS", "admin")
MINIO_SECRET = os.getenv("MINIO_TRAVEL_SECRET", "admin1234")
MINIO_BUCKET_TRAVEL_DIMS = os.getenv("MINIO_BUCKET_TRAVEL_DIMS", "aerotrack-travel-dims")
MINIO_BUCKET_TRAVEL_CATALOG = os.getenv("MINIO_BUCKET_TRAVEL_CATALOG", "aerotrack-travel-catalog")

# ── PocketBase Travel: instancia NUEVA y separada ───────────────────────────
PB_TRAVEL_URL = (
    os.getenv("PB_TRAVEL_URL_DOCKER", "http://pocketbase-travel:8090")
    if IN_DOCKER
    else os.getenv("PB_TRAVEL_URL", "http://localhost:8091")
)
PB_TRAVEL_EMAIL = os.getenv("PB_TRAVEL_EMAIL", "")
PB_TRAVEL_PASSWORD = os.getenv("PB_TRAVEL_PASSWORD", "")

# ── App FastAPI Travel: mismo travel-network, nombre de servicio Docker ────
APP_TRAVEL_URL = (
    "http://app-travel:8000"
    if IN_DOCKER
    else f"http://localhost:{os.getenv('APP_TRAVEL_PORT', '8001')}"
)

# ── Parámetros de negocio con valor por defecto (se sobreescriben con
#    configuracion_sistema vía get_config(), ver pocketbase_client.py) ──────
DEFAULT_UMBRAL_API_REAL_HORAS = 72
DEFAULT_HORIZONTE_CATALOGO_DIAS = 7

# ── ClickHouse Travel (BD analítica, base `aerotrack_travel` — no confundir
#    con `aerotrack_travel_analitico`, que sigue siendo la base configurada
#    en CLICKHOUSE_TRAVEL_DB para otros usos futuros) ────────────────────────
CLICKHOUSE_HOST = "clickhouse-travel" if IN_DOCKER else "localhost"
CLICKHOUSE_PORT = 9000 if IN_DOCKER else int(os.getenv("CLICKHOUSE_TRAVEL_NATIVE_PORT", "9004"))
CLICKHOUSE_USER = os.getenv("CLICKHOUSE_TRAVEL_USER", "admin")
CLICKHOUSE_PASSWORD = os.getenv("CLICKHOUSE_TRAVEL_PASSWORD", "admin1234")
CLICKHOUSE_DB = "aerotrack_travel"

# ── Staging de Parquet E/L/T del pipeline ELT (versionado por timestamp,
#    los archivos nunca se sobrescriben) ─────────────────────────────────
#    E = Extracción — extraído de MinIO/app vía endpoints internos
#    T = Transformado — agregado ya calculado, previo a insertar en ClickHouse
#    L = Cargado — agregado ya insertado en ClickHouse
#    (reemplaza crudo/procesando/terminado — ver
#    docs/estrategico-auditoria.md sección Fase A para el mapeo acordado)
PARQUET_BASE_DIR = Path("/opt/airflow/datos") if IN_DOCKER else Path(__file__).parent.parent / "datos"
PARQUET_E = PARQUET_BASE_DIR / "E"
PARQUET_T = PARQUET_BASE_DIR / "T"
PARQUET_L = PARQUET_BASE_DIR / "L"

# ── Integración puente con AeroTrack Analytics (minio-elt) ─────────────────
# SOLO la usa el DAG aerotrack_travel_sync_dims para disparar el ELT/cobertura
# global de Analytics y sincronizar el resultado a minio-travel. No es una
# dependencia permanente de Travel — el resto del proyecto funciona sin
# Analytics corriendo; únicamente este DAG específico lo necesita, y solo
# mientras se ejecuta. host.docker.internal (no elt-network) para no volver
# a acoplar los contenedores de Travel a la red de Analytics.
ANALYTICS_AIRFLOW_URL = (
    os.getenv("ANALYTICS_AIRFLOW_URL_DOCKER", "http://host.docker.internal:8080")
    if IN_DOCKER
    else os.getenv("ANALYTICS_AIRFLOW_URL", "http://localhost:8080")
)
ANALYTICS_AIRFLOW_USER = os.getenv("ANALYTICS_AIRFLOW_USER", "admin")
ANALYTICS_AIRFLOW_PASSWORD = os.getenv("ANALYTICS_AIRFLOW_PASSWORD", "admin1234")

ANALYTICS_MINIO_ENDPOINT = (
    os.getenv("ANALYTICS_MINIO_URL_DOCKER", "host.docker.internal:9000")
    if IN_DOCKER
    else os.getenv("ANALYTICS_MINIO_URL", "localhost:9000")
)
ANALYTICS_MINIO_ACCESS = os.getenv("ANALYTICS_MINIO_ACCESS", "admin")
ANALYTICS_MINIO_SECRET = os.getenv("ANALYTICS_MINIO_SECRET", "admin1234")
ANALYTICS_MINIO_BUCKET_DIMS = os.getenv("ANALYTICS_MINIO_BUCKET_DIMS", "aerotrack-dims")
