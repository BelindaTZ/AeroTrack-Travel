"""Consultas de Vuelos sobre `vuelos_catalogo`, `tarifas_vuelo`,
`niveles_tarifa`, `aerolineas`, `politicas_reembolso` en PocketBase."""

from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client


class VuelosRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    async def buscar(
        self, origen: str, destino: str, fecha: str, aerolinea_id: str | None = None
    ) -> list[dict]:
        condiciones = [
            f'origen_codigo="{origen}"',
            f'destino_codigo="{destino}"',
            # PocketBase almacena `date` con hora ("2027-06-15 00:00:00.000Z");
            # "~" hace match por substring, "=" contra la fecha pelada nunca calza.
            f'fecha_salida ~ "{fecha}"',
            'estado="programado"',
        ]
        if aerolinea_id:
            condiciones.append(f'aerolinea_id="{aerolinea_id}"')
        resultado = await self._client.list_records(
            "vuelos_catalogo",
            {"filter": " && ".join(condiciones), "perPage": 100, "sort": "hora_salida_programada"},
        )
        return resultado["items"]

    async def obtener_vuelo(self, vuelo_id: str) -> dict | None:
        try:
            return await self._client.get_record("vuelos_catalogo", vuelo_id)
        except PocketBaseError:
            return None

    async def obtener_por_numero_vuelo(self, numero_vuelo: str) -> dict | None:
        safe = numero_vuelo.replace('"', '\\"')
        return await self._client.get_first("vuelos_catalogo", f'numero_vuelo="{safe}"')

    async def obtener_aerolinea(self, aerolinea_id: str) -> dict:
        return await self._client.get_record("aerolineas", aerolinea_id)

    async def listar_aerolineas_activas(self) -> list[dict]:
        resultado = await self._client.list_records(
            "aerolineas", {"filter": "activa=true", "perPage": 200, "sort": "nombre"}
        )
        return resultado["items"]

    async def obtener_tarifa(self, tarifa_id: str) -> dict | None:
        try:
            return await self._client.get_record("tarifas_vuelo", tarifa_id)
        except PocketBaseError:
            return None

    async def tarifas_de_vuelo(self, vuelo_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "tarifas_vuelo", {"filter": f'vuelo_id="{vuelo_id}"', "perPage": 10}
        )
        return resultado["items"]

    async def nivel_tarifa(self, nivel_id: str) -> dict:
        return await self._client.get_record("niveles_tarifa", nivel_id)

    async def politica_reembolso(self, politica_id: str) -> dict:
        return await self._client.get_record("politicas_reembolso", politica_id)

    async def listar_para_selector(self) -> list[dict]:
        """Vuelos + nombre de aerolínea, para el combobox de CU-O48."""
        resultado = await self._client.list_records(
            "vuelos_catalogo", {"perPage": 200, "sort": "-fecha_salida"}
        )
        aerolineas = {a["id"]: a["nombre"] for a in await self.listar_aerolineas_activas()}
        vuelos = []
        for v in resultado["items"]:
            aerolinea_nombre = aerolineas.get(v["aerolinea_id"], "")
            texto = (
                f"{v['numero_vuelo']} ({aerolinea_nombre}) {v['origen_codigo']}→{v['destino_codigo']} "
                f"{v['fecha_salida'][:10]} {v['hora_salida_programada']} · {v['estado']}"
            )
            vuelos.append({"id": v["id"], "texto": texto})
        return vuelos

    async def destinos_populares(self, limite: int = 6) -> list[dict]:
        """Destinos con más vuelos programados en el catálogo real — proxy
        honesto de "popularidad" ya que el sistema no registra conteos de
        búsqueda/reserva por destino. Alimenta la sección "Destinos
        populares" de Inicio con datos reales, no una lista fija."""
        resultado = await self._client.list_records(
            "vuelos_catalogo", {"filter": 'estado="programado"', "perPage": 200}
        )
        conteo: dict[str, int] = {}
        for v in resultado["items"]:
            conteo[v["destino_codigo"]] = conteo.get(v["destino_codigo"], 0) + 1

        top = sorted(conteo.items(), key=lambda kv: kv[1], reverse=True)[:limite]
        return [{"codigo": codigo, "vuelos_disponibles": cantidad} for codigo, cantidad in top]

    async def codigos_aeropuertos_disponibles(self) -> list[str]:
        """Códigos de aeropuerto realmente presentes en el catálogo hoy —
        alimenta el datalist de búsqueda en vez de una lista fija hardcodeada."""
        resultado = await self._client.list_records("vuelos_catalogo", {"perPage": 200})
        codigos: set[str] = set()
        for v in resultado["items"]:
            codigos.add(v["origen_codigo"])
            codigos.add(v["destino_codigo"])
        return sorted(codigos)
