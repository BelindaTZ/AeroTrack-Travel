# Pendientes de implementación en código — catálogo v3.0/v3.1

**Creado:** 2026-07-18
**Actualizado:** 2026-07-19 (octava ronda) — módulo **Asistente IA** completo (Operativo + Táctico), el último de los 10 módulos nuevos del catálogo v3.0: conversación (anónima ephemeral o de pasajero persistida), contexto verificable REG-H1 (`contexto_service.py`, se ejecuta antes de cualquier llamada al LLM y solo devuelve hechos reales — reserva propia del pasajero, requisitos de visa cacheados), respuesta por plantilla determinista para hechos estructurados (no necesita al LLM), rechazo honesto sin datos inventados cuando no hay contexto verificado, escalación ofrecida, calificación de mensajes, backoffice de configuración (tono/temas permitidos/respuestas predefinidas) y reporte de consultas con separación resueltas/sin-respuesta-verificable. **Verificado en el escenario más exigente posible: sin ninguna credencial real de Groq/Gemini sembrada** — `test_reserva_ajena_nunca_se_expone` confirma que un pasajero nunca recibe datos de la reserva de otro, ni por plantilla ni citados por el LLM. Widget de chat flotante global (`_chat_asistente.html`, incluido en `layout_portal.html`). Dos bugs de aislamiento de tests corregidos (regex de código de reserva demasiado angosto; contaminación de `configuracion_sistema` entre tests) — ver `errores-conocidos.md`. Con este módulo, **los 10 módulos nuevos del catálogo v3.0 (Operativo + Táctico) quedan completos**. Ronda anterior (séptima): módulo **Ofertas y Promociones** completo (Operativo + Táctico): ofertas destacadas, destinos populares (estadística real sobre `busquedas_recientes`+`reserva_items`, nunca curación editorial), cupones de descuento con validación completa (vigencia/estado/usos/producto aplicable/doble canje) y acumulación configurable con descuento de paquete (CU-T44, excepción por cupón siempre gana sobre el default global), newsletter, backoffice de cupones/campañas/reporte. **Dos bugs reales encontrados y corregidos en verificación en vivo**: (a) PocketBase rechaza un `json` requerido vacío `{}` como "valor faltante" — mismo gotcha que `number`/`bool` en `0`/`false`, ver `feedback_pocketbase_required_numerico`; (b) bug propio — "Destinos populares" con origen inferido automáticamente (sin query param explícito) nunca mostraba resultados porque el router pasaba el query param crudo a la plantilla en vez del origen que el servicio realmente calculó. Envío real de campañas de email rechaza explícitamente (sin credencial SendGrid sembrada, a diferencia de Gmail que sí tiene credenciales pero con scope insuficiente). Ronda anterior (sexta): módulo **Centro de Ayuda** completo (Operativo + Táctico): buscar/ver/calificar artículos (anónimo o pasajero), escalar caso vía Gmail API real, backoffice de artículos/métricas (Administrador) y bandeja de casos escalados (Agente) con RBAC de dos niveles real (Nivel 2 restringe a Agente a la tabla `casos_escalados`). **Hallazgo real de infraestructura**: el refresh token OAuth de Gmail solo tiene scope de lectura — el envío real de email falla con 403, tanto para este módulo como (latente, nunca antes verificado en vivo) para el envío de notificaciones de Disrupciones. Ver `errores-conocidos.md`. Ronda anterior (quinta): módulo **Cuenta/Mis Viajes** completo: Mis Viajes agrupado por próxima/activa/pasada/sin_fecha (reutiliza `construir_detalle` de Reservas), favoritos con botón ♥ real conectado en Hoteles/Actividades/Inicio, viajes personalizados, búsquedas recientes retrofitadas en los 5 buscadores (Vuelos/Hoteles/Autos/Actividades/Cruceros ahora escriben en `busquedas_recientes` vía `app/shared/busqueda_reciente.py`), programa de beneficios con vencimiento real (RN-CTA-002). También: página de Inicio real (antes "/" redirigía directo a `/vuelos/buscar`), y dos bugs preexistentes corregidos (topbar del portal perdía `usuario` en 6 routers; tabs del backoffice de Pasajeros no recibían `nav_modulos`) — ver `errores-conocidos.md`. Ronda anterior (cuarta): brechas transversales cerradas (cupo real, `cantidad`, Reservas multi-producto, cargos locales de Hoteles). Ronda anterior (tercera): Actividades/Cruceros/Hoteles Fase 2-3 completadas, bug real de `itinerario_puertos` corregido. Segunda ronda: Autos Fase 2, primera vista HTML de Carrito. Ronda original: esquema real de `pocketbase-travel` migrado a v3, 10 módulos nuevos + nivel Táctico completo.
**Propósito:** consolidar en un solo lugar todo lo que queda por implementar en código sobre el catálogo v3.0/v3.1 completo (166 CU, 16 módulos Operativo + 17 Táctico), para no tener que releer ~66 archivos de spec cuando se retome el código.

