# AeroTrack Travel — Mapa de Objetivos Estratégicos, Tácticos y Operativos

> Estructura equivalente al doc empresarial de AeroTrack Analytics.
> Los objetivos siguen la jerarquía OE → OT → OO → Meta.
> Los OT corresponden a los definidos en el análisis táctico por departamento.
> Los OO corresponden a los CU-O del catálogo operativo.

---

## Balanced Scorecard — Cuadro de Mando Integral

| PERSPECTIVA | OBJETIVO ESTRATÉGICO | INDICADOR CLAVE | META |
|---|---|---|---|
| Financiera | OE-1: Incrementar la adquisición y activación de viajeros a escala global mediante canales digitales de alto rendimiento y bajo costo de captación | Costo de Adquisición del Cliente (CAC) digital / Tasa de activación (registro → primera reserva) | Reducir el CAC en un 20% anual; tasa de activación ≥ 40% |
| Cliente | OE-2: Ampliar el inventario de productos de viaje y el alcance comercial de la agencia mediante la integración con ecosistemas globales de distribución y reservas | Cobertura de productos disponibles (vuelos, hoteles, autos, actividades, cruceros, paquetes) / Tasa de conversión búsqueda→reserva | 6 tipos de producto activos; tasa de conversión ≥ 3% |
| Procesos Internos | OE-3: Garantizar la disponibilidad continua y el rendimiento óptimo de la plataforma de reservas ante el crecimiento global de la demanda operacional | Uptime de la plataforma / Tiempo de respuesta de notificaciones de disrupción al pasajero | Uptime ≥ 99.9% mensual; notificación al pasajero en < 5 minutos desde la detección |
| Aprendizaje y Crecimiento | OE-4: Fortalecer la ventaja competitiva de AeroTrack Travel centralizando la inteligencia de datos del viajero y de las operaciones para la toma de decisiones estratégicas | Tiempo de disponibilidad de reportes estratégicos / Precisión del riesgo de disrupción estimado vs. real | Dashboards actualizados cada hora; precisión del risk score ≥ 80% |

---

## Mapa jerárquico OE → OT → OO → Meta

---

### OE-1 — Incrementar la adquisición y activación de viajeros a escala global mediante canales digitales de alto rendimiento y bajo costo de captación

| OBJETIVO TÁCTICO (OT) | OBJETIVO OPERATIVO (OO) | META |
|---|---|---|
| **Maximizar la adquisición de nuevos pasajeros y la tasa de retención de pasajeros activos mediante el análisis de tendencias de registro, comportamiento de reserva recurrente y segmentación por destinos preferidos** (T04, T37, T41) | OO-1.1: Registrar nuevo pasajero mediante autoservicio digital completo (CU-O07) | El pasajero completa su registro sin intervención de agente desde cualquier dispositivo |
| | OO-1.2: Ver reporte de captación de pasajeros nuevos por período y canal de registro (IS-05) | El Director de Clientes identifica qué canal digital genera mayor volumen de activación |
| | OO-1.3: Ver reporte de retención y segmentación de pasajeros (DB-05) | La Dirección conoce la distribución de pasajeros por segmento (nuevo/recurrente/frecuente) y ajusta estrategias |
| **Incrementar la conversión de intenciones de compra en reservas confirmadas mediante el seguimiento y medición de la efectividad de las alertas de precio activadas por los pasajeros** (T25) | OO-1.4: Crear alerta de precio para una ruta guardada (CU-O91) | El pasajero recibe notificación automática cuando el precio de su ruta de interés baja |
| | OO-1.5: Ver reporte de alertas de precio activas y conversiones generadas (DB-12) | El Director de Clientes mide qué porcentaje de alertas resulta en reserva confirmada |
| **Evaluar la efectividad de las estrategias de promoción y captación de leads mediante el análisis del comportamiento de suscriptores al newsletter, el impacto de los cupones y la identificación de destinos de mayor interés** (T32, T53, T54, T55) | OO-1.6: Crear y gestionar cupones de descuento (WP-06) | El CMO configura promociones con código, porcentaje/monto, producto y fecha de expiración |
| | OO-1.7: Aplicar cupón de descuento en checkout (CU-O103) | El pasajero aplica el descuento directamente en el pago sin fricción adicional |
| | OO-1.8: Ver reporte de cupones usados, descuentos aplicados y conversiones (DB-10) | El CMO evalúa el retorno de cada campaña promocional |
| **Medir la eficiencia del embudo de compra completo para identificar las etapas con mayor tasa de abandono y proponer acciones de mejora en el flujo de adquisición** (T42) | OO-1.9: Agregar ítem al carrito y proceder al checkout (CU-O94, CU-O96) | El pasajero avanza de la selección al pago en un flujo continuo sin salir del sistema |
| | OO-1.10: Ver reporte de conversión del funnel completo: búsqueda → carrito → checkout → confirmada (DB-01) | El Director Comercial identifica en qué etapa del embudo se pierden más usuarios y toma acciones |
| **Controlar el ciclo de vida de las reservas activas detectando las que están en riesgo de expiración y evaluando la distribución por canal para mejorar la autonomía digital del pasajero** (T16, T17, T40) | OO-1.11: Ver listado de reservas por estado y período (IS-08) | El Jefe de Ventas supervisa la operación comercial del período sin buscar reserva por reserva |
| | OO-1.12: Ver reservas próximas a vencer por pago pendiente (IS-09) | El equipo contacta proactivamente al pasajero antes de que la reserva expire |
| | OO-1.13: Ver distribución de reservas por canal de venta (DB-01) | La Dirección mide el avance hacia el autoservicio digital y reduce dependencia del agente |

