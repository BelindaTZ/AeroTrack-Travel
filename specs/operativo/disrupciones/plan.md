# Plan de Implementación — Disrupciones y Notificaciones

**Módulo:** Disrupciones y Notificaciones
**Prefijo:** DIS
**Spec:** [`disrupciones-spec.md`](./disrupciones-spec.md)
**Código fuente:** `app/disrupciones/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Detectar cambios operativos sobre vuelos con reservas confirmadas, vía dos fuentes en paralelo (API de estado de vuelo real y monitoreo de bandeja de correo), y notificar al pasajero de forma confiable, con precedencia/deduplicación entre fuentes, degradación ordenada y reintento ante fallo de envío. Es el módulo que materializa el diferenciador de negocio. Cubre 6 RF y 3 RNF sobre 6 CU (CU-O27–O31, O46).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5; cliente PocketBase para `disrupciones`, `notificaciones`; SDK de la API de estado de vuelo elegida (AviationStack o AeroDataBox, REG-I7); Gmail API (OAuth, REG-I6) para el monitor de correo; cliente de envío de email/SMS (proveedor abstraído detrás de una interfaz, REG-F1); scheduler (Airflow o equivalente) para los ciclos periódicos de CU-O27/O28.
**Almacenamiento:** PocketBase — dueño de `disrupciones` y `notificaciones`; lee `vuelos_catalogo` (Vuelos) y `reservas` (Reservas); credenciales de las integraciones en `configuracion_sistema` (REG-B3).
**Pruebas:** pytest + mocks de la API externa y de Gmail API; prueba dedicada de degradación (RNF-DIS-001) simulando caída de la API real; prueba de precedencia/deduplicación (RN-DIS-002) con dos fuentes simultáneas.
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose; jobs periódicos vía Airflow.
**Tipo de proyecto:** servicio web + procesos automáticos periódicos.
**Objetivos de rendimiento:** timeout y reintento configurables por integración, nunca espera indefinida (RNF-DIS-002).
**Restricciones:** el peor caso normal (API disponible) nunca depende de que la degradación E3 se dispare (RNF-DIS-001) — este es un requisito de diseño explícito, no solo de manejo de errores.
**Escala/alcance:** 6 RF, dos integraciones externas reales, motor de precedencia entre 3 fuentes (incluyendo la futura fuente estadística del nivel Estratégico).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-E1 (ninguna disrupción sin notificar) | Sí | RF-DIS-004 es el único punto de generación de `notificaciones`; toda disrupción detectada pasa por él |
| REG-E2 (precedencia/deduplicación) | Sí | RN-DIS-002 implementada como función pura testeable de forma aislada |
| REG-E3 (degradación ordenada) | Sí | RNF-DIS-001 — prueba explícita de caída de API con fallback a fuente estadística, sin fallo silencioso |
| REG-F1/F2/F3 (integraciones reemplazables, timeouts, aislamiento) | Sí | Cliente de API de estado de vuelo y Gmail API detrás de interfaces abstractas; timeouts leídos de `configuracion_sistema` |
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales OAuth de Gmail y API key de estado de vuelo solo en `configuracion_sistema`/variables de entorno |
| REG-J7 (estado nunca solo por color) | Sí | Banner de disrupción y notificación siempre combinan color + ícono + texto |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/disrupciones/
├── disrupciones-spec.md
├── plan.md
└── checklist.md
```

### Código fuente

```text
app/disrupciones/
├── __init__.py
├── router_notificaciones.py     # RF-DIS-005
├── schemas.py
├── services/
│   ├── api_estado_vuelo_service.py   # RF-DIS-001 (CU-O27), degradación (RNF-DIS-001)
│   ├── monitor_correo_service.py     # RF-DIS-002 (CU-O28)
│   ├── deteccion_service.py          # RF-DIS-003 (CU-O29), aplica RN-DIS-001
│   ├── notificacion_service.py       # RF-DIS-004 (CU-O30), aplica RN-DIS-002/003
│   └── reintento_service.py          # RF-DIS-006 (CU-O46), aplica RN-DIS-006
├── integrations/
│   ├── flight_status_client.py        # abstracción sobre AviationStack/AeroDataBox
│   ├── gmail_client.py                # abstracción sobre Gmail API
│   └── notification_sender.py         # abstracción sobre email/SMS
├── repositories/
│   └── pocketbase_client.py
├── dags/
│   ├── consultar_estado_vuelo_dag.py  # ciclo periódico de RF-DIS-001
│   └── monitorear_correo_dag.py       # ciclo periódico de RF-DIS-002
├── templates/
│   └── historial_notificaciones.html
└── tests/
    ├── test_api_estado_vuelo.py       # incluye simulación de caída (QP-01)
    ├── test_monitor_correo.py         # incluye correo sin reserva asociada (QP-07)
    ├── test_notificacion.py           # incluye precedencia/deduplicación (QP-02) y tipo cancelación (QP-12)
    └── test_reintento.py              # incluye agotamiento de reintentos (QP-09)
```

**Decisión de estructura:** cada integración externa vive detrás de una interfaz en `integrations/`, nunca invocada directamente desde `services/` sin pasar por esa capa — es el mecanismo concreto que satisface REG-F1 (toda integración externa es reemplazable).

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo |
|---|---|
| `disrupciones` | Dueño |
| `notificaciones` | Dueño |
| `vuelos_catalogo` | Escritura vía servicio externo (Vuelos, RF-VUE-004), nunca directa desde aquí |
| `reservas` | Lectura (Reservas) — determina a quién notificar |
| `configuracion_sistema` | Lectura — credenciales y política de timeout/reintento |

---

## Contratos de API

- `POST /internal/disrupciones/consultar-api`, `POST /internal/disrupciones/monitorear-correo` — RF-DIS-001, 002/003 (jobs periódicos).
- `POST /internal/notificaciones/enviar`, `POST /internal/notificaciones/{id}/reintentar` — RF-DIS-004, 006.
- `GET /notificaciones`, `GET /backoffice/notificaciones` — RF-DIS-005.

---

## Fases de implementación

### Fase 1 — Consultar API de estado de vuelo real, con degradación (RF-DIS-001)
**Precondición externa:** Vuelos Fase 4 (actualización de estado) completa, para poder disparar la escritura real.
**Entregable:** `api_estado_vuelo_service.py`, `flight_status_client.py`, prueba de degradación (RNF-DIS-001).

### Fase 2 — Monitor de correo y detección (RF-DIS-002, 003)
**Precondición externa:** ninguna adicional a Fase 1.
**Entregable:** `monitor_correo_service.py`, `gmail_client.py`, `deteccion_service.py` con RN-DIS-001.

### Fase 3 — Notificar al pasajero (RF-DIS-004)
**Precondición externa:** Fases 1 y 2 completas (converge ambas fuentes); Reservas Fase 1 completa (necesita reservas confirmadas reales).
**Entregable:** `notificacion_service.py` con RN-DIS-002 (precedencia) y RN-DIS-003 (reembolso condicionado).

### Fase 4 — Reintento de envío fallido (RF-DIS-006)
**Precondición externa:** Fase 3 completa.
**Entregable:** `reintento_service.py`.

### Fase 5 — Historial de notificaciones (RF-DIS-005)
**Precondición externa:** Fase 3 completa; Seguridad Fase 2 (RBAC) para la vista de backoffice.
**Entregable:** `router_notificaciones.py`.

---

## Complexity Tracking

*No aplica.*
