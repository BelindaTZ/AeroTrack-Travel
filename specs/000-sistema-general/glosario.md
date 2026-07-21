# Glosario — AeroTrack Travel (Niveles Operativo y Táctico)

**Fuentes:** `docs/aerotrack-travel-documento-empresarial.md`, `docs/aerotrack-travel-casos-de-uso-v3.md` (catálogo v3.1, 165 CU / 17 módulos), `docs/aerotrack-travel-propuesta-tablas-v3.dbml`, `docs/fuentes-datos-por-tabla.md`, `.specify/memory/constitution.md`.

Términos de dominio y técnicos usados de forma consistente en todas las specs de módulo. Cuando un término tiene un nombre de tabla asociado en el esquema propuesto, se indica entre paréntesis.

> **Nota (2026-07-18):** este glosario cubría originalmente solo los 6 módulos del catálogo v1/v2 (48 CU-O, un único nivel Operativo). Se amplía para cubrir los 17 módulos del catálogo v3.1 — la sección "Organización y niveles" se actualiza, y se agregan secciones nuevas por módulo (Integraciones, Hoteles, Autos, Actividades, Cruceros, Paquetes, Carrito, Cuenta/Mis Viajes, Centro de Ayuda, Ofertas y Promociones, Asistente IA) sin tocar lo ya definido para los módulos originales.

---

## Organización y niveles

- **AeroTrack Travel** — Agencia de viajes digital minorista con sede en Miami, FL, con alcance internacional, especializada en venta y gestión de seis verticales de producto: vuelos, hoteles, autos de renta, actividades, cruceros y paquetes combinados.
- **Nivel Operativo** — Registro diario del negocio: búsqueda/reserva de cualquier vertical de producto, pasajeros, notificaciones, pagos. 122 CU-O en 16 módulos-spec, todos en alcance de esta entrega.
- **Nivel Táctico** — Configuración de reglas de negocio, roles, parámetros, permisos por tabla, reportes operativos. 43 CU-T en 17 módulos-spec (todos los del nivel Operativo más Integraciones, que es 100% táctico) — su catálogo ya está redactado y sus carpetas creadas bajo `specs/tactico/`; el `spec.md` de cada módulo se redacta progresivamente.
- **Nivel Estratégico** — Metas de negocio, predicción, medición de efectividad. Sigue siendo alcance previsto (catálogo CU-E), sin spec ni carpeta todavía — el único de los tres niveles que no está en esta entrega.
- **Departamento** — Agrupación organizacional de los 17 módulos: Tecnología y Sistemas (Seguridad, Integraciones), Gestión de Clientes (Pasajeros, Cuenta/Mis Viajes), Ventas y Reservas (Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes, Reservas, Carrito), Operaciones (Disrupciones, Centro de Ayuda), Finanzas (Facturación), Comercial y Marketing (Ofertas y Promociones, Asistente IA). El catálogo v1/v2 reservaba un 7º departamento, "Ingeniería y Analítica de Datos", que no sobrevivió a la reorganización v3.
- **Módulo** — Subdivisión funcional dentro de un departamento (p. ej. Seguridad, Vuelos, Hoteles, Reservas); es la unidad que corresponde a **dos** carpetas de spec, una por nivel: `specs/operativo/{modulo}/spec.md` y `specs/tactico/{modulo}/spec.md` — nunca CU-O y CU-T mezclados en el mismo archivo.
- **Vertical de producto** — Cada uno de los seis tipos de ítem que un pasajero puede buscar y reservar: Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes (combinación de las anteriores). Todas comparten el flujo de Carrito → Reservas → Facturación; solo Vuelos tiene monitoreo de Disrupciones.

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

## Integraciones *(módulo nuevo v3.1)*

- **Fuente de datos externa** (`fuentes_datos_externas`) — Registro de cada API/proceso externo que alimenta un catálogo (AeroDataBox, HotelLens, Global Rental Cars, Travel Advisor, Cruise Pricing, ExchangeRate-API, etc.), con su frecuencia de sincronización configurable y estado activo/inactivo.
- **Sincronización** (`sincronizaciones_log`) — Registro de cada corrida de un job de catálogo (éxito/fallo/parcial, registros procesados, cuota consumida). Generaliza a las 5 verticales de producto lo que CU-T06/T07 ya resolvían solo para Vuelos, sin reemplazarlos.
- **Rotación de cuota** — Estrategia de consumo de una API externa con límite mensual/diario (ej. 3 hubs/día en AeroDataBox) para no agotar la cuota antes de fin de periodo; documentada por fuente en `docs/fuentes-datos-por-tabla.md`.
- **Disponibilidad sintética** — Cupo/horario generado por regla de negocio propia (`configuracion_sistema.disponibilidad_*`) cuando ninguna API real expone inventario — usado en Actividades (horarios) y Cruceros (camarotes), confirmado como gap real tras pruebas en vivo, no una simplificación arbitraria.

## Hoteles, Autos, Actividades, Cruceros *(módulos nuevos v3.0)*

