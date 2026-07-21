# APIs Externas — Verificadas y Listas para Implementación

> Generado el 2026-07-15 tras una sesión completa de pruebas en vivo (curl real contra cada API, con las credenciales del `.env`). Este documento contiene **solo lo que quedó confirmado funcionando** — las APIs que no sirvieron o fueron reemplazadas NO aparecen aquí (ver `docs/apis-reference.md` si hace falta el detalle crudo de esa investigación).
>
> **Ningún valor real de key ni host aparece en este archivo** — todo se referencia por el nombre de la variable en `.env`. Verificado que cada variable mencionada abajo existe y tiene el valor correcto en el `.env` local (que está en `.gitignore`, no se sube a git).

## Cómo autenticar

La mayoría de las APIs de este documento son de RapidAPI y siguen el mismo patrón:

```
headers = {
  "x-rapidapi-key": os.environ["RAPIDAPI_KEY"],       # una sola key para todas
  "x-rapidapi-host": os.environ["<VAR_HOST_ESPECIFICA>"]  # distinta por API, ver cada sección
}
```

Las que no son de RapidAPI (SendGrid, Stripe, Gmail, Groq, Gemini, etc.) usan su propia key nativa — se indica en cada sección.

## ⚠️ Nota general antes de implementar: fuentes de hoteles duplicadas

Hay **tres** APIs que devuelven datos de hoteles (Skyscanner, TripAdvisor vía `tripadvisor16`, y Travel Advisor). No hace falta integrar las tres — conviene elegir una primaria antes de escribir código, para no duplicar trabajo. Sugerencia: Skyscanner para vuelos+hoteles en el mismo flujo de búsqueda, Travel Advisor para atracciones/tours/restaurantes (cubre lo que las otras dos no cubren bien).

---

## ✈️ Vuelos

### Skyscanner Flights & Travel API
- **Env:** host en `SKYSCANNER_API_HOST`
- 19 endpoints: búsqueda de vuelos (ida/vuelta/multi-ciudad), calendario de precios, exploración "everywhere", hoteles completos, autos (solo lookup de ubicación), config (locale/tasas de cambio).
- ⚠️ **Las rutas van SIN el prefijo `/api/v1`** aunque la documentación del proveedor lo muestre así (ej. usar `/flights/searchAirport`, no `/api/v1/flights/searchAirport` — con el prefijo da 404).
- Flujo de vuelos: `flights/searchAirport?query=` → `skyId`+`entityId` → `flights/searchFlights` (devuelve `sessionToken` + itinerarios ya con precio y `bookingUrl` incluidos).
- Flujo de hoteles: `hotels/searchDestination?query=` → `entityId` → `hotels/searchHotels?entityId=&checkIn=&checkOut=` → `hotelId` → `getHotelDetails` / `getHotelReviews` / `getSimilarHotels` / `getNearbyMap`. `getHotelPrices` necesita `entityId` **además** de `hotelId` (si falta, da 422).
- 🔴 **`flights/getFlightDetails` no sirve** — siempre devuelve vacío (`legs`/`price` null) aunque se pasen los parámetros exactos con una sesión recién creada. No es necesario: `searchFlights` ya trae todo lo que hace falta (legs, precio, booking URL).
- ⚠️ **`flights/searchFlightEverywhere` es lenta (~2min 30s de respuesta)** pero funciona con datos reales. Usar timeout largo (3min+) y no bloquear la UI esperándola.

### AeroDataBox
- **Env:** `AERODATABOX_API_HOST`
- Estado de vuelo en tiempo real, horarios, datos de aeropuerto/aerolínea/aeronave, retrasos, y suscripciones de alertas por webhook. **Cobertura completa probada 2026-07-15** — detalle por categoría en `docs/apis-reference.md` sección 2.
- ⚠️ Plan Free: 600 unidades/mes. Costo real por tipo: lookups simples ≈1-2 unidades, búsquedas ≈2, **Statistical API y flota por aerolínea ≈6 (caro)**, Healthcheck/Subscriptions gratis. Vigilar el header `X-RateLimit-API-Units-Remaining` (no el de requests-por-ventana, que es otro límite y no refleja la cuota real). Espaciar llamadas ≥2-3s.
- ✅ Confirmado con datos reales en las 8 categorías (Aircraft, Airport, Flight Alert, Flight, Healthcheck, Industry, Miscellaneous, Statistical).
- 🔴 `/airports/{codeType}/{code}/time/solar` (y su variante con fecha) da 404 a nivel de gateway de RapidAPI — existe en la spec propia de AeroDataBox pero no está publicada en el producto de RapidAPI.
- 💡 Enums a usar tal cual (no adivinar): Aircraft `searchBy`: `Reg`/`Icao24`/`Id`. Flight `searchBy`: `Number`/`Reg`/`CallSign`/`Icao24`. Airport `codeType`: `Icao`/`Iata`. Webhook `subjectType`: solo `FlightByNumber` o `FlightByAirportIcao`.
- ⚠️ No se probó `POST /subscriptions/balance/refill` a propósito (riesgo de afectar facturación real de la cuenta).

