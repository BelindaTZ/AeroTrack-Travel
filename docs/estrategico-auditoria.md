# AeroTrack Travel — Auditoría Nivel Estratégico

> Solo auditoría. Nada de lo descrito acá fue implementado todavía.
> Fuentes: `docs/aerotrack-travel-objetivos-estrategicos.md`,
> `docs/aerotrack-travel-dashboards-spec.md`, código real en `dags/` y `app/`
> (verificado en vivo el 2026-08-07).

---

## 1.1 — Estructura de carpetas ELT actual vs. requerida

**Conteo real actual** (`datos/parquet/`):

| Carpeta | Archivos |
|---|---|
| `crudo/` | 254 |
| `procesando/` | 119 |
| `terminado/` | 213 |

**Los 5 DAGs conservan los Parquets — ninguno borra.** El flujo real
(`dags/clickhouse_client.py::mover_parquet`) usa `shutil.move`, no copia
ni borrado: cada archivo pasa físicamente de `crudo/` → `procesando/` →
`terminado/` y se queda ahí para siempre. La única excepción es un
`unlink()` puntual en la tarea `transformar()`: el archivo crudo que ya
se leyó y movió a `procesando/` se borra ahí mismo tras generar el
agregado (evita dejar basura intermedia), pero eso NO es el archivo
`crudo` original — ese ya vive intacto en `crudo/` desde que se escribió.

**El versionado por timestamp YA EXISTE**, y ya es el único nombre de
archivo que usa el código — no hay modo "sobrescribir". Patrón real:
`{tabla}_{marca}.parquet` donde `marca = datetime.now(UTC).strftime("%Y-%m-%d_%H%M%S")`.
Un detalle real encontrado en el listado de `terminado/`: hay archivos
con dos formatos de marca conviviendo — `_2026-08-02_06.parquet` (solo
hora, formato viejo) y `_2026-08-02_224717.parquet` (hora:min:seg,
formato actual). El código ACTUAL siempre genera el segundo formato; los
primeros son historial de una convención anterior que ya no se usa pero
que nadie limpió. No es un bug activo, es ruido de nombre a tener en
cuenta si se migra `terminado/` tal cual a una carpeta nueva.

**Conclusión de 1.1**: la promesa central del pedido del instructor —
"los archivos no se sobrescriben, se acumulan como historial" — **ya es
cierto hoy**, solo que repartido en 3 carpetas por etapa en vez de 3
carpetas por tipo de dato. La migración a E/L/T no resuelve un problema
de pérdida de datos que exista hoy; es un cambio de organización/semántica
de carpetas, no de comportamiento de escritura.

**Hallazgo colateral, no pedido pero relevante para Fase A**:
`procesando/` tiene 119 archivos hoy, cuando en el flujo normal (sin
fallos) debería terminar cada corrida casi vacía (los crudos se
`unlink()` ahí mismo y los agregados se mueven a `terminado/` en la
tarea `cargar`). 119 archivos acumulados sugiere corridas que fallaron
a mitad de camino (entre `transformar` y `cargar`) y dejaron huérfanos.
Vale la pena revisarlo antes o durante Fase A — si se migra tal cual a
la carpeta `L`/`T` nueva, esos huérfanos viajan con la migración.

---

## 1.2 — Estado de los 5 DAGs ELT actuales

Los 5 (`aerotrack_travel_etl_dims`, `_comercial`, `_clientes`,
`_operaciones`, `_finanzas`) comparten **exactamente el mismo patrón**
de 3 tareas (`extraer` → `transformar` → `cargar`) sobre el mismo helper
`dags/clickhouse_client.py` (`escribir_parquet`/`mover_parquet`/`insertar_df`).
Confirmado por grep sobre las 5 tasks: mismas llamadas a
`config.PARQUET_CRUDO/PROCESANDO/TERMINADO` en los 5 archivos, sin
ninguna variación estructural entre ellos.

| DAG | Carpeta que usa hoy | ¿Borra/sobrescribe? | Esfuerzo de migración |
|---|---|---|---|
| `aerotrack_travel_etl_dims` | crudo→procesando→terminado | No | **Bajo** |
| `aerotrack_travel_etl_comercial` | crudo→procesando→terminado | No | **Bajo** |
| `aerotrack_travel_etl_clientes` | crudo→procesando→terminado | No | **Bajo** |
| `aerotrack_travel_etl_operaciones` | crudo→procesando→terminado | No | **Bajo** |
| `aerotrack_travel_etl_finanzas` | crudo→procesando→terminado | No | **Bajo** |

