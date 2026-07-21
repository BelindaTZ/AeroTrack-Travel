from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi.responses import JSONResponse

from app.shared.nav import nav_context
from app.shared.templating import templates
from app.seguridad.services.session_service import usuario_opcional
from app.vuelos.repositories.dims_reader import resolver_aeropuerto
from app.vuelos.repositories.vuelos_repo import VuelosRepository
from app.seguridad.router_auditoria import router as seguridad_auditoria_router
from app.seguridad.router_auth import router as seguridad_auth_router
from app.seguridad.router_password import router as seguridad_password_router
from app.seguridad.router_perfil import router as seguridad_perfil_router
from app.seguridad.router_registro import router as seguridad_registro_router
from app.seguridad.router_roles import router as seguridad_roles_router
from app.seguridad.router_usuarios import router as seguridad_usuarios_router
from app.seguridad.services.rbac_service import AccesoDenegado
from app.seguridad.services.session_service import SesionExpirada
from app.vuelos.router_backoffice import router as vuelos_backoffice_router
from app.vuelos.router_busqueda import router as vuelos_busqueda_router
from app.reservas.router_alertas import router as reservas_alertas_router
from app.reservas.router_backoffice import router as reservas_backoffice_router
from app.reservas.router_interno import router as reservas_interno_router
from app.reservas.router_reservas import router as reservas_router
from app.facturacion.router_backoffice import router as facturacion_backoffice_router
from app.facturacion.router_documentos import router as facturacion_documentos_router
from app.facturacion.router_interno import router as facturacion_interno_router
from app.facturacion.router_pagos import router as facturacion_pagos_router
from app.pasajeros.router_backoffice import router as pasajeros_backoffice_router
from app.pasajeros.router_contacto import router as pasajeros_contacto_router
from app.pasajeros.router_historial import router as pasajeros_historial_router
from app.disrupciones.router_interno import router as disrupciones_interno_router
from app.disrupciones.router_interno import router_notificaciones as disrupciones_notificaciones_interno_router
from app.disrupciones.router_notificaciones import router as disrupciones_notificaciones_router
from app.integraciones.router_bitacora import router as integraciones_bitacora_router
from app.integraciones.router_fuentes import router as integraciones_fuentes_router
from app.hoteles.router_interno import router as hoteles_interno_router
from app.hoteles.router_busqueda import router as hoteles_busqueda_router
from app.autos.router_interno import router as autos_interno_router
from app.autos.router_busqueda import router as autos_busqueda_router
from app.actividades.router_interno import router as actividades_interno_router
from app.actividades.router_busqueda import router as actividades_busqueda_router
from app.cruceros.router_interno import router as cruceros_interno_router
from app.cruceros.router_busqueda import router as cruceros_busqueda_router
from app.carrito.router_carrito import router as carrito_router
from app.carrito.router_checkout import router as carrito_checkout_router
from app.carrito.router_vista import router as carrito_vista_router
from app.paquetes.router_construccion import router as paquetes_construccion_router
from app.paquetes.router_resumen import router as paquetes_resumen_router
from app.cuenta.router_mis_viajes import router as cuenta_mis_viajes_router
from app.cuenta.router_favoritos import router as cuenta_favoritos_router
from app.cuenta.router_viajes_personalizados import router as cuenta_viajes_personalizados_router
from app.cuenta.router_busquedas import router as cuenta_busquedas_router
from app.cuenta.router_puntos import router as cuenta_puntos_router
from app.centro_ayuda.router_escalar import router as centro_ayuda_escalar_router
from app.centro_ayuda.router_ayuda import router as centro_ayuda_ayuda_router
from app.centro_ayuda.router_backoffice import router as centro_ayuda_backoffice_router
from app.ofertas.router_cupon import router as ofertas_cupon_router
from app.ofertas.router_ofertas import router as ofertas_ofertas_router
from app.ofertas.router_backoffice import router as ofertas_backoffice_router
from app.asistente_ia.router_conversacion import router as asistente_conversacion_router
from app.asistente_ia.router_backoffice import router as asistente_backoffice_router

BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI(title="AeroTrack Travel")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "public")), name="static")

