"""CHK001-003, CHK007-008 (RF-INT-001, RN-INT-001/002/004)."""

import httpx
from httpx import ASGITransport

from app.main import app


async def _crear_fuente(pb, **overrides) -> dict:
    rol = await pb.get_first("roles", 'nombre="Administrador"')
    admin = await pb.get_first("usuarios", f'rol_id="{rol["id"]}"')
    data = {
        "nombre": f"Fuente de prueba {overrides.get('_sufijo', '')}".strip(),
        "tipo_uso": "catalogo_periodico",
        "activa": True,
        "modificado_por": admin["id"],
    }
    data.update({k: v for k, v in overrides.items() if k != "_sufijo"})
    return await pb.create_record("fuentes_datos_externas", data)


# ── CHK001: lista protegida por RBAC ────────────────────────────────────

async def test_listar_fuentes_requiere_permiso(admin_client, client, usuario_factory):
    resp_admin = await admin_client.get("/backoffice/integraciones/fuentes")
    assert resp_admin.status_code == 200

    usuario = await usuario_factory(tipo_actor="pasajero")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as cliente_sin_permiso:
        await cliente_sin_permiso.post(
            "/login", data={"email": usuario["email"], "password": usuario["_password"]}
        )
        resp = await cliente_sin_permiso.get("/backoffice/integraciones/fuentes")
        assert resp.status_code == 403


# ── CHK002/RN-INT-001: edición respeta tipo_uso ─────────────────────────

async def test_editar_frecuencia_en_catalogo_periodico_se_aplica(admin_client, pb):
    fuente = await _crear_fuente(pb, _sufijo="periodica", tipo_uso="catalogo_periodico")
    try:
        resp = await admin_client.put(
            f"/backoffice/integraciones/fuentes/{fuente['id']}",
            data={"frecuencia_sincronizacion_horas": "6"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        actualizada = await pb.get_record("fuentes_datos_externas", fuente["id"])
        assert actualizada["frecuencia_sincronizacion_horas"] == 6
    finally:
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


async def test_editar_frecuencia_en_fuente_constante_se_bloquea(admin_client, pb):
    fuente = await _crear_fuente(pb, _sufijo="constante", tipo_uso="constante")
    try:
        resp = await admin_client.put(
            f"/backoffice/integraciones/fuentes/{fuente['id']}",
            data={"frecuencia_sincronizacion_horas": "6"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 422
        sin_cambios = await pb.get_record("fuentes_datos_externas", fuente["id"])
        assert sin_cambios.get("frecuencia_sincronizacion_horas") in (None, 0)
    finally:
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


# ── CHK003/RN-INT-002: desactivar no borra el catálogo ya generado ─────

async def test_desactivar_fuente_no_borra_catalogo_generado(admin_client, pb, vuelo_factory):
    fuente = await _crear_fuente(pb, _sufijo="desactivable")
    vuelo = await vuelo_factory()
    try:
        resp = await admin_client.put(
            f"/backoffice/integraciones/fuentes/{fuente['id']}",
            data={"activa": "false"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200
        actualizada = await pb.get_record("fuentes_datos_externas", fuente["id"])
        assert actualizada["activa"] is False

        # El catálogo ya generado (vuelos_catalogo, dueño de otro módulo) sigue intacto.
        vuelo_intacto = await pb.get_record("vuelos_catalogo", vuelo["id"])
        assert vuelo_intacto["id"] == vuelo["id"]
    finally:
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


# ── CHK007/RN-INT-004: edición queda auditada ───────────────────────────

async def test_editar_fuente_queda_auditada(admin_client, pb):
    fuente = await _crear_fuente(pb, _sufijo="auditada")
    try:
        resp = await admin_client.put(
            f"/backoffice/integraciones/fuentes/{fuente['id']}",
            data={"activa": "false"},
            headers={"Accept": "application/json"},
        )
        assert resp.status_code == 200

        entrada = await pb.get_first(
            "auditoria", f'accion="actualizar_fuente" && tabla="fuentes_datos_externas" && registro_id="{fuente["id"]}"'
        )
        assert entrada is not None
    finally:
        await pb.delete_record("fuentes_datos_externas", fuente["id"])


# ── CHK008/REG-B3: host_env_var nunca es el valor real de una credencial ──

def test_host_env_var_nunca_contiene_valores_hardcodeados():
    import re
    from pathlib import Path

    # Prefijos reales vistos en credenciales de este proyecto (Stripe, Google,
    # SendGrid...) — building el patrón por partes para no auto-matchear esta
    # misma línea al escanear el árbol de archivos.
    prefijos = ["sk" + "_", "pk" + "_", "AIza", "ya29" + ".", "GOCSPX" + "-"]
    patron_secreto = re.compile("(" + "|".join(re.escape(p) for p in prefijos) + ")")
    for archivo in Path("app/integraciones").rglob("*.py"):
        if archivo.name == "test_fuentes.py":
            continue  # este archivo, para no auto-matchear su propio patrón
        contenido = archivo.read_text(encoding="utf-8")
        assert not patron_secreto.search(contenido), f"posible secreto hardcodeado en {archivo}"
