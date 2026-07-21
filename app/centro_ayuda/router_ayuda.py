"""RF-AYU-001,002,003 (CU-O97,O98,O99) — buscar/ver artículos de ayuda
(público, sesión opcional) y calificar utilidad (anónimo permitido)."""

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from app.centro_ayuda.repositories.centro_ayuda_repo import CentroAyudaRepository
from app.centro_ayuda.services.centro_ayuda_service import calificar_articulo
from app.reservas.repositories.reservas_repo import ReservasRepository
from app.seguridad.services.session_service import usuario_opcional
from app.shared.templating import templates

router = APIRouter(prefix="/ayuda")


@router.get("/buscar")
async def buscar(
    request: Request,
    q: str | None = None,
    categoria: str | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    repo = CentroAyudaRepository()
    articulos = await repo.buscar_articulos(q, categoria) if (q or categoria) else []
    categorias = await repo.categorias_disponibles()
    return templates.TemplateResponse(
        request, "buscar_ayuda.html",
        {"usuario": usuario, "articulos": articulos, "categorias": categorias, "q": q or "", "categoria": categoria or ""},
    )


@router.get("/{articulo_id}")
async def detalle(request: Request, articulo_id: str, usuario: dict | None = Depends(usuario_opcional)):
    repo = CentroAyudaRepository()
    articulo = await repo.obtener_articulo(articulo_id)
    if articulo is None or not articulo.get("activo", True):
        return templates.TemplateResponse(
            request, "detalle_articulo.html", {"usuario": usuario, "articulo": None}, status_code=404
        )

    calificaciones = await repo.calificaciones_de_articulo(articulo_id)
    arriba = sum(1 for c in calificaciones if c["util"] == "arriba")
    abajo = sum(1 for c in calificaciones if c["util"] == "abajo")
    return templates.TemplateResponse(
        request, "detalle_articulo.html",
        {"usuario": usuario, "articulo": articulo, "calificaciones_arriba": arriba, "calificaciones_abajo": abajo},
    )


@router.post("/{articulo_id}/calificar")
async def calificar(articulo_id: str, util: str = Form(...), usuario: dict | None = Depends(usuario_opcional)):
    pasajero_id = None
    if usuario and usuario.get("tipo_actor") == "pasajero":
        pasajero = await ReservasRepository().pasajero_de_usuario(usuario["id"])
        pasajero_id = pasajero["id"] if pasajero else None

    if util not in ("arriba", "abajo"):
        return RedirectResponse(f"/ayuda/{articulo_id}?mensaje=Calificación inválida", status_code=303)

    await calificar_articulo(articulo_id, pasajero_id, util)
    return RedirectResponse(f"/ayuda/{articulo_id}?mensaje=Gracias por tu calificación", status_code=303)