app.include_router(seguridad_auth_router)
app.include_router(seguridad_password_router)
app.include_router(seguridad_perfil_router)
app.include_router(seguridad_registro_router)
app.include_router(seguridad_usuarios_router)
app.include_router(seguridad_roles_router)
app.include_router(seguridad_auditoria_router)
app.include_router(vuelos_busqueda_router)
app.include_router(vuelos_backoffice_router)
app.include_router(reservas_router)
app.include_router(reservas_backoffice_router)
app.include_router(reservas_interno_router)
app.include_router(reservas_alertas_router)
app.include_router(facturacion_pagos_router)
app.include_router(facturacion_documentos_router)
app.include_router(facturacion_interno_router)
app.include_router(facturacion_backoffice_router)
app.include_router(pasajeros_backoffice_router)
app.include_router(pasajeros_contacto_router)
app.include_router(pasajeros_historial_router)
app.include_router(disrupciones_interno_router)
app.include_router(disrupciones_notificaciones_interno_router)
app.include_router(disrupciones_notificaciones_router)
app.include_router(integraciones_fuentes_router)
app.include_router(integraciones_bitacora_router)
app.include_router(hoteles_interno_router)
app.include_router(hoteles_busqueda_router)
app.include_router(autos_interno_router)
app.include_router(autos_busqueda_router)
app.include_router(actividades_interno_router)
app.include_router(actividades_busqueda_router)
app.include_router(cruceros_interno_router)
app.include_router(cruceros_busqueda_router)
app.include_router(carrito_router)
app.include_router(carrito_checkout_router)
app.include_router(carrito_vista_router)
app.include_router(paquetes_construccion_router)
app.include_router(paquetes_resumen_router)
app.include_router(cuenta_mis_viajes_router)
app.include_router(cuenta_favoritos_router)
app.include_router(cuenta_viajes_personalizados_router)
app.include_router(cuenta_busquedas_router)
app.include_router(cuenta_puntos_router)
app.include_router(centro_ayuda_escalar_router)
app.include_router(centro_ayuda_ayuda_router)
app.include_router(centro_ayuda_backoffice_router)
app.include_router(ofertas_cupon_router)
app.include_router(ofertas_ofertas_router)
app.include_router(ofertas_backoffice_router)
app.include_router(asistente_conversacion_router)
app.include_router(asistente_backoffice_router)


@app.exception_handler(SesionExpirada)
async def sesion_expirada_handler(request: Request, exc: SesionExpirada) -> RedirectResponse:
    location = "/login"
    if exc.next_path:
        location += f"?next={exc.next_path}"
    return RedirectResponse(location, status_code=303)


@app.exception_handler(AccesoDenegado)
async def acceso_denegado_handler(request: Request, exc: AccesoDenegado):
    # RF-SEG-013: el bloqueo ocurre antes de tocar datos. Los llamadores por
    # fetch() (JS de las pantallas de backoffice) piden JSON explícitamente
    # (Accept: application/json); cualquier otra solicitud es una navegación
    # de página completa y debe recibir una página legible, no JSON crudo
    # (REG-J6/J7 — el bloqueo se comunica de forma explícita, no como texto
    # sin formato).
    if "application/json" in request.headers.get("accept", ""):
        return JSONResponse(
            status_code=403,
            content={"detail": f"Sin permiso para {exc.modulo}" + (f".{exc.tabla}" if exc.tabla else "")},
        )

    usuario = getattr(request.state, "usuario", None)
    contexto = {"modulo": exc.modulo, "tabla": exc.tabla}
    if usuario:
        contexto.update(await nav_context(usuario))
    return templates.TemplateResponse(request, "acceso_denegado.html", contexto, status_code=403)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def raiz(request: Request, usuario: dict | None = Depends(usuario_opcional)):
    # Un administrador que llega a "/" (ej. logo en el topbar del backoffice)
    # va a su panel — la landing de abajo es para pasajero/invitado, mismo
    # criterio que login_submit() en router_auth.py.
    if usuario and usuario.get("tipo_actor") == "administrador":
        return RedirectResponse("/admin/usuarios", status_code=303)

    repo = VuelosRepository()
    destinos = await repo.destinos_populares(limite=6)
    destinos_out = [
        {**d, "legible": await resolver_aeropuerto(d["codigo"])} for d in destinos
    ]
    return templates.TemplateResponse(
        request, "inicio.html", {"usuario": usuario, "destinos_populares": destinos_out}
    )
