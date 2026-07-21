# Checklist de Validación: Disrupciones y Notificaciones

**Propósito:** Validar que la implementación del módulo Disrupciones cumple los RF/RNF y RN definidos en `disrupciones-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`disrupciones-spec.md`](./disrupciones-spec.md) · [`plan.md`](./plan.md)

---

**Implementado y verificado:** 2026-07-10 — 23/23 tests de este módulo pasando, con las 3 integraciones externas reales verificadas en vivo al menos una vez cada una (AviationStack, lectura Gmail, envío Gmail — este último con un hallazgo real de scope insuficiente, ver `errores-conocidos.md`). Los tests automatizados usan dobles de prueba determinísticos de las integraciones (no gastan la cuota mensual real de AviationStack en cada corrida) — documentado en `app/disrupciones/tests/conftest.py`.

## Requisitos funcionales

- [x] CHK001 RF-DIS-001 — Consulta periódica a la API real detecta discrepancias de estado y las registra con `fuente_deteccion = api_real`. (`test_api_estado_vuelo.py`; verificado también contra la API real de AviationStack en un smoke test manual, Fase 0)
- [x] CHK002 RF-DIS-002 — Monitoreo de bandeja de correo detecta correos nuevos sin intervención manual. (`test_monitor_correo.py`; lectura real de Gmail verificada en smoke test, Fase 0)
- [x] CHK003 RF-DIS-003 — Parseo identifica correctamente los 5 tipos de cambio (`retraso`, `cancelacion`, `cambio_horario`, `cambio_puerta`, `desvio`). (`test_monitor_correo.py::test_deteccion_identifica_los_5_tipos_de_cambio`, parametrizado)
- [x] CHK004 RF-DIS-004 — Toda disrupción detectada genera notificación a titular y acompañantes de reservas confirmadas asociadas. **Parcial**: el código itera `pasajero_titular_id` + todos los `reserva_pasajeros` de cada reserva (titular y acompañantes por igual), pero la prueba automatizada solo cubre el caso de titular único — no hay fixture con acompañantes reales para probar el caso multi-pasajero.
- [x] CHK005 RF-DIS-004 — Disrupción de tipo `cancelacion` dispara CU-O37; los demás tipos no. (`test_notificacion.py::test_cancelacion_dispara_reembolso_real` — reembolso real vía Stripe test mode; `test_retraso_no_dispara_reembolso`)
- [x] CHK006 RF-DIS-005 — Historial de notificaciones filtra de forma instantánea y respeta alcance (propio vs. RBAC de backoffice). (`test_historial.py`, 4 pruebas)
- [x] CHK007 RF-DIS-006 — Notificación fallida se reintenta según política configurada; al agotar reintentos, queda constancia visible del fallo definitivo. (`test_reintento.py`)

## Reglas de negocio

- [x] CHK008 RN-DIS-001 — Correo sin vuelo/reserva activa asociada se descarta sin notificar y se marca para revisión. (`test_monitor_correo.py::test_correo_sin_vuelo_reconocido_se_descarta_sin_notificar`)
- [x] CHK009 RN-DIS-002 — Prueba explícita: dos fuentes detectando el mismo cambio producen una sola notificación, respetando precedencia `api_real > monitor_correo > simulador_estadistico`. (`test_notificacion.py::test_dos_fuentes_mismo_cambio_generan_una_sola_notificacion`, `test_aplicar_precedencia_es_funcion_pura`)
- [x] CHK010 RN-DIS-003 — Reembolso automático solo se dispara para `tipo_cambio = cancelacion`. (mismo par de pruebas que CHK005)
- [ ] CHK011 RN-DIS-004 — Ninguna disrupción activa queda sin al menos un intento de notificación. **Parcial**: `api_estado_vuelo_service` y `monitor_correo_service` invocan `procesar_disrupcion` automáticamente tras crear cada disrupción (wiring real, no manual) — cubre las 2 fuentes implementadas en esta sesión. La 3ª fuente (`simulador_estadistico`) es Nivel Estratégico, explícitamente fuera de alcance de `disrupciones-spec.md` — no hay code path que la dispare todavía, así que "cobertura sobre las 3 fuentes" no es evaluable tal como está escrito.
- [ ] CHK012 RN-DIS-005 — Con la API real caída, el sistema sigue notificando vía fuente estadística. **No completable tal como está escrito**: el simulador estadístico (fuente de respaldo) no existe en el sistema — es Nivel Estratégico previsto, fuera de alcance de este módulo (ver "Fuera de alcance" en `disrupciones-spec.md`). Lo que sí está implementado y probado es la mitad real de RNF-DIS-001: la degradación se registra y el ciclo no falla (`test_degradacion_no_falla_y_continua`) — simplemente no hay today una fuente de respaldo real a la que "caer".
- [x] CHK013 RN-DIS-006 — Reintentos tienen límite configurado; no existe bucle de reintento indefinido en el código. (`test_reintento.py::test_no_hay_reintento_indefinido_tras_agotar_el_limite` — límite leído de `configuracion_sistema.notificaciones.max_reintentos`, sembrado en esta sesión)

## No funcionales

- [x] CHK014 RNF-DIS-001 — Prueba explícita de degradación: caída de la API real no bloquea el resto del sistema, y el peor caso normal (API disponible) no depende de esta ruta. (`test_degradacion_no_falla_y_continua`, `test_falla_puntual_en_un_vuelo_no_interrumpe_el_resto`; el camino normal se confirmó real y funcional en el smoke test de Fase 0 sin ninguna degradación)
- [x] CHK015 RNF-DIS-002 — Timeout y política de reintento de cada integración externa se leen de `configuracion_sistema`, nunca hardcodeados. (`test_api_estado_vuelo.py::test_timeout_se_lee_de_configuracion_sistema_no_hardcodeado`; `notificaciones.max_reintentos`/`intervalo_reintento_minutos` sembrados y leídos igual en `reintento_service.py`)
- [x] CHK016 RNF-DIS-003 — Prueba de aislamiento: caída simulada del proveedor de correo/SMS no afecta otras funcionalidades del sistema. (`test_reintento.py::test_canal_no_disponible_no_lanza_excepcion_ni_afecta_el_resto` — y confirmado con un hallazgo real: el envío real por Gmail API falla por scope OAuth insuficiente, y el sistema lo aísla correctamente en vez de propagar la excepción)

## Trazabilidad de casos de uso

- [x] CHK017 CU-O27 — prueba automatizada cubre el criterio de aceptación, incluyendo degradación. (`test_api_estado_vuelo.py`)
- [x] CHK018 CU-O28 — ídem. (`test_monitor_correo.py`)
- [x] CHK019 CU-O29 — ídem, incluyendo descarte de correo sin reserva asociada. (`test_monitor_correo.py`)
- [x] CHK020 CU-O30 — ídem, incluyendo deduplicación entre fuentes. (`test_notificacion.py`)
- [x] CHK021 CU-O31 — ídem. (`test_historial.py`)
- [x] CHK022 CU-O46 — ídem, incluyendo agotamiento de reintentos. (`test_reintento.py`)
- [ ] CHK023 RF-DIS-007 (CU-O83) — calcular y registrar risk score. *(catálogo v3.0, agregado 2026-07-18, no implementado)*
- [ ] CHK024 RF-DIS-008 (CU-O84) — posición en tiempo real vía OpenSky. *(catálogo v3.0, agregado 2026-07-18, no implementado)*

## Notas

- CHK011 y CHK012 quedan parcial/no-completable por la misma razón: la 3ª fuente (`simulador_estadistico`) es Nivel Estratégico, fuera de alcance — ver `errores-conocidos.md`.
- Esquema de `notificaciones` incompleto al empezar esta sesión (sin `fallido_definitivo` en `estado_envio`, sin campo de conteo de intentos) — corregido con `scripts/pb_schema_disrupciones_fix.py` (idempotente); este módulo es dueño de esa colección, a diferencia de Facturación con las suyas.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
