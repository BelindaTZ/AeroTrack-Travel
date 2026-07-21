# Checklist de Validación: Ofertas y Promociones (Táctico)

**Propósito:** Validar que la implementación del nivel Táctico cumple los RF/RN definidos en `ofertas-promociones-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/ofertas/router_backoffice.py`, 8/8 tests de backoffice. Ver nota sobre CHK004/CHK009 (sin credencial real de SendGrid, no verificable como envío exitoso — ver abajo).

---

## Requisitos funcionales

- [x] CHK001 RF-OFE-T01 — Gestión de cupones protegida por RBAC — Actor: Administrador únicamente en este módulo, sin rol Agente (a diferencia de Centro de Ayuda). Verificado en vivo: Agente recibe 403 en `/backoffice/ofertas/cupones`.
- [x] CHK002 RN-OFE-T01 — Código de cupón con usos registrados no puede editarse — el resto de campos (valor, expiración, activo) sí. Test explícito.
- [x] CHK003 RF-OFE-T02 — Campaña en `borrador` se puede crear, protegida por RBAC.
- [x] CHK004 RF-OFE-T02 — Envío de campaña **rechaza explícitamente** en vez de simular — no hay ninguna credencial `sendgrid.*` sembrada en `configuracion_sistema` (confirmado, ni siquiera un placeholder como sí existe para `smtp.host`). `SendGridCampanaSender.enviar()` lanza `CredencialNoConfigurada`, el router lo traduce en un mensaje explícito ("No hay credencial real de SendGrid configurada — el envío no se simula") y la campaña permanece en `borrador`. Mismo criterio que `notification_sender.py` aplica al canal SMS de Disrupciones. **No verificable como envío real exitoso** — no hay credencial que autorizar, a diferencia del caso de Gmail (Centro de Ayuda) donde sí existían credenciales, solo con scope insuficiente.
- [x] CHK005 RN-OFE-T02 — Campaña `enviada` es inmutable, no se reenvía — test explícito (`CampanaBloqueada`).
- [x] CHK006 RF-OFE-T03 — Reporte protegido por RBAC (mismo mecanismo que CHK001).
- [x] CHK007 RF-OFE-T03 — Filtro de período (`?dias=30/90/365`) se aplica por navegación GET simple, sin botón "Aplicar" (REG-J9) — mismo patrón que el resto del proyecto.
- [x] CHK011 RF-OFE-T04 — Default global de acumulación se guarda en `configuracion_sistema` (`cupones.acumulable_con_paquete_default`) — verificado en vivo, refleja el valor real sembrado (`false`).
- [x] CHK012 RF-OFE-T04 — Excepción por cupón (`acumulable_con_paquete`) se define en el formulario de creación/edición de cupón (select: "usar default global" / "sí, excepción" / "no, excepción").
- [x] CHK013 RN-OFE-T03 — La excepción por cupón siempre gana sobre el default global — ver CHK015.
- [x] CHK014 RN-OFE-T04 — La regla de acumulación con paquete solo se evalúa si `reservas.es_paquete = true` — para una reserva normal, `aplicar_cupon()` ni siquiera consulta `acumulable_con_paquete`.

## Trazabilidad de casos de uso

- [x] CHK008 CU-T30 — `app/ofertas/tests/test_backoffice.py` (crear/editar cupón) + integración real con RF-OFE-003 verificada (`test_cupon.py`, el cupón creado en backoffice es el mismo que valida `aplicar_cupon`).
- [x] CHK009 CU-T31 — `test_crear_campana_queda_como_borrador`/`test_enviar_campana_sin_credencial_sendgrid_se_rechaza`/`test_reenviar_campana_ya_enviada_se_bloquea`. Envío real no verificable (ver CHK004) — el camino de rechazo explícito sí está verificado en vivo.
- [x] CHK010 CU-T32 — `test_reporte_cupones_muestra_uso_real`, con una reserva y un uso reales (no simulados).
- [x] CHK015 CU-T44 — verificado ambos sentidos en `app/ofertas/tests/test_cupon.py`: `test_cupon_sobre_paquete_usa_default_global_no_acumulable` (default `false`, cupón sin excepción → rechazado) y `test_excepcion_de_cupon_gana_sobre_default_global` (default `false`, cupón con excepción `true` → aplicado).

## Notas

- **Diferencia real entre los dos bloqueos de integración de esta sesión**: Gmail (Centro de Ayuda) tiene credenciales reales pero con scope insuficiente — el intento de envío llega a la API real y falla con un error específico verificable. SendGrid (este módulo) no tiene ninguna credencial sembrada — el sistema nunca intenta la llamada real, se detiene antes por diseño (mismo patrón que Disrupciones ya aplica al canal SMS). Ambos casos rechazan explícitamente en vez de fingir éxito; ninguno de los dos se puede marcar "envío real verificado con éxito" honestamente.
- Al cerrar, actualizado `specs/000-sistema-general/pendientes-implementacion-codigo.md`.
