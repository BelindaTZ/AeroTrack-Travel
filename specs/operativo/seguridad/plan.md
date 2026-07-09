# Plan de Implementación — Seguridad

**Módulo:** Seguridad
**Prefijo:** SEG
**Spec:** [`seguridad-spec.md`](./seguridad-spec.md)
**Código fuente:** `app/seguridad/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Implementar el módulo base de identidad, control de acceso (RBAC de dos niveles) y auditoría inmutable sobre PocketBase, del que dependen los 5 módulos operativos restantes. Cubre 16 RF/RNF y 11 RN sobre 16 CU (CU-O01–O13, O41–O43), organizados en 9 funcionalidades: autenticación, verificación de sesión, recuperación de contraseña, perfil propio, alta de pasajero, gestión de usuarios internos, gestión de roles, verificación RBAC, y auditoría.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5 (REG-I2); SDK/cliente HTTP de PocketBase para `usuarios` (colección AUTH), `roles`, `permisos`, `roles_permisos`, `roles_permisos_tablas`, `modulos`, `modulo_tablas`, `auditoria`, `configuracion_sistema`; librería de hashing de contraseñas (delegada a PocketBase auth, que ya hashea `usuarios.password`); manejo de JWT/cookie de sesión (nativo de PocketBase auth o middleware FastAPI equivalente).
**Almacenamiento:** PocketBase (`pocketbase-travel`) — este módulo es dueño de todas las colecciones listadas arriba.
**Pruebas:** pytest + `httpx.AsyncClient` (cliente de pruebas de FastAPI) para los routers; pruebas de integración contra una instancia PocketBase de test.
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose (REG-I4).
**Tipo de proyecto:** servicio web (backend FastAPI + frontend server-rendered Jinja2/Bootstrap 5, sin SPA separada).
**Objetivos de rendimiento:** login < 1s (RNF-SEG-002); verificación de sesión < 50ms (RNF-SEG-003), dado que se ejecuta en prácticamente el 100% del tráfico autenticado.
**Restricciones:** cero secretos hardcodeados (REG-B3, credenciales en `configuracion_sistema`/variables de entorno); ninguna contraseña en texto plano (RNF-SEG-001); log de auditoría de solo inserción, sin excepción (REG-B4).
**Escala/alcance:** módulo base — 16 RF/RNF, 11 RN, ~20 endpoints, 9 colecciones PocketBase propias.

---

## Constitution Check

*GATE: debe pasar antes de iniciar implementación de cada fase.*

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B1 (RBAC dos niveles) | Sí | RF-SEG-013 implementa la verificación; `roles_permisos`/`roles_permisos_tablas` son las tablas de origen — ninguna ruta de Agente/Admin se implementa sin pasar por `rbac_service` |
| REG-B3 (cero secretos hardcodeados) | Sí | Credenciales SMTP/JWT secret leídas de variables de entorno o `configuracion_sistema`, nunca en código fuente |
| REG-B4 (auditoría inmutable) | Sí | `audit_service` expone solo `insertar()`; no se implementa ningún método de update/delete sobre `auditoria` en el repositorio |
| REG-C1 (no tarjetas crudas) | No aplica a este módulo | Sin campos de pago en Seguridad |
| REG-C2 (derecho de eliminación) | Sí | RF-SEG-017 — Fase 3 |
| REG-G1 (autoservicio por defecto) | Sí | Login, recuperación, registro y perfil no requieren agente humano en ningún paso |
| REG-J6 (RBAC/auditoría visibles) | Sí | Vista de auditoría (RF-SEG-015) sin controles de edición/eliminación en el template; bloqueos RBAC comunicados explícitamente en UI, no como ausencia silenciosa |
| REG-J9 (filtros instantáneos) | Sí | Filtro de auditoría (RF-SEG-016) sin botón "Aplicar" |
| REG-J10/J11 (navegación y feedback) | Sí | Reautenticación en flujo multi-paso preserva estado (RF-SEG-003); confirmaciones autodescartables en cambios de perfil/contraseña |

Sin violaciones que requieran justificación — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/seguridad/
├── seguridad-spec.md   # Especificación (ya generada)
├── plan.md             # Este archivo
└── checklist.md        # Checklist de validación contra RF/RN
```

### Código fuente

