# AeroTrack Travel — Especificaciones de Dashboards e Informes Compuestos

> Este documento define la arquitectura ETL, el esquema de ClickHouse
> y las especificaciones completas de los 13 dashboards tácticos.
> Es la fuente de verdad para la implementación de la fase de informes compuestos.

---

## 1. Arquitectura ETL — Flujo de datos hacia ClickHouse

### Pipeline de Parquet (indicado por el instructor)

```
MinIO BD Operacional (aerotrack-travel-operational)
    + MinIO Dims/BTS (aerotrack-travel-dims)
                ↓
        Airflow DAG (cada hora — básico, sin condiciones de calidad)
                ↓
    /Proyecto_AeroTrack/Datos/Parquet/
        crudo/          ← extracción directa desde MinIO
        procesando/     ← transformación y agregación en curso
        terminado/      ← listo para carga en ClickHouse
                ↓
        ClickHouse (BD Columnar — aerotrack_travel)
```

**Nota:** La estructura crudo/procesando/terminado es temporal para esta
entrega. Los archivos se nombran por tabla y timestamp:
`{nombre_tabla}_{YYYY-MM-DD_HH}.parquet`

### DAGs de Airflow requeridos

| DAG ID | Schedule | Qué hace |
|---|---|---|
| `aerotrack_travel_etl_comercial` | `@hourly` | Extrae reservas + reserva_items → genera agg_ingresos_por_producto_mes + agg_conversion_busqueda_reserva |
| `aerotrack_travel_etl_clientes` | `@hourly` | Extrae pasajeros + reservas → genera agg_segmentos_pasajero + agg_alertas_conversion |
| `aerotrack_travel_etl_operaciones` | `@hourly` | Extrae disrupciones + vuelos_monitoreo → genera agg_disrupciones_aerolinea_ruta + agg_satisfaccion_soporte |
| `aerotrack_travel_etl_finanzas` | `@hourly` | Extrae facturas + pagos + comisiones + remesas → genera agg_ingresos_por_producto_mes + agg_paquetes_margen_mes |
| `aerotrack_travel_etl_dims` | `@daily` | Sincroniza agg_otp_aerolinea_mes, agg_causas_retraso_mes, agg_otp_dia_semana, agg_rutas_eficiencia desde MinIO dims a ClickHouse |

Cada DAG sigue el patrón de 3 tareas:
1. `extraer` → lee de MinIO, escribe en Parquet/crudo/
2. `transformar` → mueve a Parquet/procesando/, agrega y calcula
3. `cargar` → mueve a Parquet/terminado/, inserta en ClickHouse

---

## 2. Esquema de ClickHouse

### Base de datos
```sql
CREATE DATABASE IF NOT EXISTS aerotrack_travel;
```

### Tablas de agregación

