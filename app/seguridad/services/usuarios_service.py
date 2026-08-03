"""RF-SEG-008 — alta de pasajero (autoservicio). RF-SEG-009 se añade en Fase 5."""

import secrets
from datetime import date

from app.pasajeros.repositories.pasajeros_repo import PasajerosRepository
from app.seguridad.repositories.seguridad_repo import SeguridadRepository
from app.seguridad.services.password_service import PasswordService
from app.shared.pocketbase_client import PocketBaseError


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
        canal_registro: str = "autoservicio_web",
    ) -> dict:
        # RN-SEG-006: precheck para dar el mensaje específico de RF-SEG-008
        # en vez del error genérico de PocketBase; el índice único en
        # `usuarios.email` es el resguardo real contra condiciones de carrera.
        if await self._repo.get_usuario_by_email(email) is not None:
            raise CorreoDuplicado()

        rol_pasajero = await self._repo._client.get_first("roles", 'nombre="Pasajero"')
        assert rol_pasajero is not None, "scripts/seed_seguridad.py debe correrse antes de operar"

        try:
            usuario = await self._repo.create_usuario(
                {
                    "email": email,
                    "password": password,
                    "passwordConfirm": password,
                    "nombre_completo": nombre_completo,
                    "rol_id": rol_pasajero["id"],
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
            # CU-T37 — reporte de captación por canal. Antes solo se sembraba
            # "autoservicio_web" (único caller era el registro público);
            # ahora también lo usa el alta manual de backoffice (WP-01,
            # 2026-07-31), que pasa "agente_call_center" o "presencial_counter".
            "canal_registro": canal_registro,
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
            await PasajerosRepository().crear_pasajero(pasajero_data)
        except Exception:
            await self._repo._client.delete_record("usuarios", usuario["id"])
            raise

        return usuario

    # ── RF-SEG-009 — alta manual desde /admin/usuarios. A diferencia de
    # `crear_pasajero` (autoservicio, RF-SEG-008), acá el Administrador
    # elige el rol directamente — qué panel le corresponde (`tipo_actor` de
    # antes) se deriva de `rol_id` (`roles.tipo_panel`), ya no se pide
    # aparte. Incluye poder asignar un rol de autoservicio para el alta
    # manual de un cliente sin self-service (ej. reserva telefónica sin que
    # el pasajero llegue a registrarse solo); esas cuentas no aparecen en
    # `listar_usuarios_internos` (ver abajo), igual que las autoservicio.

    async def crear_usuario_interno(
        self, nombre_completo: str, email: str, password: str, rol_id: str
    ) -> dict:
        if await self._repo.get_usuario_by_email(email) is not None:
            raise CorreoDuplicado()
        try:
            return await self._repo.create_usuario(
                {
                    "email": email,
                    "password": password,
                    "passwordConfirm": password,
                    "nombre_completo": nombre_completo,
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

    async def cerrar_sesiones_activas(self, usuario_id: str) -> None:
        """CU-T02 — fuerza el cierre de toda sesión activa de este usuario,
        sin esperar a que expire el token por su cuenta. PocketBase no tiene
        una blocklist de tokens propia: el mecanismo real es rotar la
        contraseña (verificado en vivo — un PATCH de `password` invalida
        de inmediato cualquier token ya emitido para ese registro; PATCHear
        el campo `tokenKey` directamente NO lo invalida en esta versión).
        La cuenta queda con una contraseña aleatoria que nadie conoce — el
        usuario vuelve a entrar recién cuando un Administrador le envíe un
        enlace de recuperación (`resetear_password`, acción separada)."""
        nueva = secrets.token_urlsafe(24)
        await self._repo.update_usuario(usuario_id, {"password": nueva, "passwordConfirm": nueva})

    async def listar_usuarios_internos(
        self,
        nombre: str | None = None,
        email: str | None = None,
        rol_id: str | None = None,
        activo: bool | None = None,
    ) -> list[dict]:
        # "Interno" = tiene un rol de panel backoffice (antes era
        # tipo_actor="agente" || tipo_actor="administrador"; ahora se deriva
        # de `roles.tipo_panel`, no de un campo propio de `usuarios`).
        roles_backoffice = await self._repo._client.list_records(
            "roles", {"filter": 'tipo_panel="backoffice"', "perPage": 200}
        )
        rol_ids = [r["id"] for r in roles_backoffice["items"]]
        if not rol_ids:
            return []
        condiciones = ["(" + " || ".join(f'rol_id="{rid}"' for rid in rol_ids) + ")"]
        if nombre:
            safe = nombre.replace('"', '\\"')
            condiciones.append(f'nombre_completo~"{safe}"')
        if email:
            safe = email.replace('"', '\\"')
            condiciones.append(f'email~"{safe}"')
        if rol_id:
            condiciones.append(f'rol_id="{rol_id}"')
        if activo is not None:
            condiciones.append(f'activo={"true" if activo else "false"}')

        result = await self._repo.list_usuarios(
            {"filter": " && ".join(condiciones), "perPage": 200, "sort": "nombre_completo"}
        )
        return result["items"]