---

### OE-2 — Ampliar el inventario de productos de viaje y el alcance comercial de la agencia mediante la integración con ecosistemas globales de distribución y reservas

| OBJETIVO TÁCTICO (OT) | OBJETIVO OPERATIVO (OO) | META |
|---|---|---|
| **Optimizar la relevancia y actualización del catálogo de vuelos mediante el monitoreo del proceso de publicación automática y el análisis de rutas de mayor demanda para priorizar el catálogo** (T07, T08) | OO-2.1: Generar y publicar catálogo de vuelos automáticamente (CU-O19) | El catálogo de vuelos se actualiza sin intervención manual con datos frescos de la fuente externa global |
| | OO-2.2: Ver estado del proceso de publicación del catálogo de vuelos (IS-06) | El Jefe de Ventas confirma que el catálogo está actualizado antes de una campaña |
| | OO-2.3: Ver rutas más buscadas y tasa de conversión búsqueda→reserva (DB-08) | La Dirección prioriza las rutas con mayor demanda en el catálogo |
| **Identificar los productos de mayor demanda en cada categoría de servicio para orientar las estrategias de disponibilidad y negociación con proveedores** (T10, T11, T12, T13) | OO-2.4: Buscar y reservar vuelos con cobertura mundial (CU-O17) | El pasajero accede a cualquier ruta origen-destino disponible en el catálogo global |
| | OO-2.5: Buscar y reservar hoteles por destino y fechas (CU-O54) | El pasajero accede a disponibilidad real de hoteles en cualquier destino del mundo |
| | OO-2.6: Buscar y reservar autos por aeropuerto y fechas (CU-O61) | El pasajero compara y reserva vehículos de múltiples proveedores globales |
| | OO-2.7: Buscar y reservar actividades por destino (CU-O65) | El pasajero explora tours y excursiones con disponibilidad y precios reales |
| | OO-2.8: Buscar y reservar cruceros por destino y duración (CU-O71) | El pasajero accede a itinerarios y precios de cruceros desde la misma plataforma |
| | OO-2.9: Ver demanda por tipo de producto (DB-06) | La Dirección identifica qué categoría de servicio lidera en reservas e ingresos |
| **Evaluar el rendimiento de los paquetes combinados y medir la efectividad del carrito para reducir el abandono y aumentar el margen por venta** (T15, T27) | OO-2.10: Construir paquete seleccionando componentes (CU-O76) | El pasajero combina vuelo + hotel + auto/actividad en un solo flujo de compra |
| | OO-2.11: Ver resumen de paquete con desglose de ahorro vs. reserva por separado (CU-O77) | El pasajero visualiza cuánto ahorra al reservar en paquete y toma la decisión con información completa |
| | OO-2.12: Ver reporte de paquetes más vendidos y margen generado (DB-07) | El Director Comercial identifica qué combinaciones son más rentables y las prioriza |
| **Proveer al pasajero inteligencia histórica sobre el desempeño operacional de rutas y aerolíneas en el momento de la búsqueda** (T47, T48, T49) | OO-2.13: Ver análisis histórico de puntualidad de una ruta (CU-T47 / DB-04) | El pasajero ve el OTP real de la ruta, por mes y día de la semana, antes de comprar |
| | OO-2.14: Ver comparativa de aerolíneas para un par origen-destino (CU-T48 / DB-04) | El pasajero compara el historial de puntualidad entre aerolíneas que operan su ruta y elige con datos reales |

