"""RF-AUT-001,002,003 (CU-O61,O62,O63) — buscar autos disponibles por
ciudad/fechas, ver detalle y filtrar resultados (instantáneo, REG-J9)."""

from fastapi import APIRouter, Depends, Request

from app.autos.repositories.autos_repo import AutosRepository
from app.autos.schemas import AutoBusquedaOut
from app.seguridad.services.session_service import usuario_opcional
from app.shared.busqueda_reciente import registrar_busqueda_reciente
from app.shared.templating import templates

router = APIRouter(prefix="/autos")


def _filtrar(autos: list[dict], categoria: str, transmision: str, precio_max: float | None) -> list[dict]:
    resultado = autos
    if categoria:
        resultado = [a for a in resultado if a.get("categoria") == categoria]
    if transmision:
        resultado = [a for a in resultado if a.get("transmision") == transmision]
    if precio_max is not None:
        resultado = [a for a in resultado if a.get("precio_dia") is not None and a["precio_dia"] <= precio_max]
    return resultado


async def _formulario_vacio(request: Request, usuario: dict | None, **filtros_extra) -> object:
    repo = AutosRepository()
    ciudades = await repo.ciudades_disponibles()
    filtros = {"ciudad": "", "recogida": "", "devolucion": "", "categoria": "", "transmision": "", "precio_max": ""}
    filtros.update(filtros_extra)
    return templates.TemplateResponse(
        request, "buscar_autos.html", {"resultados": None, "ciudades": ciudades, "filtros": filtros, "usuario": usuario}
    )


@router.get("/buscar")
async def buscar(
    request: Request,
    ciudad: str | None = None,
    recogida: str | None = None,
    devolucion: str | None = None,
    categoria: str = "",
    transmision: str = "",
    precio_max: float | None = None,
    usuario: dict | None = Depends(usuario_opcional),
):
    if not ciudad:
        return await _formulario_vacio(request, usuario, categoria=categoria, transmision=transmision, precio_max=precio_max or "")

    await registrar_busqueda_reciente(
        usuario, "auto", {"ciudad": ciudad, "recogida": recogida or "", "devolucion": devolucion or ""}
    )
    repo = AutosRepository()
    autos = await repo.buscar_por_ciudad(ciudad)

    categorias = sorted({a["categoria"] for a in autos if a.get("categoria")})
    transmisiones = sorted({a["transmision"] for a in autos if a.get("transmision")})

    autos = _filtrar(autos, categoria, transmision, precio_max)
    resultados = [
        AutoBusquedaOut(
            id=a["id"],
            modelo=a.get("modelo") or a.get("categoria") or "Vehículo",
            categoria=a.get("categoria") or "",
            transmision=a.get("transmision"),
            proveedor_agregador=a["proveedor_agregador"],
            ciudad_recogida=a["ciudad_recogida"],
            precio_dia=a["precio_dia"],
            moneda=a.get("moneda") or "USD",
            modalidad_pago_disponible=a.get("modalidad_pago_disponible"),
        )
        for a in autos
    ]
    resultados.sort(key=lambda r: r.precio_dia)

    ciudades = await repo.ciudades_disponibles()

    return templates.TemplateResponse(
        request,
        "buscar_autos.html",
        {
            "resultados": resultados,
            "ciudades": ciudades,
            "categorias": categorias,
            "transmisiones": transmisiones,
            "filtros": {
                "ciudad": ciudad, "recogida": recogida or "", "devolucion": devolucion or "",
                "categoria": categoria, "transmision": transmision, "precio_max": precio_max or "",
            },
            "usuario": usuario,
        },
    )


@router.get("/{auto_id}")
async def detalle(request: Request, auto_id: str, usuario: dict | None = Depends(usuario_opcional)):
    repo = AutosRepository()
    auto = await repo.obtener_auto(auto_id)
    if auto is None:
        return templates.TemplateResponse(request, "detalle_auto.html", {"auto": None, "usuario": usuario}, status_code=404)

    return templates.TemplateResponse(request, "detalle_auto.html", {"auto": auto, "usuario": usuario})
