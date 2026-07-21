# Referencia de APIs (RapidAPI) — Proyecto Agencia de Viajes

> Nota: la X-RapidAPI-Key es UNA SOLA para todas las APIs de tu cuenta RapidAPI.
> Va siempre como header `x-rapidapi-key`. NO la subas a git, ponla en tu .env.
> Cada API además necesita su propio `x-rapidapi-host` (distinto por API).
> AviationStack para monitoreo activo de reservas (disrupciones), AeroDataBox para datos estáticos de aeropuertos y horarios base. 
> Búsqueda → Kiwi.com (resultados, precios, disponibilidad)
> Reserva   → Duffel   (crear la orden, emitir "ticket" en sandbox)

---

## 1. Travelpayouts — Flight Data (🔴 CAÍDA del lado del proveedor — verificado 2026-07-15)
Precios de vuelos, tendencias y destinos populares.

- Host: `travelpayouts-travelpayouts-flight-data-v1.p.rapidapi.com`
- Requiere ADEMÁS un `X-Access-Token` propio de Travelpayouts (afiliado, gratis, se obtiene en tu perfil de app.travelpayouts.com)
- ⚠️ **Estado verificado 2026-07-15:** los 18 endpoints de abajo devuelven 404 de texto plano ("404 page not found", servido por CloudFront) en vez del JSON de RapidAPI. Se comparó contra una ruta inexistente al azar, que sí devuelve el 404 propio de RapidAPI — eso confirma que la key/suscripción es válida y RapidAPI reconoce estas rutas y las reenvía, pero el backend de origen de Travelpayouts detrás de este wrapper está caído (responde 404 a todo). No es arreglable desde el código del proyecto; hay que reportarlo al creador en RapidAPI o monitorear si vuelve. **Reemplazada por [Skyscanner Flights & Travel API](#15-skyscanner-flights--travel-api--confirmada-2026-07-15--reemplazo-de-kiwi-y-travelpayouts)** para precios/calendario (`/flights/getPriceCalendar`, `/config/getExchangeRates`), confirmada funcionando.

Flight Data API v1:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/v1/prices/direct/` | Vuelos directos más baratos |
| GET | `/v1/city-directions` | Destinos populares desde una ciudad |
| GET | `/v1/airline-directions` | Rutas populares de una aerolínea |
| GET | `/v1/prices/calendar` | Tickets para cada día del mes |
| GET | `/v1/prices/cheap` | Tickets más baratos por ruta |
| GET | `/v1/prices/monthly` | Tickets baratos agrupados por mes |

Flight Data API v2:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/v2/prices/nearest-places-matrix` | Precios de direcciones alternativas |
| GET | `/v2/prices/month-matrix` | Calendario de precios por mes |
| GET | `/v2/prices/special-offers` | Ofertas especiales |
| GET | `/v2/prices/latest` | Precios encontrados últimas 48h |
| GET | `/v2/prices/week-matrix` | Calendario de precios por semana |

Flight Data API json files (archivos estáticos, sin parámetros):
| Método | Ruta | Uso |
|---|---|---|
| GET | `/data/en-GB/airlines.json` | Datos de aerolíneas |
| GET | `/data/planes.json` | Datos de aviones |
| GET | `/data/en-GB/cities.json` | Datos de ciudades |
| GET | `/data/airlines_alliances.json` | Datos de alianzas de aerolíneas |
| GET | `/data/en-GB/airports.json` | Datos de aeropuertos |
| GET | `/data/en-GB/countries.json` | Datos de países |
| GET | `/data/routes.json` | Datos de rutas |

---

## 2. AeroDataBox (✅ OFICIAL — cobertura amplia confirmada 2026-07-15, ✅ REACTIVADA 2026-07-17)
Estatus de vuelos, horarios, datos de aeropuertos/aerolíneas/aeronaves en tiempo real, retrasos y suscripciones de alertas por webhook.

- Host: `aerodatabox.p.rapidapi.com`
- ⚠️ Tiene alerta oficial de scam: verifica que uses este host exacto.
- 🟡→✅ **Historial de la caída 2026-07-16**: el listado fue deshabilitado a nivel de RapidAPI (`405`, "provider has disabled request access") — según confirmó el proveedor por correo, fue un incidente de RapidAPI que afectó a varios suscriptores, no algo específico de esta cuenta. **Reactivada y reconfirmada con datos reales 2026-07-17** (`/airports/iata/ATL`, `/flights/airports/...`, `/airports/.../delays`, `/airports/.../stats/routes/daily` — los 4 con 200 y datos reales).
- ⚠️ **Plan Free: 600 unidades/mes** (520 restantes al reactivarse, 504 tras las pruebas de reconfirmación). Costo real por tipo de endpoint: lookups simples (aircraft/airport por código) ≈1-2 unidades; **FIDS (`/flights/airports/...`) ≈2 unidades**; **Statistical API (`/delays`, `/stats/routes/daily`) y flota por aerolínea ≈6 unidades cada uno (caro)**; Healthcheck y Subscriptions son gratis (0 unidades). **Ojo: incluso una llamada que da 400 por parámetro inválido consume cuota** (confirmado: un rango de fecha fuera de límite consumió 2 unidades igual que una exitosa) — no asumir que un error siempre es gratis. El header a vigilar es `X-RateLimit-API-Units-Remaining`.
- 🔴 **CORRECCIÓN IMPORTANTE 2026-07-17 sobre rangos de fecha en FIDS**: `GET /flights/airports/{codeType}/{code}/{fromLocal}/{toLocal}` **tiene un límite duro de 12 horas por llamada** — confirmado en vivo: pedir un rango de 24h da `400 "period of time... must not be more than 12 hours in duration"`. La nota anterior de este doc (y del DBML) que decía "hasta 7-30 días según plan" **era una confusión con la OTRA familia de endpoints** (`/flights/{searchBy}/{searchParam}/{dateFromLocal}/{dateToLocal}`, historial por vuelo/aeronave específica, no por aeropuerto) — no aplica a FIDS. Corregido en `docs/aerotrack-travel-propuesta-tablas-v3.dbml`.
- 💡 **FIDS es muy eficiente pese al límite de 12h**: una sola llamada a `/flights/airports/iata/ATL/{12h futuras}` devolvió **781 salidas reales**, de las cuales **141 iban hacia 14 de los otros 15 aeropuertos hub del catálogo** (prácticamente todas las rutas que tocan ATL, con ~10 vuelos reales por ruta en promedio) — mucho más eficiente que consultar por ruta específica (1 llamada = 1 ruta) como hace Google Flights. Trae `number` (ej. "DL 466", con espacio — normalizar), `aircraft.model` (ej. "Boeing 757"), `airline.iata`/`name`, horario real UTC+local, `status`. SÍ acepta fechas futuras sin la restricción que tiene AviationStack (confirmado con 5 días adelante, 200 OK).
- 💡 `/airports/{code}/delays` da `departuresDelayInformation`/`arrivalsDelayInformation`, cada uno con `numTotal`, `numQualifiedTotal`, `numCancelled`, `medianDelay`, `delayIndex` (ej. 4.42) — el campo real para construir `risk_score`. `/stats/routes/daily` da `routes[].{destination, averageDailyFlights, operators[]}` — contexto de frecuencia/competencia por ruta, no un índice de riesgo directo.
- 💡 La spec OpenAPI completa del proveedor (`https://doc.aerodatabox.com/docs/openapi-rapidapi-v1.json`) es gratis de consultar (no gasta cuota) y trae los valores exactos de enums (`searchBy`, `codeType`, etc.) — consultarla antes de adivinar parámetros por prueba y error.

### Aircraft API — ✅ todos probados con datos reales
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/aircrafts/{searchBy}/{searchParam}` | Aeronave por matrícula/Mode-S/ID | ✅ `searchBy`: `Reg`, `Icao24`, `Id` |
| GET | `/aircrafts/{searchBy}/{searchParam}/registrations` | Historial de registro | ✅ |
| GET | `/aircrafts/{searchBy}/{searchParam}/all` | Todos los datos de la aeronave | ✅ |
| GET | `/airlines/{airlineCode}/aircrafts` | Flota por aerolínea | ✅ requiere `pageSize`+`pageOffset` (no `limit` — da 400 "pageSize field is required" si falta) |
| GET | `/aircrafts/reg/{reg}/image/beta` | Imagen por matrícula | ✅ (204 si no hay imagen para esa matrícula, es normal) |
| GET | `/aircrafts/search/term?q=&limit=` | Búsqueda de matrículas por término | ✅ |

### Airport API — ✅ todos probados
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/airports/{codeType}/{code}` | Aeropuerto por código | ✅ `codeType`: `Icao` o `Iata` |
| GET | `/airports/{codeType}/{code}/runways` | Pistas del aeropuerto | ✅ |
| GET | `/airports/search/location?lat=&lon=&radiusKm=&limit=` | Búsqueda por ubicación | ✅ `radiusKm` y `limit` son obligatorios (no opcionales pese al nombre) |
| GET | `/airports/search/ip?q=&radiusKm=&limit=` | Búsqueda por IP | ✅ pero **`q` debe ser una IP explícita** — no detecta la IP del caller automáticamente pese al nombre. `radiusKm`/`limit` también obligatorios. |
| GET | `/airports/search/term?q=&limit=` | Búsqueda por texto libre | ✅ |

### Flight Alert API — ✅ probado y limpiado (se creó y borró un webhook de prueba)
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| POST | `/subscriptions/webhook/{subjectType}/{subjectId}` | Crear suscripción webhook | ✅ **`subjectType` solo acepta `FlightByNumber` o `FlightByAirportIcao`** (no "Aircraft"/"Airport" como podría suponerse). Body: `{"url": "..."}` (`maxDeliveryRetries` opcional). |
| GET | `/subscriptions/webhook/{subscriptionId}` | Obtener suscripción | ✅ |
| DELETE | `/subscriptions/webhook/{subscriptionId}` | Eliminar suscripción | ✅ |
| GET | `/subscriptions/webhook` | Listar suscripciones | ✅ (204 si no hay ninguna) |
| GET | `/subscriptions/balance` | Saldo de suscripción | ✅ (cuerpo vacío — cuenta sin balance de alertas configurado aún) |
| POST | `/subscriptions/balance/refill` | Recargar saldo | ⏭️ **no probado a propósito** — podría afectar el balance/facturación real de la cuenta. Solo documentado. |
- 💡 Toda esta familia es **gratis (0 unidades de cuota)**.

### Flight API
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/flights/{searchBy}/{searchParam}` | Estado de vuelo (día actual) | ✅ `searchBy`: `Number`, `Reg`, `CallSign`, `Icao24` |
| GET | `/flights/{searchBy}/{searchParam}/{dateLocal}` | Estado de vuelo (fecha específica) | 🟡 no probado individualmente — misma familia/auth que el de arriba |
| GET | `/flights/{searchBy}/{searchParam}/{dateFromLocal}/{dateToLocal}` | Historial/horario (rango de fechas) | 🟡 no probado individualmente |
| GET | `/flights/{searchBy}/{searchParam}/dates` | Fechas de salida | 🟡 no probado individualmente |
| GET | `/flights/{searchBy}/{searchParam}/dates/{fromLocal}/{toLocal}` | Fechas de salida (rango) | 🟡 no probado individualmente |
| GET | `/flights/airports/{codeType}/{code}/{fromLocal}/{toLocal}` | FIDS: salidas/llegadas (rango horario) | ✅ probado con JFK, dio el vuelo real DL288/N833MH usado para encadenar el resto de las pruebas de esta sesión |
| GET | `/flights/airports/{codeType}/{code}` | FIDS: salidas/llegadas (tiempo relativo) | 🟡 no probado individualmente — hermano del anterior, misma familia |
| GET | `/flights/search/term?q=&limit=` | Búsqueda de números de vuelo | ✅ |

### Healthcheck API — ✅ todos probados (gratis, 0 unidades)
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/health/services/feeds/{service}` | Estado del feed | ✅ `service`: `FlightSchedules`, `FlightLiveUpdates`, `AdsbUpdates` |
| GET | `/health/services/airports/{icao}/feeds` | Estado por aeropuerto | ✅ usar ICAO de 4 letras, no IATA |
| GET | `/health/services/feeds/{service}/airports` | Aeropuertos que soportan el feed | ✅ (1476 ICAOs para `FlightLiveUpdates`) |

### Industry API
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/industry/faa-ladd/{id}/status` | Estado FAA LADD | ✅ `id` = matrícula |

### Miscellaneous API
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/airports/{codeType}/{code}/time/local` | Hora local del aeropuerto | ✅ |
| GET | `/airports/{codeType}/{code}/time/solar` | Hora solar (actual) | 🔴 **404 a nivel de gateway de RapidAPI** ("Endpoint does not exist") — la ruta existe en la spec propia de AeroDataBox pero **no está publicada en el producto de RapidAPI**. No consume cuota (se rechaza antes de llegar al backend). |
| GET | `/airports/{codeType}/{code}/time/solar/{dateLocal}` | Hora solar (fecha específica) | 🔴 presumido igual de no-disponible (misma familia no publicada) — no probado individualmente |
| GET | `/airports/{codeType}/{codeFrom}/distance-time/{codeTo}` | Distancia y tiempo entre aeropuertos | ✅ |

### Statistical API — ✅ variantes base probadas (caro: ~6 unidades cada uno)
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/airports/{codeType}/{code}/delays` | Retrasos del aeropuerto (actual) | ✅ |
| GET | `/airports/{codeType}/{code}/delays/{dateLocal}` | Retrasos (fecha específica) | 🟡 no probado individualmente — variante de fecha, misma familia |
| GET | `/airports/{codeType}/{code}/delays/{dateFromLocal}/{dateToLocal}` | Retrasos (rango de fechas) | 🟡 no probado individualmente |
| GET | `/airports/{codeType}/{code}/stats/routes/daily` | Rutas y estadísticas diarias (actual) | ✅ |
| GET | `/airports/{codeType}/{code}/stats/routes/daily/{dateLocal}` | Rutas y estadísticas (fecha) | 🟡 no probado individualmente |
| GET | `/airports/delays` | Retrasos globales (actual) | ✅ (respuesta de ~519KB, todos los aeropuertos) |
| GET | `/airports/delays/{dateUtc}` | Retrasos globales (fecha) | 🟡 no probado individualmente |
| GET | `/flights/{number}/delays` | Estadísticas de retraso por vuelo | ✅ |

**Enums confirmados (útiles para no adivinar por prueba y error):**
- Aircraft `searchBy`: `Id`, `Reg`, `Icao24`
- Flight `searchBy`: `Number`, `Reg`, `CallSign`, `Icao24`
- Airport `codeType`: `Icao`, `Iata`
- Webhook `subjectType`: `FlightByNumber`, `FlightByAirportIcao` (únicos dos valores válidos)
- Healthcheck `service`: `FlightSchedules`, `FlightLiveUpdates`, `AdsbUpdates`

---

## 3. Kiwi.com Cheap Flights (🔴 CAÍDA — deployment deshabilitado, verificado 2026-07-15)
Buscador de vuelos tipo Skyscanner/Kiwi.

- Host: `kiwi-com-cheap-flights.p.rapidapi.com`
- ⚠️ **Estado verificado 2026-07-15 (dos veces, incluso con suscripción activa):** ambos endpoints devuelven `402 Payment Required` con cuerpo `DEPLOYMENT_DISABLED` — es el deployment del creador (probablemente en Vercel/Fly) el que está apagado, no depende de tu key/suscripción. **Reemplazada por [Skyscanner Flights & Travel API](#15-skyscanner-flights--travel-api--confirmada-2026-07-15--reemplazo-de-kiwi-y-travelpayouts)** (`/flights/searchFlights`), confirmada funcionando con datos reales.

Endpoints:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/round-trip` | Búsqueda ida y vuelta |
| GET | `/one-way` | Búsqueda solo ida |

---

## 4. FlightDelay Intelligence API (🔴 descartada — deshabilitada por el proveedor, confirmado 2026-07-16)
Predicción de retrasos con IA (no es dato oficial de aerolíneas/aeropuertos).

- Host: `flightdelay-intelligence-api1.p.rapidapi.com`
- 2026-07-15: `GET /health` → `404 "Application not found"`.
- 🔴 **Reconfirmado 2026-07-16**: `GET /health` ahora da `405` con `{"message":"The API provider has disabled request access to the API. Please contact API Provider."}` — el mismo mensaje que empezó a dar AeroDataBox (sección 2) y TripAdvisor `searchLocation` (sección 6) ese mismo día. Esta ya no es candidata viable, descartar.
- **Candidata de reemplazo evaluada: Aviation Data (API Burst)**, host `aviation-data1.p.rapidapi.com` (42 endpoints listados por el proveedor, pero son nombres de función, no rutas reales — el patrón real es REST con parámetros en la URL, ej. `/airports/iata/{code}`).
  - ✅ **Datos estáticos siguen funcionando 2026-07-16** (reconfirmado): `/airports/iata/JFK` → 200 real, `/airports/{iata}/runways` → 200 real.
  - 🔴 **Los endpoints de retrasos SIGUEN caídos, reconfirmado 2026-07-16 (dos sesiones distintas, no un blip de un solo día):** `/airports/{iata}/delays` y `/flights/{flight}/delays` dan `503 SERVICE_UNAVAILABLE "This endpoint is temporarily unavailable"` de forma consistente. Ya no se puede tratar como "temporal" — es un patrón persistente del lado del proveedor. **No es un reemplazo viable para datos de retrasos/estadísticas** — solo sirve como fuente estática complementaria de aeropuertos/pistas, que ya cubren AeroDataBox y `dim_aeropuerto` (MinIO).

Endpoints:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/predict-delay` | Predicción general de retraso |
| GET | `/predict-flight-specific` | Predicción por vuelo específico |
| GET | `/analyze-route` | Análisis de ruta |
| GET | `/airports` | Catálogo de aeropuertos soportados |
| GET | `/airlines` | Catálogo de aerolíneas soportadas |
| GET | `/health` | Health check |
| GET | `/models` | Info de los modelos ML usados |

---

## 5. HotelLens (⚠️ NO oficial — scraper, creador: Crawlio) — cobertura completa confirmada 2026-07-15
Agrega Google Hotels + Booking.com + Agoda en una sola API.

- Host: `hotellens.p.rapidapi.com`
- ⚠️ **Plan BASIC: rate limit estricto por minuto** — dio `429 "exceeded the rate limit per minute"` tras ~4-5 llamadas rápidas seguidas, se recupera en ~60s. Espaciar/backoff al integrar, no disparar lookups de detalle en paralelo.
- Los 15 endpoints son GET, autenticación estándar RapidAPI (misma key/host también para los rotos — los 502 no son de auth).

### Meta
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/health` | Health check | ✅ sin params |

### Google Hotels — ✅ único proveedor con búsqueda propia funcional
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/api/v1/hotels` | Buscar hoteles | ⚠️ requiere **`location=`** (ej. `location=Paris`). **`query=`/`q=`/`destination=` se ignoran silenciosamente** — siempre cae al listado hardcodeado de Nueva York sin importar el valor (falso positivo en versión anterior de este doc, coincidía con el default). |
| GET | `/api/v1/hotels/details` | Detalle de hotel | ✅ requiere `url=` (la URL de entidad de Google del resultado de búsqueda, `https://www.google.com/travel/hotels/entity/{id}`) |
| GET | `/api/v1/hotels/reviews` | Reseñas | ✅ mismo `url=`. `entity_id=`/`id=`/`hotel_id=`/`property_token=` se ignoran (caen a un hotel default). |
| GET | `/api/v1/hotels/reviews/complete` | Reseñas completas (multi-fuente) | ✅ mismo `url=`, payload mucho más grande (~320KB vs ~3.5KB de `/reviews`) |
| GET | `/api/v1/hotels/about` | Info general | ✅ mismo `url=` |
| GET | `/api/v1/hotels/location` | Ubicación / POIs cercanos | ✅ mismo `url=` |
| GET | `/api/v1/hotels/prices` | Comparador de precios | ⚠️ mismo `url=`, ofertas reales multi-proveedor (Agoda, Booking, Expedia, Priceline, Super.com, Trip.com, eDreams con `booking_url` reales) pero **`check_in=`/`check_out=` se ignoran** — siempre devuelve una estadía fija de 1 noche por defecto |

Flujo: `GET /api/v1/hotels?location={ciudad}` → tomar `url` de un resultado → usarla en `/details`, `/about`, `/location`, `/reviews`, `/reviews/complete`, `/prices`.

### Booking.com — 🔴 búsqueda propia caída del lado del proveedor
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/api/v1/booking/hotels` | Buscar en Booking.com | 🔴 `502 "The API is unreachable... API (not working)"` con cualquier parámetro — outage confirmado del backend, no es tema de parámetros |
| GET | `/api/v1/booking/hotels/details` | Detalle (Booking.com) | ✅ requiere `hotel_id=` (numérico) + `check_in=YYYY-MM-DD` + `check_out=YYYY-MM-DD` (**con guion bajo** — `checkin`/`checkout` sin guion dan 400 genérico) |
| GET | `/api/v1/booking/hotels/reviews` | Reseñas (Booking.com) | ✅ mismos params, reseñas reales paginadas (`offset`/`limit`/`sort_by`) |

**Workaround para `hotel_id`** (búsqueda caída): sacar la oferta de Booking.com embebida en una respuesta de `/api/v1/hotels/prices` (Google Hotels) y parsear el id numérico de su `booking_url` (`dest_id`/`highlighted_hotels`).

### Agoda — 🔴 búsqueda propia caída del lado del proveedor
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/api/v1/agoda/destinations` | Resolver destino (Agoda) | ✅ requiere `query=` (este sí usa `query`, a diferencia de Google Hotels) — devuelve `id` (city_id), `type_name`, `property_count` |
| GET | `/api/v1/agoda/hotels` | Buscar en Agoda | 🔴 mismo `502` de outage, probado con `city_id` real de `/destinations`, `location=`, y sin params — siempre falla igual |
| GET | `/api/v1/agoda/hotels/details` | Detalle (Agoda) | ✅ requiere `hotel_id=` + `check_in=` + `check_out=` |
| GET | `/api/v1/agoda/hotels/reviews` | Reseñas (Agoda) | ✅ requiere solo `hotel_id=` (funciona sin fechas) |

**Workaround para `hotel_id`**: mismo truco — parsear el `hid=` de la oferta de Agoda dentro de una respuesta de `/api/v1/hotels/prices` (Google Hotels). El `city_id` de `/agoda/destinations` es real pero no sirve para llegar a un hotel porque `/agoda/hotels` (la búsqueda que lo consume) está caída.

---

## 6. TripAdvisor API (⚠️ NO oficial — proveedor "tripadvisor16")
Reseñas, fotos, calificaciones de hoteles/restaurantes/atracciones.

- Host real (el que usa el `.env`, `TRIPADVISOR_API_HOST`): `tripadvisor16.p.rapidapi.com`
- 💡 Existe una alternativa 100% oficial en RapidAPI llamada **"TripAdvisor Gateway API"** (usa el Partner API real de TripAdvisor, "zero scraping") si prefieres algo sin riesgo de ToS — no la evalué a fondo, pero vale la pena revisarla si esto va a producción.
- 🔴 **Regresión confirmada 2026-07-16**: `GET /api/v1/hotels/searchLocation` (el resolver de `geoId`, paso 1 del flujo de abajo) ahora responde `{"status":false,"message":"The API provider has disabled request access to the API. Please contact API Provider."}` — dejó de funcionar desde que se confirmó el 2026-07-15. **`searchHotels` (paso 2) sigue funcionando** si se le pasa un `geoId` obtenido por otra vía (ej. Travel Advisor usa el mismo esquema de `geoId` de TripAdvisor — probado: `geoId=187147` para Paris funciona en ambos hosts).
- ⚠️ **Forma de respuesta:** tanto `searchHotels` de este host como `hotels/v2/list` de Travel Advisor (sección 18) devuelven la misma estructura GraphQL anidada de "tarjetas de presentación" (`__typename`, `cardPhotos`, `commerceInfo.priceForDisplay`, `bubbleRating`) — probablemente ambos wrappers scrapean el mismo backend de tripadvisor.com. Es notablemente más costoso de parsear que el JSON plano de HotelLens (sección 5): hay que descender 3-4 niveles (`sections[].listSingleCardContent.commerceInfo.priceForDisplay`) para sacar un precio, en vez de leer `hotel.price` directo.

**Flujo verificado 2026-07-15, con el paso 1 roto desde 2026-07-16 (ver arriba):**
1. ~~`GET /api/v1/hotels/searchLocation?query={ciudad}` → devuelve una lista con `geoId`~~ (deshabilitado por el proveedor 2026-07-16) — usar `POST locations/v2/auto-complete` de Travel Advisor (sección 18) para resolver el `geoId` en su lugar.
2. `GET /api/v1/hotels/searchHotels?geoId={geoId}&checkIn=YYYY-MM-DD&checkOut=YYYY-MM-DD` → ✅ **re-confirmado 2026-07-16**, resultados reales (Le Bristol Paris, `bubbleRating`, `priceForDisplay: "$2,188"`, fotos). `checkIn` no puede ser fecha pasada.

**Restaurantes (🔴 roto del lado del proveedor):**
`GET /api/v1/restaurant/searchLocation?query={ciudad}` responde siempre `{"status":false,"message":"Something went wrong..."}` sin importar la ciudad — probado con Paris y London. Es un bug del módulo, no de parámetros (el módulo de hoteles con la misma key/host sí funciona). Sin ese resolver no se puede conseguir el `locationId` que pide `/api/v1/restaurant/searchRestaurants`.

**Atracciones:** no se encontró endpoint de resolución de ubicación — `/api/v1/attraction/searchLocation` y variantes en plural devuelven 404 "Endpoint does not exist" (no registrado en este host).

Otros endpoints confirmados que existen en este host (mismo patrón `/api/v1/{categoria}/...`): revisar el playground de RapidAPI para el resto (detalle de hotel, reviews, fotos, Q&A) antes de integrarlos, ya que el esquema de parámetros difiere del que tenía documentado antes esta sección (no es `locationId` simple sino `geoId` + fechas para hoteles).

---
## 7. Borrado 

## 8. Global Rental Cars (⚠️ NO oficial — "research/informational purposes") — 26 endpoints, cobertura completa confirmada 2026-07-15
Agrega Priceline, Booking, Expedia y Kiwi para autos de renta.

- Host: `global-rental-cars.p.rapidapi.com`
- ⚠️ **Prefijos distintos por proveedor** (confirmado por prueba): `priceline`, `expedia`, `kiwi` usan `/1.0/...`; `booking` usa `/booking` (idiomas/moneda) y `/booking-app` (autos) — **no** `/1.0` (`GET /1.0/booking/languages` → 404, `GET /booking/languages` → 200).
- No se encontraron errores 429/402 de cuota en las 26 pruebas.

### Priceline (pricetrail) — 4/6 funcionales
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/1.0/pricetrail/cars/auto-complete?query=` | Autocompletar ubicación | ✅ devuelve AIRPORT/CITY/POI/HOTEL/PARTNER_LOC con `id` estilo IATA (ej. `CDG`) |
| GET | `/1.0/pricetrail/cars/search?pickUpLocation=&dropOffLocation=` | Buscar autos | ⚠️ ubicación respetada correctamente, pero **`pickUpDate`/`dropOffDate` se ignoran** — siempre resuelve a un alquiler fijo "mañana, 2 días" sin importar las fechas enviadas. Inventario real (~670KB). |
| GET | `/1.0/pricetrail/cars/details?key=` | Detalle de auto | ✅ `key` = `detailsKey` de `search` (`data.vehicles[].rate[].detailsKey`, token largo separado por `~`) |
| GET | `/1.0/pricetrail/cars/top-airports` | Top aeropuertos | 🔴 siempre `403 "NO DATA!"` sin importar params — outage/bloqueo real, no tema de parámetros |
| GET | `/1.0/pricetrail/cars/partners` | Partners | 🔴 mismo `403 "NO DATA!"` |
| GET | `/1.0/pricetrail/cars/nearbyAirPorts?latitude=&longitude=` | Aeropuertos cercanos | ✅ requiere `latitude`/`longitude` (no `lat`/`lon` — da 400 "latitude is required!") |

Flujo: `auto-complete?query=Paris` → id `CDG` → `search?pickUpLocation=CDG&dropOffLocation=CDG` → `rate[].detailsKey` → `details?key=...`

### Booking — 8/11 funcionales
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/booking/languages` | Idiomas | ✅ sin params, 45 idiomas |
| GET | `/booking/currency` | Monedas | ✅ sin params, 40 monedas |
| GET | `/booking-app/car/autocomplete?query=` | Autocompletar | ✅ devuelve `pickUpId` (blob base64 de lat/lon) |
| GET | `/booking-app/car/search-by-location?pickUpLocation=` | Buscar por ubicación | 🔴 `500 Internal Server Error` con cualquier valor probado (`pickUpId` de autocomplete, IATA plano, `"lat,lon"`) |
| GET | `/booking-app/car/search` | Buscar autos | ⚠️ requiere **snake_case**: `pick_up_latitude`, `pick_up_longitude`, `drop_off_latitude`, `drop_off_longitude`, `pick_up_date`, `drop_off_date`, `pick_up_time`, `drop_off_time`. Inventario real (~1.4MB, 339 vehículos) **pero el lat/lon se ignora** — probado con coords de CDG vs Tokio, respuesta idéntica (`search_key` decodificado siempre `pickUpLocation: "EWR"`, Newark). Las fechas sí se respetan. |
| GET | `/booking-app/car/search-by-id?pickUpId=` | Buscar por ID | 🔴 `500 Internal Server Error` con cualquier combinación probada |
| GET | `/booking-app/car/detail?vehicle_id=&search_key=` | Detalle | ✅ `vehicle_id` = `vehicle_info.v_id` de `search`, `search_key` = blob base64 de `search` |
| GET | `/booking-app/car/detail/packages` | Paquetes/seguros | ✅ mismos params |
| GET | `/booking-app/car/detail/supplier/details` | Detalle de proveedor | ✅ mismos params |
| GET | `/booking-app/car/detail/supplier/location` | Ubicación del proveedor | ✅ mismos params |
| GET | `/booking-app/car/detail/supplier/reviews` | Reseñas del proveedor | ✅ mismos params |

**Único camino funcional a la familia `detail`**: `car/autocomplete` → `car/search` (snake_case, ignora coords, siempre EWR) → `vehicle_info.v_id` + `search_key` → `car/detail*`. `search-by-location` y `search-by-id` son caminos muertos (500).

### Expedia — 5/5 funcionales
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/1.0/expedia/configs` | Configuración | ✅ sin params, 39 configs de sitio/locale/moneda |
| GET | `/1.0/expedia/rigions` | Regiones | ✅ **el "typo" es real en la ruta del proveedor** — `/1.0/expedia/regions` (bien escrito) da 404; solo `rigions` funciona |
| GET | `/1.0/expedia/cars/auto-complete?query=` | Autocompletar | ✅ devuelve `gaiaId` y `hierarchyInfo.airport.airportCode` (ej. `CDG`) |
| GET | `/1.0/expedia/cars/search?pickUpLocation=` | Buscar autos | ✅ **`pickUpLocation` debe ser el código IATA plano** (ej. `CDG`), no el `gaiaId` de autocomplete (ese da 400 "NO DATA!"). Inventario real (~240KB), `data[].carOfferToken` por oferta. |
| GET | `/1.0/expedia/cars/details?carOfferToken=` | Detalle | ✅ token de `search` |

Flujo: `cars/auto-complete?query=Paris` → código IATA `CDG` → `cars/search?pickUpLocation=CDG` → `carOfferToken` → `cars/details?carOfferToken=...`

### Kiwi — 0/4 funcionales, familia completa caída
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/1.0/kiwi/cars/auto-complete?query=` | Autocompletar | 🔴 param correcto es `query`, pero cualquier valor da `405 Method Not Allowed` disfrazado de `{"message":"NO DATA!"}` |
| GET | `/1.0/kiwi/cars/search?pickUpLocation=` | Buscar autos | 🔴 param correcto es `pickUpLocation`, pero cualquier combinación da `500 Internal Server Error` (página cruda de Spring Boot) |
| GET | `/1.0/kiwi/cars/details?id=&searchKey=` | Detalle de auto | 🔴 inalcanzable — nunca hay un `searchKey` real porque `search` nunca funciona |
| GET | `/1.0/kiwi/cars/price-breakdown?id=&searchKey=` | Desglose de precio (Kiwi) | 🔴 inalcanzable, mismo motivo |

No hay camino funcional para Kiwi en esta API — integración caída del lado del proveedor.

---

## 9. Viator API (🔴 sin confirmar — reemplazada por Travel Advisor, sección 18)
- Host: `viator-api.p.rapidapi.com`
- ⚠️ **Estado verificado 2026-07-15 (con suscripción ya activa):** la key funciona (ya no da 403), pero probé 3 URLs reales de Viator distintas (dos de tour, una de destino) en ambos endpoints y siempre devuelve `200 {"messageCode":"OK","message":"Please check your request, verify the input..."}` sin datos — nunca devolvió un resultado real. Puede que el scraper esté desactualizado respecto al formato actual de URLs de viator.com. **Reemplazada por [Travel Advisor](#18-travel-advisor--api-dojo--confirmada-2026-07-15--reemplazo-de-viator), endpoint `attraction-products/v2/list`**, que sí trae tours reales bookeables.

Endpoints:
| Método | Ruta | Uso |
|---|---|---|
| POST | `/tour/listing-by-url` | Listado de tours desde URL de atracción |
| POST | `/tour/get-by-url` | Detalle completo de un tour desde su URL |

---

## 10. ExchangeRate-API (✅ confirmada 2026-07-15)
Tipo de cambio, 160 monedas.

- Host correcto: `exchange-rate-api1.p.rapidapi.com` (con guiones — el host anterior `exchangerate-api1` sin guiones NO existe, daba 403 "not subscribed" por host equivocado).
- ⚠️ El `.env` no tiene un var de host para esta API todavía — falta agregar algo como `EXCHANGE_RATE_RAPIDAPI_HOST=exchange-rate-api1.p.rapidapi.com`. La var `EXCHANGE_RATE_API_KEY` existente es de otro servicio (v6.exchangerate-api.com directo, sin RapidAPI) y esa key da 403 invalid-key ahí — no se necesita si usas la vía RapidAPI con `RAPIDAPI_KEY`.

Endpoints (los 3 únicos que tiene esta API, confirmados funcionando):
| Método | Ruta | Uso |
|---|---|---|
| GET | `/latest?base={moneda}` | Últimas tasas de cambio |
| GET | `/convert?base={moneda}&target={moneda}` | Convertir entre dos monedas |
| GET | `/codes` | Códigos de moneda soportados |

---

## 11. CountryWise (🔴 CAÍDA/rota — verificado 2026-07-15, reemplazada)
Banderas, ISO, monedas, idiomas, zona horaria.

- Host: `countrywise.p.rapidapi.com`
- ⚠️ **Confirmado que solo existe esta única URL** (no hay otras rutas — probé `/country`, `/countries`, ambas dan 404 "Endpoint does not exist"). El problema: `GET /` sí pasa por RapidAPI correctamente (headers y rate-limit de RapidAPI presentes, key válida) pero el backend de origen (Heroku, `countrywise.dev`) devuelve la página de aterrizaje HTML de marketing, no el catálogo JSON de países que promete la descripción. **Reemplazada por "Countries" (Aptitude Apps, LLC)** — ver sección 16.

Endpoint:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/` | Debería devolver el catálogo de países, pero devuelve HTML de landing page |

---

## 17. Countries — Oliver Marchington (✅ confirmada 2026-07-15 — mejor reemplazo de CountryWise)
Catálogo de países: nombre, capital, continente, área, zona horaria, idiomas, moneda, código telefónico, ISO3, dominio, FIPS, ISO numérico.

- Host: `countries59.p.rapidapi.com` *(falta agregar var al `.env`)*
- Plan Basic gratis: **25 requests/mes, tope 1000 req/hora** — restricción por CANTIDAD de requests, no por endpoint bloqueado (a diferencia de la API de la sección 16). Los 10 endpoints están disponibles, solo hay que cuidar la cuota mensual.
- ⚠️ **Probé solo 2 de los 10 endpoints (`list_countries` y `all`) para no gastar la cuota** — ambos con datos reales. Antes de integrar el resto, probarlos con moderación (cada llamada de prueba cuenta contra los 25/mes).
- ⚠️ **Gotcha de formato:** el campo `"data"` de la respuesta viene como un **string con sintaxis de dict de Python** (comillas simples: `"data": "{'Country Name': 'United States', ...}"`), NO como JSON anidado real. `json.loads()` sobre ese string falla por las comillas simples — hay que usar `ast.literal_eval()` en Python (u otro parser tolerante si se consume desde JS/TS).

Todos los endpoints usan el parámetro `country_code` (excepto `list_countries`):
| Método | Ruta | Uso |
|---|---|---|
| GET | `/list_countries` | Lista de países con su ISO2 (✅ probado) |
| GET | `/all?country_code=US` | Todos los datos del país (✅ probado, dato rico) |
| GET | `/iso3?country_code=USA` | Código ISO3 |
| GET | `/iso2?country_code=US` | Código ISO2 |
| GET | `/time_zone?country_code=US` | Zona horaria |
| GET | `/phone_number?country_code=US` | Código telefónico |
| GET | `/language?country_code=US` | Idioma(s) |
| GET | `/geo?country_code=US` | Datos geográficos |
| GET | `/currency?country_code=US` | Moneda |
| GET | `/capital?country_code=US` | Capital |

---

## 16. Countries — Aptitude Apps, LLC (🟡 confirmada 2026-07-15, PERO solo 1 de 12 endpoints disponible en el plan gratis — ver alternativa mejor en sección 17)
Catálogo de países: nombre, capital, coordenadas, códigos ISO, región/subregión UN, población. Reemplazo de CountryWise.

- Host: `countries33.p.rapidapi.com` *(falta agregar var al `.env`, ej. `COUNTRIES_API_HOST=countries33.p.rapidapi.com`)*
- ⚠️ **Solo `GET /basic` funciona con el plan actual** — devuelve un dump completo de ~250 países (116 KB) con `name`, `state_name`, `capital[]` (con lat/lng y población), `iso_3166` (alpha2/alpha3/numeric/subdivision), `un_geoscheme` (region/subregion), `population` (total/densidad).
- Los otros 11 endpoints (`/all`, `/name/{x}`, `/capital/{x}`, `/region/{x}`, `/subregion/{x}`, `/subsubregion/{x}`, `/alpha2/{x}`, `/alpha3/{x}`, `/numeric/{x}`, `/timezone/{x}`, `/metadata`) dan **401 "This endpoint is disabled for your subscription"** — están bloqueados en el plan gratis, hace falta upgrade de plan en RapidAPI para desbloquearlos.
- **Importante:** `/basic` NO trae bandera, moneda, idioma ni zona horaria (probablemente eso vive en `/all`, que está bloqueado). Si esos campos son necesarios, evaluar el upgrade de plan o buscar otra fuente solo para ese dato — con el plan gratis actual el reemplazo de CountryWise es parcial (geografía/ISO/capital sí, banderas/moneda/idioma no).

Endpoint disponible:
| Método | Ruta | Uso |
|---|---|---|
| GET | `/basic` | Catálogo completo de países: nombre, capital, ISO, región, población |

Endpoints bloqueados en el plan actual (requieren upgrade):
| Método | Ruta | Uso |
|---|---|---|
| GET | `/all` | Datos detallados de país (probablemente incluye bandera/moneda/idioma/tz) |
| GET | `/name/{nombre}` | Buscar por nombre |
| GET | `/capital/{capital}` | Buscar por capital |
| GET | `/region/{region}` | Por región UN geoscheme |
| GET | `/subregion/{subregion}` | Por subregión UN geoscheme |
| GET | `/subsubregion/{subsubregion}` | Por sub-subregión |
| GET | `/alpha2/{codigos}` | Por código ISO 3166 Alpha-2 |
| GET | `/alpha3/{codigos}` | Por código ISO 3166 Alpha-3 |
| GET | `/numeric/{codigos}` | Por código ISO 3166 numérico |
| GET | `/timezone/{tz}` | Por zona horaria |
| GET | `/metadata?valueList={campo}` | Metadata de un campo |

---

## 12. SendGrid (✅ CONFIRMADO end-to-end 2026-07-15 — API nativa, ya no vía RapidAPI)
Notificaciones por correo (confirmaciones de reserva, etc.)

- El proyecto ya NO usa el wrapper de RapidAPI (`rapidprod-sendgrid-v1.p.rapidapi.com`) — se quitó `SENDGRID_HOST_KEY` del `.env`. Ahora se usa la **API nativa de SendGrid** directo: host `api.sendgrid.com`, header `Authorization: Bearer $SENDGRID_KEY` (key real sacada del portal de sendgrid.com, var `.env`: `SENDGRID_KEY`).
- ✅ **Verificado 2026-07-15:**
  1. `GET /v3/scopes` → 200, la key tiene permisos completos incluyendo `mail.send` (no es de solo lectura).
  2. `GET /v3/verified_senders` → 200, sender `aerotracktravel.demo@gmail.com` con `"verified": true` (necesario, si no está verificado SendGrid rechaza cualquier envío aunque la key sea válida).
  3. `POST /v3/mail/send` con ese sender → **202 Accepted**, envío real de prueba a `btoaquizaz@uteq.edu.ec` confirmado.
- Diagnóstico previo (cuando se usaba el wrapper de RapidAPI, ya no aplica): el wrapper daba 403 porque le faltaba el header `Authorization: Bearer {SendGrid key real}` — se confirmó pasando una key inventada, que devolvió el error real de SendGrid en vez del genérico 403, probando que sí reenviaba la petición.

Endpoints principales (API nativa `api.sendgrid.com`, todas con prefijo `/v3`, no la de RapidAPI):
| Método | Ruta | Uso |
|---|---|---|
| POST | `/v3/mail/send` | Enviar correo (✅ probado, 202) |
| GET | `/v3/verified_senders` | Sender identities verificadas (✅ probado) |
| GET | `/v3/scopes` | Permisos de la key (✅ probado) |
| GET | `/v3/suppression/blocks/{email}` | Consultar bloqueos |
| GET | `/v3/suppression/bounces` | Consultar rebotes |
| GET | `/v3/stats` | Estadísticas de cuenta |

---

## 13. 🚢 Cruceros — Cruise Pricing API (⚠️ NO oficial, agregador transparente — creador: Track.Cruises) — 11/11 confirmados 2026-07-15
- Host: `cruise-pricing-api1.p.rapidapi.com`
- ⚠️ **Corrección: `/coverage` SÍ requiere autenticación** (la nota anterior de "público sin auth" era incorrecta) — sin headers `x-rapidapi-key`/`x-rapidapi-host` da `401 "Invalid API key..."`. Todos los endpoints usan el mismo patrón estándar.
- Cuota amplia en el plan probado: 87/100 en el límite por ventana, ~499,987/500,000 en el límite mensual — sin riesgo de agotarla con uso normal.

| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/coverage?company=` | Cobertura por naviera | ✅ devuelve las 9 navieras (costa, royal-caribbean, ncl, princess, celebrity-cruises, msc, disney-cruise-line, carnival, holland-america) |
| GET | `/cruise-lines` | Listado de navieras | ✅ mismos 9 slugs, con conteos de cruceros/barcos/destinos, locales, rango de fechas |
| GET | `/cruise-lines/{cruiseLine}` | Detalle de una naviera | ✅ probado con `msc` — mismo shape que una entrada de `/cruise-lines` |
| GET | `/cruise-lines/{cruiseLine}/destinations` | Destinos de una naviera | ✅ probado con `msc` — array de nombres de destino |
| GET | `/cruises?locale=&sort=&company=&limit=` | Buscar cruceros | ✅ paginación por cursor (`next_cursor`), campos `cruise_id`, `itinerary_id`, `company`, `ship_name`, `departure_date`, `price`, `ports_list` |
| GET | `/cruises/{id}` | Detalle de un crucero | ✅ probado con id real `AX20260717BDSBDS` — incluye `cabin_prices_per_person` (BALCONY/OCEANVIEW) |
| GET | `/cruises/{id}/price-history?locale=` | Histórico de precios | 🔴 **confirmado con test real, no solo documentado**: `403` `{"code":"tier_insufficient","detail":"Price history requires Pro tier or higher.","required_tier":"pro"}` |
| GET | `/price-drops?company=&sort=&limit=` | Bajadas de precio recientes | ✅ `previous_price_euro`, `current_price_euro`, `drop_amount_euro`, `drop_pct`, `cabin_type`, `detected_at` |
| GET | `/ships?limit=&company=` | Catálogo de barcos | ✅ `ship_name`, `company`, `sailing_count`, rango de fechas |
| GET | `/ports?limit=` | Catálogo de puertos | ✅ nombre + `sailing_count`, paginación por cursor |
| GET | `/filter-options?company=` | Opciones de filtro | ✅ probado con `company=msc` — `companies`, `locales`, `destinations`, `ship_names`, `ports` |

.env:
CRUISE_PRICING_API_HOST=cruise-pricing-api1.p.rapidapi.com

---

## 14. Visa Requirement (Travel Buddy AI) (✅ confirmada 2026-07-15, con suscripción activa) — 5/6 endpoints funcionales
**Estado:** Producto propio (no gubernamental oficial, pero primera parte — no es scraper de terceros)
**Host:** `visa-requirement.p.rapidapi.com`
- ✅ `POST /v2/visa/check` probado con `{"passport":"US","destination":"FR"}` → 200 con datos reales (moneda, embajada, validez de pasaporte, etc.)
- ⚠️ `GET /v2/health` da 404 "Endpoint does not exist" — esa ruta del doc no está registrada en este host, ignorarla (el health check real seguramente es otro path, no crítico).

| Método | Endpoint | Descripción | Estado |
|---|---|---|---|
| POST | `/v2/visa/check` | Requisitos de visa pasaporte→destino | ✅ **acepta JSON o form-data indistintamente** (probado ambos formatos con pares de países distintos para descartar caché — corrige nota anterior de "solo form-data") |
| POST | `/v2/visa/map` | Mapa de colores de requisitos por pasaporte | ✅ mismo body flexible (JSON o form-data), campo `passport` |
| GET | `/v2/visa/check/history/{pcc}/{dcc}/{YYYY-MM-DD}` | Histórico de cambios de visa | 🔴 **responde 200 pero con datos falsos/demo, ignorando los parámetros de la ruta** — probado `/KZ/ME/2024-05-01` y devolvió `pcc:"US",dcc:"VN"`; probado `/US/FR/2023-01-01` y devolvió `pcc:"BR",dcc:"JP"` (aleatorio cada vez). El `meta` de la respuesta es explícito: `"data_mode":"demo","is_demo":true,"required_subscription":["MEGA","CUSTOM-internal"]`. Requiere plan MEGA para datos reales. |
| POST | `/v2/passport/rank/custom` | Ranking personalizado de pasaportes | ✅ body JSON envuelto en `{"weights": {...}}` (NO plano) — **requiere las 9 categorías exactas**: `Visa-free`, `Visa on arrival`, `eVisa`, `ESTA`, `eTA`, `Visa required`, `Tourist card`, `Freedom of movement`, `Not admitted` (falta cualquiera → 422 nombrando la que falta). Plan BASIC limita el resultado a top 10 pasaportes. |
| GET | `/v2/destinations` | Listado de países destino | ✅ `iso_alpha2`, `iso_alpha3`, `name` |
| GET | `/v2/passports` | Listado de pasaportes | ✅ mismo shape que `/destinations` |
| GET | `/v2/health` | Health check | 🔴 no existe en este host (404, ver nota arriba) |

**Notas:** Free tier disponible (BASIC $0/mo). Histórico "real" completo solo en plan MEGA (confirmado con test real, no solo documentado — la petición ignora los parámetros y siempre devuelve datos demo aleatorios). Ranking personalizado limitado a top 10 en plan BASIC. Datos no son asesoría legal — agregar disclaimer similar en tu app.
**Enlace directo:** https://rapidapi.com/TravelBuddyAI/api/visa-requirement

---

## 15. Skyscanner Flights & Travel API (✅ confirmada 2026-07-15 — reemplazo de Kiwi y Travelpayouts)
Datos en tiempo real de vuelos y hoteles de Skyscanner. 19 endpoints: Flights, Hotels, Car Hire (solo lookup de ubicación), Config.

- Host: `skyscanner-flights-travel-api.p.rapidapi.com` (var `.env`: `SKYSCANNER_API_HOST`)
- ⚠️ **Ojo con las rutas:** la doc de la API (Quick Start y tabla de endpoints) muestra el prefijo `/api/v1/...`, pero ese prefijo **no existe** en el gateway real — da 404 "Endpoint does not exist" con ese prefijo. Las rutas reales van sin él: `/flights/...`, `/hotels/...`, `/cars/...`, `/config/...`.
- Sistema de IDs propio: primero `searchAirport`/`searchDestination` para resolver `skyId`+`entityId` (vuelos) o `entityId` (hoteles), luego usarlos en el resto de endpoints. Búsqueda de vuelos es progresiva: `searchFlights` devuelve `sessionToken` + `status` (`RESULT_STATUS_INCOMPLETE`/`_COMPLETE`), hay que hacer polling con `searchIncomplete` hasta completar.
- Lista de rutas confirmada 2026-07-15 directo en el panel "Test Endpoint" de RapidAPI (Params/Headers reales), coincide con lo verificado por curl: todas sin prefijo `/api/v1`.

**Los 19 endpoints — estado verificado 2026-07-15 con datos reales de prueba:**

Flights:
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/flights/searchAirport` | Buscar aeropuertos/ciudades por nombre | ✅ (Quito → `UIO`) |
| GET | `/flights/searchFlights` | Buscar vuelos ida o ida y vuelta | ✅ (LON→NYC $483.93 real) |
| GET | `/flights/searchIncomplete` | Paginar más resultados (con `sessionId`) | ✅ responde 200, pero vacío si el `status` ya era `COMPLETE` en la búsqueda original — normal, no hay más que paginar |
| GET | `/flights/getFlightDetails` | Detalle de vuelo + info de reserva | 🔴 200 pero `legs`/`price` siempre vacíos. Probado con los params exactos del playground (`currency`, `itineraryId`, `sessionId`, `countryCode`) y encadenando una búsqueda nueva justo antes para descartar sesión vencida — mismo resultado. No es tema de parámetros, el endpoint no devuelve datos. Usar `searchFlights` para el detalle del itinerario (ya trae legs/price/bookingUrl) en vez de este. |
| GET | `/flights/searchFlightEverywhere` | Explorar destinos más baratos | ✅ funciona con datos reales (desde Londres: Barcelona $20.57, Amsterdam $22.70, Roma $24.09...) pero es **lenta: ~2min 22s de respuesta**. Usar timeout largo (mínimo 3 min) y no bloquear la UI esperándola — considerar spinner/estado async si se integra. |
| GET | `/flights/getCheapestOneway` | Precio más barato por mes (ida) | ✅ datos reales |
| GET | `/flights/searchFlightsMultiStops` | Vuelos multi-ciudad (`legs` como JSON) | ✅ datos reales |
| GET | `/flights/getPriceCalendar` | Calendario de precios (fechas flexibles) | ✅ responde 200 (vacío si no hay quotes para esas fechas) |
| GET | `/flights/getPriceCalendarReturn` | Calendario de precios ida y vuelta (grid 2D) | ✅ datos reales |

Hotels:
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/hotels/searchDestination` | Buscar destinos de hotel | ✅ datos reales (Paris) |
| GET | `/hotels/searchHotels` | Buscar hoteles disponibles (con `entityId`) | ✅ datos reales, `hotelId` real para encadenar el resto |
| GET | `/hotels/getHotelDetails` | Detalle + amenidades de hotel (`hotelId`) | ✅ datos reales |
| GET | `/hotels/getHotelPrices` | Tipos de habitación y precios | ✅ pero requiere `entityId` ADEMÁS de `hotelId` (da 422 "entityId is required" si falta) |
| GET | `/hotels/getHotelReviews` | Reseñas de huéspedes, paginadas | ✅ datos reales (617 reviews) |
| GET | `/hotels/getSimilarHotels` | Hoteles similares cercanos | ✅ datos reales |
| GET | `/hotels/getNearbyMap` | Hoteles con lat/lng para mapa | ✅ datos reales |

Car Hire / Config:
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `/cars/searchLocation` | Ubicaciones de recogida de auto | ✅ datos reales (Paris) |
| GET | `/config/getLocale` | Mercados, monedas y locales soportados | ✅ datos reales |
| GET | `/config/getExchangeRates` | Tasas de cambio en vivo | ✅ datos reales |

---

## 18. Travel Advisor — Api Dojo (✅ confirmada 2026-07-15 — reemplazo de Viator)
Replica datos públicos de TripAdvisor.com: ubicaciones, hoteles, restaurantes, atracciones y **attraction products (tours/actividades reservables, equivalente a Viator)**. También reseñas, fotos, preguntas/respuestas, tips, y un módulo legacy de vuelos en deprecación (no evaluado, no es prioridad — ya está Skyscanner).

- Host: `travel-advisor.p.rapidapi.com` (var `.env`: `TRAVEL_ADVISOR_API_HOST`)
- Flujo: `locations/v2/auto-complete?query={ciudad}` → `geoId` (ej. Paris → `187147`) → usarlo en los `v2/list` de cada categoría.
- ⚠️ **Los endpoints `v2` esperan el campo `geoId` en el body** (no `locationId` ni `location_id` como sugieren nombres alternativos — probar con esos nombres da `204 No Content` silencioso, sin mensaje de error).

**✅ Confirmados con datos reales (2026-07-15):**
- `attraction-products/v2/list` con `{"geoId":187147,"currencyCode":"USD"}` → 30 tours reales de Paris con nombre/ranking (ej. "Paris Seine River Sightseeing Guided Cruise", "Eiffel Tower Dedicated Reserved Access", "Louvre Museum Premium Guided Tour") — **este es el reemplazo directo de Viator**.
- `attractions/v2/list`, `restaurants/v2/list`, `hotels/v2/list` — mismo patrón con `geoId`, todos devuelven datos reales.
- Legacy GET (marcados "deprecating" pero funcionando bien): `attractions/list`, `restaurants/list`, `attractions/get-details` — parámetros simples REST (`location_id`, `currency`, `lang`), confirmados con datos reales.

**🔴 Rotos (verificado, no es tema de parámetros):**
- `attraction-products/v2/get-details` y `hotels/v2/get-details` — siempre `204 No Content` vacío, probado con `contentId` real sacado de un `list` anterior, con y sin `contentType`/`geoId` adicional. Parece que **toda la familia `v2/get-details` está rota** del lado del proveedor.
- **Workaround confirmado 2026-07-16 con el `contentId` real de un tour** (`11475917`, de `attraction-products/v2/list`): `GET attractions/get-details?location_id=11475917&currency=USD&lang=en_US` → **200 con datos reales completos**, y **usa el mismo namespace de IDs que `attraction-products/v2/list`** (el `contentId` del listado SÍ sirve como `location_id` del legacy — no son IDs distintos como se sospechaba). Trae: `name`, `description` (texto libre completo), `num_reviews`, `rating`, `rating_histogram`, `address_obj` (`city`/`country` limpios — mejor que HotelLens, que solo da dirección en texto libre), `supplier_location_name`/`supplier_location_id` (el operador turístico real, ej. "France Tourisme - Daily tour"), `category`, y **`reviews[]` ya embebidas en la misma respuesta** (título, rating, resumen, autor, fecha) — no hace falta otra llamada para reseñas. Para hoteles sigue sin confirmarse un legacy GET equivalente.
- **🔴 NUEVO hallazgo 2026-07-16 — gap real para disponibilidad:** `attraction-products/v2/check-availability` reconfirmado roto (`204` vacío) con el mismo `contentId` real + fechas futuras reales. **`reviews/v2/list` también da `204`** (antes no probado) — ya no hace falta, las reseñas vienen embebidas en el `get-details` legacy de arriba. Conclusión: **no existe ninguna fuente funcional de disponibilidad/horarios por fecha para tours** en esta API — cualquier módulo que necesite eso (ej. CU-O68 de AeroTrack Travel) no tiene de dónde poblarse automáticamente, hay que generarlo con una regla de negocio (igual que ya se hace con `cupos_disponibles` aproximados en otras APIs) o buscar otra fuente.
- Legacy GET `hotels/list` devolvió 200 pero 0 resultados — puede ser falta de disponibilidad real o parámetros de fecha distintos a los probados (`checkin`+`nights`), no confirmado como roto, solo sin datos en la prueba.
- ⚠️ **Gotcha de formato de nombre:** `attraction-products/v2/list` devuelve el título con un prefijo de ranking incrustado, ej. `"1. Paris Seine River Sightseeing Guided Cruise..."` — hay que despojar el `"N. "` inicial antes de guardarlo como nombre limpio.
- 💡 **El campo `trackingKey` de cada tarjeta de `v2/list` es más útil que los campos de presentación**: es un string JSON plano con `prc` (precio), `cur` (moneda), `lid` (id = mismo `contentId`), `br` (rating), `rc` (cantidad de reseñas), `apc` (código de producto) — evita tener que descender 4 niveles de `cardTitle`/`bubbleRating`/`commerceInfo` como en TripAdvisor/hoteles (sección 6).

Endpoints principales:
| Método | Ruta | Uso | Estado |
|---|---|---|---|
| GET | `locations/v2/auto-complete` | Resolver `geoId` de una ciudad/lugar | ✅ |
| POST | `attraction-products/v2/list` | Tours/actividades reservables (= Viator) | ✅ |
| POST | `attractions/v2/list` | Listado de atracciones | ✅ |
| POST | `restaurants/v2/list` | Listado de restaurantes | ✅ |
| POST | `hotels/v2/list` | Listado de hoteles | ✅ |
| POST | `attraction-products/v2/get-details` | Detalle de tour | 🔴 siempre vacío |
| POST | `hotels/v2/get-details` | Detalle de hotel | 🔴 siempre vacío |
| GET | `attractions/get-details` (deprecating) | Detalle de tour/atracción (fallback) | ✅ **reconfirmado 2026-07-16** — mismo namespace de ID que `attraction-products/v2/list`, trae reseñas embebidas |
| GET | `attractions/list` (deprecating) | Listado de atracciones (fallback) | ✅ |
| GET | `restaurants/list` (deprecating) | Listado de restaurantes (fallback) | ✅ |
| POST | `reviews/v2/list` | Reseñas | 🔴 **confirmado roto 2026-07-16** (`204`) — no hace falta, ya vienen embebidas en `attractions/get-details` |
| POST | `photos/v2/list` / `questions/v2/list` | Fotos, Q&A | no probados |
| POST | `attraction-products/v2/check-availability` | Disponibilidad de tour por fecha | 🔴 **reconfirmado roto 2026-07-16** con fechas reales — sin fuente automática para disponibilidad |

---

## 🔗 Enlaces directos (páginas de cada API en RapidAPI)

- Flight Data (Travelpayouts): https://rapidapi.com/Travelpayouts/api/flight-data
- AeroDataBox: https://rapidapi.com/aedbx-aedbx/api/aerodatabox
- Kiwi.com Cheap Flights: https://rapidapi.com/emir12/api/kiwi-com-cheap-flights
- FlightDelay Intelligence API: https://rapidapi.com/gowtham.seeda/api/flightdelay-intelligence-api1
- HotelLens: https://rapidapi.com/Crawlio/api/hotellens
- TripAdvisor API: https://rapidapi.com/elis-lab-2-elis-lab-2-default/api/tripadvisor-api
- Trawex Car Rental: https://rapidapi.com/nilesh160195/api/trawex-car-rental
- Global Rental Cars: https://rapidapi.com/vibemaxdev/api/global-rental-cars
- Viator API: https://rapidapi.com/otomo-autokozo/api/viator-api
- ExchangeRate-API: https://rapidapi.com/exchangerateapi/api/exchangerate-api
- CountryWise: https://rapidapi.com/mapsiter/api/countrywise
- SendGrid: https://rapidapi.com/sendgrid/api/sendgrid
- Cruise Pricing API: https://rapidapi.com/trackcruises/api/cruise-pricing-api1