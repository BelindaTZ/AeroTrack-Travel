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

    @staticmethod
    def _require(name: str) -> str:
        value = os.environ.get(name)
        if not value:
            raise RuntimeError(f"Variable de entorno requerida no configurada: {name}")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
