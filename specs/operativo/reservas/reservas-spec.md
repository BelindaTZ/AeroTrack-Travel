# Especificación Operativa — Reservas

**Módulo:** Reservas
**Prefijo:** RES
**Código fuente:** `app/reservas/`
**Casos de uso cubiertos:** CU-O21 (Crear reserva autoservicio), CU-O22 (Crear reserva asistida), CU-O23 (Modificar reserva), CU-O24 (Cancelar reserva), CU-O25 (Consultar estado de una reserva), CU-O26 (Crear alerta de precio), CU-O44 (Expirar reserva pendiente de pago), CU-O45 (Verificar disponibilidad de vuelo/cupo — RN, orquestación/negocio), CU-O47 (Cobrar/reembolsar diferencia de tarifa — RN, disparador/negocio)
**Actor:** Pasajero / Agente / Sistema (automático, temporizador)

---

## Funcionalidad 1: Crear reserva — autoservicio y asistida (CU-O21, CU-O22)

Núcleo transaccional del negocio: convierte un vuelo/tarifa seleccionado en una reserva confirmable.

### RF-RES-001 — Crear reserva (autoservicio)
El sistema debe permitir a un pasajero autenticado, tras seleccionar vuelo y nivel de tarifa (CU-O17/O18), ingresar datos de pasajero(s) si viajan varios y extras opcionales (equipaje, asiento, seguro), y confirmar. Antes de crear la reserva, invoca la verificación de disponibilidad de cupo (CU-O45, mecanismo en `vuelos-spec.md`); si hay cupo, crea el registro en `reservas` con `estado = pendiente_pago`, `canal = autoservicio` y `fecha_expiracion_pago` calculada, y dirige al pasajero al pago (CU-O32, `facturacion-spec.md`).

### RF-RES-002 — Crear reserva asistida
El sistema debe permitir a un Agente crear una reserva en nombre de un pasajero, con el mismo flujo de RF-RES-001 pero `canal = asistida` y `reservas.agente_id` obligatorio. Esta acción incluye `<<include>>` la verificación de permisos RBAC (CU-O43).

### RN-RES-001 — Verificación de cupo como precondición obligatoria (CU-O45, orquestación)
Toda creación o modificación de reserva (CU-O21, O22, O23) invoca primero el servicio de verificación de cupo definido en `vuelos-spec.md` (RF-VUE-005). Si el servicio responde sin disponibilidad, la reserva no se crea/modifica y el sistema informa explícitamente al pasajero/agente que el cupo dejó de estar disponible, en vez de continuar el flujo con un cupo inexistente (resuelve la mitad "negocio" de QP-08 — la revalidación ocurre justo antes de confirmar, incluso si el pasajero ya había visto el vuelo con cupo disponible minutos antes).

### RNF-RES-001 — Precio nunca cambia sin aviso explícito
Si entre la selección del vuelo y la confirmación de la reserva el precio de la tarifa cambió, el sistema muestra el nuevo precio antes de proceder al pago; nunca cobra un monto distinto al que el pasajero vio y confirmó (REG-G2).

---

## Funcionalidad 2: Modificar y cancelar reserva (CU-O23, CU-O24)

Gestión del ciclo de vida de una reserva ya confirmada.

### RF-RES-003 — Modificar reserva
El sistema debe permitir a un pasajero o Agente modificar una reserva existente (cambio de vuelo, tarifa, extras o pasajeros), siempre que la reserva no esté en estado `cancelada` o `completada`. Invoca nuevamente la verificación de cupo (RN-RES-001) para el nuevo vuelo/tarifa si cambia. Si el vuelo nuevo tiene un precio distinto al original, dispara CU-O47 (ver RN-RES-002).

### RF-RES-004 — Cancelar reserva
El sistema debe permitir a un pasajero o Agente cancelar una reserva, cambiando su estado a `cancelada`. Si el vuelo asociado ya fue marcado `completado` (CU-O20, `vuelos-spec.md`), el sistema bloquea la cancelación con el mensaje "No es posible cancelar un vuelo ya realizado." Si la política de la tarifa comprada lo permite, dispara `<<extend>>` CU-O37 (Procesar reembolso, `facturacion-spec.md`).

### RN-RES-002 — Diferencia de tarifa al modificar reserva (CU-O47, disparador de negocio)
Cuando CU-O23 resulta en un vuelo/tarifa con `precio_final` distinto al original, el sistema calcula la diferencia (positiva o negativa) y dispara el mecanismo de cobro/reembolso correspondiente, cuyo RF completo (procesamiento vía Stripe) vive en `facturacion-spec.md`. Esta regla es la condición exacta del `<<extend>>` de CU-O23 hacia CU-O47: solo se dispara si el precio cambió, nunca en una modificación que no afecta el monto (p. ej. cambio de asiento sin cambio de tarifa).

---

## Funcionalidad 3: Consultar estado de una reserva (CU-O25)

### RF-RES-005 — Consultar estado de una reserva
El sistema debe mostrar a un pasajero el estado actual de una reserva propia (`pendiente_pago`, `confirmada`, `modificada`, `cancelada`, `completada`), junto con el detalle del vuelo, pasajeros, extras y monto total.

