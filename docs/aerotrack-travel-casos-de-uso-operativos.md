# AeroTrack Travel — Casos de Uso, Módulos y Departamentos

> Base para el proyecto en Claude Code. **v2 — corregida y renumerada.** La v1 mezclaba niveles (varios CU marcados "operativo" en realidad eran de configuración, consulta agregada o predicción). Aquí se separan por su naturaleza real, siguiendo el mismo criterio que ya usaste en el proyecto anterior (Operativo = CRUD/transacciones/estados; Táctico = consultas, monitoreo, configuración; Estratégico = análisis, predicción, reportes). **No se pierde ningún CU** — los que no son operativos quedan documentados aquí mismo como "previstos", sin crear specs de esos niveles todavía.

---

## 0. Formato de caso de uso utilizado

Formato estándar Ivar Jacobson/UML (Craig Larman, usecases.org):

- **Nombre**: verbo en infinitivo + objeto
- **Actor principal**
- **Precondiciones** / **Postcondiciones**
- **Flujo básico (FB)**: pasos numerados, camino feliz
- **Flujos alternos (FA)**: numerados X.Y (X = paso del FB, Y = consecutivo)
- **Reglas de negocio**: RN-XXX asociadas

Se expanden con este formato completo los CU más complejos o novedosos; el resto queda en tablas resumen (ID, nombre, actor, módulo).

---

## 1. Departamentos y módulos del sistema (visión completa)

> Nota: solo el **Nivel Operativo** se desarrolla ahora (specs + implementación). Táctico y Estratégico quedan documentados como alcance previsto — no se crean carpetas `specs/tactico/` ni `specs/estrategico/` todavía.

| Departamento | Módulo | Contenido | Nivel | Estado |
|---|---|---|---|---|
| Tecnología y Sistemas (TI) | Seguridad | Usuarios · Roles · Auditoría | Operativo | ✅ Esta entrega |
| Tecnología y Sistemas (TI) | Seguridad | Permisos (módulo + tabla), matriz de permisos | Táctico | 📋 Previsto |
| Tecnología y Sistemas (TI) | Configuración | Panel general, todas las credenciales/parámetros/umbrales/plantillas | Táctico | 📋 Previsto |
| Tecnología y Sistemas (TI) | Configuración → Limpieza de datos | Mantenimiento de registros | Táctico | 📋 Previsto |
| *(Toda cuenta autenticada)* | Mi cuenta / Mi perfil | Ver/editar perfil, cambiar contraseña | Operativo | ✅ Esta entrega |
| Ventas y Reservas | Pasajeros | Registro, historial, gestión backoffice | Operativo | ✅ Esta entrega |
| Ventas y Reservas | Vuelos (catálogo) | Búsqueda, detalle, generación y actualización de estado | Operativo | ✅ Esta entrega |
| Ventas y Reservas | Vuelos (catálogo) | Tendencia histórica de precio/puntualidad (lee `agg_*`) | Táctico | 📋 Previsto |
| Ventas y Reservas | Reservas | Autoservicio, asistida, modificación, cancelación, alertas | Operativo | ✅ Esta entrega |
| Operaciones | Disrupciones y Notificaciones | API real, monitor de correo, detección, notificación, historial | Operativo | ✅ Esta entrega |
| Operaciones | Disrupciones y Notificaciones | Simulador estadístico de riesgo (predicción sobre `agg_*`) | Estratégico | 📋 Previsto (ya implementado como DAG — ver nota) |
| Operaciones | Disrupciones y Notificaciones | Medir efectividad de notificación (KPI) | Estratégico | 📋 Previsto |
| Finanzas | Facturación | Pagos, comisiones, remesas, reembolsos, facturas (con descarga) | Operativo | ✅ Esta entrega |
| Finanzas | Configuración de aerolíneas/comisiones pactadas | — | Táctico | 📋 Previsto |
| Finanzas | Dashboard Financiero | KPIs de ingresos, comisiones pendientes vs. cobradas | Estratégico | 📋 Alcance futuro (sin CU redactados aún) |
| Comercial y Marketing *(reservado)* | Fidelización, Socios API, Dashboard Comercial | — | — | 📋 Alcance futuro (sin CU redactados aún) |
| Ingeniería y Analítica de Datos *(reservado)* | Pipeline ELT, Modelo Dimensional (solo lectura), Predictivo, Asistente IA | — | — | 📋 Alcance futuro (sin CU redactados aún) |

> **Nota sobre el simulador de riesgo:** técnicamente ya existe como DAG de Airflow funcionando (implementado durante la fase de infraestructura, antes de esta reclasificación). Se documenta aquí como Estratégico por su naturaleza (predicción sobre agregados históricos), coherente con cómo clasificaste el módulo Predictivo en el proyecto anterior. Cuando se redacte el spec de nivel Estratégico, este DAG ya construido sirve como base técnica — no habrá que rehacerlo, solo formalizarlo en spec.

