"""CU-T33 (reporte), CU-T34 (configuración) — Actor: Administrador únicamente."""

_CLAVES_ASISTENTE = ("asistente_ia.tono", "asistente_ia.temas_permitidos", "asistente_ia.respuestas_predefinidas")


async def test_admin_configura_asistente(pb, admin_client):
    """`configuracion_sistema` es estado global compartido por toda la
    suite (igual que `cupones.acumulable_con_paquete_default` en
    Ofertas) — este test debe dejarlo exactamente como lo encontró, o
    contamina cualquier otro test que llame a `conversar()` después."""
    originales = {clave: await pb.get_first("configuracion_sistema", f'clave="{clave}"') for clave in _CLAVES_ASISTENTE}

    try:
        resp = await admin_client.post(
            "/backoffice/asistente/configuracion",
            data={
                "tono": "cercano y directo",
                "temas_permitidos": "vuelos, pagos, disrupciones",
                "respuestas_clave": ["horario"],
                "respuestas_valor": ["Atendemos 24/7 por este chat."],
            },
            follow_redirects=True,
        )
        assert resp.status_code == 200

        registro = await pb.get_first("configuracion_sistema", 'clave="asistente_ia.tono"')
        assert registro["valor"] == "cercano y directo"
        registro_temas = await pb.get_first("configuracion_sistema", 'clave="asistente_ia.temas_permitidos"')
        assert "vuelos" in registro_temas["valor"]
    finally:
        for clave, original in originales.items():
            actual = await pb.get_first("configuracion_sistema", f'clave="{clave}"')
            if actual is None:
                continue
            if original is None:
                await pb.delete_record("configuracion_sistema", actual["id"])
            else:
                await pb.update_record("configuracion_sistema", actual["id"], {"valor": original["valor"]})


async def test_configuracion_pagina_muestra_valores_reales(pb, admin_client):
    registro = await pb.get_first("configuracion_sistema", 'clave="asistente_ia.tono"')
    creado = False
    if registro is None:
        registro = await pb.create_record(
            "configuracion_sistema",
            {
                "clave": "asistente_ia.tono", "valor": "tono de prueba único xyz", "categoria": "asistente_ia",
                "modificado_por": admin_client.admin_usuario["id"],
            },
        )
        creado = True
        esperado = "tono de prueba único xyz"
    else:
        esperado = registro["valor"]

    resp = await admin_client.get("/backoffice/asistente/configuracion")
    assert resp.status_code == 200
    assert esperado in resp.text

    if creado:
        await pb.delete_record("configuracion_sistema", registro["id"])


async def test_agente_no_tiene_acceso_a_asistente_ia(agente_client):
    resp = await agente_client.get("/backoffice/asistente/configuracion")
    assert resp.status_code == 403


async def test_reporte_cuenta_consultas_reales(pb, admin_client, pasajero_factory):
    from app.asistente_ia.integrations.llm_client import LLMClient
    from app.asistente_ia.services.asistente_service import conversar

    class LLMFalso(LLMClient):
        async def generar(self, system_prompt, historial, mensaje):
            return "respuesta de prueba"

    usuario, pasajero = await pasajero_factory()
    resultado = await conversar(usuario, pasajero["id"], "consulta única de prueba para reporte", LLMFalso())

    resp = await admin_client.get("/backoffice/asistente/reporte")
    assert resp.status_code == 200
    assert "consulta única de prueba para reporte" in resp.text

    mensajes = await pb.list_records("mensajes_ia", {"filter": f'conversacion_id="{resultado["conversacion_id"]}"'})
    for m in mensajes["items"]:
        await pb.delete_record("mensajes_ia", m["id"])
    await pb.delete_record("conversaciones_ia", resultado["conversacion_id"])
