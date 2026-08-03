# Auditoría ETL + ClickHouse + Dashboards — AeroTrack Travel (2026-08-02)

> Fase 1 del encargo "Implementación ETL + ClickHouse + Dashboards". Solo
> auditoría — no se escribió código. Fuente de verdad revisada primero,
> completa: `docs/aerotrack-travel-dashboards-spec.md` (13 dashboards, 10
> tablas ClickHouse, arquitectura de pipeline).

---

## 1. Estado actual de ClickHouse

**Conexión:** exitosa, sin errores. `clickhouse-travel` está arriba y
`healthy` (`docker ps`), puerto 8123 HTTP responde con las credenciales de
`.env` (`CLICKHOUSE_TRAVEL_USER`/`CLICKHOUSE_TRAVEL_PASSWORD`).

**Hallazgo importante — nombre de base de datos no coincide:**
- El spec dice: `CREATE DATABASE IF NOT EXISTS aerotrack_travel;`
- La base real configurada en `.env`/`docker-compose.yml` es
  **`aerotrack_travel_analitico`** (`CLICKHOUSE_TRAVEL_DB=aerotrack_travel_analitico`).
- Verificado en vivo: `aerotrack_travel` **no existe** como base de datos
  (`EXISTS DATABASE aerotrack_travel` → `0`). Solo existe
  `aerotrack_travel_analitico` (vacía).

| Ítem | Estado |
|---|---|
| Base de datos `aerotrack_travel` (nombre del spec) | ❌ No existe |
| Base de datos `aerotrack_travel_analitico` (nombre real en `.env`) | ✅ Existe, **0 tablas** |
| Las 10 tablas `agg_*` del spec | ❌ Ninguna existe |
| Datos cargados | N/A — no hay tablas |

**Decisión requerida antes de Fase A:** usar `aerotrack_travel_analitico`
(ya configurada, cero fricción) o migrar `.env`/`docker-compose.yml` al
nombre `aerotrack_travel` del spec. Recomiendo lo primero — ver sección 4.

---

## 2. Estado actual de los DAGs ETL

**Búsqueda exhaustiva en `dags/*.py` (26 archivos):** ningún DAG, tarea ni
import menciona `clickhouse` (0 coincidencias). No existe ninguno de los 5
DAGs `aerotrack_travel_etl_*` del spec.

**Estructura `Parquet/crudo/procesando/terminado`:** no existe en ninguna
forma — ni como carpeta en el repo, ni como volumen Docker montado (grep
sobre `docker-compose.yml` sin coincidencias), ni referenciada en código.
El único volumen de `airflow-scheduler-travel` es `./dags:/opt/airflow/dags`
(+ `logs`, `plugins`) — no hay un volumen para datos intermedios todavía.

**Driver de ClickHouse:** `_PIP_ADDITIONAL_REQUIREMENTS` del scheduler
(`docker-compose.yml`) instala `requests pandas pyarrow minio python-dotenv
docker` — **no incluye ningún cliente de ClickHouse** (`clickhouse-connect`
o `clickhouse-driver`). Hace falta agregarlo antes de que cualquier DAG
pueda escribir a ClickHouse.

**DAGs Travel existentes y relevancia como base:**

| DAG | Qué hace | Reutilizable para el ETL nuevo |
|---|---|---|
| `aerotrack_travel_sync_dims` (`aerotrack_travel_sync_dag.py`) | Dispara el ELT completo del proyecto hermano `minio-elt` y sincroniza el modelo dimensional BTS/FAA resultante a `aerotrack-travel-dims` | **Sí, indirectamente** — es la fuente de los Parquets `agg_otp_aerolinea_mes`/`agg_causas_retraso_mes`/`agg_otp_dia_semana` que el DAG `etl_dims` del spec necesita sincronizar a ClickHouse. No se toca, solo se lee lo que ya deja en MinIO. |
| `dag_estimar_riesgo_disrupcion.py` (dispara `disrupciones_tasks.py`) | Ya lee `agg_otp_aerolinea_mes` y `agg_causas_retraso_mes` desde `aerotrack-travel-dims` con `read_parquet()` para estimar riesgo por aerolínea | **Sí, como patrón de referencia** — es el único código Travel que ya lee estos Parquets; confirma que el join por `codigo_iata`/`carrier` funciona en producción (ya lo usé en IS-11, `riesgo_estimado_por_aerolinea()`). |
| `catalogo_vuelos_tasks.py` | Lee `dim_ruta` de dims para enriquecer el catálogo de vuelos generado | Mismo patrón `read_parquet`, otro precedente de lectura de dims. |
| `dag_publicar_catalogo_minio.py` | Publica NDJSON de PocketBase a `aerotrack-travel-catalog` (bucket distinto, no dims) | No aplica al ETL de ClickHouse, pero es el patrón de referencia para el `extraer→transformar→cargar` de 3 tareas que pide el spec (mismo patrón de 3 pasos, distinto destino). |

