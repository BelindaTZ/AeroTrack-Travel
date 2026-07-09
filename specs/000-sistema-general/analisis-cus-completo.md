# Análisis completo de casos de uso — Nivel Operativo

**Fuente única de verdad:** `docs/aerotrack-travel-casos-de-uso-operativos.md` (v2 — corregida y renumerada, v2.1 con análisis include/extend)
**Total:** 48 CU-O (40 del catálogo original + 7 transversales identificados vía análisis `<<include>>`/`<<extend>>` + 1 añadido durante la redacción de specs — ver nota abajo)
**Alcance de este documento:** no crea, no modifica y no reclasifica ningún caso de uso del catálogo fuente original de 47 CU. Reproduce ese catálogo tal cual está y le añade tres capas de análisis nuevas: (1) mapa de relaciones/dependencias, (2) escenarios "qué pasa si", (3) matriz técnica de asignación a los 6 módulos-spec operativos.

> **Nota — CU-O48 (añadido fuera de la fuente original):** durante la redacción de `vuelos-spec.md` se agregó **CU-O48 — Forzar/ajustar puntualmente un vuelo del catálogo (solo pruebas/demo)**, Actor: Administrador. No proviene de `docs/aerotrack-travel-casos-de-uso-operativos.md`; es una vía **excepcional**, fuera del flujo de negocio normal (el catálogo sigue siendo 100% automático en producción vía CU-O19/O20), pensada únicamente para preparar escenarios reproducibles de demo/sustentación. Incluye `<<include>>` a CU-O41 (auditoría) y CU-O43 (RBAC), igual que cualquier acción de Administrador. Documentado en detalle en `vuelos-spec.md`.

---

## 1. Catálogo completo (48 CU-O), tal como está en la fuente + CU-O48

### Módulo: Seguridad
| ID | Nombre | Actor |
|---|---|---|
| CU-O01 | Iniciar sesión | Pasajero / Agente / Administrador |
| CU-O02 | Cerrar sesión | Todos |
| CU-O03 | Recuperar contraseña (solicitar enlace) | Todos |
| CU-O04 | Restablecer contraseña vía enlace | Todos |
| CU-O05 | Ver y editar perfil propio | Todos |
| CU-O06 | Cambiar contraseña (autenticado) | Todos |
| CU-O07 | Registrar nuevo pasajero (autoservicio) | Pasajero |
| CU-O08 | Gestionar usuarios internos (agentes/admin) | Administrador |
| CU-O09 | Crear rol | Administrador |
| CU-O10 | Editar rol | Administrador |
| CU-O11 | Eliminar rol | Administrador |
| CU-O12 | Ver log de auditoría | Administrador |
| CU-O13 | Filtrar y exportar log de auditoría | Administrador |

### Módulo: Pasajeros
| ID | Nombre | Actor |
|---|---|---|
| CU-O14 | Consultar historial de reservas propio | Pasajero |
| CU-O15 | Editar datos de contacto | Pasajero |
| CU-O16 | Buscar y gestionar pasajeros (backoffice) | Agente / Administrador |

### Módulo: Vuelos (catálogo)
| ID | Nombre | Actor |
|---|---|---|
| CU-O17 | Buscar vuelos disponibles | Pasajero |
| CU-O18 | Ver detalle y niveles de tarifa de un vuelo | Pasajero |
| CU-O19 | Generar catálogo de vuelos programables | Sistema (automático, Airflow) |
| CU-O20 | Actualizar estado de un vuelo | Sistema (automático) |
| CU-O48 *(añadido, fuera de fuente)* | Forzar/ajustar puntualmente un vuelo del catálogo (solo pruebas/demo) — vía EXCEPCIONAL | Administrador |

### Módulo: Reservas
| ID | Nombre | Actor |
|---|---|---|
| CU-O21 | Crear reserva (autoservicio) | Pasajero |
| CU-O22 | Crear reserva asistida | Agente |
| CU-O23 | Modificar reserva | Pasajero / Agente |
| CU-O24 | Cancelar reserva | Pasajero / Agente |
| CU-O25 | Consultar estado de una reserva | Pasajero |
| CU-O26 | Crear alerta de precio | Pasajero |

### Módulo: Disrupciones y Notificaciones
| ID | Nombre | Actor |
|---|---|---|
| CU-O27 | Consultar estado real de vuelo vía API externa | Sistema (automático) |
| CU-O28 | Monitorear bandeja de correo de aerolíneas | Sistema (automático) |
| CU-O29 | Detectar cambio de itinerario | Sistema (automático) |
| CU-O30 | Notificar al pasajero | Sistema (automático) |
| CU-O31 | Consultar historial de notificaciones | Pasajero / Agente |

