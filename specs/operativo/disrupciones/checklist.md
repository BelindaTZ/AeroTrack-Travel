# Checklist de Validación: Disrupciones y Notificaciones

**Propósito:** Validar que la implementación del módulo Disrupciones cumple los RF/RNF y RN definidos en `disrupciones-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`disrupciones-spec.md`](./disrupciones-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [ ] CHK001 RF-DIS-001 — Consulta periódica a la API real detecta discrepancias de estado y las registra con `fuente_deteccion = api_real`.
- [ ] CHK002 RF-DIS-002 — Monitoreo de bandeja de correo detecta correos nuevos sin intervención manual.
- [ ] CHK003 RF-DIS-003 — Parseo identifica correctamente los 5 tipos de cambio (`retraso`, `cancelacion`, `cambio_horario`, `cambio_puerta`, `desvio`).
- [ ] CHK004 RF-DIS-004 — Toda disrupción detectada genera notificación a titular y acompañantes de reservas confirmadas asociadas.
- [ ] CHK005 RF-DIS-004 — Disrupción de tipo `cancelacion` dispara CU-O37; los demás tipos no.
- [ ] CHK006 RF-DIS-005 — Historial de notificaciones filtra de forma instantánea y respeta alcance (propio vs. RBAC de backoffice).
- [ ] CHK007 RF-DIS-006 — Notificación fallida se reintenta según política configurada; al agotar reintentos, queda constancia visible del fallo definitivo.

## Reglas de negocio

- [ ] CHK008 RN-DIS-001 — Correo sin vuelo/reserva activa asociada se descarta sin notificar y se marca para revisión.
- [ ] CHK009 RN-DIS-002 — Prueba explícita: dos fuentes detectando el mismo cambio producen una sola notificación, respetando precedencia `api_real > monitor_correo > simulador_estadistico`.
- [ ] CHK010 RN-DIS-003 — Reembolso automático solo se dispara para `tipo_cambio = cancelacion`.
- [ ] CHK011 RN-DIS-004 — Ninguna disrupción activa queda sin al menos un intento de notificación (prueba de cobertura sobre las 3 fuentes).
- [ ] CHK012 RN-DIS-005 — Con la API real simulada caída, el sistema sigue notificando vía fuente estadística, sin excepción no controlada.
- [ ] CHK013 RN-DIS-006 — Reintentos tienen límite configurado; no existe bucle de reintento indefinido en el código.

## No funcionales

- [ ] CHK014 RNF-DIS-001 — Prueba explícita de degradación: caída de la API real no bloquea el resto del sistema, y el peor caso normal (API disponible) no depende de esta ruta.
- [ ] CHK015 RNF-DIS-002 — Timeout y política de reintento de cada integración externa se leen de `configuracion_sistema`, nunca hardcodeados.
- [ ] CHK016 RNF-DIS-003 — Prueba de aislamiento: caída simulada del proveedor de correo/SMS no afecta otras funcionalidades del sistema.

## Trazabilidad de casos de uso

- [ ] CHK017 CU-O27 — prueba automatizada cubre el criterio de aceptación, incluyendo degradación.
- [ ] CHK018 CU-O28 — ídem.
- [ ] CHK019 CU-O29 — ídem, incluyendo descarte de correo sin reserva asociada.
- [ ] CHK020 CU-O30 — ídem, incluyendo deduplicación entre fuentes.
- [ ] CHK021 CU-O31 — ídem.
- [ ] CHK022 CU-O46 — ídem, incluyendo agotamiento de reintentos.

## Notas

- CHK009 y CHK014 requieren pruebas con doble fuente simulada simultánea — no basta con probar cada fuente por separado.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
