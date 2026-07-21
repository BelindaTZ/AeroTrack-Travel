# Especificación Operativa — Facturación

**Módulo:** Facturación
**Prefijo:** FAC
**Código fuente:** `app/facturacion/`
**Casos de uso cubiertos:** CU-O32 (Procesar pago de reserva), CU-O33 (Emitir factura/recibo), CU-O34 (Registrar comisión por reserva), CU-O35 (Conciliar comisiones pendientes vs. cobradas), CU-O36 (Generar remesa simulada a aerolínea), CU-O37 (Procesar reembolso), CU-O38 (Consultar historial de pagos), CU-O39 (Descargar factura/recibo en PDF), CU-O40 (Descargar itinerario/e-ticket en PDF), CU-O47 (Cobrar/reembolsar diferencia de tarifa — RF, mecanismo de cobro), CU-O85 (Convertir moneda para presentación de precios — nuevo v3.0, no implementado), CU-O86 (Capturar pago diferido de hotel — nuevo v3.0, no implementado)
**Actor:** Pasajero / Agente / Administrador / Sistema (automático)

> **Nota de actualización 2026-07-18:** CU-O85/O86 son del catálogo v3.0. Además, la sección "Fuera de alcance" de este documento tenía varias referencias a CU-T que cambiaron de significado al renumerar el catálogo completo (CU-T08/T09/T10/T12 ya no son de Facturación) — corregidas ahí mismo.

---

## Funcionalidad 1: Procesar pago de reserva (CU-O32)

Punto de entrada del dinero al sistema; convierte una reserva `pendiente_pago` en `confirmada`.

### RF-FAC-001 — Procesar pago de reserva
El sistema debe mostrar, para una reserva `pendiente_pago`, el desglose completo (precio base + cargo de servicio + impuestos = total, REG-G2) antes de solicitar los datos de pago. Procesa el cobro vía Stripe test mode; si Stripe confirma, marca el pago como `exitoso` en `pagos`, actualiza la reserva a `confirmada`, y dispara `<<include>>` CU-O33 (Emitir factura) y CU-O34 (Registrar comisión). Si Stripe rechaza el pago, lo marca `fallido`, muestra el motivo y permite reintentar.

### RNF-FAC-001 — Nunca se almacenan datos de tarjeta crudos
Toda captura de datos de pago se delega íntegramente a Stripe (tokenizado); el sistema nunca recibe, transmite ni persiste el número completo de una tarjeta (REG-C1).

### RNF-FAC-002 — Idempotencia del cobro
Cada intento de pago se asocia a un `stripe_payment_intent_id` único; el sistema nunca procesa dos veces el mismo evento de cobro para la misma reserva (REG-D1).

---

## Funcionalidad 2: Emitir factura y registrar comisión (CU-O33, CU-O34)

Consecuencias automáticas de todo pago exitoso.

### RF-FAC-002 — Emitir factura/recibo
El sistema debe generar automáticamente, tras un pago exitoso, un registro en `facturas` con número único, total y fecha de emisión, junto con el archivo PDF correspondiente.

### RF-FAC-003 — Registrar comisión por reserva
El sistema debe generar automáticamente, tras un pago exitoso, un registro en `comisiones` con `estado = pendiente_cobro` y el monto pactado con el proveedor (`aerolineas.comision_pactada_pct`/`navieras`/`proveedores_comerciales`, según `tipo_producto` — dbml v3 rediseñó `comisiones` para referenciar `reserva_item_id`, una fila por componente), reflejando el modelo de ingreso diferido descrito en `consideraciones.md` (sección 5). **Si la reserva es un paquete** (`reservas.es_paquete = true`), el "monto correspondiente" de cada componente es su `reserva_items.precio_final` **sin el descuento de paquete aplicado** — ver RN-FAC-007.

---

## Funcionalidad 3: Conciliar comisiones y generar remesas (CU-O35, CU-O36)

Gestión administrativa del dinero pendiente de cobro/remisión.

### RF-FAC-004 — Conciliar comisiones pendientes vs. cobradas
El sistema debe permitir a un Administrador ver, filtrar de forma instantánea (REG-J9) y marcar como `cobrada` una comisión previamente `pendiente_cobro`, registrando `fecha_cobro_real`. Esta acción incluye `<<include>>` la verificación RBAC (CU-O43) y auditoría (CU-O41).

