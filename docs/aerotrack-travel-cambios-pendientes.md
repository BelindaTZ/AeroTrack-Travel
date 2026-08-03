# AeroTrack Travel — Cambios Pendientes al Catálogo de CUs
**Versión de referencia:** aerotrack-travel-casos-de-uso-v3.md (148 CU)  
**Origen:** análisis táctico por departamento + migración de arquitectura de BD  

> **Criterio de implementación por fases:**
> - **Fase actual:** CU tácticos de **gestión** (configuración del sistema) e **informes simples**
>   (lectura directa desde BD Operacional — MinIO, sin ETL previo).
> - **Fase posterior:** CU tácticos de **informes compuestos** (requieren pipeline ETL
>   Airflow → ClickHouse). Se documentan aquí para trazabilidad pero NO se implementan ahora.

---

## 0. Contexto de arquitectura

| Capa | BD | Rol |
|---|---|---|
| Staging / Configuración | PocketBase | Datos origen (BTS/FAA, respuestas APIs), config del sistema (usuarios, roles, permisos) |
| **Operacional** | **MinIO** `aerotrack-travel-operational` | Registros de negocio activos en JSON por colección — reservas, pasajeros, pagos, facturas, disrupciones, conversaciones, carritos |
| **Analítica táctica** | **ClickHouse** | Tablas de agregación pre-calculadas por Airflow — instalado, sin esquema todavía |

---

## 1. CU a eliminar

| CU | Razón |
|---|---|
| CU-T09 | Es feature de UI del Pasajero en búsqueda de hotel, no informe de gestión. Pasa a regla de negocio en spec de CU-O56. |

---

## 2. CUs a reasignar

| CU | Antes | Después | Razón |
|---|---|---|---|
| CU-T18 | Ventas y Reservas | **Finanzas** | Política de reembolsos es decisión financiera. |
| CU-T36 | Actor: Administrador | Actor: **Agente** | El agente gestiona operativamente la bandeja de casos escalados. |

---

## 3. CUs a implementar AHORA — Gestión + Informes simples

### 3.1 Nuevos CUs tácticos — implementar ahora

| ID | Nombre | Tipo | Departamento | Fuente |
|---|---|---|---|---|
| CU-T37 | Ver reporte de captación de pasajeros nuevos por período y canal de registro | Informe simple | Gestión de Clientes | MinIO — `pasajeros` |
| CU-T38 | Ver estado de salud del catálogo de productos (disponibles, última sincronización por fuente) | Informe simple | TI | MinIO — `sincronizaciones_log` |
| CU-T43 | Ver mis reservas asistidas por período | Informe simple | Operaciones (Agente) | MinIO — `reservas` |
| CU-T44 | Ver cola de reservas con pago próximo a vencer en mi cartera | Informe simple | Operaciones (Agente) | MinIO — `reservas` |
| CU-T46 | Ver casos de soporte escalados pendientes (mi bandeja activa) | Informe simple | Operaciones (Agente) | MinIO — `tickets_soporte` |
| CU-T49 | Ver historial de disrupciones recibidas en mis reservas pasadas | Informe simple | Pasajero — Diferenciador | MinIO — `disrupciones` |
| CU-T51 | Ver reporte de comisiones pendientes de cobro por aerolínea y proveedor | Informe simple | Finanzas | MinIO — `comisiones` |
| CU-T52 | Ver reporte de remesas pendientes de pago a proveedores (modelo merchant) | Informe simple | Finanzas | MinIO — `remesas` |
| CU-T55 | Ver reporte de favoritos y destinos más guardados por los pasajeros | Informe simple | Comercial y Marketing | MinIO — `favoritos` |

### 3.2 CUs tácticos existentes (v3) — también implementar ahora

Estos ya estaban en el catálogo v3. Se implementan porque son de gestión o informe simple:

| ID | Nombre | Tipo |
|---|---|---|
| CU-T01 | Monitorear intentos fallidos de autenticación | Informe simple |
| CU-T02 | Forzar expiración de sesiones activas de un usuario | Gestión |
| CU-T03 | Configurar política de contraseñas y duración de sesión | Gestión |
| CU-T05 | Exportar base de pasajeros con filtros (período, destino, frecuencia) | Informe simple |
| CU-T06 | Configurar parámetros del catálogo de vuelos | Gestión |
| CU-T07 | Monitorear estado del DAG de catálogo de vuelos | Informe simple |
| CU-T14 | Configurar porcentajes de descuento por tipo de paquete | Gestión |
| CU-T16 | Ver reporte de reservas por estado y período | Informe simple |
| CU-T17 | Monitorear reservas próximas a vencer por pago pendiente | Informe simple |
| CU-T18 | Configurar política de reembolsos por tipo de producto y tarifa *(reasignado a Finanzas)* | Gestión |
| CU-T19 | Ver dashboard de vuelos activos en monitoreo en tiempo real | Informe simple |
| CU-T20 | Configurar umbrales de risk score que disparan alerta proactiva | Gestión |
| CU-T24 | Configurar programa de beneficios (puntos, niveles, vencimiento) | Gestión |
| CU-T26 | Configurar recuperación de carrito abandonado | Gestión |
| CU-T28 | Gestionar base de conocimiento (artículos FAQ) | Gestión |
| CU-T30 | Crear y gestionar cupones de descuento | Gestión |
| CU-T31 | Configurar y enviar campaña de email promocional | Gestión |
| CU-T34 | Configurar el asistente IA | Gestión |
| CU-T36 | Gestionar bandeja de casos escalados *(reasignado a actor Agente)* | Informe simple |

