# Tasks: Seguridad

**Input:** [`plan.md`](./plan.md) · [`seguridad-spec.md`](./seguridad-spec.md) · [`checklist.md`](./checklist.md) · [`../../.specify/memory/constitution.md`](../../../.specify/memory/constitution.md)
**Código fuente:** `app/seguridad/`
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 6), precedido por una Fase 0 de setup no presente como fase numerada en el plan pero requerida porque `app/` todavía no existe en el repositorio.
**Trazabilidad:** cada tarea de prueba referencia su ítem `CHKxxx` de `checklist.md`.

## Formato: `[ID] [P?] Descripción`

- **[P]**: archivo distinto, sin dependencia de otra tarea del mismo bloque — paralelizable.
- Sin `[P]`: depende de una tarea anterior del mismo bloque (mismo archivo o requiere que exista antes).

---

## Fase 0: Setup e infraestructura compartida

**Propósito:** todo lo que no existe todavía y del que dependen las 6 fases del plan — estructura de proyecto, conexión a PocketBase, y las 9 colecciones propias del módulo.
**⚠️ Bloqueante:** ninguna fase 1-6 puede empezar sin esto.

- [ ] T001 Crear estructura `app/shared/` (`__init__.py`, `templates/`) y `app/seguridad/` (`__init__.py`, `services/`, `repositories/`, `templates/`, `templates/admin/`, `tests/`) según `plan.md` — `shared/` para código sin dueño de dominio, `seguridad/` para lo propio del módulo
- [ ] T002 [P] Crear `pyproject.toml`/`requirements.txt` en la raíz: `fastapi`, `uvicorn`, `jinja2`, `httpx`, `python-multipart`, `pydantic`, `pytest`, `pytest-asyncio`
- [ ] T003 [P] Crear `app/main.py` — instancia FastAPI, monta Jinja2 (`app/shared/templates` + `app/seguridad/templates`, con `shared` como directorio base para que `{% extends "base.html" %}` funcione desde cualquier módulo), monta estáticos desde `public/`
- [ ] T004 [P] Añadir servicio `app-travel` a `docker-compose.yml` (Dockerfile propio, red `travel-network`, depende de `pocketbase-travel` healthy) — cumple REG-I4
- [ ] T005 Crear `app/shared/config.py` (lectura de `PB_TRAVEL_URL`/`PB_TRAVEL_EMAIL`/`PB_TRAVEL_PASSWORD`/`SECRET_KEY` desde `.env` — **no** `PB_URL`/`PB_EMAIL`/`PB_PASSWORD`, que apuntan a la instancia PocketBase del proyecto anterior minio-elt; cero credenciales en código, REG-B3) y `app/shared/pocketbase_client.py` — wrapper async genérico (`httpx`) sobre la API REST de `pocketbase-travel`, sin conocimiento de colecciones específicas, reutilizable por el repository de cada uno de los 6 módulos
- [ ] T005b Crear `app/seguridad/repositories/seguridad_repo.py` — usa `app/shared/pocketbase_client.py`; encapsula las 9 colecciones propias de este módulo (CRUD específico de `usuarios`, `roles`, `auditoria`, etc.)
- [ ] T006 Crear colección AUTH `usuarios` en `pocketbase-travel` (`nombre_completo`, `tipo_actor` select[pasajero,agente,administrador], `rol_id` relation→`roles` nullable, `activo` bool default true) — vía `scripts/pb_schema_seguridad.py`
- [ ] T007 [P] Crear colección `roles` (`nombre`, `descripcion`, `es_sistema` bool default false)
- [ ] T008 [P] Crear colección `modulos` (`clave` unique, `nombre_display`, `descripcion`, `orden`)
- [ ] T009 [P] Crear colección `permisos` (`modulo_id` relation→`modulos`, `accion` select[ver,crear,editar,eliminar,exportar,ejecutar])
- [ ] T010 [P] Crear colección `roles_permisos` (`rol_id` relation→`roles`, `permiso_id` relation→`permisos`)
- [ ] T011 [P] Crear colección `roles_permisos_tablas` (`rol_id` relation→`roles`, `modulo_id` relation→`modulos`, `tabla` varchar)
- [ ] T012 [P] Crear colección `modulo_tablas` (`modulo_id` relation→`modulos`, `tabla` varchar, `descripcion`)
- [ ] T013 [P] Crear colección `auditoria` (`usuario_id` relation→`usuarios` nullable, `accion`, `tabla`, `registro_id`, `detalle` json, `ip`) — reglas API de PocketBase: `update`/`delete` bloqueadas a nivel de base (defensa en profundidad de RN-SEG-010, independiente de la capa de aplicación)
- [ ] T014 [P] Crear colección `configuracion_sistema` (`clave` unique, `valor` text, `categoria`, `descripcion`, `modificado_por` not null)
- [ ] T015 Crear `scripts/seed_seguridad.py` — siembra catálogo `modulos` (seguridad, configuracion, pasajeros, vuelos_catalogo, reservas, disrupciones, facturacion), rol `Administrador` (`es_sistema=true`) con permisos Nivel 1 completos, y defaults en `configuracion_sistema` (`expiraciones.recuperacion_password_minutos=30`, política mínima de contraseña)
- [ ] T016 Crear `app/seguridad/schemas.py` — modelos Pydantic base (`LoginRequest`, `UsuarioOut`); se amplía en cada fase siguiente
- [ ] T017 [P] Crear `app/shared/templates/base.html` — layout compartido portal/backoffice (Bootstrap 5, tokens J1-J4) del que heredan las plantillas de `seguridad/` y, en sesiones futuras, las de los otros 5 módulos
- [ ] T018 [P] Configurar `app/seguridad/tests/conftest.py` — fixture `AsyncClient` de FastAPI + fixture de PocketBase de test (colecciones limpias por test)

