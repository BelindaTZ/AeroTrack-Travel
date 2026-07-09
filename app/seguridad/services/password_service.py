"""RF-SEG-004,005,007 — política de fortaleza y tokens de recuperación."""

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from app.seguridad.repositories.seguridad_repo import SeguridadRepository

# RNF-SEG-004: default documentado en código si `configuracion_sistema` no
# tiene la clave (ya sembrada como "password_reset.expiracion_minutos").
DEFAULT_EXPIRACION_MINUTOS = 30
MIN_LENGTH = 8


class PasswordDebil(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


class TokenInvalido(Exception):
    pass


class PasswordService:
    def __init__(self, repo: SeguridadRepository | None = None) -> None:
        self._repo = repo or SeguridadRepository()

    # ── RN-SEG-005 — política mínima de fortaleza ───────────────────────
    def validar_fortaleza(self, password: str) -> None:
        if len(password) < MIN_LENGTH:
            raise PasswordDebil(f"La contraseña debe tener al menos {MIN_LENGTH} caracteres")
        if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
            raise PasswordDebil("La contraseña debe combinar letras y números")

    # ── RNF-SEG-004 — expiración configurable ───────────────────────────
    async def minutos_expiracion_recuperacion(self) -> int:
        config = await self._repo.get_config("password_reset.expiracion_minutos")
        if config is None:
            return DEFAULT_EXPIRACION_MINUTOS
        try:
            return int(config["valor"])
        except (TypeError, ValueError):
            return DEFAULT_EXPIRACION_MINUTOS

    # ── RF-SEG-004 — generar enlace de un solo uso ──────────────────────
    async def generar_token_recuperacion(self, usuario_id: str) -> str:
        token = secrets.token_urlsafe(32)
        minutos = await self.minutos_expiracion_recuperacion()
        expira = datetime.now(timezone.utc) + timedelta(minutes=minutos)
        await self._repo.update_usuario(
            usuario_id,
            {
                "reset_token_hash": self._hash(token),
                "reset_token_expira": expira.isoformat(),
            },
        )
        return token

    # ── RF-SEG-005 — validar y consumir el enlace ───────────────────────
    async def validar_token(self, token: str) -> dict:
        usuario = await self._repo.get_usuario_by_token_hash(self._hash(token))
        if usuario is None or not usuario.get("reset_token_expira"):
            raise TokenInvalido()

        expira = datetime.fromisoformat(usuario["reset_token_expira"].replace("Z", "+00:00"))
        if expira < datetime.now(timezone.utc):
            raise TokenInvalido()

        return usuario

    async def consumir_token(self, usuario_id: str, nueva_password: str) -> None:
        await self._repo.update_usuario(
            usuario_id,
            {
                "password": nueva_password,
                "passwordConfirm": nueva_password,
                "reset_token_hash": "",
                "reset_token_expira": None,
            },
        )

    @staticmethod
    def _hash(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()
