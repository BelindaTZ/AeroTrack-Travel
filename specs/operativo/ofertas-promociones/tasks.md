# Tasks: Ofertas y Promociones

**Input:** [`plan.md`](./plan.md) · [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/ofertas/` *(no existe todavía)*

---

## Fase 0: Setup e infraestructura del módulo

- [ ] T001 Crear estructura `app/ofertas/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `tests/`)
- [ ] T002 [P] Crear colección `ofertas_destacadas` — `scripts/pb_schema_ofertas.py`
- [ ] T003 [P] Crear colección `cupones_descuento`
- [ ] T004 [P] Crear colección `cupones_uso`
- [ ] T005 [P] Crear colección `newsletter_suscripciones`
- [ ] T006 Crear `app/ofertas/repositories/ofertas_repo.py`
- [ ] T007 Crear `app/ofertas/schemas.py`

**Checkpoint:** las 4 colecciones existen.

---

## Fase 1: Ofertas destacadas y términos (RF-OFE-001, 005)

- [ ] T008 `app/ofertas/router_ofertas.py` — `GET /ofertas`, filtra vigentes y activas (CHK001)
- [ ] T009 `router_ofertas.py` — `GET /ofertas/{id}/terminos` (CHK002)
- [ ] T010 [P] `app/ofertas/templates/ofertas.html`
- [ ] T011 [P] `app/ofertas/tests/test_ofertas.py`

---

## Fase 2: Destinos populares (RF-OFE-002)

- [ ] T012 `app/ofertas/services/destinos_populares_service.py` — agregación real sobre `busquedas_recientes`/`reservas`, nunca mezclada con `ofertas_destacadas` (CHK003, RN-OFE-001)
- [ ] T013 `app/ofertas/router_ofertas.py` — `GET /destinos-populares`
- [ ] T014 [P] `app/ofertas/tests/test_ofertas.py` — destinos populares no se presentan como oferta editorial (CHK003)

**Checkpoint:** ofertas curadas y destinos estadísticos se muestran sin confundirse entre sí.

---

## Fase 3: Cupones en checkout (RF-OFE-003)

**⚠️ Depende de `reserva_items`/checkout real (Carrito/Reservas, no implementado)**

- [ ] T015 `app/ofertas/services/cupon_service.py` — valida vigencia, activo, usos disponibles, producto aplicable (CHK004)
- [ ] T016 `cupon_service.py` — verifica que la combinación cupón-reserva no exista ya en `cupones_uso` antes de aplicar (CHK005, RN-OFE-002)
- [ ] T017 `app/ofertas/router_cupones.py` — `POST /checkout/aplicar-cupon`
- [ ] T018 Evaluar la regla de acumulación con paquete antes de aplicar el cupón: excepción del cupón (`cupones_descuento.acumulable_con_paquete`) → default global (`configuracion_sistema`) → rechazo explícito si el resultado es "no acumulable" (RN-OFE-003, CU-T44 en `specs/tactico/ofertas-promociones/`) — no implementar ningún comportamiento implícito fuera de esta regla
- [ ] T019 [P] `app/ofertas/tests/test_cupones.py` — cupón válido/expirado/agotado/no aplicable (CHK004), doble canje bloqueado (CHK005)

**Checkpoint:** un pasajero aplica un cupón válido una sola vez por reserva.

---

## Fase 4: Newsletter (RF-OFE-004)

- [ ] T020 `app/ofertas/router_newsletter.py` — `POST /newsletter/suscribirse`, asocia a `pasajero_id` si hay sesión (CHK006)
- [ ] T021 [P] `app/ofertas/tests/test_newsletter.py`

---

## Cierre

- [ ] T022 Grep de verificación de cero secretos hardcodeados sobre `app/ofertas/`
- [ ] T023 Correr suite completa `pytest app/ofertas/` y re-correr los módulos existentes
- [ ] T024 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 y Fase 4 son independientes, implementables de inmediato.
- Fase 2 depende de datos reales de búsqueda/reserva.
- Fase 3 depende de `specs/tactico/ofertas-promociones/` (cupones reales) y de Carrito/Reservas.