**Conclusión:** no hay nada que migrar ni romper — el ETL de ClickHouse
parte de cero, pero hay dos patrones de código ya probados en producción
para reutilizar (lectura de dims Parquet, DAG de 3 tareas extraer/
transformar/cargar).

---

## 3. Estado de los datos fuente en MinIO

### 3.1 — Colecciones operacionales (`aerotrack-travel-operational`, vía `minio_operational_client`)

Primer hallazgo: **varios nombres del encargo no son los nombres reales**
de la colección — confirmado contra las constantes `ENTIDAD_*` de cada
repositorio (la misma discrepancia que ya se documentó para IS-12/IS-13 en
`informes-simples-auditoria.md`):

| Nombre en el encargo | Nombre real | Registros | ¿Alcanza para agregación mensual útil? |
|---|---|---|---|
| `reservas` | `reservas` | **18** | ⚠️ Muy poco — ver 3.3 |
| `reserva_items` | `reserva_items` | **13** | ⚠️ Solo 2 de 5 tipos de producto presentes (9 hotel, 4 vuelo — **0** auto/actividad/crucero) |
| `facturas` | `facturas` | 12 | ⚠️ Poco |
| `pagos` | `pagos` | 14 | ⚠️ Poco |
| `comisiones` | `comisiones` | 26 | OK para un período |
| `remesas` | `remesas` | 1 | ❌ Insuficiente |
| `pasajeros` | `pasajeros` | 128 | ✅ Suficiente para segmentación |
| `disrupciones` | `disrupciones` | 327 | ✅ Volumen alto, **pero el 100% está en estado `activa`** (0 resueltas) |
| `vuelos_monitoreo` | **no existe** — es `vuelos_catalogo` (PocketBase) filtrado a programado/retrasado/desviado, sin campo `risk_score` guardado | 631 vuelos en catálogo | ⚠️ Ver 4 — el riesgo se calcula en vivo, no está persistido |
| `mensajes_ia` | `mensajes_ia` | 26 | ⚠️ Poco para "top 15 temas" |
| `conversaciones_ia` | `conversaciones_ia` | 13 | ⚠️ Poco |
| `cupones_descuento` | `cupones_descuento` (PocketBase, catálogo) — el **uso/canje** real es `cupones_uso` (MinIO) | 1 cupón definido / **0 usos** | ❌ 0 canjes registrados hoy |
| `suscriptores_newsletter` | `newsletter_suscripciones` | **0** | ❌ Vacía |
| `campanas_email` | `campanas_email` (PocketBase) | **0** | ❌ Vacía |
| `favoritos` | `favoritos` | 8 | ⚠️ Poco pero ya usado en IS-23 |
| `alertas_precio` | `alertas_precio` | 1 | ❌ Insuficiente |
| `tickets_soporte` | `casos_escalados` | 2 | ❌ Insuficiente |

Adicional, no pedido explícitamente pero necesario para el funnel de
conversión de DB-01/06/07/08:
- `carritos`: 145 (131 convertido / 11 abandonado / 3 activo) — volumen
  decente, pero **no hay un estado "checkout iniciado"** distinto de
  "activo"/"convertido" — el KPI `total_checkouts` del funnel no tiene una
  fuente directa 1:1, habría que aproximarlo (p. ej. carritos con al menos
  un intento de pago registrado) o reinterpretar la etapa.