**Estado de la base de datos:** el esquema (colecciones + campos) ya existe en `pocketbase-travel` — ver los 15 scripts en `scripts/pb_schema_*.py` (todos idempotentes, ya ejecutados). Lo que falta en todos los ítems de este documento es **código de aplicación** (routers, services, jobs de Airflow), no esquema. Excepción explícita: la migración de **datos** de `reservas`→`reserva_items` no aplica — las 9 reservas demo del modelo viejo se borraron (`scripts/limpiar_datos_demo_reservas.py`, 2026-07-19, autorizado explícitamente); las reservas nuevas se crean directamente sobre el modelo v3, sin dato legado que migrar.

---

## 1. Módulos ya implementados (Operativo) — extensiones pendientes

Los 6 módulos que ya tenían código antes del catálogo v3 (Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación). Todo lo del esquema real que estos ítems necesitaban ya existe.

### 1.1 Seguridad

| Ítem | RF | Detalle |
|---|---|---|
| Foto de perfil | RF-SEG-006 (ampliación) | Subir/reemplazar/mostrar `usuarios.foto_perfil` (file field, ya en esquema) en `/mi-perfil` |

CU-O112/O113 **no requieren trabajo** — ya cubiertos por `RF-SEG-011`/`roles_service.editar_rol`.

### 1.2 Pasajeros

| Ítem | RF | Detalle |
|---|---|---|
| Documentos de viaje | RF-PAS-005 | CRUD de pasaporte/cédula, país de emisión, vencimiento (`documentos_viaje`) |
| Viajeros frecuentes | RF-PAS-006 | CRUD de acompañantes recurrentes, autocompletado en checkout (`viajeros_frecuentes`) |

### 1.3 Vuelos (el más grande de los 6 originales)

| Ítem | RF | Detalle |
|---|---|---|
| Filtros completos de búsqueda | RF-VUE-007 | Escalas *(no implementable, sin dato en el modelo)*, equipaje, horario, duración + ordenamiento — hoy solo filtra por aerolínea |
| Predicción de precio | RF-VUE-008 | Job propio sobre `price_insights` de Google Flights (`predicciones_precio_ruta`) |
| Riesgo de disrupción en detalle | RF-VUE-009 | Solo lectura de `risk_score`/`risk_score_fuente` — **depende de que Disrupciones implemente CU-O83 primero** |
| Clase de cabina | RF-VUE-010 | Mostrar Economy/Business/First con precio real (rotación de cuota Google Flights) |
| Mapa de asientos | RF-VUE-011 | Generar mapa por vuelo en el mismo job de catálogo (`asientos_vuelo`) |
| Seleccionar asiento | RF-VUE-012 | `<<extend>>` de crear/modificar reserva — coordinar con Reservas |
| Asignación automática de asiento | RF-VUE-013 | Job por temporizador, análogo a CU-O44 |

**Orden sugerido:** filtros → predicción de precio → mapa de asientos + clase de cabina → selección de asiento (coordina con Reservas) → asignación automática → risk score (bloqueado por Disrupciones).

### 1.4 Reservas

