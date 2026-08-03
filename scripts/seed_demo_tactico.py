"""Datos semisintéticos para que los 13 dashboards de Fase C (ETL +
ClickHouse) tengan algo real que mostrar — sesión 2026-08-02.

Alcance ampliado sobre el pedido original de B.6 (confirmado con el
usuario después de correr B.1-B.5 y encontrar gaps reales de datos):

1. Reservas + reserva_items distribuidos en 6 meses, en los 5 tipos de
   producto (hoy solo había hotel/vuelo), con algunas `es_paquete=True`.
   Para las confirmadas: pago + factura + (si tienen ítem de vuelo)
   comisión con `reserva_id` REAL — antes las 26 comisiones de la base
   tenían `reserva_id=""`.
2. Algunas de esas reservas de vuelo, con una disrupción + notificación
   con `disrupcion_id` REAL — antes las 4 notificaciones no tenían
   ningún vínculo real a una disrupción.
3. campañas de email, suscriptores de newsletter, cupones (+ usos),
   alertas de precio, favoritos — el pedido original de B.6.

Nota sobre 2 campos que el pedido original asumía y no existen en el
esquema real: `campanas_email` no tiene `tasa_apertura`/`tasa_clicks`
(solo `estado`/`fecha_envio`) — no se inventan acá, se documenta.

No reemplaza datos reales — solo agrega variedad donde hoy está vacío o
muy delgado. Idempotente por marca distintiva en cada bloque (no vuelve a
crear si ya corrió antes).

Ejecutar: python scripts/seed_demo_tactico.py
"""

import asyncio
import datetime
import random
import sys

sys.path.insert(0, ".")

from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.ofertas.repositories.ofertas_repo import OfertasRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import get_pocketbase_client
from app.vuelos.repositories.vuelos_repo import VuelosRepository

MARCA_RESERVA = "SDT-"  # prefijo de codigo_reserva — marca de este seed
random.seed(20260802)


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S.000Z")


