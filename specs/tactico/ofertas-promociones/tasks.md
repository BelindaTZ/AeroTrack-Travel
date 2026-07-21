# Tasks: Ofertas y Promociones (Táctico)

**Input:** [`plan.md`](./plan.md) · [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/ofertas/` *(compartido con el nivel Operativo)*

---

## Fase 1: Gestionar cupones (RF-OFE-T01, CU-T30)

- [ ] T001 `app/ofertas/router_cupones_admin.py` — `GET/POST /backoffice/ofertas/cupones`, protegido por RBAC (CHK001)
- [ ] T002 Bloquea edición de `codigo` si el cupón ya tiene registros en `cupones_uso` (CHK002, RN-OFE-T01)
- [ ] T003 [P] `app/ofertas/tests/test_cupones_admin.py`

**Checkpoint:** un Administrador gestiona cupones reales que consume el checkout del nivel Operativo.

---

## Fase 2: Campañas de email (RF-OFE-T02, CU-T31)

- [ ] T004 `app/ofertas/router_campanas.py` — `GET/POST /backoffice/ofertas/campanas` (`borrador`), protegido por RBAC (CHK003)
- [ ] T005 `router_campanas.py` — `POST /backoffice/ofertas/campanas/{id}/enviar`: resuelve el segmento contra `pasajeros`/`newsletter_suscripciones`, envía real vía SendGrid, marca `enviada` (CHK004)
- [ ] T006 Bloquea edición/reenvío de una campaña ya `enviada` (CHK005, RN-OFE-T02)
- [ ] T007 [P] `app/ofertas/tests/test_campanas.py` — envío real (CHK004), inmutabilidad tras envío (CHK005)

**Checkpoint:** un Administrador envía una campaña real a un segmento de pasajeros.

---

## Fase 3: Reporte de cupones (RF-OFE-T03, CU-T32)

- [ ] T008 `app/ofertas/router_reporte_cupones.py` — `GET /backoffice/ofertas/reporte-cupones`, protegido por RBAC (CHK006)
- [ ] T009 Filtro instantáneo por período (REG-J9, CHK007)
- [ ] T010 [P] `app/ofertas/tests/test_reporte_cupones.py`

**Checkpoint:** un Administrador ve uso y descuento real por cupón.

---

## Fase 4: Configurar acumulación cupón+paquete (RF-OFE-T04, CU-T44)

- [ ] T011 Agregar campo `acumulable_con_paquete` (nullable) al formulario de `router_cupones_admin.py` (Fase 1) (CHK008)
- [ ] T012 `app/ofertas/router_config_acumulacion.py` — `GET/POST /backoffice/ofertas/config-acumulacion-paquete`, guarda el default global en `configuracion_sistema` (clave `cupones.acumulable_con_paquete_default`) (CHK009)
- [ ] T013 Coordinar con Operativo: `cupon_service.py` (Fase 3 de Operativo) debe leer excepción por cupón → default global, en ese orden, antes de aplicar sobre un paquete (CHK010, RN-OFE-T03/T04)
- [ ] T014 [P] `app/ofertas/tests/test_config_acumulacion.py` — excepción de cupón gana sobre default global (CHK010), regla no se evalúa si la reserva no es paquete (CHK011)

**Checkpoint:** un cupón se aplica o no sobre un paquete según la regla configurada, con la excepción por cupón siempre priorizada.

---

## Cierre

- [ ] T011 Correr `pytest app/ofertas/` completo (Operativo + Táctico)
- [ ] T012 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Fase 1 es independiente — priorizar, alimenta a Operativo.
- Fase 2 es independiente de Fase 1 y 3.
- Fase 3 depende de Fase 1 y de cupones usados reales.
- Fase 4 depende de Fase 1 (el campo por-cupón vive en su mismo formulario) y debe coordinarse con Operativo Fase 3 antes de que el checkout aplique cupones sobre paquetes.
