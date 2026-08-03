# Checklist de Validación: Carrito (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico de Carrito cumple los RF/RN definidos en `carrito-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`carrito-spec.md`](./carrito-spec.md) · [`plan.md`](./plan.md)
**Estado:** Completo 2026-07-22 — 15 tests (`app/carrito/tests/test_abandono.py`, `test_router_abandono.py`).

---

## Requisitos funcionales

- [x] CHK001 RF-CAR-T01 — Configuración protegida por RBAC (`requiere_permiso("carrito", "editar", "carritos")`).
- [x] CHK002 RF-CAR-T01 — Umbral de inactividad y plantilla se guardan en `configuracion_sistema` (`pb_schema_carrito_abandono.py`).
- [x] CHK003 RF-CAR-T01 — Carrito inactivo más allá del umbral se marca `abandonado` y dispara el email (`abandono_service.marcar_abandonados_y_notificar`, reutiliza `GmailNotificationSender`).
- [x] CHK004 RN-CAR-T01 — Un carrito `convertido` nunca se marca `abandonado` (revalidación justo antes de escribir, `test_carrito_convertido_nunca_se_marca_abandonado`).
- [x] CHK005 RF-CAR-T02 — Reporte protegido por RBAC (`requiere_permiso("carrito", "ver")`).
- [x] CHK006 RF-CAR-T02 — Filtro de período se aplica sin botón "Aplicar" (enlaces `?dias=N`, mismo patrón que Autos CU-T11).
- [x] CHK007 RN-CAR-T02 — Tasa de recuperación cuenta solo carritos que pasaron por `abandonado` (`fue_abandonado=true`) y luego se convirtieron; uno convertido sin pasar por abandono no participa.

## Trazabilidad de casos de uso

- [x] CHK008 CU-T26 — `test_marca_abandonado_un_carrito_activo_inactivo_y_envia_email`, `test_fallo_de_envio_no_impide_marcar_abandonado`.
- [x] CHK009 CU-T27 — `test_reporte_cuenta_recuperados_y_no_recuperados`, `test_reporte_periodo_excluye_marcados_fuera_de_rango`.

## Nota de implementación no prevista en el plan original

`carritos.fue_abandonado`/`fecha_marcado_abandonado` (bool/date) se agregaron porque `estado` por sí solo no basta para CU-T27: un carrito puede volver a `activo` (recuperación) y luego a `convertido`, y en ese punto el `estado` final ya no dice que pasó por abandono. `CarritoRepository.carrito_de_trabajo` (antes `carrito_activo_de_pasajero`) reactiva un carrito `abandonado` a `activo` en el único punto de entrada real (ver/agregar/checkout) — sin esto, un carrito abandonado nunca podría completar checkout ni contar como recuperado, y el escenario feliz de `carrito-spec.md` sería imposible de verificar en la práctica.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- Al cerrar, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