---

## 2. Catálogo — NIVEL OPERATIVO (esta entrega, renumerado 1–40)

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

### Módulo: Transversal / Automatizaciones de Sistema (nuevo — CU identificados como huecos)
| ID | Nombre | Actor | Relación UML |
|---|---|---|---|
| CU-O41 | Registrar evento en auditoría | Sistema | `<<include>>` — incluido por prácticamente todo CU que crea/modifica/elimina (ver sección 2.2) |
| CU-O42 | Verificar sesión activa (token válido) | Sistema | `<<include>>` — incluido por todos excepto CU-O01/O03/O04/O07 |
| CU-O43 | Verificar permisos de acceso (RBAC) | Sistema | `<<include>>` — incluido por acciones de Agente/Administrador |
| CU-O44 | Expirar reserva pendiente de pago | Sistema (automático, temporizador) | Independiente — disparado por el paso del tiempo, no por un actor |
| CU-O45 | Verificar disponibilidad de vuelo/cupo | Sistema | `<<include>>` — incluido por CU-O21, O22, O23 |
| CU-O46 | Reintentar envío de notificación fallida | Sistema | `<<extend>>` de CU-O30 — condicional, solo si el primer envío falla |
| CU-O47 | Cobrar/reembolsar diferencia de tarifa al modificar reserva | Sistema / Pasajero | `<<extend>>` de CU-O23 — condicional, solo si cambia el precio |

**Total nivel Operativo: 47 CU** (40 + 7 identificados como huecos vía análisis include/extend — ver sección 2.2).

---

## 2.2 Relaciones entre casos de uso (`<<include>>` / `<<extend>>`)

> Semántica UML: en `<<include>>` la flecha apunta *hacia* el CU incluido (relación obligatoria — el CU base nunca se completa sin él, sirve para factorizar comportamiento común). En `<<extend>>` la flecha apunta *hacia* el CU base (relación opcional/condicional, ocurre solo en un punto de extensión bajo cierta condición).

### Relaciones ya presentes en el catálogo original

| CU origen | Relación | CU destino | Condición / motivo |
|---|---|---|---|
| CU-O21/O22 (Crear reserva) | `<<include>>` | CU-O32 (Procesar pago) | Toda reserva requiere pago para confirmarse |
| CU-O32 (Procesar pago) | `<<include>>` | CU-O33 (Emitir factura) | Todo pago exitoso genera factura |
| CU-O32 (Procesar pago) | `<<include>>` | CU-O34 (Registrar comisión) | Todo pago exitoso registra comisión esperada |
| CU-O29 (Detectar cambio de itinerario) | `<<include>>` | CU-O30 (Notificar al pasajero) | Constitución E1: ninguna disrupción queda sin notificar |
| CU-O24 (Cancelar reserva) | `<<extend>>` | CU-O37 (Procesar reembolso) | Solo si la política de la tarifa comprada lo permite |
| CU-O30 (Notificar al pasajero) | `<<extend>>` | CU-O37 (Procesar reembolso) | Solo si la disrupción notificada es una cancelación |

### Relaciones de los CU nuevos (sección de Transversal)

| CU origen | Relación | CU destino | Condición / motivo |
|---|---|---|---|
| CU-O08, O09, O10, O11, O21-O26, O32-O37 (y en general todo CU que cree/modifique/elimine) | `<<include>>` | CU-O41 (Registrar evento en auditoría) | Constitución B4: toda mutación se audita, sin excepción |
| Todos excepto O01, O03, O04, O07 | `<<include>>` | CU-O42 (Verificar sesión activa) | Ninguna acción autenticada procede con token inválido/expirado |
| CU-O08, O16, O22, O35, O36, O37 | `<<include>>` | CU-O43 (Verificar permisos de acceso) | Acciones de Agente/Administrador siempre pasan por la matriz RBAC |
| CU-O21, O22, O23 | `<<include>>` | CU-O45 (Verificar disponibilidad de vuelo/cupo) | Evita condición de carrera sobre el último cupo simulado |
| CU-O30 (Notificar al pasajero) | `<<extend>>` | CU-O46 (Reintentar envío de notificación fallida) | Solo si el primer intento de envío falla (constitución F3) |
| CU-O23 (Modificar reserva) | `<<extend>>` | CU-O47 (Cobrar/reembolsar diferencia de tarifa) | Solo si el vuelo nuevo tiene precio distinto al original |