```text
app/
├── __init__.py
├── main.py                     # instancia FastAPI, monta routers y templates de todos los módulos
├── shared/                     # código transversal, sin dueño de dominio — evita duplicación entre los 6 módulos
│   ├── __init__.py
│   ├── config.py                # lectura de variables de entorno / settings (PB_URL, SECRET_KEY, etc.)
│   ├── pocketbase_client.py     # wrapper HTTP async genérico sobre la API REST de PocketBase, reutilizado por el repository de cada módulo
│   └── templates/
│       └── base.html            # layout compartido portal/backoffice (Bootstrap 5, tokens J1-J4)
└── seguridad/
    ├── __init__.py
    ├── router_auth.py           # RF-SEG-001,002,003 — login, logout, verificar sesión
    ├── router_password.py       # RF-SEG-004,005 — recuperar/restablecer contraseña
    ├── router_perfil.py         # RF-SEG-006,007,017 — perfil propio, cambiar contraseña, eliminación
    ├── router_registro.py       # RF-SEG-008 — alta de pasajero
    ├── router_usuarios.py       # RF-SEG-009 — gestión de usuarios internos (backoffice)
    ├── router_roles.py          # RF-SEG-010,011,012 — crear/editar/eliminar rol
    ├── router_auditoria.py      # RF-SEG-015,016 — ver/filtrar/exportar log
    ├── schemas.py                # Modelos Pydantic de request/response
    ├── services/
    │   ├── auth_service.py       # RF-SEG-001,002
    │   ├── session_service.py    # RF-SEG-003 (CU-O42, transversal) — consumido por los otros 5 módulos
    │   ├── password_service.py   # RF-SEG-004,005,007 — hashing, política de fortaleza
    │   ├── rbac_service.py       # RF-SEG-013 (CU-O43, transversal) — consumido por los otros 5 módulos
    │   ├── audit_service.py      # RF-SEG-014 (CU-O41, transversal) — único punto de inserción a `auditoria`, consumido por los otros 5 módulos
    │   ├── usuarios_service.py   # RF-SEG-008,009,017
    │   └── roles_service.py      # RF-SEG-010,011,012, incluye validación RN-SEG-007/008
    ├── repositories/
    │   └── seguridad_repo.py     # usa app/shared/pocketbase_client.py; encapsula las 9 colecciones propias de este módulo
    ├── templates/                # extiende app/shared/templates/base.html
    │   ├── login.html, recuperar_password.html, restablecer_password.html
    │   ├── mi_perfil.html
    │   ├── registro.html
    │   └── admin/ (usuarios.html, roles.html, auditoria.html)
    └── tests/
        ├── test_auth.py
        ├── test_password_recovery.py
        ├── test_perfil.py
        ├── test_registro.py
        ├── test_roles.py
        ├── test_rbac_service.py
        └── test_auditoria.py
```

**Decisión de estructura:** `app/` se divide por módulo de dominio (`seguridad/` ahora; `vuelos/`, `reservas/`, `facturacion/`, etc. en sesiones futuras, mismo patrón), más una carpeta `shared/` sin dueño de dominio para lo que de otro modo se duplicaría en los 6 módulos (cliente HTTP de PocketBase, configuración, layout base). Dentro de `seguridad/`, un router por subconjunto de funcionalidad (no un único router monolítico), con `session_service`, `rbac_service` y `audit_service` expuestos como dependencias de FastAPI (`Depends(...)`) inyectables desde los otros 5 módulos — son el punto de integración transversal documentado en `seguridad-spec.md` (sección "Casos de uso relacionados"). Viven en `seguridad/` y no en `shared/` porque tienen dueño de dominio (las colecciones `usuarios`, `roles`, `auditoria`, etc. son propiedad de este módulo); `shared/` es solo para infraestructura sin dueño.

---

## Modelo de datos (resumen — detalle completo de campos en `docs/aerotrack-travel-propuesta-tablas.dbml`)

