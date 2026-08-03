"""Lector del catálogo de actividades desde MinIO
(`aerotrack-travel-catalog`) — reemplaza, solo para búsqueda/detalle, las
lecturas que antes iban directo a PocketBase (`actividades_catalogo`,
`actividades_resenas`, `actividades_horarios` — todas STAGING según el
plan de migración).

El resto del módulo (backoffice, generación desde Travel Advisor) sigue
usando `ActividadesRepository` contra PocketBase sin cambios.
"""

from app.shared.minio_catalog_reader import leer_coleccion


class CatalogoActividadesReader:
    async def obtener_actividad(self, actividad_id: str) -> dict | None:
        actividades = await leer_coleccion("actividades_catalogo")
        return next((a for a in actividades if a["id"] == actividad_id), None)

    async def buscar_por_ciudad(self, ciudad: str) -> list[dict]:
        actividades = await leer_coleccion("actividades_catalogo")
        termino = ciudad.lower()
        return [a for a in actividades if termino in (a.get("ciudad") or "").lower()]

    async def ciudades_disponibles(self) -> list[dict]:
        actividades = await leer_coleccion("actividades_catalogo")
        pares = {(a["ciudad"], a.get("pais") or "") for a in actividades if a.get("ciudad")}
        return sorted(({"ciudad": c, "pais": p} for c, p in pares), key=lambda x: x["ciudad"])

    async def resenas_de_actividad(self, actividad_id: str) -> list[dict]:
        resenas = await leer_coleccion("actividades_resenas")
        resultado = [r for r in resenas if r["actividad_id"] == actividad_id]
        resultado.sort(key=lambda r: r.get("fecha_resena") or "", reverse=True)
        return resultado

    async def horarios_de_actividad(self, actividad_id: str) -> list[dict]:
        horarios = await leer_coleccion("actividades_horarios")
        resultado = [h for h in horarios if h["actividad_id"] == actividad_id]
        resultado.sort(key=lambda h: h.get("fecha") or "")
        return resultado
