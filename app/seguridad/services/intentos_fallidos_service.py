"""RF-SEG-T01 (CU-T?? Táctico) — dashboard de intentos de login fallidos.

No es un dato nuevo: `login_fallido` ya se registra en `auditoria` desde
RF-SEG-001 (`router_auth.py`). Lo que faltaba era agregarlo de forma útil
para un Administrador (por cuenta/IP, con umbral de sospecha) en vez de
obligarlo a leer el log crudo fila por fila en /admin/auditoria.

"Expiración forzada de sesión" (la otra mitad de este ítem táctico) NO
necesita código nuevo: `verificar_sesion()` ya revalida `usuarios.activo`
en cada request (`session_service.py`), así que desactivar una cuenta desde
/admin/usuarios ya fuerza el cierre de su sesión en el siguiente request —
mecanismo existente, no un gap.
"""

import datetime

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService

UMBRAL_SOSPECHOSO_DEFAULT = 5
VENTANA_HORAS_DEFAULT = 24


class CuentaNoEncontrada(Exception):
    pass


async def resumen_intentos_fallidos(
    horas: int = VENTANA_HORAS_DEFAULT,
    umbral_sospechoso: int = UMBRAL_SOSPECHOSO_DEFAULT,
    ahora: datetime.datetime | None = None,
) -> list[dict]:
    repo = SeguridadRepository()
    ahora = ahora or datetime.datetime.now(datetime.timezone.utc)
    desde = (ahora - datetime.timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S.000Z")
    resultado = await repo.list_auditoria(
        filtro=f'accion="login_fallido" && created >= "{desde}"', per_page=500
    )

    agrupado: dict[str, dict] = {}
    for registro in resultado["items"]:
        detalle = registro.get("detalle") or {}
        # Los fallos de Google OAuth no traen email (fallan antes de saber
        # cuál cuenta) — se agrupan por IP en ese caso, nunca se descartan.
        clave = detalle.get("email") or f"IP {registro.get('ip') or 'desconocida'}"
        if clave not in agrupado:
            agrupado[clave] = {
                "identificador": clave,
                "intentos": 0,
                "ips": set(),
                "motivos": set(),
                "ultimo_intento": registro["created"],
            }
        fila = agrupado[clave]
        fila["intentos"] += 1
        if registro.get("ip"):
            fila["ips"].add(registro["ip"])
        if detalle.get("motivo"):
            fila["motivos"].add(detalle["motivo"])
        if registro["created"] > fila["ultimo_intento"]:
            fila["ultimo_intento"] = registro["created"]

    filas = []
    for fila in agrupado.values():
        filas.append(
            {
                "identificador": fila["identificador"],
                "intentos": fila["intentos"],
                "ips": sorted(fila["ips"]),
                "motivos": sorted(fila["motivos"]),
                "ultimo_intento": fila["ultimo_intento"],
                "sospechoso": fila["intentos"] >= umbral_sospechoso,
            }
        )
    filas.sort(key=lambda f: f["intentos"], reverse=True)
    return filas


async def desactivar_cuenta_por_email(admin: dict, email: str) -> dict:
    """"Expiración forzada de sesión": desactivar la cuenta hace que
    `verificar_sesion()` la rechace en su siguiente request, sin importar
    cuánto le quede al token JWT — mismo mecanismo que ya usa el toggle
    "activo" de /admin/usuarios, pero ese solo alcanza a agente/administrador
    (`listar_usuarios_internos` los filtra explícitamente). Esta es la
    versión que sí cubre pasajero, el caso real más común en este dashboard."""
    repo = SeguridadRepository()
    cuenta = await repo.get_usuario_by_email(email)
    if cuenta is None:
        raise CuentaNoEncontrada()

    actualizada = await repo.update_usuario(cuenta["id"], {"activo": False})
    await AuditService().insertar(
        "desactivar_cuenta",
        "usuarios",
        usuario_id=admin["id"],
        registro_id=cuenta["id"],
        detalle={"motivo": "intentos_de_login_fallidos_sospechosos", "email": email},
    )
    return actualizada