```sql
-- Ingresos por producto y mes (Finanzas + Ventas)
CREATE TABLE aerotrack_travel.agg_ingresos_por_producto_mes (
    periodo         Date,
    tipo_producto   LowCardinality(String),
    total_reservas  UInt32,
    ingresos_brutos Float64,
    comisiones      Float64,
    reembolsos      Float64,
    ingresos_netos  Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, tipo_producto);

-- Segmentos de pasajeros (Clientes)
CREATE TABLE aerotrack_travel.agg_segmentos_pasajero (
    pasajero_id              String,
    total_reservas           UInt32,
    primera_reserva          Date,
    ultima_reserva           Date,
    destino_frecuente        String,
    tipo_producto_frecuente  LowCardinality(String),
    gasto_total              Float64,
    segmento                 LowCardinality(String)
    -- segmento: 'nuevo' (1 reserva) / 'recurrente' (2-4) / 'frecuente' (5+)
) ENGINE = ReplacingMergeTree()
ORDER BY pasajero_id;

-- Conversión del funnel (Ventas)
CREATE TABLE aerotrack_travel.agg_conversion_busqueda_reserva (
    periodo                          Date,
    tipo_producto                    LowCardinality(String),
    total_busquedas                  UInt32,
    total_carritos                   UInt32,
    total_checkouts                  UInt32,
    total_confirmadas                UInt32,
    tasa_conversion_busqueda_reserva Float64,
    tasa_abandono_carrito            Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, tipo_producto);

-- Disrupciones por aerolínea y ruta (Operaciones)
CREATE TABLE aerotrack_travel.agg_disrupciones_aerolinea_ruta (
    periodo               Date,
    aerolinea_codigo      String,
    aerolinea_nombre      String,
    origen                String,
    destino               String,
    total_notificaciones  UInt32,
    exitosas              UInt32,
    fallidas              UInt32,
    con_accion_pasajero   UInt32,
    tasa_efectividad      Float64,
    otp_benchmark_bts     Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, aerolinea_codigo, origen, destino);

-- Margen de paquetes (Finanzas + Ventas)
CREATE TABLE aerotrack_travel.agg_paquetes_margen_mes (
    periodo            Date,
    tipo_combinacion   LowCardinality(String),
    total_vendidos     UInt32,
    ingresos_brutos    Float64,
    costo_componentes  Float64,
    margen_bruto       Float64,
    margen_porcentaje  Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, tipo_combinacion);

-- Alertas de precio y conversión (Clientes)
CREATE TABLE aerotrack_travel.agg_alertas_conversion (
    periodo                           Date,
    total_alertas_activas             UInt32,
    total_conversiones                UInt32,
    tasa_conversion                   Float64,
    tiempo_promedio_conversion_horas  Float64
) ENGINE = ReplacingMergeTree()
ORDER BY periodo;

-- Satisfacción del soporte (Operaciones)
CREATE TABLE aerotrack_travel.agg_satisfaccion_soporte (
    periodo                            Date,
    categoria                          LowCardinality(String),
    total_consultas                    UInt32,
    calificacion_promedio              Float64,
    tasa_escalacion                    Float64,
    tiempo_promedio_resolucion_horas   Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, categoria);

-- OTP por aerolínea y mes (desde dims BTS/FAA — ya existe en MinIO)
CREATE TABLE aerotrack_travel.agg_otp_aerolinea_mes (
    periodo           Date,
    aerolinea_codigo  String,
    aerolinea_nombre  String,
    origen            String,
    destino           String,
    total_vuelos      UInt32,
    vuelos_a_tiempo   UInt32,
    otp_porcentaje    Float64,
    retraso_promedio_min Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, aerolinea_codigo, origen, destino);

-- Causas de retraso por mes (desde dims BTS/FAA)
CREATE TABLE aerotrack_travel.agg_causas_retraso_mes (
    periodo              Date,
    origen               String,
    destino              String,
    causa                LowCardinality(String),
    -- causa: carrier / weather / nas / security / late_aircraft
    total_casos          UInt32,
    porcentaje_del_total Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (periodo, origen, destino, causa);

-- OTP por día de la semana (desde dims BTS/FAA)
CREATE TABLE aerotrack_travel.agg_otp_dia_semana (
    origen            String,
    destino           String,
    dia_semana        UInt8,   -- 1=lunes … 7=domingo
    total_vuelos      UInt32,
    vuelos_a_tiempo   UInt32,
    otp_porcentaje    Float64
) ENGINE = ReplacingMergeTree()
ORDER BY (origen, destino, dia_semana);
```

---

## 3. Especificaciones de Dashboards

Cada dashboard = un informe compuesto. Accesible desde el backoffice
del rol correspondiente. Todos tienen:
- Selector de período (hoy / esta semana / este mes / rango personalizado)
- Botón "Exportar PDF"
- Actualización al cambiar el filtro sin recargar la página (fetch parcial)

---

### DB-01 — Rendimiento Comercial y Embudo de Conversión
**Objetivo:** Controlar ciclo de reservas y medir eficiencia del embudo
**Rol:** admin_ventas
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_conversion_busqueda_reserva, agg_ingresos_por_producto_mes

#### Grupo A — Métricas clave (fila superior Z)
| KPI | Fórmula | Tipo de visualización | Benchmark referencia |
|---|---|---|---|
| Tasa de conversión búsqueda→reserva | confirmadas / busquedas × 100 | Tarjeta grande + flecha tendencia | OTA promedio: 2-5% |
| Valor promedio de reserva (ASV) | ingresos_brutos / total_reservas | Tarjeta grande + comparativo mes anterior | |
| Tasa de abandono del carrito | (carritos - confirmadas) / carritos × 100 | Gauge semicircular — verde < 90%, rojo > 95% | OTA industry: 93.96% |

