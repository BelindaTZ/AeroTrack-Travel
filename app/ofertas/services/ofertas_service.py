"""Servicios de Ofertas y Promociones — RF-OFE-001..005, RF-OFE-T01..T04."""

from datetime import datetime, timezone

from app.ofertas.integrations.campana_sender import CampanaSender
from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.audit_service import AuditService
from app.shared.descripcion_producto import describir_item
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


class CuponInvalido(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def ofertas_destacadas_con_descripcion(tipo_producto: str | None = None) -> list[dict]:
    repo = OfertasRepository()
    ofertas = await repo.ofertas_vigentes(_ahora_iso(), tipo_producto)
    salida = []
    for o in ofertas:
        etiqueta = await describir_item({"tipo_producto": o["tipo_producto"], f"{o['tipo_producto']}_id": o["producto_ref"]})
        salida.append({**o, "titulo_producto": etiqueta["titulo"], "href_producto": etiqueta["href"]})
    return salida


class OfertaInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def crear_oferta_destacada(usuario: dict, data: dict) -> dict:
    """WP-17 (auditoría de WorkPanels, 2026-08-01) — antes `ofertas_destacadas`
    no tenía ningún panel de gestión, solo se leía para el home público."""
    repo = OfertasRepository()
    oferta = await repo.crear_oferta(data)
    await AuditService().insertar(
        "crear_oferta_destacada", "ofertas_destacadas", usuario_id=usuario["id"], registro_id=oferta["id"]
    )
    return oferta


async def actualizar_oferta_destacada(usuario: dict, oferta_id: str, data: dict) -> dict:
    repo = OfertasRepository()
    oferta = await repo.obtener_oferta(oferta_id)
    if oferta is None:
        raise OfertaInvalida("Oferta no encontrada")
    actualizada = await repo.actualizar_oferta(oferta_id, data)
    await AuditService().insertar(
        "actualizar_oferta_destacada", "ofertas_destacadas", usuario_id=usuario["id"], registro_id=oferta_id
    )
    return actualizada


async def alternar_activa_oferta(usuario: dict, oferta_id: str) -> dict:
    repo = OfertasRepository()
    oferta = await repo.obtener_oferta(oferta_id)
    if oferta is None:
        raise OfertaInvalida("Oferta no encontrada")
    nueva_activa = not oferta.get("activa", True)
    actualizada = await repo.actualizar_oferta(oferta_id, {"activa": nueva_activa})
    await AuditService().insertar(
        "reactivar_oferta_destacada" if nueva_activa else "desactivar_oferta_destacada",
        "ofertas_destacadas", usuario_id=usuario["id"], registro_id=oferta_id,
        detalle={"activa": nueva_activa},
    )
    return actualizada


async def destinos_populares(pasajero_id: str | None, origen_declarado: str | None, limite: int = 6) -> tuple[str | None, list[dict]]:
    """RF-OFE-002/RN-OFE-001 — estadística real de uso (búsquedas +
    reservas de vuelo), nunca curación editorial. El origen se infiere de
    `busquedas_recientes` del pasajero si está autenticado; si no, se usa
    el origen que declaró en la búsqueda actual. Sin ninguno de los dos,
    no hay "origen habitual" que agregar — se retorna vacío en vez de
    mostrar un ranking global sin relación con el pasajero. Retorna
    `(origen_usado, destinos)` — el llamador necesita saber cuál origen
    se usó de verdad (declarado o inferido), no solo la lista resultante,
    para poder mostrarlo en pantalla."""
    repo = OfertasRepository()
    origen = origen_declarado

    if pasajero_id and not origen:
        busquedas = await repo.busquedas_vuelo_de_pasajero(pasajero_id)
        origenes = [b["criterios"].get("origen") for b in busquedas if b["criterios"].get("origen")]
        if origenes:
            origen = max(set(origenes), key=origenes.count)

    if not origen:
        return None, []

    conteo: dict[str, int] = {}
    for b in await repo.todas_las_busquedas_de_vuelo():
        if b["criterios"].get("origen") == origen and b["criterios"].get("destino"):
            destino = b["criterios"]["destino"]
            conteo[destino] = conteo.get(destino, 0) + 1

    vuelos_repo = VuelosRepository()
    vuelos_cache: dict[str, dict | None] = {}
    for item in await repo.reserva_items_de_vuelo():
        vuelo_id = item.get("vuelo_id")
        if not vuelo_id:
            continue
        if vuelo_id not in vuelos_cache:
            vuelos_cache[vuelo_id] = await vuelos_repo.obtener_vuelo(vuelo_id)
        vuelo = vuelos_cache[vuelo_id]
        if vuelo and vuelo["origen_codigo"] == origen:
            conteo[vuelo["destino_codigo"]] = conteo.get(vuelo["destino_codigo"], 0) + 2  # una reserva real pesa más que una búsqueda

    top = sorted(conteo.items(), key=lambda kv: kv[1], reverse=True)[:limite]
    return origen, [
        {"codigo": codigo, "legible": await resolver_aeropuerto(codigo), "volumen": volumen}
        for codigo, volumen in top
    ]


async def suscribirse_newsletter(email: str, pasajero_id: str | None) -> dict:
    repo = OfertasRepository()
    existente = await repo.suscripcion_existente(email)
    if existente:
        if not existente.get("activo", True):
            await repo.reactivar_suscripcion(existente["id"])
        return existente

    data = {"email": email, "fecha_suscripcion": _ahora_iso(), "activo": True}
    if pasajero_id:
        data["pasajero_id"] = pasajero_id
    suscripcion = await repo.crear_suscripcion(data)
    await AuditService().insertar(
        "suscribir_newsletter", "newsletter_suscripciones", registro_id=suscripcion["id"], detalle={"email": email}
    )
    return suscripcion


async def aplicar_cupon(usuario: dict, pasajero_id: str, reserva_id: str, codigo: str) -> dict:
    repo = OfertasRepository()
    reservas_repo = ReservasRepository()

    reserva = await reservas_repo.obtener_reserva(reserva_id)
    if reserva is None or reserva["pasajero_titular_id"] != pasajero_id:
        raise CuponInvalido("Reserva no encontrada")
    if reserva["estado"] != "pendiente_pago":
        raise CuponInvalido("Solo se puede aplicar un cupón antes de pagar")

    cupon = await repo.obtener_cupon_por_codigo(codigo)
    if cupon is None or not cupon.get("activo", True):
        raise CuponInvalido("Cupón inválido o inactivo")

    ahora_iso = _ahora_iso()
    if cupon["fecha_expiracion"] < ahora_iso:
        raise CuponInvalido("Cupón expirado")

    if cupon.get("usos_maximos") and (cupon.get("usos_actuales") or 0) >= cupon["usos_maximos"]:
        raise CuponInvalido("Cupón sin usos disponibles")

    if await repo.uso_existente(cupon["id"], reserva_id):
        raise CuponInvalido("Este cupón ya se aplicó a esta reserva")

    if cupon.get("producto_aplicable"):
        items = await reservas_repo.items_de_reserva(reserva_id)
        tipos = {i["tipo_producto"] for i in items}
        if not tipos and reserva.get("vuelo_id"):
            tipos = {"vuelo"}
        if tipos and tipos != {cupon["producto_aplicable"]}:
            raise CuponInvalido(f"Este cupón solo aplica a reservas de {cupon['producto_aplicable']}")

    if reserva.get("es_paquete"):
        acumulable = cupon.get("acumulable_con_paquete")
        if acumulable is None:
            default = await repo.config("cupones.acumulable_con_paquete_default")
            acumulable = bool(default and default["valor"] == "true")
        if not acumulable:
            raise CuponInvalido("Este cupón no es acumulable con el descuento de un paquete")

    if cupon["tipo"] == "porcentaje":
        monto = round(reserva["total_pagar"] * cupon["valor"] / 100, 2)
    else:
        monto = min(cupon["valor"], reserva["total_pagar"])
    nuevo_total = round(reserva["total_pagar"] - monto, 2)

    await reservas_repo.actualizar_reserva(reserva_id, {"total_pagar": nuevo_total})
    await repo.actualizar_cupon(cupon["id"], {"usos_actuales": (cupon.get("usos_actuales") or 0) + 1})
    uso = await repo.registrar_uso(cupon["id"], reserva_id, monto, ahora_iso)
    await AuditService().insertar(
        "aplicar_cupon", "cupones_uso", usuario_id=usuario["id"], registro_id=uso["id"],
        detalle={"codigo": codigo, "monto_descontado": monto, "reserva_id": reserva_id},
    )
    return {"monto_descontado": monto, "nuevo_total": nuevo_total}


# ── backoffice (CU-T30, T31, T32, T44) ──────────────────────────────
async def crear_cupon(usuario: dict, data: dict) -> dict:
    repo = OfertasRepository()
    data.setdefault("usos_actuales", 0)
    data.setdefault("activo", True)
    cupon = await repo.crear_cupon(data)
    await AuditService().insertar("crear_cupon", "cupones_descuento", usuario_id=usuario["id"], registro_id=cupon["id"])
    return cupon


class CuponInmutable(Exception):
    pass


async def actualizar_cupon(usuario: dict, cupon_id: str, data: dict) -> dict:
    """RN-OFE-T01 — el código no puede cambiar si el cupón ya tiene usos."""
    repo = OfertasRepository()
    cupon = await repo.obtener_cupon(cupon_id)
    if cupon is None:
        raise CuponInvalido("Cupón no encontrado")
    if "codigo" in data and data["codigo"] != cupon["codigo"] and (cupon.get("usos_actuales") or 0) > 0:
        raise CuponInmutable("El código de un cupón con usos registrados no puede cambiar")

    actualizado = await repo.actualizar_cupon(cupon_id, data)
    await AuditService().insertar("editar_cupon", "cupones_descuento", usuario_id=usuario["id"], registro_id=cupon_id)
    return actualizado


async def alternar_activo_cupon(usuario: dict, cupon_id: str) -> dict:
    """WP-06 (auditoría de WorkPanels, 2026-07-31) — Desactivar/Reactivar
    como acción propia (antes era un checkbox dentro del form de Editar,
    sin confirmación ni acción independiente)."""
    repo = OfertasRepository()
    cupon = await repo.obtener_cupon(cupon_id)
    if cupon is None:
        raise CuponInvalido("Cupón no encontrado")

    nuevo_activo = not cupon.get("activo", True)
    actualizado = await repo.actualizar_cupon(cupon_id, {"activo": nuevo_activo})
    await AuditService().insertar(
        "reactivar_cupon" if nuevo_activo else "desactivar_cupon",
        "cupones_descuento", usuario_id=usuario["id"], registro_id=cupon_id,
        detalle={"activo": nuevo_activo},
    )
    return actualizado


class SuscripcionInvalida(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def alternar_activo_suscripcion(usuario: dict, suscripcion_id: str) -> dict:
    """WP-07 (auditoría de WorkPanels, 2026-07-31) — panel de gestión de
    suscriptores al newsletter, antes inexistente en el backoffice."""
    repo = OfertasRepository()
    suscripcion = await repo.obtener_suscripcion(suscripcion_id)
    if suscripcion is None:
        raise SuscripcionInvalida("Suscripción no encontrada")

    if suscripcion.get("activo"):
        actualizado = await repo.desactivar_suscripcion(suscripcion_id)
        accion = "desactivar_suscripcion"
    else:
        actualizado = await repo.reactivar_suscripcion(suscripcion_id)
        accion = "reactivar_suscripcion"
    await AuditService().insertar(
        accion, "newsletter_suscripciones", usuario_id=usuario["id"], registro_id=suscripcion_id,
        detalle={"activo": actualizado.get("activo")},
    )
    return actualizado


async def reporte_cupones(desde_iso: str) -> list[dict]:
    repo = OfertasRepository()
    usos = await repo.usos_en_periodo(desde_iso)
    cupones = await repo.listar_cupones()
    por_cupon: dict[str, dict] = {c["id"]: {"usos": 0, "monto_total": 0.0} for c in cupones}
    for u in usos:
        if u["cupon_id"] in por_cupon:
            por_cupon[u["cupon_id"]]["usos"] += 1
            por_cupon[u["cupon_id"]]["monto_total"] += u["monto_descontado"]

    salida = [
        {
            "id": c["id"], "codigo": c["codigo"], "tipo": c["tipo"], "valor": c["valor"], "activo": c.get("activo", True),
            "usos": por_cupon[c["id"]]["usos"], "monto_total": round(por_cupon[c["id"]]["monto_total"], 2),
        }
        for c in cupones
    ]
    salida.sort(key=lambda c: c["usos"], reverse=True)
    return salida


async def crear_campana(usuario: dict, nombre: str, segmento_criterio: dict, plantilla: str) -> dict:
    """`campanas_email.segmento_criterio` es un `json` REQUERIDO en el
    esquema — PocketBase trata un `{}` vacío como "valor faltante" (400),
    mismo gotcha ya documentado para `number`/`bool` required en 0/false
    (ver `feedback_pocketbase_required_numerico`). Sin criterio explícito,
    se guarda un default real y legible ("todos los suscriptores") en vez
    de un `{}` que PocketBase rechazaría."""
    repo = OfertasRepository()
    criterio = segmento_criterio or {"segmento": "todos_los_suscriptores"}
    campana = await repo.crear_campana(
        {"nombre": nombre, "segmento_criterio": criterio, "plantilla": plantilla, "estado": "borrador", "creado_por": usuario["id"]}
    )
    await AuditService().insertar("crear_campana", "campanas_email", usuario_id=usuario["id"], registro_id=campana["id"])
    return campana


class CampanaBloqueada(Exception):
    pass


async def enviar_campana(usuario: dict, campana_id: str, sender: CampanaSender) -> dict:
    """RF-OFE-T02/RN-OFE-T02 — envío real; una campaña ya enviada nunca
    se reenvía. Si no hay credencial real de SendGrid, se rechaza
    explícitamente (`CredencialNoConfigurada`) en vez de marcarla
    `enviada` sin haber salido nada."""
    repo = OfertasRepository()
    campana = await repo.obtener_campana(campana_id)
    if campana is None:
        raise CuponInvalido("Campaña no encontrada")
    if campana["estado"] == "enviada":
        raise CampanaBloqueada("Esta campaña ya fue enviada — no se puede reenviar")

    suscriptores = await repo.listar_suscriptores_activos()
    destinatarios = [s["email"] for s in suscriptores]

    enviados = await sender.enviar(destinatarios, campana["nombre"], campana["plantilla"])

    actualizada = await repo.actualizar_campana(
        campana_id, {"estado": "enviada", "fecha_envio": _ahora_iso()}
    )
    await AuditService().insertar(
        "enviar_campana", "campanas_email", usuario_id=usuario["id"], registro_id=campana_id,
        detalle={"destinatarios": len(destinatarios), "enviados": enviados},
    )
    return actualizada


async def actualizar_default_acumulacion(usuario: dict, acumulable: bool) -> None:
    repo = OfertasRepository()
    await repo.actualizar_config("cupones.acumulable_con_paquete_default", "true" if acumulable else "false")
    await AuditService().insertar(
        "configurar_acumulacion_cupon_paquete", "configuracion_sistema", usuario_id=usuario["id"],
        detalle={"acumulable_con_paquete_default": acumulable},
    )