**Checkpoint:** `docker compose up` levanta `pocketbase-travel` + `app-travel`; las 9 colecciones existen con su seed; `pytest` corre (0 tests todavía, sin errores de import).

---

## Fase 1: Autenticación y sesión (RF-SEG-001, 002, 003)

**Objetivo del plan:** login/logout funcionando contra PocketBase auth, con verificación de sesión disponible como dependencia inyectable para los demás módulos.

- [ ] T019 `app/seguridad/services/auth_service.py` — `autenticar(email, password)` vía `authWithPassword` de PocketBase; distingue "Credenciales incorrectas" (sin precisar campo) de "Cuenta desactivada. Contacte al administrador." (`activo=false`)
- [ ] T020 `app/seguridad/services/session_service.py` — `verificar_sesion()` como `Depends()` de FastAPI: valida token no expirado + usuario activo; lee/escribe cookie httponly
- [ ] T021 `app/seguridad/router_auth.py` — `GET /login`, `POST /login` (redirige según `tipo_actor`/`rol_id`), `POST /logout`
- [ ] T022 [P] `app/seguridad/templates/login.html` (Bootstrap 5, contraste 4.5:1 y navegación por teclado — J8)
- [ ] T023 [P] `app/seguridad/tests/test_auth.py` — login correcto (CHK001), credenciales incorrectas (CHK002), cuenta inactiva (CHK003), logout invalida token (CHK004)
- [ ] T024 [P] `app/seguridad/tests/test_auth.py` — `verificar_sesion` rechaza token inválido/expirado antes de ejecutar lógica de negocio (CHK005), usando un endpoint dummy protegido; reautenticación en flujo multi-paso preserva estado ya ingresado (CHK006)

**Checkpoint:** cualquier router futuro puede usar `Depends(verificar_sesion)`.

---

## Fase 2: Auditoría y RBAC (RF-SEG-013, 014; CU-O41, O43)

**Nota de secuencia (del plan):** se adelanta antes que Fases 3-6 porque Reservas, Facturación y el resto del backoffice de Seguridad dependen de ambos servicios.

- [ ] T025 `app/seguridad/services/audit_service.py` — único método público `insertar(usuario_id, accion, tabla, registro_id, detalle, ip)`; sin métodos de update/delete en la interfaz (RN-SEG-010); si el insert falla, no revierte la acción original pero registra alerta para Administrador (RF-SEG-014)
- [ ] T026 Retrofit — wire `audit_service` en `router_auth.py` (T021) para auditar login exitoso, login fallido y logout (RN-SEG-001, pendiente desde Fase 1 porque el servicio no existía aún)
- [ ] T027 `app/seguridad/services/rbac_service.py` — `verificar_permiso(usuario, modulo, accion, tabla=None)` como `Depends()` parametrizable: Nivel 1 (`roles_permisos`) + Nivel 2 (`roles_permisos_tablas`), Nivel 2 nunca amplía Nivel 1 (RN-SEG-009)
- [ ] T028 [P] `app/seguridad/tests/test_rbac_service.py` — bloqueo por falta de permiso Nivel 1 (CHK017), intento de ampliar en Nivel 2 lo no autorizado en Nivel 1 queda bloqueado (CHK031)
- [ ] T029 [P] `app/seguridad/tests/test_auditoria.py` (parte servicio) — inserción con todos los campos (CHK018), fallo de inserción no revierte la acción original (CHK019), ningún método de edición/borrado expuesto en `audit_service` (CHK032, CHK042)
- [ ] T030 [P] `app/seguridad/tests/test_auth.py` — verificar que login/logout quedan auditados tras T026 (extiende CHK023)

