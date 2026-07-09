"""
AeroTrack Travel — Configuración centralizada de los DAGs de Airflow
=====================================================================
Detecta si el proceso corre dentro de Docker y selecciona
automáticamente las URLs correctas (nombres de servicio vs localhost).

Esta instancia de Airflow es NUEVA y separada de la de AeroTrack
Analytics (proyecto anterior, minio-elt): se conecta a su propia
PocketBase (pocketbase-travel) y al bucket MinIO aerotrack-travel-dims
(copia de solo lectura del modelo dimensional heredado).
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carga .env desde la raíz del proyecto Travel (no-op si no existe, p.ej. en Docker)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

IN_DOCKER = os.path.exists("/.dockerenv")

# ── MinIO: MISMA instancia del proyecto anterior, bucket propio de Travel ──
MINIO_ENDPOINT = os.getenv("MINIO_URL_DOCKER", "minio:9000") if IN_DOCKER else os.getenv("MINIO_URL", "localhost:9000")
MINIO_ACCESS = os.getenv("MINIO_ACCESS", "admin")
MINIO_SECRET = os.getenv("MINIO_SECRET", "admin1234")
MINIO_BUCKET_TRAVEL_DIMS = os.getenv("MINIO_BUCKET_TRAVEL_DIMS", "aerotrack-travel-dims")

# ── PocketBase Travel: instancia NUEVA y separada ───────────────────────────
PB_TRAVEL_URL = (
    os.getenv("PB_TRAVEL_URL_DOCKER", "http://pocketbase-travel:8090")
    if IN_DOCKER
    else os.getenv("PB_TRAVEL_URL", "http://localhost:8091")
)
PB_TRAVEL_EMAIL = os.getenv("PB_TRAVEL_EMAIL", "")
PB_TRAVEL_PASSWORD = os.getenv("PB_TRAVEL_PASSWORD", "")

# ── Parámetros de negocio con valor por defecto (se sobreescriben con
#    configuracion_sistema vía get_config(), ver pocketbase_client.py) ──────
DEFAULT_UMBRAL_API_REAL_HORAS = 72
DEFAULT_HORIZONTE_CATALOGO_DIAS = 7
