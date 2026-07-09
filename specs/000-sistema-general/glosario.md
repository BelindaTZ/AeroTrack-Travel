# Glosario — AeroTrack Travel (Nivel Operativo)

**Fuentes:** `docs/aerotrack-travel-documento-empresarial.md`, `docs/aerotrack-travel-casos-de-uso-operativos.md`, `docs/aerotrack-travel-propuesta-tablas.dbml`, `.specify/memory/constitution.md`.

Términos de dominio y técnicos usados de forma consistente en todas las specs de módulo. Cuando un término tiene un nombre de tabla asociado en el esquema propuesto, se indica entre paréntesis.

---

## Organización y niveles

- **AeroTrack Travel** — Agencia de viajes digital minorista con sede en Miami, FL, especializada en venta y gestión de boletos aéreos domésticos en EE. UU.
- **Nivel Operativo** — Registro diario del negocio: reservas, pasajeros, vuelos, notificaciones, pagos. Único nivel que se especifica e implementa en esta entrega.
- **Nivel Táctico** — Configuración de reglas de negocio, roles, parámetros, permisos por tabla. Documentado como alcance previsto (catálogo CU-T), sin spec ni carpeta todavía.
- **Nivel Estratégico** — Metas de negocio, predicción, medición de efectividad. Documentado como alcance previsto (catálogo CU-E), sin spec ni carpeta todavía.
- **Departamento** — Agrupación organizacional (Ventas y Reservas, Operaciones, Finanzas, Tecnología y Sistemas, y los reservados Comercial/Marketing e Ingeniería y Analítica de Datos).
- **Módulo** — Subdivisión funcional dentro de un departamento (p. ej. Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación); es la unidad que corresponde a un `{modulo}-spec.md`.

## Seguridad, RBAC y auditoría

- **RBAC de dos niveles** — Modelo de control de acceso con dos capas: Nivel 1 decide si un rol puede actuar sobre un módulo (`roles_permisos`); Nivel 2 restringe, nunca amplía, ese acceso a tablas específicas dentro del módulo ya autorizado (`roles_permisos_tablas`).
- **Rol** (`roles`) — Conjunto de permisos con nombre (p. ej. Administrador, Agente); puede marcarse como protegido (`es_sistema`) para impedir su eliminación.
- **Permiso** (`permisos`) — Combinación de módulo + acción (ver, crear, editar, eliminar, exportar, ejecutar) que puede otorgarse a un rol.
- **Actor** — Tipo de usuario del sistema: Pasajero, Agente, Administrador, o Sistema (procesos automáticos).
- **Auditoría** (`auditoria`) — Log inmutable, de solo inserción, de toda acción de creación/modificación/eliminación en cualquier módulo. Nunca se edita ni se borra (constitución B4).
- **Token de sesión** — Credencial emitida al iniciar sesión que identifica a un usuario autenticado en solicitudes subsecuentes; su verificación es CU-O42.
- **Sesión activa** — Estado de un usuario autenticado con un token válido y no expirado.

## Pasajeros

- **Pasajero** (`pasajeros`) — Perfil extendido del cliente final, 1:1 con `usuarios`; incluye fecha de nacimiento, teléfono, documento de identidad (declarado, no verificado), dirección de facturación y contacto de emergencia.
- **Backoffice** — Interfaz de uso interno (Agente/Administrador) para gestionar pasajeros, reservas y otros datos operativos, distinta del portal del pasajero.

## Vuelos y tarifas

- **Vuelo programable / catálogo de vuelos** (`vuelos_catalogo`) — Registro de un vuelo concreto (número, aerolínea, origen, destino, fecha, horarios, estado) disponible para búsqueda y reserva.
- **Nivel de tarifa** (`niveles_tarifa`) — Categoría de tarifa por vuelo, inspirada en KLM: **Light**, **Standard**, **Flex**, cada una con distinta política de equipaje, cambios y reembolso.
- **Cupo** (`tarifas_vuelo.cupos_disponibles`) — Número de asientos disponibles para un nivel de tarifa de un vuelo concreto; su verificación (CU-O45) evita sobreventa.
- **Aerolínea** (`aerolineas`) — Catálogo operativo de proveedores con comisión pactada, distinto de `dim_aerolinea` (heredado, histórico, solo lectura).
- **Política de reembolso** (`politicas_reembolso`) — Condiciones, porcentaje y ventana de horas antes del vuelo bajo las cuales aplica un reembolso, asociada a un nivel de tarifa.

## Reservas

- **Reserva** (`reservas`) — Registro de compra de uno o más pasajeros sobre un vuelo/tarifa concreto, identificado por su **PNR** (`codigo_reserva`).
- **PNR** — Passenger Name Record; código único que identifica una reserva.
- **Canal de reserva** — `autoservicio` (el pasajero reserva directamente) o `asistida` (un Agente reserva en su nombre).
- **Estado de reserva** — `pendiente_pago`, `confirmada`, `modificada`, `cancelada`, `completada`.
- **Extras** (`reserva_extras`) — Servicios opcionales añadidos a una reserva: equipaje, asiento, seguro.
- **Alerta de precio** (`alertas_precio`) — Suscripción de un pasajero a un umbral de precio para una ruta/fecha, no atada a una reserva existente.