### RF-FAC-005 — Generar remesa simulada a aerolínea
El sistema debe permitir, de forma automática o iniciada por un Administrador, agrupar comisiones cobradas de una aerolínea en un periodo (`remesa_comisiones`) y generar un registro en `remesas` con el monto total y estado `pendiente`. Es un registro contable simulado — no hay integración BSP/ARC real (ver `consideraciones.md` sección 7).

---

## Funcionalidad 4: Procesar reembolso (CU-O37)

Devolución de dinero al pasajero, siempre gobernada por la política de la tarifa comprada.

### RF-FAC-006 — Procesar reembolso
El sistema debe procesar un reembolso, disparado por `<<extend>>` de CU-O24 (Cancelar reserva) o de CU-O30 (Notificar al pasajero, cuando la disrupción es una cancelación — RN-DIS-003 en `disrupciones-spec.md`), evaluando automáticamente `politicas_reembolso` asociada a la tarifa comprada (porcentaje y ventana de horas). Genera un registro en `reembolsos` con `estado = pendiente`, procesa la devolución vía Stripe test mode (`stripe_refund_id`), y lo marca `procesado` o `rechazado` según la respuesta.

### RN-FAC-001 — Las políticas de reembolso se resuelven por reglas, nunca por excepción manual
Ningún Agente/Administrador puede aprobar un reembolso fuera de lo que determina `politicas_reembolso` para la tarifa comprada; el resultado del cálculo es siempre consultable por el pasajero (REG-D3, REG-C3).

---

## Funcionalidad 5: Cobrar/reembolsar diferencia de tarifa (CU-O47 — RF, mecanismo de cobro)

Contraparte de RN-RES-002 en `reservas-spec.md`, que documenta cuándo se dispara (extend condicional de CU-O23). Este módulo documenta el **mecanismo real** de cobro/reembolso de esa diferencia.

### RF-FAC-007 — Cobrar/reembolsar diferencia de tarifa
El sistema debe, al recibir el disparo de `reservas-spec.md` (RN-RES-002) con un monto de diferencia (positivo = cobro adicional, negativo = reembolso parcial), procesar la operación correspondiente vía Stripe test mode: un cobro adicional sigue el mismo mecanismo que RF-FAC-001 (nuevo `pagos` asociado a la misma reserva); un reembolso parcial sigue el mismo mecanismo que RF-FAC-006 (nuevo `reembolsos` con el monto exacto de la diferencia, no el total de la reserva).

---

## Funcionalidad 6: Consultar y descargar documentos (CU-O38, CU-O39, CU-O40)

Autoservicio de documentación para el pasajero.

### RF-FAC-008 — Consultar historial de pagos
El sistema debe mostrar a un pasajero autenticado el historial de sus pagos propios (`pagos`), con monto, método, estado y fecha.

### RF-FAC-009 — Descargar factura/recibo en PDF
El sistema debe permitir a un pasajero descargar el PDF de cualquier factura asociada a sus propias reservas (`facturas.archivo_pdf`).

### RF-FAC-010 — Descargar itinerario / e-ticket en PDF
El sistema debe generar y permitir descargar un PDF de itinerario/e-ticket para cualquier reserva confirmada propia, con los datos del vuelo (`vuelos_catalogo`) y de los pasajeros incluidos.

---

## Funcionalidad 7: Convertir moneda para presentación de precios (CU-O85) — *(nuevo v3.0, no implementado)*

Necesaria al ampliar el alcance a rutas internacionales (`consideraciones.md` sección 3) — transversal en consumo a las 6 verticales de producto, pero el RF vive una sola vez aquí.

### RF-FAC-011 — Convertir moneda para presentación de precios *(pendiente de implementación)*
El sistema debe actualizar, 1×/día mediante proceso automático, las tasas de cambio (`tasas_cambio`) contra ExchangeRate-API (confirmado funcionando en pruebas en vivo), para que Vuelos/Hoteles/Autos/Actividades/Cruceros/Paquetes puedan presentar el precio en la moneda local relevante. El cobro real vía Stripe sigue siempre en USD (`consideraciones.md` sección 3) — esta conversión es solo de presentación, nunca de cobro.

## Funcionalidad 8: Capturar pago diferido de hotel (CU-O86) — *(nuevo v3.0, no implementado)*