- `busquedas_recientes`: 16 filas, con `pasajero_id`/`tipo_producto`/
  `fecha` — es la única fuente posible para `total_busquedas`, pero es un
  log de "búsquedas recientes del pasajero" (uso de UI), no
  necesariamente un evento de analítica completo — falta confirmar si se
  poda/limita por pasajero (afectaría el conteo real de búsquedas).

### 3.2 — Concentración temporal de los datos (hallazgo crítico para "trend charts")

```
reservas por mes (fecha_reserva):  2026-07: 12 · 2026-08: 4 · 2020-01: 2 (datos de prueba residuales)
pagos por mes:                      2026-07: 6  · 2026-08: 8
facturas por mes:                   2026-07: 4  · 2026-08: 8
pasajeros por mes (created):        2026-07: 128 (100% en un solo mes — alta de seed masivo)
```

Todos los datos operacionales reales están concentrados en **2 meses**
(julio-agosto 2026), la mayoría de un solo día de siembra masiva. Los
"últimos 6 períodos"/"últimas 8 semanas" que piden varios gráficos de
tendencia del spec (DB-01, DB-02, DB-05, DB-06, DB-07, DB-09, DB-11) van a
mostrar 1-2 puntos con datos reales y el resto en cero — no es un defecto
del ETL, es que el proyecto no tiene meses de uso orgánico acumulado.

### 3.3 — Nota sobre volatilidad de estos números

Los conteos de arriba son un snapshot, no una base estable: la suite de
tests de este proyecto corre contra la **misma base compartida** (no hay
entorno de test aislado, ver memoria del proyecto) y varios tests crean y
borran reservas/pagos/pasajeros reales en cada corrida. El número real
fluctúa corrida a corrida — lo estructural (qué colecciones existen, qué
tan concentrados están los datos en el tiempo, qué tipos de producto están
sub-representados) sí es estable y es lo que importa para este análisis.

### 3.4 — Parquets BTS/FAA en `aerotrack-travel-dims`

Todos los objetos que necesita el spec **existen y tienen datos reales**:

| Parquet | Filas | Columnas reales | ¿Coincide con el esquema ClickHouse del spec? |
|---|---|---|---|
| `agg_otp_aerolinea_mes.parquet` | 936 | `carrier, year, month, total_vuelos, vuelos_a_tiempo, total_vuelos_todos, total_cancelados, otp_pct, delay_avg` | ⚠️ **No exactamente** — el spec pide `(periodo, aerolinea_codigo, origen, destino, ...)`, o sea granularidad **por ruta**; el Parquet real solo agrega por **aerolínea+mes** (nacional, sin ruta). Ver 4.4. |
| `agg_causas_retraso_mes.parquet` | 936 | `carrier, year, month, carrierdelay, weatherdelay, nasdelay, securitydelay, lateaircraftdelay` | ⚠️ El spec pide `(periodo, origen, destino, causa, total_casos, ...)` con una fila por causa — el Parquet real trae las 5 causas como columnas por aerolínea+mes, sin ruta. Transformación directa (pivotar columnas → filas) + falta la dimensión ruta. |
| `agg_otp_dia_semana.parquet` | **7** | `day_of_week, total_vuelos, vuelos_a_tiempo, otp_pct` | ⚠️ Solo 7 filas totales (una por día de semana, **agregado global**) — el spec pide `(origen, destino, dia_semana, ...)` por ruta. El Parquet real no tiene esa granularidad. |
| `agg_rutas_eficiencia.parquet` (no está en el spec, pero existe) | **45,057** | `origin, dest, carrier, year, total_vuelos, vuelos_a_tiempo, tiempo_real_avg, tiempo_prog_avg, retraso_prom, otp_pct, indice_eficiencia` | Esta es la única fuente con granularidad **ruta + aerolínea**, pero es **anual** (`year`), no mensual, y no está en el esquema ClickHouse del spec. |

**Los códigos de aerolínea (`carrier`/IATA) sí calzan** con
`aerolineas.codigo_iata` de la app — ya verificado en producción (IS-11,
`riesgo_estimado_por_aerolinea()` usa exactamente este join hoy).