**Checkpoint:** `session_service`, `rbac_service` y `audit_service` disponibles como dependencias inyectables reutilizables por los otros 5 módulos (CHK040-042).

---

## Fase 3: Perfil propio y recuperación de contraseña (RF-SEG-004, 005, 006, 007, 017)

- [ ] T031 `app/seguridad/services/password_service.py` — token de un solo uso con expiración leída de `configuracion_sistema` (categoría `expiraciones`, fallback 30 min si la clave no existe — RNF-SEG-004), validación de política de fortaleza (RN-SEG-005)
- [ ] T032 `app/seguridad/router_password.py` — `GET/POST /recuperar-password` (mismo mensaje genérico exista o no el correo — RN-SEG-003), `GET/POST /restablecer-password/{token}` (invalida el enlace tras uso)
- [ ] T033 [P] `app/seguridad/router_perfil.py` — `GET/POST /mi-perfil` (ver/editar datos no sensibles de `usuarios`+`pasajeros`, excluye correo — RF-SEG-006)
- [ ] T034 [P] `app/seguridad/router_perfil.py` — `POST /mi-perfil/cambiar-password` (valida contraseña actual antes de aceptar la nueva — RF-SEG-007)
- [ ] T035 `app/seguridad/router_perfil.py` — `POST /mi-perfil/solicitar-eliminacion` (valida reservas/pagos en curso antes de proceder, informa qué se retiene y por qué — RN-SEG-011)
- [ ] T036 [P] Capa de envío de correo reemplazable (F1) para el enlace de recuperación — interfaz simple con implementación mock/log en esta sesión si no hay SMTP real disponible; credenciales, si las hay, solo desde `configuracion_sistema`/env (REG-B3)
- [ ] T037 [P] `app/seguridad/templates/recuperar_password.html`, `restablecer_password.html`, `mi_perfil.html` (confirmaciones autodescartables 3-5s — J11)
- [ ] T038 [P] `app/seguridad/tests/test_password_recovery.py` — mensaje genérico exista o no el correo (CHK007), enlace válido/expirado/usado (CHK008), expiración con fallback documentado (CHK026, CHK037)
- [ ] T039 [P] `app/seguridad/tests/test_perfil.py` — ver/editar datos no sensibles (CHK009), cambio de contraseña exige la actual (CHK010), política de fortaleza rechaza contraseña débil (CHK027), solicitud de eliminación con retención informada (CHK022, CHK033)
- [ ] T040 Wire `audit_service`+`session_service` en los 5 endpoints de esta fase (RN-SEG-002: ninguna mutación completa sin su auditoría)

**Checkpoint:** un usuario puede recuperar acceso y gestionar su perfil sin intervención de un administrador, con todo mutación auditada.

---

## Fase 4: Registro de pasajero (RF-SEG-008)

- [ ] T041 `app/seguridad/services/usuarios_service.py` — `crear_pasajero(...)`, coordina creación de `usuarios`+`pasajeros`; documentar en el código si PocketBase no permite transacción multi-colección atómica
- [ ] T042 `app/seguridad/router_registro.py` — `GET/POST /registro`: valida formato+unicidad de correo (RN-SEG-006), sin campo de verificación documental (RNF-SEG-005), envía correo de verificación (reutiliza T036), redirige a `/login`
- [ ] T043 [P] `app/seguridad/templates/registro.html`
- [ ] T044 [P] `app/seguridad/tests/test_registro.py` — alta exitosa + redirección (CHK011 parte 1), correo duplicado rechazado (CHK011 parte 2), ausencia de cualquier input de imagen de documento (CHK012)
- [ ] T045 Wire `audit_service` en la creación de usuario+pasajero de esta fase

**Checkpoint:** un visitante crea una cuenta de pasajero y puede iniciar sesión (Fase 1) inmediatamente después.

---

## Fase 5: Gestión de usuarios internos y roles (RF-SEG-009, 010, 011, 012)