def _fecha(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%d")


async def _catalogo_pocketbase(nombre: str, campos: list[str] | None = None) -> list[dict]:
    pb = get_pocketbase_client()
    pagina = 1
    salida = []
    while True:
        resultado = await pb.list_records(nombre, {"page": pagina, "perPage": 200})
        salida.extend(resultado["items"])
        if pagina >= resultado.get("totalPages", 1):
            break
        pagina += 1
    if campos:
        salida = [{c: r.get(c) for c in campos + ["id"]} for r in salida]
    return salida


async def seed_reservas_multiproducto() -> None:
    reservas_repo = ReservasRepository()
    fact_repo = FacturacionRepository()
    disrup_repo = DisrupcionesRepository()
    pasajeros_repo = PasajerosRepository()

    existentes = await reservas_repo.listar_todas()
    ya_sembradas = [r for r in existentes if (r.get("codigo_reserva") or "").startswith(MARCA_RESERVA)]
    if len(ya_sembradas) >= 40:
        print(f"= reservas multiproducto: ya hay {len(ya_sembradas)} sembradas, no se repite")
        return

    pasajeros = await pasajeros_repo.listar_todos_pasajeros()
    if not pasajeros:
        print("! sin pasajeros en la base — no se puede sembrar reservas")
        return

    vuelos = await _catalogo_pocketbase("vuelos_catalogo")
    tarifas_vuelo = await _catalogo_pocketbase("tarifas_vuelo")
    tarifas_por_vuelo: dict[str, list[dict]] = {}
    for t in tarifas_vuelo:
        tarifas_por_vuelo.setdefault(t["vuelo_id"], []).append(t)
    vuelos_con_tarifa = [v for v in vuelos if v["id"] in tarifas_por_vuelo]

    hoteles = await _catalogo_pocketbase("hoteles_catalogo", ["nombre"])
    hoteles_tarifas = await _catalogo_pocketbase("hoteles_tarifas")
    autos = await _catalogo_pocketbase("autos_catalogo", ["precio_dia"])
    actividades = await _catalogo_pocketbase("actividades_catalogo", ["precio_desde"])
    actividades_horarios = await _catalogo_pocketbase("actividades_horarios")
    horarios_por_actividad: dict[str, list[dict]] = {}
    for h in actividades_horarios:
        horarios_por_actividad.setdefault(h["actividad_id"], []).append(h)
    actividades_con_horario = [a for a in actividades if a["id"] in horarios_por_actividad]
    cruceros = await _catalogo_pocketbase("cruceros_catalogo")
    camarotes = await _catalogo_pocketbase("cruceros_camarotes_tarifa")
    camarotes_por_crucero: dict[str, list[dict]] = {}
    for c in camarotes:
        camarotes_por_crucero.setdefault(c["crucero_id"], []).append(c)
    cruceros_con_camarote = [c for c in cruceros if c["id"] in camarotes_por_crucero]

    aerolineas = {a["id"]: a for a in await VuelosRepository().listar_aerolineas_activas()}

    def _item_vuelo() -> tuple[dict, float, str | None]:
        vuelo = random.choice(vuelos_con_tarifa)
        tarifa = random.choice(tarifas_por_vuelo[vuelo["id"]])
        precio = tarifa["precio_final"]
        return (
            {"tipo_producto": "vuelo", "vuelo_id": vuelo["id"], "tarifa_vuelo_id": tarifa["id"],
             "precio_final": precio, "cantidad": 1, "estado_item": "pendiente"},
            precio, vuelo["aerolinea_id"],
        )

    def _item_hotel() -> tuple[dict, float, None]:
        hotel = random.choice(hoteles)
        tarifas_hotel = [t for t in hoteles_tarifas if t["hotel_id"] == hotel["id"]] or hoteles_tarifas
        tarifa = random.choice(tarifas_hotel)
        noches = random.randint(1, 4)
        precio = tarifa["precio_final"] * noches
        inicio = datetime.date(2026, random.randint(3, 8), random.randint(1, 25))
        fin = inicio + datetime.timedelta(days=noches)
        return (
            {"tipo_producto": "hotel", "hotel_id": hotel["id"], "hotel_tarifa_id": tarifa["id"],
             "precio_final": tarifa["precio_final"], "cantidad": noches, "estado_item": "pendiente",
             "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()},
            precio, None,
        )

    def _item_auto() -> tuple[dict, float, None]:
        auto = random.choice(autos)
        dias = random.randint(1, 5)
        precio = auto["precio_dia"] * dias
        inicio = datetime.date(2026, random.randint(3, 8), random.randint(1, 25))
        fin = inicio + datetime.timedelta(days=dias)
        return (
            {"tipo_producto": "auto", "auto_id": auto["id"], "precio_final": auto["precio_dia"],
             "cantidad": dias, "estado_item": "pendiente",
             "fecha_inicio": inicio.isoformat(), "fecha_fin": fin.isoformat()},
            precio, None,
        )

    def _item_actividad() -> tuple[dict, float, None]:
        actividad = random.choice(actividades_con_horario)
        horario = random.choice(horarios_por_actividad[actividad["id"]])
        personas = random.randint(1, 3)
        precio = horario["precio"] * personas
        return (
            {"tipo_producto": "actividad", "actividad_id": actividad["id"], "actividad_horario_id": horario["id"],
             "precio_final": horario["precio"], "cantidad": personas, "estado_item": "pendiente"},
            precio, None,
        )

    def _item_crucero() -> tuple[dict, float, None]:
        crucero = random.choice(cruceros_con_camarote)
        camarote = random.choice(camarotes_por_crucero[crucero["id"]])
        personas = random.randint(1, 2)
        precio = camarote["precio_por_persona"] * personas
        return (
            {"tipo_producto": "crucero", "crucero_id": crucero["id"], "crucero_camarote_id": camarote["id"],
             "precio_final": camarote["precio_por_persona"], "cantidad": personas, "estado_item": "pendiente"},
            precio, None,
        )

    generadores = [_item_vuelo, _item_hotel, _item_auto, _item_actividad, _item_crucero]
    ahora = datetime.datetime.now(datetime.UTC)
    estados_posibles = ["confirmada", "confirmada", "confirmada", "cancelada", "pendiente_pago"]

    creadas = 0
    for _ in range(50):
        pasajero = random.choice(pasajeros)
        mes_atras = random.randint(0, 5)
        fecha_reserva = (ahora - datetime.timedelta(days=mes_atras * 30 + random.randint(0, 27)))

        es_paquete = random.random() < 0.25
        n_items = random.choice([2, 3]) if es_paquete else 1
        tipos_elegidos = random.sample(generadores, k=min(n_items, len(generadores)))

        items_data = []
        total = 0.0
        aerolinea_id_vuelo = None
        for gen in tipos_elegidos:
            item, precio, aerolinea_id = gen()
            items_data.append(item)
            total += precio
            if aerolinea_id:
                aerolinea_id_vuelo = aerolinea_id

        estado = random.choice(estados_posibles)
        codigo = f"{MARCA_RESERVA}{''.join(random.choices('ABCDEFGHJKLMNPQRSTUVWXYZ23456789', k=8))}"

        reserva = await reservas_repo.crear_reserva({
            "codigo_reserva": codigo,
            "pasajero_titular_id": pasajero["id"],
            "canal": random.choice(["autoservicio", "asistida"]),
            "estado": estado,
            "es_paquete": len(tipos_elegidos) >= 2,
            "total_pagar": round(total, 2),
            "fecha_reserva": _iso(fecha_reserva),
            "fecha_expiracion_pago": _iso(fecha_reserva + datetime.timedelta(minutes=15)),
        })
        for item in items_data:
            await reservas_repo.crear_item({**item, "reserva_id": reserva["id"]})
        creadas += 1

        if estado != "confirmada":
            continue

        # pago (checkout) + factura
        pago = await fact_repo.crear_pago({
            "reserva_id": reserva["id"], "monto": round(total, 2), "moneda": "USD",
            "metodo_pago_id": "", "stripe_payment_intent_id": f"pi_demo_{codigo.lower()}",
            "estado": "exitoso", "fecha_pago": _iso(fecha_reserva),
        })
        await fact_repo.crear_factura({
            "reserva_id": reserva["id"], "pago_id": pago["id"],
            "numero_factura": f"FAC-DEMO-{codigo}", "total": round(total, 2),
            "fecha_emision": _iso(fecha_reserva),
        })

        # comisión con reserva_id REAL, solo si hubo ítem de vuelo
        if aerolinea_id_vuelo:
            aerolinea = aerolineas.get(aerolinea_id_vuelo)
            pct = aerolinea["comision_pactada_pct"] if aerolinea else 6.0
            monto_vuelo = next((i["precio_final"] for i in items_data if i["tipo_producto"] == "vuelo"), total)
            await fact_repo.crear_comision({
                "reserva_id": reserva["id"], "aerolinea_id": aerolinea_id_vuelo,
                "monto": round(monto_vuelo * pct / 100, 2), "estado": random.choice(["pendiente_cobro", "cobrada"]),
            })

            # 30% de las reservas de vuelo: disrupción + notificación con vínculo real
            if random.random() < 0.3:
                vuelo_id = next((i["vuelo_id"] for i in items_data if i["tipo_producto"] == "vuelo"), None)
                if vuelo_id:
                    disrupcion = await disrup_repo.crear_disrupcion({
                        "vuelo_id": vuelo_id, "tipo_cambio": random.choice(["retraso", "cambio_puerta"]),
                        "estado": "resuelta", "fuente_deteccion": "simulador_estadistico",
                        "probabilidad": round(random.uniform(20, 40), 2),
                        "fecha_deteccion": _iso(fecha_reserva - datetime.timedelta(hours=2)),
                        "detalle": "Generado por seed_demo_tactico.py",
                    })
                    await disrup_repo.crear_notificacion({
                        "disrupcion_id": disrupcion["id"], "pasajero_id": pasajero["id"], "reserva_id": reserva["id"],
                        "canal": random.choice(["email", "sms"]), "asunto": "Actualización de tu vuelo",
                        "contenido": "Notificación generada por seed_demo_tactico.py",
                        "estado_envio": random.choices(["enviado", "fallido"], weights=[85, 15])[0],
                    })

    print(f"+ reservas multiproducto: {creadas} creadas (con pago/factura/comisión/notificación donde aplica)")


async def seed_campanas_email() -> None:
    repo = OfertasRepository()
    existentes = await repo.listar_campanas()
    ya_sembradas = [c for c in existentes if (c.get("nombre") or "").startswith("[DEMO]")]
    if len(ya_sembradas) >= 8:
        print(f"= campañas de email: ya hay {len(ya_sembradas)} sembradas, no se repite")
        return

    admin = await get_pocketbase_client().get_first("usuarios", 'rol_id!=""')
    ahora = datetime.datetime.now(datetime.UTC)
    creadas = 0
    for i in range(8):
        dias_atras = random.randint(0, 60)
        campana = await repo.crear_campana({
            "nombre": f"[DEMO] Campaña {i + 1}",
            "segmento_criterio": {"segmento": "todos_los_suscriptores"},
            "plantilla": f"Contenido de campaña demo {i + 1}, generado por seed_demo_tactico.py",
            "estado": "enviada",
            "creado_por": admin["id"] if admin else "",
            "fecha_envio": _iso(ahora - datetime.timedelta(days=dias_atras)),
        })
        creadas += 1
    print(f"+ campañas de email: {creadas} creadas (nota: 'tasa_apertura'/'tasa_clicks' no existen en el esquema real, no se sembraron)")


async def seed_newsletter() -> None:
    repo = OfertasRepository()
    existentes = await repo.listar_todos_suscriptores()
    ya_sembrados = [s for s in existentes if (s.get("email") or "").endswith("@seed-demo-tactico.test")]
    if len(ya_sembrados) >= 150:
        print(f"= newsletter: ya hay {len(ya_sembrados)} suscriptores sembrados, no se repite")
        return

    ahora = datetime.datetime.now(datetime.UTC)
    creados = 0
    for i in range(150):
        dias_atras = random.randint(0, 60)
        activo = random.random() > 0.15
        await repo.crear_suscripcion({
            "email": f"suscriptor{i}@seed-demo-tactico.test",
            "fecha_suscripcion": _iso(ahora - datetime.timedelta(days=dias_atras)),
            "activo": activo,
        })
        creados += 1
    print(f"+ newsletter: {creados} suscriptores creados (~15% inactivos)")


async def seed_cupones() -> None:
    repo = OfertasRepository()
    existentes = await repo.listar_cupones()
    ya_sembrados = [c for c in existentes if (c.get("codigo") or "").startswith("DEMO")]
    if len(ya_sembrados) >= 20:
        print(f"= cupones: ya hay {len(ya_sembrados)} sembrados, no se repite")
        return

    reservas_repo = ReservasRepository()
    reservas = await reservas_repo.listar_todas()
    ahora = datetime.datetime.now(datetime.UTC)
    creados = 0
    canjeados = 0
    for i in range(20):
        tipo = random.choice(["porcentaje", "monto_fijo"])
        valor = random.choice([10, 15, 20, 25]) if tipo == "porcentaje" else random.choice([15, 25, 50])
        cupon = await repo.crear_cupon({
            "codigo": f"DEMO{i:03d}", "tipo": tipo, "valor": valor,
            "usos_maximos": 50, "usos_actuales": 0, "activo": True,
            "acumulable_con_paquete": random.random() > 0.5,
            "producto_aplicable": "", "fecha_expiracion": _iso(ahora + datetime.timedelta(days=180)),
        })
        creados += 1
        if random.random() < 0.6 and reservas:
            reserva = random.choice(reservas)
            monto_descuento = round(reserva.get("total_pagar", 100) * (valor / 100 if tipo == "porcentaje" else 1), 2)
            monto_descuento = min(monto_descuento, valor if tipo == "monto_fijo" else monto_descuento)
            await repo.registrar_uso(cupon["id"], reserva["id"], monto_descuento, _iso(ahora))
            canjeados += 1
    print(f"+ cupones: {creados} creados, {canjeados} con uso registrado (~60%)")


async def seed_alertas_precio() -> None:
    reservas_repo = ReservasRepository()
    alertas_existentes = await reservas_repo.listar_todas_alertas()
    ya_sembradas = [a for a in alertas_existentes if (a.get("id") or "").startswith("sdtalert")]
    if len(ya_sembradas) >= 40:
        print(f"= alertas de precio: ya hay {len(ya_sembradas)} sembradas, no se repite")
        return

    pasajeros = await PasajerosRepository().listar_todos_pasajeros()
    vuelos = await _catalogo_pocketbase("vuelos_catalogo", ["origen_codigo", "destino_codigo"])
    if not pasajeros or not vuelos:
        print("! sin pasajeros o vuelos — no se puede sembrar alertas de precio")
        return

    ahora = datetime.datetime.now(datetime.UTC)
    creadas = 0
    for _ in range(40):
        pasajero = random.choice(pasajeros)
        vuelo = random.choice(vuelos)
        dias_atras = random.randint(0, 45)
        id_ = "sdtalert" + "".join(random.choices("0123456789abcdef", k=12))
        registro = {
            "id": id_, "created": _iso(ahora - datetime.timedelta(days=dias_atras)),
            "updated": _iso(ahora - datetime.timedelta(days=dias_atras)),
            "pasajero_id": pasajero["id"], "origen_codigo": vuelo["origen_codigo"],
            "destino_codigo": vuelo["destino_codigo"],
            "precio_umbral": round(random.uniform(120, 450), 2),
            "fecha_objetivo": _fecha(ahora + datetime.timedelta(days=random.randint(20, 90))),
            "activa": random.random() > 0.3,
        }
        await moc.crear("alertas_precio", id_, registro)
        creadas += 1
    print(f"+ alertas de precio: {creadas} creadas sobre rutas reales del catálogo")


async def seed_favoritos() -> None:
    repo = CuentaRepository()
    existentes = await repo.listar_todos_favoritos()
    ya_sembrados = [f for f in existentes if (f.get("producto_ref") or "").startswith("demo-")]
    if len(ya_sembrados) >= 80:
        print(f"= favoritos: ya hay {len(ya_sembrados)} sembrados, no se repite")
        return

    pasajeros = await PasajerosRepository().listar_todos_pasajeros()
    if not pasajeros:
        print("! sin pasajeros — no se puede sembrar favoritos")
        return

    ahora = datetime.datetime.now(datetime.UTC)
    tipos = ["vuelo", "hotel", "actividad", "auto", "crucero"]
    creados = 0
    for i in range(80):
        pasajero = random.choice(pasajeros)
        tipo = random.choice(tipos)
        dias_atras = random.randint(0, 90)
        await repo.crear_favorito(
            pasajero["id"], tipo, f"demo-{tipo}-{i % 15}", _iso(ahora - datetime.timedelta(days=dias_atras))
        )
        creados += 1
    print(f"+ favoritos: {creados} creados")


async def main() -> None:
    print("=== seed_demo_tactico.py — sesión 2026-08-02 ===")
    await seed_reservas_multiproducto()
    await seed_campanas_email()
    await seed_newsletter()
    await seed_cupones()
    await seed_alertas_precio()
    await seed_favoritos()
    print("=== listo ===")


if __name__ == "__main__":
    asyncio.run(main())