### Módulo: Facturación
| ID | Nombre | Actor |
|---|---|---|
| CU-O32 | Procesar pago de reserva | Pasajero |
| CU-O33 | Emitir factura/recibo | Sistema (automático) |
| CU-O34 | Registrar comisión por reserva | Sistema (automático) |
| CU-O35 | Conciliar comisiones pendientes vs. cobradas | Administrador |
| CU-O36 | Generar remesa simulada a aerolínea | Sistema / Administrador |
| CU-O37 | Procesar reembolso | Sistema / Agente |
| CU-O38 | Consultar historial de pagos | Pasajero |
| CU-O39 | Descargar factura/recibo en PDF | Pasajero |
| CU-O40 | Descargar itinerario / e-ticket en PDF | Pasajero |

### Módulo: Transversal / Automatizaciones de Sistema
| ID | Nombre | Actor | Relación UML |
|---|---|---|---|
| CU-O41 | Registrar evento en auditoría | Sistema | `<<include>>` — incluido por prácticamente todo CU que crea/modifica/elimina |
| CU-O42 | Verificar sesión activa (token válido) | Sistema | `<<include>>` — incluido por todos excepto CU-O01/O03/O04/O07 |
| CU-O43 | Verificar permisos de acceso (RBAC) | Sistema | `<<include>>` — incluido por acciones de Agente/Administrador |
| CU-O44 | Expirar reserva pendiente de pago | Sistema (automático, temporizador) | Independiente — disparado por el paso del tiempo |
| CU-O45 | Verificar disponibilidad de vuelo/cupo | Sistema | `<<include>>` — incluido por CU-O21, O22, O23 |
| CU-O46 | Reintentar envío de notificación fallida | Sistema | `<<extend>>` de CU-O30 |
| CU-O47 | Cobrar/reembolsar diferencia de tarifa al modificar reserva | Sistema / Pasajero | `<<extend>>` de CU-O23 |

---

## 2. CU expandidos (formato Ivar Jacobson completo, tal como están en la fuente)

La fuente expande en formato completo (FB/FA/RN) un subconjunto representativo de los 47 CU. Los demás quedan documentados en tablas resumen (sección 1) hasta que se redacte su RF/RN en el spec del módulo correspondiente.

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
2. El sistema genera un enlace de un solo uso con expiración (tiempo configurable — CU-T14) y lo envía por correo.
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

**Nota sobre documentos:** para vuelos domésticos EE.UU. no se pide ni sube ningún documento — solo se declara el nombre y, opcionalmente, el número de identificación, sin verificación ni imágenes.

---

### CU-O17 — Buscar vuelos disponibles
**Actor principal:** Pasajero
**Precondiciones:** Existe catálogo de vuelos programables generado (CU-O19).
**Postcondiciones:** Se muestra una lista de vuelos que cumplen los criterios, ordenable y filtrable.

**Flujo básico:**
1. El pasajero ingresa origen, destino, fecha(s) y número de pasajeros en el buscador.
2. El sistema consulta el catálogo de vuelos programables filtrando por esos criterios.
3. El sistema muestra resultados con aerolínea, horario, duración, escalas, precio base y niveles de tarifa disponibles (Light/Standard/Flex).
4. El pasajero puede ordenar por precio, duración o escalas, y filtrar por aerolínea o rango horario.

**Flujos alternos:**
- 2.1 — No hay vuelos que cumplan los criterios: se muestra mensaje y sugerencia de fechas cercanas (cuando el nivel Táctico exista, reutilizará CU-T18).

---

### CU-O21 — Crear reserva (autoservicio)
**Actor principal:** Pasajero
**Precondiciones:** El pasajero está autenticado y seleccionó un vuelo (CU-O17/O18).
**Postcondiciones:** Se crea la reserva en estado "pendiente de pago"; se libera automáticamente si el pago no se completa a tiempo.

**Flujo básico:**
1. El pasajero selecciona el vuelo y el nivel de tarifa.
2. El sistema solicita datos de pasajero(s) si viajan varios, y extras opcionales.
3. El pasajero confirma y es dirigido al pago (CU-O32).
4. Tras el pago exitoso, el sistema confirma la reserva, y dispara la factura (CU-O33) y el registro de comisión esperada (CU-O34).

**Flujos alternos:**
- 3.1 — El pago falla o se abandona: la reserva queda "pendiente" con expiración automática (tiempo configurable — CU-T13).

---

