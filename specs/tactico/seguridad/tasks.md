# Tasks: Seguridad (Táctico)

**Input:** [`plan.md`](./plan.md) · [`seguridad-spec.md`](./seguridad-spec.md) · [`checklist.md`](./checklist.md)
**Código fuente:** `app/seguridad/` *(nivel Operativo ya implementado)*

---

## Fase 1: Dashboard de intentos fallidos y expiración forzada (RF-SEG-T01, T02)

- [ ] T001 `app/seguridad/router_dashboard_seguridad.py` — `GET /backoffice/seguridad/intentos-fallidos`, lee `auditoria` filtrado por `accion=login_fallido`, agrupa por usuario/IP (CHK001)
- [ ] T002 Filtro instantáneo (REG-J9, CHK002)
- [ ] T003 `router_dashboard_seguridad.py` — `POST /backoffice/seguridad/usuarios/{id}/forzar-expiracion`, reutiliza `session_service` para invalidar todos los tokens del usuario (CHK003)
- [ ] T004 Incluye RBAC y auditoría (CHK004, RN-SEG-T02)
- [ ] T005 [P] `app/seguridad/tests/test_dashboard_seguridad.py` — agrupación de intentos (CHK001), expiración forzada invalida sesiones reales (CHK003)

---

## Fase 2: Configurar política (RF-SEG-T03)

- [ ] T006 `app/seguridad/router_politica.py` — `GET/POST /backoffice/seguridad/politica`, edita `configuracion_sistema` (categoría `politica_contrasenas` y duración de sesión) (CHK005)
- [ ] T007 Verificar que `password_service.py`/`session_service.py` (Operativo) ya leen estos valores dinámicamente — si hoy usan un fallback hardcodeado sin re-consultar, ajustar para que reflejen cambios sin reiniciar el servicio
- [ ] T008 [P] `app/seguridad/tests/test_politica.py` — cambio de política se refleja en el siguiente registro/login (CHK005)

---

## Fase 3: Matriz de permisos (RF-SEG-T04)

- [ ] T009 `app/seguridad/router_matriz_permisos.py` — `GET /backoffice/seguridad/matriz-permisos`, agrega `roles_permisos`+`roles_permisos_tablas` de todos los roles (CHK006)
- [ ] T010 [P] `app/seguridad/tests/test_matriz_permisos.py`

**Checkpoint:** un Administrador ve la matriz completa de permisos en una sola vista.

---

## Cierre

- [ ] T011 Correr `pytest app/seguridad/` completo (Operativo + Táctico) — confirmar cero regresión sobre los 49 tests ya existentes
- [ ] T012 Repasar `checklist.md`; actualizar `pendientes-implementacion-codigo.md`

---

## Dependencias entre fases

- Las 3 fases son independientes entre sí — ninguna depende de otra de este mismo nivel.