**Por qué el esfuerzo es bajo para los 5 a la vez, no solo por DAG**:
ninguno de los 5 archivos `*_tasks.py` referencia `PARQUET_CRUDO` etc.
de forma hardcodeada con el string `"crudo"` — todos importan las
constantes desde `dags/config.py` (`config.PARQUET_CRUDO`,
`config.PARQUET_PROCESANDO`, `config.PARQUET_TERMINADO`). **El cambio de
fondo es un solo archivo**: renombrar/redefinir esas 3 constantes en
`dags/config.py` (`PARQUET_BASE_DIR / "crudo"` → `PARQUET_BASE_DIR / "E"`,
etc.) migra los 5 DAGs a la vez sin tocar ninguna línea de los 5
`*_tasks.py`. Lo único que sí exige tocar cada archivo (5 ediciones
mecánicas idénticas) es si la Fase A además decide eliminar el `unlink()`
intermedio y el `shutil.move` en favor de "escribir directo en la
carpeta final" (ver nota de ambigüedad en el veredicto de 1.5/1.6) — eso
sí toca cada `*_tasks.py` porque hoy la lógica de 3 pasos asume mover
entre 3 carpetas físicas distintas.

---

## 1.3 — Tablas estratégicas necesarias en ClickHouse

Los 4 OE del doc estratégico y los 4 dashboards DS-00 a DS-03 (OO-4.7 a
OO-4.10) se agregan sobre las 9 tablas tácticas `agg_*` que ya existen y
ya se están cargando en producción (confirmado: las 9 tienen archivos
`terminado/` recientes, hasta `2026-08-07_18:00`). No hace falta traer
dato crudo nuevo — todo lo que pide el nivel estratégico es un roll-up
de lo que el nivel táctico ya calculó.

| Tabla propuesta | Agrega | Desde (tácticas existentes) | ¿VIEW o DAG propio? |
|---|---|---|---|
| `agg_kpi_ejecutivo_mes` | Los ~8 KPIs del Balanced Scorecard (CAC no aplica — no hay dato de costo de canal, ver bloqueante abajo; tasa activación, cobertura productos, conversión global, uptime, tiempo notif., precisión risk score) por mes | `agg_conversion_busqueda_reserva`, `agg_ingresos_por_producto_mes`, `agg_segmentos_pasajero`, `agg_disrupciones_aerolinea_ruta` | **VIEW** — es un `SELECT` con joins/agregados sobre datos ya mensuales, sin cálculo que dependa de estado externo |
| `agg_oferta_producto_mes` (DS-01) | Cobertura de los 6 tipos de producto + ingresos + conversión, consolidado (no por separado como hace DB-06/DB-08) | `agg_ingresos_por_producto_mes`, `agg_conversion_busqueda_reserva` | **VIEW** |
| `agg_disrupciones_global_mes` (DS-02) | Efectividad global (no por aerolínea/ruta como DB-03) + comparación vs. benchmark BTS/FAA agregado | `agg_disrupciones_aerolinea_ruta`, `agg_otp_aerolinea_mes` | **VIEW** |
| `agg_inteligencia_automatizacion_mes` (DS-03) | Uso del asistente IA + alertas de precio + cobertura BTS/FAA, consolidado | `agg_alertas_conversion` + datos de asistente IA (**no están en ClickHouse hoy**, ver bloqueante) | **Mixto** — la parte de alertas es VIEW; la parte de asistente IA necesita el DAG nuevo de la sección 1.4/1.6 porque `mensajes_ia`/`conversaciones_ia` no tienen tabla `agg_*` en ClickHouse todavía (DB-11 los lee de MinIO operacional en vivo, no de ClickHouse — ver `docs/aerotrack-travel-dashboards-spec.md` sección DB-11: "Tablas: MinIO operacional") |

**Regla general que sale de esto**: donde el dashboard estratégico
consolida tablas `agg_*` que YA son mensuales, alcanza con una `VIEW`
de ClickHouse (sin DAG nuevo, sin latencia de carga adicional, siempre
al día porque lee en tiempo de consulta). Donde el dashboard estratégico
necesita un dato que el nivel táctico todavía lee de MinIO operacional
en vivo (asistente IA, campañas — DB-10/DB-11 en la tabla de la sección
3 del spec dicen `Tablas: MinIO operacional`, no ClickHouse), no hay
nada que agregar con una VIEW porque no existe la tabla base — ahí sí
hace falta un DAG nuevo que primero cree el agregado táctico que falta.

