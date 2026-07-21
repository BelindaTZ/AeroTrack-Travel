# Fuentes de datos y procesos por tabla — guía para implementación

> Generado 2026-07-17 al cerrar la sesión de diseño de BD. Consolida en un solo lugar de
> dónde sale el dato de cada tabla de `docs/aerotrack-travel-propuesta-tablas-v3.dbml` —
> el detalle completo (endpoints exactos, campos reales, gotchas) sigue viviendo en
> `docs/apis-reference.md`, `docs/apis-listas-implementacion.md` y
> `docs/google-flights-serpapi-hallazgos.md`; este documento es el índice rápido para no
> tener que releer las 68 tablas del `.dbml` cada vez que se empiece a programar un módulo.
>
> **Tipos de proceso** (coinciden con `tipo_uso_fuente` del esquema):
> - 🔵 **constante** — se llama en cada acción real del usuario, no llena una tabla propia.
> - 🟢 **catálogo periódico** — job programado (Airflow) que llena/actualiza la tabla por adelantado; nunca en vivo por búsqueda del pasajero.
> - 🟡 **cache bajo demanda** — se llama la primera vez que hace falta un dato puntual y se guarda.
> - ⚪ **regla de negocio interna** — no hay API real, se genera con una fórmula/regla propia.
> - ⚫ **CRUD de la app** — lo escribe directamente la acción del usuario/administrador, sin proceso automático detrás.

---

## Seguridad
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `roles`, `modulos`, `permisos`, `roles_permisos`, `roles_permisos_tablas`, `modulo_tablas` | ⚫ CRUD (Administrador) | Seed inicial manual al implementar (10 módulos nuevos de v3 necesitan sus filas en `modulos`/`modulo_tablas`) |
| `usuarios` | ⚫ CRUD (registro/login) | `foto_perfil` es file field, ver sección Archivos al final |
| `auditoria` | ⚫ generado por el sistema | Insert-only, nunca update/delete |
| `configuracion_sistema` | ⚫ CRUD (Administrador) | Incluye las categorías nuevas `disponibilidad_*` |

## Integraciones *(módulo nuevo)*
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `fuentes_datos_externas`, `sincronizaciones_log` | ⚫ meta-registro del propio sistema de sync | Se seedea una fila por cada fuente real (AeroDataBox, HotelLens, etc.) + las `regla_negocio_interna`; `sincronizaciones_log` la escribe cada corrida del DAG correspondiente |

## Gestión de cuota real (catálogos periódicos con techo duro) — 2026-07-20

**Contexto**: los catálogos de Hoteles/Autos/Actividades/Cruceros ya tenían su pipeline completo (DAG
delgado → `POST /internal/<modulo>/generar-catalogo` → `catalogo_service.generar_catalogo()` → cliente
RapidAPI → PocketBase), pero corrían sin ningún control de cuota mensual. Se asumió inicialmente (con
base en ausencia de errores 429/402 en pruebas puntuales, o en headers de rate-limit por ventana
malinterpretados como techo mensual) que solo HotelLens tenía un límite real. El usuario revisó su panel
real de RapidAPI (Analytics/Usage de cada suscripción) y confirmó que **las 4 fuentes tienen el mismo
tipo de techo mensual duro del plan Basic** — con el diseño original (autos y actividades corriendo
`@daily` sin pausa desde que se crearon, sin ningún gate) el consumo real ya estaba en 100% (autos),
73% (hoteles) y 52% (cruceros) para el 20 de julio, sin que nuestro propio `sincronizaciones_log` supiera
nada de eso (esas corridas automáticas usaron código previo a este gate). Si en el futuro un proveedor
vuelve a fallar o se agota antes de lo esperado, **empezar por revisar esta sección** antes de
re-investigar desde cero — y **desconfiar de cualquier "sin límite mensual" que no venga confirmado
directamente del panel de RapidAPI**, no de la ausencia de errores 429 en pruebas puntuales.

**Límites duros reales confirmados en el panel de RapidAPI (plan Basic, por fuente) — verificado
2026-07-20:**

