# Especificación Operativa — Pasajeros

**Módulo:** Pasajeros
**Prefijo:** PAS
**Código fuente:** `app/pasajeros/`
**Casos de uso cubiertos:** CU-O14 (Consultar historial de reservas propio), CU-O15 (Editar datos de contacto), CU-O16 (Buscar y gestionar pasajeros — backoffice)
**Actor:** Pasajero / Agente / Administrador

---

## Funcionalidad 1: Consultar historial de reservas propio (CU-O14)

Permite a un pasajero revisar todas sus reservas, pasadas y futuras, sin intervención de un agente.

### RF-PAS-001 — Consultar historial de reservas propio
El sistema debe mostrar a todo pasajero autenticado la lista de sus reservas (`reservas` vía `reserva_pasajeros`/`pasajero_titular_id`), con estado, vuelo, fecha y monto, ordenadas por fecha de vuelo descendente. Cada reserva es navegable a su detalle (CU-O25, definido en `reservas-spec.md`).

### RNF-PAS-001 — Filtros instantáneos sobre el historial
El pasajero puede filtrar su historial por estado de reserva o rango de fechas; cada filtro se aplica automáticamente al cambiar su valor, sin botón "Aplicar" (REG-J9).

---

## Funcionalidad 2: Editar datos de contacto (CU-O15)

Especialización de la pantalla de perfil ya definida en `seguridad-spec.md` (RF-SEG-006): comparte la misma superficie de UI ("Mi perfil"), pero esta funcionalidad documenta las validaciones y consecuencias propias de los campos que actúan como canal de notificación.

### RF-PAS-002 — Editar datos de contacto
El sistema debe permitir a un pasajero autenticado actualizar su teléfono de contacto (`pasajeros.telefono`) y, cuando aplique, su dirección de facturación y contacto de emergencia. El correo electrónico, por ser también identificador de acceso, sigue la restricción definida en RF-SEG-006 (fuera de alcance el autoservicio de cambio de correo). Todo cambio exitoso se confirma con retroalimentación inmediata y no bloqueante (REG-J11).

### RNF-PAS-002 — Validación de formato de teléfono
El sistema valida que el teléfono ingresado tenga un formato utilizable como canal de notificación (SMS) antes de aceptarlo; rechaza formatos inválidos con mensaje específico.

---

## Funcionalidad 3: Buscar y gestionar pasajeros — backoffice (CU-O16)

Vista interna para que Agentes y Administradores localicen y den soporte a un pasajero.

### RF-PAS-003 — Buscar pasajeros (backoffice)
El sistema debe permitir a un Agente o Administrador buscar pasajeros por nombre, correo o número de documento, con resultados filtrados de forma instantánea (REG-J9). El alcance de esta búsqueda respeta la restricción RBAC de Nivel 2 del rol del usuario, si existe (CU-O43).

### RF-PAS-004 — Ver y editar detalle de pasajero (backoffice)
El sistema debe permitir a un Agente o Administrador ver el detalle completo de un pasajero (datos de contacto, historial de reservas) y editar sus datos de contacto en su nombre, cuando sea necesario para dar soporte. Esta acción incluye `<<include>>` la verificación de permisos RBAC (CU-O43) y el registro de auditoría (CU-O41).

---

## Reglas de negocio

