# Tasks: Disrupciones y Notificaciones

**Input:** [`plan.md`](./plan.md) · [`disrupciones-spec.md`](./disrupciones-spec.md) · [`checklist.md`](./checklist.md) · [`reglas.md`](../../000-sistema-general/reglas.md)
**Código fuente:** `app/disrupciones/` (+ imports directos de `app.vuelos.*`, `app.reservas.*`, `app.seguridad.*`, `app.facturacion.*`, `app.shared.*`)
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 5), precedido por una Fase 0 de setup.

**Nota de alcance:** este módulo es dueño de `disrupciones` y `notificaciones`. Lee `vuelos_catalogo` (Vuelos), `reservas` (Reservas), `pasajeros`/`usuarios` (Pasajeros/Seguridad), `configuracion_sistema` (Seguridad). Dispara `estado_service.actualizar_estado` (Vuelos) y `reembolso_service.procesar_reembolso` (Facturación) cuando aplica. Las integraciones externas (API de estado de vuelo, Gmail API, envío de email/SMS) viven detrás de interfaces abstractas en `integrations/` (REG-F1).

---

## Fase 0: Setup

- [ ] T001 Crear estructura `app/disrupciones/` (`__init__.py`, `services/`, `integrations/`, `repositories/`, `templates/`, `tests/`)
- [ ] T002 [P] `app/disrupciones/repositories/disrupciones_repo.py` — encapsula consultas de `disrupciones`, `notificaciones` sobre `app/shared/pocketbase_client.py`
- [ ] T003 [P] `app/disrupciones/schemas.py` — modelos Pydantic de request/response (disrupción, notificación, historial)
- [ ] T004 [P] `app/disrupciones/integrations/flight_status_client.py` — interfaz abstracta `FlightStatusClient` con métodos `consultar_estado(numero_vuelo, fecha) -> dict | None` y `esta_disponible() -> bool`; Lee timeout/reintento de `configuracion_sistema` (REG-F2)
- [ ] T005 [P] `app/disrupciones/integrations/gmail_client.py` — interfaz abstracta `GmailClient` con método `leer_correos_nuevos(ultimas_horas=24) -> list[dict]`; Lee credenciales OAuth de `configuracion_sistema` (REG-B3)
- [ ] T006 [P] `app/disrupciones/integrations/notification_sender.py` — interfaz abstracta `NotificationSender` con método `enviar(canal, destino, asunto, cuerpo) -> bool`; abstrae email/SMS (REG-F1)
- [ ] T007 [P] `app/disrupciones/tests/conftest.py` — fixtures propias (cliente FastAPI, factory de disrupción de prueba, mocks de las 3 interfaces)
- [ ] T008 Añadir `app/disrupciones/templates` a `app/shared/templating.py`

**Checkpoint:** estructura lista; interfaces abstractas definidas, sin implementación concreta todavía.

---

## Fase 1 — Consultar API de estado de vuelo real, con degradación (RF-DIS-001, RNF-DIS-001, RNF-DIS-002)

- [ ] T009 `app/disrupciones/integrations/flight_status_client.py` — implementación concreta `AviationStackClient` (o AeroDataBox) que usa `httpx`; lee API key de `configuracion_sistema` (REG-B3), timeout y política de reintento de `configuracion_sistema` (REG-F2, nunca hardcodeado); método `consultar_estado` retorna dict con `estado_api`, `retraso_minutos`, `nueva_hora_llegada` o `None` si la API falla
- [ ] T010 `app/disrupciones/services/api_estado_vuelo_service.py` — `consultar_estados_cercanos()`: busca en `vuelos_catalogo` vuelos con `estado` != `completado` y `fecha_salida` dentro de la ventana configurable (lee de `configuracion_sistema`), para cada uno invoca `flight_status_client.consultar_estado`; si el estado de la API difiere del registrado en `vuelos_catalogo`, crea registro en `disrupciones` con `fuente_deteccion = api_real` y tipo de cambio correspondiente; invoca `estado_service.actualizar_estado` (Vuelos) cuando hay cambio real
- [ ] T011 `app/disrupciones/services/api_estado_vuelo_service.py` — manejo de degradación (RNF-DIS-001): si `flight_status_client.esta_disponible()` retorna `False` o la llamada lanza excepción, el sistema registra el evento de degradación pero **no falla** — continúa operando; el resto de la función (procesamiento de los vuelos que sí respondieron) se ejecuta normalmente
- [ ] T012 `app/disrupciones/router_interno.py` — `POST /internal/disrupciones/consultar-api` (sin auth de usuario — job de Airflow; documentar que en producción debe protegerse por red/token, REG-F3)
- [ ] T013 [P] `app/disrupciones/dags/consultar_estado_vuelo_dag.py` — DAG delgado que hace `POST` al endpoint interno; sin lógica de negocio propia (o reutiliza `dags/dag_estado_real_vuelo.py` existente)
- [ ] T014 [P] `app/disrupciones/tests/test_api_estado_vuelo.py` — estado API distinto al registrado genera disrupción con `fuente_deteccion = api_real` (CHK001, CHK017)
- [ ] T015 [P] `app/disrupciones/tests/test_api_estado_vuelo.py` — API caída: sistema registra degradación y continúa sin excepción (CHK012, CHK014, RNF-DIS-001)
- [ ] T016 [P] `app/disrupciones/tests/test_api_estado_vuelo.py` — timeout y reintento se leen de `configuracion_sistema`, nunca hardcodeados (CHK015, RNF-DIS-002)
- [ ] T017 [P] `app/disrupciones/tests/test_api_estado_vuelo.py` — API retorna mismo estado que el registrado: no se genera disrupción (caso negativo)