---

## 4. CUs a implementar DESPUÉS — Informes compuestos (requieren ETL + ClickHouse)

> Estos CUs se documentan para trazabilidad. Su implementación queda pendiente
> hasta que el esquema de ClickHouse esté definido y los DAGs ETL estén activos.

### 4.1 Nuevos CUs tácticos — implementar después

| ID | Nombre | Departamento | Fuente requerida |
|---|---|---|---|
| CU-T04 | Segmentación de pasajeros por frecuencia de viaje y destinos preferidos | Gestión de Clientes | ClickHouse — `agg_segmentos_pasajero` |
| CU-T25 | Reporte de alertas de precio activas y conversiones generadas | Gestión de Clientes | ClickHouse — `agg_alertas_conversion` |
| CU-T39 | Reporte de efectividad de notificaciones de disrupción | Operaciones | ClickHouse — `agg_disrupciones_aerolinea_ruta` |
| CU-T40 | Reporte de canal de venta (autoservicio vs. asistida) por tipo de producto | Ventas y Reservas | ClickHouse — `agg_ingresos_por_producto_mes` |
| CU-T41 | Reporte de retención de pasajeros (2+ reservas, frecuencia de recompra) | Gestión de Clientes | ClickHouse — `agg_segmentos_pasajero` |
| CU-T42 | Reporte de conversión del funnel completo (búsqueda → carrito → checkout → confirmada) | Ventas y Reservas | ClickHouse — `agg_conversion_busqueda_reserva` |
| CU-T45 | Ver disrupciones activas con riesgo alto en vuelos de mis pasajeros (Agente) | Operaciones | ClickHouse — `agg_disrupciones_aerolinea_ruta` |
| CU-T47 | Ver análisis histórico de puntualidad de una ruta (mes, día de semana, causas) | Pasajero — Diferenciador | ClickHouse — `agg_otp_aerolinea_mes`, `agg_causas_retraso_mes`, `agg_otp_dia_semana` |
| CU-T48 | Ver comparativa de aerolíneas para un par origen-destino (OTP histórico) | Pasajero — Diferenciador | ClickHouse — `agg_otp_aerolinea_mes` |
| CU-T50 | Reporte de reembolsos procesados por motivo, tipo y período | Finanzas | ClickHouse — `agg_ingresos_por_producto_mes` |
| CU-T53 | Reporte de destinos más vendidos por tipo de producto y período | Comercial y Marketing | ClickHouse (MinIO operacional — `reserva_items`) |
| CU-T54 | Reporte de suscriptores al newsletter (activos, bajas, tasa de apertura) | Comercial y Marketing | MinIO operacional — `suscriptores_newsletter` × `campanas_email` |

### 4.2 CUs tácticos existentes (v3) — implementar después

| ID | Nombre | Fuente requerida |
|---|---|---|
| CU-T08 | Rutas más buscadas y tasa de conversión búsqueda→reserva | ClickHouse — `agg_conversion_busqueda_reserva` |
| CU-T10 | Hoteles más reservados por destino y período | MinIO operacional (agregación en consulta) |
| CU-T11 | Reservas de autos por proveedor y categoría de vehículo | MinIO operacional (agregación en consulta) |
| CU-T12 | Actividades más reservadas por destino y categoría | MinIO operacional (agregación en consulta) |
| CU-T13 | Cruceros más consultados por destino y temporada | MinIO operacional (agregación en consulta) |
| CU-T15 | Combinaciones de paquete más vendidas y margen generado | ClickHouse — `agg_paquetes_margen_mes` |
| CU-T21 | Reporte de disrupciones por aerolínea, ruta y período | ClickHouse — `agg_disrupciones_aerolinea_ruta` |
| CU-T22 | Dashboard financiero (ingresos, comisiones, remesas) | ClickHouse — `agg_ingresos_por_producto_mes` |
| CU-T23 | Reporte de ingresos por período y tipo de producto | ClickHouse — `agg_ingresos_por_producto_mes` |
| CU-T27 | Reporte de carritos abandonados y tasa de recuperación | MinIO operacional (agregación en consulta) |
| CU-T29 | Métricas de satisfacción del centro de ayuda | ClickHouse — `agg_satisfaccion_soporte` |
| CU-T32 | Reporte de cupones usados, descuentos aplicados y conversiones | MinIO operacional (agregación en consulta) |
| CU-T33 | Reporte de consultas frecuentes al asistente IA | MinIO operacional (agregación en consulta) |
| CU-T35 | Ver matriz de permisos actual (roles × módulos × tablas) | PocketBase (JOIN entre tablas de permisos) |

