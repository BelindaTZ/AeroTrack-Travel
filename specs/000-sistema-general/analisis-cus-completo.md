# Análisis completo de casos de uso — Niveles Operativo y Táctico

**Fuente única de verdad:** `docs/aerotrack-travel-casos-de-uso-v3.md` (v3.1, 2026-07-17 — catálogo renumerado y con mapa `<<include>>`/`<<extend>>` propio). No es `docs/aerotrack-travel-casos-de-uso-operativos.md` (versión anterior, ver nota de migración abajo) ni el `.dbml` del mismo nombre v3 (ese es el esquema de tablas).
**Total del catálogo:** 166 CU — 122 CU Operativos (CU-O) + 44 CU Tácticos (CU-T) — en **17 módulos**.
**Alcance de este documento:** no crea, no modifica y no reclasifica ningún caso de uso del catálogo fuente. Le añade capas de análisis propias de este nivel de especificación: (1) expansión Jacobson completa de un subconjunto representativo, (2) mapa de relaciones/dependencias entre módulos-spec, (3) escenarios "qué pasa si", (4) asignación de CU a la estructura de carpetas `specs/operativo/` y `specs/tactico/`, (5) matriz técnica con tablas DBML.

> **Nota de migración (2026-07-17):** este documento originalmente analizaba 48 CU-O sobre `docs/aerotrack-travel-casos-de-uso-operativos.md` (6 módulos, un único nivel Operativo). El catálogo fuente evolucionó a v3.0/v3.1 (`docs/aerotrack-travel-casos-de-uso-v3.md`): 166 CU en 17 módulos (165 al 17-07, +CU-T44 el 18-07 — ver punto abierto resuelto en sección 7), con nivel Táctico ya redactado (antes "previsto"). Este documento se actualiza para cubrir ese alcance completo. Las secciones 1-3 y 6 que ya estaban **confirmadas** para CU-O01–O48 se preservan sin cambios de contenido; lo nuevo se añade sin tocar lo ya validado.

> **Nota sobre CU-O48 (añadido fuera de la fuente original):** durante la redacción de `vuelos-spec.md` se agregó **CU-O48 — Forzar/ajustar puntualmente un vuelo del catálogo (solo pruebas/demo)**, Actor: Administrador. No proviene del catálogo original; es una vía **excepcional**, fuera del flujo de negocio normal (el catálogo sigue siendo 100% automático en producción vía CU-O19/O20), pensada únicamente para preparar escenarios reproducibles de demo/sustentación. Incluye `<<include>>` a CU-O41 (auditoría) y CU-O43 (RBAC), igual que cualquier acción de Administrador. Documentado en detalle en `vuelos-spec.md`.

> **Nota sobre CU-O26 (eliminado en v3.0):** existía en el catálogo original como "Crear alerta de precio" dentro de Reservas. Se eliminó y quedó **supersedido por CU-O91** (mismo nombre) en el módulo Cuenta / Mis Viajes, donde corresponde conceptualmente como función de gestión de cuenta, no de proceso de reserva. Ningún CU se renumeró para llenar el hueco — es intencional, ver convención de numeración abajo.

> **Convención de numeración (no cambia con este documento, ya aplicada en el catálogo fuente):** los CU usan ID plano por nivel (`CU-O##`, `CU-T##`), nunca prefijo de módulo embebido en el ID — la asociación CU↔módulo vive en la sección 4 de este documento y en la tabla de módulos del catálogo fuente. Un CU nuevo siempre se numera al final de la secuencia de su nivel (nunca reordenando los ya asignados), tal como ocurrió con CU-O48, CU-O112/O113 y con los 17 CU agregados en la sesión de diseño de BD de 2026-07-17 (CU-O114–O123, CU-T37–T43).

---

## 1. Catálogo completo — resumen por módulo (166 CU, 17 módulos)

El detalle CU-por-CU (ID, nombre, actor) **vive únicamente en el catálogo fuente** `docs/aerotrack-travel-casos-de-uso-v3.md` — no se reproduce aquí para evitar que este documento y la fuente diverjan con el tiempo (riesgo real: ya ocurrió con la versión anterior de este documento, que quedó desactualizada frente al catálogo v3.0/v3.1). Esta sección resume por módulo el **rango de CU**, el **departamento**, y si el módulo tiene carpeta en `specs/operativo/`, `specs/tactico/`, o ambas.

| Módulo | Prefijo | Departamento | CU-O (rango) | CU-T (rango) | `specs/operativo/` | `specs/tactico/` |
|---|---|---|---|---|---|---|
| Seguridad | SEG | Tecnología y Sistemas TI | O01–O13, O41–O43, O112, O113 | T01–T03, T35 | ✅ | ✅ |
| Integraciones *(nuevo)* | INT | Tecnología y Sistemas TI | — (0 CU-O) | T37, T38 | — | ✅ |
| Pasajeros | PAS | Gestión de Clientes | O14–O16, O49, O50 | T04, T05 | ✅ | ✅ |
| Vuelos | VUE | Ventas y Reservas | O17–O20, O45, O48, O51–O53, O114–O117 | T06–T08, T39–T41 | ✅ | ✅ |
| Hoteles | HOT | Ventas y Reservas | O54–O60, O118 | T09, T10 | ✅ | ✅ |
| Autos | AUT | Ventas y Reservas | O61–O64, O119 | T11 | ✅ | ✅ |
| Actividades | ACT | Ventas y Reservas | O65–O70, O120, O121 | T12, T42 | ✅ | ✅ |
| Cruceros | CRU | Ventas y Reservas | O71–O75, O122, O123 | T13, T43 | ✅ | ✅ |
| Paquetes | PAQ | Ventas y Reservas | O76–O80 | T14, T15 | ✅ | ✅ |
| Reservas | RES | Ventas y Reservas | O21–O25, O44, O45, O47, O81, O82 | T16–T18 | ✅ | ✅ |
| Disrupciones | DIS | Operaciones | O27–O31, O46, O83, O84 | T19–T21 | ✅ | ✅ |
| Facturación | FAC | Finanzas | O32–O40, O47, O85, O86 | T22, T23 | ✅ | ✅ |
| Cuenta / Mis Viajes | CTA | Gestión de Clientes | O87–O92 | T24, T25 | ✅ | ✅ |
| Carrito | CAR | Ventas y Reservas | O93–O96 | T26, T27 | ✅ | ✅ |
| Centro de Ayuda | AYU | Operaciones | O97–O100 | T28, T29, T36 | ✅ | ✅ |
| Ofertas y Promociones | OFE | Comercial y Marketing | O101–O105 | T30–T32, T44 | ✅ | ✅ |
| Asistente IA | IA | Comercial y Marketing | O106–O111 | T33, T34 | ✅ | ✅ |

**Único módulo sin `specs/operativo/`:** Integraciones — es 100% táctico (configuración/monitoreo de sincronización, no tiene acción interactiva de nivel Operativo propia).

---