**Checkpoint:** la consulta periódica a la API real detecta discrepancias y se degrada ordenadamente sin fallar.

---

## Fase 2 — Monitor de correo y detección (RF-DIS-002, 003, RN-DIS-001)

- [ ] T018 `app/disrupciones/integrations/gmail_client.py` — implementación concreta `GmailClientImpl` que usa Gmail API (OAuth); lee credenciales de `configuracion_sistema` (REG-B3); método `leer_correos_nuevos` retorna lista de `{asunto, remitente, cuerpo_texto, fecha}`
- [ ] T019 `app/disrupciones/services/deteccion_service.py` — `parsear_correo_a_disrupcion(correo) -> dict | None`: identifica si el correo corresponde a un cambio de itinerario (retraso, cancelación, cambio de horario, cambio de puerta, desvío); extrae `numero_vuelo`, `tipo_cambio`, `detalle`; si no corresponde a ningún vuelo conocido en `vuelos_catalogo`, retorna `None` y marca para revisión manual (RN-DIS-001, QP-07)
- [ ] T020 `app/disrupciones/services/monitor_correo_service.py` — `monitorear_correo()`: invoca `gmail_client.leer_correos_nuevos`, para cada correo invoca `deteccion_service.parsear_correo_a_disrupcion`; si retorna un dict válido, crea registro en `disrupciones` con `fuente_deteccion = monitor_correo`
- [ ] T021 `app/disrupciones/router_interno.py` — extiende: `POST /internal/disrupciones/monitorear-correo`
- [ ] T022 [P] `app/disrupciones/dags/monitorear_correo_dag.py` — DAG delgado que hace `POST` al endpoint interno (o reutiliza `dags/dag_monitor_correo.py` existente)
- [ ] T023 [P] `app/disrupciones/tests/test_monitor_correo.py` — correo de aerolínea con cambio válido genera disrupción con `fuente_deteccion = monitor_correo` (CHK002, CHK018)
- [ ] T024 [P] `app/disrupciones/tests/test_monitor_correo.py` — parseo identifica correctamente los 5 tipos de cambio (CHK003)
- [ ] T025 [P] `app/disrupciones/tests/test_monitor_correo.py` — correo sin vuelo/reserva activa asociada se descarta sin notificar, se marca para revisión (CHK008, RN-DIS-001, QP-07)
- [ ] T026 [P] `app/disrupciones/tests/test_monitor_correo.py` — correo que no es de aerolínea se descarta silenciosamente

**Checkpoint:** el monitor de correo detecta avisos de aerolínea y los convierte en disrupciones; los no reconocidos se descartan correctamente.

---

## Fase 3 — Notificar al pasajero (RF-DIS-004, RN-DIS-002, RN-DIS-003)

- [ ] T027 `app/disrupciones/services/notificacion_service.py` — `procesar_disrupcion(disrupcion_id)`: lee la disrupción, busca reservas confirmadas asociadas al vuelo, para cada pasajero titular y acompañantes obtiene datos de contacto de `pasajeros` (Pasajeros), genera registro en `notificaciones` con canal configurado; si el tipo es `cancelacion`, dispara `<<extend>>` CU-O37 (llama a `reembolso_service.procesar_reembolso` de Facturación, RN-DIS-003, QP-12); para otros tipos (retraso, cambio_horario, etc.), solo notifica sin disparar reembolso
- [ ] T028 `app/disrupciones/services/notificacion_service.py` — `aplicar_precedencia(disrupciones) -> list[dict]` (RN-DIS-002, QP-02): función pura que recibe una lista de disrupciones para el mismo vuelo + tipo_cambio, aplica precedencia `api_real > monitor_correo > simulador_estadistico`, retorna solo la de mayor precedencia; deduplica por `(vuelo_id, tipo_cambio)` antes de generar notificaciones
- [ ] T029 Wire `notificacion_service` en `api_estado_vuelo_service` y `monitor_correo_service`: después de crear la disrupción, invoca `procesar_disrupcion` (converge ambas fuentes — REG-E1)
- [ ] T030 `app/disrupciones/router_interno.py` — extiende: `POST /internal/notificaciones/enviar` (dispara `procesar_disrupcion`)
- [ ] T031 Wire `audit_service.insertar` (CU-O41) en la generación de notificaciones
- [ ] T032 [P] `app/disrupciones/tests/test_notificacion.py` — disrupción genera notificación a titular y acompañantes de reservas confirmadas (CHK004, CHK020)
- [ ] T033 [P] `app/disrupciones/tests/test_notificacion.py` — precedencia/deduplicación: dos fuentes detectando el mismo cambio producen una sola notificación, respetando `api_real > monitor_correo` (CHK009, RN-DIS-002, QP-02)
- [ ] T034 [P] `app/disrupciones/tests/test_notificacion.py` — `cancelacion` dispara reembolso; `retraso`/`cambio_horario`/`cambio_puerta`/`desvio` no lo disparan (CHK005, CHK010, RN-DIS-003, QP-12)
- [ ] T035 [P] `app/disrupciones/tests/test_notificacion.py` — toda disrupción activa genera al menos un intento de notificación (CHK011, RN-DIS-004)