**BLOQUEANTE real para `agg_kpi_ejecutivo_mes` (CAC digital, OE-1)**:
el indicador clave de OE-1 es "Costo de Adquisición del Cliente (CAC)
digital" — costo por canal de marketing. Revisado el esquema completo
de `docs/aerotrack-travel-dashboards-spec.md` y las 9 tablas `agg_*`
existentes: **no hay ninguna tabla, columna, ni colección de MinIO/
PocketBase con costo real de campaña o canal** (`agg_conversion_busqueda_reserva`
tiene volumen, no costo). El indicador de la fila 1 del Balanced
Scorecard, tal como está definido hoy, no se puede calcular con datos
reales del sistema — haría falta o (a) un campo de costo por campaña
que hoy no existe en `campanas_email`/cupones, o (b) resolver con el
usuario que ese KPI se muestre con dato simulado/manual hasta que exista
esa fuente. Esto no bloquea Fase B completa (las otras 3 tablas
propuestas sí son viables 100% con datos reales), pero sí bloquea
completar el cockpit de OO-4.7 (DS-00, "los KPIs más críticos de los 4
OEs en una sola vista") tal como está redactado en el doc de objetivos.

---

## 1.4 — DAG de IA: preparación

**Clave de API — SÍ hay, dos de hecho**, confirmadas en `.env`:
`GEMINI_API_KEY` y `GROQ_API_KEY`. Ambas reales (no placeholders).

**Cliente de IA reutilizable — SÍ existe**: `app/asistente_ia/integrations/llm_client.py`
(`GroqGeminiLLMClient`), Groq primero con fallback a Gemini, mismo
patrón de dos proveedores que describe `fuentes_datos_externas` para el
resto de integraciones externas del sistema. Es reutilizable tal cual
para narrativa de dashboards, no hace falta escribir un cliente nuevo.

**Gotcha real que sí bloquea usarlo hoy tal cual**: `GroqGeminiLLMClient`
NO lee `.env` — lee `configuracion_sistema` en PocketBase (claves
`groq.api_key` / `gemini.api_key`), y **confirmado que ninguna de las
dos está sembrada ahí** (ni siquiera `scripts/bootstrap_configuracion_sistema.py`
las incluye — ese script solo siembra Stripe/AviationStack/Gmail/SMTP).
Si el DAG de IA de la semana que viene llama a `GroqGeminiLLMClient` tal
cual, va a fallar con `CredencialNoConfigurada` aunque las claves existan
en `.env`, porque nunca llegaron a la tabla que el cliente realmente lee.

Dos formas de resolverlo, ninguna implementada todavía:
1. Agregar `groq.api_key`/`gemini.api_key` a `bootstrap_configuracion_sistema.py`
   (mismo patrón que las otras 4 integraciones) — el DAG entonces puede
   reusar `GroqGeminiLLMClient` sin cambios.
2. El DAG de Airflow lee `.env` directo (mismo patrón que `dags/config.py`
   ya usa con `load_dotenv`) y llama Gemini/Groq con su propio cliente
   HTTP delgado, sin pasar por `app/`.

La opción 1 es más consistente con "una sola puerta al LLM" (mismo
criterio documentado en el propio `llm_client.py`); la opción 2 evita
que el DAG dependa de que `app-travel` esté levantada. Recomiendo 1,
pero es una decisión de diseño para confirmar en Fase B/C, no algo que
bloquee la auditoría.

**Costo estimado del DAG de IA nuevo**: bajo. Ya existe el patrón
completo de "DAG delgado que llama a un endpoint interno de la app"
(`dag_estimar_riesgo_disrupcion.py`, reescrito el 2026-07-25 exactamente
con ese patrón) — el DAG de narrativa sería la misma forma: un endpoint
interno nuevo (`/internal/asistente_ia/narrativa-estrategica` o similar)
que arme el prompt con los datos de las tablas/VIEWs de la sección 1.3
y llame `GroqGeminiLLMClient.generar()`, más un DAG de 1-2 tareas que lo
dispare. No hay trabajo de infraestructura pendiente (Airflow, red,
credenciales de conexión) — todo el cableado (Airflow↔app-travel,
`APP_TRAVEL_URL` en `dags/config.py`) ya existe y se usa hoy para
`dag_estimar_riesgo_disrupcion`.

---

## 1.5 — Criterio

**¿La migración de crudo/procesando/terminado a E/L/T rompe algo que
esté funcionando?** No. Confirmado con evidencia directa: los 13
dashboards tácticos (`app/dashboards/services/*.py`) leen **ClickHouse**
(`app/shared/clickhouse_client.py::query_dicts`, contra las tablas
`agg_*` ya cargadas) y, donde la spec pide granularidad diaria que
ClickHouse no tiene, **MinIO operacional en vivo** (ej. `comercial_service.py`
mezcla ambas fuentes a propósito, documentado en su propio docstring).
**Ningún dashboard, service, ni router de `app/` lee `datos/parquet/`
directamente** (confirmado por grep: cero referencias a rutas de
Parquet fuera de `dags/`). La carpeta de Parquet es una zona de tránsito
interna del pipeline ETL — un espacio de trabajo entre Airflow y
ClickHouse, invisible para la capa de aplicación. Renombrar/reorganizar
esas carpetas es 100% transparente para los dashboards tácticos y para
cualquier código de `app/`.

**¿Los DB-01 a DB-13 leen Parquet o ClickHouse?** ClickHouse (+ MinIO
operacional para los casos de granularidad diaria ya documentados en la
spec). Ver arriba — esto confirma que la migración de carpetas no los
afecta.

**Orden recomendado**: las 3 fases son mayormente independientes entre
sí, con una sola dependencia real:

- **Fase A (migración de carpetas) y Fase B (tablas estratégicas) SÍ
  pueden ir en paralelo.** Fase A es un cambio de infraestructura interna
  del pipeline (nombres de carpeta en `dags/config.py`), Fase B es
  agregar VIEWs/DAGs sobre tablas `agg_*` tácticas que ya existen y ya
  se cargan — ninguna depende de que la otra termine primero.
- **Fase C (dashboards DS-00 a DS-03) depende de que Fase B tenga, como
  mínimo, las VIEWs/tablas listas** — no tiene sentido construir la UI
  de un dashboard que consulta una tabla que todavía no existe. Fase C
  no depende de Fase A en absoluto (mismo argumento que arriba: los
  dashboards leen ClickHouse, no Parquet).
- El DAG de IA (sección 1.4) puede prepararse en paralelo a las 3 fases
  — solo necesita que exista el endpoint interno y la credencial
  sembrada, no depende de que DS-00 a DS-03 tengan UI todavía (la
  narrativa se integra a los dashboards en la semana siguiente, según
  el pedido original).

**Recomendación concreta de orden**: A y B en paralelo; C arranca en
cuanto B entrega la primera VIEW (no hace falta esperar las 4); DAG de
IA se prepara (endpoint + credencial sembrada) en paralelo a A/B, sin
activar el schedule hasta que C tenga al menos un dashboard real donde
mostrar la narrativa.

---

## 1.6 — Plan de implementación en 3 fases

### Fase A — Migrar carpetas y DAGs al patrón E/L/T con versionado

1. Confirmar con el usuario el mapeo semántico final de las 3 letras
   (ver nota de ambigüedad abajo) antes de tocar código.
2. Editar `dags/config.py`: redefinir `PARQUET_CRUDO`/`PARQUET_PROCESANDO`/
   `PARQUET_TERMINADO` (o renombrar las constantes mismas) a las 3
   carpetas nuevas bajo `datos/` — punto único de cambio, migra los 5
   DAGs sin tocar sus `*_tasks.py`.
3. Decidir qué pasa con los 254+119+213 archivos ya existentes en
   `crudo/procesando/terminado`: ¿se mueven a las carpetas nuevas
   (preservando historial) o se dejan como archivo muerto y las carpetas
   nuevas arrancan vacías? Afecta directamente si el "historial" que
   pide el instructor incluye lo ya corrido esta semana o solo lo que
   se genere de acá en adelante.
4. Limpiar los 119 archivos huérfanos de `procesando/` (hallazgo de 1.1)
   antes de migrar, para no arrastrar basura a la carpeta nueva.
5. Si se decide además eliminar el paso de "mover entre 3 carpetas
   físicas" en favor de "escribir directo en su carpeta final" (esto sí
   cambia el comportamiento, no es solo un rename) — tocar los 5
   `*_tasks.py` para que cada tarea escriba directo en `E`/`L`/`T` en
   vez de mover.