- **Catálogo de hotel/auto/actividad/crucero** (`hoteles_catalogo`, `autos_catalogo`, `actividades_catalogo`, `cruceros_catalogo`) — Registro de un ítem de esa vertical disponible para búsqueda y reserva, generado por proceso automático programado (mismo patrón que `vuelos_catalogo`/CU-O19).
- **Camarote** (`cruceros_camarotes_tarifa`) — Tipo de alojamiento a bordo de un crucero, con tarifa y disponibilidad (sintética — ver arriba).
- **Cargos locales de destino** (`cargos_locales_destino`) — Impuestos municipales/tasas que se cobran en destino, no incluidos en la tarifa mostrada; propios de Hoteles.
- **Proveedor comercial** (`proveedores_comerciales`) — Tercero (aerolínea, cadena hotelera, rentadora, operador de actividad/crucero) con el que AeroTrack Travel tiene comisión pactada; generaliza el concepto de `aerolineas` a las demás verticales.

## Paquetes *(módulo nuevo v3.0)*

- **Paquete** — Combinación de componentes de al menos dos verticales (vuelo + hotel obligatorio; auto/actividad opcional), con descuento sobre la suma de reservar cada componente por separado.
- **Tipo de paquete** (`tipos_paquete_descuento`) — Categoría de combinación (vuelo+hotel, vuelo+hotel+auto, etc.) con su porcentaje de descuento configurable a nivel Táctico.

## Carrito *(módulo nuevo v3.0)*

- **Carrito** (`carritos`, `carrito_items`) — Colección temporal de ítems de cualquier vertical (vuelo, hotel, auto, actividad o crucero) que un pasajero acumula antes de proceder al checkout; el checkout desde el carrito incluye `<<include>>` a Reservas (CU-O21/O22).

## Cuenta / Mis Viajes *(módulo nuevo v3.0)*

- **Favorito** (`favoritos`) — Destino, hotel o actividad guardado por el pasajero para consulta posterior, sin implicar una reserva.
- **Viaje personalizado** (`viajes_personalizados`) — Agrupación libre (nombre + descripción) creada por el pasajero para planificar, sin atarse a una reserva concreta.
- **Programa de beneficios** (`programa_beneficios_niveles`, `programa_beneficios_movimientos`) — Programa de puntos con niveles y reglas de acumulación configurables a nivel Táctico (CU-T24).
- **Alerta de precio** (`alertas_precio`) — Sucesora de CU-O26 (eliminado del catálogo, ver `docs/aerotrack-travel-casos-de-uso-v3.md`); vive en Cuenta/Mis Viajes en vez de Reservas porque conceptualmente es gestión de cuenta, no proceso de reserva.

## Centro de Ayuda *(módulo nuevo v3.0)*

- **Artículo de ayuda** (`articulos_ayuda`, `articulo_calificaciones`) — Contenido de autoservicio por categoría, calificable por el pasajero (pulgar arriba/abajo).
- **Caso escalado** (`casos_escalados`) — Consulta que el Asistente IA no pudo resolver y se deriva por email al equipo de soporte interno (Gmail API) — no existe chat en vivo con agente humano dentro de la aplicación.

## Ofertas y Promociones *(módulo nuevo v3.0)*

- **Oferta destacada** (`ofertas_destacadas`) — Promoción visible en portada/resultados por producto, sin código de cupón asociado necesariamente.
- **Cupón de descuento** (`cupones_descuento`, `cupones_uso`) — Código aplicable en checkout con monto/porcentaje, producto aplicable y fecha de expiración; su acumulación con el descuento propio de un paquete (CU-T14) es una regla de negocio pendiente de definir (ver QP-18 en `analisis-cus-completo.md`).
- **Campaña de email** (`campanas_email`) — Envío promocional a un segmento de pasajeros vía SendGrid.

## Asistente IA *(módulo nuevo v3.0)*

- **Conversación** (`conversaciones_ia`, `mensajes_ia`) — Hilo de interacción entre un pasajero y el Asistente IA; puede ser informativa (documentos, destinos, clima, requisitos) o transaccional (requiere sesión activa — CU-O108).
- **Contexto acotado y verificable** — Principio constitucional H1: el Asistente IA nunca inventa información de vuelos/tarifas/políticas, solo responde sobre datos que el sistema puede verificar; si no puede, escala el caso (CU-O100).

## Documentación técnica (convenciones usadas en las specs)

- **CU-O / CU-T / CU-E** — Caso de uso Operativo / Táctico / Estratégico, numerado según el catálogo de `docs/aerotrack-travel-casos-de-uso-v3.md` (v3.1). IDs planos por nivel (nunca prefijo de módulo embebido) — la asociación CU↔módulo vive en `analisis-cus-completo.md` sección 1, no en el ID.
- **`<<include>>`** — Relación UML obligatoria: el caso de uso base nunca se completa sin ejecutar el caso de uso incluido.
- **`<<extend>>`** — Relación UML opcional/condicional: el caso de uso base se completa normalmente, y el caso de uso que extiende solo ocurre bajo una condición específica.
- **RF-{PREF}-NNN** — Requisito Funcional de un módulo (p. ej. `RF-SEG-001`).
- **RNF-{PREF}-NNN** — Requisito No Funcional de un módulo.
- **RN-{PREF}-NNN** — Regla de Negocio de un módulo.
- **HU-{PREF}-NN** — Historia de Usuario de un módulo.
- **QP-NN** — Escenario "qué pasa si" documentado en `analisis-cus-completo.md`.
