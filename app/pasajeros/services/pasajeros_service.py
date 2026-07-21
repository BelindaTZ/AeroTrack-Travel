import re

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.services.audit_service import AuditService
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository


TELEFONO_RE = re.compile(r"^\+?[\d\s\-\(\)]{7,15}$")


class PasajeroNoEncontrado(Exception):
    pass


class TelefonoInvalido(Exception):
    def __init__(self) -> None:
        super().__init__("El formato del teléfono no es válido. Usa solo dígitos, espacios, guiones o paréntesis (7-15 caracteres).")


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
        vuelo = await vuelos_repo.obtener_vuelo(r["vuelo_id"])
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
        data["direccion"] = direccion
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


async def buscar_pasajeros_backoffice(usuario: dict, termino: str) -> list[dict]:
    repo = PasajerosRepository()
    usuarios = await repo.buscar_usuarios(termino)
    pasajeros = await repo.buscar_pasajeros(termino)

    pasajeros_por_usuario_id = {p.get("usuario_id"): p for p in pasajeros}

    # Unión de ambas búsquedas (por nombre/correo de usuario, por teléfono/
    # contacto de emergencia de pasajero) — un match en cualquiera de las
    # dos basta, no se exige que aparezca en ambas.
    resultado = []
    vistos_usuario_id = set()
    for u in usuarios:
        resultado.append(_aplanar(u, pasajeros_por_usuario_id.get(u["id"])))
        vistos_usuario_id.add(u["id"])

    for p in pasajeros:
        uid = p.get("usuario_id")
        if uid and uid not in vistos_usuario_id:
            u = await repo.usuario_por_id(uid)
            if u:
                resultado.append(_aplanar(u, p))
                vistos_usuario_id.add(uid)
    return resultado


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


def _aplanar(usuario: dict, pasajero: dict | None) -> dict:
    return {
        "id": (pasajero or {}).get("id", ""),
        "usuario_id": usuario["id"],
        "nombre_completo": usuario.get("nombre_completo", ""),
        "email": usuario.get("email", ""),
        "telefono": (pasajero or {}).get("telefono"),
        "direccion": (pasajero or {}).get("direccion"),
        "contacto_emergencia": (pasajero or {}).get("contacto_emergencia"),
        "fecha_nacimiento": (pasajero or {}).get("fecha_nacimiento"),
    }