| Ítem | RF | Detalle |
|---|---|---|
| **Adoptar `reserva_items` en el flujo de creación** | — (estructural) | ✅ **Hecho 2026-07-19.** `crear_reserva_service.py`/`modificar_reserva_service.py`/`cancelar_reserva_service.py` ahora hacen dual-write: `reservas.vuelo_id`/`tarifa_id` se siguen escribiendo tal cual (compatibilidad con los 4 puntos de lectura existentes en Facturación/Reservas que no necesitaban cambiar), y en paralelo se crea/actualiza el `reserva_items` (tipo_producto=vuelo) del que dependen Paquetes/Carrito/Cuenta-Mis-Viajes. `reservas.vuelo_id`/`tarifa_id` se marcaron `required=false` en el esquema (`scripts/pb_schema_reservas_fix_opcionales.py`) para que un futuro creador de paquetes (multi-producto) pueda dejarlos vacíos. Suite completa verificada: 154/157 tests pasan (las 3 fallas son de `app/vuelos/tests/test_busqueda.py`, preexistentes al rediseño visual v4, no relacionadas). |
| Requisitos de visa | RF-RES-008 | Consulta a Visa Requirement API con caché (`requisitos_visa_cache`) — depende de Pasajeros (`documentos_viaje`) |
| Voucher PDF | RF-RES-009 | Mismo patrón que `facturas.archivo_pdf` (`reservas.voucher_pdf`) |
| Selección de asiento (lado Reservas) | — | Ver 1.3 RF-VUE-012 — `<<extend>>` de CU-O21/O22/O23, coordinado |
| ~~`/reservas/{id}` (detalle) no soporta reservas multi-producto~~ | — (estructural) | ✅ **Cerrado 2026-07-19 (cuarta ronda)** — `construir_detalle()`/`ReservaDetalleOut`/`detalle_reserva.html`/`mis_reservas.html` ahora soportan reservas sin `vuelo_id` (`es_multiproducto`/`items`, ver `errores-conocidos.md` sección "Cierre de brechas"). Verificado en vivo (script E2E) y con 2 tests nuevos. Pendiente menor no resuelto: `pago_stub_service` no generaliza la recuperación de cupo tras expiración para reservas multi-producto (caso de carrera muy estrecho, documentado). |

### 1.5 Disrupciones

| Ítem | RF | Detalle |
|---|---|---|
| Risk score | RF-DIS-007 | Se integra al mismo job que genera el catálogo de Vuelos — no es un job separado |
| Posición en tiempo real | RF-DIS-008 | Proxy en vivo contra OpenSky Network, sin tabla propia (lee `vuelos_catalogo.avion_icao24`) |

### 1.6 Facturación

| Ítem | RF | Detalle |
|---|---|---|
| Conversión de moneda | RF-FAC-011 | ✅ **Hecho 2026-07-19** — `dags/dag_actualizar_tasas_cambio.py` (`@daily`), verificado con corrida real (6 monedas). Falta el lado de lectura (helper de conversión para mostrar precio local) — se agrega cuando alguna vertical lo necesite, hoy no tiene consumidor |
| Pago diferido de hotel | RF-FAC-012 | ✅ **Completo 2026-07-22** (junto con Hoteles CU-O60) — Stripe `authorize`→`capture` real, captura disparada manualmente desde `/backoffice/pagos-diferidos` (HotelLens no tiene señal real de confirmación del hotel) |

---

## 2. Módulos nuevos (Operativo) — 10 módulos, sin código previo

Todos "Draft — pendiente de revisión" en su `plan.md`. Fases resumidas; ver el `plan.md` de cada uno para RN/Constitution Check completo.

