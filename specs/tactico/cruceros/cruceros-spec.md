# Especificación Táctica — Cruceros

**Módulo:** Cruceros
**Prefijo:** CRU
**Código fuente:** `app/cruceros/` *(compartido con el nivel Operativo — ver `specs/operativo/cruceros/`)*
**Casos de uso cubiertos:** CU-T13 (Ver cruceros más consultados por destino y temporada), CU-T43 (Configurar parámetros de disponibilidad sintética de camarotes de crucero)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0/v3.1, sin código todavía. Mismo caso que Actividades: CU-T43 es **precondición real** de RF-CRU-006 (Operativo) — implementar junto con esa fase, no después.

---

## Funcionalidad 1: Configurar disponibilidad sintética de camarotes (CU-T43)

### RF-CRU-T01 — Configurar parámetros de disponibilidad sintética de camarotes de crucero
El sistema debe permitir a un Administrador configurar, por tipo de camarote (BALCONY/OCEANVIEW/INTERIOR/SUITE) o de forma global, los parámetros que usa CU-O123 para generar `cruceros_camarotes_tarifa.cupos_disponibles`: cupo por defecto por tipo de camarote. Los valores se guardan en `configuracion_sistema` (categoría `disponibilidad_cruceros`) con `modificado_por` obligatorio.

### RN-CRU-T01 — Cambiar los parámetros no reescribe la disponibilidad ya generada retroactivamente
Mismo criterio que RN-ACT-T01 (Actividades): un cambio de configuración aplica a las próximas corridas de CU-O123, no reescribe cupos ya generados/vendidos.

---

## Funcionalidad 2: Ver cruceros más consultados (CU-T13)

### RF-CRU-T02 — Ver cruceros más consultados por destino y temporada
El sistema debe mostrar a un Administrador un reporte de los cruceros más consultados (búsquedas, no solo reservas — a diferencia de los reportes de otras verticales, este mide interés/demanda, no solo conversión), filtrable por destino y temporada. Filtros instantáneos (REG-J9).

### RN-CRU-T02 — El conteo de "consultados" mide búsquedas/vistas de detalle, no solo reservas confirmadas
A diferencia de CU-T10/T11/T12 (que cuentan reservas confirmadas), este reporte específicamente mide interés — combina vistas de detalle (CU-O72/O74) y búsquedas (CU-O71) que resultaron en ese crucero, no solo conversión a reserva. Esto es una decisión deliberada del catálogo (el nombre del CU dice "consultados", no "reservados") — no homologar con el patrón de los demás reportes sin revisar antes si el catálogo realmente quiso decir lo mismo.

---

## Reglas de negocio

- **RN-CRU-T01** — *(Funcionalidad 1)* Cambios de configuración no reescriben disponibilidad ya generada retroactivamente.
- **RN-CRU-T02** — *(Funcionalidad 2)* El reporte mide consultas/interés, no solo reservas confirmadas — no homologar con el patrón de otros módulos sin confirmar.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/cruceros/config-disponibilidad` | Cookie JWT (Admin), cupo por defecto por tipo de camarote (global o por tipo) | Configuración guardada, aplica a la próxima corrida de CU-O123 |
| `GET /backoffice/cruceros/reporte` | Cookie JWT (Admin), filtros de destino/temporada | HTML/JSON con el reporte de cruceros más consultados |

---

## Historias de usuario

- **HU-CRU-T01:** Como administrador, quiero configurar el cupo por defecto de cada tipo de camarote, para ajustar la simulación de disponibilidad a lo que observo del negocio real.
- **HU-CRU-T02:** Como administrador, quiero ver qué cruceros generan más interés por destino y temporada, para negociar mejor con las navieras de mayor demanda, incluso antes de que se traduzca en reservas.

---

## Objetivo

Dar al Administrador control sobre los parámetros de la única fuente de disponibilidad de esta vertical (sintética), y visibilidad temprana de interés/demanda por crucero — no solo de lo ya reservado — para apoyar decisiones comerciales con más anticipación que un reporte de solo conversión.

---

## Escenarios

### Camino feliz
1. Un Administrador configura cupo por defecto de camarotes SUITE (CU-T43).
2. El siguiente ciclo de CU-O123 (`specs/operativo/cruceros/`) usa ese parámetro.
3. Semanas después, el Administrador consulta el reporte de cruceros más consultados (CU-T13) filtrado por Caribe/temporada alta, y ve interés alto en un crucero específico aunque todavía tenga pocas reservas confirmadas.

### Manejo de errores
- **Cambio de configuración con cupos ya vendidos:** no se altera retroactivamente (RN-CRU-T01).
- **Reporte sin consultas en el filtro aplicado:** mensaje claro, sin error técnico.

---

## Criterios de aceptación

- **CU-T43:** Dado que un Administrador guarda nuevos parámetros de disponibilidad sintética, cuando corre la siguiente generación (CU-O123), entonces usa esos valores; la disponibilidad ya generada antes no se altera.
- **CU-T13:** Dado que existen búsquedas/vistas de detalle de cruceros en el filtro aplicado, cuando un Administrador consulta el reporte, entonces ve los cruceros ordenados por nivel de consulta, no solo por reservas confirmadas.

---

## Dependencias

- **Cruceros (Operativo):** RF-CRU-006 (CU-O123) es el consumidor real de CU-T43 — dependencia bidireccional a considerar al secuenciar.
- **Cruceros (Operativo):** CU-T13 depende de que se registren búsquedas/vistas (CU-O71/O72/O74) de forma consultable — no depende de `reserva_items` como los demás reportes de otras verticales.
- **Seguridad:** RBAC (CU-O43) y sesión (CU-O42) para ambas pantallas de backoffice.

---

## Casos de uso relacionados

- CU-O123 (Generar disponibilidad sintética, Operativo) — consumidor directo de CU-T43.
- CU-O71, O72, O74 (Buscar/ver crucero, Operativo) — origen de las consultas que cuenta CU-T13.
- CU-T42 (Configurar disponibilidad sintética de actividades) — mismo patrón aplicado a otra vertical.

---

## Fuera de alcance

- Configuración de disponibilidad por crucero individual (solo global o por tipo de camarote en esta ronda).
- Exportación del reporte de CU-T13 a archivo descargable.
- Homologar CU-T13 al patrón de "solo reservas confirmadas" de otros reportes — es una decisión deliberada distinta, no un error a corregir.