| Fuente | Límite mensual duro | Rate limit | Costo real por unidad procesada | Uso real al 2026-07-20 |
|---|---|---|---|---|
| HotelLens | **100 req/mes** | 10 req/min | hasta ~7 llamadas/ciudad (`max_hoteles_por_ciudad=2` × 3 llamadas c/u + 1 búsqueda) | 73% |
| Global Rental Cars | **100 req/mes** | 1000 req/hora | 2 llamadas/ciudad, fijo (auto-complete + search) | 100% (agotado) |
| Travel Advisor | **500 req/mes** | 5 req/seg | hasta ~5 llamadas/ciudad (geo_id + list + hasta 3 detalles) | 13.6% |
| Cruise Pricing API | **100 req/mes** | 10 req/min | 2 fijas (navieras+búsqueda) + 1 llamada/crucero de detalle | 52% |

**Importante**: Cruise Pricing se documentó inicialmente como "~500,000/mes, cuota amplísima" en base a
un header de rate-limit por ventana observado en pruebas (`docs/apis-reference.md:429`) — ese número
**era del rate limit, no del techo mensual real**. Corregido 2026-07-20 tras revisar el panel real:
también es 100/mes como HotelLens y Global Rental Cars.

**Mecanismo de protección (dos capas, la primera es la que de verdad importa):**
1. **Gate de cuota real** — `app/shared/cuota_service.py` (`hay_cupo()`/`unidades_usadas_este_mes()`).
   Antes de empezar CADA ciudad nueva (hoteles/autos/actividades) o CADA crucero nuevo (cruceros) dentro
   de `catalogo_service.generar_catalogo()`, suma `sincronizaciones_log.unidades_cuota_consumidas` del
   mes en curso para esa fuente
   y corta la corrida (`estado="parcial"`, `resumen["motivo_parcial"]="cuota_mensual_agotada"`) si ya se
   usó el 85% del techo (`fuentes_datos_externas.cuota_mensual_estimada` — ahí vive el número real de la
   tabla de arriba; si algún día RapidAPI cambia el plan, **ese es el campo a actualizar**, vía
   `scripts/seed_fuentes_datos_externas.py`). No hay un contador mutable aparte — se deriva de
   `sincronizaciones_log`, que ya es la fuente de verdad de cada corrida (incluye
   `unidades_cuota_consumidas`, llenado por cada `*_client.py` vía su atributo `llamadas_realizadas`).
2. **Rotación de ciudades** — `app/shared/rotacion_ciudades.py` (`rebanada_rotativa()`). Universo curado
   de 40 ciudades por módulo (`hoteles.ciudades_seed`/`autos.ciudades_seed`/`actividades.ciudades_seed`
   en `configuracion_sistema`); cada corrida solo toca una rebanada (`*.ciudades_por_corrida`) elegida
   determinísticamente por día-del-año, sin estado nuevo en BD. Esto es solo para dar variedad entre
   corridas — el gate de arriba es lo que realmente impide pasarse del techo, incluso si la rotación
   estuviera mal calibrada.
3. **Throttle de ráfaga** — solo HotelLens lo necesita (10 req/min): `hotellens_client.py` espera ~13s
   entre llamadas HTTP sucesivas del mismo cliente.

**Ritmo real esperado para cubrir las 40 ciudades por primera vez** (el gate manda, estos números son
orientativos y parten de cuota 100% disponible — ver estado real de cada una arriba, que al
2026-07-20 ya está consumida en gran parte): HotelLens ~10-12 ciudades/mes (**~4 meses** para la primera
pasada completa, el más lento por su relación costo/techo); Global Rental Cars ~42 ciudades/mes (~1
corrida/mes le alcanza); Travel Advisor ~85 ciudades/mes (varias pasadas por mes, el más holgado);
Cruise Pricing ~40 cruceros/mes con `limite_cruceros=10` (~4 corridas/mes).

**Estado operativo al 2026-07-20**: los 4 DAGs de catálogo (`aerotrack_travel_catalogo_hoteles/autos/
actividades/cruceros`) están **pausados** — autos/hoteles/cruceros por consumo real ya alto (100%/73%/52%)
sin margen razonable para lo que queda del mes; actividades pausado temporalmente solo hasta reconstruir
`app-travel` con este gate (13.6% real, con margen sano una vez reactivado). Antes de reactivar
cualquiera, sembrar su consumo real en `sincronizaciones_log` (no queda en 0 automáticamente) y confirmar
que `app-travel` corre la imagen reconstruida con este código — el contenedor NO tiene el código en vivo
(`docker-compose.yml`, servicio `app-travel`, sin bind-mount), así que un `git pull`/edit sin
`docker compose build app-travel && docker compose up -d app-travel` no tiene ningún efecto real.

