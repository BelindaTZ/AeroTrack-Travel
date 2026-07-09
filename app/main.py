from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi.responses import JSONResponse

from app.shared.nav import nav_context
from app.shared.templating import templates
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
async def raiz() -> RedirectResponse:
    # Camino feliz de un pasajero (HU-VUE-01): buscar vuelos no requiere
    # sesión. Sin landing page de marketing propia todavía — el buscador es
    # el punto de entrada real del producto.
    return RedirectResponse("/vuelos/buscar", status_code=303)
