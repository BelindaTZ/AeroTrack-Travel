# Checklist de Validación: Pasajeros

**Propósito:** Validar que la implementación del módulo Pasajeros cumple los RF/RNF y RN definidos en `pasajeros-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`pasajeros-spec.md`](./pasajeros-spec.md) · [`plan.md`](./plan.md)

---

**Revisado y corregido:** 2026-07-10 — la implementación original tenía varios defectos reales (`NameError` que tumbaba la búsqueda de backoffice, RBAC Nivel 2 nunca aplicado, colisión de nombre de template que anulaba silenciosamente la plantilla propia del módulo, filtro de fechas contra un campo inexistente). Ver `specs/000-sistema-general/errores-conocidos.md` para el detalle de cada uno. 14/14 tests de este módulo pasan tras la corrección; regresión cruzada de los 5 módulos confirmada.

## Requisitos funcionales

- [x] CHK001 RF-PAS-001 — El historial muestra únicamente reservas del pasajero autenticado, ordenadas por fecha de vuelo descendente. (`test_historial.py::test_historial_muestra_solo_mis_reservas`; orden descendente por `fecha_salida` aplicado en `obtener_historial`)
- [x] CHK002 RF-PAS-001 — Cada reserva del historial es navegable a su detalle (CU-O25). (`historial_reservas.html` enlaza cada tarjeta a `/reservas/{id}`)
- [x] CHK003 RF-PAS-002 — Edición de teléfono/dirección/contacto de emergencia funciona sin tocar el correo (fuera de alcance). (`test_contacto.py::test_contacto_no_permite_cambiar_correo`)
- [x] CHK004 RF-PAS-002 — Confirmación de cambio es inmediata y no bloqueante (REG-J11). (redirect con `mensaje` + `flash-bar` autodescartable de `layout_portal.html`)
- [ ] CHK005 RF-PAS-003 — Búsqueda de pasajeros por nombre/correo/documento respeta el alcance RBAC Nivel 2 del rol del usuario. **Parcial**: nombre/correo funcionan y respetan Nivel 2 (`test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado`); búsqueda por documento no es posible — `pasajeros` no tiene un campo de documento de identidad en el esquema actual.
- [x] CHK006 RF-PAS-004 — Ver/editar detalle de pasajero desde backoffice incluye verificación RBAC (CU-O43) y auditoría (CU-O41). (`test_backoffice.py::test_editar_pasajero_backoffice_audita`, `test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado`)

## Reglas de negocio

- [ ] CHK007 RN-PAS-001 — El documento de identidad, opcional en registro, se exige explícitamente al intentar reservar, no antes. Fuera de esta revisión — pertenece al flujo de registro/reserva (Seguridad/Reservas), no al código corregido en Pasajeros esta sesión.
- [ ] CHK008 RN-PAS-002 — Ninguna funcionalidad bloquea por dato de contacto desactualizado. Cierto por construcción (nada en el sistema valida `pasajeros.telefono` como precondición de otro flujo), pero no hay una prueba explícita que lo demuestre.
- [x] CHK009 RN-PAS-003 — Un Agente con restricción de Nivel 2 no puede ver/editar pasajeros fuera de su alcance. **Corregido**: `router_backoffice.py` no pasaba `tabla="pasajeros"` a `requiere_permiso(...)`, por lo que el chequeo de Nivel 2 nunca se evaluaba (Nivel 2 se salta por completo cuando `tabla` es `None` en `rbac_service.requiere_permiso`). (`test_backoffice.py::test_agente_con_restriccion_nivel2_fuera_de_alcance_bloqueado`)
- [x] CHK010 RN-PAS-004 — Toda edición de contacto, propia o desde backoffice, queda auditada identificando quién la hizo. (`test_contacto.py::test_contacto_telefono_valido_se_actualiza`, `test_backoffice.py::test_editar_pasajero_backoffice_audita`)

## No funcionales

- [x] CHK011 RNF-PAS-001 — Filtros de historial (estado, fechas) se aplican sin botón "Aplicar". **Corregido**: el filtro de fechas apuntaba a `fecha_salida` directamente sobre `reservas` (campo que no existe ahí — solo existe en `vuelos_catalogo`); movido al servicio, que ya resuelve el vuelo de cada reserva. (`test_historial.py::test_historial_filtros_instantaneos`, `test_historial_filtro_rango_fechas`)
- [x] CHK012 RNF-PAS-002 — Formato de teléfono inválido se rechaza antes de guardar, con mensaje específico. (`test_contacto.py::test_contacto_telefono_invalido_rechazado`)

## Trazabilidad de casos de uso

- [x] CHK013 CU-O14 — prueba automatizada cubre el criterio de aceptación tal como está en `pasajeros-spec.md`. (`test_historial.py`)
- [x] CHK014 CU-O15 — ídem. (`test_contacto.py`)
- [x] CHK015 CU-O16 — ídem, incluyendo el caso de bloqueo por RBAC Nivel 2.
- [ ] CHK016 RF-PAS-005 (CU-O49) *(catálogo v3.0, agregado 2026-07-18)* — gestionar documentos de viaje. *(no implementado)*
- [ ] CHK017 RF-PAS-006 (CU-O50) *(catálogo v3.0, agregado 2026-07-18)* — gestionar viajeros frecuentes guardados. *(no implementado)* (`test_backoffice.py`)

## Notas

- Marcar `[x]` solo con evidencia verificable (prueba, captura, revisión de código).
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
- Además de los CHK arriba, se corrigieron dos defectos sin CHK propio: (a) `buscar_pasajeros_backoffice` tenía un `NameError` real (variable mal referenciada) que tumbaba toda búsqueda por nombre/correo — la búsqueda por teléfono era la única que funcionaba; (b) `app/pasajeros/templates/mis_reservas.html` colisionaba de nombre con `app/reservas/templates/mis_reservas.html` — Jinja2 resolvía siempre la de Reservas (listada antes en `templating.py`), dejando la plantilla propia de Pasajeros como código muerto nunca ejecutado. Renombrada a `historial_reservas.html` y reescrita con el layout/design system correctos.
