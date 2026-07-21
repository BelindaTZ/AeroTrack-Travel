"""Servicios de Centro de Ayuda — RF-AYU-001..004, RF-AYU-T01..T03."""

from datetime import datetime, timezone

from app.centro_ayuda.integrations.escalacion_sender import EscalacionSender
from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.seguridad.services.audit_service import AuditService


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def calificar_articulo(articulo_id: str, pasajero_id: str | None, util: str) -> dict:
    """RN anónima permitida (RF-AYU-003) — `pasajero_id` puede ser `None`."""
    repo = CentroAyudaRepository()
    calificacion = await repo.crear_calificacion(articulo_id, pasajero_id, util, _ahora_iso())
    await AuditService().insertar(
        "calificar_articulo", "articulo_calificaciones",
        usuario_id=None, registro_id=calificacion["id"], detalle={"util": util},
    )
    return calificacion


class ArticuloNoEncontrado(Exception):
    pass


async def escalar_caso(
    usuario: dict, pasajero_id: str, asunto: str, mensaje: str, sender: EscalacionSender
) -> dict:
    """RF-AYU-004 — crea el caso SIEMPRE (para que quede registrado y
    disponible en la bandeja de CU-T36) aunque el envío real del email
    falle; en ese caso `gmail_thread_id` queda vacío en vez de fabricar
    un hilo que no existe — el Agente lo verá igual en la bandeja, sin
    hilo de correo vinculado hasta que se reintente."""
    repo = CentroAyudaRepository()
    caso = await repo.crear_caso(
        {
            "pasajero_id": pasajero_id, "asunto": asunto, "mensaje": mensaje,
            "estado": "abierto", "fecha_creacion": _ahora_iso(),
        }
    )

    thread_id = await sender.enviar(usuario["email"], asunto, mensaje)
    if thread_id:
        caso = await repo.actualizar_caso(caso["id"], {"gmail_thread_id": thread_id})

    await AuditService().insertar(
        "escalar_caso", "casos_escalados", usuario_id=usuario["id"], registro_id=caso["id"],
        detalle={"asunto": asunto, "email_enviado": bool(thread_id)},
    )
    return caso


async def resolver_caso(caso_id: str, agente_id: str) -> dict:
    repo = CentroAyudaRepository()
    caso = await repo.actualizar_caso(
        caso_id, {"estado": "resuelto", "fecha_resolucion": _ahora_iso(), "agente_asignado_id": agente_id}
    )
    await AuditService().insertar(
        "resolver_caso", "casos_escalados", usuario_id=agente_id, registro_id=caso_id
    )
    return caso


async def crear_articulo(usuario: dict, categoria: str, titulo: str, contenido: str) -> dict:
    repo = CentroAyudaRepository()
    articulo = await repo.crear_articulo(
        {
            "categoria": categoria, "titulo": titulo, "contenido": contenido,
            "autor_id": usuario["id"], "activo": True, "fecha_publicacion": _ahora_iso(),
        }
    )
    await AuditService().insertar(
        "crear_articulo", "articulos_ayuda", usuario_id=usuario["id"], registro_id=articulo["id"]
    )
    return articulo


async def actualizar_articulo(
    usuario: dict, articulo_id: str, categoria: str, titulo: str, contenido: str, activo: bool
) -> dict:
    repo = CentroAyudaRepository()
    articulo = await repo.actualizar_articulo(
        articulo_id, {"categoria": categoria, "titulo": titulo, "contenido": contenido, "activo": activo}
    )
    await AuditService().insertar(
        "editar_articulo", "articulos_ayuda", usuario_id=usuario["id"], registro_id=articulo_id
    )
    return articulo


async def metricas_satisfaccion(desde_iso: str) -> dict:
    """RF-AYU-T02 — **"más consultados" no es literal**: `articulos_ayuda`
    no tiene un contador de vistas en el esquema real (confirmado contra
    el dbml v3) — se usa la cantidad de calificaciones por artículo como
    proxy real de interacción (un artículo calificado fue, como mínimo,
    leído), nunca un número inventado. Ver `errores-conocidos.md`."""
    repo = CentroAyudaRepository()
    articulos = await repo.listar_articulos_admin()
    calificaciones = await repo.todas_las_calificaciones()

    por_articulo: dict[str, dict] = {}
    for c in calificaciones:
        aid = c["articulo_id"]
        entrada = por_articulo.setdefault(aid, {"arriba": 0, "abajo": 0})
        entrada["arriba" if c["util"] == "arriba" else "abajo"] += 1

    articulos_out = []
    for a in articulos:
        stats = por_articulo.get(a["id"], {"arriba": 0, "abajo": 0})
        total = stats["arriba"] + stats["abajo"]
        articulos_out.append(
            {
                "id": a["id"], "titulo": a["titulo"], "categoria": a["categoria"], "activo": a.get("activo", True),
                "calificaciones_total": total, "calificaciones_positivas": stats["arriba"],
                "porcentaje_util": round(100 * stats["arriba"] / total, 1) if total else None,
            }
        )
    articulos_out.sort(key=lambda a: a["calificaciones_total"], reverse=True)

    casos = await repo.casos_en_periodo(desde_iso)
    casos_por_estado: dict[str, int] = {}
    for c in casos:
        casos_por_estado[c["estado"]] = casos_por_estado.get(c["estado"], 0) + 1

    return {"articulos": articulos_out, "casos_escalados_total": len(casos), "casos_por_estado": casos_por_estado}
