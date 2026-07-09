# Especificación Operativa — Disrupciones y Notificaciones

**Módulo:** Disrupciones y Notificaciones
**Prefijo:** DIS
**Código fuente:** `app/disrupciones/`
**Casos de uso cubiertos:** CU-O27 (Consultar estado real de vuelo vía API externa), CU-O28 (Monitorear bandeja de correo de aerolíneas), CU-O29 (Detectar cambio de itinerario), CU-O30 (Notificar al pasajero), CU-O31 (Consultar historial de notificaciones), CU-O46 (Reintentar envío de notificación fallida)
**Actor:** Sistema (automático) / Pasajero / Agente

---

## Funcionalidad 1: Consultar estado real de vuelo vía API externa (CU-O27)

Fuente de detección más cercana a la fecha de viaje, con control de cuota y degradación ordenada.

### RF-DIS-001 — Consultar estado real de vuelo
El sistema debe consultar periódicamente, para vuelos con reservas confirmadas cercanas a su fecha, el estado real vía una API externa de estado de vuelo (AviationStack o AeroDataBox, REG-I7), respetando el límite de cuota configurado. Si la API responde con un estado distinto al registrado en `vuelos_catalogo`, genera un registro en `disrupciones` con `fuente_deteccion = api_real`.

### RNF-DIS-001 — Degradación ordenada ante falla de la API en tiempo real
Si la API de estado de vuelo no responde o se agota la cuota, el sistema continúa operando con la fuente estadística (simulador, nivel Estratégico) como respaldo; nunca falla silenciosamente, y registra el evento de degradación (REG-E3, resuelve QP-01). **El peor caso normal (API disponible, cuota suficiente) nunca depende de que esta degradación se dispare** — la ruta principal de detección para reservas cercanas es siempre la consulta directa a la API real.

### RNF-DIS-002 — Timeout y reintento configurables
Toda llamada a la API de estado de vuelo define un límite de tiempo y una política de reintento en `configuracion_sistema` (categoría `api_estado_vuelo`); nunca hay una espera indefinida (REG-F2).

---

## Funcionalidad 2: Monitorear bandeja de correo y detectar cambios (CU-O28, CU-O29)

Segunda fuente de detección, en paralelo a la API real, inspirada en TripIt.

### RF-DIS-002 — Monitorear bandeja de correo de aerolíneas
El sistema debe monitorear automáticamente, vía Gmail API (OAuth, REG-I6), la bandeja de correo de la agencia en busca de avisos de cambio/cancelación enviados por aerolíneas.

### RF-DIS-003 — Detectar cambio de itinerario
El sistema debe parsear los correos monitoreados por RF-DIS-002 para identificar si corresponden a un cambio real de itinerario (retraso, cancelación, cambio de horario, cambio de puerta, desvío) sobre un vuelo con reservas activas. Si detecta un cambio válido, genera un registro en `disrupciones` con `fuente_deteccion = monitor_correo` y dispara `<<include>>` CU-O30 (Notificar al pasajero) — constitución E1: ninguna disrupción detectada queda sin notificar.

### RN-DIS-001 — Correo sin reserva activa asociada (resuelve QP-07)
Si un correo parseado por RF-DIS-003 no corresponde a ningún vuelo con reservas activas, o el vuelo no se reconoce en `vuelos_catalogo`, el sistema descarta el aviso sin generar notificación errónea al pasajero, y lo marca para revisión manual sin interrumpir el resto del monitoreo (REG-F3).

---

## Funcionalidad 3: Notificar al pasajero (CU-O30)

Punto de convergencia de las tres fuentes de detección — el corazón del diferenciador del negocio.

### RF-DIS-004 — Notificar al pasajero
El sistema debe, ante cualquier disrupción detectada (por API real o monitor de correo — la fuente estadística del nivel Estratégico también converge aquí cuando exista), generar una notificación (`notificaciones`) al pasajero titular y acompañantes de toda reserva confirmada asociada al vuelo afectado, por el canal configurado (email o SMS). Si la disrupción implica cancelación, dispara además `<<extend>>` CU-O37 (Procesar reembolso, `facturacion-spec.md`) según la política de la tarifa comprada.

### RN-DIS-002 — Precedencia y deduplicación entre fuentes (resuelve QP-02)
Cuando más de una fuente (API real, monitor de correo) detecta el mismo cambio sobre el mismo vuelo, el sistema aplica la siguiente precedencia: `api_real` > `monitor_correo` > `simulador_estadistico`. Solo se genera una notificación por cambio y por pasajero, aunque múltiples fuentes lo hayan detectado (REG-E2).

### RN-DIS-003 — Reembolso condicionado a la naturaleza de la disrupción (resuelve QP-12)
CU-O37 solo se dispara desde CU-O30 cuando el tipo de cambio es `cancelacion`. Para `retraso`, `cambio_horario`, `cambio_puerta` o `desvio`, la notificación se envía pero no se dispara reembolso automático, salvo que la política de la tarifa comprada lo contemple explícitamente (evaluado en `facturacion-spec.md`, REG-C3 — transparencia, nunca resolución discrecional).

