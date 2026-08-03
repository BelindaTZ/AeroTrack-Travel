"""Endpoints internos de solo lectura para los DAGs ETL de ClickHouse
(Fase B, sesión 2026-08-02) — devuelven colecciones OPERACIONAL completas
como JSON, vía los repositorios existentes.

Único punto de acceso para los DAGs a estas colecciones: desde la
migración a MinIO, ningún DAG las lee/escribe directo (ver
`dags/dag_estimar_riesgo_disrupcion.py`, mismo principio ya establecido
para el simulador de riesgo — "el DAG ya no puede escribir la colección
directo... solo la app tiene acceso"). Cada tarea `extraer` de los DAGs
`aerotrack_travel_etl_comercial/operaciones/clientes/finanzas` llama a uno
de estos endpoints en vez de instanciar un cliente MinIO propio.

Misma nota de seguridad que el resto de `/internal/*`: sin autenticación,
pensado para llamarse solo dentro de la red Docker (`travel-network`);
en un despliegue real haría falta protegerlo a nivel de red o con token
compartido — no implementado en esta sesión, igual que los demás.
"""

from fastapi import APIRouter

from app.asistente_ia.repositories.asistente_repo import AsistenteRepository
from app.carrito.repositories.carrito_repo import CarritoRepository
from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.cuenta.repositories.cuenta_repo import CuentaRepository
from app.disrupciones.repositories.disrupciones_repo import DisrupcionesRepository
from app.facturacion.repositories.facturacion_repo import FacturacionRepository
from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.reservas.repositories.reservas_repo import ReservasRepository

router = APIRouter(prefix="/internal/analitica")


# ── comercial ────────────────────────────────────────────────────────────
@router.get("/reservas")
async def reservas_endpoint() -> list[dict]:
    return await ReservasRepository().listar_todas()


@router.get("/reserva-items")
async def reserva_items_endpoint() -> list[dict]:
    return await ReservasRepository().listar_todos_items()


@router.get("/carrito-items")
async def carrito_items_endpoint() -> list[dict]:
    return await CarritoRepository().listar_todos_items()


@router.get("/busquedas-recientes")
async def busquedas_recientes_endpoint() -> list[dict]:
    return await CuentaRepository().listar_todas_busquedas()


@router.get("/pagos")
async def pagos_endpoint() -> list[dict]:
    return await FacturacionRepository().listar_pagos()


@router.get("/facturas")
async def facturas_endpoint() -> list[dict]:
    return await FacturacionRepository().listar_facturas()


@router.get("/comisiones")
async def comisiones_endpoint() -> list[dict]:
    return await FacturacionRepository().listar_comisiones()


@router.get("/reembolsos")
async def reembolsos_endpoint() -> list[dict]:
    return await FacturacionRepository().listar_reembolsos()


@router.get("/remesas")
async def remesas_endpoint() -> list[dict]:
    return await FacturacionRepository().listar_remesas()


# ── operaciones ──────────────────────────────────────────────────────────
@router.get("/disrupciones")
async def disrupciones_endpoint() -> list[dict]:
    return await DisrupcionesRepository().listar_disrupciones()


@router.get("/notificaciones")
async def notificaciones_endpoint() -> list[dict]:
    return await DisrupcionesRepository().listar_notificaciones()


@router.get("/casos-escalados")
async def casos_escalados_endpoint() -> list[dict]:
    return await CentroAyudaRepository().listar_casos()


@router.get("/mensajes-ia")
async def mensajes_ia_endpoint() -> list[dict]:
    return await AsistenteRepository().listar_todos_mensajes()


@router.get("/conversaciones-ia")
async def conversaciones_ia_endpoint() -> list[dict]:
    return await AsistenteRepository().listar_todas_conversaciones()


# ── clientes ─────────────────────────────────────────────────────────────
@router.get("/pasajeros")
async def pasajeros_endpoint() -> list[dict]:
    return await PasajerosRepository().listar_todos_pasajeros()


@router.get("/alertas-precio")
async def alertas_precio_endpoint() -> list[dict]:
    return await ReservasRepository().listar_todas_alertas()
