# Checklist de Validación: Reservas (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Reservas cumple los RF/RN definidos en `reservas-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`reservas-spec.md`](./reservas-spec.md) · [`plan.md`](./plan.md)
**Estado:** Sin implementación todavía — todos los ítems `[ ]`.

---

## Requisitos funcionales

- [ ] CHK001 RF-RES-T01 — Reporte por estado protegido por RBAC.
- [ ] CHK002 RF-RES-T01 — Filtro de período se aplica sin botón "Aplicar".
- [ ] CHK003 RF-RES-T02 — Monitoreo accesible por rol Agente, no restringido solo a Administrador.
- [ ] CHK004 RN-RES-T01 — No existe ninguna acción de extender el plazo de expiración desde esta pantalla.
- [ ] CHK005 RF-RES-T03 — Configuración de políticas protegida por RBAC.
- [ ] CHK006 RF-RES-T03 — Formulario distingue `tipo_producto`, no una política genérica única.

## Reglas de negocio

- [ ] RN-RES-T01 — cubierto por CHK004 arriba.
- [ ] CHK007 RN-RES-T02 — Para Hoteles (y otros con dato real del proveedor), la política aquí es opcional, no sustituye el dato real cuando existe.

## Trazabilidad de casos de uso

- [ ] CHK008 CU-T16 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK009 CU-T17 — ídem, verificando específicamente el acceso de rol Agente.
- [ ] CHK010 CU-T18 — ídem, verificando que al menos una vertical de producto (ej. Vuelos) puede referenciar la política nueva creada aquí.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK009 es un punto de atención real — igual que Centro de Ayuda CU-T36, este es uno de los pocos CU tácticos de rol Agente, no Administrador.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