6. Probar los 5 DAGs con `airflow dags test` (mismo método ya usado en
   sesiones anteriores para no gastar cuota de nada, esto no consume
   ninguna API externa).

**Ambigüedad a resolver con el usuario antes de empezar Fase A** (no es
un bloqueante técnico, es una decisión de nombres/orden pendiente): el
pedido original definía `E/T/L` con `L =`"listos para insertar en
ClickHouse", y la nota final del pedido corrige el orden a `E/L/T`. Pero
el proceso real de los 5 DAGs hoy es Extraer → **Transformar** → Cargar
(el agregado pasa por `procesando/` antes de llegar a `terminado/`/
ClickHouse) — no hay ningún paso de "cargar a MinIO" dentro de este
pipeline específico (los datos ya están en MinIO antes de que el DAG
arranque, escritos por la app en operación normal, no por este ETL).
Antes de tocar `dags/config.py` en el paso 2 de arriba, confirmar cuál
de estas dos lecturas es la correcta:
- **(a)** las 3 letras nombran carpetas en el orden real del código
  (`E`=extraído, `T`=transformado/agregado, `L`=cargado/insertado) —
  solo cambia el nombre de carpeta, no el orden interno de las tareas.
- **(b)** el orden E-L-T describe un concepto distinto (aterrizar crudo
  en un "lago" antes de transformar, patrón ELT clásico) que no aplica
  literal a este pipeline porque no hay paso de carga a MinIO acá
  dentro — en ese caso `L` necesitaría redefinirse como otra cosa (¿una
  copia espejo de lo que ya está en MinIO operacional al momento de la
  extracción?) que hoy no existe en el código.