### AviationStack
- **Env:** `FLIGHT_STATUS_API_KEY` (va como query param `access_key`, no como header)
- Datos de vuelos en tiempo real — pensada para el monitoreo activo de disrupciones.
- ⚠️ El plan free solo responde por `http://`, no `https://` — no forzar TLS en la llamada.

### OpenSky Network
- **Env:** `OPENSKY_API_URL` — pública, sin autenticación.

### Duffel (sandbox)
- **Env:** `DUFFEL_API_KEY`
- Confirmado con `GET /air/airlines`. Requiere el header `Duffel-Version: v2`. Modo sandbox — para emitir "tickets" de prueba, no reservas reales.

### Cruise Pricing API
- **Env:** `CRUISE_PRICING_API_HOST`
- Precios, itinerarios y disponibilidad de cruceros. **Los 11 endpoints confirmados con datos reales 2026-07-15** — detalle en `docs/apis-reference.md` sección 13.
- ⚠️ **Corrección: `/coverage` SÍ requiere los headers de auth estándar** (la nota anterior de "público sin auth" era incorrecta — da 401 sin ellos).
- 🔴 Único endpoint restringido: `GET /cruises/{id}/price-history` — confirmado con test real que da `403 tier_insufficient` (requiere plan PRO), no solo documentado.

---

## 🏨 Hoteles / Restaurantes / Atracciones

### Travel Advisor (Api Dojo)
- **Env:** `TRAVEL_ADVISOR_API_HOST`
- Replica datos públicos de TripAdvisor: ubicaciones, hoteles, restaurantes, atracciones, y **attraction products (tours/actividades reservables — el reemplazo funcional de lo que se buscaba con Viator)**.
- Flujo: `locations/v2/auto-complete?query={ciudad}` → `geoId` → usarlo en cualquier `v2/list`.
- ⚠️ **El body de los endpoints `v2` espera el campo `geoId`** (no `locationId` ni `location_id` — con esos nombres da `204 No Content` silencioso, sin mensaje de error).
- ✅ Confirmados con datos reales: `attraction-products/v2/list`, `attractions/v2/list`, `restaurants/v2/list`, `hotels/v2/list` — todos con `{"geoId": ..., "currencyCode": "USD"}`.
- 🔴 **Toda la familia `v2/get-details` está rota** (`attraction-products/v2/get-details`, `hotels/v2/get-details`) — siempre `204` vacío, probado con `contentId` real sacado de un `list` anterior y varias combinaciones de parámetros. Tampoco funciona `attraction-products/v2/check-availability`.
- ✅ **Workaround para detalle:** usar el endpoint legacy `GET attractions/get-details?location_id=&currency=&lang=` — está marcado "deprecating" en la doc del proveedor pero funciona perfecto con datos reales. También funcionan `GET attractions/list` y `GET restaurants/list` (legacy) si se prefiere REST simple en vez del body GraphQL-style de `v2`.

### TripAdvisor (vía host `tripadvisor16`)
- **Env:** `TRIPADVISOR_API_HOST`
- Flujo hoteles: `hotels/searchLocation?query={ciudad}` → `geoId` → `hotels/searchHotels?geoId=&checkIn=&checkOut=` → resultados reales con precios de Booking.com.
- 🔴 **Módulo de restaurantes roto del lado del proveedor**: `restaurant/searchLocation` siempre devuelve `{"status":false,"message":"Something went wrong..."}` sin importar la ciudad — usar Travel Advisor para restaurantes en su lugar.
- Atracciones: no se encontró endpoint de resolución de ubicación registrado en este host — usar Travel Advisor para atracciones/tours.

### HotelLens
- **Env:** `HOTELLens_API_HOST`
- Agrega Google Hotels + Booking.com + Agoda. **Cobertura completa probada 2026-07-15** (15 endpoints) — detalle en `docs/apis-reference.md` sección 5.
- ✅ Google Hotels es el único proveedor con búsqueda propia funcional: `GET /api/v1/hotels?location={ciudad}` (⚠️ **NO uses `query=`** — se ignora silenciosamente y siempre cae al listado default de Nueva York; corrige la nota anterior de este doc, que era un falso positivo). El resultado trae un `url` de entidad de Google que alimenta `/details`, `/about`, `/location`, `/reviews`, `/reviews/complete`, `/prices`.
- 🔴 **`GET /api/v1/booking/hotels` y `GET /api/v1/agoda/hotels` (las búsquedas propias de esos dos proveedores) están caídas** (502 "API not working", outage del backend, confirmado con múltiples params). Workaround: sacar el `hotel_id`/`hid` de las ofertas de Booking/Agoda embebidas en la respuesta de `/api/v1/hotels/prices` (Google Hotels) — con eso sí funcionan `/booking/hotels/details`, `/booking/hotels/reviews`, `/agoda/hotels/details`, `/agoda/hotels/reviews`.
- ⚠️ Plan BASIC: rate limit estricto por minuto (429 tras ~4-5 llamadas rápidas, recupera en ~60s) — espaciar/backoff.