**Si hace falta expandir el universo de 40 ciudades o subir la cadencia**: primero recalcular contra la
tabla de límites de arriba (no asumir "no dio 429 en la prueba" = sin límite, ese fue justamente el
error de esta sesión) — idealmente confirmando en el panel real de RapidAPI, no solo con curl.

## APIs de Google Cloud — 2026-07-20

**Contexto**: 8 keys de Google Cloud vivían en `.env` (sección "# Google cloud APIS") sin usarse en
ningún código. Se cruzaron contra `docs/aerotrack-travel-casos-de-uso-v3.md` y contra las cuotas reales
del usuario (Cuotas y Límites → IAM). Resultado: **Places API** y **Maps Embed API** resultaron
directamente útiles; **Geocoding**, **Maps JavaScript** y **Routes** son secundarias/complementarias;
**Travel Impact Model API**, **Travel Partner Prices API** y la key de **Gmail** quedan **deliberadamente
sin explorar** a pedido del usuario (las dos primeras necesitarían confirmar partnership con Google, la
tercera es redundante con el Gmail OAuth que ya funciona para Centro de Ayuda) — si una sesión futura
necesita revisarlas, no hay nada ya hecho que perder, es investigación desde cero.

**Cuotas reales** (Cuotas y Límites → IAM, confirmadas por el usuario 2026-07-20) — a diferencia de
RapidAPI (plan fijo, no ajustable sin cambiar de plan pago), **las cuotas de Google Cloud normalmente se
pueden aumentar desde la misma consola** una vez verificada la facturación — estos números son el techo
de hoy, no necesariamente un límite duro permanente:

| API | Método usado | Límite diario | Límite por minuto |
|---|---|---|---|
| Places API (New) | autocomplete / getPlace | **100/día** | 600-12,000/min según método |
| Geocoding API | clásica (`/maps/api/geocode/json`) — la que usamos | **sin límite diario** | 3,000/min |
| Geocoding API | nueva ("v4": GeocodeAddress/Location/Place) — NO la usamos | 100/día | 1,500/min |
| Maps Embed API | — | sin cuota configurada en el sistema | — |
| Maps JavaScript API | Map loads | sin límite diario | 30,000/min (300/min/usuario) |
| Routes API | ComputeRoutes (Directions) — la que usamos | **100/día** | 3,000/min |
| Routes API | ComputeRouteMatrix — NO la usamos | sin límite diario | 3,000/min |

**Mecanismo de protección**: estas 3 (Places/Geocoding/Routes) se llaman **en vivo, por interacción de
usuario** — no tienen un "run" de catálogo como Hoteles/Autos/Actividades. El gate correspondiente es
`app/shared/cuota_service.cupo_diario_disponible()`/`.registrar_uso_diario()` (nuevo, generaliza el
patrón que ya usaba `AviationStackClient._config()`/`.esta_disponible()` en
`app/disrupciones/integrations/flight_status_client.py`): contador mutable en `configuracion_sistema`
(`google_apis.<nombre>.limite_diario`/`.usadas_dia`/`.periodo_actual`), con reseteo automático al
cambiar el día. Geocoding no lo necesita — usamos deliberadamente el endpoint clásico sin límite diario.

**Qué quedó implementado (2026-07-20)**:
- `app/shared/google_apis/` — paquete nuevo con `places_client.py`, `geocoding_client.py`,
  `routes_client.py` (patrón `abc.ABC` + implementación real, igual que `hotellens_client.py`) y
  `maps_embed.py` (funciones puras, sin cliente HTTP — el iframe lo carga el navegador del usuario, no
  nuestro backend).
- `scripts/seed_google_apis_config.py` — siembra las 5 keys + límites diarios en `configuracion_sistema`
  (categoría `google_apis`), mismo patrón idempotente-actualizable que los `seed_*_config.py`.
- **Única funcionalidad visible conectada esta ronda**: Maps Embed en detalle de hotel (CU-O55, card
  "Ubicación", usa `hotel.latitud/longitud` que ya llegan reales de HotelLens) y en detalle de crucero
  (CU-O72, card "Ruta del crucero", modo `directions` con nombres de puerto como texto — sin necesitar
  Geocoding).
