# Especificación Táctica — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Código fuente:** `app/seguridad/` *(nivel Operativo ya implementado y probado — ver `specs/operativo/seguridad/`; este nivel agrega routers/servicios nuevos sobre el mismo paquete)*
**Casos de uso cubiertos:** CU-T01 (Monitorear intentos fallidos de autenticación), CU-T02 (Forzar expiración de sesiones activas de un usuario), CU-T03 (Configurar política de contraseñas y duración de sesión), CU-T35 (Ver matriz de permisos actual)
**Actor:** Administrador

> **Estado:** nivel nuevo, sin código propio todavía — pero **los 4 CU de este nivel son extensiones directas de servicios ya implementados y probados** en el nivel Operativo (`auth_service`, `session_service`, `rbac_service`, `roles_service`, todos con 49/49 tests reales pasando). Ninguno requiere colección nueva ni integración externa nueva — son lectura/configuración sobre datos que Seguridad Operativo ya genera (`auditoria`, `usuarios`, `configuracion_sistema`, `roles_permisos`/`roles_permisos_tablas`).

---

## Funcionalidad 1: Monitorear intentos fallidos de autenticación (CU-T01)

### RF-SEG-T01 — Monitorear intentos fallidos de autenticación (dashboard de seguridad)
El sistema debe mostrar a un Administrador un dashboard de intentos de login fallidos recientes, leído de `auditoria` (RN-SEG-001, Operativo, ya audita todo intento exitoso/fallido) filtrado por `accion = login_fallido`, agrupado por usuario/IP para detectar patrones de fuerza bruta. Filtros instantáneos (REG-J9).

### RN-SEG-T01 — Este dashboard no introduce un mecanismo de bloqueo nuevo
CU-T01 es solo visibilidad — el bloqueo de cuenta tras N intentos fallidos, si se decide implementar, es un RF nuevo separado (ver Fuera de alcance), no algo que este CU haga implícitamente.

---

## Funcionalidad 2: Forzar expiración de sesiones activas (CU-T02)

### RF-SEG-T02 — Forzar expiración de sesiones activas de un usuario
El sistema debe permitir a un Administrador invalidar de inmediato todas las sesiones activas de un usuario específico (reutiliza el mecanismo de `session_service.verificar_sesion` ya implementado — invalida el token en vez de solo dejarlo expirar naturalmente), útil ante sospecha de cuenta comprometida.

### RN-SEG-T02 — Forzar expiración es una acción de Administrador, auditada como cualquier mutación
Esta acción incluye `<<include>>` RBAC (CU-O43) y auditoría (CU-O41), igual que cualquier otra acción administrativa — no es una excepción al patrón ya establecido.

---

## Funcionalidad 3: Configurar política de contraseñas y sesión (CU-T03)

### RF-SEG-T03 — Configurar política de contraseñas y duración de sesión
El sistema debe permitir a un Administrador editar, en `configuracion_sistema`, la política mínima de fortaleza de contraseña (ya consumida por RNF-SEG-007, Operativo, con default hardcodeado hasta ahora) y la duración de sesión antes de expirar. **Cierra un hueco real**: RNF-SEG-007 (Operativo) ya lee estos valores de `configuracion_sistema` con fallback documentado — este CU es la primera vez que existe una UI real para editarlos, en vez de requerir tocar la base de datos directamente.

---

## Funcionalidad 4: Ver matriz de permisos actual (CU-T35)

### RF-SEG-T04 — Ver matriz de permisos actual (roles × módulos × tablas)
El sistema debe mostrar a un Administrador una matriz completa de roles × módulos (Nivel 1, `roles_permisos`) × tablas (Nivel 2, `roles_permisos_tablas`) — datos que RF-SEG-011 (Operativo, CU-O10/O112/O113) ya genera y que hoy solo son consultables editando un rol a la vez. Esta es la primera vista agregada de toda la matriz a la vez.

---

## Reglas de negocio