## 2. CU expandidos (formato Jacobson completo, tal como están en la fuente)

La fuente expande en formato completo (FB/FA/RN) un subconjunto representativo de los CU originales (CU-O01–O48). Los demás quedan documentados en tablas resumen hasta que se redacte su RF/RN en el spec del módulo correspondiente.

> **Alcance no ampliado en esta actualización:** los 117 CU añadidos en v3.0/v3.1 (CU-O49 en adelante, CU-T01 en adelante) **no** tienen expansión Jacobson aquí todavía — se redactará como RF/RN al escribir el `spec.md` de cada módulo nuevo bajo `specs/operativo/<módulo>/` y `specs/tactico/<módulo>/`, siguiendo el mismo patrón que ya se usó para CU-O48 en `vuelos-spec.md`.

### CU-O01 — Iniciar sesión
**Actor principal:** Pasajero / Agente / Administrador
**Precondiciones:** El usuario cuenta con una cuenta registrada y activa.
**Postcondiciones:** El usuario obtiene una sesión válida y accede a las funciones permitidas por su rol.

**Flujo básico:**
1. El usuario accede a la pantalla de inicio de sesión.
2. El usuario ingresa su correo y contraseña.
3. El sistema valida las credenciales contra el repositorio de usuarios.
4. El sistema genera un token de sesión y redirige al panel correspondiente al rol del usuario.

**Flujos alternos:**
- 3.1 — Credenciales incorrectas: el sistema muestra "Credenciales incorrectas" y registra el intento fallido en auditoría.
- 3.2 — Cuenta inactiva: el sistema muestra "Cuenta desactivada. Contacte al administrador."

**Reglas de negocio:** RN-SEG-001 — Todo intento de login (exitoso o fallido) se audita.

---

### CU-O03 / CU-O04 — Recuperar y restablecer contraseña (autoservicio)
**Actor principal:** Cualquier usuario registrado
**Precondiciones:** El usuario tiene una cuenta con correo verificado.
**Postcondiciones:** La contraseña queda actualizada y el enlace de recuperación queda invalidado.

**Flujo básico:**
1. El usuario hace clic en "¿Olvidaste tu contraseña?" e ingresa su correo.
2. El sistema genera un enlace de un solo uso con expiración (tiempo configurable — CU-T03) y lo envía por correo.
3. El usuario abre el enlace e ingresa una nueva contraseña (con confirmación).
4. El sistema valida la fortaleza de la contraseña, la actualiza, invalida el enlace y notifica el cambio exitoso.

**Flujos alternos:**
- 1.1 — El correo no existe en el sistema: se muestra el mismo mensaje genérico, para no revelar qué correos están registrados.
- 2.1 — El enlace expiró o ya fue usado: el sistema rechaza el restablecimiento y ofrece generar uno nuevo.
- 3.1 — Las contraseñas no coinciden o no cumplen la política mínima: se rechaza con mensaje específico.

---

### CU-O07 — Registrar nuevo pasajero (autoservicio)
**Actor principal:** Pasajero
**Precondiciones:** Ninguna.
**Postcondiciones:** Se crea el perfil del pasajero con estado activo y puede iniciar sesión.

**Flujo básico:**
1. El pasajero accede a "Crear cuenta".
2. Ingresa sus datos (ver tabla de campos abajo).
3. El sistema valida formato y unicidad del correo.
4. El sistema crea el registro, envía correo de verificación y redirige al login.

**Flujos alternos:**
- 3.1 — Correo ya registrado: se rechaza con mensaje de duplicado.

**Campos del registro de pasajero:**

| Campo | Obligatorio | Motivo |
|---|---|---|
| Nombre completo (tal como en identificación) | Sí | Debe coincidir con el ID presentado en el aeropuerto |
| Fecha de nacimiento | Sí | Requerida para el manifiesto de pasajeros |
| Correo electrónico | Sí | Usuario de acceso y canal principal de notificación |
| Teléfono de contacto | Sí | Canal secundario de notificación |
| Contraseña | Sí | Autenticación |
| Género (M/F/Prefiero no decir) | Opcional | Algunos manifiestos lo solicitan |
| Número de documento de identidad (solo número, no imagen) | Opcional en registro / obligatorio al reservar | Se declara, no se verifica |
| Dirección de facturación | Opcional | Solo si se requiere recibo formal |
| Contacto de emergencia | Opcional | Valor agregado |

**Nota sobre documentos:** para vuelos domésticos EE. UU. no se pide ni sube ningún documento — solo se declara el nombre y, opcionalmente, el número de identificación, sin verificación ni imágenes. La gestión completa de documentos de viaje (pasaporte, cédula, vencimiento) vive en CU-O49 (módulo Pasajeros, v3.0), fuera del flujo de registro.

---

### CU-O17 — Buscar vuelos disponibles
**Actor principal:** Pasajero
**Precondiciones:** Existe catálogo de vuelos programables generado (CU-O19).
**Postcondiciones:** Se muestra una lista de vuelos que cumplen los criterios, ordenable y filtrable.

**Flujo básico:**
1. El pasajero ingresa origen, destino, fecha(s) y número de pasajeros en el buscador.
2. El sistema consulta el catálogo de vuelos programables filtrando por esos criterios.
3. El sistema muestra resultados con aerolínea, horario, duración, escalas, precio base y niveles de tarifa disponibles (Light/Standard/Flex).
4. El pasajero puede ordenar por precio, duración o escalas, y filtrar por aerolínea o rango horario (CU-O53).

**Flujos alternos:**
- 2.1 — No hay vuelos que cumplan los criterios: se muestra mensaje y sugerencia de fechas cercanas (cuando exista, reutiliza CU-T08 — reporte de rutas más buscadas — como fuente de sugerencia).

---

### CU-O21 — Crear reserva (autoservicio)
**Actor principal:** Pasajero
**Precondiciones:** El pasajero está autenticado y seleccionó un vuelo (CU-O17/O18), y opcionalmente clase de cabina/asiento (CU-O114–O116, v3.1).
**Postcondiciones:** Se crea la reserva en estado "pendiente de pago"; se libera automáticamente si el pago no se completa a tiempo.

**Flujo básico:**
1. El pasajero selecciona el vuelo y el nivel de tarifa.
2. El sistema solicita datos de pasajero(s) si viajan varios, y extras opcionales.
3. El pasajero confirma y es dirigido al pago (CU-O32).
4. Tras el pago exitoso, el sistema confirma la reserva, y dispara la factura (CU-O33) y el registro de comisión esperada (CU-O34).

**Flujos alternos:**
- 3.1 — El pago falla o se abandona: la reserva queda "pendiente" con expiración automática (tiempo configurable — CU-T18).

---

### CU-O27 a CU-O30 — Flujo combinado de detección y notificación de disrupciones
**Actor principal:** Sistema (automático)
**Precondiciones:** Existen reservas confirmadas con vuelos asociados.
**Postcondiciones:** El pasajero recibe una notificación oportuna ante cualquier cambio relevante, sin importar cuál fuente lo detectó.