| Entidad | Rol en este módulo | Validaciones clave (spec) |
|---|---|---|
| `usuarios` | Colección AUTH; identidad de todo actor humano | Correo único (RN-SEG-006), `activo` controla login (RF-SEG-001) |
| `pasajeros` | Perfil extendido 1:1, consumido pero no dueño (ver `pasajeros-spec.md`) | Creado junto con `usuarios` en RF-SEG-008 |
| `roles` | Catálogo de roles | `es_sistema = true` protege contra eliminación (RN-SEG-007) |
| `modulos` | Catálogo de módulos del sistema | Base para Nivel 1 de RBAC |
| `permisos` | Combinación módulo + acción | Base para `roles_permisos` |
| `roles_permisos` | RBAC Nivel 1 | Un rol autoriza módulos completos |
| `roles_permisos_tablas` | RBAC Nivel 2 | Nunca amplía lo no autorizado en Nivel 1 (RN-SEG-009) |
| `modulo_tablas` | Catálogo de tablas por módulo | Alimenta el checklist de UI del Nivel 2 |
| `auditoria` | Log inmutable | Solo `INSERT`, ningún `UPDATE`/`DELETE` expuesto (RN-SEG-010) |
| `configuracion_sistema` | Parámetros leídos por este módulo | Expiración de enlace, política de contraseña (RNF-SEG-007) |

---

## Contratos de API

Ver la tabla completa "Entradas y salidas" en `seguridad-spec.md`. Agrupados por fase de implementación:

- **Autenticación:** `POST /login`, `POST /logout`.
- **Recuperación:** `GET/POST /recuperar-password`, `GET/POST /restablecer-password/{token}`.
- **Perfil:** `GET/POST /mi-perfil`, `POST /mi-perfil/cambiar-password`, `POST /mi-perfil/solicitar-eliminacion`.
- **Registro:** `GET/POST /registro`.
- **Backoffice usuarios/roles:** `GET/POST /admin/usuarios`, `PUT /admin/usuarios/{id}`, `GET/POST /admin/roles`, `PUT/DELETE /admin/roles/{id}`.
- **Auditoría:** `GET /admin/auditoria`, `GET /admin/auditoria/exportar`.

---

## Fases de implementación

### Fase 1 — Autenticación y sesión (RF-SEG-001, 002, 003)
**Objetivo:** login/logout funcionando contra PocketBase auth, con verificación de sesión disponible como dependencia inyectable para los demás módulos.
**Entregable:** `router_auth.py`, `auth_service.py`, `session_service.py`; login end-to-end probado.
**Salida de fase:** cualquier otro módulo puede importar `Depends(verificar_sesion)`.

### Fase 2 — Auditoría y RBAC (RF-SEG-013, 014; CU-O41, O43)
**Objetivo:** los dos servicios transversales restantes, antes de construir cualquier pantalla de backoffice que los necesite.
**Entregable:** `audit_service.py`, `rbac_service.py`, ambos expuestos como dependencias inyectables.
**Salida de fase:** cualquier otro módulo puede registrar auditoría y verificar RBAC.
**Nota de secuencia:** se adelanta antes que Fase 3-6 porque Reservas, Facturación y el resto de backoffice de Seguridad dependen de ambos servicios.

### Fase 3 — Perfil propio y recuperación de contraseña (RF-SEG-004, 005, 006, 007, 017)
**Objetivo:** autoservicio completo de cuenta para cualquier usuario ya autenticado o que perdió acceso.
**Entregable:** `router_password.py`, `router_perfil.py`, `password_service.py`.
**Salida de fase:** un usuario puede recuperar acceso y gestionar su perfil sin intervención de un administrador.

### Fase 4 — Registro de pasajero (RF-SEG-008)
**Objetivo:** alta autoservicio de cuentas de pasajero.
**Entregable:** `router_registro.py`, coordinado con `pasajeros-spec.md` para la creación simultánea del perfil extendido.
**Salida de fase:** un visitante puede crear una cuenta de pasajero y luego iniciar sesión (Fase 1).

### Fase 5 — Gestión de usuarios internos y roles (RF-SEG-009, 010, 011, 012)
**Objetivo:** backoffice de administración de identidad y RBAC.
**Entregable:** `router_usuarios.py`, `router_roles.py`, `roles_service.py`, `usuarios_service.py`.
**Salida de fase:** un Administrador puede crear/editar/eliminar roles y gestionar cuentas internas, con las validaciones RN-SEG-007/008/009.

### Fase 6 — Vistas de auditoría (RF-SEG-015, 016)
**Objetivo:** consulta y exportación del log ya generado desde la Fase 2.
**Entregable:** `router_auditoria.py`.
**Salida de fase:** un Administrador puede ver y exportar el log de auditoría filtrado.

---

## Complexity Tracking

*No aplica — el Constitution Check no registró violaciones que requieran justificación.*
