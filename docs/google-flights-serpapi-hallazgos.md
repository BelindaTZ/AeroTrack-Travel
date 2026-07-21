# Google Flights (SerpApi) — hallazgos y muestras reales

> Doc de trabajo — guarda los resultados reales de las pruebas para no gastar más
> de la cuota (250 búsquedas/mes, plan free, **compartida entre los 3 motores**:
> `google_flights`, `google_flights_autocomplete`, `google_flights_deals`) mientras
> se termina de diseñar la BD. Host: `serpapi.com`, key en `.env`:
> `GOOGLE_FLIGHTS_API_KEY`. Cuando se implemente de verdad, esto se traslada a
> `docs/apis-reference.md` como sección formal.

## Estado de cuota (2026-07-17)

**4 de 250 búsquedas usadas** en esta sesión de pruebas:
1. `ATL→JFK`, `2026-07-22`, sin `travel_class` (default Economy) — ruta base.
2. `ATL→JFK`, `2026-07-22`, `travel_class=3` (Business).
3. `ATL→JFK`, `2026-07-22`, `travel_class=4` (First).
4. *(reservado, no gastado)* — pendiente probar `booking_options`/`baggage_prices` vía `booking_token`, ver sección "Equipaje" más abajo antes de decidir si vale la pena gastarlo.

Las 3 respuestas completas están guardadas en el repo (no en `%TEMP%`, que se
puede limpiar en cualquier reinicio):
- `fuentes_extra/serpapi_samples/economy_atl_jfk.json`
- `fuentes_extra/serpapi_samples/business_atl_jfk.json`
- `fuentes_extra/serpapi_samples/first_atl_dca_gotcha.json` (la del gotcha de destino sustituido, ver sección 3)

## 1. Búsqueda base (Economy, default) — `ATL→JFK`, `2026-07-22`

```
GET https://serpapi.com/search.json?engine=google_flights
    &departure_id=ATL&arrival_id=JFK&outbound_date=2026-07-22
    &type=2&currency=USD&hl=en&api_key=...
```

Respuesta real (`best_flights[0].flights[0]`):
```json
{
  "departure_airport": {"name": "Hartsfield-Jackson Atlanta International Airport", "id": "ATL", "time": "2026-07-22 09:21"},
  "arrival_airport": {"name": "John F. Kennedy International Airport", "id": "JFK", "time": "2026-07-22 11:50"},
  "duration": 149,
  "airplane": "Airbus A321neo",
  "airline": "Frontier",
  "airline_logo": "https://www.gstatic.com/flights/airline_logos/70px/F9.png",
  "travel_class": "Economy",
  "flight_number": "F9 4732",
  "legroom": "28 in",
  "extensions": ["Below average legroom (28 in)", "Carbon emissions estimate: 91 kg"]
}
```
Nivel itinerario: `price: 134`, `carbon_emissions: {this_flight: 92000, typical_for_this_route: 142000, difference_percent: -35}`, `booking_token: "Wy..."`.

✅ **Cruzado y confirmado real contra AviationStack** (`dep_iata=ATL&arr_iata=JFK&airline_iata=F9`, sin fecha): devolvió `F94732`, mismos horarios (09:21→11:50), solo que "hoy" en vez del 22 de julio — coincidencia exacta, no es data sintética (a diferencia de Duffel, que da aerolíneas/números fabricados).

`price_insights` (nivel de RUTA, no de vuelo — útil para CU-O51 predicción de precio):
```json
{
  "lowest_price": 134,
  "price_level": "typical",
  "typical_price_range": [75, 155],
  "price_history": [[1778990400, 94], [1779076800, 94], "... histórico real de varios meses ..."]
}
```

`other_flights` trae **10 itinerarios reales adicionales** para la misma búsqueda (ej. JetBlue `B6 320`, Airbus A320, $304, legroom 32 in, extensions con Wi-Fi/USB/Live TV) — confirma que hay que guardar VARIOS vuelos reales por ruta/fecha, no solo "el mejor".

**Equipaje**: NO hay campo estructurado en la búsqueda base — solo texto libre a nivel de itinerario, ej. `"extensions": ["Checked baggage for a fee"]`. El precio real de equipaje (`baggage_prices`) vive en un endpoint separado usando `booking_token` (no probado aún, ver arriba).

## 2. Business Class — mismo vuelo, mismo query + `travel_class=3`

```json
{
  "...": "mismos horarios/aeropuertos/avión que la búsqueda Economy",
  "travel_class": "Business Class",
  "flight_number": "F9 4732",
  "extensions": ["Carbon emissions estimate: 137 kg"]
}
```
`price: 326` (vs. `134` en Economy — el mismo vuelo físico, tarifa de cabina distinta). Frontier es aerolínea "budget" — es plausible que Google Flights esté categorizando su asiento premium ("UpFront Plus" real de Frontier) como "Business Class" genérico. No se verificó ese detalle a fondo.

## 3. First Class — 🔴 GOTCHA real encontrado, leer con cuidado

Mismo query que arriba pero `travel_class=4`. **La API cambió el destino sin avisar:**

```json
"search_parameters": {"departure_id": "ATL", "arrival_id": "JFK", "outbound_date": "2026-07-22", "travel_class": 4, ...},
"search_metadata": {"status": "Success"}
```
pero el resultado real (`best_flights[0].flights[0]`):
```json
{
  "departure_airport": {"id": "ATL", "time": "2026-07-22 16:58"},
  "arrival_airport": {"id": "DCA", "time": "2026-07-22 18:59"},
  "airplane": "Canadair RJ 900",
  "airline": "American",
  "travel_class": "First Class",
  "flight_number": "AA 5084",
  "plane_and_crew_by": "PSA Airlines as American Eagle"
}
```

**`arrival_airport.id` es `DCA`, no `JFK`** — pidió ATL→JFK y devolvió ATL→DCA, con `status: "Success"` y sin ningún warning/flag que lo indique. Conclusión: **cuando no hay First Class real disponible en la ruta exacta pedida, la API sustituye silenciosamente otro itinerario.**

⚠️ **Regla obligatoria para cualquier implementación futura**: SIEMPRE validar que `flights[].departure_airport.id` y `flights[].arrival_airport.id` coincidan con lo pedido antes de guardar el resultado — descartar (no almacenar) cualquier itinerario que no coincida. No confiar en `search_metadata.status: "Success"` como garantía de que la ruta pedida es la que vino.

## Conclusiones para la BD

- **Clase de cabina**: sí hay datos reales (Economy/Business/First confirmados; Premium Economy no probado, `travel_class=2`). Pero cada clase adicional = 1 búsqueda más por ruta/fecha — con la cuota ya comprometida en la opción B (40-60 llamadas/mes solo para Economy en 2 días de ventana), pedir las 4 clases en las 20 rutas dispararía el gasto ~4x. Decisión pendiente: ¿todas las rutas con multi-clase, o solo un subconjunto pequeño "premium" para no comprometer la cuota?
- **Equipaje real**: no vale la pena gastar cuota en `booking_options`/`baggage_prices` para todo el catálogo — mejor usar `equipaje_incluido` (nuestra propia regla de negocio en `niveles_tarifa`, ya existente) + guardar el texto libre de `extensions` como señal barata complementaria.
- **Asientos**: ninguna fuente da mapa de asientos real (ni Google Flights ni AviationStack ni Duffel-sandbox son útiles para esto) — necesita ser generado como regla de negocio propia, igual que cupos de Actividades/Cruceros.
