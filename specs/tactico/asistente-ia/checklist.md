# Checklist de Validación: Asistente IA (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico cumple los RF/RN definidos en `asistente-ia-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`asistente-ia-spec.md`](./asistente-ia-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/asistente_ia/router_backoffice.py`, 4/4 tests (`test_backoffice.py`).

---

## Requisitos funcionales

- [x] CHK001 RF-IA-T01 — Configuración protegida por RBAC — `test_agente_no_tiene_acceso_a_asistente_ia` (403 para rol Agente; módulo `asistente_ia` sembrado solo para Administrador).
- [x] CHK002 RF-IA-T01 — Tono, temas permitidos y respuestas predefinidas se guardan en `configuracion_sistema` — `test_admin_configura_asistente` verifica los 3 registros (`asistente_ia.tono`, `asistente_ia.temas_permitidos`, `asistente_ia.respuestas_predefinidas`) con sus valores reales tras el POST.
- [x] CHK003 RN-IA-T01 — Consulta fuera de temas permitidos se rechaza explícitamente — `_tema_permitido()` en `asistente_service.py`; verificado en vivo: con `temas_permitidos` configurado a "vuelos, pagos, disrupciones", una consulta sobre un tema fuera de esa lista recibió el mensaje de rechazo explícito, no una respuesta genérica.
- [x] CHK004 RF-IA-T02 — Reporte protegido por RBAC — mismo mecanismo que CHK001, verificado también contra el reporte (`/backoffice/asistente/reporte`).
- [x] CHK005 RF-IA-T02 — Filtro de período se aplica sin botón "Aplicar" — `?dias=` como query param con navegación directa (mismo patrón que Centro de Ayuda y Ofertas, REG-J9).
- [x] CHK006 RN-IA-T02 — Reporte separa consultas resueltas de temas sin respuesta verificable — `reporte_consultas()` empareja mensajes usuario→asistente consecutivos dentro de la misma conversación y clasifica por coincidencia con `MENSAJE_SIN_CONTEXTO_VERIFICADO`/`MENSAJE_SIN_CREDENCIAL`; verificado en vivo con una consulta real sin contexto (apareció en "sin respuesta verificable") y una con reserva real (apareció en "resueltas").

## Trazabilidad de casos de uso

- [x] CHK007 CU-T34 — `test_admin_configura_asistente` + verificado en vivo que el nivel Operativo respeta lo configurado aquí (ver CHK003 — no solo se guarda, se aplica).
- [x] CHK008 CU-T33 — `test_reporte_cuenta_consultas_reales` + `test_configuracion_pagina_muestra_valores_reales`.

## Notas

- CHK007 se cerró confirmando la integración real con `_tema_permitido()` del nivel Operativo (no solo que el POST persiste) — la consulta de prueba fuera de tema fue rechazada explícitamente en vivo, no solo en test.
- Bug de contaminación de estado global encontrado y corregido en `test_admin_configura_asistente` durante esta ronda — ver nota correspondiente en el checklist Operativo.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md` — **hecho**.
