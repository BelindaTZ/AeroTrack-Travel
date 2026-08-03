import os
from functools import lru_cache

from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Configuración leída de variables de entorno — nunca hardcodeada (REG-B3).

    Usa PB_TRAVEL_* (instancia pocketbase-travel), no PB_* (instancia del
    proyecto anterior minio-elt, aislada del stack de AeroTrack Travel).
    """

    def __init__(self) -> None:
        self.pb_url = self._require("PB_TRAVEL_URL")
        self.pb_email = self._require("PB_TRAVEL_EMAIL")
        self.pb_password = self._require("PB_TRAVEL_PASSWORD")
        self.secret_key = self._require("SECRET_KEY")
        self.algorithm = os.environ.get("ALGORITHM", "HS256")
        self.token_expire_minutes = int(os.environ.get("TOKEN_EXPIRE_MINUTES", "60"))

        # MinIO (modelo dimensional, REG-A2 solo lectura) — instancia PROPIA
        # de Travel (minio-travel), no la de minio-elt. Mismos defaults de
        # desarrollo que dags/config.py, no secretos de producción.
        in_docker = os.path.exists("/.dockerenv")
        self.minio_endpoint = (
            os.environ.get("MINIO_TRAVEL_URL_DOCKER", "minio-travel:9000")
            if in_docker
            else os.environ.get("MINIO_TRAVEL_URL", "localhost:9002")
        )
        self.minio_access = os.environ.get("MINIO_TRAVEL_ACCESS", "admin")
        self.minio_secret = os.environ.get("MINIO_TRAVEL_SECRET", "admin1234")
        self.minio_bucket_travel_dims = os.environ.get(
            "MINIO_BUCKET_TRAVEL_DIMS", "aerotrack-travel-dims"
        )

        # MinIO operacional (REG-A2 ya no aplica a este bucket — lectura y
        # escritura). Bucket separado de aerotrack-travel-dims, que se queda
        # como espejo BTS/FAA de solo lectura.
        self.minio_bucket_travel_operational = os.environ.get(
            "MINIO_BUCKET_TRAVEL_OPERATIONAL", "aerotrack-travel-operational"
        )

        # Catálogo NDJSON publicado por el ETL de staging (PocketBase) —
        # generado por dags/dag_publicar_catalogo_minio.py. Solo lectura
        # desde la app (la app nunca escribe acá, solo los DAGs).
        self.minio_bucket_travel_catalog = os.environ.get(
            "MINIO_BUCKET_TRAVEL_CATALOG", "aerotrack-travel-catalog"
        )

        # Airflow (CU-T07, solo lectura vía API REST) — mismo criterio
        # in_docker que MinIO: dentro del compose se resuelve por nombre de
        # servicio, fuera (dev local) por localhost:8081 (puerto publicado).
        self.airflow_url = (
            os.environ.get("AIRFLOW_TRAVEL_URL_DOCKER", "http://airflow-webserver-travel:8080")
            if in_docker
            else "http://localhost:8081"
        )
        self.airflow_user = os.environ.get("AIRFLOW_TRAVEL_ADMIN_USER", "admin")
        self.airflow_password = os.environ.get("AIRFLOW_TRAVEL_ADMIN_PASSWORD", "admin1234")

        # ClickHouse (BD analítica, solo lectura desde la app — la carga la
        # hacen los DAGs `aerotrack_travel_etl_*`, ver dags/config.py). Base
        # `aerotrack_travel`, no `aerotrack_travel_analitico` (default de
        # CLICKHOUSE_TRAVEL_DB, sin usar por ahora).
        self.clickhouse_host = (
            "clickhouse-travel" if in_docker else "localhost"
        )
        self.clickhouse_port = (
            9000 if in_docker else int(os.environ.get("CLICKHOUSE_TRAVEL_NATIVE_PORT", "9004"))
        )
        self.clickhouse_user = os.environ.get("CLICKHOUSE_TRAVEL_USER", "admin")
        self.clickhouse_password = os.environ.get("CLICKHOUSE_TRAVEL_PASSWORD", "admin1234")
        self.clickhouse_db = "aerotrack_travel"

    @staticmethod
    def _require(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"Variable de entorno requerida no configurada: {name}")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
