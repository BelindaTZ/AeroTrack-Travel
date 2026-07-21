# Especificación Táctica — Autos

**Módulo:** Autos
**Prefijo:** AUT
**Código fuente:** `app/autos/` *(compartido con el nivel Operativo — ver `specs/operativo/autos/`)*
**Casos de uso cubiertos:** CU-T11 (Ver reporte de reservas de autos por proveedor y categoría de vehículo)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. El nivel Táctico de Autos tiene un único CU — depende de que el nivel Operativo (`specs/operativo/autos/`) esté implementado y de que existan reservas reales de tipo `auto` (`reserva_items`, migración pendiente en `reservas-spec.md`).

---

## Funcionalidad 1: Ver reporte de reservas de autos por proveedor y categoría (CU-T11)

Vista administrativa de backoffice, análoga a CU-T08 (Vuelos) y CU-T10 (Hoteles).

### RF-AUT-T01 — Ver reporte de reservas de autos por proveedor y categoría de vehículo
El sistema debe mostrar a un Administrador un reporte de reservas confirmadas de autos, agrupado por proveedor comercial (rentadora real cuando se conoce, o `proveedor_agregador` cuando no) y por categoría de vehículo (económico/SUV/lujo/...), filtrable por rango de fechas, con el número de reservas y el ingreso generado por combinación proveedor×categoría. Los filtros se aplican de forma instantánea (REG-J9).

### RN-AUT-T01 — Solo cuenta reservas confirmadas
El reporte cuenta únicamente reservas en estado `confirmada` o posterior — mismo criterio que el resto de los reportes de ingresos del sistema (ver `facturacion-spec.md`, `specs/tactico/hoteles/hoteles-spec.md` RN-HOT-T02).

---

## Reglas de negocio

- **RN-AUT-T01** — *(ver Funcionalidad 1)* Solo reservas `confirmada` o posterior cuentan en el reporte.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/autos/reporte` | Cookie JWT (Admin), filtros de fecha | HTML/JSON con el reporte agrupado por proveedor y categoría |

---

## Historias de usuario

- **HU-AUT-T01:** Como administrador, quiero ver qué proveedores y categorías de auto generan más reservas, para negociar mejor comisión con los proveedores de mayor volumen.

---

## Objetivo

Dar al Administrador visibilidad de qué combinación proveedor×categoría concentra el volumen de reservas de autos, para apoyar decisiones comerciales sobre datos reales de uso.

---

## Escenarios

### Camino feliz
1. Existen reservas confirmadas de autos de varios proveedores y categorías.
2. Un Administrador consulta el reporte filtrado por el último trimestre.
3. Ve que Expedia/SUV es la combinación con más reservas e ingreso generado.

### Manejo de errores
- **Sin reservas confirmadas en el período filtrado:** se muestra un mensaje claro, sin error técnico.

---

## Criterios de aceptación

- **CU-T11:** Dado que existen reservas confirmadas de auto en el período filtrado, cuando un Administrador consulta el reporte, entonces ve las combinaciones proveedor×categoría ordenadas por volumen, con su ingreso generado.

---

## Dependencias

- **Autos (Operativo):** fuente del catálogo y de la selección que originan las reservas.
- **Reservas:** depende de `reserva_items` con `tipo_producto = auto` — colección todavía no implementada.
- **Seguridad:** RBAC (CU-O43) y sesión (CU-O42) para el reporte de backoffice.

---

## Casos de uso relacionados

- CU-O61–O64 (Buscar/seleccionar auto, Operativo) — origen de las reservas que cuenta este reporte.
- CU-T08 (Vuelos), CU-T10 (Hoteles) — mismo patrón de reporte aplicado a otra vertical.

---

## Fuera de alcance

- Exportación del reporte a archivo descargable — solo vista en pantalla en esta ronda.
- Desglose por rentadora individual cuando el agregador no identifica al proveedor comercial real — en ese caso se agrupa por `proveedor_agregador`, no se infiere la rentadora.