**Fuente cruda disponible si hace falta re-agregar:** `fact_vuelo.parquet`
(67 MB, el hecho a nivel de vuelo individual) existe y en teoría permite
generar cualquier combinación de granularidad (ruta × aerolínea × mes ×
día de semana) — pero es un archivo pesado para reprocesar en cada corrida
horaria; ver recomendación en 4.4.

---

## 4. Mi criterio técnico

### 4.1 — ¿Falta alguna tabla de agregación que los dashboards necesitarán?

- **`agg_funnel_carrito` o similar** — el spec reutiliza
  `agg_conversion_busqueda_reserva` para DB-01/06/07/08, pero como se
  explicó en 3.1, `total_checkouts` no tiene una fuente 1:1 clara en los
  datos actuales (`carritos` solo distingue activo/abandonado/convertido).
  No es una tabla nueva, es un vacío de **definición**: hay que decidir
  qué evento operacional cuenta como "checkout" antes de escribir el ETL
  comercial.
- **Nada relacionado a `agg_otp_aerolinea_mes`/`agg_otp_dia_semana` con
  granularidad de ruta** — no es que falte una tabla, es que las 3 tablas
  de dims del spec asumen una granularidad (`origen, destino`) que el
  Parquet fuente real no tiene. Ver 4.4 para la recomendación concreta.
- El spec no define ninguna tabla de agregación para DB-13
  (Productividad del Agente) — dice explícitamente "Tablas: MinIO
  operacional (reservas, tickets_soporte)", igual que DB-10/DB-11. Está
  bien así (no toda tabla necesita pasar por ClickHouse), solo lo marco
  para que quede explícito en el plan de Fase B: DB-10/11/13 **no**
  necesitan DAG de ETL a ClickHouse, se consultan en vivo contra MinIO
  igual que los WorkPanels/informes simples ya construidos.

### 4.2 — ¿Alguna colección fuente no tiene suficientes datos?

Sí, varias — resumen de las más críticas (detalle completo en tabla 3.1):

| Colección | Registros | Problema |
|---|---|---|
| `campanas_email` | 0 | DB-10 saldría completamente vacío |
| `newsletter_suscripciones` | 0 | Ídem |
| `cupones_uso` | 0 | "Cupones canjeados del período" de DB-10 sería siempre 0 |
| `remesas` | 1 | Insuficiente para cualquier tendencia |
| `alertas_precio` | 1 | DB-12 (dashboard completo dedicado a esto) tendría casi nada que mostrar |
| `reserva_items` (por tipo) | 13, solo 2 de 5 tipos | DB-06/DB-07 mostrarían auto/actividad/crucero en cero |
| `articulo_calificaciones` | 0 | Afecta parte de DB-09 |

Esto no bloquea construir el pipeline ni el esquema — pero si se generan
capturas de pantalla o demo de los 13 dashboards con los datos de hoy,
al menos 3 (DB-10, DB-12, y parcialmente DB-07) se van a ver vacíos o casi
vacíos. Vale la pena decidir ahora si eso es aceptable para la entrega o
si hace falta sembrar más datos demo antes de Fase C.

### 4.3 — ¿El pipeline crudo/procesando/terminado tiene sentido?

Es más infraestructura de la que el volumen real de datos justifica (18
reservas, 26 comisiones... esto cabe en memoria sin ningún problema), pero
es un requisito explícito del instructor, así que lo implementaría tal
cual — con dos ajustes que sí importan independientemente del volumen:

1. **Necesita un volumen Docker persistente**, no un directorio dentro del
   contenedor del scheduler — hoy `airflow-scheduler-travel` no tiene
   ningún volumen para datos (solo `dags/logs/plugins`), así que
   cualquier archivo en `Parquet/crudo/` se perdería al recrear el
   contenedor. Agregar algo como `./data/parquet:/opt/airflow/data/parquet`.
2. **Necesita una política de retención** — corriendo `@hourly`, sin poda
   la carpeta `terminado/` crece indefinidamente. Con el volumen de datos
   actual el peso es irrelevante, pero es buena práctica dejarlo resuelto
   desde el inicio (p. ej. limpiar `crudo/`+`procesando/` al final de cada
   corrida exitosa, conservar solo N corridas en `terminado/`).

No creo que valga la pena proponer una variación "más limpia" que se
salte el pipeline de 3 carpetas — es un requisito explícito, no una
decisión de arquitectura abierta.

