import logging

import pytest

from app.seguridad.services.audit_service import AuditService


# ── RF-SEG-014 (CHK018) ──────────────────────────────────────────────────

async def test_insertar_auditoria_guarda_todos_los_campos(pb, usuario_factory):
    usuario = await usuario_factory()
    service = AuditService()
    await service.insertar(
        "crear",
        "usuarios",
        usuario_id=usuario["id"],
        registro_id=usuario["id"],
        detalle={"campo": "valor"},
        ip="127.0.0.1",
    )

    registro = await pb.get_first("auditoria", f'registro_id="{usuario["id"]}"')
    assert registro is not None
    assert registro["accion"] == "crear"
    assert registro["tabla"] == "usuarios"
    assert registro["usuario_id"] == usuario["id"]
    assert registro["ip"] == "127.0.0.1"

    await pb.delete_record("auditoria", registro["id"])


# ── RF-SEG-014: fallo no revierte la acción original (CHK019) ───────────

async def test_fallo_de_insercion_no_propaga_excepcion(monkeypatch, caplog):
    class RepoQueFalla:
        async def insertar_auditoria(self, data):
            raise RuntimeError("PocketBase no disponible")

    service = AuditService(repo=RepoQueFalla())
    with caplog.at_level(logging.CRITICAL, logger="auditoria"):
        await service.insertar("crear", "usuarios")  # no debe lanzar

    assert any("Fallo al insertar registro de auditoría" in r.message for r in caplog.records)


# ── RN-SEG-010 / REG-B4: solo inserción (CHK032, CHK042) ─────────────────

def test_audit_service_no_expone_update_ni_delete():
    metodos_publicos = {
        nombre
        for nombre in dir(AuditService)
        if not nombre.startswith("_") and callable(getattr(AuditService, nombre))
    }
    assert metodos_publicos == {"insertar"}


# ── RF-SEG-015 (CHK020) ───────────────────────────────────────────────────

async def test_vista_auditoria_no_tiene_controles_de_edicion(admin_client):
    # "editar"/"eliminar" SÍ pueden aparecer como valor de dato (acción
    # auditada de otro módulo), y la plantilla base SÍ tiene botones propios
    # del shell (menú, cerrar sesión) — lo que se prueba es la ausencia de
    # controles interactivos DENTRO DE LA TABLA de auditoría: ningún botón
    # ni fetch PUT/DELETE contra /admin/auditoria/{id}.
    resp = await admin_client.get("/admin/auditoria")
    assert resp.status_code == 200
    html = resp.text
    tabla = html[html.index("<table") : html.index("</table>")]
    assert "<button" not in tabla
    assert "method: 'PUT'" not in html
    assert "method: 'DELETE'" not in html


async def test_vista_auditoria_lista_orden_descendente(admin_client, pb):
    service = AuditService()
    await service.insertar("orden_test", "usuarios", registro_id="primero-cronologico")
    await service.insertar("orden_test", "usuarios", registro_id="segundo-cronologico")

    resp = await admin_client.get("/admin/auditoria?accion=orden_test")
    assert resp.status_code == 200
    pos_primero = resp.text.find("primero-cronologico")
    pos_segundo = resp.text.find("segundo-cronologico")
    assert pos_primero != -1 and pos_segundo != -1
    assert pos_segundo < pos_primero  # el más reciente (segundo insertado) aparece primero

    registros = await pb.list_records("auditoria", {"filter": 'accion="orden_test"', "perPage": 10})
    for item in registros["items"]:
        await pb.delete_record("auditoria", item["id"])


# ── RF-SEG-016 (CHK021) ───────────────────────────────────────────────────

async def test_filtros_sin_boton_aplicar(admin_client):
    resp = await admin_client.get("/admin/auditoria")
    html = resp.text
    # IS-02 (auditoría de informes simples, 2026-08-01) — el auto-envío ahora
    # se conecta vía el script global `filtros-auto.js` (fix J9 reusado por
    # todos los informes), no con un <script> inline por página.
    assert 'data-auto-filtros' in html
    assert ">Aplicar<" not in html
    assert ">Buscar<" not in html


async def test_exportacion_respeta_filtro(admin_client, pb):
    marca = "marca-export-test"
    r1 = await pb.create_record("auditoria", {"accion": marca, "tabla": "usuarios", "detalle": {}})
    r2 = await pb.create_record("auditoria", {"accion": "otra_accion", "tabla": "usuarios", "detalle": {}})

    resp = await admin_client.get(f"/admin/auditoria/exportar?accion={marca}")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert marca in resp.text
    assert "otra_accion" not in resp.text

    await pb.delete_record("auditoria", r1["id"])
    await pb.delete_record("auditoria", r2["id"])


# ── IS-02 (auditoría de informes simples, 2026-08-01) — filtro por actor
# (email, resuelto a usuario_id) y paginación real ──────────────────────

async def test_filtro_por_actor_email(admin_client, pb, usuario_factory):
    marca = "marca-actor-test"
    actor = await usuario_factory()
    otro = await usuario_factory()
    r1 = await pb.create_record(
        "auditoria", {"accion": marca, "tabla": "usuarios", "usuario_id": actor["id"], "detalle": {}}
    )
    r2 = await pb.create_record(
        "auditoria", {"accion": marca, "tabla": "usuarios", "usuario_id": otro["id"], "detalle": {}}
    )

    try:
        resp = await admin_client.get(f"/admin/auditoria?accion={marca}&actor_email={actor['email']}")
        assert resp.status_code == 200
        assert actor["id"] in resp.text
        assert otro["id"] not in resp.text
    finally:
        await pb.delete_record("auditoria", r1["id"])
        await pb.delete_record("auditoria", r2["id"])


async def test_filtro_por_actor_email_inexistente_no_muestra_todo(admin_client):
    resp = await admin_client.get("/admin/auditoria?actor_email=no-existe@aerotrack.test")
    assert resp.status_code == 200
    assert "Sin registros para el filtro actual" in resp.text


async def test_paginacion_auditoria(admin_client):
    resp = await admin_client.get("/admin/auditoria?page=1")
    assert resp.status_code == 200

    resp = await admin_client.get("/admin/auditoria?page=999")
    assert resp.status_code == 200
