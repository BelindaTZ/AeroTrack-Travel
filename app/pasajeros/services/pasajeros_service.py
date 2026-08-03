import re
from datetime import date

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.usuarios_service import CorreoDuplicado, UsuariosService
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository


TELEFONO_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,15}$")

# RN-SEG-011 (retención mínima) aplicada aquí, no solo a borrado de datos
# personales: un pasajero con una reserva todavía en curso no puede
# eliminarse — dejaría `reservas.pasajero_titular_id` apuntando a un
# registro inexistente, y al pasajero sin forma de gestionar esa reserva.
RESERVAS_QUE_BLOQUEAN_ELIMINACION = {"pendiente_pago", "confirmada"}


class PasajeroNoEncontrado(Exception):
    pass


class TelefonoInvalido(Exception):
    def __init__(self) -> None:
        super().__init__("El formato del teléfono no es válido. Usa solo dígitos, espacios, guiones o paréntesis (7-15 caracteres).")


class PasajeroConReservasActivas(Exception):
    def __init__(self, cantidad: int) -> None:
        self.cantidad = cantidad
        super().__init__(f"{cantidad} reserva(s) activa(s)")


async def obtener_historial(
    usuario: dict,
    estado: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
) -> list[dict]:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return []

    reservas_raw = await repo.reservas_de_pasajero(pasajero["id"], estado=estado)
    vuelos_repo = VuelosRepository()
    resultado = []
    for r in reservas_raw:
        # `vuelo_id`/`tarifa_id` son el dual-write LEGADO de la reserva
        # single-producto original — una reserva armada solo con hotel/auto/
        # actividad/crucero (modelo v3, `reserva_items`) nunca los escribe,
        # así que ni siquiera existe la key. Esta vista es específicamente
        # de historial de VUELOS (RF-PAS-001/CU-O14, ver forma del dict de
        # salida), no un historial general — se salta lo que no es vuelo en
        # vez de fallar. Mostrar el historial completo multi-producto queda
        # fuera de este fix puntual.
        if not r.get("vuelo_id"):
            continue
        vuelo = await vuelos_repo.obtener_vuelo(r["vuelo_id"])
        if vuelo is None:
            continue
        tarifa = await vuelos_repo.obtener_tarifa(r["tarifa_id"])
        aerolinea = await vuelos_repo.obtener_aerolinea(vuelo["aerolinea_id"])
        nivel = await vuelos_repo.nivel_tarifa(tarifa["nivel_tarifa_id"])
        fecha_salida = vuelo["fecha_salida"][:10]
        # RNF-PAS-001: rango de fecha es sobre la fecha de VUELO, no la de
        # creación de la reserva — `fecha_salida` solo existe en el vuelo,
        # por eso se compara aquí y no en el filtro de PocketBase.
        if fecha_desde and fecha_salida < fecha_desde:
            continue
        if fecha_hasta and fecha_salida > fecha_hasta:
            continue
        resultado.append(
            {
                "id": r["id"],
                "codigo_reserva": r["codigo_reserva"],
                "estado": r["estado"],
                "numero_vuelo": vuelo["numero_vuelo"],
                "aerolinea_nombre": aerolinea["nombre"],
                "origen_legible": await resolver_aeropuerto(vuelo["origen_codigo"]),
                "destino_legible": await resolver_aeropuerto(vuelo["destino_codigo"]),
                "fecha_salida": fecha_salida,
                "total_pagar": r["total_pagar"],
                "nivel_tarifa": nivel["nombre"],
            }
        )
    resultado.sort(key=lambda r: r["fecha_salida"], reverse=True)
    return resultado


async def actualizar_contacto(
    usuario: dict,
    telefono: str,
    direccion: str | None = None,
    contacto_emergencia: str | None = None,
) -> dict:
    if not TELEFONO_RE.match(telefono):
        raise TelefonoInvalido()

    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    data = {"telefono": telefono}
    if direccion is not None:
        # Campo real en PocketBase: direccion_facturacion (ver mismo fix en
        # router_backoffice.py) — "direccion" no existe en el esquema.
        data["direccion_facturacion"] = direccion
    if contacto_emergencia is not None:
        data["contacto_emergencia"] = contacto_emergencia

    actualizado = await repo.actualizar_contacto(pasajero["id"], data)
    await AuditService().insertar(
        "editar",
        "pasajeros",
        usuario_id=usuario["id"],
        registro_id=pasajero["id"],
        detalle={"campos": list(data.keys()), "origen": "autoservicio"},
    )
    return actualizado