#### Grupo B — Volumen y distribución (centro Z)
| Visualización | Datos | Notas |
|---|---|---|
| Gráfico de líneas — tendencia de reservas | Reservas por día del período | Línea principal + línea del período anterior en gris |
| Gráfico de barras apiladas — ingresos por producto | ingresos_netos por tipo_producto | vuelo/hotel/auto/actividad/crucero/paquete |

#### Grupo C — Canal y estado (fila inferior Z)
| Visualización | Datos |
|---|---|
| Gráfico de dona — distribución por canal | autoservicio vs asistida |
| Tarjeta de alerta — reservas próximas a expirar | COUNT WHERE estado=pendiente_pago AND expira<24h |
| Tabla — top 5 productos más reservados | tipo_producto + conteo + ingresos |

**Filtros adicionales:** tipo de producto, canal de venta

---

### DB-02 — Control Financiero del Período
**Objetivo:** Asegurar exactitud y trazabilidad de flujos financieros
**Rol:** admin_finanzas
**Patrón visual:** Modelo F
**Tablas ClickHouse:** agg_ingresos_por_producto_mes, agg_paquetes_margen_mes

#### Fila 1 — Ingresos principales (Modelo F)
| KPI | Fórmula | Visualización |
|---|---|---|
| Ingresos totales del período | SUM(ingresos_netos) | Tarjeta XL destacada |
| Take Rate (tasa de comisión) | SUM(comisiones) / SUM(ingresos_brutos) × 100 | Tarjeta con % objetivo marcado (línea roja si < umbral) |
| Ingreso promedio por reserva | ingresos_brutos / total_reservas | Tarjeta + comparativo mes anterior |

#### Fila 2 — Obligaciones pendientes
| KPI | Visualización | Color |
|---|---|---|
| Comisiones pendientes de cobro | Tarjeta + lista de aerolíneas | Naranja si > 0 |
| Remesas pendientes a proveedores | Tarjeta + próxima fecha vencimiento | Rojo si hay vencidas |
| Reembolsos del período (monto y % sobre ingresos) | Tarjeta doble | Informativo |

#### Columna vertical F — Detalle histórico
| Visualización | Datos |
|---|---|
| Gráfico de líneas — tendencia de ingresos | ingresos_netos últimos 6 períodos |
| Gráfico de barras agrupadas — ingresos vs reembolsos | Por tipo de producto, período actual |
| Mapa de calor — ingresos por día del mes | Cuadrícula 5×7 coloreada por monto |
| Tabla de desglose — Ingresos / Comisiones / Reembolsos / Remesas | Una fila por tipo de producto |

**Filtros adicionales:** tipo de producto, proveedor/aerolínea

---

### DB-03 — Monitoreo de Disrupciones
**Objetivo:** Garantizar detección temprana y comunicación oportuna
**Rol:** admin_operaciones
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_disrupciones_aerolinea_ruta, agg_otp_aerolinea_mes

#### Grupo A — Estado actual (fila superior Z)
| KPI | Fórmula | Visualización |
|---|---|---|
| Vuelos en monitoreo hoy | COUNT vuelos_monitoreo activos | Tarjeta grande |
| Vuelos con riesgo alto | COUNT WHERE risk_score > umbral | Tarjeta con semáforo rojo/amarillo/verde |
| Notificaciones enviadas este mes | COUNT disrupciones WHERE estado=enviado | Tarjeta + tendencia |

#### Grupo B — Efectividad (centro Z)
| Visualización | Datos |
|---|---|
| Gráfico de dona — efectividad de notificaciones | con_accion_pasajero / exitosas × 100 |
| Gráfico de barras horizontal — disrupciones por aerolínea | total_notificaciones + barra comparativa OTP benchmark BTS/FAA |

#### Grupo C — Histórico y soporte (fila inferior Z)
| Visualización | Datos |
|---|---|
| Gráfico de líneas — disrupciones en el tiempo | Por semana, últimas 8 semanas |
| Tarjeta — Casos escalados abiertos | COUNT tickets_soporte WHERE estado=abierto |
| Tarjeta — Satisfacción promedio del soporte | AVG calificacion_promedio |

