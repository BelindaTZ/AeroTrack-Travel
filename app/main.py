from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from fastapi.responses import JSONResponse

from app.seguridad.router_auditoria import router as seguridad_auditoria_router
from app.seguridad.router_auth import router as seguridad_auth_router
from app.seguridad.router_password import router as seguridad_password_router
from app.seguridad.router_perfil import router as seguridad_perfil_router
from app.seguridad.router_registro import router as seguridad_registro_router
from app.seguridad.router_roles import router as seguridad_roles_router
from app.seguridad.router_usuarios import router as seguridad_usuarios_router
from app.seguridad.services.rbac_service import AccesoDenegado
from app.seguridad.services.session_service import SesionExpirada

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


@app.exception_handler(SesionExpirada)
async def sesion_expirada_handler(request: Request, exc: SesionExpirada) -> RedirectResponse:
    location = "/login"
    if exc.next_path:
        location += f"?next={exc.next_path}"
    return RedirectResponse(location, status_code=303)


@app.exception_handler(AccesoDenegado)
async def acceso_denegado_handler(request: Request, exc: AccesoDenegado) -> JSONResponse:
    # RF-SEG-013: el bloqueo ocurre antes de tocar datos. Comunicación visual
    # explícita (REG-J6) se implementa en las plantillas del backoffice
    # (Fase 5/6); esta respuesta cubre el contrato para cualquier caller.
    return JSONResponse(
        status_code=403,
        content={"detail": f"Sin permiso para {exc.modulo}" + (f".{exc.tabla}" if exc.tabla else "")},
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/")
async def raiz() -> RedirectResponse:
    # Sin una landing page propia todavía (fuera de alcance de Seguridad):
    # el punto de entrada por defecto es login, el camino feliz documentado
    # en seguridad-spec.md.
    return RedirectResponse("/login", status_code=303)
