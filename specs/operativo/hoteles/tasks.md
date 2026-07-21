# Tasks: Hoteles

**Input:** [`plan.md`](./plan.md) · [`hoteles-spec.md`](./hoteles-spec.md) · [`checklist.md`](./checklist.md) · [`../../.specify/memory/constitution.md`](../../../.specify/memory/constitution.md)
**Código fuente:** `app/hoteles/` *(Fase 1 implementada 2026-07-19, resto sin código)*
**Orden de fases:** idéntico al de `plan.md` (Fase 1 → Fase 4), precedido por una Fase 0 de setup.
**Trazabilidad:** cada tarea de prueba referencia su ítem `CHKxxx` de `checklist.md`.

## Formato: `[ID] [P?] Descripción`

- **[P]**: archivo distinto, sin dependencia de otra tarea del mismo bloque — paralelizable.
- Sin `[P]`: depende de una tarea anterior del mismo bloque.

---

## Fase 0: Setup e infraestructura del módulo

**⚠️ Bloqueante:** ninguna fase 1-4 puede empezar sin esto.

- [x] T001 Crear estructura `app/hoteles/` (`__init__.py`, `services/`, `repositories/`, `tests/` — `templates/` diferido a Fase 2, todavía no hay pantallas)
- [x] T002 [P] Crear colección `hoteles_catalogo` en `pocketbase-travel` — `scripts/pb_schema_hoteles.py`
- [x] T003 [P] Crear colección `hoteles_tarifas` — corregida después con `scripts/pb_schema_hoteles_fix_required.py` (`precio_final`/`reembolsable` a `required=false`, ver `errores-conocidos.md`)
- [x] T004 [P] Crear colección `hoteles_resenas`
- [x] T005 [P] Crear colección `cargos_locales_destino` (esquema listo; importación CSV real es Fase 3, sin código todavía)
- [x] T006 Crear `app/hoteles/repositories/hoteles_repo.py` — usa `app/shared/pocketbase_client.py`
- [x] T007 ~~Crear `app/hoteles/schemas.py`~~ — no fue necesario en Fase 1 (sin endpoints públicos todavía, `router_interno.py` devuelve el dict del servicio directo)
- [x] T008 [P] Sembrar credenciales de HotelLens en `configuracion_sistema` (categoría `hoteles`) — `scripts/seed_hoteles_config.py`
- [x] T009 [P] `app/hoteles/tests/conftest.py` — doble determinista `HotelLensClientFalso` (mismo patrón que Disrupciones)

**Checkpoint:** ✅ las 4 colecciones existen; `pytest app/hoteles/` corre.

---

## Fase 1: Generación de catálogo (RF-HOT-004, 005)

- [x] T010 `app/hoteles/services/hotellens_client.py` — cliente de los 3 endpoints reales: `GET /api/v1/hotels`, `GET /api/v1/hotels/prices`, `GET /api/v1/booking/hotels/details`. Nombres de campo corregidos tras verificar contra la API real — ver `errores-conocidos.md` ("Nombres de campo reales de HotelLens distintos a los asumidos").
- [x] T011 `app/hoteles/services/hotellens_client.py` — `GET /api/v1/hotels/reviews` (reseñas, mismo ciclo) — campos confirmados exactos al primer intento.
- [x] T012 `app/hoteles/services/catalogo_service.py` — orquesta los 3 pasos, escribe `hoteles_catalogo`/`hoteles_tarifas` con cupo/cancelación reales (CHK008, CHK009)
- [x] T013 `app/hoteles/services/catalogo_service.py` — escribe `hoteles_resenas` en el mismo ciclo (CHK010)
- [x] T014 `dags/dag_generar_catalogo_hoteles.py` — thin DAG (`@daily`-like, cada 12h) que dispara `POST /internal/hoteles/generar-catalogo`, mismo patrón que `dag_expirar_reservas_pendientes.py`. `is_paused_upon_creation=True` a propósito — cada corrida gasta cuota real, activar manualmente.
- [x] T015 [P] `app/hoteles/tests/test_catalogo_service.py` — 4 tests: camino feliz (CHK001, CHK008, CHK009), idempotencia (no duplica hotel, reemplaza tarifas), sin oferta de Booking.com resoluble (`parcial`, no es error), falla completa (`fallido` con `error_detalle`).

**Checkpoint:** ✅ el catálogo se puebla con datos reales de HotelLens — verificado en vivo (Hilton Paris Opera, `hotel_id` Booking.com 54642, 1 tarifa real con `rooms_left=14`, 3 reseñas reales); `sincronizaciones_log` registra la corrida (`estado="exitoso"`).

---

## Fase 2: Búsqueda, detalle, filtros y reseñas (RF-HOT-001, 002, 003, 007, 008 parcial)

**Estado:** ✅ Hecho 2026-07-19.