**Filtros adicionales:** aerolínea, ruta origen-destino, nivel de riesgo

---

### DB-04 — Diferenciador Analítico de Vuelos (Vista del Pasajero)
**Objetivo:** Proveer inteligencia histórica sobre rutas y aerolíneas
**Rol:** pasajero (disponible desde la página de resultados de búsqueda)
**Patrón visual:** Modelo F
**Tablas ClickHouse:** agg_otp_aerolinea_mes, agg_causas_retraso_mes, agg_otp_dia_semana

**Funcionamiento:** se activa cuando el pasajero selecciona un vuelo en
el buscador. Muestra la información de la ruta origen-destino específica.

#### Fila 1 (Modelo F) — Lo más importante
| KPI | Visualización |
|---|---|
| OTP histórico de la ruta (% vuelos a tiempo) | Tarjeta grande + badge "Datos reales BTS/FAA 2021-2025" |
| Mejor aerolínea para esta ruta (mayor OTP) | Tarjeta con nombre de aerolínea + porcentaje |
| Causa de retraso más frecuente | Tarjeta + descripción en lenguaje natural |

#### Columna vertical F — Detalle
| Visualización | Datos |
|---|---|
| Gráfico de barras horizontales rankeadas — OTP por aerolínea | Todas las aerolíneas que vuelan esa ruta |
| Gráfico de líneas — OTP por mes del año | 12 meses — estacionalidad visible |
| Gráfico de barras — OTP por día de la semana | Lunes a domingo |
| Gráfico de torta — distribución de causas de retraso | carrier / weather / NAS / late_aircraft / security |

**Nota:** este dashboard no tiene filtro de período manual — usa
siempre los últimos 12 meses del dataset BTS/FAA disponible.

---

### DB-05 — Captación y Retención de Pasajeros
**Objetivo:** Maximizar adquisición y fidelización
**Rol:** admin_clientes
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_segmentos_pasajero, agg_alertas_conversion

#### Grupo A — Adquisición (fila superior Z)
| KPI | Fórmula | Visualización |
|---|---|---|
| Nuevos pasajeros del período | COUNT WHERE primera_reserva en período | Tarjeta + vs período anterior |
| Tasa de activación | pasajeros con reserva / total registrados × 100 | Tarjeta gauge |
| Canal con mayor captación | GROUP BY canal ORDER BY count DESC LIMIT 1 | Tarjeta texto |

#### Grupo B — Retención (centro Z)
| Visualización | Datos |
|---|---|
| Gráfico de dona — distribución por segmento | nuevo / recurrente / frecuente |
| Gráfico de barras — nuevos pasajeros por semana | Tendencia del período |

#### Grupo C — Alertas e intención de compra (fila inferior Z)
| KPI / Visualización | Datos |
|---|---|
| Alertas de precio activas | COUNT alertas_activas total |
| Tasa de conversión de alertas | tasa_conversion % |
| Tabla — top destinos en alertas activas | destino + count alertas |

---

### DB-06 — Demanda por Tipo de Producto
**Objetivo:** Identificar productos de mayor demanda para orientar estrategias
**Rol:** admin_ventas
**Patrón visual:** Modelo F
**Tablas ClickHouse:** agg_ingresos_por_producto_mes, agg_conversion_busqueda_reserva

#### Fila 1 (Modelo F)
| KPI | Visualización |
|---|---|
| Producto más vendido del período | Tarjeta con icono del tipo de producto |
| Producto con mayor ingreso generado | Tarjeta |
| Producto con mayor tasa de conversión | Tarjeta |

#### Columna vertical F
| Visualización | Datos |
|---|---|
| Gráfico de barras agrupadas — reservas por producto | Por semana, top 6 tipos |
| Gráfico de barras horizontales — ingresos por producto | Ordenado de mayor a menor |
| Gráfico de líneas — tendencia por tipo de producto | Últimas 8 semanas, una línea por tipo |
| Tabla — métricas por producto | tipo / reservas / ingresos / tasa_conversión / abandono |