### Global Rental Cars
- **Env:** `GLOBAL_RENTAL_CARS_API_HOST`
- Agrega Priceline, Booking, Expedia y Kiwi para autos de renta. **Cobertura completa probada 2026-07-15** (26 endpoints: 17 ✅ + 2 ⚠️ + 7 🔴) — detalle en `docs/apis-reference.md` sección 8.
- ⚠️ **Prefijos distintos por proveedor**: `priceline`/`expedia`/`kiwi` usan `/1.0/...`, `booking` usa `/booking` y `/booking-app` (NO `/1.0`).
- ✅ Flujos funcionales de punta a punta: **Priceline** (`auto-complete`→`search`→`details`, pero ignora fechas pedidas), **Booking** (`autocomplete`→`search` con params snake_case→`detail`/`detail/packages`/`detail/supplier/*`, pero `search` ignora las coordenadas y siempre devuelve Newark/EWR), **Expedia** (`auto-complete`→`search` con código IATA plano, no el `gaiaId`→`details`, sin caveats).
- 🔴 **Kiwi está completamente caído** (los 4 endpoints: 405/500 upstream, sin camino funcional). `priceline/top-airports` y `priceline/partners` también caídos (403 "NO DATA!"). `booking-app/car/search-by-location` y `search-by-id` dan 500.
- 💡 `/1.0/expedia/rigions` (con ese typo, no "regions") es la ruta real del proveedor — confirmado, no corregir.

---

## 🌍 Países / Geografía

### Countries — Oliver Marchington (`countries59`)
- **Env:** host en `COUNTRIES_API_HOST2`
- 10 endpoints por `country_code` (`iso2`, `iso3`, `time_zone`, `phone_number`, `language`, `geo`, `currency`, `capital`, `all`, `list_countries`). `/all` trae todo junto: capital, continente, área, timezone, idiomas, moneda, código telefónico, ISO3, dominio, FIPS, ISO numérico.
- ⚠️ **Plan Basic: 25 requests/mes (tope 1000/hora)** — la restricción es por cantidad, no por endpoint bloqueado. Cuidar la cuota, cada llamada de prueba cuenta.
- ⚠️ **El campo `"data"` de la respuesta es un string con sintaxis de dict de Python** (comillas simples: `"data": "{'Country Name': 'United States', ...}"`), no JSON anidado real. Usar `ast.literal_eval()` en Python — `json.loads()` falla por las comillas simples.

### Countries — Aptitude Apps (`countries33`), complementaria
- **Env:** host en `COUNTRIES_API_HOST`
- Solo el endpoint `/basic` está disponible en el plan gratis (el resto da 401 "disabled for your subscription"), pero `/basic` no tiene el límite de 25/mes de la otra y devuelve **un dump completo de ~250 países en una sola llamada** (nombre, capital, ISO alpha2/alpha3/numeric, región/subregión UN, población).
- **Uso recomendado:** uno para seed inicial de una tabla de referencia de países (una sola llamada, sin gastar cuota), y `countries59` solo para lookups puntuales que necesiten moneda/idioma/timezone (que `/basic` no trae).

### Opentripmap
- **Env:** `OPENTRIPMAP_API_KEY`
- Geocoding de lugares / puntos de interés turístico. Confirmado con `GET /0.1/en/places/geoname`.

### Nominatim / OpenStreetMap
- **Env:** `NOMINATIM_URL` — pública, sin key, pero **requiere un header `User-Agent` propio** (ej. `AeroTrackTravel/1.0`) o puede rechazar la petición por política de uso.

---

## 💱 Moneda

### ExchangeRate-API (vía RapidAPI)
- **Env:** host en `HOST_EXCHANGE_RATE_API`
- 3 endpoints confirmados con datos reales: `GET /latest?base=`, `GET /convert?base=&target=`, `GET /codes`.
- ⚠️ La var `EXCHANGE_RATE_API_KEY` (pensada para el API oficial directo `v6.exchangerate-api.com`) **no funciona** (403 invalid-key) — no usarla. La vía que sí funciona es `RAPIDAPI_KEY` + `HOST_EXCHANGE_RATE_API`.