Mismo patrón de doble documentación que CU-O45/O47/O52/O83: la RN de cuándo se dispara vive en Hoteles (`specs/operativo/hoteles/`, no redactado todavía); este módulo documenta el RF del mecanismo real de cobro.

### RF-FAC-012 — Capturar pago diferido de hotel *(pendiente de implementación)*
El sistema debe completar el cobro de una reserva de hotel creada con "Reservar sin pagar ahora" cuando el hotel confirma la disponibilidad, usando el flujo nativo de Stripe authorize-then-capture: `pagos.captura_diferida = true`, `estado` pasa por el nuevo valor `autorizado` (con `fecha_autorizacion`) antes de `exitoso` (con `fecha_pago` = fecha de captura real). Mismo mecanismo de idempotencia que RF-FAC-001/002 (RNF-FAC-002).

---

## Reglas de negocio

- **RN-FAC-001** — *(Funcionalidad 4)* Las políticas de reembolso se resuelven por reglas, nunca por excepción manual.
- **RN-FAC-002** — Todo pago, comisión, remesa o reembolso, real o simulado, queda registrado con origen, destino y estado, permitiendo reconstruir el estado financiero de cualquier reserva en cualquier momento (REG-D2).
- **RN-FAC-003** — Una comisión solo puede pasar de `pendiente_cobro` a `cobrada`; nunca se revierte automáticamente a `pendiente_cobro` una vez marcada cobrada (solo corrección manual auditada, si aplica).
- **RN-FAC-004** — El cargo de servicio se cobra de forma inmediata al pasajero al momento de la reserva; la comisión de la aerolínea se registra como pendiente y se cobra semanas después — nunca se tratan como el mismo evento contable (ver `consideraciones.md` sección 5).
- **RN-FAC-005** — Ningún dato completo de tarjeta de pago se almacena en ninguna tabla del sistema (REG-C1); solo se persisten identificadores tokenizados de Stripe (`stripe_payment_intent_id`, `stripe_refund_id`).
- **RN-FAC-006** — *(Nueva, complementa RN-RES-005 de `reservas-spec.md`, resuelve QP-04)* Si un pago llega confirmado por Stripe para una reserva que el proceso de expiración automática (CU-O44) ya canceló, el pago no se descarta: se enlaza a la reserva re-confirmada si el cupo sigue disponible, o se marca de inmediato para reembolso total si no — nunca queda un pago exitoso sin una reserva o un reembolso asociado.
- **RN-FAC-007** — *(Nueva 2026-07-18, complementa RN-PAQ-004 de `paquetes-spec.md`)* **El descuento de paquete (`reservas.descuento_paquete_pct`) nunca reduce la comisión pactada con un proveedor.** Cuando `reservas.es_paquete = true`, cada `comisiones` (RF-FAC-003) se calcula sobre el `reserva_items.precio_final` de su propio componente — el precio real/de lista, sin el descuento de paquete aplicado — porque ese descuento vive únicamente a nivel de cabecera de la reserva (`reservas.total_pagar`), no en cada línea. Es la agencia, vía su propio cargo de servicio/margen, quien absorbe el costo comercial del descuento; ningún proveedor (aerolínea, hotel, rentadora, operador de actividad) cobra menos comisión por el solo hecho de que su componente forme parte de un paquete.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `POST /reservas/{id}/pagar` | Cookie JWT, datos de pago (tokenizados por Stripe) | Pago procesado (`exitoso`/`fallido`), reserva actualizada, factura y comisión generadas si exitoso |
| `GET /pagos` | Cookie JWT | HTML/JSON con historial de pagos del pasajero autenticado |
| `GET /facturas/{id}/pdf` | Cookie JWT | Archivo PDF descargable de la factura |
| `GET /reservas/{id}/itinerario-pdf` | Cookie JWT | Archivo PDF descargable del itinerario/e-ticket |
| `GET /backoffice/comisiones` | Cookie JWT (Admin), filtros | HTML/JSON con comisiones pendientes/cobradas |
| `POST /backoffice/comisiones/{id}/marcar-cobrada` | Cookie JWT (Admin) | Comisión actualizada a `cobrada` |
| `POST /backoffice/remesas` | Cookie JWT (Admin/Sistema), aerolínea, periodo | Remesa generada agrupando comisiones cobradas |
| `POST /internal/reembolsos` | `reserva_id` o `disrupcion_id`, motivo | Reembolso procesado según política de tarifa, o rechazado con motivo |
| `POST /internal/reservas/{id}/diferencia-tarifa` | Monto de diferencia (positivo/negativo) desde Reservas | Cobro adicional o reembolso parcial procesado vía Stripe |

