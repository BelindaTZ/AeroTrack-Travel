"""CU-T09 (RF-HOT-T01) — comparar hasta 5 propiedades de hotel lado a lado.

`<<extend>>` de CU-O54/O55 — reutiliza `hoteles_catalogo`/`hoteles_tarifas`
ya cargados, nunca vuelve a consultar HotelLens (RNF-HOT-T01)."""

from app.hoteles.repositories.catalogo_reader import CatalogoHotelesReader

MAXIMO_HOTELES = 5


class DemasiadosHoteles(Exception):
    def __init__(self, cantidad: int):
        self.cantidad = cantidad
        super().__init__(
            f"Solo se pueden comparar hasta {MAXIMO_HOTELES} hoteles a la vez (intentaste {cantidad})."
        )


async def comparar_hoteles(ids: list[str]) -> list[dict]:
    # Dedupe preservando orden — un mismo id repetido en la URL no debe
    # contar dos veces contra el máximo de 5 (RN-HOT-T01).
    ids_unicos = list(dict.fromkeys(i for i in ids if i))
    if len(ids_unicos) > MAXIMO_HOTELES:
        raise DemasiadosHoteles(len(ids_unicos))

    catalogo = CatalogoHotelesReader()
    filas = []
    for hotel_id in ids_unicos:
        hotel = await catalogo.obtener_hotel(hotel_id)
        if hotel is None:
            continue  # oferta ya reemplazada por una corrida más nueva del catálogo — se omite, no rompe

        tarifas = await catalogo.tarifas_de_hotel(hotel_id)
        tarifa_economica = min(tarifas, key=lambda t: t["precio_final"]) if tarifas else None

        filas.append(
            {
                "id": hotel["id"],
                "nombre": hotel["nombre"],
                "imagen_principal": hotel.get("imagen_principal"),
                "estrellas": hotel.get("estrellas"),
                "calificacion_promedio": hotel.get("calificacion_promedio"),
                "cantidad_resenas": hotel.get("cantidad_resenas"),
                "category_scores": hotel.get("category_scores") or {},
                "servicios": hotel.get("servicios") or [],
                "precio_desde": tarifa_economica["precio_final"] if tarifa_economica else None,
                "reembolsable": tarifa_economica["reembolsable"] if tarifa_economica else None,
                "cancelacion_hasta": tarifa_economica.get("cancelacion_hasta") if tarifa_economica else None,
            }
        )
    return filas
