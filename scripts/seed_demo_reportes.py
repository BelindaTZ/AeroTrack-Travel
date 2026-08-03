"""Datos demo para que los informes simples nuevos (T05, T16/T17, T18,
T24, T36/T46, T37, T43/T44, T55) tengan algo que mostrar en capturas —
no reemplaza datos reales, solo agrega variedad donde hoy está vacío o
plano (todo en un mismo canal_registro, 0 favoritos, 0 niveles de
beneficios, etc.). Idempotente por clave natural en cada bloque.

Requiere: scripts/seed_roles_departamento.py y
scripts/seed_usuarios_demo_departamento.py ya corridos (usa el usuario
demo.agente@aerotrack.test como agente_id de las reservas asistidas).

Ejecutar: python scripts/seed_demo_reportes.py
"""

import asyncio
import datetime
import sys

sys.path.insert(0, ".")

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client
from app.vuelos.repositories.vuelos_repo import VuelosRepository

CANALES = ["autoservicio_web", "agente_call_center", "presencial_counter"]

NIVELES_BENEFICIOS = [
    # puntos_minimos=1 (no 0) a propósito — RN-CTA-002 espera que un
    # pasajero SIN movimientos no tenga nivel asignado todavía (ver
    # `test_sin_movimientos_saldo_cero_y_sin_nivel`); Bronce arranca en el
    # primer punto ganado, no antes.
    {"nombre_nivel": "Bronce", "puntos_minimos": 1, "puntos_por_dolar": 1, "vencimiento_meses": 12,
     "beneficios": "Acumulación estándar de puntos"},
    {"nombre_nivel": "Plata", "puntos_minimos": 2000, "puntos_por_dolar": 1.25, "vencimiento_meses": 18,
     "beneficios": "10% más puntos, check-in prioritario"},
    {"nombre_nivel": "Oro", "puntos_minimos": 6000, "puntos_por_dolar": 1.5, "vencimiento_meses": 24,
     "beneficios": "Equipaje adicional gratis, sala VIP en escalas largas"},
    {"nombre_nivel": "Platino", "puntos_minimos": 15000, "puntos_por_dolar": 2, "vencimiento_meses": 36,
     "beneficios": "Upgrade automático sujeto a disponibilidad, línea de atención dedicada"},
]

CASOS_DEMO = [
    {"asunto": "Equipaje extraviado en escala", "mensaje": "Mi maleta no llegó en la conexión de Miami, necesito seguimiento."},
    {"asunto": "Reembolso no procesado", "mensaje": "Cancelé mi reserva hace 5 días y todavía no veo el reembolso reflejado."},
]


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def backfill_canal_registro() -> None:
    pasajeros = await moc.listar_todos("pasajeros")
    sin_canal = [p for p in pasajeros if not p.get("canal_registro")]
    if not sin_canal:
        print("= canal_registro: todos los pasajeros ya tienen valor")
        return
    # Solo se backfillea una muestra (30) para tener variedad real en el
    # reporte T37 sin reescribir de golpe los ~130 registros de prueba
    # acumulados por la suite de tests.
    muestra = sin_canal[:30]
    for i, p in enumerate(muestra):
        canal = CANALES[i % len(CANALES)]

        def _mutar(actual: dict, canal=canal) -> dict:
            actual["canal_registro"] = canal
            return actual

        # Solo MinIO (fuente real de `pasajeros`) — el espejo en PocketBase
        # no tiene `canal_registro` en su esquema y nunca se lee de vuelta
        # (ver docstring de PasajerosRepository), no hace falta espejarlo.
        await moc.actualizar_con_reintento("pasajeros", p["id"], _mutar)
    print(f"+ canal_registro backfilleado en {len(muestra)} pasajeros (muestra)")


async def seed_niveles_beneficios(cuenta_repo: CuentaRepository) -> None:
    existentes = {n["nombre_nivel"] for n in await cuenta_repo.niveles_programa_beneficios()}
    creados = 0
    for nivel in NIVELES_BENEFICIOS:
        if nivel["nombre_nivel"] in existentes:
            continue
        await cuenta_repo.crear_nivel_beneficio(nivel)
        creados += 1
    print(f"+ {creados} niveles de programa de beneficios creados" if creados else "= niveles de beneficios ya sembrados")


async def seed_favoritos(cuenta_repo: CuentaRepository, pasajero_ids: list[str]) -> None:
    existentes = await cuenta_repo.listar_todos_favoritos()
    if existentes:
        print(f"= favoritos ya existen ({len(existentes)})")
        return
    productos = [
        ("vuelo", "MIA"), ("vuelo", "MIA"), ("vuelo", "LAX"),
        ("hotel", "Barcelona"), ("hotel", "Barcelona"), ("hotel", "Cancun"),
        ("actividad", "Roma"), ("crucero", "Caribe"),
    ]
    ahora = _timestamp()
    for i, (tipo, ref) in enumerate(productos):
        pasajero_id = pasajero_ids[i % len(pasajero_ids)]
        await cuenta_repo.crear_favorito(pasajero_id, tipo, ref, ahora)
    print(f"+ {len(productos)} favoritos demo creados")