---

## Funcionalidad 4: Consultar historial de notificaciones (CU-O31)

### RF-DIS-005 — Consultar historial de notificaciones
El sistema debe mostrar a un pasajero (sus propias notificaciones) o a un Agente (con permiso RBAC, notificaciones de cualquier pasajero) el historial de notificaciones enviadas, con su canal, asunto, estado de envío y si fue leída, filtrable de forma instantánea (REG-J9).

---

## Funcionalidad 5: Reintentar envío de notificación fallida (CU-O46)

`<<extend>>` condicional de CU-O30, solo si el primer intento de envío falla.

### RF-DIS-006 — Reintentar envío de notificación fallida
El sistema debe, cuando una notificación queda en `estado_envio = fallido`, reintentar su envío según la política de reintentos configurada (número de intentos, intervalo) en `configuracion_sistema` (REG-F2). Tras agotar los reintentos configurados sin éxito, el sistema deja constancia del fallo definitivo (no reintenta indefinidamente) y lo hace visible para el Agente/Administrador (resuelve QP-09).

### RNF-DIS-003 — Aislamiento de fallos del canal de envío
La caída del proveedor de correo o SMS no impide el resto de las funcionalidades del sistema; el reintento de CU-O46 opera de forma aislada e independiente de cualquier otra integración (REG-F3).

---

## Reglas de negocio

- **RN-DIS-001** — *(Funcionalidad 2, resuelve QP-07)* Un correo sin vuelo/reserva activa asociada se descarta sin notificar al pasajero, y se marca para revisión manual.
- **RN-DIS-002** — *(Funcionalidad 3, resuelve QP-02)* Precedencia `api_real` > `monitor_correo` > `simulador_estadistico` y deduplicación: una sola notificación por cambio y por pasajero.
- **RN-DIS-003** — *(Funcionalidad 3, resuelve QP-12)* El reembolso automático (CU-O37) solo se dispara desde una disrupción de tipo `cancelacion`.
- **RN-DIS-004** — Toda disrupción detectada, sin importar la fuente, genera una notificación verificable; ninguna disrupción activa queda sin su intento de notificación (REG-E1).
- **RN-DIS-005** — Si la API de estado de vuelo en tiempo real no está disponible, el sistema no deja de operar: continúa con la fuente estadística como respaldo (REG-E3); esta degradación nunca es la ruta esperada en operación normal.
- **RN-DIS-006** — El reintento de notificación fallida (CU-O46) tiene un límite de intentos configurado; al agotarse, el fallo queda registrado como definitivo y visible para el equipo interno, nunca en reintento silencioso indefinido.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `POST /internal/disrupciones/consultar-api` | Disparado por temporizador, sin input de usuario | Registros nuevos en `disrupciones` con `fuente_deteccion = api_real`, o evento de degradación si la API falla |
| `POST /internal/disrupciones/monitorear-correo` | Disparado por temporizador, sin input de usuario (usa credenciales OAuth de `configuracion_sistema`) | Registros nuevos en `disrupciones` con `fuente_deteccion = monitor_correo`, o avisos descartados |
| `POST /internal/notificaciones/enviar` | `disrupcion_id` o evento informativo, pasajero destino | Registro en `notificaciones` con `estado_envio` actualizado |
| `POST /internal/notificaciones/{id}/reintentar` | Disparado automáticamente tras fallo | Notificación reenviada, o fallo definitivo registrado tras agotar reintentos |
| `GET /notificaciones` | Cookie JWT, filtros opcionales | HTML/JSON con historial de notificaciones del pasajero autenticado |
| `GET /backoffice/notificaciones` | Cookie JWT (Agente/Admin), filtros | HTML/JSON con historial de notificaciones de cualquier pasajero dentro del alcance RBAC |

---

## Historias de usuario

- **HU-DIS-01:** Como sistema, quiero consultar el estado real de un vuelo cerca de la fecha de viaje, para detectar cambios operativos con la mayor precisión disponible.
- **HU-DIS-02:** Como sistema, quiero monitorear la bandeja de correo de la agencia, para detectar avisos de la aerolínea aunque no lleguen por API.
- **HU-DIS-03:** Como pasajero, quiero recibir una notificación inmediata ante cualquier cambio relevante en mi vuelo, para reaccionar a tiempo sin depender de que un agente me avise.
- **HU-DIS-04:** Como pasajero o agente, quiero consultar el historial de notificaciones, para verificar qué avisos se enviaron y cuándo.
- **HU-DIS-05:** Como sistema, quiero reintentar el envío de una notificación fallida, para maximizar la probabilidad de que el pasajero se entere del cambio.

---

## Objetivo

