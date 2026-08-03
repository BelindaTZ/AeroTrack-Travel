"""Lector del catálogo de autos desde MinIO (`aerotrack-travel-catalog`) —
reemplaza, solo para búsqueda/detalle, las lecturas que antes iban directo
a PocketBase (`autos_catalogo`, STAGING según el plan de migración).

El resto del módulo (backoffice, generación desde Global Rental Cars) sigue
usando `AutosRepository` contra PocketBase sin cambios.
"""

from app.shared.minio_catalog_reader import leer_coleccion


class CatalogoAutosReader:
    async def obtener_auto(self, auto_id: str) -> dict | None:
        autos = await leer_coleccion("autos_catalogo")
        return next((a for a in autos if a["id"] == auto_id), None)

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        autos = await leer_coleccion("autos_catalogo")
        termino = ciudad.lower()
        return [a for a in autos if termino in (a.get("ciudad_recogida") or "").lower()]

    async def ciudades_disponibles(self) -> list[str]:
        autos = await leer_coleccion("autos_catalogo")
        return sorted({a["ciudad_recogida"] for a in autos if a.get("ciudad_recogida")})

    async def disponibilidad_de_auto(self, auto_id: str) -> list[dict]:
        filas = await leer_coleccion("autos_disponibilidad")
        return [f for f in filas if f["auto_id"] == auto_id]
