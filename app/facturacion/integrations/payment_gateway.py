"""Única puerta al SDK de Stripe en todo el sistema (REG-F1) — ningún otro
módulo importa `stripe` directamente. Credenciales leídas de
`configuracion_sistema` (REG-B3, nunca hardcodeadas). El SDK de Stripe es
síncrono; cada llamada se envuelve en `asyncio.to_thread` para no bloquear
el event loop de FastAPI (mismo patrón que `minio_dims_reader`).

Escenarios de prueba (ver nota de alcance en `plan.md`): en vez de
Stripe.js Elements, se usan los PaymentMethod ID de prueba que Stripe
documenta oficialmente para probar sin tokenizar una tarjeta real —
la llamada a la API sigue siendo 100% real.
"""

import asyncio

import stripe

from app.shared.pocketbase_client import get_pocketbase_client

PAYMENT_METHOD_EXITOSO = "pm_card_visa"
PAYMENT_METHOD_RECHAZADO = "pm_card_visa_chargeDeclined"


class PagoRechazado(Exception):
    def __init__(self, motivo: str):
        self.motivo = motivo
        super().__init__(motivo)


async def _api_key() -> str:
    client = get_pocketbase_client()
    config = await client.get_first("configuracion_sistema", 'clave="stripe.secret_key"')
    if config is None:
        raise RuntimeError("configuracion_sistema.stripe.secret_key no está configurada")
    return config["valor"]


def _cobrar_sync(api_key: str, monto_centavos: int, metodo_pago: str, idempotency_key: str, descripcion: str) -> dict:
    stripe.api_key = api_key
    try:
        intent = stripe.PaymentIntent.create(
            amount=monto_centavos,
            currency="usd",
            payment_method=metodo_pago,
            confirm=True,
            description=descripcion,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            idempotency_key=idempotency_key,
        )
        return {"id": intent.id, "status": intent.status}
    except stripe.error.CardError as exc:
        return {"id": exc.json_body.get("error", {}).get("payment_intent", {}).get("id"), "status": "failed", "motivo": exc.user_message or str(exc)}


async def cobrar(monto: float, metodo_pago: str, idempotency_key: str, descripcion: str) -> dict:
    """Devuelve {"id": payment_intent_id, "status": "succeeded"|"failed", "motivo"?: str}."""
    api_key = await _api_key()
    monto_centavos = int(round(monto * 100))
    return await asyncio.to_thread(
        _cobrar_sync, api_key, monto_centavos, metodo_pago, idempotency_key, descripcion
    )


def _autorizar_sync(api_key: str, monto_centavos: int, metodo_pago: str, idempotency_key: str, descripcion: str) -> dict:
    """RF-FAC-012 (CU-O86) — mismo flujo que `_cobrar_sync` pero con
    `capture_method='manual'`: el cargo queda retenido (`requires_capture`)
    en la tarjeta sin completarse hasta que `_capturar_sync` lo confirme."""
    stripe.api_key = api_key
    try:
        intent = stripe.PaymentIntent.create(
            amount=monto_centavos,
            currency="usd",
            payment_method=metodo_pago,
            confirm=True,
            capture_method="manual",
            description=descripcion,
            automatic_payment_methods={"enabled": True, "allow_redirects": "never"},
            idempotency_key=idempotency_key,
        )
        return {"id": intent.id, "status": intent.status}
    except stripe.error.CardError as exc:
        return {"id": exc.json_body.get("error", {}).get("payment_intent", {}).get("id"), "status": "failed", "motivo": exc.user_message or str(exc)}


async def autorizar(monto: float, metodo_pago: str, idempotency_key: str, descripcion: str) -> dict:
    """Devuelve {"id": payment_intent_id, "status": "requires_capture"|"failed", "motivo"?: str}."""
    api_key = await _api_key()
    monto_centavos = int(round(monto * 100))
    return await asyncio.to_thread(
        _autorizar_sync, api_key, monto_centavos, metodo_pago, idempotency_key, descripcion
    )


def _capturar_sync(api_key: str, payment_intent_id: str) -> dict:
    stripe.api_key = api_key
    try:
        intent = stripe.PaymentIntent.capture(payment_intent_id)
        return {"id": intent.id, "status": intent.status}
    except stripe.error.StripeError as exc:
        return {"id": payment_intent_id, "status": "failed", "motivo": str(exc)}


async def capturar(payment_intent_id: str) -> dict:
    """RF-FAC-012 — completa un cargo previamente autorizado (`requires_capture`).
    Devuelve {"id": payment_intent_id, "status": "succeeded"|"failed", "motivo"?: str}."""
    api_key = await _api_key()
    return await asyncio.to_thread(_capturar_sync, api_key, payment_intent_id)


def _reembolsar_sync(api_key: str, payment_intent_id: str, monto_centavos: int) -> dict:
    stripe.api_key = api_key
    refund = stripe.Refund.create(payment_intent=payment_intent_id, amount=monto_centavos)
    return {"id": refund.id, "status": refund.status}


async def reembolsar(payment_intent_id: str, monto: float) -> dict:
    api_key = await _api_key()
    monto_centavos = int(round(monto * 100))
    return await asyncio.to_thread(_reembolsar_sync, api_key, payment_intent_id, monto_centavos)