- **RN-PAS-001** — El número de documento de identidad es opcional al registrarse (CU-O07) pero se vuelve obligatorio antes de poder confirmar una reserva (CU-O21/O22); el sistema lo exige en ese punto del flujo, no antes.
- **RN-PAS-002** — El teléfono y el correo del pasajero son, respectivamente, el canal secundario y primario de notificación de disrupciones; mantenerlos actualizados es responsabilidad del pasajero, pero el sistema no bloquea ninguna funcionalidad por un dato de contacto desactualizado — solo reduce la efectividad de la notificación (REG-E1 no se ve comprometido, la notificación se intenta igual).
- **RN-PAS-003** — En backoffice, un Agente solo puede ver y editar pasajeros dentro del alcance permitido por su restricción RBAC de Nivel 2, si su rol la tiene definida; un Administrador sin restricción de Nivel 2 accede a todos.
- **RN-PAS-004** — Toda edición de datos de pasajero, ya sea por autoservicio o desde backoffice, se audita (CU-O41), identificando si el cambio lo hizo el propio pasajero o un Agente/Administrador en su nombre.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /mis-reservas` | Cookie JWT, filtros opcionales (estado, fechas) | HTML/JSON con historial de reservas del pasajero autenticado |
| `POST /mi-perfil/contacto` | Cookie JWT, teléfono/dirección/contacto de emergencia | Confirmación de actualización o mensaje de error de validación |
| `GET /backoffice/pasajeros` | Cookie JWT (Agente/Admin), término de búsqueda | HTML/JSON con resultados filtrados de pasajeros |
| `GET /backoffice/pasajeros/{id}` | Cookie JWT (Agente/Admin) | HTML/JSON con detalle del pasajero y su historial |
| `PUT /backoffice/pasajeros/{id}` | Cookie JWT (Agente/Admin), campos de contacto | Pasajero actualizado o mensaje de error RBAC |

---

## Historias de usuario

- **HU-PAS-01:** Como pasajero, quiero consultar mi historial de reservas, para revisar mis viajes pasados y futuros.
- **HU-PAS-02:** Como pasajero, quiero editar mis datos de contacto, para asegurarme de recibir las notificaciones de disrupciones en el canal correcto.
- **HU-PAS-03:** Como agente o administrador, quiero buscar pasajeros por nombre, correo o documento, para atenderlos o resolver una solicitud de soporte.
- **HU-PAS-04:** Como agente o administrador, quiero ver y editar el detalle de un pasajero, para corregir sus datos de contacto cuando me lo solicita por otro canal.

---

## Objetivo

Dar a cada pasajero visibilidad total sobre su propio historial de viaje y control sobre sus datos de contacto — el canal del que depende directamente la confiabilidad de notificación que es el diferenciador del negocio (constitución E1) — y dar al equipo interno (Agente/Administrador) una vía de soporte sobre esos mismos datos, siempre dentro de los límites de su matriz RBAC.

---

## Escenarios

### Camino feliz
1. Un pasajero autenticado accede a "Mis reservas" y consulta su historial (CU-O14).
2. Detecta que su teléfono está desactualizado y lo corrige desde su perfil (CU-O15).
3. El cambio queda auditado y disponible de inmediato como canal de notificación válido.
4. Días después, el pasajero llama a soporte; un Agente lo busca por correo en el backoffice (CU-O16) y confirma sus datos actualizados.

### Manejo de errores
- **Teléfono con formato inválido:** se rechaza con mensaje específico antes de guardar.
- **Búsqueda de backoffice sin resultados:** se muestra un mensaje claro, sin error técnico.
- **Agente fuera de su alcance RBAC de Nivel 2:** el pasajero buscado no aparece en los resultados o la edición se bloquea, comunicado visualmente (REG-J6).
- **Documento de identidad ausente al intentar reservar:** el sistema lo exige en ese punto (RN-PAS-001), no lo bloquea antes.

---

## Criterios de aceptación

- **CU-O14:** Dado que un pasajero está autenticado, cuando accede a su historial de reservas, entonces ve todas sus reservas propias ordenadas por fecha de vuelo, sin ver reservas de otros pasajeros.
- **CU-O15:** Dado que un pasajero autenticado ingresa un teléfono con formato válido, cuando guarda el cambio, entonces su dato de contacto queda actualizado y disponible como canal de notificación.
- **CU-O16:** Dado que un Agente/Administrador con permiso RBAC busca un pasajero, cuando encuentra el resultado dentro de su alcance autorizado, entonces puede ver y editar su detalle; si está fuera de su alcance, la acción se bloquea.

---

## Dependencias

- **Seguridad:** sesión (CU-O42), RBAC (CU-O43), auditoría (CU-O41), y la pantalla base de perfil (RF-SEG-006) que esta funcionalidad especializa.
- **Reservas:** el historial de CU-O14 lee directamente la tabla `reservas` que ese módulo posee.
- **Disrupciones:** consume los datos de contacto mantenidos aquí como canal de envío de notificaciones (CU-O30).

---

## Casos de uso relacionados

- CU-O05 (Ver y editar perfil propio, Seguridad) — superficie de UI compartida con CU-O15.
- CU-O07 (Registrar nuevo pasajero, Seguridad) — origen del registro que este módulo consulta y edita.
- CU-O21, O22 (Crear reserva, Reservas) — exige el número de documento que aquí es opcional (RN-PAS-001).
- CU-O30, O31 (Notificar al pasajero / historial de notificaciones, Disrupciones) — dependen de los datos de contacto de este módulo.

---

## Fuera de alcance

- Programa de fidelización o perfil de viajero frecuente — reservado para el departamento Comercial y Marketing, sin CU redactados aún.
- Cambio de correo electrónico (identificador de acceso) — pertenece a `seguridad-spec.md` y no está implementado en esta versión.
- Eliminación de cuenta o de datos personales — el mecanismo de solicitud vive en `seguridad-spec.md` (RF-SEG-017); este módulo solo participa como dueño del dato de perfil extendido.