async def buscar_pasajeros_backoffice(
    usuario: dict,
    nombre: str | None = None,
    email: str | None = None,
    documento: str | None = None,
    telefono: str | None = None,
    pasajero_id: str | None = None,
) -> list[dict]:
    """WP-01 (auditoría de WorkPanels) — filtros AND: cada criterio provisto
    debe matchear (nombre/email en `usuarios`, documento/teléfono en
    `pasajeros`). Sin ningún filtro, devuelve el listado completo (la
    paginación del router se encarga de no volcarlo entero a la pantalla).

    `pasajero_id` ignora el resto de los filtros y aísla un único registro
    — usado al volver de una acción sobre las tablas de detalle (documentos
    de viaje) para garantizar que esa fila (y su modal) esté en la página
    actual sin importar dónde caiga alfabéticamente en el listado completo."""
    repo = PasajerosRepository()
    usuarios = await repo.listar_todos_usuarios_pasajero()
    pasajeros = await repo.listar_todos_pasajeros()
    pasajeros_por_usuario_id = {p.get("usuario_id"): p for p in pasajeros}

    nombre_bajo = nombre.lower() if nombre else None
    email_bajo = email.lower() if email else None
    documento_bajo = documento.lower() if documento else None
    telefono_bajo = telefono.lower() if telefono else None

    resultado = []
    for u in usuarios:
        pasajero = pasajeros_por_usuario_id.get(u["id"])
        if pasajero is None:
            # Cuenta desactivada sin perfil (WP-01 "Eliminar" borra el perfil
            # de `pasajeros` y solo desactiva `usuarios`, ver
            # eliminar_pasajero_backoffice) — no tiene nada que listar acá.
            continue
        if pasajero_id:
            if pasajero["id"] == pasajero_id:
                resultado.append(_aplanar(u, pasajero))
            continue
        if nombre_bajo and nombre_bajo not in (u.get("nombre_completo") or "").lower():
            continue
        if email_bajo and email_bajo not in (u.get("email") or "").lower():
            continue
        if documento_bajo and documento_bajo not in (pasajero.get("numero_documento") or "").lower():
            continue
        if telefono_bajo and telefono_bajo not in (pasajero.get("telefono") or "").lower():
            continue
        resultado.append(_aplanar(u, pasajero))

    resultado.sort(key=lambda r: r["nombre_completo"])
    return resultado


# ── CU-T05 (export con filtros) / CU-T37 (captación por canal) ────────
async def listar_pasajeros_reporte(
    desde: str | None = None,
    hasta: str | None = None,
    destino: str | None = None,
    frecuencia_min: int | None = None,
    canal_registro: str | None = None,
) -> list[dict]:
    """Base común de T05 (exportar pasajeros con filtros) y T37 (captación
    por período/canal) — un solo barrido en memoria, mismo criterio que
    `ReservasRepository.listar_todas` (el volumen del proyecto no justifica
    más que eso). `destino` filtra por cualquier reserva del pasajero cuyo
    vuelo tenga ese código de destino; `frecuencia_min` por número total de
    reservas."""
    repo = PasajerosRepository()
    usuarios = await repo.listar_todos_usuarios_pasajero()
    pasajeros = await repo.listar_todos_pasajeros()
    pasajeros_por_usuario_id = {p.get("usuario_id"): p for p in pasajeros}

    reservas_repo = ReservasRepository()
    todas_reservas = await reservas_repo.listar_todas()
    reservas_por_pasajero: dict[str, list[dict]] = {}
    for r in todas_reservas:
        pid = r.get("pasajero_titular_id")
        if pid:
            reservas_por_pasajero.setdefault(pid, []).append(r)

    vuelos_repo = VuelosRepository()
    cache_destinos: dict[str, str] = {}

    async def _destinos_de(reservas: list[dict]) -> set[str]:
        codigos = set()
        for r in reservas:
            vuelo_id = r.get("vuelo_id")
            if not vuelo_id:
                continue
            if vuelo_id not in cache_destinos:
                vuelo = await vuelos_repo.obtener_vuelo(vuelo_id)
                cache_destinos[vuelo_id] = vuelo["destino_codigo"] if vuelo else ""
            if cache_destinos[vuelo_id]:
                codigos.add(cache_destinos[vuelo_id])
        return codigos

    resultado = []
    for u in usuarios:
        fecha_registro = (u.get("created") or "")[:10]
        if desde and fecha_registro < desde:
            continue
        if hasta and fecha_registro > hasta:
            continue

        pasajero = pasajeros_por_usuario_id.get(u["id"])
        canal = (pasajero or {}).get("canal_registro") or "sin_canal"
        if canal_registro and canal != canal_registro:
            continue

        pid = (pasajero or {}).get("id")
        reservas_pas = reservas_por_pasajero.get(pid, []) if pid else []
        if frecuencia_min is not None and len(reservas_pas) < frecuencia_min:
            continue

        destinos = await _destinos_de(reservas_pas)
        if destino and destino not in destinos:
            continue

        resultado.append(
            {
                "usuario_id": u["id"],
                "nombre_completo": u.get("nombre_completo", ""),
                "email": u.get("email", ""),
                "fecha_registro": fecha_registro,
                "canal_registro": canal,
                "num_reservas": len(reservas_pas),
                "destinos": sorted(destinos),
            }
        )
    resultado.sort(key=lambda r: r["fecha_registro"], reverse=True)
    return resultado


