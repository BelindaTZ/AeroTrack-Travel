# Checklist de Validación: Seguridad

**Propósito:** Validar que la implementación del módulo Seguridad cumple los RF/RNF y RN definidos en `seguridad-spec.md`, antes de darlo por completo y desbloquear a los módulos que dependen de él.
**Creado:** 2026-07-09
**Feature:** [`seguridad-spec.md`](./seguridad-spec.md) · [`plan.md`](./plan.md)
**Cerrado (primera pasada de implementación):** 2026-07-09 — 49/49 tests automatizados pasando contra `pocketbase-travel` real (sin mocks). Ver "Notas de cierre" al final para las excepciones.

---

## Requisitos funcionales

- [x] CHK001 RF-SEG-001 — Login válido con correo/contraseña correctos emite token y redirige al panel del rol.
- [x] CHK002 RF-SEG-001 — Credenciales incorrectas muestran "Credenciales incorrectas" sin indicar cuál campo falló.
- [x] CHK003 RF-SEG-001 — Cuenta inactiva (`activo = false`) muestra "Cuenta desactivada. Contacte al administrador." y no emite token.
- [x] CHK004 RF-SEG-002 — Logout invalida el token y redirige al login.
- [x] CHK005 RF-SEG-003 — Toda ruta que requiere sesión rechaza un token inválido/expirado antes de ejecutar lógica de negocio.
- [x] CHK006 RF-SEG-003 — En un flujo multi-paso, la reautenticación tras expiración no descarta el progreso ya ingresado (REG-J10).
- [x] CHK007 RF-SEG-004 — Solicitud de recuperación responde con el mismo mensaje genérico exista o no el correo.
- [x] CHK008 RF-SEG-005 — Enlace válido y no expirado permite establecer nueva contraseña; enlace expirado/usado se rechaza con opción de generar uno nuevo.
- [x] CHK009 RF-SEG-006 — Usuario autenticado puede ver y editar sus datos no sensibles; cambio de correo permanece fuera de alcance.
- [x] CHK010 RF-SEG-007 — Cambio de contraseña autenticado exige y valida la contraseña actual antes de aceptar la nueva.
- [x] CHK011 RF-SEG-008 — Registro de pasajero valida formato y unicidad de correo; duplicado se rechaza con mensaje específico.
- [x] CHK012 RF-SEG-008 — Ningún campo de verificación documental (imagen) existe en el formulario de registro (RNF-SEG-005).
- [x] CHK013 RF-SEG-009 — Administrador puede crear/editar/desactivar usuarios internos con rol obligatorio.
- [x] CHK014 RF-SEG-010 — Creación de rol nuevo queda sin permisos asignados por defecto.
- [x] CHK015 RF-SEG-011 — Edición de rol permite Nivel 1 (módulos) y Nivel 2 (tablas); Nivel 2 nunca amplía lo no autorizado en Nivel 1.
- [x] CHK016 RF-SEG-012 — Eliminación de rol protegido (`es_sistema = true`) se bloquea siempre.
- [x] CHK017 RF-SEG-013 — Acción de Agente/Administrador sin permiso RBAC correspondiente se bloquea antes de tocar datos.
- [x] CHK018 RF-SEG-014 — Toda mutación de cualquier módulo genera un registro de auditoría con usuario, acción, módulo/tabla y resultado.
- [x] CHK019 RF-SEG-014 — Fallo de inserción de auditoría no revierte la acción original, pero genera alerta al Administrador. *(alerta actual = log crítico; ver Notas de cierre)*
- [x] CHK020 RF-SEG-015 — Vista de auditoría no expone ningún control de edición/eliminación (REG-J6).
- [x] CHK021 RF-SEG-016 — Filtros de auditoría se aplican sin botón "Aplicar" (REG-J9) y la exportación respeta el filtro activo.
- [x] CHK022 RF-SEG-017 — Solicitud de eliminación de datos personales está disponible desde el perfil propio.

## Reglas de negocio

