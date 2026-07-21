"""Corrige, de una sola vez, TODOS los campos numéricos `required=true`
restantes en `pocketbase-travel` que podrían legítimamente valer `0` en un
caso de negocio real — el mismo bug ya encontrado dos veces por separado
(`tarifas_vuelo.cupos_disponibles`, `hoteles_tarifas.precio_final`/
`.reembolsable`): PocketBase 0.22 trata `0`/`false` como valor AUSENTE en
campos `required`, no como un valor válido.

En vez de esperar a que cada colección falle en su turno según se
implementen Autos/Actividades/Cruceros/Paquetes/Carrito/Ofertas/Programa de
beneficios, se audita TODO el esquema real ahora (`scripts/` no tiene un
"fix" separado por módulo esta vez) y se corrige de un tirón. Casos reales
con `0` legítimo ya identificados: `reservas.total_pagar`/
`reserva_items.precio_final`/`pagos.monto` (100% de descuento por cupón
acumulado con paquete, CU-T44), `actividades_horarios.precio` (actividades
gratuitas, muy comunes: tours a pie, días de museo gratis),
`programa_beneficios_niveles.puntos_minimos` (el nivel de entrada SIEMPRE
empieza en 0 puntos), `cupones_uso.monto_descontado` (un cupón de 100%
sobre un ítem ya gratis). El resto se corrige por consistencia/prevención,
no por un caso de negocio confirmado — no hay costo real en permitir `0`
donde antes solo se permitían positivos.

Excepción deliberada: `tasas_cambio.tasa` NO se toca — una tasa de cambio
en 0 nunca es un valor de negocio válido (siempre sería un error de datos,
no un caso legítimo), así que aquí sí tiene sentido que PocketBase la
rechace como "falta".

Idempotente.

Ejecutar: python scripts/pb_schema_fix_required_numericos.py
"""

import os

import httpx
from dotenv import load_dotenv

load_dotenv()

PB_URL = os.environ["PB_TRAVEL_URL"].rstrip("/")
PB_EMAIL = os.environ["PB_TRAVEL_EMAIL"]
PB_PASSWORD = os.environ["PB_TRAVEL_PASSWORD"]

# (coleccion, [campos]) — excluye tasas_cambio.tasa a propósito (ver docstring)
CAMPOS_POR_COLECCION = {
    "aerolineas": ["comision_pactada_pct"],
    "vuelos_catalogo": ["precio_base"],
    "reservas": ["total_pagar"],
    "reserva_extras": ["precio"],
    "alertas_precio": ["precio_umbral"],
    "pagos": ["monto"],
    "comisiones": ["monto"],
    "remesas": ["monto_total"],
    "reembolsos": ["monto"],
    "facturas": ["total"],
    "asientos_vuelo": ["fila"],
    "predicciones_precio_ruta": ["precio_predicho"],
    "autos_catalogo": ["precio_dia"],
    "actividades_horarios": ["precio"],
    "cruceros_catalogo": ["precio_base"],
    "cruceros_camarotes_tarifa": ["precio_por_persona"],
    "tipos_paquete_descuento": ["porcentaje_descuento"],
    "reserva_items": ["precio_final"],
    "carrito_items": ["precio_snapshot"],
    "programa_beneficios_niveles": ["puntos_minimos", "puntos_por_dolar"],
    "programa_beneficios_movimientos": ["puntos"],
    "cupones_descuento": ["valor"],
    "cupones_uso": ["monto_descontado"],
}


def admin_token() -> str:
    resp = httpx.post(
        f"{PB_URL}/api/admins/auth-with-password",
        json={"identity": PB_EMAIL, "password": PB_PASSWORD},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["token"]


def main() -> None:
    headers = {"Authorization": admin_token()}
    total_corregidos = 0

    for nombre_coleccion, campos in CAMPOS_POR_COLECCION.items():
        resp = httpx.get(f"{PB_URL}/api/collections/{nombre_coleccion}", headers=headers, timeout=10)
        resp.raise_for_status()
        coleccion = resp.json()
        schema = coleccion.get("schema", coleccion.get("fields"))

        cambiado = False
        for nombre_campo in campos:
            campo = next((f for f in schema if f["name"] == nombre_campo), None)
            if campo is None:
                print(f"  ! {nombre_coleccion}.{nombre_campo} no existe, se omite")
                continue
            if not campo["required"]:
                print(f"  = {nombre_coleccion}.{nombre_campo} ya es required=false")
                continue
            campo["required"] = False
            cambiado = True
            total_corregidos += 1
            print(f"  + {nombre_coleccion}.{nombre_campo} ahora es required=false")

        if not cambiado:
            continue

        patch = httpx.patch(
            f"{PB_URL}/api/collections/{coleccion['id']}", json={"schema": schema}, headers=headers, timeout=10
        )
        if patch.status_code >= 400:
            print(f"  ! posible 400 cosmético en {nombre_coleccion} (ver nota en pb_schema_vuelos_v3.py): {patch.text}")

    print(f"\nListo. {total_corregidos} campo(s) corregido(s) en esta corrida.")


if __name__ == "__main__":
    main()