**Flujo básico:**
1. (CU-E01, previsto — ya implementado como DAG) Para reservas lejanas, se calcula la probabilidad de disrupción vía simulador estadístico (CU-O83 registra el risk score resultante).
2. (CU-O27) Cerca de la fecha de viaje, el sistema consulta la API de estado de vuelo real, con control de cuota.
3. (CU-O28/O29) En paralelo, se monitorea la bandeja de correo de la agencia y se parsea cualquier aviso de cambio.
4. Cualquiera de las tres fuentes que detecte un cambio dispara (CU-O30) la notificación al pasajero.

**Flujos alternos:**
- 4.1 — Si el cambio implica cancelación, se dispara además CU-O37 (procesar reembolso) según la política de la tarifa comprada.

---

### CU-O32 — Procesar pago de reserva
**Actor principal:** Pasajero
**Precondiciones:** Existe una reserva en estado "pendiente de pago".
**Postcondiciones:** El pago queda registrado como exitoso o fallido; si es exitoso, la reserva pasa a "confirmada".

**Flujo básico:**
1. El sistema muestra el desglose: precio base + cargo de servicio + impuestos = total.
2. El pasajero ingresa los datos de pago (tarjeta de prueba vía Stripe test mode).
3. El sistema procesa el cobro y recibe confirmación de Stripe.
4. El sistema marca el pago como exitoso, actualiza la reserva a "confirmada" y registra la comisión esperada como "pendiente de cobro".

**Flujos alternos:**
- 3.1 — El pago es rechazado: se muestra el motivo y se permite reintentar.

---

### CU-O41 — Registrar evento en auditoría
**Actor principal:** Sistema (automático — nunca se invoca directamente por un actor humano, solo por `<<include>>` desde otro CU)
**Precondiciones:** Está ocurriendo una acción de creación, modificación o eliminación en cualquier módulo.
**Postcondiciones:** Queda un registro inmutable en el log de auditoría con: usuario, acción, módulo/tabla afectada, timestamp, resultado (éxito/fallo).

**Flujo básico:**
1. El CU que incluye a CU-O41 llega al punto donde ocurre la mutación de datos.
2. El sistema captura: usuario autenticado, acción realizada, módulo y tabla afectada, y el resultado.
3. El sistema inserta el registro en la colección de auditoría (solo inserción — constitución B4, nunca se edita ni se borra).
4. El flujo del CU que incluyó a este continúa normalmente.

**Flujos alternos:**
- 3.1 — Si la inserción del registro de auditoría fallara, el sistema no debe revertir la acción original ya realizada, pero debe alertar al Administrador (fallo de auditoría es en sí mismo un evento crítico a monitorear).

**Reglas de negocio:** RN-SEG-002 — Ninguna acción de creación/modificación/eliminación se considera completa hasta que su registro de auditoría correspondiente exista.

---

## 3. Mapa de relaciones y dependencias entre CU

### 3.1 Relaciones `<<include>>` / `<<extend>>` confirmadas (CU-O01–O48, tal como están documentadas en la fuente original)

> Semántica UML: en `<<include>>` la flecha apunta *hacia* el CU incluido (relación obligatoria). En `<<extend>>` la flecha apunta *hacia* el CU base (relación opcional/condicional).

| CU origen | Relación | CU destino | Condición / motivo |
|---|---|---|---|
| CU-O21/O22 (Crear reserva) | `<<include>>` | CU-O32 (Procesar pago) | Toda reserva requiere pago para confirmarse |
| CU-O32 (Procesar pago) | `<<include>>` | CU-O33 (Emitir factura) | Todo pago exitoso genera factura |
| CU-O32 (Procesar pago) | `<<include>>` | CU-O34 (Registrar comisión) | Todo pago exitoso registra comisión esperada |
| CU-O29 (Detectar cambio de itinerario) | `<<include>>` | CU-O30 (Notificar al pasajero) | Constitución E1: ninguna disrupción queda sin notificar |
| CU-O24 (Cancelar reserva) | `<<extend>>` | CU-O37 (Procesar reembolso) | Solo si la política de la tarifa comprada lo permite |
| CU-O30 (Notificar al pasajero) | `<<extend>>` | CU-O37 (Procesar reembolso) | Solo si la disrupción notificada es una cancelación |
| CU-O08, O09, O10, O11, O21-O26, O32-O37 (y en general todo CU que cree/modifique/elimine) | `<<include>>` | CU-O41 (Registrar evento en auditoría) | Constitución B4: toda mutación se audita, sin excepción |
| Todos excepto O01, O03, O04, O07 | `<<include>>` | CU-O42 (Verificar sesión activa) | Ninguna acción autenticada procede con token inválido/expirado |
| CU-O08, O16, O22, O35, O36, O37 | `<<include>>` | CU-O43 (Verificar permisos de acceso) | Acciones de Agente/Administrador siempre pasan por la matriz RBAC |
| CU-O21, O22, O23 | `<<include>>` | CU-O45 (Verificar disponibilidad de vuelo/cupo) | Evita condición de carrera sobre el último cupo simulado |
| CU-O30 (Notificar al pasajero) | `<<extend>>` | CU-O46 (Reintentar envío de notificación fallida) | Solo si el primer intento de envío falla (constitución F3) |
| CU-O23 (Modificar reserva) | `<<extend>>` | CU-O47 (Cobrar/reembolsar diferencia de tarifa) | Solo si el vuelo nuevo tiene precio distinto al original |

**Flujo alterno agregado (no requiere CU aparte):** CU-O24 (Cancelar reserva) — si el vuelo ya fue marcado "completado" por CU-O20, el sistema bloquea la cancelación con "No es posible cancelar un vuelo ya realizado."

### 3.2 Vista por CU transversal — quién lo incluye/extiende (CU-O41–O47)

| CU transversal | Incluido/extendido por | Naturaleza |
|---|---|---|
| CU-O41 (Registrar auditoría) | Prácticamente todo CU mutante de los 17 módulos | `<<include>>` obligatorio, universal |
| CU-O42 (Verificar sesión) | Todos excepto O01, O03, O04, O07 (los únicos que ocurren *antes* de tener sesión) y las vistas/búsquedas públicas | `<<include>>` obligatorio, universal |
| CU-O43 (Verificar RBAC) | Toda acción de Agente/Administrador | `<<include>>` obligatorio, acotado a roles internos |
| CU-O44 (Expirar reserva) | Ninguno lo incluye — se dispara por temporizador sobre CU-O21/O22 | Independiente, disparado por tiempo |
| CU-O45 (Verificar cupo) | O21, O22, O23 | `<<include>>` obligatorio, acotado a mutaciones de reserva |
| CU-O46 (Reintentar notificación) | Extiende a O30 | `<<extend>>` condicional (falla del primer envío) |
| CU-O47 (Diferencia de tarifa) | Extiende a O23 | `<<extend>>` condicional (cambio de precio) |

