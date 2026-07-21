# Especificación Táctica — Reservas

**Módulo:** Reservas
**Prefijo:** RES
**Código fuente:** `app/reservas/` *(nivel Operativo ya implementado y probado — ver `specs/operativo/reservas/`; 21/21 tests reales pasando, 92/92 en todo el sistema)*
**Casos de uso cubiertos:** CU-T16 (Ver reporte de reservas por estado y período), CU-T17 (Monitorear reservas próximas a vencer por pago pendiente), CU-T18 (Configurar política de reembolsos por tipo de producto y tarifa)
**Actor:** Agente (CU-T17) / Administrador (CU-T16, CU-T18)

> **Estado:** nivel nuevo, sin código propio todavía. **CU-T18 es más central de lo habitual en un nivel Táctico**: `politicas_reembolso` (dbml v3) ganó el campo `tipo_producto` precisamente para que este CU pueda gestionar políticas de vuelo/hotel/auto/actividad/crucero desde un solo lugar — no es exclusivo de Reservas, es consumido por las 5 verticales de producto (`niveles_tarifa.politica_reembolso_id`, `hoteles_tarifas.politica_reembolso_id`, `autos_catalogo.politica_reembolso_id`, `actividades_catalogo.politica_reembolso_id`, `cruceros_camarotes_tarifa.politica_reembolso_id`).

---

## Funcionalidad 1: Ver reporte de reservas por estado (CU-T16)

### RF-RES-T01 — Ver reporte de reservas por estado y período
El sistema debe mostrar a un Administrador el número de reservas por estado (`pendiente_pago`, `confirmada`, `modificada`, `cancelada`, `completada`) en un período filtrado, con filtros instantáneos (REG-J9).

---

## Funcionalidad 2: Monitorear reservas próximas a vencer (CU-T17)

### RF-RES-T02 — Monitorear reservas próximas a vencer por pago pendiente y gestionar acciones
El sistema debe mostrar a un Agente/Administrador las reservas en `pendiente_pago` cercanas a su `fecha_expiracion_pago` (mismo mecanismo que CU-O44, Operativo, ya implementado y probado), permitiendo contactar al pasajero antes de que expire automáticamente.

### RN-RES-T01 — Este monitoreo no altera el mecanismo de expiración automática
CU-T17 es solo visibilidad y una vía de contacto proactivo — la expiración real (CU-O44) sigue corriendo automáticamente sin importar si un Agente intervino o no; no hay una acción de "extender plazo" en el catálogo actual (ver Fuera de alcance).

---

## Funcionalidad 3: Configurar política de reembolsos (CU-T18)

**Consumida por las 5 verticales de producto**, no solo por Reservas.

### RF-RES-T03 — Configurar política de reembolsos por tipo de producto y tarifa
El sistema debe permitir a un Administrador crear y editar políticas de reembolso (`politicas_reembolso`: nombre, condiciones, porcentaje de reembolso, ventana de horas) para cada `tipo_producto` (vuelo, hotel, auto, actividad, crucero) — no una política única genérica.

### RN-RES-T02 — Hoteles/Autos/Actividades/Cruceros pueden tener política real del proveedor superpuesta
Para Hoteles en particular (`hoteles_tarifas.reembolsable`/`.cancelacion_hasta`), la política configurada aquí es una capa **opcional** que la agencia puede superponer sobre el dato real del proveedor — nunca sustituye el dato real cuando existe (mismo criterio que RN-HOT-002, `hoteles-spec.md`).

---

## Reglas de negocio

- **RN-RES-T01** — *(Funcionalidad 2)* El monitoreo no altera el mecanismo de expiración automática ya implementado.
- **RN-RES-T02** — *(Funcionalidad 3)* Para productos con dato real de reembolso del proveedor, la política configurada aquí es una capa opcional, no un sustituto.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/reservas/reporte-estado` | Cookie JWT (Admin), filtro de período | HTML/JSON con reservas agrupadas por estado |
| `GET /backoffice/reservas/proximas-vencer` | Cookie JWT (Agente/Admin) | HTML/JSON con reservas próximas a expirar |
| `GET/POST /backoffice/reservas/politicas-reembolso` | Cookie JWT (Admin), tipo de producto, condiciones, porcentaje, ventana | Política creada/actualizada |

---

## Historias de usuario

- **HU-RES-T01:** Como administrador, quiero ver reservas por estado y período, para tener visibilidad del pipeline de ventas.
- **HU-RES-T02:** Como agente, quiero ver reservas próximas a vencer, para contactar al pasajero antes de que se cancele automáticamente.
- **HU-RES-T03:** Como administrador, quiero configurar políticas de reembolso por producto y tarifa, para todas las verticales desde un solo lugar.

---

## Objetivo

Dar visibilidad del pipeline de reservas, una vía proactiva de contacto antes de la expiración automática, y control centralizado sobre políticas de reembolso que aplican a las 6 verticales de producto del sistema.

---

## Escenarios

### Camino feliz
1. Un Administrador consulta el reporte de reservas por estado del último mes (CU-T16).
2. Un Agente ve una reserva a 2 horas de expirar (CU-T17) y contacta al pasajero para completar el pago.
3. El Administrador configura una política de reembolso nueva para cruceros (CU-T18), que `cruceros_camarotes_tarifa` empieza a referenciar.

### Manejo de errores
- **Reserva ya expirada al momento de contactar:** el Agente ve que ya cambió de estado, sin poder revertir la expiración (RN-RES-T01).

---

## Criterios de aceptación

- **CU-T16:** Dado que existen reservas en distintos estados en el período filtrado, cuando un Administrador consulta el reporte, entonces las ve agrupadas por estado.
- **CU-T17:** Dado que existen reservas `pendiente_pago` próximas a vencer, cuando un Agente las consulta, entonces las ve listadas, sin que esto afecte el mecanismo automático de expiración.
- **CU-T18:** Dado que un Administrador crea o edita una política para un tipo de producto, cuando la guarda, entonces queda disponible para que las verticales correspondientes la referencien.

---

## Dependencias

- **Reservas (Operativo):** CU-T16/T17 son vistas sobre datos ya generados por CU-O21–O25/O44.
- **Vuelos, Hoteles, Autos, Actividades, Cruceros:** todos consumen `politicas_reembolso` vía su propio `politica_reembolso_id`.
- **Seguridad:** RBAC (CU-O43) — distingue Agente (CU-T17) de Administrador (CU-T16, T18); sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O21–O25 (Reservas, Operativo) — fuente de datos de CU-T16/T17.
- CU-O44 (Expirar reserva pendiente, Operativo) — mecanismo que CU-T17 monitorea sin alterar.
- CU-O57 (Hoteles), CU-O64 (Autos), CU-O69 (Actividades), CU-O75 (Cruceros) — todos referencian las políticas de CU-T18.

---

## Fuera de alcance

- Extender manualmente el plazo de expiración de una reserva desde CU-T17 — no está en el catálogo de CU actual; el mecanismo automático (CU-O44) sigue siendo la única vía.
- Políticas de reembolso condicionadas por antigüedad del pasajero o nivel de fidelización — el esquema actual solo condiciona por tipo de producto y tarifa.
