"""Describe legiblemente un ítem polimórfico (`carrito_items` o
`reserva_items`) para el pasajero — un solo lugar que sabe resolver cada
`tipo_producto` contra su módulo dueño. Compartido por Carrito
(`router_vista.py`, ver carrito) y Reservas (`router_reservas.py`,
detalle de reserva / "Mis reservas") para no duplicar la misma
resolución dos veces."""

from datetime import date, timedelta

from app.actividades.repositories.actividades_repo import ActividadesRepository
from app.autos.repositories.autos_repo import AutosRepository
from app.cruceros.repositories.cruceros_repo import CrucerosRepository
from app.hoteles.repositories.hoteles_repo import HotelesRepository
from app.vuelos.repositories.vuelos_repo import VuelosRepository


async def describir_item(item: dict) -> dict:
    """`{"titulo": str, "href": str | None}` — genérico para cualquier
    tipo de producto; cae a un genérico "Ítem de {tipo}" si el producto
    ya no existe o el tipo no tiene resolución propia (ninguno de los 5
    tipos válidos debería llegar a ese fallback en la práctica)."""
    tipo = item["tipo_producto"]
    if tipo == "vuelo" and item.get("vuelo_id"):
        vuelo = await VuelosRepository().obtener_vuelo(item["vuelo_id"])
        if vuelo:
            return {"titulo": f"Vuelo {vuelo['numero_vuelo']}", "href": f"/vuelos/{item['vuelo_id']}"}
    if tipo == "auto" and item.get("auto_id"):
        auto = await AutosRepository().obtener_auto(item["auto_id"])
        if auto:
            return {"titulo": f"{auto.get('modelo') or 'Auto de renta'} — {auto['ciudad_recogida']}", "href": f"/autos/{item['auto_id']}"}
    if tipo == "actividad" and item.get("actividad_id"):
        actividad = await ActividadesRepository().obtener_actividad(item["actividad_id"])
        if actividad:
            return {"titulo": actividad["nombre"], "href": f"/actividades/{item['actividad_id']}"}
    if tipo == "hotel" and item.get("hotel_id"):
        hotel = await HotelesRepository().obtener_hotel(item["hotel_id"])
        if hotel:
            return {"titulo": hotel["nombre"], "href": f"/hoteles/{item['hotel_id']}"}
    if tipo == "crucero" and item.get("crucero_id"):
        crucero = await CrucerosRepository().obtener_crucero(item["crucero_id"])
        if crucero:
            barco = await CrucerosRepository().obtener_barco(crucero["barco_id"])
            titulo = barco["nombre"] if barco else "Crucero"
            return {"titulo": titulo, "href": f"/cruceros/{item['crucero_id']}"}
    return {"titulo": f"Ítem de {tipo}", "href": None}


async def fecha_referencia_item(item: dict) -> tuple[str, str] | None:
    """`(fecha_inicio, fecha_fin)` ISO reales del ítem, para clasificar una
    reserva en próxima/activa/pasada (Cuenta/Mis Viajes) — `None` si el tipo
    de producto no tiene una fecha propia que resolver.

    **Gap real, no un olvido:** Hoteles y Autos no tienen fecha aquí porque
    Carrito nunca captura check-in/check-out ni recogida/devolución al
    agregar el ítem (`reserva_items.fecha_inicio`/`fecha_fin` existen en el
    esquema pero ningún flujo de compra los escribe todavía) — ver
    `errores-conocidos.md`. No se inventa una fecha para no fabricar dato."""
    tipo = item["tipo_producto"]
    if tipo == "vuelo" and item.get("vuelo_id"):
        vuelo = await VuelosRepository().obtener_vuelo(item["vuelo_id"])
        if vuelo:
            return (vuelo["fecha_salida"][:10], vuelo["fecha_salida"][:10])
    if tipo == "actividad" and item.get("actividad_horario_id"):
        horario = await ActividadesRepository().obtener_horario(item["actividad_horario_id"])
        if horario:
            return (horario["fecha"][:10], horario["fecha"][:10])
    if tipo == "crucero" and item.get("crucero_id"):
        crucero = await CrucerosRepository().obtener_crucero(item["crucero_id"])
        if crucero:
            inicio = crucero["fecha_zarpe"][:10]
            duracion = crucero.get("duracion_dias") or 0
            fin = (date.fromisoformat(inicio) + timedelta(days=duracion)).isoformat()
            return (inicio, fin)
    return None
