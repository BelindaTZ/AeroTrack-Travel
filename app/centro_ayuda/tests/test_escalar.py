"""RF-AYU-004 (CU-O100) — escalar caso a agente humano vía email.

El envío real usa credenciales OAuth de Gmail reales (mismo criterio que
`app/disrupciones/tests/test_api_estado_vuelo.py` con `NotificationSenderFalso`)
— `escalar_caso()` (el servicio) se prueba directo con un sender falso para
no disparar un email real en cada corrida de tests; el router solo se
prueba por HTTP en los caminos que NUNCA llegan a enviar (sin sesión, sin
perfil de pasajero)."""

from app.centro_ayuda.integrations.escalacion_sender import EscalacionSender
from app.centro_ayuda.services.centro_ayuda_service import escalar_caso
from app.shared import minio_operational_client as moc


class EscalacionSenderFalso(EscalacionSender):
    def __init__(self, thread_id: str | None = "thread-falso-123"):
        self.thread_id = thread_id
        self.enviados: list[dict] = []

    async def enviar(self, email_pasajero: str, asunto: str, cuerpo: str) -> str | None:
        self.enviados.append({"email_pasajero": email_pasajero, "asunto": asunto, "cuerpo": cuerpo})
        return self.thread_id


async def test_escalar_caso_crea_registro_y_guarda_thread_id(pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    sender = EscalacionSenderFalso(thread_id="thread-abc")

    caso = await escalar_caso(usuario, pasajero["id"], "No encuentro mi reserva", "Ayuda porfa", sender)

    assert caso["estado"] == "abierto"
    assert caso["gmail_thread_id"] == "thread-abc"
    assert len(sender.enviados) == 1
    assert sender.enviados[0]["email_pasajero"] == usuario["email"]

    await moc.eliminar("casos_escalados", caso["id"])


async def test_escalar_caso_se_crea_aunque_falle_el_envio(pasajero_factory):
    usuario, pasajero = await pasajero_factory()
    sender = EscalacionSenderFalso(thread_id=None)

    caso = await escalar_caso(usuario, pasajero["id"], "Asunto", "Mensaje", sender)

    assert caso["estado"] == "abierto"
    assert not caso.get("gmail_thread_id")

    await moc.eliminar("casos_escalados", caso["id"])


async def test_escalar_requiere_sesion(client):
    resp = await client.post("/ayuda/escalar", data={"asunto": "x", "mensaje": "y"})
    assert resp.status_code in (303, 307)
    assert "/login" in resp.headers["location"]


async def test_escalar_sin_perfil_pasajero_redirige_sin_enviar(admin_client):
    """Un usuario sin `pasajeros` vinculado (ej. Administrador) no puede
    escalar — se detiene ANTES de llamar a `escalar_caso`/Gmail."""
    resp = await admin_client.post("/ayuda/escalar", data={"asunto": "x", "mensaje": "y"})
    assert resp.status_code == 303
    assert "Solo%20cuentas%20de%20pasajero" in resp.headers["location"]
