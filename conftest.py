"""Fixtures compartidas por todos los módulos (`app/*/tests/`).

pytest descubre este archivo automáticamente por estar en la raíz del
repo, junto a `pytest.ini` — no requiere import explícito desde ningún
`conftest.py` de módulo.
"""

import datetime
import uuid

import httpx
import pytest
from httpx import ASGITransport

from app.main import app
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_catalog_reader, minio_operational_client
from app.shared.pocketbase_client import get_pocketbase_client

DEFAULT_PASSWORD = "ClaveSegura#123"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def pb():
    return get_pocketbase_client()


@pytest.fixture
async def usuario_factory(pb):
    """Crea usuarios de PocketBase desechables para pruebas; los borra al finalizar."""
    creados: list[str] = []

    async def _crear(
        tipo_actor: str = "pasajero",
        activo: bool = True,
        rol_id: str | None = None,
        password: str = DEFAULT_PASSWORD,
        **extra,
    ) -> dict:
        # `usuarios.rol_id` es obligatorio para los 3 tipos de actor (migración
        # 2026-07-27) — si el llamador no pasa uno explícito y es pasajero, se
        # usa el rol de sistema "Pasajero" sembrado por seed_seguridad.py,
        # igual que en producción (autoregistro / alta manual).
        if rol_id is None and tipo_actor == "pasajero" and "rol_id" not in extra:
            rol_pasajero = await pb.get_first("roles", 'nombre="Pasajero"')
            assert rol_pasajero is not None, "seed_seguridad.py debe correrse antes de la suite de tests"
            rol_id = rol_pasajero["id"]

        email = f"test.{uuid.uuid4().hex[:10]}@aerotrack.test"
        # `usuarios` ya no tiene columna `tipo_actor` (migración 2026-07-27,
        # ver roles.tipo_panel) — el parámetro de arriba solo se usa para
        # resolver un `rol_id` por default cuando no se pasa uno explícito.
        data = {
            "email": email,
            "password": password,
            "passwordConfirm": password,
            "nombre_completo": "Usuario de Prueba",
            "activo": activo,
            "emailVisibility": True,
            "verified": True,
        }
        if rol_id:
            data["rol_id"] = rol_id
        data.update(extra)
        record = await pb.create_record("usuarios", data)
        record["_password"] = password
        creados.append(record["id"])
        return record

    yield _crear

    for usuario_id in creados:
        try:
            await pb.delete_record("usuarios", usuario_id)
        except Exception:
            pass


@pytest.fixture
async def rol_administrador(pb):
    rol = await pb.get_first("roles", 'nombre="Administrador"')
    assert rol is not None, "seed_seguridad.py debe correrse antes de la suite de tests"
    return rol


@pytest.fixture
async def rol_agente(pb):
    rol = await pb.get_first("roles", 'nombre="Agente"')
    assert rol is not None, "seed_seguridad.py debe correrse antes de la suite de tests"
    return rol


@pytest.fixture
async def admin_client(client, usuario_factory, rol_administrador):
    """Cliente ya autenticado como Administrador (rol sembrado, permisos completos)."""
    usuario = await usuario_factory(tipo_actor="administrador", rol_id=rol_administrador["id"])
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    client.admin_usuario = usuario
    return client


@pytest.fixture
async def agente_client(client, usuario_factory, rol_agente):
    """Cliente ya autenticado como Agente (rol sembrado, permisos según RBAC de cada módulo)."""
    usuario = await usuario_factory(tipo_actor="agente", rol_id=rol_agente["id"])
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    client.agente_usuario = usuario
    return client


@pytest.fixture
async def vuelo_factory(pb):
    """Crea vuelos_catalogo desechables para pruebas; los borra al finalizar.

    `vuelos_catalogo` es STAGING (ver plan de migración) — las búsquedas
    (`router_busqueda.py`) leen del snapshot NDJSON en MinIO, no de
    PocketBase directo. Por eso cada creación/borrado republica la
    colección para que el vuelo de prueba sea visible de inmediato en vez
    de esperar al DAG diario (`aerotrack_travel_publicar_catalogo`)."""
    creados: list[str] = []

    async def _crear(estado: str = "programado", generado_por: str = "sistema", **extra) -> dict:
        aerolinea = await pb.get_first("aerolineas", "activa=true")
        data = {
            "numero_vuelo": f"TST{uuid.uuid4().hex[:6].upper()}",
            "aerolinea_id": aerolinea["id"],
            "origen_codigo": "JFK",
            "destino_codigo": "LAX",
            "fecha_salida": "2027-01-01",
            "hora_salida_programada": "10:00",
            "hora_llegada_programada": "13:00",
            "duracion_min": 180,
            "precio_base": 199.0,
            "estado": estado,
            "generado_por": generado_por,
        }
        data.update(extra)
        vuelo = await pb.create_record("vuelos_catalogo", data)
        creados.append(vuelo["id"])
        await minio_catalog_reader.publicar_y_refrescar("vuelos_catalogo")
        return vuelo

    yield _crear

    for vuelo_id in creados:
        try:
            await pb.delete_record("vuelos_catalogo", vuelo_id)
        except Exception:
            pass
    if creados:
        await minio_catalog_reader.publicar_y_refrescar("vuelos_catalogo")


