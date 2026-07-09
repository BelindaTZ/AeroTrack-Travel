"""RF-SEG-001/002 — autenticación (login/logout)."""

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.shared.pocketbase_client import PocketBaseError


class CredencialesInvalidas(Exception):
    pass


class CuentaInactiva(Exception):
    pass


class AuthService:
    def __init__(self, repo: SeguridadRepository | None = None) -> None:
        self._repo = repo or SeguridadRepository()

    async def autenticar(self, email: str, password: str) -> dict:
        """Valida contraseña primero (vía PocketBase) y activo después: así
        un intento con contraseña incorrecta nunca revela si la cuenta
        existe pero está desactivada (RF-SEG-001 solo exige distinguir los
        dos mensajes, no evitar esta capa extra de cautela)."""
        try:
            resultado = await self._repo.auth_usuario(email, password)
        except PocketBaseError:
            raise CredencialesInvalidas()

        if not resultado["record"].get("activo", False):
            raise CuentaInactiva()

        return resultado
