# Tasks: Integraciones

**Input:** [`plan.md`](./plan.md) · [`integraciones-spec.md`](./integraciones-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/integraciones/` *(implementado 2026-07-19, 10/10 tests pasando)*

---

## Fase 0: Setup e infraestructura del módulo

- [x] T001 Crear estructura `app/integraciones/` (`__init__.py`, `services/`, `repositories/`, `tests/`)
- [x] T002 [P] Crear colección `fuentes_datos_externas` — `scripts/pb_schema_integraciones.py`
- [x] T003 [P] Crear colección `sincronizaciones_log`
- [x] T004 Crear `app/integraciones/repositories/integraciones_repo.py`
- [x] T005 ~~Crear `app/integraciones/schemas.py`~~ — no fue necesario, los routers devuelven el dict de PocketBase o un `TemplateResponse` directo, sin modelo Pydantic de salida propio.
- [x] T006 Script de seed — una fila por fuente real conocida (AeroDataBox, Google Flights/SerpApi, HotelLens, Global Rental Cars, Travel Advisor, Cruise Pricing API, ExchangeRate-API, Visa Requirement, SendGrid, Gmail API, OpenSky Network, Stripe, Groq, Gemini) + filas `regla_negocio_interna` (disponibilidad tarifas_vuelo/asientos/actividades/cruceros)

**Checkpoint:** las 2 colecciones existen, sembradas con las fuentes reales conocidas. ✅

---

## Fase 1: Configurar fuentes (RF-INT-001)

- [x] T007 `app/integraciones/router_fuentes.py` — `GET /backoffice/integraciones/fuentes` (CHK001)
- [x] T008 `router_fuentes.py` — `PUT /backoffice/integraciones/fuentes/{id}`, campos editables según `tipo_uso` (CHK002, RN-INT-001)
- [x] T009 Desactivar una fuente no borra el catálogo ya generado por otros módulos (CHK003, RN-INT-002)
- [x] T010 `router_fuentes.py` — `POST /backoffice/integraciones/fuentes/{id}/resincronizar` — solo `catalogo_periodico`; registra `estado="fallido"` con motivo explícito (ningún job real está wireado todavía) en vez de fabricar un `exitoso` falso.
- [x] T011 [P] `app/integraciones/tests/test_fuentes.py` — edición respeta `tipo_uso` (CHK002), desactivar no borra datos (CHK003), RBAC (CHK001), auditoría (CHK007), grep de secretos (CHK008). 6 tests.

---

## Fase 2: Bitácora de sincronizaciones (RF-INT-002)

- [x] T012 `app/integraciones/router_bitacora.py` — `GET /backoffice/integraciones/bitacora`, filtrable por fuente/fecha (CHK004)
- [x] T013 Filtro instantáneo (REG-J9, CHK005) — `requestSubmit()` en `change`, mismo patrón que `comisiones.html`
- [x] T014 Corrida fallida se muestra sin ocultar la última exitosa (CHK006, RN-INT-003)
- [x] T015 [P] `app/integraciones/tests/test_bitacora.py` — filtros (CHK004), corrida fallida no oculta exitosa (CHK006), resincronización manual. 4 tests.

**Checkpoint:** un Administrador ve la bitácora completa de todas las fuentes. ✅

---

## Cierre

- [x] T016 Grep de verificación de cero secretos hardcodeados sobre `app/integraciones/` — `test_host_env_var_nunca_contiene_valores_hardcodeados`, pasa.
- [x] T017 `pytest app/integraciones/` — 10/10 pasan. Vuelos no es todavía consumidor real (ver CHK010 en checklist.md) — nada que re-correr ahí específico a este módulo.
- [x] T018 `checklist.md` repasado (CHK001-009 `[x]`, CHK010 abierto a propósito); `pendientes-implementacion-codigo.md` actualizado.

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 es independiente — priorizar, es consumida por los 5 módulos de catálogo.
- Fase 2 depende de que algún módulo ya esté escribiendo en `sincronizaciones_log`.