---

## Historias de usuario

- **HU-FAC-01:** Como pasajero, quiero pagar mi reserva viendo el desglose completo del precio, para saber exactamente cuánto y por qué estoy pagando antes de confirmar.
- **HU-FAC-02:** Como pasajero, quiero recibir automáticamente mi factura tras pagar, para tener el comprobante sin pedirlo manualmente.
- **HU-FAC-03:** Como administrador, quiero conciliar las comisiones pendientes contra las cobradas, para llevar control financiero de lo que la agencia debe recibir de cada aerolínea.
- **HU-FAC-04:** Como administrador, quiero generar una remesa simulada a una aerolínea, para reflejar el proceso real de remisión del sector aunque no haya integración BSP/ARC.
- **HU-FAC-05:** Como pasajero, quiero que mi reembolso se calcule automáticamente según la política de mi tarifa, para no depender de la discrecionalidad de un agente.
- **HU-FAC-06:** Como pasajero, quiero consultar mi historial de pagos y descargar mis facturas e itinerarios, para tener mis documentos de viaje siempre disponibles.

---

## Objetivo

Sostener con transparencia e idempotencia todo movimiento de dinero del sistema — cobro, factura, comisión, remesa y reembolso — replicando el modelo real de ingresos de una agencia de viajes (cargo de servicio inmediato + comisión diferida) sin mover dinero real ni requerir certificación formal, y garantizando que ningún evento de dinero se procese dos veces ni quede sin trazabilidad completa.

---

## Escenarios

### Camino feliz
1. Un pasajero con una reserva `pendiente_pago` ve el desglose de precio y confirma el pago (CU-O32).
2. Stripe confirma el cobro; se emite la factura (CU-O33) y se registra la comisión pendiente (CU-O34).
3. Semanas después, un Administrador concilia esa comisión como cobrada (CU-O35) y la agrupa en una remesa (CU-O36).
4. El pasajero descarga su factura y su itinerario cuando lo necesita (CU-O39, CU-O40).

### Manejo de errores
- **Pago rechazado por Stripe:** se muestra el motivo y se permite reintentar (RF-FAC-001).
- **Reembolso fuera de la política de la tarifa:** se rechaza automáticamente según regla, nunca por decisión manual discrecional (RN-FAC-001).
- **Pago confirmado para una reserva ya expirada:** se enlaza a la reserva re-confirmada o se marca para reembolso inmediato, nunca queda huérfano (RN-FAC-006, QP-04).
- **Diferencia de tarifa negativa (precio bajó al modificar reserva):** se procesa como reembolso parcial del monto exacto de la diferencia, no del total de la reserva (RF-FAC-007).

---

## Criterios de aceptación

- **CU-O32:** Dado que existe una reserva `pendiente_pago`, cuando el pasajero completa el pago y Stripe lo confirma, entonces la reserva pasa a `confirmada` y se disparan factura y comisión.
- **CU-O33:** Dado que un pago se marca exitoso, cuando el sistema procesa la consecuencia, entonces se genera una factura con PDF descargable.
- **CU-O34:** Dado que un pago se marca exitoso, cuando el sistema procesa la consecuencia, entonces se registra una comisión en estado `pendiente_cobro`.
- **CU-O35:** Dado que existen comisiones `pendiente_cobro`, cuando un Administrador las marca como cobradas, entonces su estado y fecha de cobro real quedan actualizados.
- **CU-O36:** Dado que existen comisiones cobradas de una aerolínea en un periodo, cuando se genera la remesa, entonces se agrupan en un registro `remesas` con el monto total correcto.
- **CU-O37:** Dado que se dispara un reembolso por cancelación, cuando el sistema evalúa la política de la tarifa comprada, entonces procesa el reembolso según el porcentaje y ventana definidos, sin intervención discrecional.
- **CU-O38:** Dado que un pasajero consulta su historial de pagos, cuando accede a la vista, entonces ve únicamente sus propios pagos.
- **CU-O39:** Dado que existe una factura asociada a una reserva propia, cuando el pasajero la descarga, entonces recibe el PDF correspondiente.
- **CU-O40:** Dado que existe una reserva confirmada propia, cuando el pasajero descarga su itinerario, entonces recibe el PDF con los datos del vuelo y pasajeros.
- **CU-O47 (RF):** Dado que Reservas dispara una diferencia de tarifa, cuando Facturación la procesa, entonces cobra o reembolsa exactamente el monto de la diferencia vía Stripe, nunca el total de la reserva.
- **CU-O85** *(pendiente):* Dado que pasa un día, cuando corre el job de conversión, entonces `tasas_cambio` queda actualizado contra ExchangeRate-API para todos los pares de moneda relevantes.
- **CU-O86** *(pendiente):* Dado que una reserva de hotel con pago diferido es confirmada por el hotel, cuando se dispara la captura, entonces el pago autorizado en Stripe se captura y queda `exitoso` con su `fecha_pago` real.

