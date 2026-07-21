"""RF-IA-001..006, RN-IA-001/002/003 (REG-H1) — conversación, contexto
verificado, permisos entre pasajeros, calificación."""

from app.asistente_ia.integrations.llm_client import CredencialNoConfigurada, LLMClient
from app.asistente_ia.services.asistente_service import (
    MENSAJE_SIN_CONTEXTO_VERIFICADO,
    MensajeInvalido,
    calificar_mensaje,
    conversar,
    historial_de_pasajero,
    nueva_conversacion,
)


class LLMClientFalso(LLMClient):
    def __init__(self, respuesta: str = "Respuesta generada de prueba"):
        self.respuesta = respuesta
        self.llamado_con: list[dict] = []

    async def generar(self, system_prompt: str, historial: list, mensaje: str) -> str:
        self.llamado_con.append({"system_prompt": system_prompt, "mensaje": mensaje})
        return self.respuesta


class LLMClientSinCredencial(LLMClient):
    async def generar(self, system_prompt: str, historial: list, mensaje: str) -> str:
        raise CredencialNoConfigurada("sin credencial de prueba")


async def test_conversar_anonimo_no_persiste(pb):
    resultado = await conversar(None, None, "hola, tengo una pregunta general", LLMClientFalso())
    assert resultado["persistido"] is False
    assert resultado["conversacion_id"] is None
    assert resultado["respuesta"]


async def test_conversar_pasajero_persiste_conversacion_y_mensajes(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()

    resultado = await conversar(usuario, pasajero["id"], "cuéntame algo sobre mi viaje", LLMClientFalso("Hola, ¿en qué te ayudo?"))
    assert resultado["persistido"] is True
    assert resultado["conversacion_id"]

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    assert mensajes["totalItems"] == 2  # usuario + asistente
    roles = {m["rol"] for m in mensajes["items"]}
    assert roles == {"usuario", "asistente"}

    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_segundo_mensaje_reutiliza_conversacion_activa(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()

    r1 = await conversar(usuario, pasajero["id"], "primera pregunta", LLMClientFalso())
    r2 = await conversar(usuario, pasajero["id"], "segunda pregunta", LLMClientFalso())
    assert r1["conversacion_id"] == r2["conversacion_id"]

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{r1["conversacion_id"]}"'})
    assert mensajes["totalItems"] == 4
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", r1["conversacion_id"])


async def test_reserva_propia_responde_con_plantilla_sin_llamar_al_llm(
    pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory
):
    """RF-IA-004 — el hecho estructurado (reserva verificada) se responde
    por plantilla determinista; el LLM (que fallaría, sin credencial) ni
    siquiera se invoca para este camino."""
    usuario, pasajero = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva = await reserva_factory(pasajero["id"], vuelo["id"], tarifa["id"], total_pagar=250.0)

    llm = LLMClientSinCredencial()
    resultado = await conversar(usuario, pasajero["id"], f"¿cómo va mi reserva {reserva['codigo_reserva']}?", llm)

    assert reserva["codigo_reserva"] in resultado["respuesta"]
    assert "250.00" in resultado["respuesta"]

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_reserva_ajena_nunca_se_expone(pb, pasajero_factory, vuelo_factory, tarifa_factory, reserva_factory):
    """REG-H1 "respeta los permisos del usuario que la invoca" — un
    pasajero preguntando por el código de reserva de OTRO pasajero nunca
    recibe esos datos, ni por plantilla ni citados por el LLM."""
    usuario_a, pasajero_a = await pasajero_factory()
    usuario_b, pasajero_b = await pasajero_factory()
    vuelo = await vuelo_factory()
    tarifa = await tarifa_factory(vuelo["id"])
    reserva_de_b = await reserva_factory(pasajero_b["id"], vuelo["id"], tarifa["id"])

    resultado = await conversar(
        usuario_a, pasajero_a["id"], f"dime el estado de la reserva {reserva_de_b['codigo_reserva']}",
        LLMClientSinCredencial(),
    )

    assert reserva_de_b["codigo_reserva"] not in resultado["respuesta"]
    assert resultado["respuesta"] == MENSAJE_SIN_CONTEXTO_VERIFICADO

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_sin_contexto_y_sin_credencial_ofrece_escalar(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resultado = await conversar(usuario, pasajero["id"], "pregunta genérica sin datos verificables", LLMClientSinCredencial())
    assert resultado["respuesta"] == MENSAJE_SIN_CONTEXTO_VERIFICADO
    assert "escal" in resultado["respuesta"].lower()

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_nueva_conversacion_cierra_activa_sin_borrar_historial(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    r1 = await conversar(usuario, pasajero["id"], "conversación uno", LLMClientFalso())

    await nueva_conversacion(pasajero["id"])

    conv_cerrada = await pb.get_record("conversaciones_ia", r1["conversacion_id"])
    assert conv_cerrada["activa"] is False

    r2 = await conversar(usuario, pasajero["id"], "conversación dos", LLMClientFalso())
    assert r2["conversacion_id"] != r1["conversacion_id"]

    historial = await historial_de_pasajero(pasajero["id"])
    assert len(historial) == 2  # ambas conversaciones siguen accesibles (RF-IA-005)

    for conv_id in (r1["conversacion_id"], r2["conversacion_id"]):
        mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{conv_id}"'})
        for m in mensajes["items"]:
            await pb.delete_record("mensajes_ia", m["id"])
        await pb.delete_record("conversaciones_ia", conv_id)


async def test_calificar_mensaje_asistente(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resultado = await conversar(usuario, pasajero["id"], "hola", LLMClientFalso())

    actualizado = await calificar_mensaje(usuario, resultado["mensaje_id"], "arriba")
    assert actualizado["calificacion"] == "arriba"

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_calificar_mensaje_de_usuario_se_rechaza(pb, pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    resultado = await conversar(usuario, pasajero["id"], "hola", LLMClientFalso())

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}" && rol="usuario"'})
    mensaje_usuario_id = mensajes["items"][0]["id"]

    try:
        await calificar_mensaje(usuario, mensaje_usuario_id, "arriba")
        assert False, "debía rechazar calificar un mensaje de rol usuario"
    except MensajeInvalido:
        pass

    todos = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in todos["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])


async def test_endpoint_historial_requiere_sesion(client):
    resp = await client.get("/asistente/historial")
    assert resp.status_code in (303, 307)


async def test_endpoint_conversar_anonimo_funciona(client):
    resp = await client.post("/asistente/conversar", data={"mensaje": "hola, consulta anónima"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["persistido"] is False
    assert data["respuesta"]