| Módulo | Fases (en orden) | Bloqueo real |
|---|---|---|
| **Hoteles** | ✅ **Completo 2026-07-22** (catálogo real HotelLens + búsqueda/detalle/filtros/reseñas/comparación reembolsable + cargos locales reales, 99 ciudades del CSV Holidu + selección vía Carrito con cupo real + pago diferido RF-HOT-009/CU-O86 con Stripe authorize→capture) | 17 tests Fase 1-3 + 8 de `test_pago_diferido.py` (Facturación) + 3 de `test_modalidad_pago.py` (Carrito) |
| **Autos** | ✅ **Completo 2026-07-19** (catálogo real + búsqueda/detalle/filtros + selección vía Carrito) — revalidación en vivo contra `fuente_oferta_ref` (RN-AUT-001) sigue sin código, bajo riesgo real (solo Expedia implementado; no aplica cupo, sin ese concepto en el catálogo) | 12 tests (5 catálogo + 7 búsqueda) |
| **Actividades** | ✅ **Completo 2026-07-19** (catálogo + reseñas + disponibilidad sintética + búsqueda/detalle/filtros/horarios/reseñas + selección vía Carrito, cupo real validado por `cantidad` de participantes) | 15 tests (5 catálogo + 7 búsqueda + 3 cupo en Carrito) |
| **Cruceros** | ✅ **Completo 2026-07-19** (catálogo real + disponibilidad sintética + búsqueda/itinerario/barco/comparación + selección vía Carrito, cupo real) | 9 tests (3 catálogo + 6 búsqueda). Bug real corregido: `itinerario_puertos` es `[{day,port}]`, no strings planos |
| **Paquetes** | ✅ **Completo 2026-07-19** — construcción, resumen con descuento real, cambio de componente, traslado aeropuerto, condiciones por componente | 9 tests, verificado en vivo (RN-PAQ-004: descuento nunca reduce el precio real de cada componente) |
| **Carrito** | ✅ **Completo 2026-07-19** — ver/agregar/eliminar + checkout con revalidación de precio Y cupo real (todo o nada, `app.shared.cupo_service`) + conversión real a `reserva_items` (con `cantidad`). Vista HTML (`router_vista.py`) es el punto de entrada real de las 4 verticales nuevas | 10 + 4 + 3 tests, verificado en vivo con productos reales de las 4 verticales |
| **Cuenta/Mis Viajes** | ✅ **Completo 2026-07-19** (Mis Viajes agrupado por próxima/activa/pasada/sin_fecha + favoritos con botón ♥ real + viajes personalizados + búsquedas recientes retrofitadas en los 5 buscadores + programa de beneficios con vencimiento) | 21 tests, verificado en vivo |
| **Centro de Ayuda** | ✅ **Completo 2026-07-19** (buscar/ver/calificar artículos + escalar caso vía Gmail API + backoffice: gestionar artículos, métricas con filtro de período, bandeja de casos escalados para Agente) | 20 tests, verificado en vivo. Envío real de email bloqueado por scope OAuth insuficiente — ver `errores-conocidos.md` |
| **Ofertas y Promociones** | ✅ **Completo 2026-07-19** (ofertas destacadas + términos + destinos populares reales + cupones en checkout con acumulación con paquete + newsletter + backoffice: cupones, campañas, reporte, config. acumulación) | 28 tests, verificado en vivo. Envío real de campañas rechaza sin credencial SendGrid — ver `errores-conocidos.md` |
| **Asistente IA** | ✅ **Completo 2026-07-19** (conversación anónima ephemeral/pasajero persistida + contexto verificable REG-H1 + respuesta por plantilla desde reserva real + rechazo honesto sin dato + escalación ofrecida + calificación + widget flotante global) | 15 tests, verificado en vivo sin credencial LLM real (el escenario más exigente para REG-H1) |

---

## 3. Nivel Táctico — 17 módulos (6 originales + 10 nuevos + Integraciones)

Integraciones es el único módulo **solo Táctico** (no tiene nivel Operativo propio — CU-T05/T06 generalizan lo que antes era exclusivo de Vuelos).