### 3.3 Mapa completo de los 166 CU (CU-O49 en adelante, todos los CU-T)

> No se duplica aquí — vive en `docs/aerotrack-travel-casos-de-uso-v3.md`, sección **"Relaciones entre casos de uso (base / `<<include>>` / `<<extend>>`)"**, organizada por módulo, con la misma semántica UML de 3.1. Cubre los 17 módulos completos. Para CU-O49 en adelante esas relaciones son un análisis editorial (no vienen expandidas en Jacobson todavía) — se confirman al redactar el `spec.md` de cada módulo nuevo, igual tratamiento que recibieron CU-O45/O47 en su momento.

### 3.4 Dependencias entre los 16 módulos-spec Operativos

Derivadas de las relaciones de 3.1–3.3 — determinan el orden de lectura/implementación sugerido. Los 6 módulos originales ya tienen esta relación confirmada; los 10 nuevos son una propuesta editorial basada en el flujo de negocio del catálogo.

| Módulo | Depende de | Por qué |
|---|---|---|
| **Seguridad** | (ninguno) | Base del sistema — todo lo demás depende de él (autenticación, RBAC, auditoría) |
| **Pasajeros** | Seguridad | El perfil de pasajero es 1:1 con `usuarios` (CU-O07 vive en Seguridad; historial/edición vive en Pasajeros) |
| **Vuelos** | Seguridad (RBAC de backoffice), Integraciones (config de sincronización, v3.1) | Generación/actualización de catálogo son procesos de sistema, pero su exposición en backoffice requiere permisos; su frecuencia de sync se generaliza en Integraciones (T37/T38) sin reemplazar T06/T07 |
| **Hoteles / Autos / Actividades / Cruceros** | Seguridad, Integraciones | Mismo patrón que Vuelos: catálogo generado por proceso automático (O118–O123), config/monitoreo de sync compartido con Integraciones |
| **Paquetes** | Vuelos, Hoteles, Autos, Actividades | Construye el paquete componiendo la selección de esos 4 módulos (CU-O76 consume O18/O57/O64/O69) |
| **Reservas** | Seguridad, Pasajeros, Vuelos (y, si aplica, Hoteles/Autos/Actividades/Cruceros/Paquetes según el tipo de ítem) | Toda reserva requiere pasajero autenticado, un producto válido y verificación de cupo (CU-O45) |
| **Carrito** | Vuelos, Hoteles, Autos, Actividades, Reservas | Agrega ítems de cualquier producto y entrega el checkout a Reservas (CU-O96 incluye O21/O22) |
| **Disrupciones** | Vuelos, Reservas | Detecta cambios sobre vuelos del catálogo y notifica a pasajeros con reservas confirmadas sobre esos vuelos |
| **Facturación** | Reservas, Seguridad | Todo pago/factura/comisión nace de una reserva; conciliación y remesas son acciones de Administrador (RBAC) |
| **Cuenta / Mis Viajes** | Reservas, Vuelos, Hoteles, Autos, Actividades, Cruceros | Agrega historial de reservas y favoritos de todos los productos; sucesor de CU-O26 para alertas de precio |
| **Centro de Ayuda** | Seguridad, Asistente IA | Escalación por email cuando el Asistente IA no resuelve la consulta (CU-O100 extiende O106-O108) |
| **Ofertas y Promociones** | Carrito, Reservas, Paquetes | Los cupones se aplican en el checkout de cualquiera de esos módulos |
| **Asistente IA** | Seguridad, Reservas | Consultas transaccionales (CU-O108) requieren sesión activa y leen datos de reserva del pasajero |

**Orden de lectura recomendado para las specs de módulo Operativo:** Seguridad → Pasajeros → Vuelos → Hoteles/Autos/Actividades/Cruceros → Paquetes → Reservas → Carrito → Disrupciones → Facturación → Cuenta/Mis Viajes → Centro de Ayuda → Ofertas y Promociones → Asistente IA. (Integraciones no tiene spec Operativo — se lee junto con Vuelos por ser donde primero aparece el patrón que generaliza.)

---

## 4. Asignación de los 166 CU a la estructura `specs/operativo/` y `specs/tactico/`

**Decisión de estructura (2026-07-17):** a diferencia de la ronda anterior (un único nivel Operativo, una carpeta por módulo bajo `specs/operativo/`), ahora existen dos niveles redactados (Operativo y Táctico) y 17 módulos. La estructura es **una carpeta por módulo dentro de cada carpeta de nivel** — nunca un módulo mezclando CU-O y CU-T en el mismo `spec.md`:

```
specs/
  operativo/
    seguridad/        ← CU-O01–O13, O41–O43, O112, O113
    pasajeros/        ← CU-O14–O16, O49, O50
    vuelos/           ← CU-O17–O20, O45, O48, O51–O53, O114–O117
    hoteles/          ← CU-O54–O60, O118
    autos/            ← CU-O61–O64, O119
    actividades/      ← CU-O65–O70, O120, O121
    cruceros/         ← CU-O71–O75, O122, O123
    paquetes/         ← CU-O76–O80
    reservas/         ← CU-O21–O25, O44, O45, O47, O81, O82
    disrupciones/     ← CU-O27–O31, O46, O83, O84
    facturacion/      ← CU-O32–O40, O47, O85, O86
    cuenta-mis-viajes/← CU-O87–O92
    carrito/          ← CU-O93–O96
    centro-ayuda/     ← CU-O97–O100
    ofertas-promociones/ ← CU-O101–O105
    asistente-ia/     ← CU-O106–O111
    (Integraciones no tiene carpeta aquí — 0 CU-O)
  tactico/
    seguridad/        ← CU-T01–T03, T35
    integraciones/    ← CU-T37, T38
    pasajeros/        ← CU-T04, T05
    vuelos/           ← CU-T06–T08, T39–T41
    hoteles/          ← CU-T09, T10
    autos/            ← CU-T11
    actividades/      ← CU-T12, T42
    cruceros/         ← CU-T13, T43
    paquetes/         ← CU-T14, T15
    reservas/         ← CU-T16–T18
    disrupciones/     ← CU-T19–T21
    facturacion/      ← CU-T22, T23
    cuenta-mis-viajes/← CU-T24, T25
    carrito/          ← CU-T26, T27
    centro-ayuda/     ← CU-T28, T29, T36
    ofertas-promociones/ ← CU-T30–T32
    asistente-ia/     ← CU-T33, T34
```

Las 27 carpetas (16 operativo + 17 táctico, comparten 16 módulos + Integraciones solo-táctico) ya están creadas en el repositorio, vacías — el `spec.md`/`plan.md`/`tasks.md`/`checklist.md` de cada una se redacta en una ronda posterior, módulo por módulo.

### 4.1 CU transversales — asignación (sin cambios respecto a la ronda anterior)

Los 7 CU transversales originales (O41-O47) no tienen módulo-spec propio — se asignan al módulo-spec cuyo dominio de datos y flujo principal les corresponde. Esta asignación es una propuesta editorial y queda abierta a ajuste:

