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

    async def listar_activos(
        self,
        limite: int = 200,
        aerolinea_id: str | None = None,
        ruta: str | None = None,
    ) -> list[dict]:
        """CU-T19 — vuelos "en monitoreo": aún no completados/cancelados,
        ordenados por salida más próxima primero. IS-11 (auditoría de
        informes simples, sesión 2026-08-01) — se agregaron `aerolinea_id` y
        `ruta` (origen o destino, código IATA) sobre el filtro fijo que ya
        existía; `limite` subió de 100 a 200 porque ahora se pagina 25/página
        en vez de volcar todo de una vez."""
        condiciones = ['(estado="programado" || estado="retrasado" || estado="desviado")']
        if aerolinea_id:
            condiciones.append(f'aerolinea_id="{aerolinea_id}"')
        if ruta:
            safe = ruta.replace('"', '\\"').upper()
            condiciones.append(f'(origen_codigo="{safe}" || destino_codigo="{safe}")')
        resultado = await self._client.list_records(
            "vuelos_catalogo",
            {
                "filter": " && ".join(condiciones),
                "perPage": limite,
                "sort": "fecha_salida,hora_salida_programada",
            },
        )
        todas_aerolineas = await self._client.list_records("aerolineas", {"perPage": 200})
        aerolineas = {a["id"]: a for a in todas_aerolineas["items"]}
        vuelos = resultado["items"]
        for v in vuelos:
            aerolinea = aerolineas.get(v["aerolinea_id"])
            v["aerolinea_nombre"] = aerolinea["nombre"] if aerolinea else "—"
            v["aerolinea_iata"] = aerolinea["codigo_iata"] if aerolinea else None
        return vuelos

    async def listar_aerolineas_activas(self) -> list[dict]:
        resultado = await self._client.list_records(
            "aerolineas", {"filter": "activa=true", "perPage": 200, "sort": "nombre"}
        )
        return resultado["items"]

    async def listar_aerolineas(self, nombre: str | None = None, estado: str | None = None) -> list[dict]:
        """WP-16 (auditoría de WorkPanels, 2026-08-01) — antes no había
        ningún camino de código para dar de alta una aerolínea nueva; el
        catálogo se poblaba fuera del repo versionado."""
        condiciones = []
        if nombre:
            safe = nombre.replace('"', '\\"')
            condiciones.append(f'nombre~"{safe}"')
        if estado == "activo":
            condiciones.append("activa=true")
        elif estado == "inactivo":
            condiciones.append("activa=false")
        params: dict = {"sort": "nombre", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("aerolineas", params)
        return resultado["items"]

    async def crear_aerolinea(self, data: dict) -> dict:
        return await self._client.create_record("aerolineas", data)

    async def actualizar_aerolinea(self, aerolinea_id: str, data: dict) -> dict:
        return await self._client.update_record("aerolineas", aerolinea_id, data)

    async def listar_vuelos_filtrado(
        self,
        aerolinea_id: str | None = None,
        origen: str | None = None,
        destino: str | None = None,
        fecha: str | None = None,
        estado: str | None = None,
    ) -> list[dict]:
        """WP-16 — catálogo general de vuelos; `listar_activos` sigue
        siendo el dashboard de monitoreo (CU-T19), este es el listado con
        filtros combinables que faltaba."""
        condiciones = []
        if aerolinea_id:
            condiciones.append(f'aerolinea_id="{aerolinea_id}"')
        if origen:
            condiciones.append(f'origen_codigo="{origen.upper()}"')
        if destino:
            condiciones.append(f'destino_codigo="{destino.upper()}"')
        if fecha:
            condiciones.append(f'fecha_salida ~ "{fecha}"')
        if estado:
            condiciones.append(f'estado="{estado}"')
        params: dict = {"sort": "-fecha_salida,hora_salida_programada", "perPage": 500}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("vuelos_catalogo", params)
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

    async def listar_niveles_tarifa(self) -> list[dict]:
        resultado = await self._client.list_records("niveles_tarifa", {"perPage": 50, "sort": "nombre"})
        return resultado["items"]

    async def obtener_nivel_tarifa(self, nivel_id: str) -> dict | None:
        try:
            return await self._client.get_record("niveles_tarifa", nivel_id)
        except PocketBaseError:
            return None

    async def crear_nivel_tarifa(self, data: dict) -> dict:
        return await self._client.create_record("niveles_tarifa", data)

    async def actualizar_nivel_tarifa(self, nivel_id: str, data: dict) -> dict:
        return await self._client.update_record("niveles_tarifa", nivel_id, data)

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

    # ── enriquecimiento real (AeroDataBox / Google Flights) ─────────────
    async def rutas_disponibles(self) -> list[tuple[str, str]]:
        """Pares (origen, destino) únicos realmente presentes en el
        catálogo hoy — para rotar el enriquecimiento real sin inventar
        rutas fuera de las ya generadas por catalogo_vuelos_tasks."""
        resultado = await self._client.list_records(
            "vuelos_catalogo",
            {"filter": 'estado="programado"', "perPage": 200, "fields": "origen_codigo,destino_codigo"},
        )
        pares = {(v["origen_codigo"], v["destino_codigo"]) for v in resultado["items"]}
        return sorted(pares)

    async def actualizar_vuelo(self, vuelo_id: str, data: dict) -> dict:
        return await self._client.update_record("vuelos_catalogo", vuelo_id, data)

    async def actualizar_tarifa(self, tarifa_id: str, data: dict) -> dict:
        return await self._client.update_record("tarifas_vuelo", tarifa_id, data)

    async def tarifa_por_vuelo_y_clase(self, vuelo_id: str, clase_cabina: str) -> dict | None:
        return await self._client.get_first(
            "tarifas_vuelo", f'vuelo_id="{vuelo_id}" && clase_cabina="{clase_cabina}"'
        )

    async def crear_tarifa(self, data: dict) -> dict:
        return await self._client.create_record("tarifas_vuelo", data)

    async def nivel_tarifa_por_nombre(self, nombre: str) -> dict | None:
        safe = nombre.replace('"', '\\"')
        return await self._client.get_first("niveles_tarifa", f'nombre="{safe}"')

    async def prediccion_por_ruta_fecha(self, origen: str, destino: str, fecha: str) -> dict | None:
        # PocketBase almacena `date` con hora ("2027-01-01 00:00:00.000Z");
        # "~" hace match por substring, "=" contra la fecha pelada nunca
        # calza (mismo gotcha ya documentado en VuelosRepository.buscar()).
        return await self._client.get_first(
            "predicciones_precio_ruta",
            f'origen_codigo="{origen}" && destino_codigo="{destino}" && fecha_objetivo ~ "{fecha}"',
        )

    async def crear_prediccion(self, data: dict) -> dict:
        return await self._client.create_record("predicciones_precio_ruta", data)

    async def actualizar_prediccion(self, prediccion_id: str, data: dict) -> dict:
        return await self._client.update_record("predicciones_precio_ruta", prediccion_id, data)

    # ── asientos_vuelo (CU-O115/116/117) ─────────────────────────────────
    async def asientos_de_vuelo(self, vuelo_id: str) -> list[dict]:
        resultado = await self._client.list_records(
            "asientos_vuelo",
            {"filter": f'vuelo_id="{vuelo_id}"', "perPage": 500, "sort": "fila,columna"},
        )
        return resultado["items"]

    async def crear_asiento(self, data: dict) -> dict:
        return await self._client.create_record("asientos_vuelo", data)

    async def obtener_asiento(self, asiento_id: str) -> dict | None:
        try:
            return await self._client.get_record("asientos_vuelo", asiento_id)
        except PocketBaseError:
            return None

    async def actualizar_asiento(self, asiento_id: str, data: dict) -> dict:
        return await self._client.update_record("asientos_vuelo", asiento_id, data)

    # ── configuración / auditoría (Integraciones) ────────────────────────
    async def config(self, clave: str) -> str | None:
        safe = clave.replace('"', '\\"')
        registro = await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
        return registro["valor"] if registro else None

    async def actualizar_config(self, clave: str, valor: str, usuario_id: str) -> dict | None:
        """CU-T39/T40/T41 — estas claves ya vienen sembradas (con default de
        código como fallback, RN-VUE-T03); esto siempre es un UPDATE, nunca
        crea una fila nueva. `None` si la clave no existe (no debería pasar
        en uso normal, ver `scripts/pb_schema_asientos_v31.py`)."""
        safe = clave.replace('"', '\\"')
        registro = await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
        if registro is None:
            return None
        return await self._client.update_record(
            "configuracion_sistema", registro["id"], {"valor": valor, "modificado_por": usuario_id}
        )

    async def fuente_por_nombre(self, nombre: str) -> dict | None:
        safe = nombre.replace('"', '\\"')
        return await self._client.get_first("fuentes_datos_externas", f'nombre="{safe}"')

    async def crear_log_sincronizacion(self, data: dict) -> dict:
        return await self._client.create_record("sincronizaciones_log", data)
