# Plan de Implementación — Reservas

**Módulo:** Reservas
**Prefijo:** RES
**Spec:** [`reservas-spec.md`](./reservas-spec.md)
**Código fuente:** `app/reservas/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Gestionar el ciclo de vida completo de una reserva: creación (autoservicio/asistida), modificación, cancelación, consulta de estado, alertas de precio y expiración automática. Es el módulo con más dependencias cruzadas del sistema — orquesta la verificación de cupo de Vuelos y dispara el cobro/reembolso de diferencia de tarifa en Facturación. Cubre 7 RF, 2 RNF y 6 RN sobre 9 CU (CU-O21–O26, O44, y las contrapartes RN de O45/O47).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5; cliente PocketBase para `reservas`, `reserva_pasajeros`, `reserva_extras`, `alertas_precio`; scheduler para el proceso de expiración automática (CU-O44) — Airflow o un scheduler ligero interno (APScheduler), a decidir en Fase 5 de este plan si la constitución no lo fija explícitamente.
**Almacenamiento:** PocketBase — este módulo es dueño de 4 colecciones; consume `tarifas_vuelo`/`vuelos_catalogo` (Vuelos) y `pagos`/`reembolsos` (Facturación) por integración de servicio, no por escritura directa.
**Pruebas:** pytest + `httpx.AsyncClient`; prueba de concurrencia para RN-RES-001 (verificación de cupo) y prueba de condición de carrera para RN-RES-005 (pago vs. expiración).
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose.
**Tipo de proyecto:** servicio web + proceso automático por temporizador.
**Objetivos de rendimiento:** confirmación de reserva no debe exceder el tiempo de verificación de cupo + creación de registro (<1s combinado, alineado con RNF-SEG-002 de login como referencia de UX de autoservicio).
**Restricciones:** ninguna reserva puede confirmarse sin cupo verificado (RN-RES-001); ningún pago exitoso puede quedar sin reserva o reembolso asociado (RN-RES-005, idempotencia REG-D1).
**Escala/alcance:** módulo núcleo transaccional — 7 RF, más interdependencias que ningún otro módulo (Seguridad, Pasajeros, Vuelos, Facturación, Disrupciones).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-D1 (idempotencia) | Sí | RN-RES-005 — prueba explícita de la condición de carrera pago/expiración (QP-04) |
| REG-G1/G2 (autoservicio, transparencia de precio) | Sí | RF-RES-001 muestra precio antes de confirmar; RNF-RES-001 revalida precio si cambió |
| REG-A2 (indirecta) | Sí | Este módulo nunca escribe sobre el modelo heredado; solo consume el servicio de cupo de Vuelos |
| REG-B1/B4 (RBAC/auditoría) | Sí, en CU-O22 | Reserva asistida incluye verificación RBAC (CU-O43) |
| REG-J10/J11 (navegación, feedback) | Sí | Checkout multi-paso preserva estado ante reautenticación; confirmaciones destructivas (cancelar) exigen paso separado |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/reservas/
├── reservas-spec.md
├── plan.md
└── checklist.md
```

### Código fuente

```text
app/reservas/
├── __init__.py
├── router_reservas.py        # RF-RES-001, 002, 003, 004, 005
├── router_backoffice.py      # RF-RES-002 (asistida)
├── router_alertas.py         # RF-RES-006
├── schemas.py
├── services/
│   ├── crear_reserva_service.py     # RF-RES-001, 002 — invoca cupo_service de Vuelos (RN-RES-001)
│   ├── modificar_reserva_service.py # RF-RES-003 — dispara diferencia de tarifa (RN-RES-002)
│   ├── cancelar_reserva_service.py  # RF-RES-004
│   ├── expiracion_service.py        # RF-RES-007 (CU-O44), ejecutado por scheduler
│   └── alertas_precio_service.py    # RF-RES-006
├── repositories/
│   └── pocketbase_client.py
├── templates/
│   ├── checkout.html, modificar_reserva.html, detalle_reserva.html
│   └── backoffice/reserva_asistida.html
└── tests/
    ├── test_crear_reserva.py
    ├── test_modificar_reserva.py
    ├── test_cancelar_reserva.py
    ├── test_expiracion.py            # incluye QP-04 (pago vs. expiración)
    └── test_alertas_precio.py
```

**Decisión de estructura:** ningún servicio de este módulo accede directamente a `tarifas_vuelo.cupos_disponibles` — siempre a través de `cupo_service` de `app/vuelos/services`, y ningún servicio inserta directamente en `pagos`/`reembolsos` — siempre a través del servicio equivalente de `app/facturacion/services`.

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo |
|---|---|
| `reservas` | Dueño |
| `reserva_pasajeros`, `reserva_extras` | Dueño |
| `alertas_precio` | Dueño |
| `tarifas_vuelo` | Lectura/decremento vía servicio externo (Vuelos) |
| `pasajeros` | Lectura (Pasajeros) |
| `pagos`, `reembolsos` | Escritura vía servicio externo (Facturación), nunca directa |