| CU | Módulo-spec destino | Justificación |
|---|---|---|
| CU-O41 (Registrar auditoría) | **Seguridad (SEG)**, operativo | Dueño de la tabla `auditoria` y de CU-O12/O13 (ver/filtrar el mismo log) |
| CU-O42 (Verificar sesión activa) | **Seguridad (SEG)**, operativo | Dueño de `usuarios` y del mecanismo de token (CU-O01/O02) |
| CU-O43 (Verificar RBAC) | **Seguridad (SEG)**, operativo | Dueño de `roles`, `roles_permisos`, `roles_permisos_tablas` |
| CU-O44 (Expirar reserva pendiente) | **Reservas (RES)**, operativo | Opera exclusivamente sobre `reservas.estado`, extiende el ciclo de vida de CU-O21/O22 |
| CU-O45 (Verificar disponibilidad de vuelo/cupo) | **Vuelos (VUE) y Reservas (RES) — doble documentación**, ambos operativo | Se invoca desde dos puntos con enfoque distinto en cada uno (ver detalle abajo) |
| CU-O46 (Reintentar notificación fallida) | **Disrupciones (DIS)**, operativo | Extiende directamente a CU-O30, mismo dominio de `notificaciones` |
| CU-O47 (Diferencia de tarifa) | **Reservas (RES) y Facturación (FAC) — doble documentación**, ambos operativo | Se invoca desde dos puntos con enfoque distinto en cada uno (ver detalle abajo) |

- **CU-O45 (Verificar disponibilidad de vuelo/cupo):**
  - En `specs/operativo/vuelos/`: el **RF** del servicio de validación en sí — cómo se consulta y decrementa `tarifas_vuelo.cupos_disponibles`, quién es dueño del dato. Perspectiva de mecanismo/dato.
  - En `specs/operativo/reservas/`: la **RN** de cómo CU-O21/O22/O23 invocan ese servicio como precondición y qué ocurre si falla (bloqueo de creación/modificación, condición de carrera — ver QP-08). Perspectiva de orquestación/negocio.
- **CU-O47 (Cobrar/reembolsar diferencia de tarifa):**
  - En `specs/operativo/reservas/`: la **RN** de cuándo se dispara — extend condicional de CU-O23, solo si el vuelo nuevo tiene precio distinto al original. Perspectiva de negocio/disparador.
  - En `specs/operativo/facturacion/`: el **RF** del mecanismo real de cobro/reembolso de la diferencia vía Stripe (`pagos`, `reembolsos`). Perspectiva de mecanismo/dato.

### 4.2 CU transversales nuevos (v3.0/v3.1) — misma lógica de doble documentación cuando aplica

| CU | Módulo-spec destino | Justificación |
|---|---|---|
| CU-O85 (Convertir moneda) | **Facturación (FAC)**, operativo | Dueño de `tasas_cambio`; es transversal *en consumo* (toda presentación de precio de Vuelos/Hoteles/Autos/Actividades/Cruceros/Paquetes lo usa) pero el RF vive una sola vez en Facturación |
| CU-O86 (Capturar pago diferido de hotel) | **Facturación (FAC) y Hoteles (HOT) — doble documentación** | RN de cuándo se dispara (extend de O60, "Reservar sin pagar ahora") en Hoteles; RF del cobro real vía Stripe en Facturación |
| CU-O112/O113 (Permisos granulares de módulo/tabla) | **Seguridad (SEG)**, operativo | Extienden a CU-O10 (Editar rol); alimentan la matriz que consulta CU-O43 |
| CU-T37/T38 (Integraciones) | **Integraciones (INT)**, táctico, único | Generalizan T06/T07 (config/monitoreo específico de Vuelos) para Hoteles/Autos/Actividades/Cruceros — no los reemplazan, son paralelos |
| CU-O100 (Escalar caso a agente) | **Centro de Ayuda (AYU)**, operativo | Extiende a CU-O106–O108 (Asistente IA); dueño de `casos_escalados` |

**Nota de implementación (sin cambios de criterio):** cada módulo-spec debe documentar los CU transversales que consume vía `<<include>>`/`<<extend>>` en su sección "Casos de uso relacionados", aunque el RF/RN detallado viva en el/los módulo(s)-spec destino de las tablas anteriores.

---

## 5. Escenarios "qué pasa si"

Escenarios de análisis derivados del catálogo y de los principios A-J de `constitution.md`/`reglas.md`. No introducen CU nuevos: cada escenario referencia el/los CU y principio(s) que lo resuelven, para que el spec del módulo correspondiente lo convierta en flujo alterno o regla de negocio explícita.

### 5.1 Confirmados (nivel Operativo original, sin cambios)

| # | Escenario | CU / RN involucrados | Principio constitucional | Resolución esperada |
|---|---|---|---|---|
| QP-01 | La API de estado de vuelo real (AviationStack/AeroDataBox) no responde o se agota la cuota | CU-O27 | E3 — Degradación ordenada | El sistema sigue operando con el simulador estadístico como respaldo; nunca falla silenciosamente, se registra el evento de degradación |
| QP-02 | Dos fuentes (API real y monitor de correo) detectan el mismo cambio de itinerario casi al mismo tiempo | CU-O27, O28, O29, O30 | E2 — Precedencia y deduplicación | Se aplica una regla de precedencia entre fuentes y se notifica una sola vez al pasajero por el mismo cambio |
| QP-03 | Falla la inserción del registro de auditoría tras una mutación ya ejecutada | CU-O41 (flujo alterno 3.1) | B4 — Auditoría inmutable y universal | La acción original no se revierte, pero se alerta al Administrador; el fallo de auditoría es en sí mismo un evento crítico |
| QP-04 | Stripe confirma el pago justo cuando la reserva ya expiró por temporizador (condición de carrera) | CU-O32, O44 | D1 — Idempotencia obligatoria | El sistema debe resolver el conflicto de forma determinista y verificable (p. ej. honrar el pago y re-confirmar la reserva, o revertir el cobro) — a definir como RN explícita en `reservas`/`facturacion` |
| QP-05 | Un Agente intenta una acción sobre una tabla fuera de su restricción de Nivel 2 (RBAC) | CU-O43 | B1 — RBAC de dos niveles obligatorio | La acción se bloquea antes de tocar datos; el bloqueo se comunica visualmente (J6), no como ausencia silenciosa de datos |
| QP-06 | Se intenta cancelar una reserva de un vuelo ya marcado "completado" por CU-O20 | CU-O24 (flujo alterno agregado, sección 3.1) | — | El sistema bloquea la cancelación con "No es posible cancelar un vuelo ya realizado" |
| QP-07 | Llega un correo de disrupción que no corresponde a ninguna reserva activa (falso positivo o vuelo no reconocido) | CU-O28, O29 | F3 — Aislamiento de fallos de terceros | El aviso se descarta o se marca para revisión manual sin generar notificación errónea al pasajero ni interrumpir el resto del monitoreo |
| QP-08 | El precio de la tarifa cambia mientras el pasajero está en checkout (condición de carrera sobre el último cupo) | CU-O21, O22, O45 | G2 — Transparencia de precio | El sistema revalida precio/cupo antes de confirmar el pago; si cambió, se informa explícitamente al pasajero antes de cobrar, nunca se cobra un monto distinto al mostrado |
| QP-09 | El reintento de notificación (CU-O46) también falla | CU-O30, O46 | F2 — Timeouts y reintentos configurables | Tras agotar los reintentos configurados, el sistema debe dejar constancia del fallo definitivo (no reintentar indefinidamente) y hacerlo visible para el Agente/Administrador |
| QP-10 | Se intenta eliminar un rol que tiene usuarios activos asignados | CU-O11 | — (integridad referencial) | El sistema bloquea la eliminación o exige reasignar primero a los usuarios afectados — a definir como RN explícita en `seguridad` |
| QP-11 | El token de sesión expira a mitad de un flujo multi-paso (checkout de reserva) | CU-O42, J10 | J10 — Navegación sin pérdida de estado | Se solicita reautenticación sin descartar los datos ya ingresados en pasos previos del flujo |
| QP-12 | Una disrupción notificada es una cancelación, pero la tarifa comprada no da derecho a reembolso | CU-O30 → O37 (extend condicional) | C3 — Transparencia en cancelaciones y reembolsos | CU-O37 no se dispara; el pasajero puede consultar la política aplicada de forma explícita, nunca una resolución discrecional u oculta |
| QP-13 | El pasajero solicita eliminar sus datos personales mientras tiene una reserva activa o pendiente de pago | CU-O05, O15 | C2 — Propósito declarado y derecho de eliminación | La eliminación se resuelve respetando la retención mínima necesaria para reservas/pagos en curso — a definir como RN explícita en `seguridad`/`pasajeros` |

