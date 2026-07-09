# Errores conocidos — Sistema AeroTrack Travel (Nivel Operativo)

> Se completa durante la implementación de cada módulo: cada entrada debe registrar el error encontrado, el módulo/CU afectado, la causa raíz y el estado de resolución (abierto / mitigado / cerrado), para no perder el conocimiento acumulado durante el desarrollo.

## Módulo Seguridad (implementado 2026-07-09)

- **[abierto] RF-SEG-014 — alerta de fallo de auditoría es solo log, no notificación visible.**
  Causa raíz: no existe todavía ningún canal de notificaciones internas a Administrador (pertenece a un nivel Táctico/futuro). `audit_service.insertar()` hace `logger.critical(...)` cuando la inserción falla, en vez de una alerta accionable en la UI. Mitigado por ahora: el log crítico es monitoreable a nivel de infraestructura.

- **[abierto] RN-SEG-011 — retención de datos personales sin reservas/pagos reales que verificar.**
  Causa raíz: Reservas y Facturación están fuera de alcance de esta sesión. `POST /mi-perfil/solicitar-eliminacion` registra la solicitud en auditoría pero no ejecuta ninguna verificación de retención real. Se debe revisar este endpoint cuando Reservas/Facturación existan, para conectar la verificación real de "reservas o pagos en curso".

- **[abierto] RNF-SEG-002/003 — objetivos de rendimiento (login <1s, verificación de sesión <50ms) no medidos.**
  Causa raíz: sin prueba de carga ni profiling en esta sesión. `verificar_sesion` hace un round-trip HTTP a PocketBase (`auth-refresh`) en cada solicitud autenticada, lo cual es la implementación correcta funcionalmente pero no está optimizada para el objetivo de <50ms — una futura optimización razonable es cachear la validación del JWT localmente (con invalidación activa) en vez de repetir el round-trip. Pendiente de una sesión de medición dedicada.

- **[abierto] REG-J6 — banner de alcance RBAC Nivel 2 solo implementado en `admin/rol_editar.html`.**
  Causa raíz: es la única pantalla de Seguridad hoy donde Nivel 2 es relevante para quien la edita. Falta el mismo patrón en pantallas donde el usuario *actuante* navega bajo su propia restricción Nivel 2 — no hay ninguna todavía dentro de Seguridad; revisar cuando otros módulos (Reservas, Facturación) construyan sus propias pantallas de backoffice sobre restricciones Nivel 2 reales.

- **[abierto] REG-J8/J11 — accesibilidad y animaciones de feedback no verificadas en navegador real.**
  Causa raíz: sesión de implementación vía CLI, sin herramienta de accesibilidad ni navegador disponible. Verificar contraste WCAG AA y comportamiento de autodescartado antes de considerar el módulo listo visualmente.

- **[cerrado 2026-07-09] CHK048 — sin prueba de integración cruzada genuina entre módulos.**
  Causa raíz (histórica): Seguridad era el primer módulo implementado; no existía todavía un segundo módulo real que consumiera `session_service`/`rbac_service`/`audit_service` desde fuera de Seguridad. **Resuelto por el módulo Vuelos**: `app/vuelos/router_backoffice.py` (CU-O48) importa y usa los 3 servicios de forma real — `Depends(requiere_permiso("vuelos_catalogo", "editar", "vuelos_catalogo"))` y `AuditService().insertar(...)` — probado en `app/vuelos/tests/test_forzar_estado.py` contra `pocketbase-travel` real, incluyendo los 3 casos de bloqueo (sin sesión, sin RBAC, sin motivo).

## Módulo Vuelos (catálogo) (implementado 2026-07-09)

