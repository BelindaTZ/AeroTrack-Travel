"""
AeroTrack Travel — Tarea del módulo Facturación: actualizar tasas de cambio
(RF-FAC-011, CU-O85)
=============================================================================
Actualiza, 1×/día, las tasas de cambio (`tasas_cambio`) contra ExchangeRate-
API (RapidAPI, host confirmado funcionando en docs/apis-reference.md sección
10: `exchange-rate-api1.p.rapidapi.com`) para que las verticales de producto
puedan presentar precio en moneda local. El cobro real vía Stripe sigue
siempre en USD — esta conversión es solo de presentación (facturacion-spec.md
RF-FAC-011), nunca de cobro.

Config leída de `configuracion_sistema` (categoría `tasas_cambio`), no de
variables de entorno directamente — mismo criterio que
`flight_status_provider.py` (api_estado_vuelo.*), permite rotar la key o
agregar una moneda destino desde el backoffice sin redeploy.
"""

from __future__ import annotations

import datetime

import requests

import pocketbase_client as pb

_CATEGORIA = "tasas_cambio"
_BASE_URL = "https://exchange-rate-api1.p.rapidapi.com"


def _config(clave: str) -> str:
    valor = pb.get_config(f"{_CATEGORIA}.{clave}")
    if not valor:
        raise RuntimeError(f"configuracion_sistema.{_CATEGORIA}.{clave} no está sembrado")
    return valor


def _consultar_tasas(moneda_base: str, api_key: str, api_host: str) -> dict:
    resp = requests.get(
        f"{_BASE_URL}/latest",
        params={"base": moneda_base},
        headers={"x-rapidapi-key": api_key, "x-rapidapi-host": api_host},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def actualizar_tasas_cambio() -> int:
    """CU-O85. Idempotente por (moneda_origen, moneda_destino): actualiza la
    fila existente si ya hay una tasa para ese par, la crea si es la primera
    vez — nunca acumula histórico de filas por día (RF-FAC-011 es
    presentación del valor vigente, no una serie temporal)."""
    api_key = _config("rapidapi_key")
    api_host = _config("rapidapi_host")
    moneda_base = _config("moneda_base")
    monedas_destino = [m.strip() for m in _config("monedas_destino").split(",") if m.strip()]

    datos = _consultar_tasas(moneda_base, api_key, api_host)
    tasas = datos.get("rates") or datos.get("data") or {}
    if not tasas:
        raise RuntimeError(f"ExchangeRate-API no devolvió tasas para base={moneda_base}: {datos}")

    ahora_iso = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.000Z")
    actualizadas = 0

    for moneda_destino in monedas_destino:
        tasa = tasas.get(moneda_destino)
        if tasa is None:
            print(f"[TASAS_CAMBIO] ⚠ sin tasa para {moneda_base}->{moneda_destino}, se omite")
            continue

        existente = pb.get_first(
            "tasas_cambio", f'moneda_origen="{moneda_base}" && moneda_destino="{moneda_destino}"'
        )
        payload = {
            "moneda_origen": moneda_base,
            "moneda_destino": moneda_destino,
            "tasa": float(tasa),
            "fecha_actualizacion": ahora_iso,
        }
        if existente:
            pb.update("tasas_cambio", existente["id"], payload)
        else:
            pb.create("tasas_cambio", payload)
        actualizadas += 1

    print(f"[TASAS_CAMBIO] {actualizadas}/{len(monedas_destino)} tasas actualizadas (base={moneda_base})")
    return actualizadas