Cerrar el hueco de comunicación que origina el proyecto: garantizar que ningún cambio operativo relevante detectado por cualquiera de las fuentes disponibles (API real, monitor de correo, y en el futuro el simulador estadístico) deje de llegar al pasajero final, combinando las fuentes con precedencia clara, degradándose de forma ordenada cuando una fuente falla, y reintentando el envío cuando el primer intento no llega.

---

## Escenarios

### Camino feliz
1. El sistema consulta la API de estado de vuelo para reservas cercanas a la fecha (CU-O27).
2. En paralelo, monitorea la bandeja de correo de la agencia (CU-O28) y detecta un cambio (CU-O29).
3. Cualquiera de las dos fuentes que detecte primero el cambio dispara la notificación al pasajero (CU-O30).
4. El pasajero consulta después su historial de notificaciones para confirmar que la recibió (CU-O31).

### Manejo de errores
- **API de estado de vuelo no responde o se agota la cuota:** el sistema sigue operando con la fuente estadística como respaldo, sin fallar silenciosamente (RNF-DIS-001, QP-01).
- **Dos fuentes detectan el mismo cambio:** se aplica precedencia y se notifica una sola vez (RN-DIS-002, QP-02).
- **Correo sin reserva activa asociada:** se descarta sin notificar, se marca para revisión (RN-DIS-001, QP-07).
- **Primer envío de notificación falla:** se reintenta según política configurada; si se agotan los reintentos, se registra el fallo definitivo y se hace visible al equipo interno (RF-DIS-006, QP-09).
- **Disrupción de tipo retraso (no cancelación):** se notifica pero no se dispara reembolso automático (RN-DIS-003, QP-12).

---

## Criterios de aceptación

- **CU-O27:** Dado que existen reservas confirmadas cercanas a su fecha de vuelo, cuando el sistema consulta la API de estado real, entonces registra cualquier discrepancia como disrupción con `fuente_deteccion = api_real`, o se degrada ordenadamente si la API falla.
- **CU-O28:** Dado que la agencia tiene una bandeja de correo configurada, cuando el sistema la monitorea, entonces detecta correos nuevos de aerolíneas sin intervención manual.
- **CU-O29:** Dado que un correo monitoreado corresponde a un vuelo con reservas activas, cuando se parsea, entonces se registra como disrupción y dispara notificación; si no corresponde a ninguna reserva activa, se descarta sin notificar.
- **CU-O30:** Dado que se detecta una disrupción por cualquier fuente, cuando el sistema procesa el evento, entonces genera una notificación verificable a cada pasajero afectado, deduplicada si más de una fuente detectó el mismo cambio.
- **CU-O31:** Dado que un pasajero o agente autorizado consulta el historial de notificaciones, cuando accede a la vista, entonces ve todas las notificaciones dentro de su alcance, filtrable de forma instantánea.
- **CU-O46:** Dado que una notificación queda en estado fallido, cuando el sistema ejecuta el reintento configurado, entonces reenvía la notificación; si se agotan los reintentos, registra el fallo definitivo.

---

## Dependencias

- **Vuelos:** consume `vuelos_catalogo` para saber qué vuelo consultar/actualizar (CU-O27 dispara la actualización de estado definida en `vuelos-spec.md`, RF-VUE-004).
- **Reservas:** consume las reservas confirmadas de un vuelo para saber a quién notificar.
- **Pasajeros:** consume los datos de contacto (teléfono/correo) mantenidos en ese módulo como canal de envío.
- **Facturación:** dispara CU-O37 (Procesar reembolso) cuando la disrupción notificada es una cancelación.
- **Seguridad:** credenciales de Gmail API y de la API de estado de vuelo viven en `configuracion_sistema`, nunca hardcodeadas (REG-B3); auditoría (CU-O41) de cada disrupción/notificación generada.

---

## Casos de uso relacionados

- CU-O20 (Actualizar estado de un vuelo, Vuelos) — destino de la detección de CU-O27/O29.
- CU-O21-O26 (Reservas) — fuente de qué pasajeros tienen reservas activas sobre un vuelo.
- CU-O37 (Procesar reembolso, Facturación) — extend condicional de CU-O30.
- CU-E01 (previsto, Estratégico) — simulador estadístico, ya implementado como DAG; fuente adicional que converge en CU-O30 cuando se formalice su spec.

---

## Fuera de alcance

- El simulador estadístico de riesgo en sí (CU-E01) — pertenece al nivel Estratégico previsto; este módulo solo define cómo convergería su resultado en CU-O30 cuando exista.
- Medición de efectividad de notificación (CU-E02, KPI) — nivel Estratégico previsto.
- Configuración de umbrales del simulador, canales de notificación activos, credenciales de Gmail/API de vuelo (CU-T06, T07, T11, T17) — nivel Táctico previsto; este módulo lee los valores ya persistidos en `configuracion_sistema`, no expone su panel de edición.
- OpenSky Network (posición ADS-B) — considerado en el documento empresarial como complemento secundario, no forma parte de ningún CU-O redactado; no se implementa en esta versión.