---

## Dependencias

- **Reservas:** toda operación de este módulo nace de una reserva (`reservas_id` en `pagos`, `comisiones`, `reembolsos`, `facturas`); consume el disparo de diferencia de tarifa (RN-RES-002).
- **Seguridad:** sesión (CU-O42), RBAC para acciones de Administrador (CU-O35, O36 — CU-O43), auditoría (CU-O41), credenciales de Stripe en `configuracion_sistema` (REG-B3).
- **Disrupciones:** dispara CU-O37 cuando una disrupción notificada es una cancelación (RN-DIS-003 en `disrupciones-spec.md`).
- **Hoteles** *(`hoteles-spec.md`, sin implementación todavía):* CU-O86 se dispara desde CU-O60 ("Reservar sin pagar ahora") — la RN de cuándo confirma el hotel vive del lado de Hoteles.
- **Vuelos/Hoteles/Autos/Actividades/Cruceros/Paquetes:** todos consumen `tasas_cambio` (CU-O85) para presentación de precio en moneda local.
- **Paquetes** (`paquetes-spec.md`): el descuento de paquete (`reservas.descuento_paquete_pct`) nunca reduce la comisión que este módulo calcula por componente (RN-FAC-007).

---

## Casos de uso relacionados

- CU-O21, O22 (Crear reserva, Reservas) — incluyen obligatoriamente CU-O32.
- CU-O23 (Modificar reserva, Reservas) — extend hacia CU-O47.
- CU-O24 (Cancelar reserva, Reservas) — extend hacia CU-O37.
- CU-O30 (Notificar al pasajero, Disrupciones) — extend hacia CU-O37 si la disrupción es cancelación.
- CU-O60 (Reservar hotel con pago diferido, Hoteles) — extend hacia CU-O86.
- CU-O76 (Construir paquete, Paquetes) — su descuento de cabecera nunca toca el cálculo de `comisiones` por componente (RN-FAC-007).
- CU-T22, T23 (previsto, Táctico, este módulo) — dashboard financiero y reporte de ingresos, consumirán los datos que este módulo ya genera.

---

## Fuera de alcance

- **Corregidas 2026-07-18 las referencias de CU-T de esta sección** — apuntaban a números que, tras renumerar el catálogo completo, pasaron a significar otra cosa en otros módulos (CU-T08 hoy es de Vuelos, CU-T09/T10 de Hoteles, CU-T12 de Actividades). Los CU-T correctos de este módulo son **CU-T22** (Ver dashboard financiero) y **CU-T23** (Generar reporte de ingresos por período), ver abajo.
- Configuración de reglas de tarifas de servicio, comisiones y políticas de reembolso por nivel de tarifa — es CU-T18 (Configurar política de reembolsos), redactado bajo Reservas, no Facturación; este módulo consume los valores ya persistidos.
- Configuración de credenciales de Stripe y catálogo de aerolíneas/comisión pactada — parámetros que hoy se leen de `configuracion_sistema`/`aerolineas` sin panel de edición propio; no tienen CU-T dedicado en el catálogo actual.
- **Dashboard financiero con KPIs — corregido: ya NO es "alcance futuro sin CU"** — CU-T22/CU-T23 lo definen explícitamente desde v3.0 (nivel Táctico, `specs/tactico/facturacion/`, carpeta creada, `spec.md` pendiente de redactar).
- Integración real con BSP/ARC — la remesa es siempre un registro contable simulado (ver `consideraciones.md` sección 7).