---

## ✉️ Notificaciones

### SendGrid (API nativa, no RapidAPI)
- **Env:** `SENDGRID_KEY` — se manda como `Authorization: Bearer $SENDGRID_KEY` directo contra `api.sendgrid.com`, sin pasar por RapidAPI.
- ✅ **Confirmado de punta a punta**: key con permisos completos (incluye `mail.send`), sender `aerotracktravel.demo@gmail.com` verificado, y un correo de prueba real enviado con éxito (`POST /v3/mail/send` → 202, recibido y confirmado por el usuario).
- Endpoints útiles: `POST /v3/mail/send`, `GET /v3/verified_senders`, `GET /v3/scopes`, `GET /v3/stats`, `GET /v3/suppression/bounces`. Todos con prefijo `/v3`.

### Gmail API OAuth
- **Env:** `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`, `GMAIL_REFRESH_TOKEN`
- Confirmado: el refresh_token es válido y genera un access_token nuevo sin problema contra `https://oauth2.googleapis.com/token`.
- ⚠️ El scope actual del token es `gmail.readonly` — si se necesita enviar correo por la API de Gmail (no solo leer), hay que volver a autorizar con scope `gmail.send` o `gmail.compose`.

### Gmail SMTP (alternativa simple)
- **Env:** `GMAIL_ADDRESS`, `GMAIL_APP_PASS`
- Credenciales configuradas pero **no se hizo un envío SMTP real de prueba esta sesión** — probarlo antes de depender de esta vía (con SendGrid ya confirmado, probablemente no haga falta usar esta).

---

## 💳 Pagos

### Stripe (test mode)
- **Env:** `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`
- Confirmado con `GET /v1/balance` — responde con datos reales de la cuenta de test.

---

## 🧭 Visado

### Visa Requirement (Travel Buddy AI)
- **Env:** host en `VISA_REQUIREMENT_API_HOST`
- **5/6 endpoints confirmados con datos reales 2026-07-15** — detalle en `docs/apis-reference.md` sección 14.
- ✅ `POST /v2/visa/check` y `POST /v2/visa/map` — **aceptan JSON o form-data indistintamente** (corrige nota anterior de "solo form-data").
- ✅ `POST /v2/passport/rank/custom` — body JSON debe ir envuelto en `{"weights": {...}}` con las 9 categorías exactas (`Visa-free`, `Visa on arrival`, `eVisa`, `ESTA`, `eTA`, `Visa required`, `Tourist card`, `Freedom of movement`, `Not admitted`); plan BASIC limita a top 10 resultados.
- ✅ `GET /v2/destinations` y `GET /v2/passports` — catálogos completos.
- 🔴 `GET /v2/visa/check/history/{pcc}/{dcc}/{fecha}` — responde 200 pero con **datos demo aleatorios que ignoran los parámetros de la ruta** (`data_mode: demo`), requiere plan MEGA para histórico real.
- ⚠️ `GET /v2/health` no existe en este host (404) — no está en la lista real de endpoints, ignorar esa ruta si aparece en documentación externa.

---

## 🖼️ Media

### Unsplash
- **Env:** `ACCESS_KEY` (se manda como header `Authorization: Client-ID $ACCESS_KEY`)
- Fotos de stock para destinos/hoteles. Confirmado con `GET /photos/random?query=`.

---

## 🤖 IA

### Groq
- **Env:** `GROQ_API_KEY`
- Confirmado con `GET /openai/v1/models`.

### Gemini
- **Env:** `GEMINI_API_KEY`
- Confirmado con `GET /v1beta/models`.
- ⚠️ El formato de esta key en particular no es el típico `AIza...` de Gemini — funciona igual, pero si se genera una key nueva y tiene el formato clásico, no debería ser un problema.

---

## 🌤️ Clima

### OpenWeatherMap
- **Env:** `OPENWEATHERMAP_API_KEY`
- Confirmado con `GET /data/2.5/weather?q=`.

---

## ⏳ Pendiente de verificar en la próxima sesión

- **FlightDelay Intelligence API** (env: `FLIGHT_DELAY_API_HOST`) — se probó una sola vez, muy al inicio de esta sesión (`GET /health` → `404 "Application not found"`) y nunca se retomó. Estado desconocido, no confirmada ni como funcional ni como descartada — falta re-probarla antes de decidir si se integra o se busca alternativa.
- Como pediste, conviene re-confirmar en la próxima sesión que todas las APIs de este documento sigan con la suscripción/clave activa y con cuota disponible (especialmente `countries59`, que tiene solo 25 requests/mes) antes de empezar a escribir código de integración.