### 4.4 — ¿Qué dashboard es difícil de implementar con los datos actuales?

**DB-04 (Diferenciador Analítico de Vuelos, vista del pasajero) es el más
difícil**, por un problema real de granularidad de datos, no de código:
pide OTP de una ruta específica **por mes** (12 meses, estacionalidad) y
ranking de aerolíneas **en esa ruta**. Ninguna de las 3 tablas de dims
existentes tiene esa combinación exacta:
- `agg_otp_aerolinea_mes` tiene mes, no tiene ruta.
- `agg_rutas_eficiencia` tiene ruta, no tiene mes (solo año).
- `agg_otp_dia_semana` es un agregado global de 7 filas, no tiene ruta.

**Recomendación:** en vez de forzar el esquema ClickHouse del spec
(`agg_otp_aerolinea_mes` con columnas `origen`/`destino` que el Parquet no
trae), lo más honesto es regenerar estas 3 tablas desde `fact_vuelo.parquet`
(67 MB, pero es un job que corre `@daily`, no `@hourly` — tiempo de sobra)
con la granularidad completa que pide el spec. Es más trabajo en el DAG
`etl_dims`, pero evita tener una tabla ClickHouse con columnas
`origen`/`destino` vacías o inventadas.

**DB-01/DB-06/DB-07/DB-08 (comercial/demanda/paquetes/catálogo) son el
segundo grupo difícil**, no por el esquema sino por volumen real (sección
3.2/3.3): con 18 reservas y 13 ítems en 2 tipos de producto de 5, varios
KPIs y gráficos van a mostrar series casi planas o con huecos. El pipeline
va a funcionar correctamente — el problema es de contenido, no de
ingeniería.

**DB-10 (Campañas) es directamente inviable hoy**: sus 3 colecciones base
(`campanas_email`, `newsletter_suscripciones`, `cupones_uso`) están en 0.

### 4.5 — ¿Falta algún dashboard para algún rol sin ninguno?

Revisando la tabla de acceso del spec (sección 4) contra los roles reales
del sistema (`scripts/seed_roles_departamento.py`): **`admin_ti` es el
único rol departamental sin ningún dashboard asignado** — ni siquiera
`👁` de solo lectura. Los otros 6 roles departamentales (ventas,
finanzas, operaciones, clientes, comercial) y agente/pasajero tienen al
menos uno.

No necesariamente es un vacío que haya que llenar — el trabajo de
admin_ti en este proyecto es seguridad/auditoría/integraciones, más
operativo que analítico-táctico, y ya tiene su propio informe (IS-02, log
de auditoría). Lo marco como observación, no como recomendación firme de
agregar un DB-14: si se agrega, el candidato natural sería algo como
"Salud de integraciones y cuota de APIs externas" (ya hay datos reales en
`sincronizaciones_log`/sección IS-03), pero no lo incluiría en el alcance
de esta entrega salvo que el usuario lo pida explícitamente.

---

## 5. Plan propuesto de implementación (3 fases)

### Fase A — Schema ClickHouse + pipeline base

1. **Decidir el nombre de la base** (`aerotrack_travel` del spec vs.
   `aerotrack_travel_analitico` ya configurada) — recomiendo mantener
   `aerotrack_travel_analitico` y ajustar el `CREATE DATABASE` del spec,
   en vez de tocar `.env`/`docker-compose.yml` (ya está en uso por otros
   servicios, menor riesgo).
2. Crear las 10 tablas `agg_*` del spec — con el ajuste de columnas
   `origen`/`destino` en las 3 tablas de dims (4.4), sea agregando esas
   columnas de verdad (recalculando desde `fact_vuelo`) o quitándolas del
   esquema si se decide no perseguir esa granularidad todavía.
3. Agregar `clickhouse-connect` a `_PIP_ADDITIONAL_REQUIREMENTS` del
   scheduler de Airflow.
4. Crear el volumen Docker para `Parquet/crudo|procesando|terminado/` y la
   política mínima de retención (4.3).
5. Un script/DAG de smoke test: escribe un Parquet dummy, lo mueve por las
   3 carpetas, inserta 1 fila en una tabla ClickHouse — confirma que el
   pipeline conecta de punta a punta antes de escribir los 5 DAGs reales.