## Disrupciones y notificaciones

- **Disrupción** (`disrupciones`) — Cambio detectado en un vuelo (retraso, cancelación, cambio de horario, cambio de puerta, desvío).
- **Fuente de detección** — Origen del dato que detecta una disrupción: `simulador_estadistico` (histórico BTS/FAA, nivel Estratégico), `api_real` (API de estado de vuelo), `monitor_correo` (Gmail API sobre la bandeja de la agencia).
- **Notificación** (`notificaciones`) — Aviso enviado al pasajero (canal email o SMS) sobre una disrupción u otro evento relevante de su reserva.
- **Degradación ordenada** — Comportamiento del sistema cuando una fuente de datos en tiempo real no está disponible: continúa operando con la fuente estadística como respaldo, nunca falla silenciosamente (constitución E3).

## Facturación

- **Cargo de servicio** — Monto que AeroTrack Travel cobra directamente al pasajero al momento de la reserva (ingreso inmediato).
- **Comisión** (`comisiones`) — Monto pactado con la aerolínea, registrado como `pendiente_cobro` al vender y marcado `cobrada` semanas después (ingreso diferido, simula el retraso real del sector).
- **Remesa** (`remesas`) — Registro contable simulado del neto de boletos que la agencia "remite" a la aerolínea, agrupando comisiones (`remesa_comisiones`) por periodo; no hay integración BSP/ARC real.
- **Reembolso** (`reembolsos`) — Devolución de dinero al pasajero, disparada automáticamente ante disrupción grave o cancelación, según la política de la tarifa comprada; procesado vía Stripe test mode.
- **Factura/recibo** (`facturas`) — Documento descargable (PDF) emitido tras un pago exitoso.
- **Stripe test mode** — Modo de prueba de la pasarela de pago Stripe: replica la mecánica real (autorización, captura, reembolso) sin mover dinero real ni requerir certificación.
- **Money-in / Money-out** — Money-in: lo que el pasajero paga (precio base + cargo de servicio). Money-out: lo que la agencia remite a la aerolínea reteniendo su cargo de servicio.

## Datos heredados e integraciones externas

- **Modelo dimensional heredado** — Esquema Kimball (`fact_vuelo` + `dim_*` + `agg_*`) del proyecto anterior (AeroTrack Analytics), almacenado en Parquet sobre MinIO, siempre de solo lectura (constitución A1/A2).
- **SOFT-REF** — Campo de texto simple (no relation field de PocketBase) que referencia un valor del modelo dimensional heredado, resuelto en la capa de aplicación (p. ej. `vuelos_catalogo.origen_codigo` → `dim_aeropuerto.AirportCode`).
- **BTS / FAA** — Bureau of Transportation Statistics y Federal Aviation Administration; fuentes de los datos históricos que sustentan el modelo dimensional heredado y el simulador estadístico (nivel Estratégico).
- **PocketBase** — Motor de base de datos/backend operacional transaccional donde viven todas las tablas nuevas de este proyecto (`pocketbase-travel`), separado de MinIO.
- **Gmail API (OAuth)** — Integración que monitorea automáticamente la bandeja de correo de la agencia para detectar y parsear avisos reales de cambio/cancelación enviados por la aerolínea (CU-O28).
- **API de estado de vuelo** — Servicio externo (AviationStack, FlightAware AeroAPI o AeroDataBox) que entrega el estado real y actual de un vuelo específico (CU-O27).
- **IATA / NDC / BSP / ARC** — Estándares y mecanismos de certificación formal de la industria aérea, explícitamente fuera de alcance de este proyecto (ver `consideraciones.md`).

## Documentación técnica (convenciones usadas en las specs)

- **CU-O / CU-T / CU-E** — Caso de uso Operativo / Táctico / Estratégico, numerado según el catálogo de `docs/aerotrack-travel-casos-de-uso-operativos.md`.
- **`<<include>>`** — Relación UML obligatoria: el caso de uso base nunca se completa sin ejecutar el caso de uso incluido.
- **`<<extend>>`** — Relación UML opcional/condicional: el caso de uso base se completa normalmente, y el caso de uso que extiende solo ocurre bajo una condición específica.
- **RF-{PREF}-NNN** — Requisito Funcional de un módulo (p. ej. `RF-SEG-001`).
- **RNF-{PREF}-NNN** — Requisito No Funcional de un módulo.
- **RN-{PREF}-NNN** — Regla de Negocio de un módulo.
- **HU-{PREF}-NN** — Historia de Usuario de un módulo.
- **QP-NN** — Escenario "qué pasa si" documentado en `analisis-cus-completo.md`.
