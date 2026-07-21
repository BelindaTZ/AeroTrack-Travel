# Especificación Táctica — Centro de Ayuda

**Módulo:** Centro de Ayuda
**Prefijo:** AYU
**Código fuente:** `app/centro_ayuda/` *(compartido con el nivel Operativo — ver `specs/operativo/centro-ayuda/`)*
**Casos de uso cubiertos:** CU-T28 (Gestionar base de conocimiento), CU-T29 (Ver métricas de satisfacción del centro de ayuda), CU-T36 (Gestionar bandeja de casos escalados)
**Actor:** Administrador (CU-T28, CU-T29) / Agente (CU-T36)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. CU-T28 es **precondición real** de RF-AYU-001/002 (Operativo, la búsqueda no tiene nada que mostrar sin artículos) — implementar antes o junto con esa fase. CU-T36 es el **contraparte humana real** de CU-O100 (Operativo) — sin esto, un caso escalado se envía por email pero nadie lo gestiona desde el sistema.

---

## Funcionalidad 1: Gestionar base de conocimiento (CU-T28)

### RF-AYU-T01 — Gestionar base de conocimiento
El sistema debe permitir a un Administrador crear, editar y archivar (`activo = false`, nunca eliminar físicamente — mismo criterio que `aerolineas.activa`/`hoteles_catalogo` en otros módulos) artículos de ayuda por categoría, registrando `autor_id` y `fecha_publicacion`.

### RN-AYU-T01 — Archivar, no eliminar
Un artículo nunca se elimina físicamente — se archiva (`activo = false`), desapareciendo de la búsqueda (RF-AYU-001) pero conservando su historial de calificaciones para el reporte de CU-T29.

---

## Funcionalidad 2: Ver métricas de satisfacción (CU-T29)

### RF-AYU-T02 — Ver métricas de satisfacción del centro de ayuda
El sistema debe mostrar a un Administrador los artículos más consultados, su calificación (proporción de pulgar arriba/abajo) y el número de casos escalados en el período, como indicador indirecto de qué tan bien resuelve la base de conocimiento antes de necesitar escalación. Filtros instantáneos (REG-J9).

---

## Funcionalidad 3: Gestionar bandeja de casos escalados (CU-T36)

Contraparte real de CU-O100 (Operativo) — sin esta funcionalidad, los casos escalados se envían por email pero no hay dónde gestionarlos desde el sistema.

### RF-AYU-T03 — Gestionar bandeja de casos escalados
El sistema debe mostrar a un Agente los casos escalados (`casos_escalados`, filtrable por `estado`), permitirle revisar el hilo de correo real (`gmail_thread_id`), responder al pasajero desde ahí (vía Gmail, no una UI de chat separada) y marcar el caso como `resuelto` (`fecha_resolucion` registrada), opcionalmente asignándoselo a sí mismo (`agente_asignado_id`).

### RN-AYU-T02 — Un caso resuelto conserva su hilo de correo real
Marcar un caso como `resuelto` no borra ni desvincula `gmail_thread_id` — la conversación real permanece consultable para auditoría o referencia futura.

---

## Reglas de negocio

- **RN-AYU-T01** — *(Funcionalidad 1)* Los artículos se archivan, nunca se eliminan físicamente.
- **RN-AYU-T02** — *(Funcionalidad 3)* Un caso resuelto conserva su vínculo al hilo de correo real.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/ayuda/articulos` | Cookie JWT (Admin), datos del artículo | Artículo creado/actualizado/archivado |
| `GET /backoffice/ayuda/metricas` | Cookie JWT (Admin), filtro de período | HTML/JSON con métricas de satisfacción |
| `GET /backoffice/ayuda/casos` | Cookie JWT (Agente), filtro de estado | HTML/JSON con casos escalados |
| `POST /backoffice/ayuda/casos/{id}/resolver` | Cookie JWT (Agente) | Caso marcado `resuelto`, `fecha_resolucion` registrada |

---

## Historias de usuario

- **HU-AYU-T01:** Como administrador, quiero gestionar la base de conocimiento, para mantenerla vigente sin depender de un desarrollador.
- **HU-AYU-T02:** Como administrador, quiero ver métricas de satisfacción del centro de ayuda, para saber si la base de conocimiento realmente resuelve dudas.
- **HU-AYU-T03:** Como agente, quiero gestionar la bandeja de casos escalados, para dar seguimiento real a los pasajeros que no se resolvieron por autoservicio.

---

## Objetivo

Dar al Administrador control sobre el contenido de autoservicio y visibilidad de su efectividad, y al Agente una vía real de seguimiento de los casos escalados — sin inventar una bandeja simulada cuando la comunicación real ocurre por email.

---

## Escenarios

### Camino feliz
1. Un Administrador crea artículos de ayuda por categoría (CU-T28).
2. Pasajeros los consultan y califican (`specs/operativo/centro-ayuda/`, CU-O97-O99); algunos escalan casos (CU-O100).
3. Un Agente revisa la bandeja de casos escalados (CU-T36), responde por email y marca el caso resuelto.
4. El Administrador consulta métricas de satisfacción (CU-T29) y ve la proporción de consultas resueltas por autoservicio vs. escaladas.

### Manejo de errores
- **Intento de eliminar físicamente un artículo:** no existe esa acción, solo archivar (RN-AYU-T01).
- **Caso marcado resuelto sin respuesta real enviada:** el sistema no impide marcarlo (la respuesta ocurre en Gmail, fuera del sistema), pero el hilo real queda siempre consultable para verificar (RN-AYU-T02).

---

## Criterios de aceptación

- **CU-T28:** Dado que un Administrador crea, edita o archiva un artículo, cuando confirma, entonces el cambio se refleja en la búsqueda (visible si `activo`, invisible si archivado).
- **CU-T29:** Dado que existen artículos consultados y casos escalados en el período, cuando un Administrador consulta métricas, entonces ve los más consultados, su calificación y el volumen de escalación.
- **CU-T36:** Dado que existen casos escalados, cuando un Agente los revisa y marca uno como resuelto, entonces su estado y fecha de resolución quedan actualizados, con el hilo de correo real intacto.

---

## Dependencias

- **Centro de Ayuda (Operativo):** RF-AYU-001/002 son consumidores reales de CU-T28; CU-T36 es la contraparte de CU-O100.
- **Seguridad:** RBAC (CU-O43) — Administrador para CU-T28/T29, Agente para CU-T36; sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O97, O98 (Buscar/ver artículo, Operativo) — consumidores de CU-T28.
- CU-O99 (Calificar artículo, Operativo) — fuente de datos de CU-T29.
- CU-O100 (Escalar caso, Operativo) — origen de los casos que gestiona CU-T36.

---

## Fuera de alcance

- Chat en vivo o UI de mensajería propia para responder casos — la respuesta siempre ocurre en Gmail; este módulo solo gestiona el estado del caso y da acceso al hilo real.
- Reasignación automática de casos entre agentes por carga de trabajo — `agente_asignado_id` es manual en esta ronda.