- **RN-SEG-T01** — *(Funcionalidad 1)* El dashboard de intentos fallidos es solo visibilidad, no introduce bloqueo automático.
- **RN-SEG-T02** — *(Funcionalidad 2)* Forzar expiración de sesión es una acción administrativa auditada, con RBAC.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/seguridad/intentos-fallidos` | Cookie JWT (Admin), filtros | HTML/JSON con intentos fallidos agrupados |
| `POST /backoffice/seguridad/usuarios/{id}/forzar-expiracion` | Cookie JWT (Admin) | Todas las sesiones del usuario invalidadas |
| `GET/POST /backoffice/seguridad/politica` | Cookie JWT (Admin), longitud mínima, duración de sesión | Política actualizada en `configuracion_sistema` |
| `GET /backoffice/seguridad/matriz-permisos` | Cookie JWT (Admin) | HTML/JSON con la matriz completa roles×módulos×tablas |

---

## Historias de usuario

- **HU-SEG-T01:** Como administrador, quiero ver intentos fallidos de login, para detectar posibles ataques de fuerza bruta.
- **HU-SEG-T02:** Como administrador, quiero forzar el cierre de todas las sesiones de un usuario, para reaccionar rápido ante una cuenta comprometida.
- **HU-SEG-T03:** Como administrador, quiero configurar la política de contraseñas y duración de sesión desde una UI, para no tener que editar la base de datos directamente.
- **HU-SEG-T04:** Como administrador, quiero ver la matriz completa de permisos, para auditar de un vistazo qué puede hacer cada rol.

---

## Objetivo

Dar al Administrador visibilidad y control operativo sobre la seguridad del sistema más allá de la gestión CU-por-CU ya existente — monitoreo de amenazas, respuesta rápida ante compromiso, configuración sin tocar la base de datos, y auditoría agregada de la matriz de permisos.

---

## Escenarios

### Camino feliz
1. Un Administrador nota un patrón sospechoso de intentos fallidos desde una IP (CU-T01) y fuerza la expiración de las sesiones del usuario afectado (CU-T02).
2. Ajusta la política de contraseñas para exigir mayor longitud mínima (CU-T03).
3. Revisa la matriz de permisos completa (CU-T35) para confirmar que ningún rol tiene acceso más amplio del esperado.

### Manejo de errores
- **Forzar expiración de un usuario sin sesiones activas:** no falla, simplemente no hay nada que invalidar.

---

## Criterios de aceptación

- **CU-T01:** Dado que existen intentos fallidos en `auditoria`, cuando un Administrador consulta el dashboard, entonces los ve agrupados y filtrables.
- **CU-T02:** Dado que un usuario tiene sesiones activas, cuando un Administrador fuerza su expiración, entonces todas quedan invalidadas de inmediato.
- **CU-T03:** Dado que un Administrador edita la política, cuando la guarda, entonces `RNF-SEG-007` (Operativo) usa esos valores en las siguientes validaciones.
- **CU-T35:** Dado que existen roles con permisos asignados, cuando un Administrador consulta la matriz, entonces ve todos los roles × módulos × tablas de una vez.

---

## Dependencias

- **Seguridad (Operativo):** este nivel reutiliza `session_service`, `rbac_service`, `roles_service`, `audit_service` ya implementados — no crea servicios paralelos.

---

## Casos de uso relacionados

- CU-O01 (Iniciar sesión, Operativo) — fuente de los intentos que monitorea CU-T01.
- CU-O42 (Verificar sesión activa, Operativo) — mecanismo que CU-T02 fuerza a expirar.
- CU-O10, O112, O113 (Editar rol/permisos, Operativo) — fuente de los datos que agrega CU-T35.

---

## Fuera de alcance

- Bloqueo automático de cuenta tras N intentos fallidos — CU-T01 es solo visibilidad; un mecanismo de bloqueo automático es una funcionalidad nueva no definida en el catálogo actual.
- Autenticación multifactor (MFA) — sigue fuera de alcance, mismo criterio que ya documentó `seguridad-spec.md` (Operativo).
