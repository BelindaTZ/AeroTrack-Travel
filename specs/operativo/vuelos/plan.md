# Plan de Implementación — Vuelos (catálogo)

**Módulo:** Vuelos (catálogo)
**Prefijo:** VUE
**Spec:** [`vuelos-spec.md`](./vuelos-spec.md)
**Código fuente:** `app/vuelos/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Sostener el catálogo operativo de vuelos: generación automática desde el modelo dimensional heredado (solo lectura), búsqueda/detalle para el pasajero, actualización de estado, verificación atómica de cupo (mecanismo consumido por Reservas), y una vía excepcional de backoffice (CU-O48) para forzar el estado de un vuelo con fines de demo. Cubre 6 RF, 3 RNF y 6 RN sobre 5 CU (CU-O17–O20, O45, O48) — **implementados y probados**, salvo el filtro completo de CU-O17 (solo aerolínea). Ampliado en el catálogo v3.1 con CU-O51/O52/O53/O114–O117 (RF-VUE-007 a 013, sección "Extensión pendiente" abajo) — ninguno implementado todavía.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5 (REG-I2); cliente PocketBase para `vuelos_catalogo`, `tarifas_vuelo`, `niveles_tarifa`, `aerolineas`, `politicas_reembolso`; cliente de lectura sobre el modelo dimensional heredado en MinIO/Parquet (`dim_ruta`, `dim_aeropuerto`, `dim_aerolinea`, `dim_avion`) — solo lectura (REG-A2); Apache Airflow (heredado, REG-I8) como orquestador de CU-O19/CU-O20 en producción.
**Almacenamiento:** PocketBase (colecciones propias) + MinIO/Parquet (solo lectura).
**Pruebas:** pytest + `httpx.AsyncClient`; prueba de concurrencia dedicada para RF-VUE-005 (decremento atómico de cupo).
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose; DAGs de Airflow en el contenedor heredado.
**Tipo de proyecto:** servicio web + jobs automáticos (Airflow).
**Objetivos de rendimiento:** verificación/decremento de cupo como operación atómica sin ventana de lectura intermedia (RNF-VUE-003).
**Restricciones:** ningún proceso de este módulo escribe sobre `dim_*`/`agg_*`/`fact_vuelo` (REG-A2); CU-O48 nunca se ejecuta como parte del flujo automático de producción (RN-VUE-006).
**Escala/alcance:** 6 RF, dueño de 5 colecciones PocketBase, consumidor de 4 tablas heredadas.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-A1/A2 (solo lectura del modelo heredado) | Sí | `dims_reader.py` expone únicamente métodos de consulta; sin métodos de escritura en su interfaz |
| REG-G2 (transparencia de precio) | Sí | RF-VUE-002 muestra precio final y política de reembolso completos antes de reservar |
| REG-J9 (filtros instantáneos / combobox) | Sí | RF-VUE-001 — filtros secundarios instantáneos; combobox de aerolínea/aeropuerto si >8 opciones |
| REG-B1/B4 (RBAC/auditoría) | Sí, solo para CU-O48 | RF-VUE-006 incluye `<<include>>` CU-O41/O42/O43 igual que cualquier acción de Administrador |
| REG-F2/F3 (resiliencia) | Indirecta | No aplica integración externa directa en este módulo (la API de estado de vuelo es dueña de Disrupciones) |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/vuelos/
├── vuelos-spec.md
├── plan.md
└── checklist.md
```

### Código fuente

```text
app/vuelos/
├── __init__.py
├── router_busqueda.py        # RF-VUE-001, 002
├── router_backoffice.py      # RF-VUE-006 (CU-O48, excepcional)
├── schemas.py
├── services/
│   ├── estado_service.py     # RF-VUE-004 — punto de escritura genérico de `vuelos_catalogo.estado`
│   ├── cupo_service.py       # RF-VUE-005 — único punto de decremento atómico de `tarifas_vuelo.cupos_disponibles`
│   └── forzar_estado_service.py  # RF-VUE-006 — marca origen manual/demo (RN-VUE-005), exige motivo (RN-VUE-006)
├── repositories/
│   └── dims_reader.py         # consultas específicas de Vuelos (resolver aeropuerto legible) sobre app/shared/minio_dims_reader.py
├── templates/
│   ├── buscar_vuelos.html, detalle_vuelo.html
│   └── backoffice/forzar_estado.html
└── tests/
    ├── test_busqueda.py
    ├── test_cupo_service.py       # incluye prueba de concurrencia (RNF-VUE-003)
    ├── test_estado_service.py
    └── test_forzar_estado.py      # incluye caso sin motivo (RN-VUE-006) y caso sin RBAC
```

**Ajuste de estructura tras inspección del repo (no estaba visible al escribir la primera versión de este plan):** RF-VUE-003 (generación de catálogo, CU-O19/O30) y la mitad de RF-VUE-004 (transición automática `programado`→`completado` por horario vencido, CU-O31) **ya están implementadas y en producción** como el DAG de Airflow `aerotrack_travel_catalogo_vuelos` (`dags/dag_generar_catalogo_vuelos.py` + `dags/catalogo_vuelos_tasks.py` + `dags/minio_dims_reader.py`), con corridas reales ya registradas (`logs/dag_id=aerotrack_travel_catalogo_vuelos/...`) y 150 `vuelos_catalogo`/450 `tarifas_vuelo` ya poblados. Esto sigue el mismo patrón que el proyecto anterior (DAGs viven en `./dags` en la raíz, montado por Airflow vía `docker-compose.yml`, **no** dentro de `app/`, que es un contenedor distinto sin Airflow). En consecuencia:
- No se reescribe `catalogo_service.py` ni el DAG — Fase 1 de este plan pasa a ser de **verificación**, no de construcción.
- `estado_service.py` (Fase 4) se construye de todas formas: expone la escritura *genérica* de `vuelos_catalogo.estado` que necesita CU-O48 (Fase 5, dentro de `app/vuelos/`, un proceso distinto al de Airflow) — la transición automática por horario vencido sigue viviendo en el DAG existente, sin refactorizar (no está roto, no se toca).
- El lector de solo lectura del modelo dimensional se separa en dos capas para evitar duplicar la lógica de MinIO+Parquet entre el contenedor de Airflow y el de la app: `app/shared/minio_dims_reader.py` (mecánica genérica de lectura Parquet, sin pandas — usa `pyarrow` directo para no cargar una dependencia pesada innecesaria) + `app/vuelos/repositories/dims_reader.py` (consulta específica: resolver `AirportCode` → nombre legible, RNF-VUE-001). El `dags/minio_dims_reader.py` existente no se modifica ni se importa desde `app/` (son builds/contenedores distintos, `Dockerfile` de la app no copia `dags/`).

