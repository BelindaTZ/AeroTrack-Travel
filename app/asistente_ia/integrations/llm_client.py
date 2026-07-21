"""RF-IA-003/004 — única puerta al LLM real (Groq primero, Gemini como
respaldo — mismo orden que describe `fuentes_datos_externas` para ambos:
"modelo primario o de respaldo, según config"). **Sin ninguna credencial
real sembrada en `configuracion_sistema`** (ni `groq.api_key` ni
`gemini.api_key`, confirmado — a diferencia de Gmail, que sí tiene
credenciales con scope insuficiente) — `generar()` rechaza explícitamente
con `CredencialNoConfigurada` en vez de fingir una respuesta. Mismo
criterio que `app/ofertas/integrations/campana_sender.py` (SendGrid) y
`app/disrupciones/integrations/notification_sender.py` (canal SMS)."""

import abc

import httpx

from app.shared.pocketbase_client import get_pocketbase_client

_GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
_GEMINI_URL_TEMPLATE = "https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"


class CredencialNoConfigurada(Exception):
    pass


class LLMClient(abc.ABC):
    @abc.abstractmethod
    async def generar(self, system_prompt: str, historial: list[dict], mensaje: str) -> str:
        """`historial` es `[{"rol": "usuario"|"asistente", "contenido": str}, ...]`.
        Retorna el texto de la respuesta. Lanza `CredencialNoConfigurada`
        si no hay ninguna credencial real utilizable (Groq ni Gemini)."""


class GroqGeminiLLMClient(LLMClient):
    async def generar(self, system_prompt: str, historial: list[dict], mensaje: str) -> str:
        client = get_pocketbase_client()
        groq_key = await client.get_first("configuracion_sistema", 'clave="groq.api_key"')
        if groq_key and groq_key.get("valor"):
            return await self._generar_groq(groq_key["valor"], system_prompt, historial, mensaje)

        gemini_key = await client.get_first("configuracion_sistema", 'clave="gemini.api_key"')
        if gemini_key and gemini_key.get("valor"):
            return await self._generar_gemini(gemini_key["valor"], system_prompt, historial, mensaje)

        raise CredencialNoConfigurada(
            "Ni groq.api_key ni gemini.api_key están sembrados en configuracion_sistema"
        )

    async def _generar_groq(self, api_key: str, system_prompt: str, historial: list[dict], mensaje: str) -> str:
        mensajes = [{"role": "system", "content": system_prompt}]
        for h in historial:
            mensajes.append({"role": "assistant" if h["rol"] == "asistente" else "user", "content": h["contenido"]})
        mensajes.append({"role": "user", "content": mensaje})

        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.post(
                _GROQ_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                json={"model": "llama-3.3-70b-versatile", "messages": mensajes, "temperature": 0.3},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]

    async def _generar_gemini(self, api_key: str, system_prompt: str, historial: list[dict], mensaje: str) -> str:
        contents = []
        for h in historial:
            contents.append({"role": "model" if h["rol"] == "asistente" else "user", "parts": [{"text": h["contenido"]}]})
        contents.append({"role": "user", "parts": [{"text": mensaje}]})

        url = _GEMINI_URL_TEMPLATE.format(modelo="gemini-1.5-flash")
        async with httpx.AsyncClient(timeout=20) as c:
            resp = await c.post(
                url,
                params={"key": api_key},
                json={"system_instruction": {"parts": [{"text": system_prompt}]}, "contents": contents},
            )
            resp.raise_for_status()
            return resp.json()["candidates"][0]["content"]["parts"][0]["text"]
