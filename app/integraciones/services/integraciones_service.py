"""RF-INT-001/002 (CU-T37/T38) — configurar fuentes de datos externas y
consultar su bitácora de sincronizaciones.

Este módulo NO llama a ninguna API externa directamente (ver plan.md,
"Contexto técnico") — solo configura/monitorea lo que los jobs de catálogo
de cada vertical (Vuelos, Hoteles, Autos, Actividades, Cruceros) hacen. Por
eso `resincronizar_fuente` no puede disparar un sync real todavía: ningún
job de catálogo real está wireado a estas APIs (Vuelos sigue siendo
sintético, ver `dags/catalogo_vuelos_tasks.py`; las otras 4 verticales
todavía no tienen su Fase 1 implementada). Se registra la corrida como
`fallido` con el motivo real en `error_detalle`, en vez de fabricar un
"exitoso" con 0 registros — RN-INT-003 exige que una corrida fallida no
oculte la última exitosa, no que toda corrida se muestre como éxito.
"""

import datetime

from app.integraciones.repositories.integraciones_repo import IntegracionesRepository

TIPOS_CON_FRECUENCIA = {"catalogo_periodico"}
TIPOS_RESINCRONIZABLES = {"catalogo_periodico"}


class FuenteNoEncontrada(Exception):
    pass


class CampoNoAplicaParaTipoUso(Exception):
    def __init__(self, campo: str, tipo_uso: str) -> None:
        self.campo = campo
        self.tipo_uso = tipo_uso
        super().__init__(f"'{campo}' no aplica a fuentes con tipo_uso='{tipo_uso}'")


class FuenteNoResincronizable(Exception):
    def __init__(self, tipo_uso: str) -> None:
        self.tipo_uso = tipo_uso
        super().__init__(f"Fuentes con tipo_uso='{tipo_uso}' no tienen resincronización manual")


def _ahora_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")


async def listar_fuentes_con_cuota() -> list[dict]:
    repo = IntegracionesRepository()
    fuentes = await repo.listar_fuentes()
    salida = []
    for fuente in fuentes:
        cuota = await repo.cuota_consumida_por_fuente(fuente["id"])
        salida.append({**fuente, "cuota_consumida": cuota})
    return salida


async def actualizar_fuente(
    fuente_id: str,
    activa: bool | None = None,
    frecuencia_sincronizacion_horas: int | None = None,
) -> dict:
    repo = IntegracionesRepository()
    fuente = await repo.obtener_fuente(fuente_id)
    if fuente is None:
        raise FuenteNoEncontrada(fuente_id)

    data: dict = {}
    if activa is not None:
        data["activa"] = activa
    if frecuencia_sincronizacion_horas is not None:
        if fuente["tipo_uso"] not in TIPOS_CON_FRECUENCIA:
            raise CampoNoAplicaParaTipoUso("frecuencia_sincronizacion_horas", fuente["tipo_uso"])
        data["frecuencia_sincronizacion_horas"] = frecuencia_sincronizacion_horas

    if not data:
        return fuente
    # RN-INT-002: desactivar (o cualquier otro cambio de config) solo toca
    # este registro — nunca borra ni toca vuelos_catalogo/hoteles_catalogo/etc.
    return await repo.actualizar_fuente(fuente_id, data)


async def resincronizar_fuente(fuente_id: str, usuario_id: str) -> dict:
    repo = IntegracionesRepository()
    fuente = await repo.obtener_fuente(fuente_id)
    if fuente is None:
        raise FuenteNoEncontrada(fuente_id)
    if fuente["tipo_uso"] not in TIPOS_RESINCRONIZABLES:
        raise FuenteNoResincronizable(fuente["tipo_uso"])

    ahora = _ahora_iso()
    return await repo.crear_log(
        {
            "fuente_id": fuente_id,
            "tipo_producto": fuente.get("tipo_producto_alimentado"),
            "fecha_inicio": ahora,
            "fecha_fin": ahora,
            "estado": "fallido",
            "registros_procesados": 0,
            "registros_nuevos": 0,
            "registros_actualizados": 0,
            "error_detalle": (
                f"Resincronización manual solicitada, pero el job de catálogo real de "
                f"'{fuente['nombre']}' todavía no está implementado (ver pendientes-implementacion-codigo.md)."
            ),
            "ejecutado_por": usuario_id,
        }
    )


async def listar_bitacora(fuente_id: str | None = None, desde: str | None = None, hasta: str | None = None) -> list[dict]:
    repo = IntegracionesRepository()
    condiciones = []
    if fuente_id:
        condiciones.append(f'fuente_id="{fuente_id}"')
    if desde:
        condiciones.append(f'fecha_inicio>="{desde} 00:00:00.000Z"')
    if hasta:
        condiciones.append(f'fecha_inicio<="{hasta} 23:59:59.999Z"')
    filtro = " && ".join(condiciones) if condiciones else None
    return await repo.listar_bitacora(filtro)