---

## Funcionalidad 4: Crear alerta de precio (CU-O26)

### RF-RES-006 — Crear alerta de precio
El sistema debe permitir a un pasajero autenticado suscribirse a un umbral de precio para una ruta y fecha objetivo, sin necesidad de tener una reserva existente. Al crearse, la alerta queda `activa` en `alertas_precio`.

---

## Funcionalidad 5: Expirar reserva pendiente de pago (CU-O44)

Proceso automático que libera cupo cuando el pago no se completa a tiempo.

### RF-RES-007 — Expirar reserva pendiente de pago
El sistema debe, mediante un proceso automático por temporizador, identificar toda reserva en estado `pendiente_pago` cuya `fecha_expiracion_pago` ya pasó, cambiar su estado a `cancelada` y liberar el cupo que había sido decrementado por CU-O45 (devolviéndolo a `tarifas_vuelo.cupos_disponibles`). Este proceso queda auditado igual que cualquier mutación automática (CU-O41).

### RNF-RES-002 — Ventana de expiración configurable
El tiempo entre creación de una reserva `pendiente_pago` y su expiración se lee de `configuracion_sistema` (categoría `expiraciones`); mientras el nivel Táctico (CU-T13) no exista, se usa un valor por defecto de 15 minutos documentado en el código.

---

## Reglas de negocio

- **RN-RES-001** — *(ver Funcionalidad 1)* Verificación de cupo como precondición obligatoria de CU-O21/O22/O23.
- **RN-RES-002** — *(ver Funcionalidad 2)* Diferencia de tarifa al modificar reserva dispara CU-O47 solo si el precio cambió.
- **RN-RES-003** — Una reserva no puede cancelarse si su vuelo asociado ya está en estado `completado` (flujo alterno agregado a CU-O24 en la fuente).
- **RN-RES-004** — Una reserva `pendiente_pago` que supera su `fecha_expiracion_pago` se cancela automáticamente y libera su cupo, sin intervención manual (CU-O44).
- **RN-RES-005** — *(Nueva, resuelve QP-04)* Si el pago de una reserva se confirma exitosamente (vía Stripe) en el mismo instante o después de que el proceso de expiración automática (CU-O44) ya la canceló, el sistema prioriza honrar el pago recibido: re-confirma la reserva si aún hay cupo, o la marca para reembolso inmediato si el cupo ya fue tomado por otra reserva — nunca se queda un pago exitoso sin una reserva o un reembolso asociado (REG-D1, idempotencia).
- **RN-RES-006** — Toda reserva confirmada mantiene invariante que su `total_pagar` refleja la suma de tarifa + extras vigente al momento de la última confirmación de pago, no al momento de la selección inicial.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `POST /reservas` | Cookie JWT, vuelo/tarifa, pasajeros, extras | Reserva creada en `pendiente_pago` + redirección a pago, o mensaje de cupo no disponible |
| `POST /backoffice/reservas` | Cookie JWT (Agente), vuelo/tarifa, pasajeros, extras | Reserva creada con `canal = asistida` |
| `PUT /reservas/{id}` | Cookie JWT, campos a modificar | Reserva actualizada, o disparo de cobro/reembolso de diferencia si cambió el precio |
| `POST /reservas/{id}/cancelar` | Cookie JWT | Reserva cancelada, o mensaje de bloqueo si el vuelo ya se completó |
| `GET /reservas/{id}` | Cookie JWT | HTML/JSON con estado y detalle completo de la reserva |
| `POST /alertas-precio` | Cookie JWT, origen, destino, fecha objetivo, precio umbral | Alerta creada en estado `activa` |
| `POST /internal/reservas/expirar-pendientes` | Disparado por temporizador, sin input de usuario | Reservas vencidas canceladas + cupo liberado |

---

## Historias de usuario

- **HU-RES-01:** Como pasajero, quiero crear una reserva por autoservicio, para comprar mi vuelo sin necesidad de hablar con un agente.
- **HU-RES-02:** Como agente, quiero crear una reserva asistida en nombre de un pasajero, para atender casos que llegan por un canal distinto al autoservicio.
- **HU-RES-03:** Como pasajero o agente, quiero modificar una reserva existente, para ajustar el vuelo, la tarifa o los extras cuando cambian mis planes.
- **HU-RES-04:** Como pasajero o agente, quiero cancelar una reserva, para liberar el cupo y, si aplica, iniciar mi reembolso.
- **HU-RES-05:** Como pasajero, quiero consultar el estado de mi reserva, para confirmar que todo está en orden antes de viajar.
- **HU-RES-06:** Como pasajero, quiero crear una alerta de precio para una ruta que me interesa, para enterarme cuando el precio baje del umbral que definí.

---

## Objetivo

Gestionar el ciclo de vida completo de una reserva — desde su creación hasta su confirmación, modificación, cancelación o expiración automática — garantizando en todo momento que el cupo vendido nunca exceda el disponible, que ningún cambio de precio se aplique sin transparencia, y que ninguna reserva quede en un estado inconsistente frente a un pago real.

---

## Escenarios

