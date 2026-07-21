# Especificación Táctica — Disrupciones y Notificaciones

**Módulo:** Disrupciones y Notificaciones
**Prefijo:** DIS
**Código fuente:** `app/disrupciones/` *(nivel Operativo ya implementado — ver `specs/operativo/disrupciones/`)*
**Casos de uso cubiertos:** CU-T19 (Ver dashboard de vuelos activos en monitoreo), CU-T20 (Configurar umbrales de risk score que disparan alerta proactiva), CU-T21 (Ver reporte de disrupciones por aerolínea, ruta y período)
**Actor:** Agente/Administrador (CU-T19) / Administrador (CU-T20, T21)

> **Estado:** nivel nuevo, sin código propio todavía. **CU-T20 depende de CU-O83** (Calcular y registrar risk score, `specs/operativo/disrupciones/`, no implementado todavía) — sin ese dato, no hay umbral que configurar de forma significativa. CU-T19/T21 sí pueden implementarse ya, sobre CU-O27-O31/O46 (Operativo, implementados y probados).

---

## Funcionalidad 1: Ver dashboard de vuelos activos en monitoreo (CU-T19)

### RF-DIS-T01 — Ver dashboard de vuelos activos en monitoreo con estado en tiempo real
El sistema debe mostrar a un Agente/Administrador los vuelos con reservas confirmadas actualmente en monitoreo (CU-O27/O28, Operativo), su estado real más reciente y si tienen una disrupción activa.

---

## Funcionalidad 2: Configurar umbrales de risk score (CU-T20)

**Precondición real: CU-O83** (`specs/operativo/disrupciones/`, no implementado).

### RF-DIS-T02 — Configurar umbrales de risk score que disparan alerta proactiva al pasajero
El sistema debe permitir a un Administrador configurar el umbral de `risk_score` (0-1) a partir del cual se envía una notificación proactiva al pasajero antes de que ocurra una disrupción real confirmada — distinta de la notificación reactiva de CU-O30 (que se dispara ante un cambio ya detectado). Guardado en `configuracion_sistema`.

### RN-DIS-T01 — La alerta proactiva no reemplaza la notificación reactiva
CU-T20 configura un aviso **adicional y anticipado** basado en probabilidad estadística — nunca sustituye la notificación real cuando el cambio efectivamente ocurre (CU-O30 sigue disparándose siempre, sin importar si hubo alerta proactiva antes).

---

## Funcionalidad 3: Ver reporte de disrupciones (CU-T21)

### RF-DIS-T03 — Ver reporte de disrupciones por aerolínea, ruta y período
El sistema debe mostrar a un Administrador el número de disrupciones detectadas, agrupadas por aerolínea y ruta, en un período filtrado, con filtros instantáneos (REG-J9).

---

## Reglas de negocio

- **RN-DIS-T01** — *(Funcionalidad 2)* La alerta proactiva es adicional, nunca sustituye la notificación reactiva real.
- **RN-DIS-T02** — Toda edición de configuración de este nivel se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/disrupciones/dashboard` | Cookie JWT (Agente/Admin) | HTML/JSON con vuelos en monitoreo y su estado |
| `GET/POST /backoffice/disrupciones/config-umbral-riesgo` | Cookie JWT (Admin), umbral (0-1) | Configuración actualizada |
| `GET /backoffice/disrupciones/reporte` | Cookie JWT (Admin), filtro de aerolínea/ruta/período | HTML/JSON con disrupciones agrupadas |

---

## Historias de usuario

- **HU-DIS-T01:** Como agente, quiero ver un dashboard de vuelos en monitoreo, para tener visibilidad operativa en tiempo real.
- **HU-DIS-T02:** Como administrador, quiero configurar el umbral de risk score que dispara una alerta proactiva, para avisar al pasajero antes de que el cambio sea definitivo.
- **HU-DIS-T03:** Como administrador, quiero ver disrupciones por aerolínea y ruta, para identificar patrones y negociar con proveedores problemáticos.

---

## Objetivo

Dar visibilidad operativa en tiempo real del monitoreo activo, una vía de aviso anticipado basado en riesgo estadístico (complementaria, nunca sustituta, de la notificación real), y análisis agregado de disrupciones por proveedor y ruta.

---

## Escenarios

### Camino feliz
1. Un Agente consulta el dashboard de vuelos en monitoreo (CU-T19) durante su turno.
2. Un Administrador configura el umbral de risk score en 0.7 (CU-T20) — vuelos con score mayor disparan alerta proactiva, una vez CU-O83 esté implementado.
3. Consulta el reporte de disrupciones (CU-T21) y detecta que una aerolínea concentra la mayoría de retrasos en una ruta específica.

### Manejo de errores
- **Vuelo con risk_score alto pero sin CU-O83 implementado todavía:** el umbral queda configurado pero sin efecto real hasta que ese CU exista — no se simula un disparo falso.

---

## Criterios de aceptación

- **CU-T19:** Dado que existen vuelos con reservas confirmadas en monitoreo, cuando un Agente/Administrador consulta el dashboard, entonces ve su estado real más reciente.
- **CU-T20:** Dado que un Administrador configura un umbral, cuando un vuelo supera ese `risk_score` (una vez CU-O83 exista), entonces se dispara la alerta proactiva, sin reemplazar la notificación reactiva real.
- **CU-T21:** Dado que existen disrupciones detectadas en el período filtrado, cuando un Administrador consulta el reporte, entonces las ve agrupadas por aerolínea y ruta.

---

## Dependencias

- **Disrupciones (Operativo):** CU-T19/T21 son vistas sobre CU-O27-O31/O46 ya implementados; CU-T20 depende de CU-O83 (pendiente).
- **Seguridad:** RBAC (CU-O43) — distingue Agente (CU-T19) de Administrador (CU-T20, T21); sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O27, O28, O29 (Disrupciones, Operativo) — fuente de datos de CU-T19.
- CU-O30 (Notificar al pasajero, Operativo) — notificación reactiva, complementada (no reemplazada) por CU-T20.
- CU-O83 (Calcular risk score, Operativo, pendiente) — precondición real de CU-T20.

---

## Fuera de alcance

- Cálculo del risk score en sí — vive en CU-O83 (Operativo), este nivel solo configura el umbral de disparo.
- Canal de alerta proactiva distinto a los ya usados por CU-O30 (email/SMS) — reutiliza el mismo mecanismo de envío, no introduce uno nuevo.