### 5.2 Nuevos (módulos v3.0/v3.1) — propuesta editorial de esta sesión

| # | Escenario | CU / RN involucrados | Principio constitucional | Resolución esperada |
|---|---|---|---|---|
| QP-14 | Se agota la cuota mensual de una fuente externa nueva (HotelLens, Global Rental Cars, Travel Advisor, Cruise Pricing) antes de fin de mes | CU-O118–O123, CU-T37/T38 | F3 — Aislamiento de fallos de terceros | El catálogo de ese producto deja de refrescarse pero sigue sirviendo el último dato generado; T38 registra la corrida como "parcial/fallida por cuota" — nunca bloquea la búsqueda del pasajero con error crudo |
| QP-15 | La disponibilidad sintética (Actividades CU-O121, Cruceros CU-O123) genera cupo cero para todos los horarios/camarotes de una fecha consultada | CU-O68, O75, O121, O123 | G1 — Autoservicio, transparencia | Mismo tratamiento que "sin resultados" en búsqueda (QP análogo a O17): mensaje claro, sin error técnico expuesto |
| QP-16 | Un pasajero selecciona asiento premium (CU-O116) pero la reserva expira por falta de pago (CU-O44) antes de confirmarse | CU-O21, O44, O116 | D1 — Idempotencia | La liberación de la reserva libera también el asiento reservado; ningún cargo de asiento premium se cobra sobre una reserva expirada — a definir como RN explícita en `reservas` |
| QP-17 | El pasajero no seleccionó asiento y llega la ventana de check-in gratuito configurada (CU-T40) sin que se haya asignado uno | CU-O117 | G1 — Autoservicio como camino por defecto | Se dispara la asignación automática (CU-O117); el pasajero puede seguir cambiando el asiento asignado hasta el cierre real de check-in si hay disponibilidad |
| QP-18 | Se aplica un cupón de descuento (CU-O103) sobre un paquete que ya trae su propio descuento por tipo (CU-T14) | CU-O76, O103, T14, T44 | G2 — Transparencia de precio | **Resuelto 2026-07-18** — ya no es una decisión de negocio pendiente: CU-T44 (nuevo, Ofertas y Promociones) lo convierte en una regla configurable — default global (`configuracion_sistema`, clave `cupones.acumulable_con_paquete_default`) + excepción opcional por cupón individual (`cupones_descuento.acumulable_con_paquete`, la excepción siempre gana sobre el default). Ver `ofertas-promociones-spec.md` (ambos niveles) para el detalle completo. El desglose de precio sigue siendo siempre visible (REG-G2), sin importar el resultado de la regla. |
| QP-19 | El Asistente IA (CU-O106-O108) no puede responder una consulta transaccional por falta de datos verificables | CU-O100, O106-O108 | H1 — Contexto de IA acotado y verificable | El asistente no inventa la respuesta; ofrece escalar el caso a agente humano por email (CU-O100) en vez de responder con información no verificada |

---

## 6. Matriz técnica

### 6.1 Confirmada — CU-O01–O47 (formato completo con tablas DBML, sin cambios respecto a la ronda anterior)

