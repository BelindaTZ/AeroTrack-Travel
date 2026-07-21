"""RF-IA-001..006, RF-IA-T01..T02 — orquestación del Asistente IA.

Diseño deliberado ante la falta de credencial real de LLM (ni
`groq.api_key` ni `gemini.api_key` sembrados): para los hechos
ESTRUCTURADOS que `contexto_service` ya verificó (ej. el estado real de
una reserva propia), la respuesta se arma con una plantilla determinista
— no necesita al LLM para eso, es más confiable que pedirle a un modelo
que "no se equivoque" repitiendo un número que ya tenemos exacto. El LLM
solo se invoca para la fase abierta (cuando hay contexto verificado pero
la pregunta necesita explicarlo en lenguaje natural, o no hay contexto y
se necesita reconocer el tema). Si el LLM no está disponible en ese
punto, el sistema lo dice explícitamente y ofrece escalar — nunca
aproxima (RN-IA-001/003)."""

import json
from datetime import datetime, timezone

from app.asistente_ia.integrations.llm_client import CredencialNoConfigurada, LLMClient
from app.asistente_ia.repositories.asistente_repo import AsistenteRepository
from app.asistente_ia.services.contexto_service import resolver_contexto
from app.seguridad.services.audit_service import AuditService

MENSAJE_SIN_CREDENCIAL = (
    "No puedo generar una respuesta abierta en este momento — nuestro asistente de IA no está disponible. "
    "¿Quieres que escalemos tu consulta a un agente humano?"
)
MENSAJE_SIN_CONTEXTO_VERIFICADO = (
    "No tengo un dato verificado en el sistema para responder eso con seguridad todavía. "
    "¿Quieres que escalemos tu consulta a un agente humano?"
)


def _ahora_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000Z")


async def _configuracion() -> dict:
    repo = AsistenteRepository()
    tono = await repo.config("asistente_ia.tono")
    temas = await repo.config("asistente_ia.temas_permitidos")
    predefinidas = await repo.config("asistente_ia.respuestas_predefinidas")
    return {
        "tono": tono["valor"] if tono else "profesional y cercano",
        "temas_permitidos": [t.strip() for t in temas["valor"].split(",") if t.strip()] if temas and temas["valor"] else [],
        "respuestas_predefinidas": json.loads(predefinidas["valor"]) if predefinidas and predefinidas["valor"] else {},
    }


def _respuesta_predefinida(mensaje: str, predefinidas: dict) -> str | None:
    texto = mensaje.lower()
    for palabra_clave, respuesta in predefinidas.items():
        if palabra_clave.lower() in texto:
            return respuesta
    return None


def _tema_permitido(mensaje: str, temas_permitidos: list[str]) -> bool:
    if not temas_permitidos:  # RN-IA-T01: sin lista configurada, no hay restricción activa todavía
        return True
    texto = mensaje.lower()
    return any(tema.lower() in texto for tema in temas_permitidos)


def _respuesta_desde_contexto_estructurado(contexto: list[dict]) -> str | None:
    """Hechos con forma conocida se responden con plantilla determinista,
    sin necesitar al LLM — más confiable para cifras/estados exactos."""
    for hecho in contexto:
        if hecho["tipo"] == "reserva_propia":
            paquete = " (parte de un paquete)" if hecho["es_paquete"] else ""
            return (
                f"Tu reserva {hecho['codigo_reserva']}{paquete} está en estado \"{hecho['estado']}\", "
                f"con un total a pagar de ${hecho['total_pagar']:.2f}. "
                f"Creada el {hecho['fecha_reserva'][:10]}."
            )
        if hecho["tipo"] == "visa_sin_dato_cacheado":
            return (
                "Todavía no tenemos un requisito de visa verificado en caché para esa consulta — "
                "no puedo darte una respuesta confiable sobre eso ahora mismo. "
                "¿Quieres que escalemos tu consulta a un agente humano?"
            )
    return None