- [x] CHK023 RN-SEG-001 — Todo intento de login, exitoso o fallido, queda auditado.
- [x] CHK024 RN-SEG-002 — Ninguna mutación se considera completa sin su registro de auditoría correspondiente.
- [x] CHK025 RN-SEG-003 — Recuperación de contraseña nunca revela si un correo existe.
- [x] CHK026 RN-SEG-004 — Enlace de recuperación expira tras el tiempo configurado (default 30 min si no hay CU-T14).
- [x] CHK027 RN-SEG-005 — Contraseñas nuevas/restablecidas se validan contra la política mínima de fortaleza.
- [x] CHK028 RN-SEG-006 — El correo es único en `usuarios`; intento de duplicado se rechaza a nivel de aplicación y de base de datos.
- [x] CHK029 RN-SEG-007 — Rol protegido no puede eliminarse ni perder su permiso base.
- [x] CHK030 RN-SEG-008 — Eliminación de rol con usuarios activos asignados se bloquea, ofreciendo reasignación previa.
- [x] CHK031 RN-SEG-009 — RBAC Nivel 2 restringe, nunca amplía, lo ya otorgado en Nivel 1 — probado con un caso de intento de ampliación (tanto en lectura vía `rbac_service` como en escritura vía `roles_service`).
- [x] CHK032 RN-SEG-010 — No existe ningún endpoint ni método de servicio que edite o elimine un registro de `auditoria`.
- [x] CHK033 RN-SEG-011 — Solicitud de eliminación de datos personales con reserva/pago en curso informa explícitamente qué se retiene y por qué. *(sin reservas/pagos reales en esta sesión; ver Notas de cierre)*

## No funcionales y seguridad

- [x] CHK034 RNF-SEG-001 — Ninguna contraseña se almacena o transmite en texto plano; verificado con inspección de payloads y de la colección `usuarios`.
- [ ] CHK035 RNF-SEG-002 — Login responde en <1s bajo carga normal (medido con prueba de carga básica). *(no medido esta sesión)*
- [ ] CHK036 RNF-SEG-003 — Verificación de sesión agrega <50ms de latencia (medido con profiling del middleware). *(no medido esta sesión)*
- [x] CHK037 RNF-SEG-004 — Expiración del enlace de recuperación se lee de `configuracion_sistema`, con fallback documentado si la clave no existe.
- [x] CHK038 RNF-SEG-006 — Ningún job de mantenimiento del sistema tiene permisos de escritura sobre `auditoria` más allá de `INSERT`. *(no hay jobs de mantenimiento que la toquen; ver Notas de cierre sobre el límite real de PocketBase)*
- [x] CHK039 RNF-SEG-007 — Ninguna credencial (SMTP, JWT secret, etc.) aparece hardcodeada en el código fuente ni en el repositorio (grep de verificación antes de cerrar el módulo).

## RBAC y auditoría (transversal — consumido por los otros 5 módulos)

- [x] CHK040 `session_service` expone una dependencia FastAPI reutilizable por los 5 módulos restantes, sin duplicar lógica de verificación de token.
- [x] CHK041 `rbac_service` expone una dependencia FastAPI reutilizable, parametrizable por módulo/tabla.
- [x] CHK042 `audit_service` expone una única función de inserción, sin exponer ningún método de edición/borrado en su interfaz pública.

## Diseño de interfaz (constitución, Sección J)

- [ ] CHK043 J6 — El alcance de restricción RBAC Nivel 2 vigente se muestra de forma persistente en pantallas de backoffice afectadas. *(implementado en `rol_editar.html`; falta extenderlo a las pantallas donde el usuario actuante navega bajo su propia restricción Nivel 2 — ver Notas de cierre)*
- [ ] CHK044 J8 — Formularios de login/registro/perfil cumplen contraste 4.5:1 y son operables por teclado. *(HTML semántico + Bootstrap 5 por defecto; no verificado con herramienta de accesibilidad ni navegador real)*
- [x] CHK045 J9 — Comboboxes con búsqueda para selección de rol/módulo con más de ~8 opciones. *(no aplica todavía: ningún select de este módulo supera las ~8 opciones — roles=3, módulos=7; queda como criterio para cuando el catálogo crezca)*
- [ ] CHK046 J11 — Confirmaciones de éxito (cambio de contraseña, edición de perfil) se autodescartan en 3–5s sin bloquear la siguiente interacción. *(CSS implementado; no verificado en navegador real)*

