# Tasks: Hoteles (Táctico)

**Input:** [`plan.md`](./plan.md) · [`hoteles-spec.md`](./hoteles-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/hoteles/` *(compartido con el nivel Operativo)*
**Orden de fases:** idéntico al de `plan.md`.
**Trazabilidad:** cada tarea de prueba referencia su ítem `CHKxxx` de `checklist.md`.

---

## Fase 0: Precondición

**⚠️ Bloqueante:** requiere `specs/operativo/hoteles/` implementado (al menos Fase 1-2 de ese plan) antes de iniciar.

- [ ] T001 Confirmar que `app/hoteles/` (nivel Operativo) existe y tiene datos reales de catálogo antes de empezar Fase 1 de este documento.

---

## Fase 1: Comparación de propiedades (RF-HOT-T01, CU-T09)

- [ ] T002 `app/hoteles/router_comparacion.py` — `GET /hoteles/comparar`, acepta 2-5 IDs de hotel, rechaza un sexto explícitamente (CHK001, CHK003)
- [ ] T003 Servicio de comparación reutiliza `hoteles_repo` ya existente — sin llamada nueva a `hotellens_client` (CHK002, RNF-HOT-T01)
- [ ] T004 [P] `app/hoteles/templates/comparar_hoteles.html` (design system v4)
- [ ] T005 [P] `app/hoteles/tests/test_comparacion.py` — comparación de 2-5 hoteles (CHK001), rechazo del sexto (CHK003), sin llamada externa nueva (CHK002)

**Checkpoint:** un pasajero compara hasta 5 hoteles sin generar tráfico adicional a HotelLens.

---

## Fase 2: Reporte de hoteles más reservados (RF-HOT-T02, CU-T10)

**⚠️ Depende de `reserva_items` (Reservas, migración pendiente)** — implementar con datos de prueba sembrados manualmente si se adelanta antes de esa migración; documentar el punto de integración real como pendiente, no simulado como si ya funcionara con datos reales.

- [ ] T006 `app/hoteles/router_reporte.py` — `GET /backoffice/hoteles/reporte`, protegido por `rbac_service` (CHK004)
- [ ] T007 Filtro instantáneo por destino/rango de fechas (REG-J9, CHK005)
- [ ] T008 Solo cuenta reservas `confirmada` o posterior (CHK006, RN-HOT-T02)
- [ ] T009 [P] `app/hoteles/tests/test_reporte.py` — reporte con reservas de prueba sembradas manualmente (documentar que depende de `reserva_items` real para cerrar de verdad)

**Checkpoint:** un Administrador ve el reporte de hoteles más reservados — cierre completo solo cuando `reserva_items` exista con datos reales.

---

## Cierre

- [ ] T010 Correr `pytest app/hoteles/` completo (Operativo + Táctico) para confirmar cero regresión
- [ ] T011 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md` cuando ambas fases cierren

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 y Fase 2 son independientes entre sí — Fase 1 no depende de Reservas, Fase 2 sí.
