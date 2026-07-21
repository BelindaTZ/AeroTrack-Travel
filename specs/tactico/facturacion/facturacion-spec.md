# Especificación Táctica — Facturación

**Módulo:** Facturación
**Prefijo:** FAC
**Código fuente:** `app/facturacion/` *(nivel Operativo ya implementado y probado — ver `specs/operativo/facturacion/`)*
**Casos de uso cubiertos:** CU-T22 (Ver dashboard financiero), CU-T23 (Generar reporte de ingresos por período y tipo de producto)
**Actor:** Administrador

> **Estado:** nivel nuevo, sin código propio todavía. Ambos CU son vistas agregadas sobre datos ya generados por Facturación Operativo (`pagos`, `comisiones`, `remesas`, `facturas`) — ninguno requiere colección nueva. La cobertura de "por tipo de producto" (CU-T23) mejora conforme las 5 verticales nuevas generen `comisiones` reales (hoy `comisiones` ya soporta `tipo_producto` desde el rediseño v3, pero solo Vuelos genera datos reales todavía).

---

## Funcionalidad 1: Ver dashboard financiero (CU-T22)

### RF-FAC-T01 — Ver dashboard financiero
El sistema debe mostrar a un Administrador un resumen financiero en tiempo real: ingresos por producto (agrupado por `tipo_producto` vía `comisiones`/`reserva_items`), comisiones acumuladas (`pendiente_cobro` vs. `cobrada`) y remesas pendientes (`remesas.estado = pendiente`).

---

## Funcionalidad 2: Generar reporte de ingresos (CU-T23)

### RF-FAC-T02 — Generar reporte de ingresos por período y tipo de producto
El sistema debe permitir a un Administrador generar un reporte de ingresos (cargo de servicio + comisión cobrada) filtrado por período y tipo de producto, con filtros instantáneos (REG-J9).

### RN-FAC-T01 — El reporte respeta el desfase temporal cargo de servicio vs. comisión
Mismo criterio que RN-FAC-004 (Operativo): el reporte nunca suma cargo de servicio (inmediato) y comisión (diferida) como si fueran el mismo evento contable — los presenta como dos series separadas, o claramente etiquetadas, dentro del mismo reporte (`consideraciones.md` sección 5).

---

## Reglas de negocio

- **RN-FAC-T01** — *(Funcionalidad 2)* El reporte respeta el desfase temporal entre cargo de servicio y comisión, nunca los suma como el mismo evento.
- **RN-FAC-T02** — El dashboard (CU-T22) se actualiza sobre datos reales en cada consulta — no es un snapshot cacheado que pueda mostrar cifras desactualizadas sin indicarlo.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/facturacion/dashboard` | Cookie JWT (Admin) | HTML/JSON con ingresos por producto, comisiones acumuladas, remesas pendientes |
| `GET /backoffice/facturacion/reporte-ingresos` | Cookie JWT (Admin), filtro de período/producto | HTML/JSON con el reporte, cargo de servicio y comisión separados |

---

## Historias de usuario

- **HU-FAC-T01:** Como administrador, quiero ver un dashboard financiero en tiempo real, para tener visibilidad inmediata del estado del negocio.
- **HU-FAC-T02:** Como administrador, quiero generar un reporte de ingresos por período y producto, para análisis financiero detallado.

---

## Objetivo

Dar al Administrador visibilidad financiera agregada y por período, manteniendo siempre la distinción entre ingreso inmediato (cargo de servicio) e ingreso diferido (comisión) que ya es un principio establecido del módulo Operativo.

---

## Escenarios

### Camino feliz
1. Un Administrador consulta el dashboard financiero (CU-T22) al iniciar su día, ve remesas pendientes de generar.
2. Genera el reporte de ingresos del mes por tipo de producto (CU-T23), separando claramente cargo de servicio y comisión.

### Manejo de errores
- **Dashboard sin datos de una vertical nueva (ej. Hoteles, sin reservas reales todavía):** esa sección se muestra en cero, no se omite ni genera error.

---

## Criterios de aceptación

- **CU-T22:** Dado que existen pagos, comisiones y remesas reales, cuando un Administrador consulta el dashboard, entonces ve las 3 métricas actualizadas en tiempo real.
- **CU-T23:** Dado que un Administrador filtra por período y producto, cuando genera el reporte, entonces ve cargo de servicio y comisión como series claramente separadas, nunca sumadas como un solo evento.

---

## Dependencias

- **Facturación (Operativo):** ambos CU son vistas sobre `pagos`, `comisiones`, `remesas`, `facturas` ya generados.
- **Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes:** fuente de `tipo_producto` para la desagregación — hoy solo Vuelos tiene datos reales.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O32–O37 (Facturación, Operativo) — fuente de datos de ambos CU.
- CU-O34 (Registrar comisión, Operativo) — ya soporta `tipo_producto` por el rediseño v3 de `comisiones` (referencia `reserva_item_id`).

---

## Fuera de alcance

- Proyecciones o forecasting financiero — el catálogo define reportes descriptivos sobre datos históricos, no predictivos.
- Exportación del reporte a archivo descargable — solo vista en pantalla en esta ronda; si se necesita exportar, se amplía como RF nuevo.
