# Especificación Táctica — Hoteles

**Módulo:** Hoteles
**Prefijo:** HOT
**Código fuente:** `app/hoteles/` *(compartido con el nivel Operativo — ver `specs/operativo/hoteles/`; esta spec documenta las funcionalidades propias del nivel Táctico, en routers/servicios separados dentro del mismo paquete de módulo)*
**Casos de uso cubiertos:** CU-T09 (Comparar hasta 5 propiedades de hotel lado a lado), CU-T10 (Ver reporte de hoteles más reservados por destino y período)
**Actor:** Pasajero (CU-T09) / Administrador (CU-T10)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Depende de que el nivel Operativo de Hoteles (`specs/operativo/hoteles/`) esté implementado — ambos CU de este documento leen datos que genera ese nivel, ninguno tiene tabla propia nueva.

---

## Funcionalidad 1: Comparar hasta 5 propiedades de hotel lado a lado (CU-T09)

`<<extend>>` de CU-O54/O55 (`specs/operativo/hoteles/hoteles-spec.md`) — no es un CU independiente en el flujo, es una capacidad adicional sobre los resultados de búsqueda o el detalle.

### RF-HOT-T01 — Comparar hasta 5 propiedades de hotel lado a lado
El sistema debe permitir a un pasajero seleccionar hasta 5 hoteles de sus resultados de búsqueda (CU-O54) y verlos comparados en una vista lado a lado: precio desde, estrellas, calificación promedio, `category_scores` (Value/Location/Rooms/Cleanliness/Service), servicios principales y política de cancelación de su tarifa más económica. Si el pasajero intenta agregar un sexto hotel a la comparación, el sistema rechaza la acción con un mensaje explícito en vez de reemplazar silenciosamente uno ya agregado.

### RNF-HOT-T01 — La comparación no dispara nuevas consultas a la fuente externa
La vista de comparación reutiliza los datos ya cargados en `hoteles_catalogo`/`hoteles_tarifas` (mismo catálogo que consume CU-O54) — no consulta HotelLens de nuevo por cada hotel comparado, para no consumir cuota adicional.

---

## Funcionalidad 2: Ver reporte de hoteles más reservados (CU-T10)

Vista administrativa de backoffice, análoga a CU-T08 en Vuelos (rutas más buscadas).

### RF-HOT-T02 — Ver reporte de hoteles más reservados por destino y período
El sistema debe mostrar a un Administrador un reporte de los hoteles con más reservas confirmadas, filtrable por destino (ciudad/país) y rango de fechas, con el número de reservas y el ingreso generado por cada uno. Los filtros se aplican de forma instantánea (REG-J9). Este reporte depende de que existan reservas reales sobre `reserva_items` con `tipo_producto = hotel` (ver nota de migración en `reservas-spec.md` — la colección `reserva_items` todavía no existe en código).

---

## Reglas de negocio

- **RN-HOT-T01** — La comparación (CU-T09) admite un máximo de 5 propiedades simultáneas; un sexto intento se rechaza explícitamente, nunca reemplaza en silencio una selección previa.
- **RN-HOT-T02** — El reporte de CU-T10 cuenta únicamente reservas en estado `confirmada` o posterior (no `pendiente_pago` ni `cancelada`) — mismo criterio de "reserva real" que usarían los demás reportes de ingresos del sistema (ver `facturacion-spec.md`).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /hoteles/comparar` | IDs de hasta 5 hoteles (query params) | HTML/JSON con la comparación lado a lado |
| `GET /backoffice/hoteles/reporte` | Cookie JWT (Admin), filtros de destino/fecha | HTML/JSON con el reporte de hoteles más reservados |

---

## Historias de usuario

- **HU-HOT-T01:** Como pasajero, quiero comparar hasta 5 hoteles lado a lado, para decidir entre mis finalistas sin abrir pestañas separadas.
- **HU-HOT-T02:** Como administrador, quiero ver qué hoteles se reservan más por destino y período, para negociar mejor con los proveedores que más volumen generan.

---

## Objetivo

Dar al pasajero una herramienta de decisión final entre sus opciones favoritas de hospedaje, y al Administrador visibilidad de qué propiedades concentran el volumen de reservas, para apoyar decisiones comerciales (negociación de comisión, priorización de proveedores) sobre datos reales de uso, no estimaciones.

---

## Escenarios

### Camino feliz
1. Un pasajero busca hoteles (CU-O54, `specs/operativo/hoteles/`) y marca 3 como favoritos para comparar.
2. Accede a la vista de comparación (CU-T09) y ve los 3 lado a lado con sus datos clave.
3. Semanas después, un Administrador consulta el reporte de hoteles más reservados (CU-T10) filtrado por el destino de esa búsqueda, y ve que uno de esos 3 hoteles está entre los más reservados.

### Manejo de errores
- **Intento de comparar un sexto hotel:** se rechaza explícitamente, la selección de 5 se mantiene intacta (RN-HOT-T01).
- **Reporte sin reservas confirmadas en el período filtrado:** se muestra un mensaje claro, sin error técnico.

---

## Criterios de aceptación

- **CU-T09:** Dado que un pasajero seleccionó entre 2 y 5 hoteles de sus resultados, cuando accede a la comparación, entonces ve una vista lado a lado con los datos clave de cada uno; al intentar un sexto, la acción se rechaza.
- **CU-T10:** Dado que existen reservas confirmadas de hotel en el período filtrado, cuando un Administrador consulta el reporte, entonces ve los hoteles ordenados por volumen de reservas con su ingreso generado.

---

## Dependencias

- **Hoteles (Operativo):** CU-T09 reutiliza `hoteles_catalogo`/`hoteles_tarifas` ya cargados por CU-O54/O118; sin ese nivel implementado, no hay datos que comparar.
- **Reservas:** CU-T10 depende de `reserva_items` con `tipo_producto = hotel` — colección todavía no implementada (ver nota de migración en `reservas-spec.md`).
- **Seguridad:** RBAC (CU-O43) y sesión (CU-O42) para el reporte de backoffice; la comparación (CU-T09) es de cara al pasajero, no requiere rol interno.

---

## Casos de uso relacionados

- CU-O54, O55 (Buscar/ver detalle de hotel, Operativo) — CU-T09 extiende ambos.
- CU-O118 (Generar catálogo de hoteles, Operativo) — fuente de los datos que compara CU-T09.
- CU-T08 (Ver reporte de rutas más buscadas, Vuelos) — mismo patrón de reporte aplicado a otra vertical.

---

## Fuera de alcance

- Comparación entre hoteles y otras verticales (ej. hotel vs. paquete) — CU-T09 es exclusivamente entre propiedades de hotel.
- Exportación del reporte de CU-T10 a archivo descargable — solo vista en pantalla en esta ronda; si se necesita exportar, se amplía como RF nuevo, no se asume incluido.
- Configuración de qué campos aparecen en la comparación (personalización por Administrador) — la comparación de CU-T09 tiene un set fijo de campos en esta versión.