---

### OE-3 — Garantizar la disponibilidad continua y el rendimiento óptimo de la plataforma de reservas ante el crecimiento global de la demanda operacional

| OBJETIVO TÁCTICO (OT) | OBJETIVO OPERATIVO (OO) | META |
|---|---|---|
| **Detectar y prevenir accesos no autorizados al sistema mediante el monitoreo continuo de eventos de autenticación y la gestión granular de permisos por rol, módulo y tabla de base de datos** (T01, T35) | OO-3.1: Iniciar sesión con autenticación segura (CU-O01) | Cada usuario accede al sistema según su rol asignado con token JWT validado |
| | OO-3.2: Gestionar usuarios internos y roles del sistema (WP-02, WP-03) | El Director de TI crea, edita y desactiva usuarios y define permisos granulares sin intervención técnica |
| | OO-3.3: Ver listado de intentos fallidos de autenticación (IS-02) | El Director de TI detecta patrones de acceso anómalo antes de que se convierta en una brecha |
| | OO-3.4: Ver matriz de permisos activos (DB-TI) | La Dirección de TI audita quién tiene acceso a qué módulo y tabla en cualquier momento |
| **Asegurar la disponibilidad y consistencia del catálogo de productos mediante la supervisión continua del estado operacional de las integraciones con fuentes externas** (T38) | OO-3.5: Ver estado de sincronización de todas las fuentes externas (IS-03) | El Director de TI verifica que los 6 tipos de catálogo están actualizados antes del horario pico |
| | OO-3.6: Gestionar configuración del sistema (WP-08) | El administrador ajusta parámetros de frecuencia de actualización sin intervención técnica |
| **Garantizar la detección temprana y comunicación oportuna de disrupciones aéreas mediante el monitoreo activo de vuelos reservados y la medición de la efectividad de las notificaciones proactivas** (T19, T21, T39) | OO-3.7: Monitorear bandeja de correo de aerolíneas (CU-O28) | El sistema detecta automáticamente avisos de cambio/cancelación enviados al inbox de la agencia |
| | OO-3.8: Detectar cambio de itinerario comparando estado real vs. reserva (CU-O29) | El sistema identifica cualquier discrepancia entre el vuelo confirmado y su estado operacional actual |
| | OO-3.9: Notificar al pasajero sobre disrupción (CU-O30) | El pasajero recibe el aviso de cambio antes de enterarse por otro canal |
| | OO-3.10: Ver dashboard de vuelos activos en monitoreo (IS-11) | El Director de Operaciones supervisa en tiempo real todos los vuelos de reservas activas del día |
| | OO-3.11: Ver efectividad de notificaciones y disrupciones históricas vs. benchmark (DB-03) | La Dirección mide si las notificaciones generan acción real del pasajero y compara con el histórico BTS/FAA |
| **Evaluar la calidad del servicio de atención al pasajero mediante el análisis de la satisfacción con el centro de ayuda y el seguimiento de los casos escalados** (T29, T36) | OO-3.12: Buscar y consultar artículo de ayuda (CU-O97, CU-O98) | El pasajero resuelve su consulta sin necesidad de escalar a un agente humano |
| | OO-3.13: Hacer consulta al asistente IA (CU-O107, CU-O108) | El pasajero obtiene respuesta a su consulta informativa o transaccional en lenguaje natural |
| | OO-3.14: Ver métricas de satisfacción y casos escalados (DB-09) | El Director de Operaciones mide la tasa de resolución autónoma y la satisfacción del pasajero |
| **Controlar la productividad individual del agente y la gestión de su cartera de reservas y casos para garantizar la calidad del servicio asistido** (T43, T44, T45, T46) | OO-3.15: Crear reserva asistida en nombre del pasajero (CU-O22) | El agente puede reservar cualquier producto en nombre del pasajero cuando este lo solicita |
| | OO-3.16: Ver mis reservas asistidas y cola de pagos próximos a vencer (IS-15, IS-16) | El agente organiza su día de trabajo sin depender de un supervisor para saber qué atender primero |
| | OO-3.17: Ver productividad del agente (DB-13) | El Director de Operaciones compara el rendimiento entre agentes y detecta desbalances de carga |
| **Asegurar la exactitud y trazabilidad de todos los flujos financieros del período mediante el seguimiento de ingresos, comisiones, reembolsos y remesas pendientes** (T22, T23, T50, T51, T52) | OO-3.18: Procesar pago de reserva (CU-O32) | Cada pago queda registrado con su estado, monto y vínculo a la reserva correspondiente |
| | OO-3.19: Procesar reembolso según política de tarifa (CU-O37) | Los reembolsos se procesan automáticamente respetando la política de la tarifa comprada |
| | OO-3.20: Ver dashboard financiero del período (DB-02) | El CFO accede en tiempo real al estado de ingresos, comisiones y obligaciones pendientes |
| | OO-3.21: Ver comisiones pendientes y remesas adeudadas (IS-20, IS-21) | El Director Financiero prioriza las gestiones de cobro y pago con mayor impacto financiero |

