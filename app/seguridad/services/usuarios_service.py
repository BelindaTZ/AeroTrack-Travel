"""RF-SEG-008 — alta de pasajero (autoservicio). RF-SEG-009 se añade en Fase 5."""

from datetime import date

from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.password_service import PasswordService
from app.shared.pocketbase_client import PocketBaseError, get_pocketbase_client


class CorreoDuplicado(Exception):
    pass


class UsuariosService:
    def __init__(self, repo: SeguridadRepository | None = None) -> None:
        self._repo = repo or SeguridadRepository()

    async def crear_pasajero(
        self,
        nombre_completo: str,
        email: str,
        password: str,
        fecha_nacimiento: date,
        telefono: str,
        genero: str | None = None,
        numero_documento: str | None = None,
        direccion_facturacion: str | None = None,
        contacto_emergencia: str | None = None,
    ) -> dict:
        # RN-SEG-006: precheck para dar el mensaje específico de RF-SEG-008
        # en vez del error genérico de PocketBase; el índice único en
        # `usuarios.email` es el resguardo real contra condiciones de carrera.
        if await self._repo.get_usuario_by_email(email) is not None:
            raise CorreoDuplicado()

        try:
            usuario = await self._repo.create_usuario(
                {
                    "email": email,
                    "password": password,
                    "passwordConfirm": password,
                    "nombre_completo": nombre_completo,
                    "tipo_actor": "pasajero",
                    "activo": True,
                    "emailVisibility": True,
                }
            )
        except PocketBaseError:
            raise CorreoDuplicado()

        # `pasajeros` es propiedad del módulo Pasajeros (plan.md de Seguridad,
        # sección Modelo de datos) — esta es la única escritura que Seguridad
        # hace ahí, exigida explícitamente por RF-SEG-008 para crear el
        # perfil extendido junto con la cuenta. PocketBase no ofrece
        # transacciones entre colecciones: si esta escritura falla, se
        # revierte manualmente el `usuarios` recién creado.
        pasajero_data: dict = {
            "usuario_id": usuario["id"],
            "fecha_nacimiento": fecha_nacimiento.isoformat(),
            "telefono": telefono,
        }
        if genero:
            pasajero_data["genero"] = genero
        if numero_documento:
            pasajero_data["numero_documento"] = numero_documento
        if direccion_facturacion:
            pasajero_data["direccion_facturacion"] = direccion_facturacion
        if contacto_emergencia:
            pasajero_data["contacto_emergencia"] = contacto_emergencia

        try:
            await get_pocketbase_client().create_record("pasajeros", pasajero_data)
        except PocketBaseError:
            await self._repo._client.delete_record("usuarios", usuario["id"])
            raise

        return usuario

    # ── RF-SEG-009 — backoffice de usuarios internos (Agente/Administrador) ─

    async def crear_usuario_interno(
        self, nombre_completo: str, email: str, password: str, tipo_actor: str, rol_id: str
    ) -> dict:
        if tipo_actor not in ("agente", "administrador"):
            raise ValueError("tipo_actor debe ser 'agente' o 'administrador'")
        if await self._repo.get_usuario_by_email(email) is not None:
            raise CorreoDuplicado()
        try:
            return await self._repo.create_usuario(
                {
                    "email": email,
                    "password": password,
                    "passwordConfirm": password,
                    "nombre_completo": nombre_completo,
                    "tipo_actor": tipo_actor,
                    "rol_id": rol_id,
                    "activo": True,
                    "emailVisibility": True,
                }
            )
        except PocketBaseError:
            raise CorreoDuplicado()

    async def editar_usuario_interno(
        self,
        usuario_id: str,
        nombre_completo: str | None = None,
        rol_id: str | None = None,
        activo: bool | None = None,
    ) -> dict:
        campos: dict = {}
        if nombre_completo is not None:
            campos["nombre_completo"] = nombre_completo
        if rol_id is not None:
            campos["rol_id"] = rol_id
        if activo is not None:
            campos["activo"] = activo
        return await self._repo.update_usuario(usuario_id, campos)

    async def resetear_password(self, usuario_id: str) -> str:
        """Genera un enlace de recuperación de un solo uso para un usuario
        interno, iniciado por un Administrador (p. ej. cuenta bloqueada sin
        acceso a autoservicio). Reutiliza el mismo mecanismo de token que
        RF-SEG-004 — nunca fija una contraseña en texto plano directamente."""
        return await PasswordService(self._repo).generar_token_recuperacion(usuario_id)

    async def listar_usuarios_internos(self) -> list[dict]:
        result = await self._repo.list_usuarios(
            {
                "filter": 'tipo_actor="agente" || tipo_actor="administrador"',
                "perPage": 200,
                "sort": "nombre_completo",
            }
        )
        return result["items"]
