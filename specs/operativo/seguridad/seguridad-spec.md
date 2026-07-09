# Especificación Operativa — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/`
**Casos de uso cubiertos:** CU-O01 (Iniciar sesión), CU-O02 (Cerrar sesión), CU-O03 (Recuperar contraseña), CU-O04 (Restablecer contraseña vía enlace), CU-O05 (Ver y editar perfil propio), CU-O06 (Cambiar contraseña autenticado), CU-O07 (Registrar nuevo pasajero), CU-O08 (Gestionar usuarios internos), CU-O09 (Crear rol), CU-O10 (Editar rol), CU-O11 (Eliminar rol), CU-O12 (Ver log de auditoría), CU-O13 (Filtrar y exportar log de auditoría), CU-O41 (Registrar evento en auditoría), CU-O42 (Verificar sesión activa), CU-O43 (Verificar permisos de acceso RBAC)
**Actor:** Pasajero / Agente / Administrador / Sistema

---

## Funcionalidad 1: Autenticación (CU-O01, CU-O02)

Permite a cualquier usuario registrado iniciar y cerrar sesión, obteniendo un token válido para el resto de sus interacciones con el sistema.

### RF-SEG-001 — Iniciar sesión
El sistema debe permitir a un usuario autenticarse con correo y contraseña. Valida las credenciales contra `usuarios`; si son correctas y la cuenta está activa, genera un token de sesión y redirige al panel correspondiente a `tipo_actor`/`rol_id`. Si las credenciales son incorrectas, muestra "Credenciales incorrectas" sin indicar cuál de los dos campos falló, y registra el intento fallido en auditoría (CU-O41). Si la cuenta está inactiva (`usuarios.activo = false`), muestra "Cuenta desactivada. Contacte al administrador." y no emite token.

### RF-SEG-002 — Cerrar sesión
El sistema debe invalidar el token de sesión activo del usuario al solicitarlo, y redirigirlo a la pantalla de inicio de sesión.

### RNF-SEG-001 — Almacenamiento seguro de credenciales
Ninguna contraseña se almacena ni se transmite en texto plano; se persiste únicamente su hash. Refuerza REG-B3.

### RNF-SEG-002 — Tiempo de respuesta del login
La validación de credenciales y emisión de token responde en menos de 1 segundo bajo condiciones normales de carga, para no introducir fricción en el camino de autoservicio (REG-G1).

---

## Funcionalidad 2: Verificar sesión activa (CU-O42)

Servicio transversal, `<<include>>` obligatorio de prácticamente toda acción autenticada del sistema (todas excepto CU-O01, O03, O04, O07). No se invoca directamente por un actor humano.

### RF-SEG-003 — Verificación de token en cada solicitud autenticada
El sistema debe validar, antes de procesar cualquier solicitud que requiera sesión, que el token presentado existe, no ha expirado y corresponde a un usuario activo. Si la validación falla, la solicitud se rechaza y el usuario es redirigido a iniciar sesión; en flujos multi-paso (p. ej. checkout de reserva), el estado ya ingresado en pasos previos se preserva para no perder el progreso al reautenticarse (REG-J10, ver QP-11 en `analisis-cus-completo.md`).

### RNF-SEG-003 — Costo de verificación
La verificación de sesión no debe añadir una latencia perceptible (objetivo: <50ms) a ninguna solicitud, dado que se ejecuta en prácticamente el 100% del tráfico autenticado del sistema.

---

## Funcionalidad 3: Recuperar y restablecer contraseña (CU-O03, CU-O04)

Permite a cualquier usuario registrado recuperar el acceso a su cuenta sin intervención de un administrador.

### RF-SEG-004 — Solicitar enlace de recuperación de contraseña
El sistema debe permitir a cualquier usuario ingresar su correo y, si existe una cuenta asociada, generar un enlace de un solo uso con expiración y enviarlo por correo. Independientemente de si el correo existe o no en el sistema, se muestra el mismo mensaje genérico de confirmación, para no revelar qué correos están registrados.

### RF-SEG-005 — Restablecer contraseña vía enlace
El sistema debe permitir, a partir de un enlace válido y no expirado, ingresar una nueva contraseña con confirmación. Valida la fortaleza de la contraseña, la actualiza, invalida el enlace de un solo uso y notifica el cambio exitoso. Si el enlace expiró o ya fue usado, rechaza el restablecimiento y ofrece generar uno nuevo. Si las contraseñas no coinciden o no cumplen la política mínima, rechaza con mensaje específico por campo.