---

### OE-4 — Fortalecer la ventaja competitiva de AeroTrack Travel centralizando la inteligencia de datos del viajero y de las operaciones para la toma de decisiones estratégicas

| OBJETIVO TÁCTICO (OT) | OBJETIVO OPERATIVO (OO) | META |
|---|---|---|
| **Mejorar la experiencia conversacional del asistente de IA mediante el análisis sistemático de las consultas más frecuentes y la identificación de temas sin respuesta satisfactoria para enriquecer la base de conocimiento** (T33) | OO-4.1: Iniciar conversación con el asistente IA y calificar respuesta (CU-O106, CU-O110) | El pasajero recibe respuestas útiles y puede retroalimentar la calidad del asistente |
| | OO-4.2: Ver consultas frecuentes al asistente y temas sin respuesta (DB-11) | El CMO identifica qué temas reforzar en el asistente y en el centro de ayuda |
| | OO-4.3: Gestionar artículos de ayuda / FAQ (WP-05) | El Director de Operaciones actualiza la base de conocimiento del asistente sin intervención técnica |
| **Proveer al pasajero inteligencia histórica sobre el desempeño operacional de rutas y aerolíneas en el momento de la búsqueda** (T47, T48, T49) | OO-4.4: Ver análisis histórico de puntualidad de una ruta con datos BTS/FAA (DB-04) | El pasajero toma una decisión de compra informada con datos históricos reales — diferenciador que ninguna OTA de la región ofrece |
| | OO-4.5: Ver comparativa de aerolíneas por OTP histórico en la ruta seleccionada (DB-04) | El pasajero elige la aerolínea con mejor historial de puntualidad en su ruta específica |
| | OO-4.6: Ver historial de disrupciones propias recibidas en reservas pasadas (IS-22) | El pasajero verifica que la agencia lo notificó proactivamente en cada incidente anterior, generando confianza |
| **Desarrollar dashboards estratégicos para la alta dirección que consoliden la inteligencia operacional y comercial de la agencia** | OO-4.7: Ver dashboard estratégico — Visión General del Negocio (DS-00) | La Dirección General accede a un cockpit ejecutivo con los KPIs más críticos de los 4 OEs en una sola vista |
| | OO-4.8: Ver dashboard estratégico — Rendimiento de la Oferta (DS-01) | La Dirección evalúa la cobertura de productos, ingresos por tipo y tasa de conversión global |
| | OO-4.9: Ver dashboard estratégico — Gestión de Disrupciones (DS-02) | La Dirección evalúa la efectividad global del sistema de notificaciones proactivas |
| | OO-4.10: Ver dashboard estratégico — Inteligencia y Automatización (DS-03) | La Dirección evalúa el uso del asistente IA, alertas de precio y cobertura del dataset BTS/FAA |
| | OO-4.11: Navegar desde dashboard estratégico al dashboard táctico del departamento correspondiente | La Dirección accede al detalle departamental sin cambiar de sistema — drill-down estratégico → táctico |

---

## Resumen de trazabilidad

| OE | OTs vinculados | OOs vinculados | CU-T ref | CU-O ref |
|---|---|---|---|---|
| OE-1 Adquisición y activación | 5 | 13 | T04, T16, T17, T25, T32, T37, T40, T41, T42, T53, T54, T55 | O07, O91, O94, O96, O103 |
| OE-2 Inventario y alcance comercial | 4 | 14 | T07, T08, T10, T11, T12, T13, T15, T27, T47, T48 | O17, O54, O61, O65, O71, O76, O77 |
| OE-3 Disponibilidad y rendimiento | 5 | 21 | T01, T19, T21, T22, T23, T29, T35, T36, T38, T39, T43, T44, T45, T46, T50, T51, T52 | O01, O22, O28, O29, O30, O32, O37, O97, O98, O107, O108 |
| OE-4 Inteligencia de datos | 3 | 11 | T33, T47, T48, T49 | O106, O110 + DS-00 a DS-03 |
| **Total** | **17** | **59** | **T01–T55** | **O01–O113** |