async def documentos_de_pasajero(pasajero_id: str) -> list[dict]:
    return await PasajerosRepository().documentos_de_pasajero(pasajero_id)


async def obtener_detalle_pasajero(usuario: dict, pasajero_id: str) -> dict | None:
    repo = PasajerosRepository()
    pasajero = await repo.obtener_pasajero(pasajero_id)
    if pasajero is None:
        return None
    u = await repo.usuario_por_id(pasajero["usuario_id"])
    if u is None:
        return None
    historial = await obtener_historial(u)
    detalle = _aplanar(u, pasajero)
    detalle["historial_reservas"] = historial
    detalle["documentos"] = await repo.documentos_de_pasajero(pasajero_id)
    detalle["genero"] = pasajero.get("genero")
    return detalle


async def editar_contacto_backoffice(usuario: dict, pasajero_id: str, data: dict) -> dict:
    repo = PasajerosRepository()
    pasajero = await repo.obtener_pasajero(pasajero_id)
    if pasajero is None:
        raise PasajeroNoEncontrado()

    actualizado = await repo.actualizar_contacto(pasajero_id, data)
    await AuditService().insertar(
        "editar",
        "pasajeros",
        usuario_id=usuario["id"],
        registro_id=pasajero_id,
        detalle={"campos_modificados": list(data.keys()), "origen": "backoffice", "agente_id": usuario["id"]},
    )
    return actualizado


# ── WP-01 (auditoría de WorkPanels, 2026-07-31) — CRUD completo desde backoffice ──

async def crear_pasajero_backoffice(
    usuario_actor: dict,
    nombre_completo: str,
    email: str,
    password: str,
    fecha_nacimiento: date,
    telefono: str,
    genero: str | None = None,
    numero_documento: str | None = None,
    direccion_facturacion: str | None = None,
    contacto_emergencia: str | None = None,
    canal_registro: str = "agente_call_center",
) -> dict:
    if not TELEFONO_RE.match(telefono):
        raise TelefonoInvalido()

    usuario = await UsuariosService().crear_pasajero(
        nombre_completo=nombre_completo,
        email=email,
        password=password,
        fecha_nacimiento=fecha_nacimiento,
        telefono=telefono,
        genero=genero or None,
        numero_documento=numero_documento or None,
        direccion_facturacion=direccion_facturacion or None,
        contacto_emergencia=contacto_emergencia or None,
        canal_registro=canal_registro,
    )
    pasajero = await PasajerosRepository().pasajero_de_usuario(usuario["id"])
    await AuditService().insertar(
        "crear", "pasajeros", usuario_id=usuario_actor["id"], registro_id=pasajero["id"],
        detalle={"origen": "backoffice", "canal_registro": canal_registro},
    )
    return pasajero


