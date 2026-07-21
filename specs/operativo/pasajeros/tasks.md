# Tasks: Pasajeros

**Input:** [`plan.md`](./plan.md) · [`pasajeros-spec.md`](./pasajeros-spec.md) · [`checklist.md`](./checklist.md) · [`reglas.md`](../../000-sistema-general/reglas.md)
**Código fuente:** `app/pasajeros/` (+ imports directos de `app.seguridad.*`, `app.reservas.*`, `app.shared.*`)
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 3), precedido por una Fase 0 de setup.

**Nota de alcance:** este módulo depende de Seguridad (sesión, RBAC, auditoría — ya completos) y de Reservas (lectura de historial — ya completos). Lee `pasajeros` (dueño propio), `usuarios` (solo lectura, propiedad de Seguridad) y `reservas` (solo lectura, propiedad de Reservas). Nunca escribe en colecciones de otros módulos.

---

## Fase 0: Setup

- [ ] T001 Crear estructura `app/pasajeros/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `templates/backoffice/`, `tests/`)
- [ ] T002 [P] `app/pasajeros/repositories/pasajeros_repo.py` — encapsula consultas de `pasajeros`, `usuarios`, `reservas` sobre `app/shared/pocketbase_client.py` (solo lectura sobre `usuarios` y `reservas`)
- [ ] T003 [P] `app/pasajeros/schemas.py` — modelos Pydantic de request/response (historial, contacto, búsqueda backoffice)
- [ ] T004 [P] `app/pasajeros/tests/conftest.py` — fixture `pasajero_con_reserva_factory` (reutiliza `pasajero_factory`, `vuelo_factory`, `tarifa_factory`, `reserva_factory` del conftest raíz)
- [ ] T005 Añadir `app/pasajeros/templates` a `app/shared/templating.py` (lista de directorios Jinja2)

**Checkpoint:** estructura lista, sin lógica de negocio todavía.

---

## Fase 1 — Consultar historial de reservas propio (RF-PAS-001, RNF-PAS-001)

- [ ] T006 `app/pasajeros/repositories/pasajeros_repo.py` — `pasajero_de_usuario(usuario_id) -> dict | None`, `reservas_de_pasajero(pasajero_id, estado=None, fecha_desde=None, fecha_hasta=None) -> list[dict]` (filtros opcionales, sort `-fecha_salida`)
- [ ] T007 `app/pasajeros/services/pasajeros_service.py` — `obtener_historial(usuario, estado=None, fecha_desde=None, fecha_hasta=None)`: resuelve `pasajeros` del usuario, delega en repo; si no tiene perfil de pasajero, retorna lista vacía (no error)
- [ ] T008 `app/pasajeros/router_historial.py` — `GET /mis-reservas` (sesión requerida via `Depends(verificar_sesion)`), pasa filtros como query params al servicio, renderiza template
- [ ] T009 [P] `app/pasajeros/templates/mis_reservas.html` — tabla de historial con filtros instantáneos por estado y rango de fechas (sin botón "Aplicar" — REG-J9), cada reserva navegable a `/reservas/{id}`
- [ ] T010 [P] `app/pasajeros/tests/test_historial.py` — pasajero autenticado ve solo sus reservas, ordenadas por fecha de vuelo descendente (CHK001, CHK013)
- [ ] T011 [P] `app/pasajeros/tests/test_historial.py` — filtros por estado y rango de fechas se aplican sin botón "Aplicar" (CHK011, RNF-PAS-001)
- [ ] T012 [P] `app/pasajeros/tests/test_historial.py` — pasajero sin perfil de pasajero ve lista vacía sin error (caso edge)

**Checkpoint:** un pasajero autenticado consulta y filtra su historial de reservas propio.

---

## Fase 2 — Editar datos de contacto (RF-PAS-002, RNF-PAS-002)

- [ ] T013 `app/pasajeros/repositories/pasajeros_repo.py` — extiende: `actualizar_contacto(pasajero_id, data: dict) -> dict`
- [ ] T014 `app/pasajeros/services/pasajeros_service.py` — `actualizar_contacto(usuario, telefono, direccion=None, contacto_emergencia=None)`: valida formato de teléfono (RNF-PAS-002 — regex `^\+?[\d\s\-\(\)]{7,15}$` o similar), actualiza `pasajeros.telefono`, `pasajeros.direccion`, `pasajeros.contacto_emergencia`; dispara `audit_service.insertar` (CU-O41, RN-PAS-004)
- [ ] T015 `app/pasajeros/router_contacto.py` — `POST /mi-perfil/contacto` (sesión requerida), valida, redirige a `/mi-perfil?mensaje=Contacto+actualizado` (feedback inmediato, REG-J11)
- [ ] T016 Wire `audit_service.insertar` con `detalle={"campo_modificado": "telefono", "origen": "autoservicio"}` en la actualización (RN-PAS-004)
- [ ] T017 [P] `app/pasajeros/tests/test_contacto.py` — teléfono válido se actualiza y queda auditado (CHK003, CHK004, CHK010, CHK014)
- [ ] T018 [P] `app/pasajeros/tests/test_contacto.py` — teléfono con formato inválido se rechaza con mensaje específico (CHK012, RNF-PAS-002)
- [ ] T019 [P] `app/pasajeros/tests/test_contacto.py` — el correo electrónico no se puede cambiar desde aquí (fuera de alcance — verificado por ausencia de campo en el formulario)

**Checkpoint:** un pasajero actualiza su teléfono/dirección/contacto de emergencia con validación y auditoría.

---

## Fase 3 — Backoffice: buscar y gestionar pasajeros (RF-PAS-003, 004, RN-PAS-003)

- [ ] T020 `app/pasajeros/repositories/pasajeros_repo.py` — extiende: `buscar_pasajeros(termino, agente_usuario_id=None, agente_rol_id=None) -> list[dict]` (búsqueda por nombre, correo o documento; si el agente tiene restricción RBAC Nivel 2, filtra por las tablas autorizadas)
- [ ] T021 `app/pasajeros/services/pasajeros_service.py` — `buscar_pasajeros_backoffice(usuario, termino)`: invoca `rbac_service.verificar_permiso(usuario, "pasajeros", "ver")` (CU-O43), luego delega en repo con contexto RBAC; `obtener_detalle_pasajero(usuario, pasajero_id)` y `editar_contacto_backoffice(usuario, pasajero_id, data)` — ambas verifican RBAC Nivel 2 y auditan (CU-O41, RN-PAS-004)
- [ ] T022 `app/pasajeros/router_backoffice.py` — `GET /backoffice/pasajeros` (filtro instantáneo por nombre/correo/documento — REG-J9), `GET /backoffice/pasajeros/{id}` (detalle + historial), `PUT /backoffice/pasajeros/{id}` (editar contacto); todos protegidos por `Depends(verificar_sesion)` + `Depends(requiere_permiso("pasajeros", "ver"/"editar"))`
- [ ] T023 Wire `audit_service.insertar` con `detalle={"campo_modificado": ..., "origen": "backoffice", "agente_id": ...}` en la edición desde backoffice (RN-PAS-004)
- [ ] T024 [P] `app/pasajeros/templates/backoffice/buscar_pasajeros.html` — tabla con filtro instantáneo (J9), combobox con búsqueda si hay muchos resultados
- [ ] T025 [P] `app/pasajeros/templates/backoffice/detalle_pasajero.html` — datos de contacto, historial de reservas, botón de editar con confirmación (J11)
- [ ] T026 [P] `app/pasajeros/tests/test_backoffice.py` — búsqueda por nombre/correo/documento retorna resultados dentro del alcance RBAC (CHK005, CHK015)
- [ ] T027 [P] `app/pasajeros/tests/test_backoffice.py` — Agente con restricción RBAC Nivel 2 no ve pasajeros fuera de su alcance (CHK009, RN-PAS-003)
- [ ] T028 [P] `app/pasajeros/tests/test_backoffice.py` — edición desde backoffice incluye verificación RBAC y registro de auditoría con `agente_id` (CHK006, CHK010, CHK015)
- [ ] T029 [P] `app/pasajeros/tests/test_backoffice.py` — sin permiso RBAC, la búsqueda y edición se bloquean antes de tocar datos

**Checkpoint:** un Agente/Administrador busca, ve y edita pasajeros dentro de su alcance RBAC, con auditoría completa.

---

## Cierre

- [ ] T030 Grep de verificación de cero secretos hardcodeados sobre `app/pasajeros/`
- [ ] T031 Correr suite completa `pytest app/pasajeros/` y re-correr `app/seguridad/ app/reservas/` para confirmar cero regresión cruzada
- [ ] T032 Repasar `checklist.md` de Pasajeros ítem por ítem; actualizar `errores-conocidos.md` con cualquier hallazgo

---

## Fase 4 (futura, no iniciada) — CU-O49/O50, catálogo v3.0

No desglosada en tareas todavía — ver `plan.md` Fase 4 y `pasajeros-spec.md` RF-PAS-005/006.

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 y Fase 2 son independientes entre sí (una lee historial, la otra edita contacto); ambas dependen de Fase 0.
- Fase 3 depende de Fase 1 (reutiliza la lectura de historial para el detalle de backoffice) y de Seguridad Fase 2 (RBAC/auditoría — ya completa).