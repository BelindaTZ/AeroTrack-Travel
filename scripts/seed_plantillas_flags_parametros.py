"""Ampliación de WP-08 (Configuración del sistema, sesión 2026-08-01):
siembra idempotente de 3 categorías nuevas en `configuracion_sistema`,
todas leídas con override-y-fallback desde el código que antes tenía el
valor hardcodeado (mismo patrón que `carrito_abandonado.plantilla_*`,
ver `app/carrito/services/abandono_service.py`):

- `plantilla_notificacion`: asunto/cuerpo de los correos que el sistema
  ya envía (recuperación de contraseña, reseteo por admin, bienvenida,
  disrupciones) — antes texto fijo en el código, ahora editable.
- `feature_flag`: interruptores reales que el código consulta antes de
  ejecutar una acción (por ahora: `pagos.stripe_habilitado`).
- `parametro_negocio`: constantes de negocio que antes eran solo un
  literal Python (precio de extras en checkout, umbral de intentos de
  login sospechosos).

Ejecutar: python scripts/seed_plantillas_flags_parametros.py
"""

import asyncio
import sys

sys.path.insert(0, ".")

from app.shared.pocketbase_client import get_pocketbase_client

PLANTILLAS = [
    ("password_recovery.plantilla_asunto", "Recuperación de contraseña — AeroTrack Travel",
     "Asunto del correo de recuperación de contraseña (RF-SEG-004)"),
    ("password_recovery.plantilla_cuerpo",
     "Usa este enlace para restablecer tu contraseña (válido por tiempo limitado): {enlace}",
     "Cuerpo del correo de recuperación de contraseña — {enlace} se reemplaza en tiempo real"),
    ("password_reset_admin.plantilla_asunto", "Restablecimiento de contraseña — AeroTrack Travel",
     "Asunto del correo cuando un administrador resetea la contraseña de otro usuario"),
    ("password_reset_admin.plantilla_cuerpo",
     "Un administrador inició un restablecimiento de tu contraseña. "
     "Usa este enlace (válido por tiempo limitado): {enlace}",
     "Cuerpo del correo de reseteo iniciado por administrador — {enlace} se reemplaza en tiempo real"),
    ("bienvenida.plantilla_asunto", "Bienvenido a AeroTrack Travel",
     "Asunto del correo de bienvenida al registrarse (autoservicio)"),
    ("bienvenida.plantilla_cuerpo", "Tu cuenta fue creada correctamente. Ya puedes iniciar sesión.",
     "Cuerpo del correo de bienvenida al registrarse"),
    ("disrupciones.plantilla_asunto", "AeroTrack Travel — {codigo_reserva}",
     "Asunto de la notificación de disrupción — {codigo_reserva} se reemplaza en tiempo real"),
    ("disrupciones.plantilla_retraso", "Tu vuelo {numero_vuelo} sufrió un retraso.",
     "Cuerpo de notificación de disrupción tipo retraso — {numero_vuelo} se reemplaza en tiempo real"),
    ("disrupciones.plantilla_cancelacion", "Tu vuelo {numero_vuelo} fue cancelado por la aerolínea.",
     "Cuerpo de notificación de disrupción tipo cancelación — {numero_vuelo} se reemplaza en tiempo real"),
    ("disrupciones.plantilla_cambio_horario", "El horario de tu vuelo {numero_vuelo} cambió.",
     "Cuerpo de notificación de disrupción tipo cambio de horario — {numero_vuelo} se reemplaza en tiempo real"),
    ("disrupciones.plantilla_cambio_puerta", "La puerta de embarque de tu vuelo {numero_vuelo} cambió.",
     "Cuerpo de notificación de disrupción tipo cambio de puerta — {numero_vuelo} se reemplaza en tiempo real"),
    ("disrupciones.plantilla_desvio", "Tu vuelo {numero_vuelo} fue desviado a otro destino.",
     "Cuerpo de notificación de disrupción tipo desvío — {numero_vuelo} se reemplaza en tiempo real"),
]

FEATURE_FLAGS = [
    ("pagos.stripe_habilitado", "true",
     "Si está en false, ningún pago/autorización/captura llega a Stripe — se rechaza con "
     "un mensaje amigable en vez de fallar duro."),
]

PARAMETROS = [
    ("reservas.precio_extra_equipaje", "35.0",
     "Precio del extra 'Equipaje facturado adicional' en el checkout de vuelos (USD)"),
    ("reservas.precio_extra_seguro", "20.0",
     "Precio del extra 'Seguro de viaje' en el checkout de vuelos (USD)"),
    ("seguridad.intentos_sospechoso_umbral", "5",
     "Cantidad de intentos de login fallidos dentro de la ventana para marcar una cuenta/IP como sospechosa"),
]


async def _seed_categoria(client, categoria: str, filas: list[tuple[str, str, str]]) -> None:
    existentes = {
        c["clave"]
        for c in (await client.list_records(
            "configuracion_sistema", {"filter": f'categoria="{categoria}"', "perPage": 200}
        ))["items"]
    }
    admin = await client.get_first("roles", 'nombre="Administrador"')
    usuarios_admin = (await client.list_records(
        "usuarios", {"filter": f'rol_id="{admin["id"]}"', "perPage": 1}
    ))["items"] if admin else []
    if not usuarios_admin:
        raise RuntimeError("No hay ningún usuario Administrador — correr seed_seguridad.py y crear uno primero")
    modificado_por = usuarios_admin[0]["id"]

    creados = 0
    for clave, valor, descripcion in filas:
        if clave in existentes:
            continue
        await client.create_record(
            "configuracion_sistema",
            {"clave": clave, "valor": valor, "categoria": categoria, "descripcion": descripcion,
             "modificado_por": modificado_por},
        )
        creados += 1
    print(f"+ {categoria}: {creados} creados, {len(filas) - creados} ya existían")


async def main() -> None:
    client = get_pocketbase_client()
    await _seed_categoria(client, "plantilla_notificacion", PLANTILLAS)
    await _seed_categoria(client, "feature_flag", FEATURE_FLAGS)
    await _seed_categoria(client, "parametro_negocio", PARAMETROS)
    print("Listo.")


if __name__ == "__main__":
    asyncio.run(main())