---

### DB-07 — Paquetes y Carrito
**Objetivo:** Evaluar rendimiento de paquetes y abandono del carrito
**Rol:** admin_ventas
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_paquetes_margen_mes, agg_conversion_busqueda_reserva

#### Grupo A (fila superior Z)
| KPI | Visualización |
|---|---|
| Paquetes vendidos del período | Tarjeta + vs período anterior |
| Margen bruto promedio por paquete | Tarjeta + % sobre precio de venta |
| Tasa de abandono del carrito | Gauge — benchmark OTA 93.96% |

#### Grupo B (centro Z)
| Visualización | Datos |
|---|---|
| Gráfico de barras — ventas por tipo de combinación | vuelo+hotel / vuelo+hotel+auto / etc. |
| Gráfico de barras — margen por combinación | Qué combinación es más rentable |

#### Grupo C (fila inferior Z)
| Visualización | Datos |
|---|---|
| Gráfico de líneas — carritos creados vs completados | Por día del período |
| Tabla — top 5 combinaciones más vendidas | tipo / vendidos / ingresos / margen% |

---

### DB-08 — Catálogo y Rutas de Vuelos
**Objetivo:** Optimizar relevancia y actualización del catálogo
**Rol:** admin_ventas
**Patrón visual:** Modelo F
**Tablas ClickHouse:** agg_conversion_busqueda_reserva, agg_otp_aerolinea_mes

#### Fila 1 (Modelo F)
| KPI | Visualización |
|---|---|
| Ruta más buscada del período | Tarjeta con código origen-destino |
| Tasa de conversión promedio búsqueda→reserva | Tarjeta gauge |
| Última actualización del catálogo | Tarjeta con fecha/hora y estado |

#### Columna vertical F
| Visualización | Datos |
|---|---|
| Tabla rankeada — top 10 rutas más buscadas | ruta / búsquedas / reservas / conversión% |
| Gráfico de barras — búsquedas por tipo de producto | vuelos/hoteles/autos/actividades/cruceros |
| Gráfico de calor — búsquedas por día de la semana y hora | Matriz 7×24 |

---

### DB-09 — Calidad de Soporte y Atención
**Objetivo:** Evaluar calidad del servicio de atención al pasajero
**Rol:** admin_operaciones
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_satisfaccion_soporte

#### Grupo A (fila superior Z)
| KPI | Visualización |
|---|---|
| Calificación promedio del centro de ayuda | Estrellas 1-5 + número |
| Tasa de escalación | % consultas que llegaron a agente humano |
| Tiempo promedio de resolución de casos | Tarjeta en horas + objetivo marcado |

#### Grupo B (centro Z)
| Visualización | Datos |
|---|---|
| Gráfico de barras — calificaciones por categoría de consulta | ordenado de menor a mayor |
| Gráfico de líneas — satisfacción en el tiempo | Por semana |

#### Grupo C (fila inferior Z)
| Visualización | Datos |
|---|---|
| Gráfico de dona — consultas por categoría | distribución temática |
| Tabla — artículos más consultados | título / vistas / calificación promedio |

---

### DB-10 — Efectividad de Campañas y Promociones
**Objetivo:** Evaluar estrategias de promoción y captación
**Rol:** admin_comercial
**Patrón visual:** Modelo F
**Tablas:** MinIO operacional (cupones, suscriptores, campanas_email, favoritos)

#### Fila 1 (Modelo F)
| KPI | Visualización |
|---|---|
| Cupones canjeados del período | Tarjeta + % sobre emitidos |
| Descuento total aplicado | Tarjeta en USD |
| Tasa de apertura del último newsletter | Tarjeta % |

#### Columna vertical F
| Visualización | Datos |
|---|---|
| Gráfico de barras — cupones usados por tipo | % descuento / producto aplicable |
| Gráfico de líneas — suscriptores activos en el tiempo | Altas vs bajas por semana |
| Tabla — top 10 destinos más guardados como favoritos | destino / veces guardado |
| Gráfico de dona — distribución de favoritos por tipo | destino/hotel/actividad |

---