**Checkpoint:** toda disrupción detectada por cualquiera de las dos fuentes converge en una notificación deduplicada al pasajero, con reembolso condicionado al tipo.

---

## Fase 4 — Reintento de envío fallido (RF-DIS-006, RN-DIS-006)

- [ ] T036 `app/disrupciones/services/reintento_service.py` — `reintentar_notificacion(notificacion_id)`: lee política de reintentos de `configuracion_sistema` (número de intentos, intervalo — REG-F2); si `notificaciones.estado_envio == "fallido"`, reintentar usando `notification_sender.enviar`; si agota reintentos, marca `estado_envio = "fallido_definitivo"` y registra detalle (QP-09, RN-DIS-006)
- [ ] T037 `app/disrupciones/router_interno.py` — extiende: `POST /internal/notificaciones/{id}/reintentar`
- [ ] T038 `app/disrupciones/services/notificacion_service.py` — después de generar la notificación, invoca `notification_sender.enviar`; si falla, marca `estado_envio = "fallido"` y dispara `reintento_service.reintentar_notificacion` inmediatamente (primer reintento)
- [ ] T039 [P] `app/disrupciones/tests/test_reintento.py` — notificación fallida se reintenta según política configurada; tras agotar reintentos, queda constancia visible del fallo definitivo (CHK007, CHK022)
- [ ] T040 [P] `app/disrupciones/tests/test_reintento.py` — no existe bucle de reintento indefinido: el código tiene un límite explícito verificable (CHK013, RN-DIS-006)
- [ ] T041 [P] `app/disrupciones/tests/test_reintento.py` — caída del proveedor de correo/SMS no afecta otras funcionalidades del sistema (CHK016, RNF-DIS-003)

**Checkpoint:** las notificaciones fallidas se reintentan con límite configurable; el fallo definitivo queda registrado y visible.

---

## Fase 5 — Historial de notificaciones (RF-DIS-005)

- [ ] T042 `app/disrupciones/router_notificaciones.py` — `GET /notificaciones` (pasajero: solo las suyas, sesión requerida), `GET /backoffice/notificaciones` (Agente/Admin: todas dentro de su alcance RBAC, sesión + permiso requeridos); filtros instantáneos por canal, estado de envío, rango de fechas (REG-J9)
- [ ] T043 [P] `app/disrupciones/templates/historial_notificaciones.html` — tabla con filtros instantáneos, banner de estado con color + ícono + texto (REG-J7)
- [ ] T044 [P] `app/disrupciones/tests/test_historial.py` — pasajero ve solo sus notificaciones (CHK006)
- [ ] T045 [P] `app/disrupciones/tests/test_historial.py` — Agente ve notificaciones de pasajeros dentro de su alcance RBAC; fuera de alcance, no las ve (CHK006)
- [ ] T046 [P] `app/disrupciones/tests/test_historial.py` — filtros instantáneos funcionan sin botón "Aplicar" (CHK006, REG-J9)

**Checkpoint:** pasajero y Agente consultan el historial de notificaciones con filtros instantáneos y respeto de alcance.

---

## Cierre

- [ ] T047 Grep de verificación de cero secretos hardcodeados sobre `app/disrupciones/` (CHK015)
- [ ] T048 Correr suite completa `pytest app/disrupciones/` y re-correr `app/seguridad/ app/vuelos/ app/reservas/ app/facturacion/` para confirmar cero regresión cruzada
- [ ] T049 Repasar `checklist.md` de Disrupciones ítem por ítem; documentar en `errores-conocidos.md` cualquier hallazgo

---

## Fase 6/7 (futuras, no iniciadas) — CU-O83/O84, catálogo v3.0

No desglosadas en tareas todavía — ver `plan.md` sección "Extensión pendiente" y `disrupciones-spec.md` RF-DIS-007/RF-DIS-008.

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 y Fase 2 son independientes entre sí (API real vs. monitor de correo) — pueden implementarse en paralelo.
- Fase 3 depende de Fase 1 y Fase 2 (converge ambas fuentes) y de Reservas (ya completo) para reservas confirmadas, y de Pasajeros (este módulo) para datos de contacto.
- Fase 4 depende de Fase 3 (necesita notificaciones reales que fallen).
- Fase 5 depende de Fase 3 (necesita notificaciones generadas) y de Seguridad Fase 2 (RBAC para backoffice — ya completa).