### CU-O27 a CU-O30 — Flujo combinado de detección y notificación de disrupciones
**Actor principal:** Sistema (automático)
**Precondiciones:** Existen reservas confirmadas con vuelos asociados.
**Postcondiciones:** El pasajero recibe una notificación oportuna ante cualquier cambio relevante, sin importar cuál fuente lo detectó.

**Flujo básico:**
1. (CU-E01, previsto — ya implementado como DAG) Para reservas lejanas, se calcula la probabilidad de disrupción vía simulador estadístico.
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

### 3.1 Relaciones `<<include>>` / `<<extend>>` (tal como están documentadas en la fuente, sección 2.2)

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

### 3.2 Vista por CU transversal — quién lo incluye/extiende

| CU transversal | Incluido/extendido por | Naturaleza |
|---|---|---|
| CU-O41 (Registrar auditoría) | Prácticamente todo CU mutante: O08-O11, O21-O26, O32-O37, y en general cualquier creación/edición/eliminación de cualquier módulo | `<<include>>` obligatorio, universal |
| CU-O42 (Verificar sesión) | Todos excepto O01, O03, O04, O07 (los únicos que ocurren *antes* de tener sesión) | `<<include>>` obligatorio, universal |
| CU-O43 (Verificar RBAC) | O08, O16, O22, O35, O36, O37 (acciones de Agente/Administrador) | `<<include>>` obligatorio, acotado a roles internos |
| CU-O44 (Expirar reserva) | Ninguno lo incluye — se dispara por temporizador sobre CU-O21/O22 | Independiente, disparado por tiempo |
| CU-O45 (Verificar cupo) | O21, O22, O23 | `<<include>>` obligatorio, acotado a mutaciones de reserva |
| CU-O46 (Reintentar notificación) | Extiende a O30 | `<<extend>>` condicional (falla del primer envío) |
| CU-O47 (Diferencia de tarifa) | Extiende a O23 | `<<extend>>` condicional (cambio de precio) |

### 3.3 Dependencias entre los 6 módulos-spec operativos

Derivadas de las relaciones anteriores — determinan el orden de lectura/implementación sugerido:

| Módulo | Depende de | Por qué |
|---|---|---|
| **Seguridad** | (ninguno) | Base del sistema — todo lo demás depende de él (autenticación, RBAC, auditoría) |
| **Pasajeros** | Seguridad | El perfil de pasajero es 1:1 con `usuarios` (CU-O07 vive en Seguridad; historial/edición vive en Pasajeros) |
| **Vuelos** | Seguridad (RBAC de backoffice) | Generación/actualización de catálogo son procesos de sistema, pero su exposición en backoffice requiere permisos |
| **Reservas** | Seguridad, Pasajeros, Vuelos | Toda reserva requiere pasajero autenticado, un vuelo/tarifa válido y verificación de cupo (CU-O45) |
| **Disrupciones** | Vuelos, Reservas | Detecta cambios sobre vuelos del catálogo y notifica a pasajeros con reservas confirmadas sobre esos vuelos |
| **Facturación** | Reservas, Seguridad | Todo pago/factura/comisión nace de una reserva; conciliación y remesas son acciones de Administrador (RBAC) |

**Orden de lectura recomendado para las specs de módulo:** Seguridad → Pasajeros → Vuelos → Reservas → Disrupciones → Facturación (coincide con el orden pedido en el flujo de trabajo).

---

## 4. Asignación de los 47 CU a los 6 módulos-spec operativos

Los 40 CU del catálogo original ya vienen agrupados por módulo en la fuente (sección 1). Los 7 CU transversales (O41-O47) no tienen módulo-spec propio — se asignan al módulo-spec cuyo dominio de datos y flujo principal les corresponde, por ser el punto donde su RF debe redactarse en detalle. Esta asignación es una propuesta editorial (no está en la fuente) y queda abierta a ajuste en este checkpoint.