| Módulo | Fases (en orden) | Nota de secuencia |
|---|---|---|
| **Integraciones** | ✅ **Implementado 2026-07-19** — `app/integraciones/`, 10/10 tests. 1) Sembrar/configurar `fuentes_datos_externas` · 2) Bitácora `sincronizaciones_log` | Precondición de configuración de Hoteles/Autos/Actividades/Cruceros y refuerzo de Vuelos — pero esos 5 jobs de catálogo siguen sin existir, así que la bitácora no tiene corridas automáticas reales todavía (CHK010 abierto) |
| **Seguridad** | 1) Dashboard de intentos fallidos + expiración forzada · 2) Configurar política · 3) Matriz de permisos | Ninguno — 4 CU sobre servicios ya construidos |
| **Pasajeros** | 1) Ver segmentación · 2) Exportar base | Bloqueado por Reservas 1.4 (`reserva_items`) para cálculo real de frecuencia/destino |
| **Vuelos** | 1) Configurar/monitorear catálogo · 2) Reporte de rutas · 3) Config. asientos/cabina (CU-T39/40/41) | **CU-T39/40/41 son precondición real de CU-O114-117** (Operativo 1.3) — priorizar sobre T06/T07/T08 si el objetivo es desbloquear asientos/cabina |
| **Reservas** | 1) Reporte por estado · 2) Monitorear próximas a vencer · 3) Configurar políticas de reembolso (CU-T18) | CU-T18 es transversal — lo consumen 5 verticales de producto, no solo Reservas |
| **Disrupciones** | 1) Dashboard de monitoreo · 2) Reporte de disrupciones · 3) Configurar umbral de risk score | CU-T20 bloqueado por CU-O83 (Operativo 1.5, risk score) |
| **Facturación** | 1) Dashboard financiero · 2) Reporte de ingresos | Ambos implementables ya, sobre datos reales existentes |
| **Hoteles** | 1) Comparación de propiedades (CU-T09) · 2) Reporte de hoteles más reservados | Depende de que Hoteles Operativo (sección 2) esté implementado primero |
| **Autos** | 1) Reporte de reservas por proveedor/categoría (CU-T11) | Depende de Autos Operativo + Reservas 1.4 |
| **Actividades** | 1) Configurar disponibilidad sintética (CU-T42) · 2) Reporte de más reservadas | **CU-T42 debe ir junto con la Fase 2 de Actividades Operativo**, no después |
| **Cruceros** | 1) Configurar disponibilidad sintética (CU-T43) · 2) Reporte de más consultados | **CU-T43 debe ir junto con la Fase 2 de Cruceros Operativo**, no después |
| **Paquetes** | 1) Configurar % de descuento (CU-T14) · 2) Reporte de combinaciones más vendidas | Paquetes Operativo ya está completo — `tipos_paquete_descuento` sembrado directo (4 combinaciones), falta la UI de administración (CU-T14) para editarlas sin tocar el script |
| **Carrito** | ✅ **Completo 2026-07-22** (configurar umbral/plantilla de abandono + job de detección + reporte de recuperación) | `carritos.fue_abandonado`/`fecha_marcado_abandonado` agregados (`pb_schema_carrito_abandono.py`) para no perder el historial cuando un carrito vuelve a `activo` y se convierte; `CarritoRepository.carrito_de_trabajo` reactiva un carrito `abandonado` en el único punto de entrada real (ver/agregar/checkout), sin eso CU-T27 nunca tendría recuperados que contar. 15 tests |
| **Cuenta/Mis Viajes** | 1) Configurar programa de beneficios (CU-T24) · 2) Reporte de alertas de precio | CU-T24 es precondición real de RF-CTA-006 (Operativo Fase 4) |
| **Centro de Ayuda** | ✅ **Completo 2026-07-19** (gestionar artículos + bandeja de casos escalados para Agente + métricas con filtro de período) | 8 tests de backoffice. RBAC Nivel 2 real: Agente restringido a `casos_escalados` |
| **Ofertas y Promociones** | 1) Gestionar cupones (CU-T30) · 2) Campañas de email · 3) Reporte de cupones · 4) Configurar acumulación cupón+paquete (CU-T44) | CU-T30 es precondición real de RF-OFE-003 (Operativo Fase 3). Fase 4 ya tiene el dato default sembrado en `configuracion_sistema`, falta el router (`router_config_acumulacion.py`) |
| **Asistente IA** | ✅ **Completo 2026-07-19** (configurar tono/temas permitidos/respuestas predefinidas + reporte de consultas con filtro de período) | 4 tests de backoffice. CU-T34 confirmado en vivo como precondición real y efectiva de RN-IA-T01 (Operativo) |

---

## 4. Dependencias cruzadas — grafo completo

