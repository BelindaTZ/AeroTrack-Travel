"""RF-PAS-003, 004 / CU-O16 — Backoffice: buscar y gestionar pasajeros.

WP-01 (auditoría de WorkPanels, 2026-07-31) — panel CRUD completo: filtros,
paginación, y Crear/Editar/Ver/Eliminar por modal en la misma pantalla de
listado. La página de detalle histórica (`GET /backoffice/pasajeros/{id}`,
`detalle_pasajero.html`) y su PUT de solo-contacto quedan intactos para no
romper nada que ya la enlace — el flujo nuevo vive enteramente en
`buscar_pasajeros.html`.
"""

from datetime import date

from fastapi import APIRouter, Depends, Form, Query, Request
from fastapi.responses import JSONResponse

from app.pasajeros.services.pasajeros_service import (
    PasajeroConReservasActivas,
    PasajeroNoEncontrado,
    SinPermiso,
    TelefonoInvalido,
    TipoDocumentoInvalido,
    TIPOS_DOCUMENTO_VALIDOS,
    buscar_pasajeros_backoffice,
    crear_documento_viaje_backoffice,
    crear_pasajero_backoffice,
    documentos_de_pasajero,
    editar_contacto_backoffice,
    editar_pasajero_backoffice_completo,
    eliminar_documento_viaje_backoffice,
    eliminar_pasajero_backoffice,
    listar_pasajeros_reporte,
    obtener_detalle_pasajero,
)
from app.seguridad.services.password_service import PasswordDebil, PasswordService
from app.seguridad.services.rbac_service import requiere_permiso, tiene_permiso
from app.seguridad.services.usuarios_service import CorreoDuplicado
from app.shared.csv_export import csv_response
from app.shared.flash import redirect_con_mensaje
from app.shared.nav import nav_context
from app.shared.paginacion import paginar
from app.shared.templating import templates

router = APIRouter(prefix="/backoffice/pasajeros")

CANALES_REGISTRO = ["autoservicio_web", "agente_call_center", "presencial_counter", "sin_canal"]
GENEROS_VALIDOS = ["M", "F", "prefiero_no_decir"]


async def _rbac_ver(usuario: dict = Depends(requiere_permiso("pasajeros", "ver", "pasajeros"))):
    return usuario


async def _rbac_crear(usuario: dict = Depends(requiere_permiso("pasajeros", "crear", "pasajeros"))):
    return usuario


async def _rbac_editar(usuario: dict = Depends(requiere_permiso("pasajeros", "editar", "pasajeros"))):
    return usuario


async def _rbac_eliminar(usuario: dict = Depends(requiere_permiso("pasajeros", "eliminar", "pasajeros"))):
    return usuario


async def _reporte_pasajeros_filtrado(
    desde: str | None, hasta: str | None, destino: str | None,
    frecuencia_min: str | None, canal_registro: str | None,
) -> list[dict]:
    frecuencia_min_int = None
    if frecuencia_min:
        try:
            frecuencia_min_int = int(frecuencia_min)
        except ValueError:
            frecuencia_min_int = None

    return await listar_pasajeros_reporte(
        desde=desde or None, hasta=hasta or None, destino=destino or None,
        frecuencia_min=frecuencia_min_int, canal_registro=canal_registro or None,
    )


@router.get("/reporte")
async def reporte_pasajeros(
    request: Request,
    desde: str | None = None,
    hasta: str | None = None,
    destino: str | None = None,
    frecuencia_min: str | None = None,
    canal_registro: str | None = None,
    page: int = Query(1, ge=1),
    usuario: dict = Depends(_rbac_ver),
):
    """CU-T05 (exportar base con filtros) + CU-T37 (captación por canal),
    misma pantalla — comparten la misma consulta filtrada. IS-05 (auditoría
    de informes simples, sesión 2026-08-01) — paginación 25/página y
    columna `tiene_reserva` agregadas sobre este reporte ya existente."""
    filas = await _reporte_pasajeros_filtrado(desde, hasta, destino, frecuencia_min, canal_registro)

    por_canal: dict[str, int] = {}
    for f in filas:
        por_canal[f["canal_registro"]] = por_canal.get(f["canal_registro"], 0) + 1

    pagina = paginar(filas, page)

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "por_canal": sorted(por_canal.items(), key=lambda kv: kv[1], reverse=True),
            "canales": CANALES_REGISTRO,
            "filtros": {
                "desde": desde or "", "hasta": hasta or "", "destino": destino or "",
                "frecuencia_min": frecuencia_min or "", "canal_registro": canal_registro or "",
            },
        }
    )
    return templates.TemplateResponse(request, "backoffice/reporte_pasajeros.html", contexto)


