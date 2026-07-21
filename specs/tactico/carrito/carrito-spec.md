# Especificación Táctica — Carrito

**Módulo:** Carrito
**Prefijo:** CAR
**Código fuente:** `app/carrito/` *(compartido con el nivel Operativo — ver `specs/operativo/carrito/`)*
**Casos de uso cubiertos:** CU-T26 (Configurar recuperación de carrito abandonado), CU-T27 (Ver reporte de carritos abandonados y tasa de recuperación)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Ambos CU son implementables en paralelo con el nivel Operativo — leen/escriben sobre `carritos` (ya definida ahí), no dependen de `reserva_items`.

---

## Funcionalidad 1: Configurar recuperación de carrito abandonado (CU-T26)

### RF-CAR-T01 — Configurar recuperación de carrito abandonado
El sistema debe permitir a un Administrador configurar el tiempo de inactividad (`carritos.fecha_ultima_actividad`) tras el cual un carrito `activo` se considera `abandonado`, y la plantilla del email de recordatorio que se envía en ese momento. Los valores se guardan en `configuracion_sistema` (categoría `carrito_abandonado`).

### RN-CAR-T01 — Un carrito solo puede marcarse abandonado si sigue activo
Un carrito ya `convertido` (checkout completado, CU-O96) nunca pasa a `abandonado`, sin importar cuánto tiempo lleve sin actividad tras la conversión — "abandono" solo aplica a carritos que nunca se convirtieron.

---

## Funcionalidad 2: Ver reporte de carritos abandonados (CU-T27)

### RF-CAR-T02 — Ver reporte de carritos abandonados y tasa de recuperación
El sistema debe mostrar a un Administrador el número de carritos abandonados por período, cuántos de ellos se recuperaron (volvieron a `activo` y luego a `convertido` tras el recordatorio) y la tasa de recuperación resultante. Filtros instantáneos (REG-J9).

---

## Reglas de negocio

- **RN-CAR-T01** — *(Funcionalidad 1)* Solo carritos `activo` pueden pasar a `abandonado`; un carrito `convertido` nunca cambia de estado retroactivamente.
- **RN-CAR-T02** — Un carrito se cuenta como "recuperado" solo si, tras marcarse `abandonado` y recibir el recordatorio, vuelve a `activo` y se convierte (`convertido`) — no basta con que el pasajero vuelva a abrir el carrito sin completar el checkout.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/carrito/config-abandono` | Cookie JWT (Admin), tiempo de inactividad, plantilla de email | Configuración guardada |
| `GET /backoffice/carrito/reporte` | Cookie JWT (Admin), filtro de período | HTML/JSON con carritos abandonados y tasa de recuperación |

---

## Historias de usuario

- **HU-CAR-T01:** Como administrador, quiero configurar cuándo se considera abandonado un carrito y qué email se envía, para automatizar la recuperación sin depender de un agente.
- **HU-CAR-T02:** Como administrador, quiero ver cuántos carritos se abandonan y cuántos se recuperan, para medir si vale la pena ajustar el tiempo de espera o la plantilla.

---

## Objetivo

Automatizar la detección y el intento de recuperación de carritos abandonados, y dar visibilidad de qué tan efectiva es esa estrategia, sin intervención manual de un agente.

---

## Escenarios

### Camino feliz
1. Un Administrador configura 2 horas de inactividad como umbral de abandono (CU-T26).
2. Un pasajero agrega un vuelo al carrito y no vuelve en 2 horas; el sistema lo marca `abandonado` y envía el email de recordatorio.
3. El pasajero vuelve, completa el checkout; el carrito pasa a `convertido` y cuenta como recuperado.
4. El Administrador consulta el reporte (CU-T27) y ve la tasa de recuperación del período.

### Manejo de errores
- **Carrito marcado abandonado que nunca se recupera:** cuenta en el denominador del reporte, no en el numerador.
- **Carrito que se convierte sin pasar nunca por abandonado:** no participa en la tasa de recuperación (no era un caso de abandono).

---

## Criterios de aceptación

- **CU-T26:** Dado que un Administrador configura el umbral de inactividad y la plantilla, cuando un carrito supera ese umbral sin actividad, entonces se marca `abandonado` y se envía el email configurado.
- **CU-T27:** Dado que existen carritos abandonados en el período filtrado, cuando un Administrador consulta el reporte, entonces ve el total de abandonados, cuántos se recuperaron y la tasa resultante.

---

## Dependencias

- **Carrito (Operativo):** dueño de `carritos`/`carrito_items`, este nivel solo lee/escribe `estado` y consume la configuración.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42), credenciales de envío de email (SendGrid, ya usado por Disrupciones/Ofertas y Promociones) — reutiliza la capa de envío existente, no crea una nueva.

---

## Casos de uso relacionados

- CU-O93–O96 (Ver/agregar/eliminar/checkout del carrito, Operativo) — ciclo de vida que este nivel monitorea.
- CU-O30 (Notificar al pasajero, Disrupciones) — mismo mecanismo de envío de email reutilizable, aunque el disparador y el contenido son distintos.

---

## Fuera de alcance

- Recordatorios múltiples escalonados (ej. a las 2h, 24h, 72h) — el catálogo define un único umbral configurable, no una secuencia de recordatorios.
- Recuperación vía canal distinto a email (SMS, notificación push) — fuera del catálogo de CU actual.
