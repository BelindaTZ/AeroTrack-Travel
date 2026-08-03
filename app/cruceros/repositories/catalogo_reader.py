"""Lector del catálogo de cruceros desde MinIO (`aerotrack-travel-catalog`)
— reemplaza, solo para búsqueda/detalle, las lecturas que antes iban
directo a PocketBase (`navieras`, `barcos`, `cruceros_catalogo`,
`cruceros_camarotes_tarifa` — todas STAGING según el plan de migración).

El resto del módulo (backoffice, generación desde Cruise Pricing API) sigue
usando `CrucerosRepository` contra PocketBase sin cambios.
"""

from app.shared.minio_catalog_reader import leer_coleccion


class CatalogoCrucerosReader:
    async def obtener_naviera(self, naviera_id: str) -> dict | None:
        navieras = await leer_coleccion("navieras")
        return next((n for n in navieras if n["id"] == naviera_id), None)

    async def obtener_barco(self, barco_id: str) -> dict | None:
        barcos = await leer_coleccion("barcos")
        return next((b for b in barcos if b["id"] == barco_id), None)

    async def obtener_crucero(self, crucero_id: str) -> dict | None:
        cruceros = await leer_coleccion("cruceros_catalogo")
        return next((c for c in cruceros if c["id"] == crucero_id), None)

    async def listar_cruceros(self) -> list[dict]:
        return await leer_coleccion("cruceros_catalogo")

    async def puertos_disponibles(self) -> list[str]:
        cruceros = await self.listar_cruceros()
        puertos: set[str] = set()
        for crucero in cruceros:
            for parada in crucero.get("itinerario_puertos") or []:
                nombre = parada.get("port") if isinstance(parada, dict) else parada
                if nombre:
                    puertos.add(str(nombre))
        return sorted(puertos)

    async def cruceros_de_barco(self, barco_id: str) -> list[dict]:
        cruceros = await leer_coleccion("cruceros_catalogo")
        resultado = [c for c in cruceros if c["barco_id"] == barco_id]
        resultado.sort(key=lambda c: c.get("fecha_zarpe") or "")
        return resultado

    async def camarotes_de_crucero(self, crucero_id: str) -> list[dict]:
        camarotes = await leer_coleccion("cruceros_camarotes_tarifa")
        resultado = [c for c in camarotes if c["crucero_id"] == crucero_id]
        resultado.sort(key=lambda c: c.get("precio_por_persona") or 0)
        return resultado