async def conversar(
    usuario: dict | None, pasajero_id: str | None, mensaje_texto: str, llm: LLMClient
) -> dict:
    config = await _configuracion()

    predefinida = _respuesta_predefinida(mensaje_texto, config["respuestas_predefinidas"])
    if predefinida:
        respuesta_texto = predefinida
    elif not _tema_permitido(mensaje_texto, config["temas_permitidos"]):
        respuesta_texto = (
            f"Esa consulta está fuera de los temas que puedo cubrir ahora mismo "
            f"({', '.join(config['temas_permitidos'])}). ¿Quieres que escalemos tu caso a un agente humano?"
        )
    else:
        contexto = await resolver_contexto(pasajero_id, mensaje_texto)
        respuesta_texto = _respuesta_desde_contexto_estructurado(contexto)
        if respuesta_texto is None:
            if not contexto:
                respuesta_texto = MENSAJE_SIN_CONTEXTO_VERIFICADO
            else:
                system_prompt = (
                    f"Eres el asistente de AeroTrack Travel. Tono: {config['tono']}. "
                    "Solo puedes afirmar datos específicos que aparezcan en CONTEXTO VERIFICADO. "
                    "Si necesitas un dato que no está ahí, dilo explícitamente y ofrece escalar a un "
                    "agente humano — nunca inventes ni aproximes.\n\nCONTEXTO VERIFICADO:\n"
                    + json.dumps(contexto, ensure_ascii=False)
                )
                try:
                    respuesta_texto = await llm.generar(system_prompt, [], mensaje_texto)
                except CredencialNoConfigurada:
                    respuesta_texto = MENSAJE_SIN_CREDENCIAL

    if not pasajero_id:
        return {"respuesta": respuesta_texto, "conversacion_id": None, "persistido": False}

    repo = AsistenteRepository()
    ahora = _ahora_iso()
    conversacion = await repo.conversacion_activa_de_pasajero(pasajero_id)
    if conversacion is None:
        conversacion = await repo.crear_conversacion(pasajero_id, ahora)

    await repo.crear_mensaje(conversacion["id"], "usuario", mensaje_texto, ahora)
    mensaje_asistente = await repo.crear_mensaje(conversacion["id"], "asistente", respuesta_texto, ahora)
    await repo.actualizar_actividad(conversacion["id"], ahora, titulo=conversacion.get("titulo") or mensaje_texto[:60])

    if usuario:
        await AuditService().insertar(
            "conversar_asistente_ia", "mensajes_ia", usuario_id=usuario["id"], registro_id=mensaje_asistente["id"]
        )

    return {
        "respuesta": respuesta_texto, "conversacion_id": conversacion["id"],
        "mensaje_id": mensaje_asistente["id"], "persistido": True,
    }


async def nueva_conversacion(pasajero_id: str) -> None:
    repo = AsistenteRepository()
    activa = await repo.conversacion_activa_de_pasajero(pasajero_id)
    if activa:
        await repo.cerrar_conversacion(activa["id"])


async def historial_de_pasajero(pasajero_id: str) -> list[dict]:
    repo = AsistenteRepository()
    conversaciones = await repo.listar_conversaciones_de_pasajero(pasajero_id)
    salida = []
    for c in conversaciones:
        mensajes = await repo.mensajes_de_conversacion(c["id"])
        salida.append({**c, "mensajes": mensajes})
    return salida


class MensajeInvalido(Exception):
    pass


async def calificar_mensaje(usuario: dict, mensaje_id: str, calificacion: str) -> dict:
    repo = AsistenteRepository()
    mensaje = await repo.obtener_mensaje(mensaje_id)
    if mensaje is None or mensaje["rol"] != "asistente":
        raise MensajeInvalido("Solo se pueden calificar respuestas del asistente")
    actualizado = await repo.calificar_mensaje(mensaje_id, calificacion)
    await AuditService().insertar(
        "calificar_mensaje_ia", "mensajes_ia", usuario_id=usuario.get("id"), registro_id=mensaje_id,
        detalle={"calificacion": calificacion},
    )
    return actualizado


# ── backoffice (CU-T33, CU-T34) ─────────────────────────────────────
async def obtener_configuracion() -> dict:
    return await _configuracion()


async def actualizar_configuracion(
    usuario: dict, tono: str, temas_permitidos: list[str], respuestas_predefinidas: dict
) -> None:
    repo = AsistenteRepository()
    await repo.actualizar_config("asistente_ia.tono", tono, usuario["id"])
    await repo.actualizar_config("asistente_ia.temas_permitidos", ",".join(temas_permitidos), usuario["id"])
    await repo.actualizar_config(
        "asistente_ia.respuestas_predefinidas", json.dumps(respuestas_predefinidas, ensure_ascii=False), usuario["id"]
    )
    await AuditService().insertar("configurar_asistente_ia", "configuracion_sistema", usuario_id=usuario["id"])


_MARCADORES_SIN_RESPUESTA = (MENSAJE_SIN_CREDENCIAL, MENSAJE_SIN_CONTEXTO_VERIFICADO, "fuera de los temas")


async def reporte_consultas(desde_iso: str) -> dict:
    """RF-IA-T02 — temas más consultados (mensajes de rol `usuario`) y
    temas sin respuesta verificable (mensajes de `asistente` que
    coinciden con los mensajes canónicos de fallback — es la única forma
    de identificarlos sin un campo de estado propio en `mensajes_ia`)."""
    repo = AsistenteRepository()
    mensajes = await repo.mensajes_de_pasajero_en_periodo(desde_iso)

    consultas = [m["contenido"] for m in mensajes if m["rol"] == "usuario"]
    sin_respuesta = [
        m["contenido"] for i, m in enumerate(mensajes)
        if m["rol"] == "usuario"
        and i + 1 < len(mensajes)
        and mensajes[i + 1]["rol"] == "asistente"
        and mensajes[i + 1]["conversacion_id"] == m["conversacion_id"]
        and any(marcador in mensajes[i + 1]["contenido"] for marcador in _MARCADORES_SIN_RESPUESTA)
    ]
    return {"total_consultas": len(consultas), "consultas": consultas[-50:], "sin_respuesta": sin_respuesta[-50:]}