### RNF-SEG-004 — Expiración configurable del enlace de recuperación
El tiempo de vida del enlace de recuperación se lee de `configuracion_sistema` (categoría `expiraciones`); mientras el nivel Táctico (CU-T14) no exista, se usa un valor por defecto de 30 minutos documentado en el código.

---

## Funcionalidad 4: Gestión de perfil propio (CU-O05, CU-O06)

Permite a cualquier usuario autenticado ver, editar sus propios datos y cambiar su contraseña sin intervención de un administrador.

### RF-SEG-006 — Ver y editar perfil propio
El sistema debe mostrar a todo usuario autenticado sus propios datos (`usuarios`, y si es pasajero, también `pasajeros`) y permitirle editar los campos no sensibles (nombre, teléfono, dirección de facturación, contacto de emergencia, género). El correo electrónico, por ser identificador de acceso, requiere un flujo de verificación adicional para cambiarse — fuera de alcance de esta versión (queda registrado como error conocido si se solicita antes de implementarse).

### RF-SEG-007 — Cambiar contraseña (autenticado)
El sistema debe permitir a un usuario autenticado cambiar su contraseña ingresando la contraseña actual y la nueva (con confirmación). Valida la contraseña actual antes de aceptar el cambio.

### RF-SEG-017 — Solicitar eliminación de datos personales
El sistema debe ofrecer, desde el perfil propio, una vía para que el usuario solicite la eliminación de sus datos personales (REG-C2). Ver RN-SEG-011 para las condiciones de retención cuando existen reservas o pagos en curso — la ejecución efectiva de la eliminación sobre el perfil extendido de pasajero se coordina con `pasajeros-spec.md`.

---

## Funcionalidad 5: Registrar nuevo pasajero (CU-O07)

Alta autoservicio de cuentas de pasajero, sin intervención de un agente.

### RF-SEG-008 — Registrar nuevo pasajero (autoservicio)
El sistema debe permitir a cualquier visitante crear una cuenta de pasajero ingresando: nombre completo, fecha de nacimiento, correo, teléfono y contraseña (obligatorios); género, número de documento, dirección de facturación y contacto de emergencia (opcionales). Valida formato y unicidad del correo antes de crear el registro. Al crear exitosamente, envía correo de verificación y redirige al login. Si el correo ya está registrado, rechaza con mensaje de duplicado.

### RNF-SEG-005 — Sin verificación documental para vuelos domésticos EE. UU.
El registro no solicita ni permite subir ninguna imagen de documento de identidad; el número de documento, si se declara, es un campo de texto sin verificación (ver `consideraciones.md` sección 3).

---

## Funcionalidad 6: Gestionar usuarios internos (CU-O08)

Administración de cuentas de Agente y Administrador — distinta del autoservicio de pasajeros.

### RF-SEG-009 — Gestionar usuarios internos
El sistema debe permitir a un Administrador crear, editar y desactivar cuentas de Agente y Administrador, asignándoles un rol obligatorio (`usuarios.rol_id`). Esta acción incluye `<<include>>` la verificación de permisos RBAC (CU-O43) y el registro de auditoría (CU-O41).

---

## Funcionalidad 7: Gestión de roles (CU-O09, CU-O10, CU-O11)

Catálogo de roles y sus permisos, base del RBAC de dos niveles (REG-B1).

### RF-SEG-010 — Crear rol
El sistema debe permitir a un Administrador crear un rol nuevo con nombre y descripción, inicialmente sin permisos asignados.

### RF-SEG-011 — Editar rol
El sistema debe permitir a un Administrador modificar el nombre/descripción de un rol y su matriz de permisos: Nivel 1 (`roles_permisos` — qué módulos puede usar) y Nivel 2 (`roles_permisos_tablas` — a qué tablas específicas dentro de un módulo ya autorizado se restringe). El Nivel 2 nunca puede otorgar acceso a un módulo no autorizado en Nivel 1 (RN-SEG-009).

### RF-SEG-012 — Eliminar rol
El sistema debe permitir a un Administrador eliminar un rol, siempre que no esté marcado como protegido (`roles.es_sistema = true`) y no tenga usuarios activos asignados actualmente (RN-SEG-008). Si tiene usuarios asignados, el sistema bloquea la eliminación y ofrece reasignar esos usuarios a otro rol primero.

---