```
Integraciones (Táctico)                    ──► Hoteles/Autos/Actividades/Cruceros/Vuelos (config real de sync)

Pasajeros (documentos_viaje)                ──► Reservas (requisitos_visa_cache)
Vuelos (asientos_vuelo, clase_cabina)       ──► Vuelos (seleccionar asiento) ──► Reservas (asiento_id en reserva_pasajeros)
Disrupciones (risk_score, job de Vuelos)    ──► Vuelos (mostrar risk score en detalle)
Facturación (tasas_cambio)                  ──► Hoteles/Autos/Actividades/Cruceros/Paquetes (presentación de precio)
Hoteles Operativo Fase 4 (CU-O60)           ──► Facturación (pago diferido de hotel)

Reservas 1.4 (adoptar reserva_items)        ──► Paquetes (✅ desbloqueado y completo 2026-07-19)
Reservas 1.4                                ──► Carrito Fase 2 (✅ desbloqueado y completo 2026-07-19)
Reservas 1.4                                ──► Cuenta/Mis Viajes Fase 1 (✅ desbloqueado y completo 2026-07-19)
Reservas 1.4                                ──► Pasajeros Táctico (segmentación por frecuencia real)
Reservas 1.4                                ──► Autos Táctico (reporte por reserva)

Actividades Táctico CU-T42                  ──► junto con Actividades Operativo Fase 2 (no después)
Cruceros Táctico CU-T43                     ──► junto con Cruceros Operativo Fase 2 (no después)
Paquetes Táctico CU-T14                     ──► junto con Paquetes Operativo Fase 1 (ambos bloqueados por Reservas 1.4)
Cuenta/Mis Viajes Táctico CU-T24            ──► Cuenta/Mis Viajes Operativo Fase 4 (programa de beneficios)
Ofertas Táctico CU-T30                      ──► Ofertas Operativo Fase 3 (cupones en checkout)
Asistente IA Táctico CU-T34                 ──► Asistente IA Operativo Fase 3 (✅ desbloqueado y completo 2026-07-19)
Centro de Ayuda Táctico CU-T28              ──► Centro de Ayuda Operativo Fase 1 (no hay artículos sin esto)
Disrupciones Operativo CU-O83 (risk score)  ──► Disrupciones Táctico CU-T20
Vuelos Táctico CU-T39/40/41                 ──► Vuelos Operativo CU-O114-117 (asientos/cabina)
```

**El nodo central del grafo es Reservas 1.4** (adoptar `reserva_items` en la creación de reservas) — desbloquea 5 módulos nuevos (Paquetes, Carrito checkout, Cuenta/Mis Viajes, Pasajeros Táctico, Autos Táctico). Es el único ítem de toda esta lista que vale la pena priorizar por pura cantidad de cosas que desbloquea, no porque sea trivial.

---

## 5. Orden de implementación sugerido (visión completa)

1. ~~**Integraciones Táctico** (Fase 1)~~ — ✅ hecho 2026-07-19.
2. ~~**Reservas 1.4** (adoptar `reserva_items`)~~ — ✅ hecho 2026-07-19. Paquetes/Carrito/Cuenta-Mis-Viajes/Pasajeros Táctico/Autos Táctico ya pueden empezar a construirse sobre `reserva_items` real.
3. ~~**Facturación RF-FAC-011** (`tasas_cambio`)~~ — ✅ hecho 2026-07-19.
4. ~~**Hoteles / Autos / Actividades / Cruceros Operativo**~~ — ✅ hechos 2026-07-19 (Fase 1 catálogo + Fase 2/3 búsqueda-detalle-selección, las 4 verticales completas de punta a punta vía Carrito).
5. ~~**Paquetes + Carrito**~~ — ✅ hechos 2026-07-19.
6. ~~**Cuenta/Mis Viajes**~~ — ✅ hecho 2026-07-19. ~~**Centro de Ayuda**~~ — ✅ hecho 2026-07-19. ~~**Ofertas y Promociones**~~ — ✅ hecho 2026-07-19. ~~**Asistente IA**~~ — ✅ hecho 2026-07-19. **Los 10 módulos nuevos del catálogo v3.0 (Operativo + Táctico) quedan completos.**
7. **Resto de extensiones de los 6 módulos originales** (sección 1) que no bloquean nada más — filtros de Vuelos, documentos de viaje de Pasajeros, etc. — se pueden intercalar en cualquier momento, son hojas del grafo.
8. ~~**Brechas transversales expuestas por el cierre del punto 4**~~ — ✅ resueltas 2026-07-19 (cuarta ronda): (a) `carrito_service` ahora valida y reserva cupo real (todo o nada) vía `app.shared.cupo_service`, generalizado desde Vuelos; (b) `/reservas/{id}` y "Mis reservas" soportan reservas multi-producto sin `vuelo_id`; (c) Hoteles Fase 3 (cargos locales) completa con 99 ciudades reales importadas. Pendiente real (menor, no bloqueante): Fase 4 de Hoteles (pago diferido) sigue sin código, depende de Facturación CU-O86; `pago_stub_service` no generaliza la recuperación de cupo tras expiración para reservas multi-producto en el caso de carrera RN-RES-005/QP-04.