- [x] T016 `app/hoteles/router_busqueda.py` — `GET /hoteles/buscar`: filtra por ciudad (CHK002)
- [x] T017 `app/hoteles/router_busqueda.py` — `GET /hoteles/{id}`: detalle completo, incluye reseñas y cargos locales en la misma pantalla (CHK003, CHK005, CHK006) — sin sub-rutas `/resenas`/`/cargos-locales` separadas
- [x] T018 Filtros instantáneos (estrellas mínimas, precio máximo, calificación mínima — **servicios y zona no implementados**, ver `checklist.md` CHK004) (REG-J9)
- [x] T019 [P] `app/hoteles/templates/buscar_hoteles.html`, `detalle_hotel.html`
- [x] T020 [P] `app/hoteles/tests/test_busqueda.py` — 7 tests: sin resultados (CHK002), precio desde (mínimo de tarifas), filtro de estrellas, filtro de precio, detalle con reembolsable/no reembolsable (CHK007), detalle con reseñas (CHK005), tarifa sin cupo no ofrece agregar, 404

**Checkpoint:** ✅ un pasajero busca, filtra y ve el detalle de un hotel real (HotelLens) con reseñas y comparación reembolsable/no reembolsable.

---

## Fase 3: Cargos locales (RF-HOT-008)

**Estado:** ✅ Hecho 2026-07-19 (segunda ronda).

- [x] T021 ~~`router_resenas.py`~~ — fusionado con el detalle (Fase 2, T017)
- [x] T022 ~~`router_cargos.py`~~ — fusionado con el detalle (Fase 2, T017); repositorio filtra por `ciudad` + `activo=true`
- [x] T023 `dags/dag_importar_cargos_locales.py` — disparo manual (`schedule=None`), llama `POST /internal/hoteles/importar-cargos-locales` → `app/hoteles/services/cargos_locales_service.py`. El CSV real trae DOS tablas concatenadas (descubierto al inspeccionarlo) — solo se importa la Tabla 1 (City/Country/regla de texto). `Dockerfile` actualizado (`COPY fuentes_extra ./fuentes_extra`) para que el archivo exista dentro del contenedor `app-travel`.
- [x] T024 `app/hoteles/tests/test_cargos_locales.py` — 6 tests: parseo solo trae Tabla 1, clasificación de regla simple (monto fijo/porcentaje), "No tourist tax", regla compuesta no inventa valor, importación real crea+actualiza (idempotente)

**Checkpoint:** ✅ verificado en vivo contra el CSV real — 99 ciudades importadas; Paris muestra su regla real compuesta ("5star: €11.38; ..."), correctamente sin estimado inventado.

---

## Fase 4: Selección de habitación (RF-HOT-006) — vía Carrito; pago diferido (RF-HOT-009) sin implementar

**Decisión de alcance (2026-07-19):** mismo criterio que Autos/Actividades/Cruceros — sin `seleccion_service.py`/`router_seleccion.py` propios. Cada tarifa en `detalle_hotel.html` postea a `/carrito/agregar` (Carrito).

- [x] T025 Comparación reembolsable/no reembolsable — badge explícito en cada tarifa antes del botón de agregar (CHK007, RN-HOT-002)
- [x] T026 Revalidar cupo real antes de confirmar (RN-HOT-001) — **cerrado 2026-07-19 (segunda ronda).** `carrito_service.confirmar_checkout` verifica y reserva cupo real (`app.shared.cupo_service`, generalizado desde Vuelos) contra `hoteles_tarifas.cupos_disponibles` antes de crear la reserva — todo o nada.
- [ ] T027 Modalidad `pago_diferido` (RN-HOT-004, CHK011) — **no implementado.** `hoteles_tarifas` no tiene ese campo en el esquema; depende de CU-O86 (Facturación), tampoco construido.
- [x] T028 Integración real con `reserva_items` — verificada en vivo (tarifa real → carrito → checkout → `reserva_items.tipo_producto=hotel`, cupo decrementado)
- [ ] T029 Punto de integración documentado hacia CU-O86 — no aplica todavía, pago diferido no existe como modalidad
- [ ] T030 `test_seleccion.py` — no existe; el caso reembolsable/no reembolsable quedó cubierto en `test_busqueda.py` (T020, CHK007), y la validación de cupo en `app/carrito/tests/test_cupo.py`. Pago diferido no tiene test porque no hay código (CHK011 abierto).

**Checkpoint:** ✅ un pasajero compara habitaciones reembolsables vs. no reembolsables y confirma la compra de una tarifa real, con cupo validado server-side. Solo pago diferido queda como trabajo pendiente real, no simulado.

---

## Cierre

- [x] T031 Grep de verificación de cero secretos hardcodeados sobre `app/hoteles/` — sin hallazgos
- [x] T032 `pytest app/hoteles/ app/carrito/` y suite completa sin regresión cruzada
- [x] T033 `checklist.md` repasado; `pendientes-implementacion-codigo.md` actualizado

---

## Dependencias entre fases

- Fase 0 bloquea todo lo demás.
- Fase 1 bloquea Fase 2 (necesita catálogo poblado) — resuelto.
- Fase 3 (cargos locales) — resuelto.
- Fase 4 (selección) se resolvió reutilizando Carrito, cupo real incluido — solo pago diferido sigue bloqueado por piezas no construidas (esquema de `hoteles_tarifas`, CU-O86 de Facturación).