## Funcionalidad 8: Verificar permisos de acceso — RBAC (CU-O43)

Servicio transversal, `<<include>>` de toda acción de Agente/Administrador (CU-O08, O16, O22, O35, O36, O37).

### RF-SEG-013 — Verificación RBAC de dos niveles
El sistema debe validar, antes de ejecutar cualquier acción de Agente/Administrador, que el rol del usuario tiene permiso de Nivel 1 sobre el módulo correspondiente y, si aplica una restricción de Nivel 2, que la tabla específica también está autorizada. Si la validación falla, la acción se bloquea antes de tocar datos, y el bloqueo se comunica visualmente de forma explícita (REG-J6), nunca como ausencia silenciosa de datos.

---

## Funcionalidad 9: Auditoría (CU-O12, CU-O13, CU-O41)

Log inmutable de toda mutación del sistema, y su consulta por un Administrador.

### RF-SEG-014 — Registrar evento en auditoría
El sistema debe insertar, en el punto donde ocurre cualquier mutación de datos en cualquier módulo, un registro en `auditoria` con: usuario autenticado (nullable si la acción es automática del sistema), acción realizada, módulo y tabla afectada, detalle, IP (si aplica) y resultado. El registro es de solo inserción — nunca se edita ni se elimina (REG-B4). Si la inserción del registro de auditoría fallara, el sistema no revierte la acción original ya realizada, pero alerta al Administrador, dado que un fallo de auditoría es en sí mismo un evento crítico.

### RF-SEG-015 — Ver log de auditoría
El sistema debe mostrar a un Administrador el log de auditoría en orden cronológico descendente, sin ningún control de edición o eliminación en su interfaz — la ausencia de esos controles es en sí misma la señal de que el registro es de solo inserción (REG-J6).

### RF-SEG-016 — Filtrar y exportar log de auditoría
El sistema debe permitir a un Administrador filtrar el log por usuario, acción, módulo/tabla y rango de fechas, aplicando cada filtro de forma instantánea sin botón "Aplicar" (REG-J9), y exportar el resultado filtrado a un archivo descargable.

### RNF-SEG-006 — Retención e inmutabilidad del log
Ningún proceso del sistema, incluyendo tareas de mantenimiento, puede editar o eliminar un registro de auditoría ya insertado. Cualquier necesidad futura de purga de registros antiguos pertenece al nivel Táctico (Configuración → Limpieza de datos) y queda fuera de alcance de este módulo.

---

## Reglas de negocio