| CU | Módulo-spec destino | Justificación |
|---|---|---|
| CU-O01 – O13 | Seguridad (SEG) | Tal como está en el catálogo |
| CU-O14 – O16 | Pasajeros (PAS) | Tal como está en el catálogo |
| CU-O17 – O20 | Vuelos (VUE) | Tal como está en el catálogo |
| CU-O21 – O26 | Reservas (RES) | Tal como está en el catálogo |
| CU-O27 – O31 | Disrupciones (DIS) | Tal como está en el catálogo |
| CU-O32 – O40 | Facturación (FAC) | Tal como está en el catálogo |
| CU-O41 (Registrar auditoría) | **Seguridad (SEG)** | Dueño de la tabla `auditoria` y de CU-O12/O13 (ver/filtrar el mismo log) |
| CU-O42 (Verificar sesión activa) | **Seguridad (SEG)** | Dueño de `usuarios` y del mecanismo de token (CU-O01/O02) |
| CU-O43 (Verificar RBAC) | **Seguridad (SEG)** | Dueño de `roles`, `roles_permisos`, `roles_permisos_tablas` |
| CU-O44 (Expirar reserva pendiente) | **Reservas (RES)** | Opera exclusivamente sobre `reservas.estado`, extiende el ciclo de vida de CU-O21/O22 |
| CU-O45 (Verificar disponibilidad de vuelo/cupo) | **Vuelos (VUE) y Reservas (RES) — doble documentación** | Se invoca desde dos puntos con enfoque distinto en cada uno (ver detalle abajo) |
| CU-O46 (Reintentar notificación fallida) | **Disrupciones (DIS)** | Extiende directamente a CU-O30, mismo dominio de `notificaciones` |
| CU-O47 (Diferencia de tarifa) | **Reservas (RES) y Facturación (FAC) — doble documentación** | Se invoca desde dos puntos con enfoque distinto en cada uno (ver detalle abajo) |

**Decisión de este checkpoint (revisada):** CU-O41, O42 y O43 son servicios verdaderamente universales — su comportamiento no cambia según quién los invoca, así que se documentan una sola vez en Seguridad. CU-O45 y CU-O47, en cambio, se invocan desde dos puntos con un enfoque distinto en cada uno, así que se documentan en ambos módulos-spec con alcance diferenciado:

- **CU-O45 (Verificar disponibilidad de vuelo/cupo):**
  - En `vuelos-spec.md`: el **RF** del servicio de validación en sí — cómo se consulta y decrementa `tarifas_vuelo.cupos_disponibles`, quién es dueño del dato. Perspectiva de mecanismo/dato.
  - En `reservas-spec.md`: la **RN** de cómo CU-O21/O22/O23 invocan ese servicio como precondición y qué ocurre si falla (bloqueo de creación/modificación, condición de carrera — ver QP-08). Perspectiva de orquestación/negocio.
- **CU-O47 (Cobrar/reembolsar diferencia de tarifa):**
  - En `reservas-spec.md`: la **RN** de cuándo se dispara — extend condicional de CU-O23, solo si el vuelo nuevo tiene precio distinto al original. Perspectiva de negocio/disparador.
  - En `facturacion-spec.md`: el **RF** del mecanismo real de cobro/reembolso de la diferencia vía Stripe (`pagos`, `reembolsos`). Perspectiva de mecanismo/dato.

**Nota de implementación:** cada módulo-spec debe documentar los CU transversales que consume vía `<<include>>`/`<<extend>>` en su sección "Casos de uso relacionados", aunque el RF/RN detallado viva en el/los módulo(s)-spec destino de la tabla anterior. Por ejemplo, `reservas-spec.md` referenciará CU-O41/O42/O43 como incluidos (RF completo en `seguridad-spec.md`), y documentará su propia RN para O45 y O47 en paralelo al RF que vive en `vuelos-spec.md`/`facturacion-spec.md` respectivamente.

---

## 5. Escenarios "qué pasa si"

Escenarios de análisis derivados del catálogo existente y de los principios A-J de `constitution.md`. No introducen CU nuevos: cada escenario referencia el/los CU y principio(s) que lo resuelven, para que el spec del módulo correspondiente lo convierta en flujo alterno o regla de negocio explícita.