### Flujo alterno agregado (no requiere CU aparte)
- **CU-O24 (Cancelar reserva):** flujo alterno nuevo — si el vuelo ya fue marcado "completado" por CU-O20, el sistema bloquea la cancelación con "No es posible cancelar un vuelo ya realizado."

---

## 3. Catálogo — NIVEL TÁCTICO (previsto, no se desarrolla aún — sin spec, sin carpeta)

### Módulo: Seguridad → Permisos
| ID (previsto) | Nombre | Actor |
|---|---|---|
| CU-T01 | Asignar permisos de módulo a un rol | Administrador |
| CU-T02 | Restringir permisos a tablas específicas dentro de un módulo | Administrador |
| CU-T03 | Ver matriz de permisos (módulo × rol × tabla) | Administrador |

### Módulo: Configuración
| ID (previsto) | Nombre | Actor |
|---|---|---|
| CU-T04 | Ver panel de configuración | Administrador |
| CU-T05 | Configurar servicio de correo (SMTP) | Administrador |
| CU-T06 | Configurar credenciales de API de estado de vuelo | Administrador |
| CU-T07 | Configurar credenciales de Gmail API | Administrador |
| CU-T08 | Configurar credenciales de pasarela de pago (Stripe test mode) | Administrador |
| CU-T09 | Configurar reglas de tarifas de servicio y comisiones | Administrador |
| CU-T10 | Configurar políticas de reembolso por nivel de tarifa | Administrador |
| CU-T11 | Configurar umbrales del simulador de disrupciones | Administrador |
| CU-T12 | Gestionar catálogo de aerolíneas y comisión pactada | Administrador |
| CU-T13 | Configurar tiempo de expiración de reserva pendiente de pago | Administrador |
| CU-T14 | Configurar tiempo de expiración de enlace de recuperación de contraseña | Administrador |
| CU-T15 | Configurar parámetros del pipeline ELT heredado | Administrador |
| CU-T16 | Configurar plantilla de factura/recibo | Administrador |
| CU-T17 | Configurar canales de notificación activos | Administrador |

### Módulo: Vuelos (catálogo)
| ID (previsto) | Nombre | Actor |
|---|---|---|
| CU-T18 | Consultar tendencia histórica de precio/puntualidad por ruta | Pasajero |

**Total nivel Táctico previsto: 18 CU.**

---

## 4. Catálogo — NIVEL ESTRATÉGICO (previsto, no se desarrolla aún — sin spec, sin carpeta)

### Módulo: Disrupciones y Notificaciones
| ID (previsto) | Nombre | Actor |
|---|---|---|
| CU-E01 | Estimar riesgo de disrupción (simulador estadístico) | Sistema (automático) — **ya implementado como DAG, ver nota sección 1** |
| CU-E02 | Medir efectividad de notificación (KPI) | Administrador |

**Total nivel Estratégico previsto: 2 CU** (se ampliará cuando se aborden Predictivo y Asistente IA).

---

## 5. CU expandidos (formato completo) — nivel Operativo únicamente

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

## 6. Notas de cierre

- **Corrección de esta v2:** los CU que antes vivían bajo "Configuración" (incluyendo permisos de tabla) pasaron a Táctico; el simulador estadístico y la medición de efectividad pasaron a Estratégico — siguiendo tu propio criterio del proyecto anterior (AUD sí era operativo; CFG y análisis sobre `agg_*` no lo eran). Ningún CU se eliminó, solo se reubicó y renumeró.
- **Por qué "descargar factura" sigue siendo operativo:** es una acción rutinaria de uso diario (ver/exportar un documento ya generado), no una configuración — sería táctico solo si habláramos de configurar la *plantilla* (CU-T16).
- **El simulador de riesgo (CU-E01)** ya está implementado técnicamente (DAG activo). La reclasificación es documental, no implica deshacer nada — cuando se redacte el spec Estratégico, se documenta sobre lo ya construido.
- El mecanismo de permisos por tabla (CU-T02) sigue siendo el ajuste más delicado del catálogo — se retoma cuando se aborde el nivel Táctico.
- El catálogo de vuelos (CU-O19) reutiliza `dim_aeropuerto` (AirportCode, CityName, State) para mostrar origen/destino legible.
- **v2.1 — análisis include/extend:** se revisaron los 40 CU operativos contra la semántica UML de `<<include>>`/`<<extend>>`, documentando 6 relaciones ya presentes (sección 2.2) y agregando 7 CU nuevos que existían como comportamiento implícito sin CU propio (CU-O41 a CU-O47, módulo Transversal). El total operativo queda en **47 CU**. Ninguno de los niveles Táctico/Estratégico se tocó en esta pasada — se revisarán de la misma forma cuando se aborden.