- **Sin UI conectada todavía** (bases listas, esperando su fase de producto): Places API (candidata a
  reemplazar la lista curada de 40 ciudades del selector origen/destino — requiere el primer JS propio
  del proyecto, hoy 100% Jinja2 server-rendered, ver fase pendiente del "dropdown estilo Despegar");
  Maps JavaScript API (mapa interactivo, ej. posición de aeronave en vivo CU-O84 — mismo requisito de JS
  nuevo); Routes API (candidata a "distancia al centro" en tarjetas de hotel, patrón visto en el análisis
  de la interfaz de Despegar de esta sesión, pendiente de diseño de producto).

## Pasajeros
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `pasajeros`, `documentos_viaje`, `viajeros_frecuentes` | ⚫ CRUD (Pasajero) | Sin fuente externa automática |

## Vuelos
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `aerolineas`, `politicas_reembolso`, `niveles_tarifa` | ⚫ CRUD (Administrador) | Seed manual/negociación de comisión |
| `vuelos_catalogo` — `numero_vuelo`, `horario`, `avion_modelo` | 🟢 **AeroDataBox FIDS** (`/flights/airports/{codeType}/{code}/{fromLocal}/{toLocal}`) | Rotación **3 hubs/día** de los 15 curados (~360 u/mes), ventana máx. 12h/llamada, cubre múltiples rutas por llamada |
| `vuelos_catalogo` — `avion_icao24` | 🟢 **AviationStack** (`/v1/flights?dep_iata=&arr_iata=&airline_iata=`) | Mismo llamado que valida el número de vuelo cruzado |
| `vuelos_catalogo` — `precio_base`, `emisiones_co2_kg`, `fuente_busqueda_ref`, `detalles_extra` | 🟢 **Google Flights (SerpApi, `engine=google_flights`)** | Rotación 2-3 rutas/día (~200-270 u/mes), presupuesto separado de 250/mes |
| `vuelos_catalogo` — `risk_score` | 🟢 MinIO `agg_otp_aerolinea_mes`/`agg_causas_retraso_mes` (rutas US) **o** AeroDataBox `/airports/{code}/delays` (rutas internacionales) | Campo real: `delayIndex` |
| `tarifas_vuelo` — `clase_cabina`, `precio_final` | 🟢 Google Flights con `travel_class` | Misma rotación de arriba |
| `tarifas_vuelo` — `cupos_disponibles` | ⚪ regla de negocio | Config en `configuracion_sistema.disponibilidad_tarifas_vuelo` |
| `asientos_vuelo` | ⚪ regla de negocio | Generado junto con el vuelo, distribución según `avion_modelo`; recargo en `configuracion_sistema.disponibilidad_asientos` |
| `predicciones_precio_ruta` | 🟢 Google Flights `price_insights` | Mismo llamado que da `precio_base` |

## Hoteles
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `hoteles_catalogo`, `hoteles_tarifas`, `hoteles_resenas` | 🟢 **HotelLens** | Flujo: Google Hotels search → `/prices` (extraer `hotel_id` de Booking.com del `booking_url`) → `/booking/hotels/details` (fuente real de ciudad limpia + `room_offers[]` + `rooms_left` real). **Límite duro 100 req/mes + 10 req/min** — ver "Gestión de cuota real" arriba |
| `cargos_locales_destino` | ⚪ CSV manual (Holidu, `fuentes_extra/`) | No es una API, importación única |

## Autos
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `autos_catalogo` | 🟢 **Global Rental Cars** | Expedia es el flujo limpio (auto-complete→search→details); Priceline/Booking sirven pero ignoran fecha/ubicación pedida, revalidar antes de cobrar; Kiwi descartado. **Límite duro 100 req/mes** (no "sin cuota" como se pensó al probarla, ver "Gestión de cuota real" arriba) |

## Actividades
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `actividades_catalogo`, `actividades_resenas` | 🟢 **Travel Advisor** | `attraction-products/v2/list` (búsqueda) + `attractions/get-details` legacy (detalle + reseñas embebidas — NO el `v2/get-details`, roto). **Límite duro 500 req/mes + 5 req/seg** — ver "Gestión de cuota real" arriba |
| `actividades_horarios` | ⚪ regla de negocio | **Sin fuente real, gap confirmado** (`check-availability` roto) — config en `configuracion_sistema.disponibilidad_actividades` |