@router.get("/reporte/exportar")
async def exportar_pasajeros(
    desde: str | None = None,
    hasta: str | None = None,
    destino: str | None = None,
    frecuencia_min: str | None = None,
    canal_registro: str | None = None,
    usuario: dict = Depends(_rbac_ver),
):
    filas = await _reporte_pasajeros_filtrado(desde, hasta, destino, frecuencia_min, canal_registro)
    return csv_response(
        filas,
        [
            ("nombre_completo", lambda f: f["nombre_completo"]),
            ("email", lambda f: f["email"]),
            ("fecha_registro", lambda f: f["fecha_registro"]),
            ("canal_registro", lambda f: f["canal_registro"]),
            ("num_reservas", lambda f: f["num_reservas"]),
            ("tiene_reserva", lambda f: "si" if f["num_reservas"] else "no"),
            ("destinos", lambda f: ",".join(f["destinos"])),
        ],
        "pasajeros.csv",
    )


@router.get("")
async def buscar_pasajeros(
    request: Request,
    nombre: str = Query(""),
    email: str = Query(""),
    documento: str = Query(""),
    telefono: str = Query(""),
    page: int = Query(1, ge=1),
    abrir: str = Query(""),
    pid: str = Query(""),
    usuario: dict = Depends(_rbac_ver),
):
    resultados = await buscar_pasajeros_backoffice(
        usuario, nombre=nombre or None, email=email or None, documento=documento or None,
        telefono=telefono or None, pasajero_id=pid or None,
    )
    pagina = paginar(resultados, page)
    # Documentos de viaje solo de las filas realmente mostradas (≤25), no de
    # todo el resultado filtrado — ver mini-sección dentro del modal Editar.
    for fila in pagina.items:
        fila["documentos"] = await documentos_de_pasajero(fila["id"])

    contexto = await nav_context(usuario)
    contexto.update(
        {
            "pagina": pagina,
            "filtros": {"nombre": nombre, "email": email, "documento": documento, "telefono": telefono},
            "generos": GENEROS_VALIDOS,
            "tipos_documento": sorted(TIPOS_DOCUMENTO_VALIDOS),
            # Orden propio (no el de CANALES_REGISTRO): un alta manual desde
            # este panel default a "agente_call_center", nunca a
            # "autoservicio_web" — ese valor implica que el pasajero se
            # registró solo, lo cual sería falso viniendo de acá.
            "canales_alta": ["agente_call_center", "presencial_counter", "autoservicio_web"],
            "abrir": abrir,
            # Agente tiene ver/crear/editar pero no eliminar (seed_seguridad.py)
            # — el botón se oculta en vez de mostrar una acción que el backend
            # va a rechazar de todos modos.
            "puede_eliminar": await tiene_permiso(usuario, "pasajeros", "eliminar"),
        }
    )
    return templates.TemplateResponse(request, "backoffice/buscar_pasajeros.html", contexto)


@router.post("")
async def crear_pasajero_endpoint(
    nombre_completo: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    fecha_nacimiento: date = Form(...),
    telefono: str = Form(...),
    genero: str | None = Form(None),
    numero_documento: str | None = Form(None),
    direccion_facturacion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
    canal_registro: str = Form("agente_call_center"),
    usuario: dict = Depends(_rbac_crear),
):
    try:
        await PasswordService().validar_fortaleza(password)
    except PasswordDebil as exc:
        return redirect_con_mensaje("/backoffice/pasajeros", exc.motivo, tipo="error")

    try:
        await crear_pasajero_backoffice(
            usuario,
            nombre_completo=nombre_completo,
            email=email,
            password=password,
            fecha_nacimiento=fecha_nacimiento,
            telefono=telefono,
            genero=genero or None,
            numero_documento=numero_documento or None,
            direccion_facturacion=direccion_facturacion or None,
            contacto_emergencia=contacto_emergencia or None,
            canal_registro=canal_registro,
        )
    except CorreoDuplicado:
        return redirect_con_mensaje("/backoffice/pasajeros", "Ya existe una cuenta con ese correo", tipo="error")
    except TelefonoInvalido as exc:
        return redirect_con_mensaje("/backoffice/pasajeros", str(exc), tipo="error")

    return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero creado")


@router.post("/{pasajero_id}/editar")
async def editar_pasajero_endpoint(
    pasajero_id: str,
    nombre_completo: str | None = Form(None),
    email: str | None = Form(None),
    telefono: str | None = Form(None),
    fecha_nacimiento: str | None = Form(None),
    genero: str | None = Form(None),
    numero_documento: str | None = Form(None),
    direccion_facturacion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
    usuario: dict = Depends(_rbac_editar),
):
    try:
        await editar_pasajero_backoffice_completo(
            usuario,
            pasajero_id,
            nombre_completo=nombre_completo or None,
            email=email or None,
            telefono=telefono or None,
            fecha_nacimiento=date.fromisoformat(fecha_nacimiento) if fecha_nacimiento else None,
            genero=genero or None,
            numero_documento=numero_documento or None,
            direccion_facturacion=direccion_facturacion or None,
            contacto_emergencia=contacto_emergencia or None,
        )
    except PasajeroNoEncontrado:
        return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero no encontrado", tipo="error")
    except CorreoDuplicado:
        return redirect_con_mensaje("/backoffice/pasajeros", "Ya existe otra cuenta con ese correo", tipo="error")
    except TelefonoInvalido as exc:
        return redirect_con_mensaje("/backoffice/pasajeros", str(exc), tipo="error")

    return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero actualizado")