- **[cerrado 2026-07-09] RF-VUE-005 — bug de esquema heredado bloqueaba "cupo agotado".**
  Causa raíz: `tarifas_vuelo.cupos_disponibles` fue creado como campo numérico `required=true` en una sesión anterior (antes de que este módulo se implementara). PocketBase 0.22 valida "required" en campos numéricos tratando `0` como valor ausente ("Missing required value"), lo que impedía representar el caso de negocio más importante de RF-VUE-005 (cupo en cero). Corregido con `scripts/pb_schema_vuelos_fix.py` (idempotente): se cambió el campo a `required=false`. Sin este fix, ninguna prueba de concurrencia ni de "cupo agotado" podía pasar — no es un defecto de la implementación de Vuelos, sino del esquema preexistente.

- **[abierto] RF-VUE-001 — "filtrar/ordenar por escalas" no es implementable con el modelo de datos actual.**
  Causa raíz: `vuelos_catalogo` no tiene ningún campo de escalas/paradas; el generador de catálogo (`dags/catalogo_vuelos_tasks.py`) solo crea rutas directas punto a punto entre hubs. Implementado: ordenar por precio/duración, filtrar por aerolínea/horario. Si en el futuro se agregan vuelos con escalas, este RF necesita revisión del modelo de datos primero (un vuelo con escalas probablemente requiere una entidad "tramo" separada, no un campo simple en `vuelos_catalogo`).

- **[abierto] RF-VUE-004/RF-VUE-006 — "invocable desde Disrupciones" y "dispara flujo de notificación" no tienen un caller real todavía.**
  Causa raíz: Disrupciones está fuera de alcance de esta sesión. `estado_service.actualizar_estado` es genérico y está listo para ser importado; `router_backoffice.py` (CU-O48) ya registra en el detalle de auditoría `"notificacion": "pendiente_de_modulo_disrupciones"` en vez de simular un disparo real. Cerrar cuando Disrupciones exista y consuma `estado_service` de verdad.

## Módulo Reservas (implementado 2026-07-09)

- **[cerrado 2026-07-09] RN-RES-005 — condición de carrera real entre pago y expiración, encontrada durante la implementación (no en producción).**
  Causa raíz: la primera versión de `pago_stub_service.confirmar_pago_reserva` y `expiracion_service.expirar_pendientes` leían el estado de la reserva y escribían sin ningún mecanismo de exclusión mutua entre ellas. En una intercalación real de corrutinas (probada con `asyncio.gather` en `test_expiracion.py`), un pago podía leer "pendiente_pago" justo antes de que la expiración cancelara la reserva y liberara su cupo, y luego escribir "confirmada" a ciegas sobre ese estado ya obsoleto — una reserva confirmada sin cupo real detrás. Corregido con `services/reserva_locks.py`, un lock en memoria por `reserva_id` (mismo patrón que `cupo_service` de Vuelos), usado por ambas rutas.

- **[abierto] RF-RES-002 (parcial) — reserva asistida no tiene una pantalla de búsqueda de pasajeros.**
  Causa raíz: Pasajeros fuera de alcance. El Agente debe conocer el correo exacto del pasajero para crear una reserva asistida (`backoffice/reserva_asistida.html`); no hay autocompletado ni búsqueda por nombre/documento. Revisar cuando Pasajeros exista.

- **[abierto] RF-RES-001 — reservas con varios pasajeros (acompañantes) no implementado.**
  Causa raíz: `reserva_pasajeros.pasajero_id` es una relación a `pasajeros` (no datos inline); sin una búsqueda de pasajeros real, esta sesión solo crea el `reserva_pasajeros` del titular. Agregar acompañantes queda para cuando exista Pasajeros.

- **[cerrado 2026-07-09] RF-RES-001/003/004 (CU-O32, CU-O37, CU-O47) — pago real, reembolso y cobro/reembolso de diferencia no existían.**
  Causa raíz (histórica): Facturación estaba fuera de alcance. `pago_stub_service.confirmar_pago_reserva` era el punto de integración real para el futuro webhook de Stripe (ya probado con RN-RES-005/QP-04). `cancelar_reserva_service`/`modificar_reserva_service` calculaban el monto exacto de reembolso/diferencia y lo dejaban en auditoría como `"pendiente_de_modulo_facturacion"`. **Resuelto por el módulo Facturación**: `app/facturacion/services/pago_service.py`, `reembolso_service.py` y `diferencia_tarifa_service.py` implementan los 3 flujos con cargos/reembolsos reales contra Stripe test mode; `cancelar_reserva_service.py` y `modificar_reserva_service.py` los llaman de verdad in-process (mismo patrón que `confirmar_pago_reserva`). Probado en `app/facturacion/tests/` y en los tests actualizados de `app/reservas/tests/test_cancelar_reserva.py` y `test_modificar_reserva.py`.