async def editar_pasajero_backoffice_completo(
    usuario_actor: dict,
    pasajero_id: str,
    nombre_completo: str | None = None,
    email: str | None = None,
    telefono: str | None = None,
    fecha_nacimiento: date | None = None,
    genero: str | None = None,
    numero_documento: str | None = None,
    direccion_facturacion: str | None = None,
    contacto_emergencia: str | None = None,
) -> dict:
    if telefono is not None and not TELEFONO_RE.match(telefono):
        raise TelefonoInvalido()

    repo = PasajerosRepository()
    pasajero = await repo.obtener_pasajero(pasajero_id)
    if pasajero is None:
        raise PasajeroNoEncontrado()

    seguridad_repo = SeguridadRepository()
    campos_usuario: dict = {}
    if nombre_completo is not None:
        campos_usuario["nombre_completo"] = nombre_completo
    if email is not None:
        existente = await seguridad_repo.get_usuario_by_email(email)
        if existente is not None and existente["id"] != pasajero["usuario_id"]:
            raise CorreoDuplicado()
        campos_usuario["email"] = email
    if campos_usuario:
        await seguridad_repo.update_usuario(pasajero["usuario_id"], campos_usuario)

    campos_pasajero: dict = {}
    if telefono is not None:
        campos_pasajero["telefono"] = telefono
    if fecha_nacimiento is not None:
        campos_pasajero["fecha_nacimiento"] = fecha_nacimiento.isoformat()
    if genero is not None:
        campos_pasajero["genero"] = genero
    if numero_documento is not None:
        campos_pasajero["numero_documento"] = numero_documento
    if direccion_facturacion is not None:
        campos_pasajero["direccion_facturacion"] = direccion_facturacion
    if contacto_emergencia is not None:
        campos_pasajero["contacto_emergencia"] = contacto_emergencia
    if campos_pasajero:
        await repo.actualizar_contacto(pasajero_id, campos_pasajero)

    await AuditService().insertar(
        "editar", "pasajeros", usuario_id=usuario_actor["id"], registro_id=pasajero_id,
        detalle={
            "campos_modificados": list(campos_usuario.keys()) + list(campos_pasajero.keys()),
            "origen": "backoffice", "agente_id": usuario_actor["id"],
        },
    )
    return await obtener_detalle_pasajero(usuario_actor, pasajero_id)


async def eliminar_pasajero_backoffice(usuario_actor: dict, pasajero_id: str) -> None:
    repo = PasajerosRepository()
    pasajero = await repo.obtener_pasajero(pasajero_id)
    if pasajero is None:
        raise PasajeroNoEncontrado()

    reservas = await repo.reservas_de_pasajero(pasajero_id)
    activas = [r for r in reservas if r.get("estado") in RESERVAS_QUE_BLOQUEAN_ELIMINACION]
    if activas:
        raise PasajeroConReservasActivas(len(activas))

    await repo.eliminar_pasajero(pasajero_id)
    # Se desactiva la cuenta en vez de borrarla (mismo criterio que
    # `editar_usuario_interno`/WP-02): `usuarios` tiene referencias desde
    # auditoría y otras colecciones que no conviene dejar colgando.
    await SeguridadRepository().update_usuario(pasajero["usuario_id"], {"activo": False})

    await AuditService().insertar(
        "eliminar", "pasajeros", usuario_id=usuario_actor["id"], registro_id=pasajero_id,
        detalle={"origen": "backoffice"},
    )


# ── RF-PAS-005 (CU-O49) — documentos de viaje ──────────────────────────

TIPOS_DOCUMENTO_VALIDOS = {"pasaporte", "cedula", "otro"}


class TipoDocumentoInvalido(Exception):
    pass


class SinPermiso(Exception):
    pass


async def listar_documentos(usuario: dict) -> list[dict]:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return []
    return await repo.documentos_de_pasajero(pasajero["id"])


async def crear_documento_viaje(
    usuario: dict, tipo: str, numero: str, pais_emision: str, fecha_vencimiento: str | None = None
) -> dict:
    if tipo not in TIPOS_DOCUMENTO_VALIDOS:
        raise TipoDocumentoInvalido()

    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    data = {"pasajero_id": pasajero["id"], "tipo": tipo, "numero": numero, "pais_emision": pais_emision}
    if fecha_vencimiento:
        data["fecha_vencimiento"] = fecha_vencimiento

    documento = await repo.crear_documento(data)
    await AuditService().insertar(
        "crear", "documentos_viaje", usuario_id=usuario["id"], registro_id=documento["id"],
        detalle={"tipo": tipo},
    )
    return documento


