"""RF-SEG-013 / CU-O43 — verificación RBAC de dos niveles, transversal.

`requiere_permiso(modulo, accion, tabla=None)` es una fábrica de dependencia
FastAPI (`Depends(requiere_permiso("seguridad", "editar"))`), inyectable
desde los otros 5 módulos. Nivel 1 se evalúa siempre primero; Nivel 2 nunca
puede otorgar acceso que Nivel 1 no otorgó (RN-SEG-009) porque si Nivel 1
falla, Nivel 2 ni siquiera se consulta.
"""

from fastapi import Depends

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.session_service import verificar_sesion


class AccesoDenegado(Exception):
    def __init__(self, modulo: str, tabla: str | None = None):
        self.modulo = modulo
        self.tabla = tabla
        super().__init__(f"Acceso denegado: módulo={modulo!r} tabla={tabla!r}")


def requiere_permiso(modulo_clave: str, accion: str, tabla: str | None = None):
    async def _verificar(usuario: dict = Depends(verificar_sesion)) -> dict:
        repo = SeguridadRepository()
        client = repo._client

        rol_id = usuario.get("rol_id")
        if not rol_id:
            raise AccesoDenegado(modulo_clave, tabla)

        modulo = await client.get_first("modulos", f'clave="{modulo_clave}"')
        if modulo is None:
            raise AccesoDenegado(modulo_clave, tabla)

        # Nivel 1 — ¿el rol tiene el permiso (módulo, acción)?
        permiso = await client.get_first(
            "permisos", f'modulo_id="{modulo["id"]}" && accion="{accion}"'
        )
        if permiso is None:
            raise AccesoDenegado(modulo_clave, tabla)

        nivel1 = await client.get_first(
            "roles_permisos", f'rol_id="{rol_id}" && permiso_id="{permiso["id"]}"'
        )
        if nivel1 is None:
            raise AccesoDenegado(modulo_clave, tabla)

        # Nivel 2 (opcional) — si el rol tiene alguna restricción de tabla
        # para este módulo, la tabla solicitada debe estar entre ellas.
        # Sin restricciones definidas, Nivel 1 ya autorizó el módulo entero.
        if tabla:
            restricciones = await client.list_records(
                "roles_permisos_tablas",
                {"filter": f'rol_id="{rol_id}" && modulo_id="{modulo["id"]}"', "perPage": 200},
            )
            items = restricciones.get("items", [])
            if items and not any(r["tabla"] == tabla for r in items):
                raise AccesoDenegado(modulo_clave, tabla)

        return usuario

    return _verificar
