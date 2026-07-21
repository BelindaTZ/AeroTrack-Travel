# Especificación Táctica — Actividades

**Módulo:** Actividades
**Prefijo:** ACT
**Código fuente:** `app/actividades/` *(compartido con el nivel Operativo — ver `specs/operativo/actividades/`)*
**Casos de uso cubiertos:** CU-T12 (Ver actividades más reservadas por destino y categoría), CU-T42 (Configurar parámetros de disponibilidad sintética de actividades)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0/v3.1, sin código todavía. CU-T42 es **precondición real** del nivel Operativo (RF-ACT-006 lee sus parámetros) — conviene implementarlo antes o junto con la Fase 2 de `specs/operativo/actividades/plan.md`, no después.

---

## Funcionalidad 1: Configurar parámetros de disponibilidad sintética (CU-T42)

A diferencia de CU-T12, este CU **no es solo un reporte** — sus valores alimentan directamente `RF-ACT-006` (Operativo). Es la config real detrás de la regla de negocio, no una vista de solo lectura.

### RF-ACT-T01 — Configurar parámetros de disponibilidad sintética de actividades
El sistema debe permitir a un Administrador configurar, por categoría de actividad o de forma global, los parámetros que usa CU-O121 para generar `actividades_horarios`: cupos por defecto y horarios por día (ej. "todos los días, 3 horarios, 15 cupos cada uno"). Los valores se guardan en `configuracion_sistema` (categoría `disponibilidad_actividades`) con `modificado_por` obligatorio.

### RN-ACT-T01 — Cambiar los parámetros no reescribe la disponibilidad ya generada retroactivamente
Un cambio en la configuración aplica a las próximas corridas de CU-O121, no reescribe `actividades_horarios` ya generado para fechas pasadas o cupos ya vendidos — evita que una reconfiguración deje cupos ya reservados en un estado inconsistente.

---

## Funcionalidad 2: Ver actividades más reservadas (CU-T12)

Vista administrativa de reporte, mismo patrón que CU-T08 (Vuelos)/CU-T10 (Hoteles)/CU-T11 (Autos).

### RF-ACT-T02 — Ver actividades más reservadas por destino y categoría
El sistema debe mostrar a un Administrador un reporte de actividades con más reservas confirmadas, filtrable por destino y categoría, con el número de reservas y el ingreso generado. Filtros instantáneos (REG-J9).

### RN-ACT-T02 — Solo cuenta reservas confirmadas
Mismo criterio que el resto de los reportes del sistema (`facturacion-spec.md`, `specs/tactico/hoteles/hoteles-spec.md` RN-HOT-T02): solo reservas `confirmada` o posterior.

---

## Reglas de negocio

- **RN-ACT-T01** — *(Funcionalidad 1)* Cambios de configuración no reescriben disponibilidad ya generada retroactivamente.
- **RN-ACT-T02** — *(Funcionalidad 2)* Solo reservas `confirmada` o posterior cuentan en el reporte.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/actividades/config-disponibilidad` | Cookie JWT (Admin), cupos/horarios por defecto (global o por categoría) | Configuración guardada, aplica a la próxima corrida de CU-O121 |
| `GET /backoffice/actividades/reporte` | Cookie JWT (Admin), filtros de destino/categoría | HTML/JSON con el reporte de actividades más reservadas |

---

## Historias de usuario

- **HU-ACT-T01:** Como administrador, quiero configurar cupos y horarios por defecto para la disponibilidad sintética, para ajustar la simulación a lo que observo del negocio real, sin tocar código.
- **HU-ACT-T02:** Como administrador, quiero ver qué actividades se reservan más por destino y categoría, para negociar mejor con los operadores turísticos de mayor volumen.

---

## Objetivo

Dar al Administrador control sobre los parámetros de la única fuente de disponibilidad que tiene esta vertical (sintética, por ausencia de dato real de proveedor), y visibilidad de qué actividades generan más reservas — ambas sin intervención de código.

---

## Escenarios

### Camino feliz
1. Un Administrador configura cupos/horarios por defecto para actividades de categoría "Sightseeing Cruises" (CU-T42).
2. El siguiente ciclo de CU-O121 (`specs/operativo/actividades/`) usa esos parámetros para generar disponibilidad nueva.
3. Semanas después, el Administrador consulta el reporte de actividades más reservadas (CU-T12) y ve que esa categoría lidera en su destino principal.

### Manejo de errores
- **Cambio de configuración con cupos ya vendidos en fechas futuras generadas con la config anterior:** esos registros no se alteran retroactivamente (RN-ACT-T01).
- **Reporte sin reservas confirmadas en el filtro aplicado:** mensaje claro, sin error técnico.

---

## Criterios de aceptación

- **CU-T42:** Dado que un Administrador guarda nuevos parámetros de disponibilidad sintética, cuando corre la siguiente generación (CU-O121), entonces usa esos valores; la disponibilidad ya generada antes no se altera.
- **CU-T12:** Dado que existen reservas confirmadas de actividad en el filtro aplicado, cuando un Administrador consulta el reporte, entonces ve las actividades ordenadas por volumen con su ingreso generado.

---

## Dependencias

- **Actividades (Operativo):** RF-ACT-006 (CU-O121) es el consumidor real de CU-T42 — es una dependencia bidireccional a tener en cuenta al secuenciar la implementación (ver nota de precondición al inicio).
- **Reservas:** CU-T12 depende de `reserva_items` con `tipo_producto = actividad` (no implementada todavía).
- **Seguridad:** RBAC (CU-O43) y sesión (CU-O42) para ambas pantallas de backoffice.

---

## Casos de uso relacionados

- CU-O121 (Generar disponibilidad sintética, Operativo) — consumidor directo de CU-T42.
- CU-O65–O70 (Buscar/seleccionar actividad, Operativo) — origen de las reservas que cuenta CU-T12.
- CU-T10 (Hoteles), CU-T11 (Autos) — mismo patrón de reporte aplicado a otra vertical.

---

## Fuera de alcance

- Configuración de disponibilidad por actividad individual (solo global o por categoría en esta ronda) — si se necesita ese nivel de granularidad, se amplía como RF nuevo.
- Exportación del reporte de CU-T12 a archivo descargable.