- [ ] T046 Extender `usuarios_service.py` — `crear_usuario_interno`/`editar_usuario_interno`/`desactivar_usuario_interno` con `rol_id` obligatorio (agente/administrador)
- [ ] T047 `app/seguridad/router_usuarios.py` — `GET/POST /admin/usuarios`, `PUT /admin/usuarios/{id}`, protegidos por `Depends(verificar_sesion)` + `Depends(rbac: modulo="seguridad")`
- [ ] T048 `app/seguridad/services/roles_service.py` — `crear_rol` (sin permisos por defecto — RF-SEG-010), `editar_rol` (Nivel 1 + Nivel 2, valida RN-SEG-009), `eliminar_rol` (bloquea `es_sistema=true` — RN-SEG-007; bloquea con usuarios activos asignados y ofrece reasignación — RN-SEG-008)
- [ ] T049 `app/seguridad/router_roles.py` — `GET/POST /admin/roles`, `PUT/DELETE /admin/roles/{id}`
- [ ] T050 [P] `app/seguridad/templates/admin/usuarios.html`, `admin/roles.html` — combobox con búsqueda para selección de rol/módulo con >8 opciones (J9), alcance vigente de RBAC Nivel 2 visible de forma persistente (J6)
- [ ] T051 [P] `app/seguridad/tests/test_roles.py` — crear rol sin permisos (CHK014), editar Nivel 1/2 sin que Nivel 2 amplíe Nivel 1 (CHK015, CHK031), eliminar rol protegido bloqueado (CHK016, CHK029), eliminar rol con usuarios asignados bloqueado con opción de reasignar (CHK030)
- [ ] T052 [P] `app/seguridad/tests/test_usuarios.py` — crear/editar/desactivar usuario interno con rol obligatorio (CHK013)
- [ ] T053 Wire `audit_service`+`rbac_service` en los 4 endpoints de esta fase

**Checkpoint:** un Administrador gestiona roles y cuentas internas con las validaciones RN-SEG-007/008/009 verificadas.

---

## Fase 6: Vistas de auditoría (RF-SEG-015, 016)

- [ ] T054 `app/seguridad/router_auditoria.py` — `GET /admin/auditoria`: orden cronológico descendente, sin ningún control de edición/eliminación en el template (RF-SEG-015); protegido por `rbac_service`
- [ ] T055 `app/seguridad/router_auditoria.py` — `GET /admin/auditoria/exportar`: filtros por usuario/acción/módulo-tabla/rango de fechas aplicados vía query params sin botón "Aplicar" (J9), exporta CSV respetando el filtro activo (RF-SEG-016)
- [ ] T056 [P] `app/seguridad/templates/admin/auditoria.html` — filtros instantáneos (J9), cero controles de edición/eliminación (J6)
- [ ] T057 [P] `app/seguridad/tests/test_auditoria.py` (parte vista) — listado descendente sin controles de edición (CHK020), filtro instantáneo + export respeta el filtro (CHK021)

**Checkpoint:** un Administrador ve y exporta el log de auditoría filtrado — módulo Seguridad funcionalmente completo.

---

## Cierre del módulo

- [ ] T058 Grep de verificación de cero secretos hardcodeados sobre `app/seguridad/` (CHK039)
- [ ] T059 Correr suite completa `pytest app/seguridad/tests/` — confirmar que CU-O01–O13 y CU-O41–O43 tienen al menos una prueba automatizada (CHK047, CHK048)
- [ ] T060 Repasar `checklist.md` ítem por ítem; cualquier `CHKxxx` no alcanzable en esta sesión se registra en `specs/000-sistema-general/errores-conocidos.md`, no se omite en silencio

---

## Fase 7 (futura, no iniciada) — catálogo v3.0/dbml v3

- CU-O112/O113 no requieren tarea nueva — ya cubiertos por T048/T051 (RF-SEG-011).
- `usuarios.foto_perfil` (file field, dbml v3) — agregar campo a la colección PocketBase real, subida/reemplazo/vista en `router_perfil.py`/`mi_perfil.html`. No desglosado en tareas todavía.

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás (colecciones y esqueleto de proyecto no existen aún).
- Fase 1 bloquea Fase 2 (`audit_service`/`rbac_service` se integran sobre `router_auth.py` ya existente vía T026).
- Fase 2 bloquea Fases 3-6 (todas auditan y las de backoffice además verifican RBAC).
- Fase 4 depende de Fase 1 (login) para su camino feliz, pero es implementable en paralelo — solo su prueba end-to-end de "registro → login" depende de Fase 1 ya mergeada.
- Fases 3, 4 y 5 no dependen entre sí y pueden implementarse en paralelo una vez cerrada la Fase 2.
- Fase 6 depende únicamente de Fase 2 (consume `auditoria`, ya poblada desde T026).