Recomiendo (a): es la lectura que no requiere inventar un paso nuevo y
preserva el comportamiento ya probado en producción, solo renombra.

### Fase B — Tablas estratégicas en ClickHouse + DAGs de agregación

1. Crear las VIEWs de `agg_kpi_ejecutivo_mes` (parcial, sin CAC — ver
   bloqueante 1.3), `agg_oferta_producto_mes`, `agg_disrupciones_global_mes`
   sobre las tablas tácticas ya existentes.
2. Resolver con el usuario el bloqueante de CAC digital (dato simulado
   temporal vs. postergar ese KPI específico del cockpit DS-00).
3. Para `agg_inteligencia_automatizacion_mes` (DS-03): como el asistente
   IA no tiene tabla `agg_*` en ClickHouse hoy (DB-11 lee MinIO en vivo),
   crear primero el agregado táctico que falta (mismo patrón que los
   otros 5 DAGs `etl_*`) antes de poder construir la vista estratégica
   sobre él — es trabajo adicional no listado en el spec original de
   dashboards tácticos.
4. Probar las VIEWs contra ClickHouse real (mismo puerto/credenciales ya
   configurados, `localhost:9004`).

### Fase C — Dashboards DS-00 a DS-03 con drill-down

1. DS-01/DS-02 (dependen solo de VIEWs sobre tablas ya existentes)
   pueden implementarse primero.
2. DS-00 (cockpit, OO-4.7) al final porque depende de que las otras 3
   VIEWs existan y del acuerdo sobre el KPI de CAC.
3. DS-03 depende del DAG táctico nuevo de asistente IA (Fase B, punto 3).
4. Drill-down estratégico→táctico (OO-4.11): confirmar con el usuario si
   es un link simple a la URL del dashboard táctico correspondiente
   (más simple, reutiliza el backoffice existente) o si necesita pasar
   filtros de contexto (período, producto) de forma explícita entre
   ambos niveles — no está especificado en el doc de objetivos ni en el
   spec de dashboards, vale la pena aclararlo antes de construir la UI.

---

## Resumen de bloqueantes y decisiones pendientes

| # | Tipo | Detalle |
|---|---|---|
| 1 | Decisión de nombres (no bloquea Fase A técnicamente, pero definir antes de tocar código) | Mapeo real de E/L/T — ver Fase A, opción (a) recomendada |
| 2 | BLOQUEANTE parcial (Fase B/C, KPI específico) | CAC digital (OE-1) no tiene fuente de dato real en el sistema hoy |
| 3 | Decisión de alcance (Fase B) | `agg_inteligencia_automatizacion_mes` necesita un DAG táctico nuevo para asistente IA que no estaba en el spec original de dashboards |
| 4 | Gotcha de credenciales (DAG de IA, sección 1.4) | `GroqGeminiLLMClient` lee `configuracion_sistema`, no `.env` — hay que sembrar las claves ahí o el DAG usa su propio cliente delgado |
| 5 | Limpieza recomendada antes de migrar (Fase A) | 119 archivos huérfanos en `procesando/`, más el ruido de 2 formatos de timestamp distintos en `terminado/` |

---

**¿Está correcto este plan?** Antes de empezar con Fase A necesito
confirmación sobre el punto 1 (mapeo E/L/T) y una decisión sobre el
punto 2 (CAC) y el punto 5 (qué hacer con los archivos ya acumulados).
