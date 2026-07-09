"""RF-SEG-014 / CU-O41 — auditoría inmutable, transversal.

Único método público: `insertar()`. Ningún método update/delete existe en
esta interfaz — es la garantía real de RN-SEG-010/REG-B4 (PocketBase no
puede bloquear al backend, que siempre habla con token de admin; ver nota
en `scripts/pb_schema_seguridad.py`).
"""

import logging

from app.seguridad.repositories.seguridad_repo import SeguridadRepository

logger = logging.getLogger("auditoria")


class AuditService:
    def __init__(self, repo: SeguridadRepository | None = None) -> None:
        self._repo = repo or SeguridadRepository()

    async def insertar(
        self,
        accion: str,
        tabla: str,
        usuario_id: str | None = None,
        registro_id: str | None = None,
        detalle: dict | None = None,
        ip: str | None = None,
    ) -> None:
        data: dict = {"accion": accion, "tabla": tabla, "detalle": detalle or {}}
        if usuario_id:
            data["usuario_id"] = usuario_id
        if registro_id:
            data["registro_id"] = registro_id
        if ip:
            data["ip"] = ip

        try:
            await self._repo.insertar_auditoria(data)
        except Exception:
            # RF-SEG-014: un fallo de auditoría no revierte la acción original
            # ya realizada, pero es en sí mismo un evento crítico -> se alerta
            # (por ahora vía log crítico; un canal a Administrador queda para
            # cuando exista el nivel Táctico de notificaciones internas).
            logger.critical("Fallo al insertar registro de auditoría: %s", data, exc_info=True)