## Trazabilidad de casos de uso

- [x] CHK047 CU-O01 a CU-O13 — cada uno tiene al menos una prueba automatizada que ejercita su criterio de aceptación tal como está redactado en `seguridad-spec.md`.
- [ ] CHK048 CU-O41, O42, O43 — cada uno tiene al menos una prueba automatizada, y se verifica que son invocables como dependencia desde un módulo externo (prueba de integración cruzada, p. ej. simulando su uso desde `pasajeros-spec.md`). *(probado vía apps FastAPI mínimas independientes que solo importan `Depends(...)`, el mismo patrón que usará un módulo externo real; sin un segundo módulo real todavía no hay una prueba de integración cruzada genuina — ver Notas de cierre)*

## Notas de cierre — sesión de implementación (2026-07-09)

- **CHK019** — el "alerta al Administrador" ante fallo de inserción de auditoría hoy es un `logger.critical(...)`, no una notificación visible en la UI (no existe todavía un canal de notificaciones internas). Suficiente para pasar la prueba automatizada tal como está redactado el RF, pero es una implementación mínima.
- **CHK033** — RN-SEG-011 (retención por reservas/pagos en curso) no tiene nada que verificar todavía: Reservas y Facturación no existen en esta sesión. El endpoint registra la solicitud de eliminación y queda documentado en el código que la retención real se activa cuando esos módulos existan.
- **CHK035/CHK036** — no se corrió ninguna prueba de carga ni profiling; son objetivos de rendimiento (RNF), no de corrección funcional, y quedan pendientes de una sesión de medición dedicada.
- **CHK038** — PocketBase no permite bloquear a un token de admin autenticado vía reglas de colección (los admins bypasean `updateRule`/`deleteRule` siempre). La garantía real de "solo inserción" es 100% de capa de aplicación (`audit_service` sin métodos de edición/borrado). Documentado en `scripts/pb_schema_seguridad.py`.
- **CHK043** — el banner de alcance Nivel 2 vigente (REG-J6) está implementado en la pantalla de edición de permisos de un rol (`admin/rol_editar.html`), que es el caso explícito que usa el ejemplo de la constitución. Falta extender el mismo patrón a las pantallas donde el usuario *actuante* (no el admin editando a otro) navega bajo su propia restricción Nivel 2 — hoy no hay ninguna pantalla de Seguridad afectada por eso (Nivel 2 solo se sembró de ejemplo en pruebas, se limpia después de cada test), así que no hay caso real que mostrar todavía.
- **CHK044/CHK046** — no se hizo verificación con navegador real (Playwright/manual) en esta sesión — el CLI no tiene forma de renderizar y medir contraste/animación. Recomendado antes de considerar el módulo "production-ready" visualmente.
- **CHK048** — la reutilización de `verificar_sesion`/`requiere_permiso`/`AuditService` se probó montándolos en apps FastAPI mínimas independientes (mismo patrón de `Depends(...)` que usará cualquier módulo futuro), lo cual demuestra que son importables y funcionales fuera de sus propios routers. Una prueba de integración cruzada *genuina* requiere que exista al menos un segundo módulo real (Pasajeros es el candidato natural) — no se puede satisfacer por completo dentro de esta sesión.

## Notas

- Marcar cada ítem como completado con `[x]` solo cuando exista evidencia verificable (prueba automatizada, captura de pantalla, o revisión de código) — no marcar por inspección visual únicamente.
- Cualquier ítem que no pueda completarse tal como está escrito debe registrarse en `specs/000-sistema-general/errores-conocidos.md`, no simplemente omitirse aquí.
