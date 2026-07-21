# Checklist de Validación: Integraciones

**Propósito:** Validar que la implementación del módulo Integraciones cumple los RF/RN definidos en `integraciones-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`integraciones-spec.md`](./integraciones-spec.md) · [`plan.md`](./plan.md)
**Estado:** Fase 1 y 2 implementadas y probadas (2026-07-19) — `app/integraciones/`, 10/10 tests pasando (`pytest app/integraciones`). CHK010 queda abierto a propósito (ver nota).

---

## Requisitos funcionales

- [x] CHK001 RF-INT-001 — Lista de fuentes protegida por RBAC. `test_listar_fuentes_requiere_permiso` (403 sin permiso, 200 con rol Administrador).
- [x] CHK002 RF-INT-001/RN-INT-001 — Campos editables por fuente respetan su `tipo_uso` (catálogo_periodico vs. constante vs. cache vs. regla_negocio_interna). `test_editar_frecuencia_en_catalogo_periodico_se_aplica` + `test_editar_frecuencia_en_fuente_constante_se_bloquea` (422).
- [x] CHK003 RN-INT-002 — Desactivar una fuente no borra el catálogo ya generado por el módulo que la consume. `test_desactivar_fuente_no_borra_catalogo_generado` (verifica `vuelos_catalogo` intacto).
- [x] CHK004 RF-INT-002 — Bitácora filtrable por fuente y rango de fechas. `test_bitacora_filtra_por_fuente_y_fecha`.
- [x] CHK005 RF-INT-002 — Filtros se aplican sin botón "Aplicar". Verificado por inspección: `bitacora.html` dispara `requestSubmit()` en `change` (mismo patrón ya usado en `comisiones.html`), sin botón "Aplicar" en el DOM — sin test JS de navegador automatizado.
- [x] CHK006 RN-INT-003 — Una corrida fallida se muestra en la bitácora sin ocultar/reemplazar la última exitosa. `test_corrida_fallida_no_oculta_ultima_exitosa`.

## Reglas de negocio

- [x] RN-INT-001 — cubierto por CHK002 arriba.
- [x] RN-INT-002 — cubierto por CHK003 arriba.
- [x] RN-INT-003 — cubierto por CHK006 arriba.
- [x] CHK007 RN-INT-004 — Edición de configuración de fuente queda auditada. `test_editar_fuente_queda_auditada` (verifica fila en `auditoria`).

## No funcionales

- [x] CHK008 — `host_env_var` nunca almacena o expone el valor real de una credencial, solo el nombre de la variable (REG-B3) — `test_host_env_var_nunca_contiene_valores_hardcodeados` (grep de prefijos de secreto reales del proyecto sobre `app/integraciones/`).

## Trazabilidad de casos de uso

- [x] CHK009 CU-T37 — cubierto por CHK001-003/007 + `test_resincronizar_fuente_catalogo_periodico_crea_log_manual`/`test_resincronizar_fuente_regla_negocio_interna_se_rechaza`.
- [ ] CHK010 CU-T38 — la bitácora en sí funciona (CHK004-006) y el disparo manual (`POST .../resincronizar`) escribe una fila real, **pero ningún job automático de catálogo (Vuelos, Hoteles, Autos, Actividades, Cruceros) escribe en `sincronizaciones_log` todavía** — `dag_generar_catalogo_vuelos.py` sigue siendo 100% sintético, sin llamar a AeroDataBox/Google Flights. Además, el disparo manual hoy registra `estado="fallido"` con motivo explícito ("job real no implementado") en vez de fabricar un `exitoso` — es honesto, pero significa que CU-T38 no tiene todavía ninguna corrida `exitoso`/`parcial` real que mostrar en producción. No cierra hasta que exista al menos un consumidor real (ver `pendientes-implementacion-codigo.md`, sección 2, Fase 1 de cualquiera de las 5 verticales de catálogo).

## Notas

- Marcar `[x]` solo con evidencia verificable.
- CHK010 no cierra completo sin al menos un consumidor real escribiendo en la bitácora.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