async def seed_reservas_agente(reservas_repo: ReservasRepository, pasajero_ids: list[str], agente_id: str, vuelo_ids: list[str], vuelos_repo: VuelosRepository) -> None:
    existentes = await reservas_repo.listar_todas(agente_id=agente_id)
    if existentes:
        print(f"= reservas asistidas del agente demo ya existen ({len(existentes)})")
        return

    ahora = datetime.datetime.now(datetime.UTC)
    escenarios = [
        # (estado, horas_para_expirar_pago, total)
        ("pendiente_pago", 4, 320.50),   # a punto de vencer — T44/T17
        ("pendiente_pago", 30, 210.00),  # todavía con margen
        ("confirmada", None, 540.75),
        ("confirmada", None, 189.90),
    ]
    for i, (estado, horas, total) in enumerate(escenarios):
        pasajero_id = pasajero_ids[i % len(pasajero_ids)]
        vuelo_id = vuelo_ids[i % len(vuelo_ids)]
        # `construir_detalle` (router_reservas.py) trata `vuelo_id` no vacío
        # como reserva de un solo vuelo y exige `tarifa_id` real para
        # resolver el nivel de tarifa — dejarlo en "" rompe /mis-viajes con
        # un 500 (KeyError: 'nivel_tarifa_id'), hallazgo real 2026-07-27.
        tarifas_del_vuelo = await vuelos_repo.tarifas_de_vuelo(vuelo_id)
        tarifa_id = tarifas_del_vuelo[0]["id"] if tarifas_del_vuelo else ""
        expiracion = (ahora + datetime.timedelta(hours=horas)).strftime("%Y-%m-%d %H:%M:%S.000Z") if horas else ""
        codigo = f"DEMO{i:03d}{estado[:3].upper()}"
        await reservas_repo.crear_reserva(
            {
                "codigo_reserva": codigo,
                "estado": estado,
                "canal": "asistida",
                "agente_id": agente_id,
                "pasajero_titular_id": pasajero_id,
                "vuelo_id": vuelo_id,
                "tarifa_id": tarifa_id,
                "total_pagar": total,
                "fecha_reserva": _timestamp(),
                "fecha_expiracion_pago": expiracion,
                "descuento_paquete_pct": 0,
                "es_paquete": False,
                "voucher_pdf": "",
            }
        )
    print(f"+ {len(escenarios)} reservas asistidas demo creadas para el agente")


async def seed_casos_escalados(client, pasajero_ids: list[str]) -> None:
    existentes = await moc.listar_todos("casos_escalados")
    if existentes:
        print(f"= casos escalados ya existen ({len(existentes)})")
        return
    for i, caso in enumerate(CASOS_DEMO):
        pasajero_id = pasajero_ids[i % len(pasajero_ids)]
        id_ = moc.generar_id()
        registro = {
            "id": id_, "created": _timestamp(), "updated": _timestamp(),
            "pasajero_id": pasajero_id, "asunto": caso["asunto"], "mensaje": caso["mensaje"],
            "estado": "abierto", "fecha_creacion": _timestamp(),
        }
        await moc.crear("casos_escalados", id_, registro)
    print(f"+ {len(CASOS_DEMO)} casos escalados demo creados")


async def main() -> None:
    client = get_pocketbase_client()
    pasajeros_repo = PasajerosRepository()
    cuenta_repo = CuentaRepository()
    reservas_repo = ReservasRepository()

    await backfill_canal_registro()
    await seed_niveles_beneficios(cuenta_repo)

    nombrados = (await client.list_records(
        "usuarios", {"filter": 'email~"toazam" || email~"repro"', "perPage": 20}
    ))["items"]
    pasajero_ids = []
    for u in nombrados:
        p = await pasajeros_repo.pasajero_de_usuario(u["id"])
        if p:
            pasajero_ids.append(p["id"])
    if not pasajero_ids:
        print("! no se encontraron pasajeros nombrados de referencia — abortando bloques que los necesitan")
        return

    await seed_favoritos(cuenta_repo, pasajero_ids)

    demo_agente = await client.get_first("usuarios", 'email="demo.agente@aerotrack.test"')
    vuelos = (await client.list_records("vuelos_catalogo", {"filter": 'estado="programado"', "perPage": 10}))["items"]
    vuelo_ids = [v["id"] for v in vuelos]
    if demo_agente and vuelo_ids:
        await seed_reservas_agente(reservas_repo, pasajero_ids, demo_agente["id"], vuelo_ids, VuelosRepository())
    else:
        print("! falta demo.agente o vuelos programados — correr seed_usuarios_demo_departamento.py primero")

    await seed_casos_escalados(client, pasajero_ids)

    print("Listo.")


if __name__ == "__main__":
    asyncio.run(main())
