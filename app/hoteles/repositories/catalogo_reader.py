"""Lector del catálogo de hoteles desde MinIO (`aerotrack-travel-catalog`)
— reemplaza, solo para búsqueda/detalle/comparación, las lecturas que antes
iban directo a PocketBase (`hoteles_catalogo`, `hoteles_tarifas`,
`hoteles_resenas`, `cargos_locales_destino` — todas STAGING según el plan
de migración).

El resto del módulo (backoffice, generación desde HotelLens, importación
de cargos locales) sigue usando `HotelesRepository` contra PocketBase sin
cambios.
"""

from app.shared.minio_catalog_reader import leer_coleccion


class CatalogoHotelesReader:
    async def obtener_hotel(self, hotel_id: str) -> dict | None:
        hoteles = await leer_coleccion("hoteles_catalogo")
        return next((h for h in hoteles if h["id"] == hotel_id), None)

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        hoteles = await leer_coleccion("hoteles_catalogo")
        termino = ciudad.lower()
        return [h for h in hoteles if termino in (h.get("ciudad") or "").lower()]

    async def ciudades_disponibles(self) -> list[dict]:
        hoteles = await leer_coleccion("hoteles_catalogo")
        pares = {(h["ciudad"], h.get("pais") or "") for h in hoteles if h.get("ciudad")}
        return sorted(({"ciudad": c, "pais": p} for c, p in pares), key=lambda x: x["ciudad"])

    async def tarifas_de_hotel(self, hotel_id: str) -> list[dict]:
        tarifas = await leer_coleccion("hoteles_tarifas")
        return [t for t in tarifas if t["hotel_id"] == hotel_id]

    async def resenas_de_hotel(self, hotel_id: str) -> list[dict]:
        resenas = await leer_coleccion("hoteles_resenas")
        return [r for r in resenas if r["hotel_id"] == hotel_id]

    async def disponibilidad_de_tarifa(self, hotel_tarifa_id: str) -> list[dict]:
        filas = await leer_coleccion("hoteles_disponibilidad")
        return [f for f in filas if f["hotel_tarifa_id"] == hotel_tarifa_id]

    async def meses_disponibles(self) -> list[str]:
        """"YYYY-MM" con al menos una noche generada — para el selector de
        mes de la búsqueda flexible ("aún no definí la fecha"), mismo
        criterio que `VuelosRepository.meses_disponibles`: solo meses con
        disponibilidad real, nunca un rango de fechas inventado."""
        filas = await leer_coleccion("hoteles_disponibilidad")
        meses = {f["fecha"][:7] for f in filas}
        return sorted(meses)

    async def cargos_locales_de_ciudad(self, ciudad: str) -> list[dict]:
        cargos = await leer_coleccion("cargos_locales_destino")
        return [c for c in cargos if c.get("ciudad") == ciudad and c.get("activo")]

    async def hoteles_destacados(self, limite: int = 6) -> list[dict]:
        """Para el carrusel de la home — solo hoteles con foto real ya
        sincronizada (`imagen_principal`, HotelLens/Booking), ordenados por
        calificación. Sin llamada nueva a ninguna API externa: reusa el
        mismo catálogo que ya lee la búsqueda."""
        hoteles = await leer_coleccion("hoteles_catalogo")
        con_foto = [h for h in hoteles if h.get("imagen_principal")]
        con_foto.sort(key=lambda h: h.get("calificacion_promedio") or 0, reverse=True)
        return con_foto[:limite]
