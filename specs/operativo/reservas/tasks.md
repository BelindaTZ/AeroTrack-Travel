# Tasks: Reservas

**Input:** [`plan.md`](./plan.md) · [`reservas-spec.md`](./reservas-spec.md) · [`checklist.md`](./checklist.md) · [`../../.specify/memory/constitution.md`](../../../.specify/memory/constitution.md)
**Código fuente:** `app/reservas/` (+ imports directos de `app.vuelos.*`, `app.seguridad.*`, `app.shared.*`)
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 5), precedido por una Fase 0 de setup.

**Ver la sección "Ajuste de alcance" en `plan.md`** — Pasajeros y Facturación no existen en esta sesión. Resumen: solo pasajero titular (sin acompañantes), pago simulado vía `pago_stub_service.py` (punto de integración real para el futuro webhook de Facturación), diferencia de tarifa/reembolso quedan documentados como `"pendiente_de_modulo_facturacion"` en auditoría en vez de simulados.

---

## Fase 0: Setup

- [ ] T001 Crear estructura `app/reservas/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `templates/backoffice/`, `tests/`)
- [ ] T002 [P] `app/reservas/repositories/reservas_repo.py` — encapsula consultas de `reservas`, `reserva_pasajeros`, `reserva_extras`, `alertas_precio` sobre `app/shared/pocketbase_client.py`
- [ ] T003 [P] `app/reservas/schemas.py` — modelos Pydantic de request/response (checkout, detalle de reserva)
- [ ] T004 [P] `app/reservas/tests/conftest.py` — fixture `reserva_factory` (crea vuelo+tarifa+pasajero de prueba y una reserva desechable, con limpieza)
- [ ] T005 Añadir `app/reservas/templates` a `app/shared/templating.py` (lista de directorios Jinja2)

**Checkpoint:** estructura lista, sin lógica de negocio todavía.

---

## Fase 1 — Crear reserva autoservicio (RF-RES-001, RN-RES-001, RNF-RES-001)

- [ ] T006 `app/reservas/services/crear_reserva_service.py` — `crear_reserva(usuario, tarifa_id, precio_esperado, extras=[])`: resuelve el `pasajeros` del usuario autenticado (rechaza si no tiene uno — solo aplica a `tipo_actor="pasajero"`), relee `tarifas_vuelo.precio_final` actual y lo compara contra `precio_esperado` (RNF-RES-001 — si difiere, rechaza sin invocar cupo), invoca `app.vuelos.services.cupo_service.verificar_y_reservar_cupo` (RN-RES-001), calcula `total_pagar` (tarifa + extras), lee minutos de expiración de `configuracion_sistema` (`reserva.expiracion_minutos`, ya sembrado en 15 — mismo patrón que `password_service`), crea `reservas` (`estado="pendiente_pago"`, `canal="autoservicio"`) + `reserva_pasajeros` (titular) + `reserva_extras`
- [ ] T007 `app/reservas/services/pago_stub_service.py` — `confirmar_pago_reserva(reserva_id)`: punto de integración real para el futuro webhook de Facturación; si la reserva sigue `pendiente_pago`, la pasa a `confirmada`; si ya fue cancelada por expiración, aplica RN-RES-005 (re-confirma si hay cupo libre, o marca `"reembolso_inmediato_pendiente"` en auditoría si no)
- [ ] T008 `app/reservas/router_reservas.py` — `GET /reservas/nueva?tarifa_id=` (formulario de checkout: extras, desglose de precio visible antes de confirmar — REG-G2), `POST /reservas` (crea, redirige a detalle)
- [ ] T009 `app/reservas/router_reservas.py` — `GET /reservas/{id}` (detalle: estado, vuelo, pasajero, extras, total; si `pendiente_pago`, nota explícita de que el cobro real se conecta cuando exista Facturación — no un pago falso)
- [ ] T010 [P] `app/reservas/templates/checkout.html` — extras opcionales, precio desglosado, un solo botón de acción primaria (REG-J5)
- [ ] T011 [P] `app/reservas/templates/detalle_reserva.html`
- [ ] T012 Wire `audit_service.insertar(...)` en la creación (CU-O41)
- [ ] T013 [P] `test_crear_reserva.py` — cupo disponible crea `pendiente_pago` con `fecha_expiracion_pago` calculada (CHK001, CHK010, CHK017)
- [ ] T014 [P] `test_crear_reserva.py` — cupo agotado no crea nada y explica el motivo (CHK001, CHK010)
- [ ] T015 [P] `test_crear_reserva.py` — `precio_esperado` distinto del `precio_final` actual rechaza sin tocar cupo (CHK016, RNF-RES-001)
- [ ] T016 [P] `test_crear_reserva.py` — `confirmar_pago_reserva` pasa la reserva a `confirmada` (base para CHK015/RN-RES-006)

**Checkpoint:** un pasajero autenticado reserva un vuelo con cupo real decrementado y transparencia total de precio.

---

## Fase 2 — Crear reserva asistida (RF-RES-002)

- [ ] T017 `app/reservas/services/crear_reserva_service.py` — `crear_reserva_asistida(agente, email_pasajero, tarifa_id, precio_esperado, extras=[])`: resuelve el `pasajeros` por correo (falla explícito si no existe cuenta), reutiliza la lógica de T006 con `canal="asistida"` y `agente_id` obligatorio
- [ ] T018 `app/reservas/router_backoffice.py` — `GET /backoffice/reservas/nueva?tarifa_id=`, `POST /backoffice/reservas`, protegidos por `Depends(requiere_permiso("reservas", "crear"))` (CU-O43)
- [ ] T019 [P] `app/reservas/templates/backoffice/reserva_asistida.html` — mismo layout de backoffice (`layout_app.html`), combobox de tarifa si aplica
- [ ] T020 Wire `audit_service` con `detalle={"canal": "asistida", "agente_id": ...}`
- [ ] T021 [P] `test_crear_reserva.py` — reserva asistida exige RBAC y registra `agente_id` (CHK002, CHK019); sin permiso, bloqueada

**Checkpoint:** un Agente reserva en nombre de un pasajero ya registrado.

---

## Fase 3 — Expiración automática (RF-RES-007, CU-O44, RNF-RES-002)

- [ ] T022 `app/reservas/services/expiracion_service.py` — `expirar_pendientes()`: busca `reservas` con `estado="pendiente_pago"` y `fecha_expiracion_pago` vencida, cambia a `cancelada`, libera el cupo exacto que había tomado (incrementa `tarifas_vuelo.cupos_disponibles` — único caso de este módulo que escribe cupo sin pasar por `cupo_service`, porque es un incremento, no una verificación; documentar por qué en el propio archivo), audita cada expiración (CU-O41)
- [ ] T023 `app/reservas/router_interno.py` — `POST /internal/reservas/expirar-pendientes` (sin autenticación de usuario — llamado por el scheduler; documentar que en producción debe protegerse por red/token compartido, no implementado en esta sesión)
- [ ] T024 [P] `dags/dag_expirar_reservas_pendientes.py` — DAG delgado (`schedule` corto, p. ej. cada 5 min) que hace `POST` al endpoint interno; sin lógica de negocio propia
- [ ] T025 [P] `test_expiracion.py` — reserva vencida se cancela y su cupo se libera exactamente (CHK009, CHK013)
- [ ] T026 [P] `test_expiracion.py` — reserva no vencida no se toca
- [ ] T027 `test_expiracion.py` — RN-RES-005 (QP-04): `confirmar_pago_reserva` y `expirar_pendientes` disparados sobre la misma reserva en condición de carrera controlada; la reserva nunca queda huérfana (confirmada+expirada a la vez) — usa `pago_stub_service` directamente, no HTTP real (CHK014)

**Checkpoint:** ninguna reserva queda `pendiente_pago` indefinidamente; el cupo siempre se libera si no se paga a tiempo.

---

## Fase 4 — Consultar estado y alertas de precio (RF-RES-005, 006)

- [ ] T028 `app/reservas/router_reservas.py` — `GET /reservas` ("Mis reservas": lista solo las del usuario autenticado — CHK007)
- [ ] T029 `app/reservas/services/alertas_precio_service.py` — `crear_alerta(usuario, origen, destino, fecha_objetivo, precio_umbral)`
- [ ] T030 `app/reservas/router_alertas.py` — `GET/POST /alertas-precio`
- [ ] T031 [P] `app/reservas/templates/mis_reservas.html`, `alertas_precio.html`
- [ ] T032 [P] `test_crear_reserva.py` (o nuevo `test_consultar_reserva.py`) — `GET /reservas/{id}` de otro pasajero se bloquea (CHK007); `GET /reservas` solo muestra las propias
- [ ] T033 [P] `test_alertas_precio.py` — alerta se crea `activa` con los campos obligatorios (CHK008, CHK023)

**Checkpoint:** un pasajero ve el estado de sus reservas y puede suscribirse a alertas de precio.

---

## Fase 5 — Modificar y cancelar reserva (RF-RES-003, 004, RN-RES-002, 003)

- [ ] T034 `app/reservas/services/cancelar_reserva_service.py` — `cancelar_reserva(usuario_o_agente, reserva_id)`: bloquea si `vuelo.estado == "completado"` (mensaje exacto de la spec, RN-RES-003), cambia a `cancelada`; si la política de la tarifa permite reembolso, registra en auditoría `detalle={"reembolso_calculado": monto, "estado": "pendiente_de_modulo_facturacion"}` en vez de llamar a un servicio inexistente
- [ ] T035 `app/reservas/services/modificar_reserva_service.py` — `modificar_reserva(usuario_o_agente, reserva_id, nueva_tarifa_id=None, nuevos_extras=None)`: bloquea si `cancelada`/`completada`; si cambia vuelo/tarifa, revalida cupo (RN-RES-001) sobre la nueva tarifa; si `precio_final` nuevo difiere del original, calcula la diferencia exacta (positiva o negativa) y la registra en auditoría como `"pendiente_de_modulo_facturacion"` (RN-RES-002) — nunca se dispara nada si el precio no cambió
- [ ] T036 `app/reservas/router_reservas.py` — `PUT /reservas/{id}`, `POST /reservas/{id}/cancelar`
- [ ] T037 [P] Botón de cancelar en `detalle_reserva.html` con confirmación explícita separada (REG-J11, acción destructiva)
- [ ] T038 [P] `test_cancelar_reserva.py` — cancelación bloqueada si el vuelo está `completado`, mensaje exacto (CHK005, CHK012, CHK021)
- [ ] T039 [P] `test_cancelar_reserva.py` — cancelación normal pasa a `cancelada` y registra el cálculo de reembolso pendiente
- [ ] T040 [P] `test_modificar_reserva.py` — cambio de tarifa con precio distinto registra la diferencia exacta (CHK004, CHK011, CHK020, CHK026)
- [ ] T041 [P] `test_modificar_reserva.py` — cambio que NO afecta el precio (p. ej. solo extras) no registra ninguna diferencia (RN-RES-002, caso negativo explícito)
- [ ] T042 [P] `test_modificar_reserva.py` — modificar una reserva `cancelada`/`completada` se bloquea (CHK003)

**Checkpoint:** ciclo de vida completo de una reserva — creación, expiración, consulta, modificación y cancelación — con todos los puntos de integración hacia Facturación documentados, no simulados.

---

## Cierre

- [ ] T043 Grep de verificación de cero secretos hardcodeados sobre `app/reservas/`
- [ ] T044 Correr suite completa `pytest app/reservas/` y re-correr `app/vuelos/ app/seguridad/` para confirmar cero regresión cruzada
- [ ] T045 Repasar `checklist.md` de Reservas ítem por ítem; CHK025/CHK026 (integración cruzada con Facturación) se documentan como parcialmente cubiertos (el disparador y el monto están probados; la ejecución real del cobro no existe) en `errores-conocidos.md`, no se marcan `[x]` con un mock permanente

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (reutiliza la misma lógica de creación) y Fase 3 (necesita reservas `pendiente_pago` reales para expirar).
- Fase 4 no depende de Fase 2/3, solo de Fase 1.
- Fase 5 depende de Fase 1 (reservas existentes que modificar/cancelar) y de Vuelos (ya completo) para revalidar cupo y estado de vuelo.

---

## Fase 6/7 (futuras, no iniciadas) — CU-O81/O82, catálogo v3.0

No desglosadas en tareas todavía — ver `plan.md` sección "Extensión pendiente" y `reservas-spec.md` RF-RES-008/RF-RES-009. Se detallan en `T0xx` cuando se agende la implementación.