**Decisión de estructura:** `cupo_service.py` es el único punto de acceso a `tarifas_vuelo.cupos_disponibles` desde cualquier módulo — Reservas lo invoca vía import directo o llamada interna, nunca accede a la colección directamente, para no romper la atomicidad garantizada aquí. La atomicidad se implementa con un lock en memoria por `tarifa_id` (`asyncio.Lock`), suficiente porque `app-travel` corre como una sola instancia/proceso en este despliegue (ver nota de escalabilidad en `cupo_service.py`); si el despliegue pasara a múltiples réplicas, este mecanismo debe migrar a un lock distribuido o a una operación atómica a nivel de base de datos.

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo |
|---|---|
| `vuelos_catalogo` | Dueño |
| `tarifas_vuelo` | Dueño — incluye `cupos_disponibles`, decremento atómico |
| `niveles_tarifa`, `politicas_reembolso` | Dueño (catálogo de referencia) |
| `aerolineas` | Dueño (catálogo operativo, distinto de `dim_aerolinea`) |
| `dim_ruta`, `dim_aeropuerto`, `dim_aerolinea`, `dim_avion` | Lectura (heredado, MinIO/Parquet) |

---

## Contratos de API

- `GET /vuelos/buscar`, `GET /vuelos/{id}` — RF-VUE-001, 002.
- `POST /internal/vuelos/generar-catalogo` (Airflow) — RF-VUE-003.
- `POST /internal/vuelos/{id}/estado` — RF-VUE-004.
- `POST /internal/tarifas/{id}/verificar-cupo` — RF-VUE-005.
- `POST /backoffice/vuelos/{id}/forzar-estado` — RF-VUE-006 (CU-O48, excepcional).

---

## Fases de implementación

### Fase 1 — Generación de catálogo (RF-VUE-003)
**Precondición externa:** acceso de lectura al modelo dimensional heredado configurado.
**Entregable:** `catalogo_service.py`, `dims_reader.py`, DAG de Airflow.

### Fase 2 — Búsqueda y detalle (RF-VUE-001, 002)
**Precondición externa:** Fase 1 completa (necesita catálogo poblado para probar de forma realista).
**Entregable:** `router_busqueda.py` con filtros instantáneos (REG-J9).

### Fase 3 — Verificación de cupo (RF-VUE-005)
**Precondición externa:** ninguna adicional; es el servicio que Reservas consumirá — debe completarse antes de que `reservas-spec.md` inicie su Fase de creación de reserva.
**Entregable:** `cupo_service.py` con prueba de concurrencia explícita.

### Fase 4 — Actualización de estado (RF-VUE-004)
**Precondición externa:** ninguna; expone el punto de escritura que `disrupciones-spec.md` consumirá.
**Entregable:** `estado_service.py`.

### Fase 5 — Ajuste puntual excepcional para demo (RF-VUE-006, CU-O48)
**Precondición externa:** Seguridad Fase 2 (RBAC/auditoría) completa; Fase 4 de este módulo completa (reutiliza `estado_service.py` internamente).
**Entregable:** `router_backoffice.py`, `forzar_estado_service.py`. **Se implementa al final, deliberadamente** — es la única funcionalidad de este módulo sin contraparte en el flujo de negocio normal, y no debe bloquear ninguna fase de la que dependen Reservas/Disrupciones.

---

## Extensión pendiente — catálogo v3.1 (2026-07-18, no iniciada)

- **Fase 6 (futura) — Filtros completos de búsqueda (RF-VUE-007, CU-O53):** completar `vuelos_repo.py` con escalas/equipaje/horario/duración y ordenamiento. Sin dependencias externas nuevas.
- **Fase 7 (futura) — Predicción de precio (RF-VUE-008, CU-O51):** nueva colección `predicciones_precio_ruta`, job de cálculo propio sobre `price_insights` de Google Flights.
- **Fase 8 (futura) — Risk score en detalle (RF-VUE-009, CU-O52):** solo lectura de `vuelos_catalogo.risk_score`/`risk_score_fuente` — depende de que Disrupciones implemente CU-O83 primero (quien escribe esos campos).
- **Fase 9 (futura) — Clase de cabina, mapa y selección de asiento (RF-VUE-010 a 013, CU-O114–O117):** la más grande de las pendientes — nueva tabla `asientos_vuelo`, campo `tarifas_vuelo.clase_cabina`, generación del mapa junto con el job de catálogo (Fase 1), y coordinación con `reservas-spec.md` (`reserva_pasajeros.asiento_id`) para RF-VUE-012. Requiere también `configuracion_sistema.disponibilidad_asientos` (categoría nueva del dbml v3).

Ninguna tiene tareas desglosadas todavía — se planean cuando se agende la implementación.

## Complexity Tracking

*No aplica.*
