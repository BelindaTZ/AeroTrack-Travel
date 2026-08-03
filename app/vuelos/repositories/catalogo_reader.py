"""Lector del catálogo de vuelos desde MinIO (`aerotrack-travel-catalog`) —
reemplaza, solo para búsqueda/detalle, las lecturas que antes iban directo
a PocketBase (`vuelos_catalogo`, `tarifas_vuelo`, `aerolineas`,
`predicciones_precio_ruta` — todas STAGING según el plan de migración).

El resto del módulo (backoffice, generación, enriquecimiento AeroDataBox/
Google Flights, asignación de asientos) sigue usando `VuelosRepository`
contra PocketBase sin cambios — esas colecciones STAGING no dejan de
existir ahí, solo se agrega este snapshot de solo lectura para búsqueda.
"""

from app.shared.minio_catalog_reader import leer_coleccion


class CatalogoVuelosReader:
    async def buscar(
        self, origen: str, destino: str, fecha: str, aerolinea_id: str | None = None
    ) -> list[dict]:
        vuelos = await leer_coleccion("vuelos_catalogo")
        resultado = [
            v for v in vuelos
            if v["origen_codigo"] == origen
            and v["destino_codigo"] == destino
            and v["estado"] == "programado"
            and v["fecha_salida"].startswith(fecha)
            and (aerolinea_id is None or v["aerolinea_id"] == aerolinea_id)
        ]
        resultado.sort(key=lambda v: v["hora_salida_programada"])
        return resultado

    async def obtener_vuelo(self, vuelo_id: str) -> dict | None:
        vuelos = await leer_coleccion("vuelos_catalogo")
        return next((v for v in vuelos if v["id"] == vuelo_id), None)

    async def obtener_aerolinea(self, aerolinea_id: str) -> dict:
        aerolineas = await leer_coleccion("aerolineas")
        return next((a for a in aerolineas if a["id"] == aerolinea_id), {})

    async def listar_aerolineas_activas(self) -> list[dict]:
        aerolineas = await leer_coleccion("aerolineas")
        return sorted((a for a in aerolineas if a.get("activa")), key=lambda a: a["nombre"])

    async def tarifas_de_vuelo(self, vuelo_id: str) -> list[dict]:
        tarifas = await leer_coleccion("tarifas_vuelo")
        return [t for t in tarifas if t["vuelo_id"] == vuelo_id]

    async def prediccion_por_ruta_fecha(self, origen: str, destino: str, fecha: str) -> dict | None:
        predicciones = await leer_coleccion("predicciones_precio_ruta")
        return next(
            (
                p for p in predicciones
                if p["origen_codigo"] == origen
                and p["destino_codigo"] == destino
                and p["fecha_objetivo"].startswith(fecha)
            ),
            None,
        )

    async def codigos_aeropuertos_disponibles(self) -> list[str]:
        vuelos = await leer_coleccion("vuelos_catalogo")
        codigos: set[str] = set()
        for v in vuelos:
            codigos.add(v["origen_codigo"])
            codigos.add(v["destino_codigo"])
        return sorted(codigos)

    async def meses_disponibles(self) -> list[str]:
        """"YYYY-MM" con al menos un vuelo programado — para el selector de
        mes de la búsqueda flexible ("aún no definí la fecha"), mismo
        criterio que `codigos_aeropuertos_disponibles`: solo meses con
        vuelos reales, nunca un rango de fechas inventado."""
        vuelos = await leer_coleccion("vuelos_catalogo")
        meses = {v["fecha_salida"][:7] for v in vuelos if v["estado"] == "programado"}
        return sorted(meses)
