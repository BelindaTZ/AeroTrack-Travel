"""`pagos`, `facturas`, `comisiones`, `remesas`, `remesa_comisiones`,
`reembolsos` son OPERACIONAL — migrados a MinIO junto con `reservas`/
`reserva_items` (paso 5 del plan, todas se mueven en el mismo lote por las
relations cruzadas confirmadas en el barrido de la sesión). `metodos_pago`
es CONFIG y sigue en PocketBase."""

import datetime

from app.shared import minio_operational_client as moc
from app.shared.pocketbase_client import PocketBaseClient, PocketBaseError, get_pocketbase_client

ENTIDAD_PAGOS = "pagos"
ENTIDAD_FACTURAS = "facturas"
ENTIDAD_COMISIONES = "comisiones"
ENTIDAD_REMESAS = "remesas"
ENTIDAD_REMESA_COMISIONES = "remesa_comisiones"
ENTIDAD_REEMBOLSOS = "reembolsos"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d %H:%M:%S.000Z")


def _crear_registro(data: dict) -> tuple[str, dict]:
    id_ = moc.generar_id()
    return id_, {"id": id_, "created": _timestamp(), "updated": _timestamp(), **data}


class FacturacionRepository:
    def __init__(self, client: PocketBaseClient | None = None) -> None:
        self._client = client or get_pocketbase_client()

    # ── pagos ────────────────────────────────────────────────────────
    async def crear_pago(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_PAGOS, id_, registro)

    async def actualizar_pago(self, pago_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_PAGOS, pago_id, _mutar)

    async def pago_exitoso_de_reserva(self, reserva_id: str) -> dict | None:
        pagos = await moc.listar_todos(ENTIDAD_PAGOS)
        return next(
            (p for p in pagos if p.get("reserva_id") == reserva_id and p.get("estado") == "exitoso"), None
        )

    async def pago_activo_de_reserva(self, reserva_id: str) -> dict | None:
        """RF-FAC-012 — idempotencia también cubre un pago ya `autorizado`
        (esperando captura), no solo uno `exitoso` (RNF-FAC-002): sin esto,
        reintentar el pago de una reserva ya autorizada volvería a llamar a
        Stripe y crearía un segundo `PaymentIntent` retenido."""
        pagos = await moc.listar_todos(ENTIDAD_PAGOS)
        return next(
            (
                p for p in pagos
                if p.get("reserva_id") == reserva_id and p.get("estado") in ("exitoso", "autorizado")
            ),
            None,
        )

    async def pagos_por_estado(self, estado: str) -> list[dict]:
        pagos = await moc.listar_todos(ENTIDAD_PAGOS)
        resultado = [p for p in pagos if p.get("estado") == estado]
        resultado.sort(key=lambda p: p.get("created") or "", reverse=True)
        return resultado

    async def pagos_de_reserva(self, reserva_id: str) -> list[dict]:
        pagos = await moc.listar_todos(ENTIDAD_PAGOS)
        resultado = [p for p in pagos if p.get("reserva_id") == reserva_id]
        resultado.sort(key=lambda p: p.get("created") or "", reverse=True)
        return resultado

    async def obtener_pago(self, pago_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_PAGOS, pago_id)

    async def listar_pagos(
        self, estado: str | None = None, desde: str | None = None, hasta: str | None = None
    ) -> list[dict]:
        """WP-15 (auditoría de WorkPanels, 2026-08-01) — panel de solo
        lectura de Pagos y Facturas, antes inexistente."""
        pagos = await moc.listar_todos(ENTIDAD_PAGOS)
        resultado = pagos
        if estado:
            resultado = [p for p in resultado if p.get("estado") == estado]
        if desde:
            resultado = [p for p in resultado if (p.get("created") or "") >= desde]
        if hasta:
            resultado = [p for p in resultado if (p.get("created") or "") <= hasta]
        resultado.sort(key=lambda p: p.get("created") or "", reverse=True)
        return resultado

    async def metodo_pago_por_defecto(self) -> dict:
        metodo = await self._client.get_first("metodos_pago", 'activo=true')
        if metodo is None:
            raise RuntimeError("No hay ningún metodos_pago activo sembrado")
        return metodo

    async def listar_metodos_pago(self, nombre: str | None = None, estado: str | None = None) -> list[dict]:
        """WP-18 (auditoría de WorkPanels, 2026-08-01)."""
        condiciones = []
        if nombre:
            safe = nombre.replace('"', '\\"')
            condiciones.append(f'nombre~"{safe}"')
        if estado == "activo":
            condiciones.append("activo=true")
        elif estado == "inactivo":
            condiciones.append("activo=false")
        params: dict = {"sort": "nombre", "perPage": 200}
        if condiciones:
            params["filter"] = " && ".join(condiciones)
        resultado = await self._client.list_records("metodos_pago", params)
        return resultado["items"]

    async def obtener_metodo_pago(self, metodo_id: str) -> dict | None:
        try:
            return await self._client.get_record("metodos_pago", metodo_id)
        except PocketBaseError:
            return None

    async def crear_metodo_pago(self, data: dict) -> dict:
        return await self._client.create_record("metodos_pago", data)

    async def actualizar_metodo_pago(self, metodo_id: str, data: dict) -> dict:
        return await self._client.update_record("metodos_pago", metodo_id, data)

    # ── facturas ─────────────────────────────────────────────────────
    async def crear_factura(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_FACTURAS, id_, registro)

    async def obtener_factura(self, factura_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_FACTURAS, factura_id)

    async def factura_de_pago(self, pago_id: str) -> dict | None:
        facturas = await moc.listar_todos(ENTIDAD_FACTURAS)
        return next((f for f in facturas if f.get("pago_id") == pago_id), None)

    async def listar_facturas(self, desde: str | None = None, hasta: str | None = None) -> list[dict]:
        """WP-15 (auditoría de WorkPanels, 2026-08-01)."""
        facturas = await moc.listar_todos(ENTIDAD_FACTURAS)
        resultado = facturas
        if desde:
            resultado = [f for f in resultado if (f.get("fecha_emision") or "") >= desde]
        if hasta:
            resultado = [f for f in resultado if (f.get("fecha_emision") or "") <= hasta]
        resultado.sort(key=lambda f: f.get("fecha_emision") or "", reverse=True)
        return resultado

    async def guardar_pdf_factura(self, factura_id: str, filename: str, contenido: bytes) -> dict:
        await moc.subir_archivo(ENTIDAD_FACTURAS, factura_id, filename, contenido, "application/pdf")

        def _mutar(actual: dict) -> dict:
            actual["archivo_pdf"] = filename
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_FACTURAS, factura_id, _mutar)

    async def descargar_pdf_factura(self, factura_id: str, filename: str) -> bytes:
        return await moc.descargar_archivo(ENTIDAD_FACTURAS, factura_id, filename)

    # ── comisiones ───────────────────────────────────────────────────
    async def crear_comision(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_COMISIONES, id_, registro)

    async def obtener_comision(self, comision_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_COMISIONES, comision_id)

    async def actualizar_comision(self, comision_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_COMISIONES, comision_id, _mutar)

    async def listar_comisiones(
        self,
        filtro_campos: dict | None = None,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> list[dict]:
        """`filtro_campos` reemplaza el string-filter de PocketBase — dict
        de igualdad exacta campo->valor (suficiente para los llamadores
        reales: `estado`/`aerolinea_id`). `desde`/`hasta` filtran por
        `created` (fecha en que se generó la comisión — IS-20)."""
        comisiones = await moc.listar_todos(ENTIDAD_COMISIONES)
        if filtro_campos:
            comisiones = [
                c for c in comisiones
                if all(c.get(campo) == valor for campo, valor in filtro_campos.items())
            ]
        if desde:
            comisiones = [c for c in comisiones if (c.get("created") or "") >= desde]
        if hasta:
            comisiones = [c for c in comisiones if (c.get("created") or "") <= hasta]
        comisiones.sort(key=lambda c: c.get("created") or "", reverse=True)
        return comisiones

    async def comisiones_cobradas_sin_remesa(self, aerolinea_id: str) -> list[dict]:
        todas = await self.listar_comisiones({"aerolinea_id": aerolinea_id, "estado": "cobrada"})
        ya_remesadas = await moc.listar_todos(ENTIDAD_REMESA_COMISIONES)
        ids_remesados = {rc["comision_id"] for rc in ya_remesadas}
        return [c for c in todas if c["id"] not in ids_remesados]

    # ── remesas ──────────────────────────────────────────────────────
    async def crear_remesa(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_REMESAS, id_, registro)

    async def agregar_remesa_comision(self, remesa_id: str, comision_id: str) -> dict:
        id_, registro = _crear_registro({"remesa_id": remesa_id, "comision_id": comision_id})
        return await moc.crear(ENTIDAD_REMESA_COMISIONES, id_, registro)

    async def listar_remesas(
        self,
        estado: str | None = None,
        aerolinea_id: str | None = None,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> list[dict]:
        """CU-T52 — `estado=pendiente` filtra a remesas todavía sin pagar
        al proveedor. WP-14 (auditoría de WorkPanels, 2026-07-31) agregó
        la transición a "pagada" (antes no existía ningún camino de código
        que la escribiera, ver `marcar_remesa_pagada` en `remesa_service.py`).
        `aerolinea_id`/`desde`/`hasta` (sobre `fecha_generacion`) — IS-21,
        auditoría de informes simples, sesión 2026-08-01."""
        remesas = await moc.listar_todos(ENTIDAD_REMESAS)
        if estado:
            remesas = [r for r in remesas if r.get("estado") == estado]
        if aerolinea_id:
            remesas = [r for r in remesas if r.get("aerolinea_id") == aerolinea_id]
        if desde:
            remesas = [r for r in remesas if (r.get("fecha_generacion") or "") >= desde]
        if hasta:
            remesas = [r for r in remesas if (r.get("fecha_generacion") or "") <= hasta]
        remesas.sort(key=lambda r: r.get("created") or "", reverse=True)
        return remesas

    async def obtener_remesa(self, remesa_id: str) -> dict | None:
        return await moc.obtener(ENTIDAD_REMESAS, remesa_id)

    async def actualizar_remesa(self, remesa_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_REMESAS, remesa_id, _mutar)

    # ── reembolsos ───────────────────────────────────────────────────
    async def crear_reembolso(self, data: dict) -> dict:
        id_, registro = _crear_registro(data)
        return await moc.crear(ENTIDAD_REEMBOLSOS, id_, registro)

    async def actualizar_reembolso(self, reembolso_id: str, data: dict) -> dict:
        def _mutar(actual: dict) -> dict:
            actual.update(data)
            actual["updated"] = _timestamp()
            return actual

        return await moc.actualizar_con_reintento(ENTIDAD_REEMBOLSOS, reembolso_id, _mutar)

    async def listar_reembolsos(
        self,
        estado: str | None = None,
        motivo: str | None = None,
        desde: str | None = None,
        hasta: str | None = None,
    ) -> list[dict]:
        """IS-24 (auditoría de informes simples, sesión 2026-08-01) —
        `desde`/`hasta` sobre `fecha_solicitud`."""
        reembolsos = await moc.listar_todos(ENTIDAD_REEMBOLSOS)
        if estado:
            reembolsos = [r for r in reembolsos if r.get("estado") == estado]
        if motivo:
            termino = motivo.lower()
            reembolsos = [r for r in reembolsos if termino in (r.get("motivo") or "").lower()]
        if desde:
            reembolsos = [r for r in reembolsos if (r.get("fecha_solicitud") or "") >= desde]
        if hasta:
            reembolsos = [r for r in reembolsos if (r.get("fecha_solicitud") or "") <= hasta]
        reembolsos.sort(key=lambda r: r.get("fecha_solicitud") or "", reverse=True)
        return reembolsos

    # ── políticas de reembolso (CU-T18, PocketBase — catálogo/config) ──
    async def listar_politicas_reembolso(self, nombre: str | None = None) -> list[dict]:
        params: dict = {"perPage": 200, "sort": "nombre"}
        if nombre:
            safe = nombre.replace('"', '\\"')
            params["filter"] = f'nombre~"{safe}"'
        resultado = await self._client.list_records("politicas_reembolso", params)
        return resultado["items"]

    async def actualizar_politica_reembolso(self, politica_id: str, data: dict) -> dict:
        return await self._client.update_record("politicas_reembolso", politica_id, data)

    async def crear_politica_reembolso(self, data: dict) -> dict:
        return await self._client.create_record("politicas_reembolso", data)

    # ── configuración ────────────────────────────────────────────────
    async def config(self, clave: str) -> dict | None:
        safe = clave.replace('"', '\\"')
        return await self._client.get_first("configuracion_sistema", f'clave="{safe}"')