---

## 5. Nuevas colecciones requeridas en MinIO operacional

| Colección | Estado | Campos mínimos | CUs |
|---|---|---|---|
| `busquedas_recientes` | Ya existe en MinIO — verificar campos | origen, destino, fecha_viaje, num_pasajeros, fecha_busqueda, pasajero_id (nullable), tipo_producto | T08, T42 |
| `suscriptores_newsletter` | No existe — crear | email, estado (activo/baja), fecha_suscripcion | T54, CU-O104 |
| `campanas_email` | No existe — crear | nombre, fecha_envio, total_enviados, tasa_apertura, tasa_clicks | T54, T31 |

---

## 6. Tablas de agregación para ClickHouse (fase posterior)

> **Tarea para Code:** definir esquema de tablas en ClickHouse antes de implementar
> la fase de informes compuestos. ClickHouse está instalado (puerto 8123) pero sin esquema.

| Tabla | DAG propuesto | Frecuencia | CUs |
|---|---|---|---|
| `agg_ingresos_por_producto_mes` | `aerotrack_travel_finanzas_etl` | Diaria | T22, T23, T40, T50 |
| `agg_segmentos_pasajero` | `aerotrack_travel_clientes_etl` | Semanal | T04, T41 |
| `agg_conversion_busqueda_reserva` | `aerotrack_travel_ventas_etl` | Diaria | T08, T42 |
| `agg_disrupciones_aerolinea_ruta` | `aerotrack_travel_operaciones_etl` | Diaria | T21, T39, T45 |
| `agg_paquetes_margen_mes` | `aerotrack_travel_finanzas_etl` | Semanal | T15 |
| `agg_alertas_conversion` | `aerotrack_travel_clientes_etl` | Diaria | T25 |
| `agg_satisfaccion_soporte` | `aerotrack_travel_operaciones_etl` | Diaria | T29 |
| `agg_otp_aerolinea_mes` | `aerotrack_elt_pipeline` | Semanal | T21, T47, T48 |
| `agg_causas_retraso_mes` | `aerotrack_elt_pipeline` | Semanal | T47 |
| `agg_otp_dia_semana` | `aerotrack_elt_pipeline` | Semanal | T47 |
| `agg_rutas_eficiencia` | `aerotrack_elt_pipeline` | Semanal | T08 |

---

## 7. Roles RBAC por departamento

Crear como seed de datos en PocketBase usando CU-O09 y CU-O112:

| Rol | Acceso |
|---|---|
| `admin_general` | Acceso total |
| `admin_ti` | Seguridad, Integraciones, Configuración del sistema |
| `admin_finanzas` | Facturación, reportes financieros |
| `admin_comercial` | Ofertas, Asistente IA, reportes de marketing |
| `admin_operaciones` | Disrupciones, Centro de Ayuda, dashboard vuelos activos |
| `admin_ventas` | Todos los módulos de productos, reportes de ventas |
| `admin_clientes` | Pasajeros, Cuenta/Mis Viajes, segmentación |
| `agente` | Reservas asistidas, cola de pagos, disrupciones de su cartera, casos escalados propios |

---

## 8. Conversión de T09 a regla de negocio

CU-T09 ("Comparar hasta 5 propiedades de hotel lado a lado") pasa a regla de negocio
en el spec de CU-O56 (Filtrar resultados de hoteles): el pasajero puede seleccionar
hasta 5 hoteles del listado para comparar. No genera CU-O nuevo.

---

## 9. Resumen de implementación por fases

### Fase actual — implementar ahora

| Tipo | CUs existentes v3 | CUs nuevos | Total fase actual |
|---|---|---|---|
| Gestión | T02, T03, T06, T14, T18, T20, T24, T26, T28, T30, T31, T34 (12) | — | 12 |
| Informe simple | T01, T05, T07, T16, T17, T19, T36 (7) | T37, T38, T43, T44, T46, T49, T51, T52, T55 (9) | 16 |
| **Total ahora** | **19** | **9** | **28** |

### Fase posterior — implementar después (requieren ClickHouse)

| Tipo | CUs existentes v3 | CUs nuevos | Total fase posterior |
|---|---|---|---|
| Informe compuesto | T08, T10, T11, T12, T13, T15, T21, T22, T23, T27, T29, T32, T33, T35 (14) | T04, T25, T39, T40, T41, T42, T45, T47, T48, T50, T53, T54 (12) | 26 |
| **Total después** | **14** | **12** | **26** |

### Totales del catálogo v4

| Nivel | v3 | Cambios | v4 |
|---|---|---|---|
| CU Operativos | 112 | Sin cambios | **112** |
| CU Tácticos | 36 | −1 (T09) + 18 nuevos (T37–T55) | **53** |
| **Total** | **148** | **+17** | **165** |
