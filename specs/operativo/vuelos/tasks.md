# Tasks: Vuelos (catálogo)

**Input:** [`plan.md`](./plan.md) · [`vuelos-spec.md`](./vuelos-spec.md) · [`checklist.md`](./checklist.md) · [`../../.specify/memory/constitution.md`](../../../.specify/memory/constitution.md)
**Código fuente:** `app/vuelos/` (+ `app/shared/` para lo transversal)
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 5), precedido por una Fase 0 de setup.

**Hallazgo importante antes de empezar (ver nota en `plan.md`):** RF-VUE-003 (generación de catálogo, CU-O19/O30) y la transición automática `programado`→`completado` por horario vencido (parte de RF-VUE-004/CU-O31) **ya están implementadas y corriendo** como el DAG de Airflow `aerotrack_travel_catalogo_vuelos` (`dags/dag_generar_catalogo_vuelos.py` + `dags/catalogo_vuelos_tasks.py` + `dags/minio_dims_reader.py`), con 150 `vuelos_catalogo`/450 `tarifas_vuelo` ya poblados y corridas reales registradas en `logs/`. Por eso la Fase 1 de abajo es de **verificación**, no de construcción — no se reescribe el DAG.

---

## Fase 0: Setup

- [ ] T001 Crear estructura `app/vuelos/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `templates/backoffice/`, `tests/`)
- [ ] T002 [P] Añadir `pyarrow` y `minio` a `requirements.txt` (sin `pandas` — no se necesita para lecturas puntuales de un Parquet pequeño)
- [ ] T003 [P] Añadir `MINIO_BUCKET_TRAVEL_DIMS` a `.env.example` (ya existe en `.env` real, falta documentarla)
- [ ] T004 Añadir servicio `app-travel` a la red `elt-network` en `docker-compose.yml` (para llegar a `minio`, igual que `airflow-webserver-travel`/`airflow-scheduler-travel`) + variables `MINIO_URL_DOCKER`/`MINIO_ACCESS`/`MINIO_SECRET`/`MINIO_BUCKET_TRAVEL_DIMS` en su entorno
- [ ] T005 `app/shared/minio_dims_reader.py` — lector de solo lectura genérico sobre Parquet sobre MinIO (`pyarrow`, sin escritura en su interfaz — REG-A2), reutilizable por cualquier módulo futuro que consulte el modelo heredado
- [ ] T006 [P] `app/vuelos/tests/conftest.py` — fixtures propias del módulo (cliente FastAPI, factory de vuelo/tarifa de prueba con limpieza posterior); reutiliza fixtures de sesión de `app/seguridad/tests/conftest.py` por import cuando aplique (admin logueado, para Fase 5)

**Checkpoint:** `app-travel` puede alcanzar tanto `pocketbase-travel` como `minio` desde dentro de Docker.

---

## Fase 1 — Generación de catálogo: verificación (RF-VUE-003, RN-VUE-001/002/003, RNF-VUE-002)

**No se construye nada nuevo de generación — se verifica lo que ya corre en `dags/`.**

- [ ] T007 `app/vuelos/tests/test_catalogo_service.py` — importa `generar_vuelos_programables` de `dags/catalogo_vuelos_tasks.py` (vía `sys.path`, mismo patrón usado para inspeccionar el DAG en esta sesión) y verifica sobre una corrida real: todo vuelo recién creado nace `estado="programado"` y `generado_por="sistema"` (RN-VUE-001, CHK009)
- [ ] T008 [P] `test_catalogo_service.py` — verifica que cada `vuelo_id` recién creado tiene exactamente 3 `tarifas_vuelo` (Light/Standard/Flex) con `precio_final` distinto entre sí y distinto de `precio_base` (RN-VUE-002, CHK010)
- [ ] T009 [P] `test_catalogo_service.py` — inspección de código: ni `dags/minio_dims_reader.py` ni `dags/catalogo_vuelos_tasks.py` contienen ninguna llamada de escritura a MinIO (`put_object`/`remove_object`/`copy_object`) — RNF-VUE-002, RN-VUE-003, CHK011, CHK016, CHK020 (parte "sin escritura en heredado")

**Checkpoint:** catálogo ya poblado y sus invariantes de generación quedan probados; nada bloqueado para las fases siguientes.

---

## Fase 2 — Búsqueda y detalle (RF-VUE-001, 002)

- [ ] T010 `app/vuelos/repositories/dims_reader.py` — `resolver_aeropuerto(codigo) -> str` (usa `app/shared/minio_dims_reader.py` sobre `dim_aeropuerto`, cachea en memoria — el modelo heredado es estático dentro de una corrida del proceso)
- [ ] T011 `app/vuelos/repositories/vuelos_repo.py` — encapsula consultas de `vuelos_catalogo`, `tarifas_vuelo`, `niveles_tarifa`, `aerolineas`, `politicas_reembolso` sobre `app/shared/pocketbase_client.py`
- [ ] T012 [P] `app/vuelos/schemas.py` — modelos Pydantic de request/response de búsqueda y detalle
- [ ] T013 `app/vuelos/router_busqueda.py` — `GET /vuelos/buscar` (origen, destino, fecha, pasajeros obligatorios — acción explícita con botón propio; filtros secundarios de aerolínea/horario y orden por query params, sin sesión requerida); mensaje claro si no hay resultados
- [ ] T014 `app/vuelos/router_busqueda.py` — `GET /vuelos/{id}` (detalle completo + niveles de tarifa con precio final, equipaje, cambios y política de reembolso — REG-G2)
- [ ] T015 [P] `app/vuelos/templates/buscar_vuelos.html` — filtros secundarios instantáneos sin botón "Aplicar" (REG-J9); combobox con búsqueda si el listado de aerolíneas supera ~8 opciones
- [ ] T016 [P] `app/vuelos/templates/detalle_vuelo.html` — los 3 niveles de tarifa visibles con precio final desglosado antes de cualquier acción de reservar (REG-G2)
- [ ] T017 [P] `test_busqueda.py` — CU-O17: filtra por origen/destino/fecha (CHK001), sin resultados muestra mensaje claro (CHK001), filtro secundario sin botón "Aplicar" (CHK002)
- [ ] T018 [P] `test_busqueda.py` — CU-O18: detalle muestra los 3 niveles de tarifa con precio/equipaje/cambios/política de reembolso (CHK003); origen/destino se muestran legibles vía `dims_reader`, nunca solo el código IATA (CHK015, RNF-VUE-001)

**Checkpoint:** un pasajero (autenticado o no) busca y compara vuelos con transparencia total de precio.

---

## Fase 3 — Verificación de cupo (RF-VUE-005, RNF-VUE-003)

- [ ] T019 `app/vuelos/services/cupo_service.py` — `verificar_y_reservar_cupo(tarifa_id, cantidad=1)`: lock en memoria (`asyncio.Lock` por `tarifa_id`) que serializa lectura+decremento de `cupos_disponibles` dentro del proceso; documentar en el propio archivo el límite de este mecanismo si el despliegue pasara a múltiples réplicas (ver nota en `plan.md`)
- [ ] T020 [P] `test_cupo_service.py` — cupo > 0 decrementa y confirma disponibilidad (CHK006 parte 1)
- [ ] T021 [P] `test_cupo_service.py` — cupo = 0 responde sin disponibilidad sin alterar el dato (CHK006 parte 2)
- [ ] T022 `test_cupo_service.py` — prueba de concurrencia: 50 solicitudes simultáneas (`asyncio.gather`) sobre una tarifa con cupo fijo N; exactamente N tienen éxito, el resto recibe "no disponible", el cupo final nunca es negativo (CHK012, CHK017, RNF-VUE-003)

**Checkpoint:** `cupo_service.verificar_y_reservar_cupo` queda listo para que Reservas lo invoque como precondición obligatoria (CU-O45).

---

## Fase 4 — Actualización de estado (RF-VUE-004)

- [ ] T023 `app/vuelos/services/estado_service.py` — `actualizar_estado(vuelo_id, nuevo_estado, origen="automatico")`: valida que `nuevo_estado` sea uno del enum `estado_vuelo`, actualiza `vuelos_catalogo.estado` + `fecha_actualizacion_estado`; punto de escritura genérico que CU-O48 (Fase 5) y, más adelante, Disrupciones reutilizarán
- [ ] T024 [P] `test_estado_service.py` — actualiza estado y `fecha_actualizacion_estado` queda registrada (CHK005)
- [ ] T025 [P] `test_estado_service.py` — estado fuera del enum `estado_vuelo` se rechaza sin tocar el registro

**Checkpoint:** existe un punto de escritura único y genérico para `vuelos_catalogo.estado`, listo para consumirse desde CU-O48 y, cuando exista, desde Disrupciones.

---

## Fase 5 — Ajuste puntual excepcional para demo (RF-VUE-006, CU-O48)

**Precondición ya cumplida:** Seguridad Fase 2 (`session_service`, `rbac_service`, `audit_service`) y Fase 4 de este módulo (`estado_service`).

- [ ] T026 `app/vuelos/services/forzar_estado_service.py` — reutiliza `estado_service.actualizar_estado(..., origen="manual")`, exige `motivo` no vacío (RN-VUE-006) antes de tocar cualquier dato, marca `generado_por="manual"` en el vuelo ajustado (RN-VUE-005)
- [ ] T027 `app/vuelos/router_backoffice.py` — `POST /backoffice/vuelos/{id}/forzar-estado`, protegido por `Depends(verificar_sesion)` + `Depends(requiere_permiso("vuelos_catalogo", "editar"))` (primer consumidor real, fuera de Seguridad, de los 3 servicios transversales — cierra el gap de prueba cruzada documentado en `seguridad/checklist.md` CHK048)
- [ ] T028 Wire `audit_service.insertar(...)` en el ajuste (CU-O41) con `detalle={"motivo": ..., "origen": "demo"}`
- [ ] T029 Si el nuevo estado es una disrupción (`retrasado`/`cancelado`/`desviado`), registrar en el detalle de auditoría la marca de "notificación pendiente de Disrupciones" — el disparo real del flujo de notificación no puede implementarse todavía (Disrupciones fuera de alcance de esta sesión); documentar explícitamente como pendiente en el código y en `errores-conocidos.md`, no simularlo silenciosamente como si ya disparara algo real
- [ ] T030 [P] `app/vuelos/templates/backoffice/forzar_estado.html` — selector de vuelo (combobox con búsqueda, REG-J9, dado que el catálogo ya tiene 150 vuelos — muy por encima del umbral de ~8), campo de motivo obligatorio, confirmación explícita antes de aplicar (REG-J11, acción que altera datos de demo)
- [ ] T031 [P] `test_forzar_estado.py` — sin sesión válida, bloqueado antes de tocar datos (CHK007 parte 1)
- [ ] T032 [P] `test_forzar_estado.py` — con sesión pero sin permiso RBAC (usuario con rol Pasajero/Agente sin `editar` sobre `vuelos_catalogo`), bloqueado (CHK007 parte 2)
- [ ] T033 [P] `test_forzar_estado.py` — con sesión y RBAC pero sin motivo, rechazado sin mutar el vuelo (CHK007 parte 3, CHK014)
- [ ] T034 `test_forzar_estado.py` — camino feliz: vuelo queda con el nuevo estado, `generado_por="manual"` (CHK013), y un registro de auditoría con el motivo (CHK008)
- [ ] T035 `test_forzar_estado.py` — ninguna prueba de CU-O19/O20 (Fases 1 y 4) depende de que CU-O48 exista — verificado por construcción (test_catalogo_service.py y test_estado_service.py no importan nada de `forzar_estado_service.py`)

**Checkpoint:** un Administrador puede preparar un escenario de demo reproducible; el flujo automático normal (Fases 1-4) sigue funcionando exactamente igual con o sin esta fase.

---

## Cierre

- [ ] T036 Grep de verificación de cero secretos hardcodeados sobre `app/vuelos/` y `app/shared/minio_dims_reader.py`
- [ ] T037 Correr suite completa `pytest app/vuelos/` (y re-correr `app/seguridad/` para confirmar cero regresión cruzada)
- [ ] T038 Repasar `checklist.md` de Vuelos ítem por ítem (igual que se hizo para Seguridad); actualizar `seguridad/checklist.md` CHK048 y `errores-conocidos.md` con el resultado del primer consumo cruzado real de los servicios transversales

---

## Fases 6-9 (futuras, no iniciadas) — catálogo v3.1

No desglosadas en tareas todavía — ver `plan.md` sección "Extensión pendiente" y `vuelos-spec.md` RF-VUE-007 a 013 (CU-O51/O52/O53/O114–O117).

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 es independiente de Fase 0 en términos de código (no construye nada), pero sus tests corren después de Fase 0 (fixtures/entorno).
- Fase 2 no depende de Fase 1 para funcionar (el catálogo ya existe), pero sí para tener datos realistas que buscar.
- Fase 3 y Fase 4 son independientes entre sí y de Fase 2 — pueden implementarse en paralelo.
- Fase 5 depende de Fase 4 (reutiliza `estado_service`) y de Seguridad Fase 2 (ya completa).
