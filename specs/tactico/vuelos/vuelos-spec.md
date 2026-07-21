# Especificación Táctica — Vuelos (catálogo)

**Módulo:** Vuelos (catálogo)
**Prefijo:** VUE
**Código fuente:** `app/vuelos/` *(nivel Operativo ya implementado y probado — ver `specs/operativo/vuelos/`; 20/20 tests reales pasando)*
**Casos de uso cubiertos:** CU-T06 (Configurar parámetros del catálogo de vuelos), CU-T07 (Monitorear estado del DAG de catálogo y alertar si falla), CU-T08 (Ver reporte de rutas más buscadas y tasa de conversión), CU-T39 (Configurar recargo y proporción de asientos premium), CU-T40 (Configurar ventana de check-in gratuito), CU-T41 (Configurar rotación de cuota de clase de cabina)
**Actor:** Administrador

> **Estado:** nivel nuevo, sin código propio todavía. **Dos grupos con estado muy distinto:** CU-T06/T07/T08 configuran/monitorean el catálogo ya implementado (CU-O19, en producción); CU-T39/T40/T41 configuran la funcionalidad de asientos/cabina (CU-O114–O117, `specs/operativo/vuelos/`) que **todavía no está implementada** — estos 3 son precondición real de esa fase Operativa pendiente, no solo un complemento.

---

## Funcionalidad 1: Configurar parámetros del catálogo de vuelos (CU-T06)

*(Generalizado en parte por CU-T37, Integraciones — no lo reemplaza, ver nota ahí.)*

### RF-VUE-T01 — Configurar parámetros del catálogo de vuelos
El sistema debe permitir a un Administrador configurar rutas prioritarias, frecuencia de actualización y número de resultados del catálogo — hoy son parámetros del proceso Airflow (`dags/dag_generar_catalogo_vuelos.py`) sin panel de edición; este CU es la primera UI real para ajustarlos sin tocar el DAG directamente.

---

## Funcionalidad 2: Monitorear estado del DAG de catálogo (CU-T07)

### RF-VUE-T02 — Monitorear estado del DAG de catálogo de vuelos y alertar si falla
El sistema debe mostrar a un Administrador el estado de las últimas corridas del DAG de generación de catálogo (`dag_generar_catalogo_vuelos.py`), y alertar (visualmente en el dashboard, como mínimo) cuando una corrida falla. Complementa a CU-T38 (Integraciones), que ya generaliza esta bitácora — CU-T07 puede reutilizar `sincronizaciones_log` en vez de una fuente separada, ver Dependencias.

---

## Funcionalidad 3: Ver reporte de rutas más buscadas (CU-T08)

### RF-VUE-T03 — Ver reporte de rutas más buscadas y tasa de conversión búsqueda → reserva
El sistema debe mostrar a un Administrador las rutas más buscadas (`busquedas_recientes`, retrofit pendiente — ver nota en `cuenta-mis-viajes-spec.md`) y su tasa de conversión a reserva real, filtrable por período. Filtros instantáneos (REG-J9).

---

## Funcionalidad 4: Configurar asientos premium (CU-T39)

**Precondición real de CU-O116/O117** (`specs/operativo/vuelos/`, no implementados todavía).

### RF-VUE-T04 — Configurar recargo y proporción de asientos premium por tipo de avión
El sistema debe permitir a un Administrador configurar, por tipo de avión (`avion_modelo`), el recargo de un asiento premium y la proporción de filas marcadas como premium al generar `asientos_vuelo` (`configuracion_sistema.disponibilidad_asientos.recargo_premium`/`.pct_filas_premium`).

---

## Funcionalidad 5: Configurar ventana de check-in gratuito (CU-T40)

**Precondición real de CU-O117** (asignación automática de asiento).

### RF-VUE-T05 — Configurar ventana de check-in gratuito para selección de asiento estándar
El sistema debe permitir a un Administrador configurar cuántas horas antes del vuelo se abre la selección gratuita de asiento estándar para tarifas Light (`configuracion_sistema.disponibilidad_asientos.horas_antes_checkin_gratis` — confirmado por el cliente: 24-48h antes, con la salvedad de que para entonces los mejores asientos ya suelen estar ocupados).

---

## Funcionalidad 6: Configurar rotación de cuota de clase de cabina (CU-T41)

**Precondición real de CU-O114** (ver y seleccionar clase de cabina).

### RF-VUE-T06 — Configurar qué rutas/clases de cabina se sincronizan con datos reales de precio
El sistema debe permitir a un Administrador configurar la rotación de qué rutas/clases de cabina se refrescan cada día contra Google Flights (cuota compartida de 250/mes con `precio_base`/`predicciones_precio_ruta`) — mismo mecanismo de rotación que ya usa el catálogo base de vuelos, extendido para decidir prioridad quándo refrescar Business/First vs. Economy.

---

## Reglas de negocio