### DB-11 — Inteligencia del Asistente IA
**Objetivo:** Mejorar experiencia conversacional del asistente
**Rol:** admin_comercial
**Patrón visual:** Modelo F
**Tablas:** MinIO operacional (mensajes_ia, conversaciones_ia)

#### Fila 1 (Modelo F)
| KPI | Visualización |
|---|---|
| Total conversaciones del período | Tarjeta |
| % respuestas con calificación positiva | Gauge |
| Temas sin respuesta satisfactoria (count) | Tarjeta de alerta |

#### Columna vertical F
| Visualización | Datos |
|---|---|
| Tabla rankeada — top 15 temas más consultados | tema / frecuencia / % positivo |
| Gráfico de barras — consultas por tipo | informativas vs transaccionales |
| Gráfico de líneas — volumen de consultas en el tiempo | Por día |

---

### DB-12 — Alertas de Precio y Conversión
**Objetivo:** Incrementar conversión de intenciones de compra
**Rol:** admin_clientes
**Patrón visual:** Modelo Z
**Tablas ClickHouse:** agg_alertas_conversion

#### Grupo A (fila superior Z)
| KPI | Visualización |
|---|---|
| Alertas activas totales | Tarjeta |
| Tasa de conversión de alertas | Tarjeta gauge + benchmark |
| Tiempo promedio alerta→reserva | Tarjeta en horas |

#### Grupo B y C
| Visualización | Datos |
|---|---|
| Gráfico de barras — alertas por ruta top 10 | origen-destino más alertado |
| Gráfico de líneas — conversiones por semana | Tendencia |
| Tabla — rutas con alerta pero sin conversión | Oportunidades de campaña |

---

### DB-13 — Productividad del Agente
**Objetivo:** Controlar productividad individual y cartera
**Rol:** admin_operaciones (vista global), agente (vista propia)
**Patrón visual:** Modelo F
**Tablas:** MinIO operacional (reservas, tickets_soporte)

#### Fila 1 (Modelo F) — Vista admin_operaciones
| KPI | Visualización |
|---|---|
| Total reservas asistidas del período | Tarjeta |
| Agente con más reservas cerradas | Tarjeta ranking |
| Casos de soporte resueltos vs pendientes | Tarjeta doble |

#### Columna vertical F
| Visualización | Datos |
|---|---|
| Tabla — ranking de agentes | agente / reservas / valor / casos_resueltos |
| Gráfico de barras — reservas por agente | Comparativo del período |
| Gráfico de líneas — productividad en el tiempo | Por semana por agente top 3 |

**Vista del agente (filtrada automáticamente por agente_id):**
- Mis reservas asistidas del período (IS-15 con contexto de tendencia)
- Mis casos resueltos vs pendientes
- Valor total gestionado

---

## 4. Resumen de acceso por rol

| Dashboard | admin_general | admin_ventas | admin_finanzas | admin_operaciones | admin_clientes | admin_comercial | agente | pasajero |
|---|---|---|---|---|---|---|---|---|
| DB-01 Rendimiento Comercial | ✅ | ✅ | 👁 | — | — | — | — | — |
| DB-02 Control Financiero | ✅ | — | ✅ | — | — | — | — | — |
| DB-03 Disrupciones | ✅ | — | — | ✅ | — | — | — | — |
| DB-04 Diferenciador vuelos | — | — | — | — | — | — | — | ✅ |
| DB-05 Captación/Retención | ✅ | — | — | — | ✅ | — | — | — |
| DB-06 Demanda por producto | ✅ | ✅ | — | — | — | — | — | — |
| DB-07 Paquetes y carrito | ✅ | ✅ | — | — | — | — | — | — |
| DB-08 Catálogo y rutas | ✅ | ✅ | — | — | — | — | — | — |
| DB-09 Calidad soporte | ✅ | — | — | ✅ | — | — | — | — |
| DB-10 Campañas | ✅ | — | — | — | — | ✅ | — | — |
| DB-11 Asistente IA | ✅ | — | — | — | — | ✅ | — | — |
| DB-12 Alertas precio | ✅ | — | — | — | ✅ | — | — | — |
| DB-13 Productividad agente | ✅ | — | — | ✅ | — | — | ✅ propia | — |

👁 = solo lectura, sin exportar
