# Plan de Implementación — Seguridad (Táctico)

**Módulo:** Seguridad
**Prefijo:** SEG
**Spec:** [`seguridad-spec.md`](./seguridad-spec.md)
**Código fuente:** `app/seguridad/` *(nivel Operativo ya implementado — 49/49 tests reales pasando)*
**Fecha:** 2026-07-18
**Estado:** Draft — pendiente de revisión. Los 4 CU son extensiones sobre servicios ya construidos, ninguno bloqueado por una pieza externa.

---

## Resumen

Dashboard de intentos fallidos, expiración forzada de sesión, UI de configuración de política de contraseñas/sesión, y vista agregada de la matriz de permisos. Cubre 4 RF y 2 RN sobre 4 CU (CU-T01, T02, T03, T35). Sin colección propia — todo lee/escribe sobre colecciones ya existentes de Seguridad Operativo.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** ninguna nueva — reutiliza `session_service.py`, `rbac_service.py`, `roles_service.py`, `audit_service.py` ya implementados. **Almacenamiento:** sin colecciones nuevas.

---

## Constitution Check

| Principio | Aplica | Verificación |
|---|---|---|
| REG-B1 (RBAC) | Sí | Los 4 endpoints protegidos |
| REG-J6 (RBAC/auditoría visibles) | Sí | CU-T35 es precisamente la vista que constitución J6 pide — extenderla aquí de forma agregada |
| REG-J9 (filtros instantáneos) | Sí | Dashboard de CU-T01 |

Sin violaciones.

---

## Estructura del proyecto

```text
app/seguridad/
├── router_dashboard_seguridad.py   # RF-SEG-T01, T02 (nuevo)
├── router_politica.py              # RF-SEG-T03 (nuevo)
├── router_matriz_permisos.py       # RF-SEG-T04 (nuevo)
└── tests/
    ├── test_dashboard_seguridad.py
    ├── test_politica.py
    └── test_matriz_permisos.py
```

**Decisión de estructura:** routers nuevos dentro del mismo paquete `app/seguridad/`, reutilizando `services/` ya existentes sin duplicarlos — mismo patrón de "nivel Táctico comparte código con Operativo" usado en todos los módulos nuevos de esta ronda.

---

## Fases de implementación

### Fase 1 — Dashboard de intentos fallidos y expiración forzada (RF-SEG-T01, T02)
**Precondición externa:** ninguna — `auditoria` y `session_service` ya existen y tienen datos reales.
**Entregable:** `router_dashboard_seguridad.py`.

### Fase 2 — Configurar política (RF-SEG-T03)
**Precondición externa:** ninguna.
**Entregable:** `router_politica.py`.

### Fase 3 — Matriz de permisos (RF-SEG-T04)
**Precondición externa:** ninguna — `roles_permisos`/`roles_permisos_tablas` ya tienen datos reales desde Operativo.
**Entregable:** `router_matriz_permisos.py`.

---

## Complexity Tracking

*No aplica.*
