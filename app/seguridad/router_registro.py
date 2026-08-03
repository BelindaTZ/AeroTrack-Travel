"""RF-SEG-008 — alta autoservicio de pasajero."""

from datetime import date

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.seguridad.services.audit_service import AuditService
from app.seguridad.services.password_service import PasswordDebil, PasswordService
from app.seguridad.services.plantillas_service import plantilla
from app.seguridad.services.usuarios_service import CorreoDuplicado, UsuariosService
from app.shared.email_sender import enviar_correo
from app.shared.templating import templates

router = APIRouter()


@router.get("/registro")
async def registro_form(request: Request):
    return templates.TemplateResponse(request, "registro.html", {})


@router.post("/registro")
async def registro_submit(
    request: Request,
    nombre_completo: str = Form(...),
    email: str = Form(...),
    fecha_nacimiento: date = Form(...),
    telefono: str = Form(...),
    password: str = Form(...),
    confirmacion: str = Form(...),
    genero: str | None = Form(None),
    numero_documento: str | None = Form(None),
    direccion_facturacion: str | None = Form(None),
    contacto_emergencia: str | None = Form(None),
):
    contexto_error = {
        "nombre_completo": nombre_completo,
        "email": email,
        "telefono": telefono,
    }

    if password != confirmacion:
        return templates.TemplateResponse(
            request,
            "registro.html",
            {**contexto_error, "error": "Las contraseñas no coinciden"},
            status_code=400,
        )

    try:
        await PasswordService().validar_fortaleza(password)
    except PasswordDebil as exc:
        return templates.TemplateResponse(
            request, "registro.html", {**contexto_error, "error": exc.motivo}, status_code=400
        )

    try:
        usuario = await UsuariosService().crear_pasajero(
            nombre_completo=nombre_completo,
            email=email,
            password=password,
            fecha_nacimiento=fecha_nacimiento,
            telefono=telefono,
            genero=genero or None,
            numero_documento=numero_documento or None,
            direccion_facturacion=direccion_facturacion or None,
            contacto_emergencia=contacto_emergencia or None,
        )
    except CorreoDuplicado:
        return templates.TemplateResponse(
            request,
            "registro.html",
            {**contexto_error, "error": "Ese correo ya está registrado"},
            status_code=409,
        )

    await AuditService().insertar(
        "crear", "usuarios", usuario_id=usuario["id"], registro_id=usuario["id"],
        detalle={"origen": "autoservicio_registro"},
    )
    asunto = await plantilla("bienvenida.plantilla_asunto", "Bienvenido a AeroTrack Travel")
    cuerpo = await plantilla("bienvenida.plantilla_cuerpo", "Tu cuenta fue creada correctamente. Ya puedes iniciar sesión.")
    await enviar_correo(email, asunto, cuerpo)

    return RedirectResponse(
        "/login?mensaje=Cuenta creada. Revisa tu correo y luego inicia sesión.", status_code=303
    )
