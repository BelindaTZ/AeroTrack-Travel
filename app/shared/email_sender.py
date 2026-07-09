"""Envío de correo — capa de abstracción reemplazable (F1).

Implementación actual: log estructurado (no hay app-password de SMTP
configurada todavía, ver `configuracion_sistema.smtp.host`). Reemplazar
`enviar_correo` con una implementación SMTP/API real no debe requerir tocar
ningún caller — todos usan esta única función.
"""

import logging

logger = logging.getLogger("email")


async def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> None:
    logger.info("EMAIL -> %s | %s\n%s", destinatario, asunto, cuerpo)