### Fase B — DAGs ETL por área

Orden recomendado, de menor a mayor riesgo/dependencias:

1. **`aerotrack_travel_etl_dims`** primero — es el más simple (copia
   Parquet→ClickHouse casi sin transformar, salvo el ajuste de 4.4), no
   depende de que las otras áreas ya tengan datos, y desbloquea a DB-03/04
   que son los dashboards con más volumen de datos reales hoy (327
   disrupciones, dims con miles de filas).
2. **`aerotrack_travel_etl_finanzas`** — colecciones ya maduras en el
   proyecto (pagos/facturas/comisiones/remesas ya tienen sus propios
   informes simples IS-18/19/20/21 probados), lógica de agregación más
   directa.
3. **`aerotrack_travel_etl_operaciones`** — depende de `disrupciones`
   (327 filas, buen volumen) pero necesita definir de dónde sale
   `agg_satisfaccion_soporte` (la colección real es `casos_escalados`,
   solo 2 filas hoy — puede quedar con datos mínimos a propósito).
4. **`aerotrack_travel_etl_comercial`** — es el que más decisiones de
   diseño pendientes tiene (definición de "checkout" del funnel, sección
   4.1) y el que menos volumen de datos reales tiene hoy; dejarlo para
   cuando ya haya patrón probado de los 3 anteriores.
5. **`aerotrack_travel_etl_clientes`** — al final, mismo motivo: pocos
   datos (128 pasajeros pero 1 sola cohorte temporal) y depende del mismo
   patrón de segmentación que ya se puede validar con datos de comercial.

### Fase C — Dashboards

Construir en el orden en que sus datos ya son sólidos, no en el orden del
spec:

1. **DB-03 (Disrupciones)** primero — 327 registros reales, el rol
   admin_operaciones ya tiene el resto de su backoffice completo (IS-11,
   13, 16 de la sesión anterior), y las tablas de dims (`agg_otp_aerolinea_mes`)
   ya están probadas en código (`riesgo_service.py`).
2. **DB-02 (Control Financiero)** — datos financieros son los más
   completos y ya auditados (IS-18 a IS-21).
3. **DB-04 (Diferenciador de vuelos, pasajero)** — una vez resuelta la
   granularidad de ruta×mes (4.4), es autocontenido y no depende de datos
   operacionales delgados, solo de dims (que están completos).
4. **DB-05 (Captación/Retención)** — 128 pasajeros es la colección más
   grande después de dims/disrupciones.
5. **DB-01, DB-06, DB-07, DB-08** (comercial/ventas) — juntos, porque
   comparten tablas ClickHouse y el mismo problema de datos delgados
   (4.4) — mejor evaluarlos como grupo una vez que haya más reservas
   demo, no uno a la vez.
6. **DB-09, DB-13** (soporte/productividad) — datos mínimos pero ya
   probados en informes simples (IS-13, IS-15/16).
7. **DB-11 (Asistente IA)** — 26 mensajes/13 conversaciones, alcanza para
   una demo aunque no para tendencias robustas.
8. **DB-10, DB-12** al final — con los datos de hoy (0 y 1 registro
   respectivamente) no hay nada que mostrar; requieren sembrar datos demo
   antes de que valga la pena construir la UI.

---

## IMPORTANTE — antes de Fase A

Preguntas abiertas que necesito que confirmes antes de tocar código:

1. ¿`aerotrack_travel_analitico` (ya configurada) o migrar a
   `aerotrack_travel` (nombre del spec)?
2. ¿Cómo definimos "checkout" para el funnel de conversión, dado que
   `carritos` no tiene ese estado intermedio?
3. ¿Reprocesar `fact_vuelo.parquet` (67 MB) para dar granularidad
   ruta×mes a las 3 tablas de dims, o ajustar el esquema ClickHouse a la
   granularidad que ya existe (aerolínea×mes, sin ruta)?
4. ¿Vale la pena sembrar más datos demo (sobre todo campañas/newsletter/
   cupones/alertas de precio, hoy en 0-1 registros) antes de Fase C, o
   seguimos con lo que hay?