### Camino feliz
1. Un pasajero selecciona vuelo y tarifa, y confirma su reserva (CU-O21); el sistema verifica y reserva el cupo (CU-O45).
2. La reserva queda `pendiente_pago` y el pasajero es dirigido al pago (`facturacion-spec.md`).
3. Tras el pago exitoso, la reserva pasa a `confirmada`.
4. Semanas después, el pasajero decide cambiar de vuelo; modifica su reserva (CU-O23), el nuevo vuelo tiene un precio mayor, y se dispara el cobro de la diferencia (CU-O47).
5. Cerca de la fecha, consulta el estado de su reserva (CU-O25) para confirmar todo en orden.

### Manejo de errores
- **Cupo no disponible al confirmar:** se informa explícitamente antes de proceder al pago (RN-RES-001).
- **Pago no completado a tiempo:** la reserva expira automáticamente y libera el cupo (CU-O44).
- **Cancelación de vuelo ya completado:** se bloquea con "No es posible cancelar un vuelo ya realizado." (RN-RES-003).
- **Pago confirmado justo cuando la reserva ya expiró:** se prioriza honrar el pago, re-confirmando o marcando para reembolso inmediato (RN-RES-005, QP-04).
- **Modificación que cambia el precio a la baja:** se dispara el reembolso de la diferencia en vez del cobro (CU-O47, mismo mecanismo con signo inverso).

---

## Criterios de aceptación

- **CU-O21:** Dado que un pasajero autenticado seleccionó un vuelo/tarifa con cupo disponible, cuando confirma la reserva, entonces esta se crea en estado `pendiente_pago` y es dirigido al pago.
- **CU-O22:** Dado que un Agente con permiso RBAC crea una reserva para un pasajero, cuando confirma, entonces la reserva se crea con `canal = asistida` y el `agente_id` correspondiente.
- **CU-O23:** Dado que una reserva no está cancelada ni completada, cuando el pasajero/agente la modifica, entonces se actualiza respetando la disponibilidad de cupo, y si el precio cambió, se dispara el cobro/reembolso de la diferencia.
- **CU-O24:** Dado que una reserva no está asociada a un vuelo completado, cuando el pasajero/agente la cancela, entonces pasa a `cancelada` y, si la política de tarifa lo permite, se dispara el reembolso.
- **CU-O25:** Dado que un pasajero consulta una reserva propia, cuando accede a su detalle, entonces ve el estado actual y toda la información asociada.
- **CU-O26:** Dado que un pasajero define origen, destino, fecha objetivo y precio umbral, cuando confirma, entonces se crea una alerta de precio activa.
- **CU-O44:** Dado que una reserva `pendiente_pago` supera su fecha de expiración, cuando se ejecuta el proceso automático, entonces la reserva se cancela y su cupo se libera.
- **CU-O45 (RN):** Dado que CU-O21/O22/O23 necesita confirmar una reserva, cuando invoca la verificación de cupo, entonces la reserva solo procede si el servicio confirma disponibilidad; si no, se informa al usuario sin crear/modificar la reserva.
- **CU-O47 (RN):** Dado que una modificación de reserva (CU-O23) resulta en un vuelo con precio distinto al original, cuando se confirma la modificación, entonces se dispara automáticamente el cobro o reembolso de la diferencia; si el precio no cambió, no se dispara nada.

---

## Dependencias

- **Seguridad:** sesión (CU-O42), RBAC para reserva asistida (CU-O43), auditoría (CU-O41).
- **Pasajeros:** datos de pasajero titular y acompañantes (`pasajeros`, incluyendo documento de identidad obligatorio en este punto — RN-PAS-001).
- **Vuelos:** vuelo/tarifa seleccionado y el servicio de verificación de cupo (CU-O45, RF-VUE-005).
- **Facturación:** procesamiento de pago (CU-O32) y del cobro/reembolso de diferencia de tarifa (CU-O47, RF completo en `facturacion-spec.md`).
- **Disrupciones:** consume el estado de reserva confirmada para saber a quién notificar ante un cambio de vuelo.

---

## Casos de uso relacionados

- CU-O17, O18 (Vuelos) — precondición de selección antes de reservar.
- CU-O32 (Procesar pago, Facturación) — incluido obligatoriamente por CU-O21/O22.
- CU-O37 (Procesar reembolso, Facturación) — extend de CU-O24 y de CU-O30 (Notificar al pasajero).
- CU-O30 (Notificar al pasajero, Disrupciones) — puede disparar CU-O37 si la disrupción es una cancelación.

---

## Fuera de alcance

- Selección de asiento específico con mapa de cabina interactivo — el campo `reserva_pasajeros.asiento` existe en el esquema pero su UI detallada no está definida en el catálogo de CU actual.
- Reservas grupales con reglas comerciales especiales (tarifas de grupo) — no existe CU operativo para esto; el agente humano puede asistir manualmente vía CU-O22 sin una tarifa de grupo dedicada.
- Configuración del tiempo de expiración de pago y de las políticas de reembolso — pertenece al nivel Táctico previsto (CU-T13, CU-T10); este módulo usa los valores por defecto documentados mientras tanto.
