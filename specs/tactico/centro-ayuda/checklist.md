# Checklist de Validación: Centro de Ayuda (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Centro de Ayuda cumple los RF/RN definidos en `centro-ayuda-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`centro-ayuda-spec.md`](./centro-ayuda-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/centro_ayuda/router_backoffice.py`, 8/8 tests de backoffice.

---

## Requisitos funcionales

- [x] CHK001 RF-AYU-T01 — Gestión de artículos protegida por RBAC (Administrador). RBAC de dos niveles: Nivel 1 (`centro_ayuda.crear`/`.editar`) + Nivel 2 (`roles_permisos_tablas`, restringe a Agente a la tabla `casos_escalados` — sin esa fila Agente heredaría acceso completo del módulo). Verificado en vivo: Agente recibe 403 real en `/backoffice/ayuda/articulos`.
- [x] CHK002 RN-AYU-T01 — Artículos se archivan (`activo=false`), nunca se eliminan físicamente — no existe endpoint de borrado, solo `PATCH` vía el formulario de edición.
- [x] CHK003 RF-AYU-T03 — Bandeja de casos accesible por rol Agente. Verificado en vivo con una cuenta Agente real: ve la bandeja, resuelve un caso.
- [x] CHK004 RN-AYU-T02 — Marcar un caso resuelto solo actualiza `estado`/`fecha_resolucion`/`agente_asignado_id` — `gmail_thread_id` nunca se toca en `resolver_caso()`, queda intacto.
- [x] CHK005 RF-AYU-T02 — Métricas protegidas por RBAC (Administrador) — mismo mecanismo Nivel 2 que CHK001, verificado con 403 real para Agente.
- [x] CHK006 RF-AYU-T02 — Filtro de período (`?dias=30/90/365`) se aplica por navegación GET simple, sin botón "Aplicar" — mismo patrón que el filtro de estado de `casos.html` (REG-J9). **Corregido durante la revisión de este checklist**: la primera versión tenía el período fijo en 90 días sin selector, no cumplía REG-J9 — se agregó el selector antes de cerrar el módulo.

## Trazabilidad de casos de uso

- [x] CHK007 CU-T28 — `app/centro_ayuda/tests/test_backoffice.py::test_admin_puede_crear_articulo`/`test_admin_puede_archivar_articulo`.
- [x] CHK008 CU-T29 — `test_admin_puede_ver_metricas_con_datos_reales`; verificado en vivo con datos reales (1 artículo, 1 calificación, 1 caso).
- [x] CHK009 CU-T36 — `test_agente_puede_ver_casos`/`test_agente_puede_resolver_caso`/`test_listar_casos_filtra_por_estado`, verificando específicamente que el rol Agente (no solo Administrador) tiene acceso.

## Notas

- CHK003/CHK009 (Agente, no solo Administrador) verificados explícitamente con una cuenta Agente real, tanto en tests como en vivo — no se asumió que el RBAC compartido del módulo alcanzaría solo porque Administrador funcionaba.
- **Hallazgo real durante la verificación en vivo de CU-O100** (ver `specs/operativo/centro-ayuda/checklist.md` CHK011): el envío real de email falla por un problema de scope OAuth preexistente (no de este módulo) — un caso escalado sin `gmail_thread_id` se ve en la bandeja con un aviso visible ("sin hilo — falló el envío"), nunca se oculta el fallo.
- Al cerrar, actualizado `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