async def eliminar_documento_viaje(usuario: dict, documento_id: str) -> None:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    documento = await repo.obtener_documento(documento_id)
    if documento is None or documento["pasajero_id"] != pasajero["id"]:
        raise SinPermiso()

    await repo.eliminar_documento(documento_id)
    await AuditService().insertar(
        "eliminar", "documentos_viaje", usuario_id=usuario["id"], registro_id=documento_id,
    )


# ── Variantes de backoffice (WP-01) — operan sobre un `pasajero_id`
# arbitrario en vez de resolverlo desde la sesión del propio pasajero. ──

async def crear_documento_viaje_backoffice(
    usuario_actor: dict, pasajero_id: str, tipo: str, numero: str, pais_emision: str,
    fecha_vencimiento: str | None = None,
) -> dict:
    if tipo not in TIPOS_DOCUMENTO_VALIDOS:
        raise TipoDocumentoInvalido()

    repo = PasajerosRepository()
    if await repo.obtener_pasajero(pasajero_id) is None:
        raise PasajeroNoEncontrado()

    data = {"pasajero_id": pasajero_id, "tipo": tipo, "numero": numero, "pais_emision": pais_emision}
    if fecha_vencimiento:
        data["fecha_vencimiento"] = fecha_vencimiento

    documento = await repo.crear_documento(data)
    await AuditService().insertar(
        "crear", "documentos_viaje", usuario_id=usuario_actor["id"], registro_id=documento["id"],
        detalle={"tipo": tipo, "origen": "backoffice"},
    )
    return documento


async def eliminar_documento_viaje_backoffice(usuario_actor: dict, pasajero_id: str, documento_id: str) -> None:
    repo = PasajerosRepository()
    documento = await repo.obtener_documento(documento_id)
    if documento is None or documento["pasajero_id"] != pasajero_id:
        raise SinPermiso()

    await repo.eliminar_documento(documento_id)
    await AuditService().insertar(
        "eliminar", "documentos_viaje", usuario_id=usuario_actor["id"], registro_id=documento_id,
        detalle={"origen": "backoffice"},
    )


# ── RF-PAS-006 (CU-O50) — viajeros frecuentes ──────────────────────────

async def listar_viajeros_frecuentes(usuario: dict) -> list[dict]:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        return []
    return await repo.viajeros_frecuentes_de_pasajero(pasajero["id"])


async def crear_viajero_frecuente(
    usuario: dict,
    nombre_completo: str,
    fecha_nacimiento: str | None = None,
    numero_documento: str | None = None,
    relacion: str | None = None,
) -> dict:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    data = {"pasajero_id": pasajero["id"], "nombre_completo": nombre_completo}
    if fecha_nacimiento:
        data["fecha_nacimiento"] = fecha_nacimiento
    if numero_documento:
        data["numero_documento"] = numero_documento
    if relacion:
        data["relacion"] = relacion

    viajero = await repo.crear_viajero_frecuente(data)
    await AuditService().insertar(
        "crear", "viajeros_frecuentes", usuario_id=usuario["id"], registro_id=viajero["id"],
    )
    return viajero


async def eliminar_viajero_frecuente(usuario: dict, viajero_id: str) -> None:
    repo = PasajerosRepository()
    pasajero = await repo.pasajero_de_usuario(usuario["id"])
    if pasajero is None:
        raise PasajeroNoEncontrado()

    viajero = await repo.obtener_viajero_frecuente(viajero_id)
    if viajero is None or viajero["pasajero_id"] != pasajero["id"]:
        raise SinPermiso()

    await repo.eliminar_viajero_frecuente(viajero_id)
    await AuditService().insertar(
        "eliminar", "viajeros_frecuentes", usuario_id=usuario["id"], registro_id=viajero_id,
    )


def _aplanar(usuario: dict, pasajero: dict | None) -> dict:
    return {
        "id": (pasajero or {}).get("id", ""),
        "usuario_id": usuario["id"],
        "nombre_completo": usuario.get("nombre_completo", ""),
        "email": usuario.get("email", ""),
        "telefono": (pasajero or {}).get("telefono"),
        "direccion": (pasajero or {}).get("direccion_facturacion"),
        "contacto_emergencia": (pasajero or {}).get("contacto_emergencia"),
        "fecha_nacimiento": (pasajero or {}).get("fecha_nacimiento"),
        "genero": (pasajero or {}).get("genero"),
        "numero_documento": (pasajero or {}).get("numero_documento"),
    }