- **RN-VUE-T01** — *(Funcionalidad 2)* CU-T07 reutiliza `sincronizaciones_log` (Integraciones) cuando esté disponible, en vez de un log paralelo — evita duplicar la bitácora.
- **RN-VUE-T02** — *(Funcionalidad 3)* La tasa de conversión relaciona búsquedas reales (`busquedas_recientes`) con reservas reales (`reserva_items`), nunca una aproximación sin ambos datos reales.
- **RN-VUE-T03** — *(Funcionalidades 4-6)* Los valores de estas 3 configuraciones tienen un default documentado en código (ya usado por Operativo con fallback) hasta que este nivel Táctico se implemente — implementarlas no es opcional para que CU-O114–O117 salgan de estado "pendiente".

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/vuelos/config-catalogo` | Cookie JWT (Admin), rutas prioritarias, frecuencia, número de resultados | Configuración actualizada |
| `GET /backoffice/vuelos/estado-dag` | Cookie JWT (Admin) | HTML/JSON con últimas corridas y alertas de fallo |
| `GET /backoffice/vuelos/reporte-rutas` | Cookie JWT (Admin), filtro de período | HTML/JSON con rutas más buscadas y conversión |
| `GET/POST /backoffice/vuelos/config-asientos` | Cookie JWT (Admin), recargo/proporción por tipo de avión | Configuración actualizada |
| `GET/POST /backoffice/vuelos/config-checkin` | Cookie JWT (Admin), horas antes del vuelo | Configuración actualizada |
| `GET/POST /backoffice/vuelos/config-rotacion-cabina` | Cookie JWT (Admin), reglas de rotación | Configuración actualizada |

---

## Historias de usuario

- **HU-VUE-T01:** Como administrador, quiero configurar los parámetros del catálogo de vuelos desde una UI, para no depender de editar el DAG directamente.
- **HU-VUE-T02:** Como administrador, quiero ver el estado del DAG de catálogo y ser alertado si falla, para reaccionar rápido.
- **HU-VUE-T03:** Como administrador, quiero ver qué rutas se buscan más y cuántas convierten, para decidir dónde enfocar esfuerzo comercial.
- **HU-VUE-T04:** Como administrador, quiero configurar el recargo de asientos premium por tipo de avión, para ajustar la estrategia de precio de asientos.
- **HU-VUE-T05:** Como administrador, quiero configurar la ventana de check-in gratuito, para replicar las políticas reales de la industria.
- **HU-VUE-T06:** Como administrador, quiero configurar qué rutas/clases se refrescan con datos reales de precio, para optimizar el uso de la cuota compartida de Google Flights.

---

## Objetivo

Dar al Administrador control operativo sobre el catálogo de vuelos ya en producción, y — de forma crítica — las 3 configuraciones que son precondición real para que la funcionalidad de asientos/cabina (Operativo, pendiente) pueda implementarse con parámetros reales en vez de valores hardcodeados.

---

## Escenarios

### Camino feliz
1. Un Administrador ajusta la frecuencia de actualización del catálogo (CU-T06) y confirma que el DAG sigue corriendo sano (CU-T07).
2. Consulta el reporte de rutas más buscadas (CU-T08) para decidir dónde reforzar oferta.
3. Configura el recargo de asientos premium (CU-T39), la ventana de check-in (CU-T40) y la rotación de clase de cabina (CU-T41) — estos 3 valores quedan listos para cuando se implemente CU-O114–O117.

### Manejo de errores
- **DAG con corrida fallida:** se muestra la alerta visual, sin bloquear el resto del dashboard.
- **Reporte de rutas sin datos de `busquedas_recientes`:** mensaje claro, mientras el retrofit pendiente (ver `cuenta-mis-viajes-spec.md`) no exista.

---

## Criterios de aceptación

- **CU-T06:** Dado que un Administrador edita los parámetros del catálogo, cuando los guarda, entonces el siguiente ciclo del DAG los usa.
- **CU-T07:** Dado que una corrida del DAG falla, cuando el Administrador consulta el estado, entonces ve la alerta correspondiente.
- **CU-T08:** Dado que existen búsquedas y reservas reales en el período, cuando el Administrador consulta el reporte, entonces ve rutas ordenadas por búsquedas con su tasa de conversión.
- **CU-T39/T40/T41:** Dado que un Administrador configura cada uno de estos 3 valores, cuando los guarda, entonces quedan disponibles para que CU-O114–O117 (Operativo, cuando se implemente) los use en vez de un default hardcodeado.

---

## Dependencias

- **Vuelos (Operativo):** CU-T06/T07 configuran/monitorean CU-O19 ya implementado; CU-T39/T40/T41 son precondición de CU-O114–O117 (pendientes).
- **Integraciones:** CU-T07/T38 pueden compartir la misma bitácora (`sincronizaciones_log`) — coordinar para no duplicar.
- **Cuenta/Mis Viajes:** CU-T08 depende del retrofit de `busquedas_recientes` documentado ahí.
- **Reservas:** CU-T08 depende de `reserva_items` para medir conversión real.

---

## Casos de uso relacionados

- CU-O19 (Generar catálogo, Operativo) — consumidor de CU-T06.
- CU-O114–O117 (Clase de cabina y asientos, Operativo, pendientes) — consumidores directos de CU-T39/T40/T41.
- CU-T37, T38 (Integraciones) — generalizan/coexisten con CU-T06/T07.

---

## Fuera de alcance

- Edición directa del código del DAG desde la UI — CU-T06 configura parámetros que el DAG lee, nunca su lógica.
- Alertas por canal externo (email/Slack) cuando el DAG falla — CU-T07 es visibilidad en el dashboard, no un sistema de alertas proactivas (mismo criterio que Integraciones, CU-T38).