---

## Contratos de API

- `POST /reservas`, `POST /backoffice/reservas`, `PUT /reservas/{id}`, `POST /reservas/{id}/cancelar`, `GET /reservas/{id}` — RF-RES-001 a 005.
- `POST /alertas-precio` — RF-RES-006.
- `POST /internal/reservas/expirar-pendientes` — RF-RES-007.

---

## Fases de implementación

### Fase 1 — Crear reserva autoservicio (RF-RES-001)
**Precondición externa:** Vuelos Fase 2/3 completas (búsqueda + verificación de cupo); Seguridad Fase 1 (sesión); Pasajeros Fase 1 no requerida aún.
**Entregable:** `crear_reserva_service.py`, `router_reservas.py` (POST).

### Fase 2 — Crear reserva asistida (RF-RES-002)
**Precondición externa:** Seguridad Fase 2 (RBAC) completa.
**Entregable:** `router_backoffice.py`.

### Fase 3 — Expiración automática (RF-RES-007, CU-O44)
**Precondición externa:** Fase 1 completa (necesita reservas `pendiente_pago` reales para probar).
**Entregable:** `expiracion_service.py` + configuración del scheduler.
**Nota de secuencia:** se implementa antes que Facturación complete su Fase de pago, para poder escribir la prueba de condición de carrera (QP-04) desde el lado de Reservas apenas Facturación esté lista.

### Fase 4 — Consultar estado y alertas de precio (RF-RES-005, 006)
**Precondición externa:** ninguna adicional.
**Entregable:** endpoints de solo lectura/creación simple.

### Fase 5 — Modificar y cancelar reserva (RF-RES-003, 004)
**Precondición externa:** Facturación Fase de reembolso (CU-O37) y de diferencia de tarifa (CU-O47) completas — esta fase dispara ambas.
**Entregable:** `modificar_reserva_service.py`, `cancelar_reserva_service.py`.
**Nota de secuencia:** deliberadamente al final — es la fase con más dependencias externas (Vuelos para revalidar cupo, Facturación para diferencia/reembolso).

---

## Ajuste de alcance tras inspección del repo (Pasajeros y Facturación no existen todavía)

Este plan asume Pasajeros y Facturación completas (`facturacion-spec.md` para CU-O32/O37/O47, gestión completa de pasajeros para CU-O22). Ninguna de las dos existe en esta sesión — están deliberadamente fuera de alcance. Las 9 colecciones de este módulo (`reservas`, `reserva_pasajeros`, `reserva_extras`, `alertas_precio`) ya existen en PocketBase (creadas en una sesión anterior, mismo patrón que Vuelos/Seguridad). Ajustes concretos:

- **Pasajero titular, no acompañantes.** `reserva_pasajeros.pasajero_id` es una relación a `pasajeros` (no datos inline) — cada pasajero en una reserva debe ya tener cuenta propia. Sin una pantalla de búsqueda de pasajeros (pertenece a Pasajeros), esta sesión resuelve el titular como el propio `pasajeros` del usuario autenticado (autoservicio) o del pasajero que el Agente identifica por correo (asistida). Agregar acompañantes adicionales (varios `reserva_pasajeros` por reserva) queda fuera de esta sesión — se retoma cuando exista una búsqueda de pasajeros real.
- **Pago real no existe.** RF-RES-001 termina en "dirige al pasajero al pago" — sin Facturación, el destino es la propia pantalla de detalle de la reserva (`GET /reservas/{id}`), que muestra `pendiente_pago` con una nota explícita de que el cobro real se conecta cuando exista Facturación. Se introduce `services/pago_stub_service.py` (no estaba en el plan original): expone `confirmar_pago_reserva(reserva_id)`, el punto de integración que el futuro webhook de Stripe de Facturación invocará. Permite implementar y probar de verdad RN-RES-005 (QP-04, la condición de carrera pago-vs-expiración) sin necesitar Stripe — es el mecanismo real, con un disparador simulado en vez de uno real.
- **CU-O47 (diferencia de tarifa) y el reembolso de CU-O24 quedan como puntos de integración documentados, no simulados.** Igual que Vuelos documentó `"notificacion": "pendiente_de_modulo_disrupciones"` en vez de fingir un disparo real, `modificar_reserva_service`/`cancelar_reserva_service` calculan el monto exacto de la diferencia/reembolso y lo registran en el detalle de auditoría como `"pendiente_de_modulo_facturacion"`, sin inventar una llamada a un servicio que no existe.
- **Scheduler de CU-O44:** se usa Airflow (ya en el stack, mismo patrón que Vuelos), no APScheduler — un DAG delgado en `dags/` llama por HTTP a `POST /internal/reservas/expirar-pendientes`, cuya lógica real vive y se prueba dentro de `app/reservas/services/expiracion_service.py`.

## Complexity Tracking

*No aplica.*