| # | Escenario | CU / RN involucrados | Principio constitucional | Resolución esperada |
|---|---|---|---|---|
| QP-01 | La API de estado de vuelo real (AviationStack/AeroDataBox) no responde o se agota la cuota | CU-O27 | E3 — Degradación ordenada | El sistema sigue operando con el simulador estadístico como respaldo; nunca falla silenciosamente, se registra el evento de degradación |
| QP-02 | Dos fuentes (API real y monitor de correo) detectan el mismo cambio de itinerario casi al mismo tiempo | CU-O27, O28, O29, O30 | E2 — Precedencia y deduplicación | Se aplica una regla de precedencia entre fuentes y se notifica una sola vez al pasajero por el mismo cambio |
| QP-03 | Falla la inserción del registro de auditoría tras una mutación ya ejecutada | CU-O41 (flujo alterno 3.1) | B4 — Auditoría inmutable y universal | La acción original no se revierte, pero se alerta al Administrador; el fallo de auditoría es en sí mismo un evento crítico |
| QP-04 | Stripe confirma el pago justo cuando la reserva ya expiró por temporizador (condición de carrera) | CU-O32, O44 | D1 — Idempotencia obligatoria | El sistema debe resolver el conflicto de forma determinista y verificable (p. ej. honrar el pago y re-confirmar la reserva, o revertir el cobro) — a definir como RN explícita en `reservas-spec.md`/`facturacion-spec.md`, nunca dejarlo implícito |
| QP-05 | Un Agente intenta una acción sobre una tabla fuera de su restricción de Nivel 2 (RBAC) | CU-O43 | B1 — RBAC de dos niveles obligatorio | La acción se bloquea antes de tocar datos; el bloqueo se comunica visualmente (J6), no como ausencia silenciosa de datos |
| QP-06 | Se intenta cancelar una reserva de un vuelo ya marcado "completado" por CU-O20 | CU-O24 (flujo alterno agregado, sección 2.2) | — | El sistema bloquea la cancelación con "No es posible cancelar un vuelo ya realizado" |
| QP-07 | Llega un correo de disrupción que no corresponde a ninguna reserva activa (falso positivo o vuelo no reconocido) | CU-O28, O29 | F3 — Aislamiento de fallos de terceros | El aviso se descarta o se marca para revisión manual sin generar notificación errónea al pasajero ni interrumpir el resto del monitoreo |
| QP-08 | El precio de la tarifa cambia mientras el pasajero está en checkout (condición de carrera sobre el último cupo) | CU-O21, O22, O45 | G2 — Transparencia de precio | El sistema revalida precio/cupo antes de confirmar el pago; si cambió, se informa explícitamente al pasajero antes de cobrar, nunca se cobra un monto distinto al mostrado |
| QP-09 | El reintento de notificación (CU-O46) también falla | CU-O30, O46 | F2 — Timeouts y reintentos configurables | Tras agotar los reintentos configurados, el sistema debe dejar constancia del fallo definitivo (no reintentar indefinidamente) y hacerlo visible para el Agente/Administrador |
| QP-10 | Se intenta eliminar un rol que tiene usuarios activos asignados | CU-O11 | — (integridad referencial) | El sistema bloquea la eliminación o exige reasignar primero a los usuarios afectados — a definir como RN explícita en `seguridad-spec.md` |
| QP-11 | El token de sesión expira a mitad de un flujo multi-paso (checkout de reserva) | CU-O42, J10 | J10 — Navegación sin pérdida de estado | Se solicita reautenticación sin descartar los datos ya ingresados en pasos previos del flujo |
| QP-12 | Una disrupción notificada es una cancelación, pero la tarifa comprada no da derecho a reembolso | CU-O30 → O37 (extend condicional) | C3 — Transparencia en cancelaciones y reembolsos | CU-O37 no se dispara; el pasajero puede consultar la política aplicada de forma explícita, nunca una resolución discrecional u oculta |
| QP-13 | El pasajero solicita eliminar sus datos personales mientras tiene una reserva activa o pendiente de pago | CU-O05, O15 | C2 — Propósito declarado y derecho de eliminación | La eliminación se resuelve respetando la retención mínima necesaria para reservas/pagos en curso — a definir como RN explícita en `seguridad-spec.md`/`pasajeros-spec.md` |

---

## 6. Matriz técnica

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
| CU-O13 | Filtrar y exportar log de auditoría | Admin | Interactivo | Seguridad | SEG | include→O42 | `auditoria` |
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
| CU-O26 | Crear alerta de precio | Pasajero | Interactivo | Reservas | RES | include→O41,O42 | `alertas_precio` |
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

---

## 7. Puntos abiertos — resolución tras revisión

1. **Resuelto.** Asignación de módulo de los 7 CU transversales: CU-O41/O42/O43 quedan solo en Seguridad (servicios universales, sin variación de enfoque). CU-O45 y CU-O47 se documentan en **dos** módulos-spec cada uno, con enfoque distinto (RF de mecanismo/dato en un lado, RN de orquestación/negocio en el otro) — ver detalle en sección 4.
2. **Resuelto (a redactar en su momento).** QP-04 y QP-08 (condiciones de carrera de pago/cupo) no tienen RN explícita en la fuente — se redactarán como reglas de negocio nuevas al escribir `reservas-spec.md`/`facturacion-spec.md`.
3. **Resuelto (a redactar en su momento).** QP-10 (eliminar rol con usuarios asignados) se redactará como RN nueva en `seguridad-spec.md`; QP-13 (derecho de eliminación de datos personales con reserva activa) se redactará como RN nueva en `seguridad-spec.md`/`pasajeros-spec.md`.

Con este documento aprobado, el siguiente paso es generar el resto de `000-sistema-general/` (spec.md, glosario, reglas, consideraciones, errores-conocidos).