@router.post("/{pasajero_id}/eliminar")
async def eliminar_pasajero_endpoint(
    pasajero_id: str,
    usuario: dict = Depends(_rbac_eliminar),
):
    try:
        await eliminar_pasajero_backoffice(usuario, pasajero_id)
    except PasajeroNoEncontrado:
        return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero no encontrado", tipo="error")
    except PasajeroConReservasActivas as exc:
        return redirect_con_mensaje(
            "/backoffice/pasajeros",
            f"No se puede eliminar: tiene {exc.cantidad} reserva(s) activa(s)",
            tipo="error",
        )

    return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero eliminado")


@router.post("/{pasajero_id}/documentos")
async def crear_documento_endpoint(
    pasajero_id: str,
    tipo: str = Form(...),
    numero: str = Form(...),
    pais_emision: str = Form(...),
    fecha_vencimiento: str | None = Form(None),
    usuario: dict = Depends(_rbac_editar),
):
    try:
        await crear_documento_viaje_backoffice(
            usuario, pasajero_id, tipo, numero, pais_emision, fecha_vencimiento or None
        )
    except PasajeroNoEncontrado:
        return redirect_con_mensaje("/backoffice/pasajeros", "Pasajero no encontrado", tipo="error")
    except TipoDocumentoInvalido:
        return redirect_con_mensaje(
            f"/backoffice/pasajeros?pid={pasajero_id}&abrir=editar-{pasajero_id}", "Tipo de documento inválido", tipo="error"
        )

    return redirect_con_mensaje(f"/backoffice/pasajeros?pid={pasajero_id}&abrir=editar-{pasajero_id}", "Documento agregado")


@router.post("/{pasajero_id}/documentos/{documento_id}/eliminar")
async def eliminar_documento_endpoint(
    pasajero_id: str,
    documento_id: str,
    usuario: dict = Depends(_rbac_editar),
):
    try:
        await eliminar_documento_viaje_backoffice(usuario, pasajero_id, documento_id)
    except SinPermiso:
        return redirect_con_mensaje(
            f"/backoffice/pasajeros?pid={pasajero_id}&abrir=editar-{pasajero_id}", "Documento no encontrado", tipo="error"
        )

    return redirect_con_mensaje(f"/backoffice/pasajeros?pid={pasajero_id}&abrir=editar-{pasajero_id}", "Documento eliminado")


@router.get("/{pasajero_id}")
async def detalle_pasajero(
    request: Request,
    pasajero_id: str,
    usuario: dict = Depends(_rbac_ver),
):
    detalle = await obtener_detalle_pasajero(usuario, pasajero_id)
    contexto = await nav_context(usuario)
    if detalle is None:
        return templates.TemplateResponse(
            request,
            "backoffice/detalle_pasajero.html",
            {**contexto, "pasajero": None},
            status_code=404,
        )
    return templates.TemplateResponse(
        request,
        "backoffice/detalle_pasajero.html",
        {**contexto, "pasajero": detalle},
    )


@router.put("/{pasajero_id}")
async def editar_pasajero(
    request: Request,
    pasajero_id: str,
    telefono: str = Form(None),
    direccion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
    usuario: dict = Depends(_rbac_editar),
):
    data = {}
    if telefono is not None:
        data["telefono"] = telefono
    if direccion is not None:
        # El campo real en PocketBase es direccion_facturacion — "direccion"
        # a secas no existe en el esquema y PocketBase lo descarta en
        # silencio, así que guardarlo así nunca persistía nada (bug real).
        data["direccion_facturacion"] = direccion
    if contacto_emergencia is not None:
        data["contacto_emergencia"] = contacto_emergencia

    try:
        actualizado = await editar_contacto_backoffice(usuario, pasajero_id, data)
    except PasajeroNoEncontrado:
        return JSONResponse(status_code=404, content={"detail": "Pasajero no encontrado"})

    return JSONResponse(
        {
            "id": actualizado["id"],
            "telefono": actualizado.get("telefono"),
            "direccion": actualizado.get("direccion_facturacion"),
            "contacto_emergencia": actualizado.get("contacto_emergencia"),
        }
    )
