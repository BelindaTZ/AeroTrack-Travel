# Especificación Táctica — Cuenta de Usuario / Mis Viajes

**Módulo:** Cuenta / Mis Viajes
**Prefijo:** CTA
**Código fuente:** `app/cuenta/` *(compartido con el nivel Operativo — ver `specs/operativo/cuenta-mis-viajes/`)*
**Casos de uso cubiertos:** CU-T24 (Configurar programa de beneficios), CU-T25 (Ver reporte de alertas de precio activas y conversiones generadas)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. CU-T24 es **precondición real** de RF-CTA-006 (Operativo, el saldo de puntos lee estos niveles) — implementar junto con esa fase.

---

## Funcionalidad 1: Configurar programa de beneficios (CU-T24)

### RF-CTA-T01 — Configurar programa de beneficios
El sistema debe permitir a un Administrador crear y editar niveles del programa de beneficios (`programa_beneficios_niveles`: nombre, puntos mínimos para alcanzarlo, beneficios asociados, puntos acumulados por dólar gastado, y meses de vencimiento de los puntos — nulo si no vencen).

### RN-CTA-T01 — Los niveles no se solapan en su rango de puntos mínimos
Dos niveles no pueden tener el mismo `puntos_minimos`; el nivel vigente de un pasajero es siempre el de mayor `puntos_minimos` que su saldo alcanza.

---

## Funcionalidad 2: Ver reporte de alertas de precio (CU-T25)

### RF-CTA-T02 — Ver reporte de alertas de precio activas y conversiones generadas
El sistema debe mostrar a un Administrador el número de alertas de precio activas (`alertas_precio.activa = true`) por ruta, y cuántas de ellas derivaron en una reserva real dentro de un plazo razonable después de que el precio cruzó el umbral ("conversión"). Filtrable por período, con filtros instantáneos (REG-J9).

### RN-CTA-T02 — Una alerta cuenta como "convertida" solo si hay una reserva real posterior con la misma ruta
El sistema no asume causalidad perfecta (el pasajero pudo reservar por otro motivo) — cuenta una conversión cuando existe una reserva confirmada de esa ruta/fecha después de que la alerta se disparó, documentando esta limitación de atribución en el propio reporte, no como un dato 100% certero.

---

## Reglas de negocio

- **RN-CTA-T01** — *(Funcionalidad 1)* Niveles del programa no se solapan; el vigente es el de mayor umbral alcanzado.
- **RN-CTA-T02** — *(Funcionalidad 2)* Conversión = reserva real posterior a la alerta, con atribución aproximada, no exacta.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/cuenta/programa-beneficios` | Cookie JWT (Admin), niveles con sus reglas | Nivel creado/actualizado |
| `GET /backoffice/cuenta/reporte-alertas` | Cookie JWT (Admin), filtro de período | HTML/JSON con alertas activas y tasa de conversión aproximada |

---

## Historias de usuario

- **HU-CTA-T01:** Como administrador, quiero configurar los niveles del programa de beneficios, para ajustar la estrategia de fidelización sin tocar código.
- **HU-CTA-T02:** Como administrador, quiero ver cuántas alertas de precio se convierten en reservas, para medir si esta funcionalidad realmente impulsa ventas.

---

## Objetivo

Dar al Administrador control sobre la estructura de fidelización del programa de beneficios y visibilidad de la efectividad de las alertas de precio como mecanismo de conversión, con atribución honesta sobre sus límites.

---

## Escenarios

### Camino feliz
1. Un Administrador crea niveles "Bronce" (0 pts), "Plata" (5000 pts) y "Oro" (15000 pts) con sus reglas de acumulación (CU-T24).
2. Pasajeros acumulan puntos por sus compras (`specs/operativo/cuenta-mis-viajes/`, CU-O92).
3. El Administrador consulta el reporte de alertas de precio (CU-T25) y ve que el 15% de las alertas activas del último trimestre derivaron en una reserva.

### Manejo de errores
- **Crear un nivel con el mismo `puntos_minimos` que uno existente:** se rechaza (RN-CTA-T01).
- **Reporte sin alertas activas en el período filtrado:** mensaje claro.

---

## Criterios de aceptación

- **CU-T24:** Dado que un Administrador crea o edita un nivel, cuando lo guarda, entonces queda disponible para que RF-CTA-006 lo use al calcular el nivel vigente de cada pasajero.
- **CU-T25:** Dado que existen alertas activas y reservas posteriores en el período filtrado, cuando un Administrador consulta el reporte, entonces ve el total de alertas y la tasa de conversión aproximada.

---

## Dependencias

- **Cuenta/Mis Viajes (Operativo):** RF-CTA-006 es el consumidor real de CU-T24.
- **Reservas:** CU-T25 lee `alertas_precio` (ya implementada, ver nota en `specs/operativo/cuenta-mis-viajes/`) y reservas confirmadas para medir conversión.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O92 (Consultar saldo de puntos, Operativo) — consumidor de CU-T24.
- CU-O91 (Crear alerta de precio, Operativo, ya implementado en Reservas) — origen de los datos de CU-T25.

---

## Fuera de alcance

- Ajuste manual de nivel de un pasajero por un Administrador fuera de la regla de puntos — no está en el catálogo de CU actual.
- Exportación del reporte de CU-T25 a archivo descargable.