@pytest.fixture
async def tarifa_factory(pb):
    """Crea tarifas_vuelo desechables para pruebas; las borra al finalizar.
    Mismo motivo de republicación que `vuelo_factory` — ver ahí."""
    creadas: list[str] = []

    async def _crear(
        vuelo_id: str,
        cupos_disponibles: int = 5,
        precio_final: float = 199.0,
        nivel_tarifa_id: str | None = None,
    ) -> dict:
        if nivel_tarifa_id is None:
            niveles = await pb.list_records("niveles_tarifa", {"perPage": 1})
            nivel_tarifa_id = niveles["items"][0]["id"]
        tarifa = await pb.create_record(
            "tarifas_vuelo",
            {
                "vuelo_id": vuelo_id,
                "nivel_tarifa_id": nivel_tarifa_id,
                "precio_final": precio_final,
                "cupos_disponibles": cupos_disponibles,
            },
        )
        creadas.append(tarifa["id"])
        await minio_catalog_reader.publicar_y_refrescar("tarifas_vuelo")
        return tarifa

    yield _crear

    for tarifa_id in creadas:
        try:
            await pb.delete_record("tarifas_vuelo", tarifa_id)
        except Exception:
            pass
    if creadas:
        await minio_catalog_reader.publicar_y_refrescar("tarifas_vuelo")


@pytest.fixture
async def pasajero_factory(pb, usuario_factory):
    """Crea un usuario tipo_actor=pasajero CON su perfil `pasajeros` vinculado
    (reservas.pasajero_titular_id apunta a `pasajeros`, no a `usuarios`).

    `pasajeros` es OPERACIONAL, migrado a MinIO — se crea vía
    `PasajerosRepository`, no `pb.create_record` directo (ver plan de
    migración)."""
    creados_pasajeros: list[str] = []

    async def _crear(**extra_usuario) -> tuple[dict, dict]:
        usuario = await usuario_factory(tipo_actor="pasajero", **extra_usuario)
        pasajero = await PasajerosRepository().crear_pasajero(
            {"usuario_id": usuario["id"], "fecha_nacimiento": "1990-01-01", "telefono": "0999999999"},
        )
        creados_pasajeros.append(pasajero["id"])
        return usuario, pasajero

    yield _crear

    for pasajero_id in creados_pasajeros:
        try:
            await minio_operational_client.eliminar("pasajeros", pasajero_id)
        except Exception:
            pass
        try:
            await pb.delete_record("pasajeros", pasajero_id)  # limpia el espejo, ver RC-OP-003
        except Exception:
            pass


@pytest.fixture
async def pasajero_client(client, pasajero_factory):
    """Cliente ya autenticado como un pasajero recién creado — para probar
    routers HTML que dependen de `verificar_sesion` (p. ej. Carrito, Autos)
    sin repetir el login en cada módulo."""
    usuario, pasajero = await pasajero_factory()
    resp = await client.post(
        "/login", data={"email": usuario["email"], "password": usuario["_password"]}
    )
    assert resp.status_code == 303
    client.pasajero = pasajero
    client.pasajero_usuario = usuario
    return client


@pytest.fixture
async def reserva_factory():
    """Crea una `reservas` desechable directamente (sin pasar por el
    servicio) — para pruebas que necesitan una reserva ya existente.

    También crea el `reserva_items` correspondiente (tipo_producto=vuelo),
    mismo dual-write que `crear_reserva_service.py` — para que las pruebas
    que arman datos con esta fábrica reflejen el modelo v3 real, no solo el
    campo legado `reservas.vuelo_id`.

    `reservas`/`reserva_items` son OPERACIONAL, migradas a MinIO (paso 5
    del plan) — se crean vía `ReservasRepository`, no `pb.create_record`
    directo."""
    creadas: list[str] = []
    items_creados: list[str] = []

    async def _crear(pasajero_id: str, vuelo_id: str, tarifa_id: str, **extra) -> dict:
        repo = ReservasRepository()
        ahora = datetime.datetime.now(datetime.timezone.utc)
        precio_final = extra.get("total_pagar", 199.0)
        data = {
            "codigo_reserva": f"PNR{uuid.uuid4().hex[:8].upper()}",
            "pasajero_titular_id": pasajero_id,
            "vuelo_id": vuelo_id,
            "tarifa_id": tarifa_id,
            "canal": "autoservicio",
            "estado": "pendiente_pago",
            "total_pagar": 199.0,
            "fecha_reserva": ahora.strftime("%Y-%m-%d %H:%M:%S.000Z"),
            "fecha_expiracion_pago": (ahora + datetime.timedelta(minutes=15)).strftime(
                "%Y-%m-%d %H:%M:%S.000Z"
            ),
        }
        data.update(extra)
        reserva = await repo.crear_reserva(data)
        creadas.append(reserva["id"])
        item = await repo.crear_item(
            {
                "reserva_id": reserva["id"],
                "tipo_producto": "vuelo",
                "vuelo_id": vuelo_id,
                "tarifa_vuelo_id": tarifa_id,
                "precio_final": precio_final,
                "estado_item": "pendiente",
            },
        )
        items_creados.append(item["id"])
        return reserva

    yield _crear

    for item_id in items_creados:
        try:
            await minio_operational_client.eliminar("reserva_items", item_id)
        except Exception:
            pass

    for reserva_id in creadas:
        try:
            await minio_operational_client.eliminar("reservas", reserva_id)
        except Exception:
            pass