- **RN-SEG-001** — Todo intento de login, exitoso o fallido, se audita (REG-B4).
- **RN-SEG-002** — Ninguna acción de creación/modificación/eliminación se considera completa hasta que su registro de auditoría correspondiente exista (REG-B4).
- **RN-SEG-003** — Al solicitar recuperación de contraseña, el sistema nunca revela si un correo está registrado o no; siempre responde con el mismo mensaje genérico.
- **RN-SEG-004** — El enlace de recuperación de contraseña es de un solo uso y expira tras el tiempo configurado (default 30 minutos mientras no exista CU-T14).
- **RN-SEG-005** — Toda contraseña nueva o restablecida debe cumplir la política mínima de fortaleza vigente (longitud y complejidad); el sistema rechaza contraseñas que no la cumplan con un mensaje específico.
- **RN-SEG-006** — El correo electrónico es único en todo el sistema; no puede haber dos cuentas (`usuarios`) con el mismo correo.
- **RN-SEG-007** — Un rol marcado como protegido (`roles.es_sistema = true`) no puede eliminarse ni perder su permiso base, sin importar quién lo solicite.
- **RN-SEG-008** — *(Nueva, resuelve QP-10)* No se puede eliminar un rol que tenga usuarios activos asignados actualmente; el sistema exige reasignar esos usuarios a otro rol antes de permitir la eliminación.
- **RN-SEG-009** — El RBAC de Nivel 2 (restricción por tabla) nunca amplía el acceso otorgado en Nivel 1; solo puede restringirlo.
- **RN-SEG-010** — El registro de auditoría es de solo inserción: ningún flujo del sistema, en ningún módulo, puede editarlo ni eliminarlo (REG-B4).
- **RN-SEG-011** — *(Nueva, resuelve QP-13)* Toda solicitud de eliminación de datos personales se resuelve respetando la retención mínima necesaria mientras existan reservas activas, pendientes de pago, o pagos/reembolsos en curso asociados al usuario; el sistema informa explícitamente al usuario qué datos no pueden eliminarse todavía y por qué (REG-C2, REG-C3).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /login` | — | HTML con formulario de inicio de sesión |
| `POST /login` | Correo, contraseña | Cookie/token JWT + redirección al panel del rol, o mensaje de error |
| `POST /logout` | Cookie JWT | Invalidación de sesión + redirección a `/login` |
| `GET /recuperar-password` | — | HTML con formulario de solicitud de enlace |
| `POST /recuperar-password` | Correo | Mensaje genérico de confirmación (envía correo si la cuenta existe) |
| `GET /restablecer-password/{token}` | Token en URL | HTML con formulario de nueva contraseña, o mensaje de enlace inválido |
| `POST /restablecer-password/{token}` | Token, nueva contraseña, confirmación | Confirmación de cambio o mensaje de error |
| `GET /mi-perfil` | Cookie JWT | HTML con datos del usuario autenticado |
| `POST /mi-perfil` | Cookie JWT, campos editables | JSON/HTML con perfil actualizado |
| `POST /mi-perfil/cambiar-password` | Cookie JWT, contraseña actual, nueva | Confirmación o mensaje de error |
| `POST /mi-perfil/solicitar-eliminacion` | Cookie JWT | Confirmación de solicitud o detalle de datos retenidos (RN-SEG-011) |
| `GET /registro` | — | HTML con formulario de alta de pasajero |
| `POST /registro` | Datos de pasajero (tabla CU-O07) | Redirección a login + correo de verificación, o mensaje de duplicado |
| `GET /admin/usuarios` | Cookie JWT (Admin), query params | HTML/JSON con listado de usuarios internos |
| `POST /admin/usuarios` | Cookie JWT (Admin), datos de usuario + rol | Usuario creado o mensaje de error |
| `PUT /admin/usuarios/{id}` | Cookie JWT (Admin), campos a editar | Usuario actualizado |
| `GET /admin/roles` | Cookie JWT (Admin) | HTML/JSON con catálogo de roles |
| `POST /admin/roles` | Cookie JWT (Admin), nombre, descripción | Rol creado |
| `PUT /admin/roles/{id}` | Cookie JWT (Admin), permisos Nivel 1/2 | Rol actualizado |
| `DELETE /admin/roles/{id}` | Cookie JWT (Admin) | Rol eliminado, o mensaje de bloqueo (RN-SEG-008) |
| `GET /admin/auditoria` | Cookie JWT (Admin), filtros | HTML/JSON con log de auditoría filtrado |
| `GET /admin/auditoria/exportar` | Cookie JWT (Admin), filtros | Archivo descargable (CSV/PDF) con el log filtrado |

---

## Historias de usuario

- **HU-SEG-01:** Como pasajero, quiero iniciar sesión con mi correo y contraseña, para acceder a mi cuenta y mis reservas.
- **HU-SEG-02:** Como usuario autenticado, quiero cerrar sesión, para proteger mi cuenta en dispositivos compartidos.
- **HU-SEG-03:** Como usuario que olvidó su contraseña, quiero solicitar un enlace de recuperación, para volver a acceder a mi cuenta sin depender de un administrador.
- **HU-SEG-04:** Como usuario con un enlace de recuperación válido, quiero establecer una nueva contraseña, para completar el restablecimiento.
- **HU-SEG-05:** Como usuario autenticado, quiero ver y editar mi perfil, para mantener mis datos de contacto actualizados.
- **HU-SEG-06:** Como usuario autenticado, quiero cambiar mi contraseña, para mantener mi cuenta segura.
- **HU-SEG-07:** Como visitante, quiero crear una cuenta de pasajero, para poder buscar y reservar vuelos.
- **HU-SEG-08:** Como administrador, quiero gestionar las cuentas de agentes y administradores, para controlar quién tiene acceso operativo interno.
- **HU-SEG-09:** Como administrador, quiero crear roles con permisos específicos, para adaptar el acceso a la estructura real del equipo.
- **HU-SEG-10:** Como administrador, quiero editar los permisos de un rol existente, para ajustar el acceso cuando cambian las responsabilidades de un equipo.
- **HU-SEG-11:** Como administrador, quiero eliminar un rol que ya no se usa, para mantener el catálogo de roles limpio y consistente.
- **HU-SEG-12:** Como administrador, quiero ver el log de auditoría, para monitorear la actividad del sistema en tiempo real.
- **HU-SEG-13:** Como administrador, quiero filtrar y exportar el log de auditoría, para investigar un incidente o generar un reporte de cumplimiento.
- **HU-SEG-14:** Como usuario autenticado, quiero solicitar la eliminación de mis datos personales, para ejercer mi derecho sobre mi propia información.

---

## Objetivo

Proveer la base de identidad, control de acceso y trazabilidad de todo el sistema AeroTrack Travel: quién puede autenticarse, qué puede hacer cada rol, y qué queda registrado de forma inmutable cuando algo cambia. Ningún otro módulo operativo puede considerarse completo sin apoyarse en Seguridad para verificar sesión, verificar permisos y auditar sus propias mutaciones — es, junto con Pasajeros, el módulo del que dependen los otros cinco.

---

## Escenarios

### Camino feliz (autenticación + sesión)
1. Un pasajero se registra (CU-O07) con sus datos obligatorios.
2. El sistema crea su cuenta y le permite iniciar sesión (CU-O01).
3. El sistema emite un token de sesión y lo redirige a su panel.
4. En cada acción posterior, el sistema verifica su sesión activa (CU-O42) de forma transparente.
5. El pasajero edita su perfil (CU-O05) o cambia su contraseña (CU-O06) cuando lo necesita.
6. Al terminar, cierra sesión (CU-O02).

### Camino feliz (administración de roles y auditoría)
1. Un Administrador crea un rol nuevo (CU-O09).
2. Le asigna permisos de Nivel 1 (módulos) y, si aplica, restricciones de Nivel 2 (tablas) (CU-O10).
3. Asigna ese rol a un nuevo usuario interno (CU-O08).
4. Cada acción de creación queda registrada en auditoría (CU-O41), visible y filtrable por el Administrador (CU-O12, CU-O13).

### Manejo de errores
- **Credenciales incorrectas:** el sistema muestra "Credenciales incorrectas" sin precisar cuál campo falló, y audita el intento fallido.
- **Cuenta inactiva:** el sistema muestra "Cuenta desactivada. Contacte al administrador." y no emite token.
- **Correo ya registrado:** el registro de pasajero se rechaza con mensaje de duplicado (RN-SEG-006).
- **Enlace de recuperación expirado o ya usado:** se rechaza el restablecimiento y se ofrece generar uno nuevo.
- **Contraseñas no coinciden o no cumplen la política:** se rechaza con mensaje específico por campo.
- **Eliminación de rol con usuarios asignados:** se bloquea con mensaje explícito y opción de reasignar usuarios primero (RN-SEG-008).
- **Acción fuera de la matriz RBAC:** se bloquea antes de tocar datos, comunicado visualmente (REG-J6).
- **Fallo en la inserción de auditoría:** la acción original no se revierte, pero se alerta al Administrador (RF-SEG-014).
- **Solicitud de eliminación de datos con reserva activa:** se informa qué datos no pueden eliminarse todavía y por qué (RN-SEG-011).

---

## Criterios de aceptación

- **CU-O01:** Dado que un usuario tiene una cuenta activa, cuando ingresa correo y contraseña correctos, entonces obtiene un token de sesión y es redirigido a su panel.
- **CU-O02:** Dado que un usuario tiene una sesión activa, cuando solicita cerrar sesión, entonces su token se invalida y es redirigido al login.
- **CU-O03:** Dado que un usuario ingresa un correo (exista o no en el sistema), cuando solicita recuperación, entonces recibe el mismo mensaje genérico de confirmación.
- **CU-O04:** Dado que un usuario abre un enlace de recuperación válido, cuando ingresa una nueva contraseña que cumple la política, entonces su contraseña se actualiza y el enlace queda invalidado.
- **CU-O05:** Dado que un usuario está autenticado, cuando accede a su perfil, entonces puede ver y editar sus datos no sensibles.
- **CU-O06:** Dado que un usuario autenticado ingresa su contraseña actual correcta y una nueva válida, cuando confirma el cambio, entonces su contraseña se actualiza.
- **CU-O07:** Dado que un visitante ingresa datos válidos y un correo no registrado, cuando envía el formulario de registro, entonces se crea su cuenta de pasajero y puede iniciar sesión.
- **CU-O08:** Dado que un Administrador con permiso RBAC crea o edita un usuario interno, cuando confirma la acción, entonces el usuario queda creado/actualizado con el rol asignado.
- **CU-O09:** Dado que un Administrador solicita crear un rol con nombre válido, cuando confirma, entonces el rol queda creado sin permisos asignados.
- **CU-O10:** Dado que un Administrador edita los permisos Nivel 1/2 de un rol existente, cuando confirma, entonces la matriz de permisos del rol queda actualizada, sin que Nivel 2 amplíe lo autorizado en Nivel 1.
- **CU-O11:** Dado que un rol no está protegido y no tiene usuarios asignados, cuando un Administrador solicita eliminarlo, entonces el rol se elimina; si tiene usuarios asignados, la eliminación se bloquea.
- **CU-O12:** Dado que un Administrador accede al log de auditoría, cuando lo consulta, entonces ve los registros en orden cronológico descendente sin controles de edición/eliminación.
- **CU-O13:** Dado que un Administrador aplica filtros sobre el log de auditoría, cuando solicita exportar, entonces recibe un archivo descargable con el resultado filtrado.
- **CU-O41:** Dado que ocurre una mutación de datos en cualquier módulo, cuando la operación se ejecuta, entonces queda un registro inmutable en auditoría con usuario, acción, módulo/tabla y resultado.
- **CU-O42:** Dado que llega una solicitud a una ruta que requiere sesión, cuando el token es inválido o expiró, entonces la solicitud se rechaza y el usuario es redirigido a iniciar sesión sin perder el progreso de un flujo multi-paso.
- **CU-O43:** Dado que un Agente/Administrador solicita una acción sobre un módulo/tabla, cuando su rol no tiene el permiso correspondiente en la matriz RBAC, entonces la acción se bloquea antes de tocar datos.

---

## Dependencias

- **Ninguna hacia otros módulos operativos** — Seguridad es la base del sistema (ver `analisis-cus-completo.md`, sección 3.3).
- **Pasajeros:** CU-O07 crea el registro `usuarios` y coordina con `pasajeros-spec.md` para el perfil extendido (1:1); RF-SEG-017 coordina con Pasajeros para la ejecución de eliminación de datos.
- **Todos los demás módulos (Pasajeros, Vuelos, Reservas, Disrupciones, Facturación):** consumen CU-O41 (auditoría), CU-O42 (sesión) y, cuando la acción es de Agente/Administrador, CU-O43 (RBAC), sin excepción.
- **Nivel Táctico (previsto):** CU-T14 (tiempo de expiración del enlace de recuperación) y CU-T01-T03 (permisos de módulo/tabla en detalle) refinarán RNF-SEG-004 y RF-SEG-011 cuando existan; mientras tanto, este módulo usa los valores por defecto documentados.

---

## Casos de uso relacionados

- CU-O14, O15, O16 (Pasajeros) — consumen sesión y RBAC de este módulo.
- CU-O21-O26 (Reservas), CU-O32-O40 (Facturación) — consumen auditoría, sesión y, en acciones de Agente, RBAC.
- CU-O44 (Expirar reserva pendiente) — acción automática del sistema, también queda auditada vía CU-O41.
- CU-T01-T03 (previsto, Táctico) — matriz de permisos de módulo × rol × tabla, ampliará la gestión de roles de este módulo.
- CU-T14 (previsto, Táctico) — configuración del tiempo de expiración del enlace de recuperación.

---

## Fuera de alcance

- Matriz de permisos por tabla en detalle de configuración táctica (CU-T01-T03) — este módulo implementa el mecanismo (RF-SEG-011, RF-SEG-013), no su panel de configuración avanzado.
- Cambio de correo electrónico de una cuenta existente (requiere flujo de re-verificación no cubierto en esta versión).
- Autenticación multifactor (MFA) — no forma parte del catálogo de CU operativos actual.
- Purga o retención automatizada de registros de auditoría antiguos — pertenece al nivel Táctico (Configuración → Limpieza de datos).
- Panel general de configuración (SMTP, credenciales de API, plantillas) — CU-T04-T17, nivel Táctico previsto.

---

## Requerimientos de configuración

### RNF-SEG-007 — Parámetros leídos de `configuracion_sistema`
Mientras no exista el nivel Táctico, este módulo lee de `configuracion_sistema` (con valores por defecto documentados en código si la clave no existe) al menos: tiempo de expiración del enlace de recuperación de contraseña (`categoria = expiraciones`, default 30 minutos) y política mínima de fortaleza de contraseña. Ningún valor de estas categorías se hardcodea fuera de este mecanismo (REG-B3).
