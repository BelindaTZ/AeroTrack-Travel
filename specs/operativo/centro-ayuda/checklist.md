# Checklist de Validación: Centro de Ayuda

**Propósito:** Validar que la implementación del módulo Centro de Ayuda cumple los RF/RN definidos en `centro-ayuda-spec.md`.
**Creado:** 2026-07-18
**Feature:** [`centro-ayuda-spec.md`](./centro-ayuda-spec.md) · [`plan.md`](./plan.md)
**Estado:** ✅ **Implementado 2026-07-19** — `app/centro_ayuda/`, 20/20 tests. Ver nota sobre CHK004/CHK011 (envío real de email bloqueado por un problema real de credenciales, no de código).

---

## Requisitos funcionales

- [x] CHK001 RF-AYU-001 — Búsqueda por categoría/término filtra solo artículos activos. Verificado en vivo con 3 artículos reales sembrados.
- [x] CHK002 RF-AYU-002 — Detalle de artículo muestra contenido completo.
- [x] CHK003 RF-AYU-003 — Calificación funciona autenticada (asocia `pasajero_id`) y anónima (`pasajero_id` vacío) — verificado en vivo ambos caminos.
- [x] CHK004 RF-AYU-004 — Escalar caso crea el registro SIEMPRE; el envío real de email se intenta contra la Gmail API real (no un mock) — ver nota abajo sobre el resultado de esa verificación.
- [x] CHK005 RN-AYU-001 — Escalar sin sesión redirige a `/login`; verificado también que un usuario sin perfil de pasajero (ej. Administrador) se detiene antes de intentar el envío.

## Reglas de negocio

- [x] RN-AYU-001 — cubierto por CHK005 arriba.
- [x] CHK006 RN-AYU-002 — Mutaciones quedan auditadas vía `AuditService`; calificación anónima audita con `usuario_id=None`.

## No funcionales

- [x] CHK007 — La integración Gmail de este módulo reutiliza las mismas **credenciales OAuth** (`gmail_api.*` en `configuracion_sistema`) que Disrupciones — no hay una app/conexión OAuth paralela. Sí existe un **cliente propio** (`app/centro_ayuda/integrations/escalacion_sender.py`, separado de `app/disrupciones/integrations/notification_sender.py`) — decisión deliberada, no una duplicación accidental: este módulo necesita el `threadId` real de vuelta para `gmail_thread_id`, y `NotificationSender.enviar()` de Disrupciones solo devuelve `bool`. Mismo criterio de "única puerta por módulo" que Disrupciones ya aplica internamente entre `gmail_client.py` (leer) y `notification_sender.py` (enviar).

## Trazabilidad de casos de uso

- [x] CHK008 CU-O97 — `app/centro_ayuda/tests/test_ayuda.py` (6 tests) + verificado en vivo.
- [x] CHK009 CU-O98 — ídem.
- [x] CHK010 CU-O99 — ídem.
- [x] CHK011 CU-O100 — `app/centro_ayuda/tests/test_escalar.py` (4 tests, servicio probado con sender falso — mismo criterio que `NotificationSenderFalso` de Disrupciones, para no disparar un email real en cada corrida de la suite) + **verificado en vivo con un intento de envío real**: el caso se crea correctamente (estado `abierto`, auditado), pero el envío real a Gmail falló con `403 ACCESS_TOKEN_SCOPE_INSUFFICIENT` — **hallazgo real de infraestructura, no un bug de este módulo**: el refresh token OAuth configurado en `configuracion_sistema.gmail_api.refresh_token` solo tiene el scope de lectura (`gmail.readonly`, usado por Disrupciones para monitorear correo) — nunca se autorizó con `gmail.send`. Esto significa que el envío real de Disrupciones (`GmailNotificationSender`, RF-DIS-004/006) probablemente tiene el mismo problema latente y nunca se verificó en vivo contra un envío real tampoco (solo contra `NotificationSenderFalso` en tests). El manejo de este caso ya es correcto por diseño: `escalar_caso()` crea el registro incondicionalmente y solo completa `gmail_thread_id` si el envío tuvo éxito — un Agente ve el caso en la bandeja igual, con un aviso visible ("sin hilo — falló el envío") en vez de fallar silenciosamente o fabricar un hilo falso.

## Notas

- **Pendiente real, fuera de alcance de código:** re-autorizar el OAuth de Gmail (`gmail_api.client_id`/`client_secret`/`refresh_token`) con el scope `https://www.googleapis.com/auth/gmail.send` agregado — requiere pasar por la pantalla de consentimiento de Google con la cuenta `aerotracktravel.demo@gmail.com` y regenerar el refresh token. Sin esto, ni Centro de Ayuda ni Disrupciones pueden enviar correo real, solo leerlo.
- Al cerrar este módulo, actualizar `specs/000-sistema-general/pendientes-implementacion-codigo.md` — **hecho**.