| ID | Nombre | Actor | Tipo | Módulo-spec | Prefijo | Relación UML | Tablas principales (DBML) |
|---|---|---|---|---|---|---|---|
| CU-O01 | Iniciar sesión | Pasajero/Agente/Admin | Interactivo | Seguridad | SEG | base | `usuarios`, `auditoria` |
| CU-O02 | Cerrar sesión | Todos | Interactivo | Seguridad | SEG | base | `usuarios` |
| CU-O03 | Recuperar contraseña | Todos | Interactivo | Seguridad | SEG | base | `usuarios`, `configuracion_sistema` |
| CU-O04 | Restablecer contraseña | Todos | Interactivo | Seguridad | SEG | base | `usuarios` |
| CU-O05 | Ver y editar perfil propio | Todos | Interactivo | Seguridad | SEG | base | `usuarios`, `pasajeros` |
| CU-O06 | Cambiar contraseña (autenticado) | Todos | Interactivo | Seguridad | SEG | base | `usuarios` |
| CU-O07 | Registrar nuevo pasajero | Pasajero | Interactivo | Seguridad | SEG | base | `usuarios`, `pasajeros` |
| CU-O08 | Gestionar usuarios internos | Admin | Interactivo | Seguridad | SEG | include→O41,O42,O43 | `usuarios`, `roles` |
| CU-O09 | Crear rol | Admin | Interactivo | Seguridad | SEG | include→O41,O42 | `roles` |
| CU-O10 | Editar rol | Admin | Interactivo | Seguridad | SEG | include→O41,O42 | `roles`, `roles_permisos`, `roles_permisos_tablas` |
| CU-O11 | Eliminar rol | Admin | Interactivo | Seguridad | SEG | include→O41,O42 | `roles` |
| CU-O12 | Ver log de auditoría | Admin | Interactivo | Seguridad | SEG | include→O42 | `auditoria` |
| CU-O13 | Filtrar y exportar log de auditoría | Admin | Interactivo | Seguridad | SEG | include→O42; extend de O12 | `auditoria` |
| CU-O14 | Consultar historial de reservas propio | Pasajero | Interactivo | Pasajeros | PAS | include→O42 | `reservas`, `pasajeros` |
| CU-O15 | Editar datos de contacto | Pasajero | Interactivo | Pasajeros | PAS | include→O41,O42 | `pasajeros`, `usuarios` |
| CU-O16 | Buscar y gestionar pasajeros (backoffice) | Agente/Admin | Interactivo | Pasajeros | PAS | include→O41,O42,O43 | `pasajeros`, `usuarios`, `reservas` |
| CU-O17 | Buscar vuelos disponibles | Pasajero | Interactivo | Vuelos | VUE | base | `vuelos_catalogo`, `tarifas_vuelo`, `niveles_tarifa` |
| CU-O18 | Ver detalle y niveles de tarifa | Pasajero | Interactivo | Vuelos | VUE | base | `vuelos_catalogo`, `tarifas_vuelo`, `niveles_tarifa`, `aerolineas` |
| CU-O19 | Generar catálogo de vuelos programables | Sistema (Airflow) | Automático | Vuelos | VUE | base | `vuelos_catalogo`, `tarifas_vuelo` (lee `dim_ruta` heredado) |
| CU-O20 | Actualizar estado de un vuelo | Sistema | Automático | Vuelos | VUE | base | `vuelos_catalogo` |
| CU-O48 *(añadido)* | Forzar/ajustar puntualmente un vuelo del catálogo (demo) | Administrador | Interactivo, EXCEPCIONAL | Vuelos | VUE | include→O41,O42,O43; puede disparar O29/O30 | `vuelos_catalogo` |
| CU-O21 | Crear reserva (autoservicio) | Pasajero | Interactivo | Reservas | RES | include→O32,O41,O42,O45 | `reservas`, `reserva_pasajeros`, `reserva_extras`, `tarifas_vuelo` |
| CU-O22 | Crear reserva asistida | Agente | Interactivo | Reservas | RES | include→O32,O41,O42,O43,O45 | `reservas` (+ `agente_id`) |
| CU-O23 | Modificar reserva | Pasajero/Agente | Interactivo | Reservas | RES | include→O41,O42,O45; extend→O47 | `reservas`, `reserva_pasajeros`, `reserva_extras`, `tarifas_vuelo` |
| CU-O24 | Cancelar reserva | Pasajero/Agente | Interactivo | Reservas | RES | include→O41,O42; extend→O37 | `reservas` |
| CU-O25 | Consultar estado de una reserva | Pasajero | Interactivo | Reservas | RES | include→O42 | `reservas` |
| CU-O27 | Consultar estado real de vuelo vía API externa | Sistema | Automático | Disrupciones | DIS | base (degradable, E3) | `vuelos_catalogo`, `disrupciones`, `configuracion_sistema` |
| CU-O28 | Monitorear bandeja de correo | Sistema | Automático | Disrupciones | DIS | base | `disrupciones`, `configuracion_sistema` |
| CU-O29 | Detectar cambio de itinerario | Sistema | Automático | Disrupciones | DIS | include→O30 | `disrupciones`, `vuelos_catalogo` |
| CU-O30 | Notificar al pasajero | Sistema | Automático | Disrupciones | DIS | extend→O37,O46 | `notificaciones`, `disrupciones`, `reservas` |
| CU-O31 | Consultar historial de notificaciones | Pasajero/Agente | Interactivo | Disrupciones | DIS | include→O42 | `notificaciones` |
| CU-O32 | Procesar pago de reserva | Pasajero | Interactivo | Facturación | FAC | include→O33,O34,O41,O42 | `pagos`, `metodos_pago`, `reservas` |
| CU-O33 | Emitir factura/recibo | Sistema | Automático | Facturación | FAC | base | `facturas`, `pagos` |
| CU-O34 | Registrar comisión por reserva | Sistema | Automático | Facturación | FAC | base | `comisiones` |
| CU-O35 | Conciliar comisiones pendientes vs. cobradas | Admin | Interactivo | Facturación | FAC | include→O41,O42,O43 | `comisiones` |
| CU-O36 | Generar remesa simulada a aerolínea | Sistema/Admin | Mixto | Facturación | FAC | include→O41,O42,O43 | `remesas`, `remesa_comisiones`, `comisiones` |
| CU-O37 | Procesar reembolso | Sistema/Agente | Mixto | Facturación | FAC | include→O41,O42,O43 | `reembolsos`, `pagos`, `politicas_reembolso` |
| CU-O38 | Consultar historial de pagos | Pasajero | Interactivo | Facturación | FAC | include→O42 | `pagos` |
| CU-O39 | Descargar factura/recibo en PDF | Pasajero | Interactivo | Facturación | FAC | include→O42 | `facturas` |
| CU-O40 | Descargar itinerario / e-ticket en PDF | Pasajero | Interactivo | Facturación | FAC | include→O42 | `reservas`, `vuelos_catalogo` |
| CU-O41 | Registrar evento en auditoría | Sistema | Automático (include target) | Seguridad | SEG | included-by (universal) | `auditoria` |
| CU-O42 | Verificar sesión activa | Sistema | Automático (include target) | Seguridad | SEG | included-by (universal) | `usuarios` (token) |
| CU-O43 | Verificar permisos de acceso (RBAC) | Sistema | Automático (include target) | Seguridad | SEG | included-by (agente/admin) | `roles_permisos`, `roles_permisos_tablas` |
| CU-O44 | Expirar reserva pendiente de pago | Sistema (temporizador) | Automático | Reservas | RES | independiente | `reservas` |
| CU-O45 | Verificar disponibilidad de vuelo/cupo | Sistema | Automático (include target) | **Vuelos (RF) + Reservas (RN)** | VUE / RES | included-by O21,O22,O23 | `tarifas_vuelo` |
| CU-O46 | Reintentar envío de notificación fallida | Sistema | Automático (extend target) | Disrupciones | DIS | extend de O30 | `notificaciones` |
| CU-O47 | Cobrar/reembolsar diferencia de tarifa | Sistema/Pasajero | Mixto (extend target) | **Reservas (RN) + Facturación (RF)** | RES / FAC | extend de O23 | `pagos`, `reembolsos`, `reservas` |

### 6.2 Módulos v3.0/v3.1 — tablas principales por módulo (nivel módulo, no por CU)

> El detalle por-CU con tipo/relación UML/tablas exactas se completa al redactar cada `spec.md`, igual que se hizo arriba para los 47 CU originales. Esta tabla da trazabilidad de alto nivel mientras tanto — tablas confirmadas en `docs/fuentes-datos-por-tabla.md`.

