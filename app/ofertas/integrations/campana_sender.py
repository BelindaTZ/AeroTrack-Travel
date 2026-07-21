"""RF-OFE-T02 (CU-T31) — única puerta al envío real de campañas por
SendGrid. `configuracion_sistema` no tiene ninguna credencial `sendgrid.*`
sembrada (confirmado — no hay ni siquiera un placeholder, a diferencia de
`smtp.host`) — mismo criterio que `app/disrupciones/integrations/
notification_sender.py` aplica al canal SMS: **nunca se simula un envío
que no puede salir de verdad**. `enviar()` lanza `CredencialNoConfigurada`
en vez de fingir éxito; el router la traduce en un rechazo explícito, no
en una campaña marcada `enviada` sin haber salido nada."""

import abc

from app.shared.pocketbase_client import get_pocketbase_client


class CredencialNoConfigurada(Exception):
    pass


class CampanaSender(abc.ABC):
    @abc.abstractmethod
    async def enviar(self, destinatarios: list[str], asunto: str, plantilla: str) -> int:
        """Retorna la cantidad de envíos confirmados. Lanza
        `CredencialNoConfigurada` si no hay credencial real utilizable."""


class SendGridCampanaSender(CampanaSender):
    async def enviar(self, destinatarios: list[str], asunto: str, plantilla: str) -> int:
        client = get_pocketbase_client()
        api_key = await client.get_first("configuracion_sistema", 'clave="sendgrid.api_key"')
        if api_key is None or not api_key.get("valor"):
            raise CredencialNoConfigurada(
                "configuracion_sistema.sendgrid.api_key no está sembrado — no hay credencial real de SendGrid"
            )

        # No implementado más allá de este punto: sin credencial real
        # sembrada nunca se llegó a ejercitar el POST real a la API de
        # SendGrid — se deja el punto de extensión explícito en vez de
        # simular la llamada HTTP.
        raise CredencialNoConfigurada("Envío real de SendGrid no implementado — falta credencial")