- **[abierto] `POST /internal/reservas/expirar-pendientes` sin autenticación.**
  Causa raíz: el endpoint que dispara CU-O44 no exige ningún token — lo llama `dags/dag_expirar_reservas_pendientes.py` por HTTP dentro de la red interna de Docker. En un despliegue expuesto a internet, este endpoint debe protegerse (token compartido o bloqueo de red) antes de ir a producción; no implementado en esta sesión.

## Módulo Facturación (implementado 2026-07-09)

- **[abierto] RN-FAC-006 (CHK017) — condición de carrera entre confirmación de pago y expiración de reserva no probada end-to-end con Facturación real.**
  Causa raíz: Reservas ya protege `confirmar_pago_reserva` vs `expirar_pendientes` con un lock por `reserva_id` (`reserva_locks.py`, ver módulo Reservas arriba), pero esta sesión no construyó una prueba de concurrencia real que dispare un pago de Facturación (con cargo real en Stripe) exactamente cuando el scheduler de expiración corre sobre la misma reserva. Riesgo real si el lock de Reservas tuviera algún hueco no cubierto por las pruebas existentes de ese módulo. Pendiente de una prueba de integración cruzada Facturación↔Reservas dedicada.

- **[abierto] RN-FAC-004 (CHK015) — "cargo de servicio" inmediato vs comisión diferida no existen como eventos contables separados.**
  Causa raíz: ajuste de alcance documentado en `plan.md` — `pagos.monto` es el `total_pagar` completo de la reserva, sin partición de un cargo de servicio propio. Si el negocio real necesita distinguir ambos conceptos contablemente, requiere un campo/colección nuevo y una revisión de `pago_service.procesar_pago`.

- **[abierto] RNF-FAC-002 (CHK019) — no hay receptor de webhooks de Stripe; "reenviar el mismo evento" no aplica literalmente.**
  Causa raíz: ajuste de alcance — el checkout usa PaymentMethod IDs de prueba de Stripe vía SDK síncrono (`pm_card_visa` / `pm_card_visa_chargeDeclined`), no Stripe Elements ni un flujo de webhooks asíncrono. La idempotencia de aplicación sí está probada (`test_pago_idempotente_no_genera_segundo_cargo`), pero el escenario específico de RNF-FAC-002 (un webhook de Stripe reenviado) requeriría construir un receptor de webhooks real, fuera de alcance de esta sesión.

- **[abierto] RF-FAC-010 (CHK011) — itinerario/e-ticket no incluye pasajeros individuales.**
  Causa raíz: Pasajeros fuera de alcance de esta sesión. `documentos_service.generar_pdf_itinerario` incluye reserva/vuelo/aerolínea reales, pero `reserva_pasajeros` no se resuelve a nombres de pasajero en el PDF (el módulo Pasajeros es quien posee esos datos). Revisar cuando Pasajeros exista.

- **[abierto] Disrupciones (CU-O37 disparado por interrupción de vuelo) sigue fuera de alcance.**
  Causa raíz: Disrupciones no existe todavía. El reembolso implementado esta sesión (`reembolso_service.procesar_reembolso`) solo cubre el camino de cancelación voluntaria del pasajero/agente (`cancelar_reserva_service`), no una interrupción de vuelo iniciada por la aerolínea. Cuando Disrupciones exista, debe poder invocar `reembolso_service.procesar_reembolso` con su propio `motivo`, reutilizando el mismo mecanismo — no debería requerir un nuevo servicio de reembolso.