| Módulo | Prefijo | CU-O | CU-T | Tablas principales (DBML) |
|---|---|---|---|---|
| Integraciones | INT | — | T37, T38 | `fuentes_datos_externas`, `sincronizaciones_log` |
| Hoteles | HOT | O54–O60, O118 | T09, T10 | `hoteles_catalogo`, `hoteles_tarifas`, `hoteles_resenas`, `cargos_locales_destino` |
| Autos | AUT | O61–O64, O119 | T11 | `autos_catalogo` |
| Actividades | ACT | O65–O70, O120, O121 | T12, T42 | `actividades_catalogo`, `actividades_resenas`, `actividades_horarios` |
| Cruceros | CRU | O71–O75, O122, O123 | T13, T43 | `navieras`, `barcos`, `cruceros_catalogo`, `cruceros_camarotes_tarifa` |
| Paquetes | PAQ | O76–O80 | T14, T15 | `tipos_paquete_descuento`, `proveedores_comerciales` (+ compone `reserva_items` de Reservas) |
| Carrito | CAR | O93–O96 | T26, T27 | `carritos`, `carrito_items` |
| Cuenta / Mis Viajes | CTA | O87–O92 | T24, T25 | `favoritos`, `busquedas_recientes`, `viajes_personalizados`, `programa_beneficios_niveles`, `programa_beneficios_movimientos` |
| Centro de Ayuda | AYU | O97–O100 | T28, T29, T36 | `articulos_ayuda`, `articulo_calificaciones`, `casos_escalados` |
| Ofertas y Promociones | OFE | O101–O105 | T30–T32, T44 | `ofertas_destacadas`, `cupones_descuento` (+`acumulable_con_paquete`, NUEVO 2026-07-18), `cupones_uso`, `newsletter_suscripciones`, `campanas_email` |
| Asistente IA | IA | O106–O111 | T33, T34 | `conversaciones_ia`, `mensajes_ia` |
| Vuelos *(campos nuevos v3.1)* | VUE | O51–O53, O114–O117 | T39–T41 | `asientos_vuelo`, `predicciones_precio_ruta` (+ tablas ya listadas en 6.1) |
| Reservas *(campos nuevos v3.0)* | RES | O81, O82 | T16–T18 | `requisitos_visa_cache` (+ tablas ya listadas en 6.1) |
| Facturación *(campos nuevos v3.0/v3.1)* | FAC | O85, O86 | T22, T23 | `tasas_cambio` (+ tablas ya listadas en 6.1) |
| Seguridad *(campos nuevos v3.0)* | SEG | O112, O113 | T35 | `modulos`, `modulo_tablas` (+ tablas ya listadas en 6.1) |

---

## 7. Puntos abiertos

### 7.1 Resueltos en rondas anteriores
1. Asignación de módulo de los 7 CU transversales originales: CU-O41/O42/O43 quedan solo en Seguridad. CU-O45 y CU-O47 se documentan en **dos** módulos-spec cada uno.
2. QP-04 y QP-08 (condiciones de carrera de pago/cupo): se redactarán como RN nuevas al escribir `reservas`/`facturacion`.
3. QP-10 y QP-13: se redactarán como RN nuevas en `seguridad`/`pasajeros`.

### 7.2 Resueltos 2026-07-17
4. **Estructura de carpetas:** `specs/operativo/` y `specs/tactico/` con una carpeta por módulo cada una (27 carpetas creadas, ver sección 4).
5. **Catálogo renumerado:** los 17 CU con ID temporal `-N#` de la sesión de diseño de BD quedaron con ID final (CU-O114–O123, CU-T37–T43) en `docs/aerotrack-travel-casos-de-uso-v3.md`.
6. **Mapa de relaciones de los CU:** cubierto en `docs/aerotrack-travel-casos-de-uso-v3.md` sección "Relaciones entre casos de uso" — no se duplica en este documento (ver 3.3).

### 7.3 Resueltos 2026-07-18
7. **`spec.md`/`glosario.md`/`consideraciones.md`** de `000-sistema-general/` actualizados al alcance de 166 CU/17 módulos/2 niveles y 6 verticales de producto (ya no "solo vuelos" ni "48 CU-O, 6 módulos") — incluyendo que Asistente IA ya es módulo Operativo/Táctico en scope, no reservado.
8. **Los 6 `spec.md`/`plan.md`/`tasks.md`/`checklist.md` de módulo ya existentes** (seguridad, pasajeros, vuelos, reservas, disrupciones, facturacion) actualizados con los CU nuevos que les corresponden y las referencias a CU-T corregidas (ej. `vuelos-spec.md` ya no cita "CU-T18 tendencia histórica" — corregido a CU-O51).
9. **`diseno-visual.md` reescrito a v4** (Sky Blue × Modernist híbrido), importado vía Design MCP desde un proyecto de diseño real del cliente.
10. **Los 10 módulos nuevos del catálogo v3.0/v3.1 tienen spec completo** (`spec.md`+`plan.md`+`tasks.md`+`checklist.md`, ambos niveles donde aplica): Hoteles, Autos, Actividades, Cruceros, Paquetes, Carrito, Cuenta/Mis Viajes, Centro de Ayuda, Ofertas y Promociones, Asistente IA, más Integraciones (solo Táctico, único módulo sin nivel Operativo). Las 27 carpetas creadas el 17-07 ya no están vacías.
11. **CU-O94 corregido** (Carrito ya admite cruceros — era un olvido de texto, el esquema `carrito_items` ya lo soportaba) y **QP-18 resuelto** (CU-T44 nuevo, acumulación cupón+paquete configurable con default global + excepción por cupón).

### 7.4 Pendientes — a resolver en las próximas rondas
12. **Jacobson completo y matriz técnica por-CU** para los 118 CU que no son de los 48 originales (CU-O49 en adelante, todo el nivel Táctico): se redacta módulo por módulo al escribir/ampliar su `spec.md` con el mismo detalle que los 47 CU originales — hoy esos módulos tienen RF/RN completos pero no expandidos en formato Jacobson estricto (FB/FA numerado).
13. **Nivel Táctico de los 6 módulos originales** (Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación) — su Operativo ya existía y fue actualizado; el Táctico (`specs/tactico/{modulo}/`) todavía no está redactado, carpetas creadas y vacías.
14. **Migración de esquema `reservas`→`reserva_items`** (multi-producto) — documentada en detalle en `reservas-spec.md` y en `specs/000-sistema-general/pendientes-implementacion-codigo.md`, pero no iniciada; bloquea la implementación real de Hoteles/Autos/Actividades/Cruceros/Paquetes/Carrito aunque sus specs ya estén completos.
15. **Retrofit de `busquedas_recientes`** en Vuelos/Hoteles/Autos/Actividades/Cruceros — ninguno de esos 5 specs documenta escribir ahí todavía; lo necesita CU-O89 (Cuenta/Mis Viajes). Anotado en `cuenta-mis-viajes-spec.md`, no propagado hacia atrás a los 5 specs de producto.

Con este documento actualizado, el siguiente paso es redactar los `spec.md` de cada módulo bajo `specs/operativo/<módulo>/` y `specs/tactico/<módulo>/`, en el orden sugerido en la sección 3.4.
