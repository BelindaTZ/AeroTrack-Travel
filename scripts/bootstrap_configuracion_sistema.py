"""
AeroTrack Travel — Precarga de configuración desde .env (CU-O17/O18/O19)
============================================================================
Qué hace: si configuracion_sistema no tiene todavía los valores de las
integraciones externas (Stripe, API de estado de vuelo, Gmail API), los
crea a partir de las variables de entorno. Es idempotente — nunca
sobreescribe una clave que el administrador ya haya modificado desde la UI
(ese es justamente el propósito de CU-O17/O18/O19: configurar una vez
desde .env, después administrar desde el panel sin volver a tocar .env).

Pensado para invocarse en el arranque de la futura app (FastAPI lifespan
hook) — por ahora, mientras esa capa no existe, se ejecuta manualmente.

Uso:
    python scripts/bootstrap_configuracion_sistema.py
"""

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

PB_URL = os.getenv("PB_TRAVEL_URL", "http://localhost:8091")
PB_EMAIL = os.getenv("PB_TRAVEL_EMAIL", "")
PB_PASSWORD = os.getenv("PB_TRAVEL_PASSWORD", "")


def autenticar() -> str:
    resp = requests.post(f"{PB_URL}/api/admins/auth-with-password",
                          json={"identity": PB_EMAIL, "password": PB_PASSWORD}, timeout=15)
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    token = autenticar()
    H = {"Authorization": token}

    admin = requests.get(f"{PB_URL}/api/collections/usuarios/records",
                          headers=H, params={"filter": f'email="{PB_EMAIL}"'}, timeout=15).json()["items"]
    if not admin:
        print("XX No se encontró el usuario administrador en 'usuarios'. Ejecuta el seed inicial primero.")
        sys.exit(1)
    modificado_por = admin[0]["id"]

    # (clave, valor_desde_env, categoria, descripcion)
    filas = [
        ("stripe.secret_key", os.getenv("STRIPE_SECRET_KEY", ""), "stripe",
         "Clave secreta de Stripe (test mode) — CU-O19"),
        ("stripe.publishable_key", os.getenv("STRIPE_PUBLISHABLE_KEY", ""), "stripe",
         "Clave publicable de Stripe (test mode) — CU-O19"),
        ("api_estado_vuelo.proveedor", "aviationstack", "api_estado_vuelo",
         "Proveedor activo de estado de vuelo en tiempo real — CU-O17"),
        ("api_estado_vuelo.api_key", os.getenv("FLIGHT_STATUS_API_KEY", ""), "api_estado_vuelo",
         "API key de AviationStack — CU-O17"),
        ("api_estado_vuelo.timeout_segundos", "10", "api_estado_vuelo",
         "Timeout configurable por integración (constitución F2)"),
        ("gmail_api.client_id", os.getenv("GMAIL_CLIENT_ID", ""), "gmail_api",
         "OAuth client_id del monitor de bandeja de correo — CU-O18"),
        ("gmail_api.client_secret", os.getenv("GMAIL_CLIENT_SECRET", ""), "gmail_api",
         "OAuth client_secret del monitor de bandeja de correo — CU-O18"),
        ("gmail_api.refresh_token", os.getenv("GMAIL_REFRESH_TOKEN", ""), "gmail_api",
         "OAuth refresh_token del monitor de bandeja de correo — CU-O18"),
        ("gmail_api.monitored_email", "aerotracktravel.demo@gmail.com", "gmail_api",
         "Buzón de la agencia que se monitorea para avisos de aerolíneas (CU-O41)"),
        ("smtp.remitente", "aerotracktravel.demo@gmail.com", "smtp",
         "Correo remitente para el envío de notificaciones (CU-O16) — falta contraseña/app-password, pendiente de configurar en la UI"),
    ]

    creadas = actualizadas_omitidas = 0
    for clave, valor, categoria, descripcion in filas:
        if not valor:
            print(f"!! omitido {clave}: no hay valor en .env")
            continue
        existente_resp = requests.get(f"{PB_URL}/api/collections/configuracion_sistema/records",
                                       headers=H, params={"filter": f'clave="{clave}"'}, timeout=15).json()
        if existente_resp.get("items"):
            print(f"= ya existe (no se sobreescribe): {clave}")
            actualizadas_omitidas += 1
            continue
        resp = requests.post(f"{PB_URL}/api/collections/configuracion_sistema/records", headers=H, json={
            "clave": clave, "valor": valor, "categoria": categoria,
            "descripcion": descripcion, "modificado_por": modificado_por,
        }, timeout=15)
        if resp.status_code != 200:
            print(f"XX ERROR creando {clave}: {resp.status_code} {resp.text}")
            sys.exit(1)
        print(f"+ creada: {clave}")
        creadas += 1

    # smtp.host ya existía como placeholder (seed inicial) — actualizar su
    # descripción para reflejar la decisión de correo dedicado (CU-O16).
    smtp_host = requests.get(f"{PB_URL}/api/collections/configuracion_sistema/records",
                              headers=H, params={"filter": 'clave="smtp.host"'}, timeout=15).json()["items"]
    if smtp_host:
        requests.patch(f"{PB_URL}/api/collections/configuracion_sistema/records/{smtp_host[0]['id']}", headers=H, json={
            "descripcion": "Servidor SMTP para el envío de notificaciones al pasajero (CU-O16/O43). "
                           "Remitente decidido: aerotracktravel.demo@gmail.com (ver smtp.remitente). "
                           "Falta la contraseña/app-password — pendiente de configurar en la UI.",
            "modificado_por": modificado_por,
        })
        print("~ actualizada descripción de smtp.host")

    print(f"\nListo: {creadas} filas nuevas, {actualizadas_omitidas} ya existían (sin tocar).")


if __name__ == "__main__":
    main()