## Cruceros
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `navieras`, `barcos`, `cruceros_catalogo`, `cruceros_camarotes_tarifa` (precio) | 🟢 **Cruise Pricing API** | 10/11 endpoints funcionales, `price-history` requiere plan PRO (no usado). **Límite duro 100 req/mes + 10 req/min** (corregido, no ~500k como se pensó — ver "Gestión de cuota real" arriba) |
| `cruceros_camarotes_tarifa` — `cupos_disponibles` | ⚪ regla de negocio | **Sin fuente real, gap confirmado** — config en `configuracion_sistema.disponibilidad_cruceros` |

## Paquetes / Proveedores comerciales
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `tipos_paquete_descuento`, `proveedores_comerciales` | ⚫ CRUD (Administrador) | Configuración/negociación manual |

## Reservas / Carrito
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `reservas`, `reserva_items`, `reserva_pasajeros`, `reserva_extras`, `alertas_precio`, `carritos`, `carrito_items` | ⚫ CRUD (Pasajero/Agente) | Acción directa del usuario, sin proceso automático de llenado |
| `requisitos_visa_cache` | 🟡 **Visa Requirement API** (`POST /v2/visa/check`) | Cache bajo demanda, refrescar si `fecha_consulta` es vieja |

## Disrupciones
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `disrupciones` | 🔵 **AviationStack** (estado real, ya implementado) + MinIO `agg_*` (estimador estadístico) + Gmail API (monitor de correo) | 3 fuentes de detección, ya documentadas en `disrupciones-spec.md` |
| `notificaciones` | 🔵 SendGrid / Gmail (envío) | Generado por el sistema al detectar disrupción |

## Facturación
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `metodos_pago`, `pagos`, `comisiones`, `remesas`, `remesa_comisiones`, `reembolsos`, `facturas` | 🔵 **Stripe** (pagos/reembolsos) + ⚫ generado por el sistema | Ya documentado en `facturacion-spec.md` |
| `tasas_cambio` | 🟢 **ExchangeRate-API** | 1×/día |

## Cuenta / Mis Viajes
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `favoritos`, `busquedas_recientes`, `viajes_personalizados`, `programa_beneficios_niveles`, `programa_beneficios_movimientos` | ⚫ CRUD (Pasajero/Administrador) | Sin fuente externa |

## Centro de Ayuda
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `articulos_ayuda`, `articulo_calificaciones` | ⚫ CRUD (Administrador/Pasajero) | Sin fuente externa |
| `casos_escalados` | 🔵 **Gmail API** | Constante, un hilo real por caso |

## Ofertas y Promociones
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `ofertas_destacadas`, `cupones_descuento`, `cupones_uso`, `newsletter_suscripciones` | ⚫ CRUD (Administrador) | Sin fuente externa |
| `campanas_email` | 🔵 **SendGrid** | Constante, envío real |

## Asistente IA
| Tabla(s) | Fuente/Proceso | Notas |
|---|---|---|
| `conversaciones_ia`, `mensajes_ia` | 🔵 **Groq / Gemini** | Constante, generación de respuesta en vivo |

## Archivos (todos los file fields)
| Campo | Backend confirmado |
|---|---|
| `usuarios.foto_perfil`, `documentos_viaje.archivo`, `facturas.archivo_pdf`, `reservas.voucher_pdf`, `barcos.planos_cubierta` | **Opción B confirmada**: backend S3 de PocketBase apuntando a `minio-travel` (bucket nuevo, ej. `aerotrack-travel-files`) — pendiente de activar al implementar, hoy PocketBase usa disco local por defecto |

---

## Pendiente / en pausa (no bloquea empezar a implementar lo demás)
- **AeroDataBox** ya reactivada y en uso (Flight API + Statistical), pero cuidar la rotación de 3 hubs/día.
- **Travel Advisor** (Actividades) queda como "un veremos" por inestabilidad — si aparece una alternativa mejor para disponibilidad real, reemplaza solo `actividades_horarios`, el resto del módulo no cambia.
- Ver `docs/apis-reference.md` para el detalle crudo de cada API si hace falta reconfirmar algo antes de programar su sync job.
