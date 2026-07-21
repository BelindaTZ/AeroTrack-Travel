# Especificación Operativa — Hoteles

**Módulo:** Hoteles
**Prefijo:** HOT
**Código fuente:** `app/hoteles/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O54 (Buscar hoteles por destino y fechas), CU-O55 (Ver detalle de hotel), CU-O56 (Filtrar resultados de hoteles), CU-O57 (Seleccionar habitación y tarifa), CU-O58 (Ver reseñas verificadas de hotel), CU-O59 (Consultar cargos adicionales en destino), CU-O60 (Reservar hotel con pago diferido), CU-O118 (Generar catálogo de hoteles desde fuente externa)
**Actor:** Pasajero / Sistema (automático)

> **Estado:** módulo nuevo del catálogo v3.0 (2026-07-15), sin código todavía. Esta especificación es la primera redacción — no hay una versión anterior que migrar. Fuente de datos real confirmada con pruebas en vivo (2026-07-16): **HotelLens**, ver `docs/fuentes-datos-por-tabla.md` sección Hoteles y `docs/aerotrack-travel-propuesta-tablas-v3.dbml` (tablas `hoteles_catalogo`, `hoteles_tarifas`, `hoteles_resenas`, `cargos_locales_destino`).

---

## Funcionalidad 1: Buscar y consultar hoteles (CU-O54, CU-O55)

Permite a cualquier pasajero, autenticado o no, explorar el catálogo de hoteles y su detalle — mismo patrón que Vuelos (`vuelos-spec.md`, RF-VUE-001/002), adaptado a hospedaje.

### RF-HOT-001 — Buscar hoteles por destino y fechas
El sistema debe permitir a un pasajero ingresar destino, fecha de check-in/check-out y número de huéspedes, y consultar `hoteles_catalogo` filtrando por destino. Muestra resultados con nombre, ciudad, estrellas, calificación promedio, imagen principal y precio desde (mínimo de `hoteles_tarifas` vigente para esas fechas). Si no hay hoteles que cumplan los criterios, muestra un mensaje claro.

### RF-HOT-002 — Ver detalle de hotel
El sistema debe mostrar, para un hotel seleccionado, su detalle completo: fotos, dirección, `category_scores` (Value/Location/Rooms/Cleanliness/Service), descripción, servicios/amenidades, horario de check-in/check-out, y un mapa con su ubicación (`latitud`/`longitud`). Incluye también el clima del destino (fuente externa complementaria, ver Fuera de alcance) cuando esté disponible.

### RNF-HOT-001 — Legibilidad de ubicación
Toda pantalla que muestre `hoteles_catalogo.ciudad`/`pais` los presenta ya limpios (vienen resueltos desde el paso 3 del flujo HotelLens, no requieren geocodificación adicional — a diferencia de Vuelos, que sí resuelve códigos IATA contra el modelo heredado).

---

## Funcionalidad 2: Filtrar resultados de hoteles (CU-O56)

Extiende a CU-O54 — no es un CU independiente en el flujo, es una capacidad adicional sobre el mismo resultado (mismo patrón que CU-O53 en Vuelos).

### RF-HOT-003 — Filtrar resultados de hoteles
El sistema debe permitir filtrar los resultados de CU-O54 por estrellas, rango de precio, servicios/amenidades, calificación mínima y zona/ciudad, aplicando cada filtro de forma instantánea sin botón "Aplicar" (REG-J9) — la búsqueda principal (destino/fechas/huéspedes) conserva su acción explícita.

---

## Funcionalidad 3: Generar catálogo de hoteles (CU-O118)

Proceso automático que puebla el catálogo operativo — mismo patrón que CU-O19 en Vuelos, generalizado por el módulo Integraciones (CU-T37/T38).

### RF-HOT-004 — Generar catálogo de hoteles desde fuente externa
El sistema debe generar periódicamente, mediante un proceso automático, registros en `hoteles_catalogo` y `hoteles_tarifas` a partir de HotelLens, siguiendo el flujo de 3 pasos confirmado: (1) `GET /api/v1/hotels?location=` (Google Hotels, descubrimiento) → (2) `GET /api/v1/hotels/prices?url=` (comparador de OTAs, extrae el `hotel_id` real de Booking.com del `booking_url`) → (3) `GET /api/v1/booking/hotels/details?hotel_id=` (fuente primaria real: `room_offers[]` con cupo real `rooms_left`, ciudad limpia, amenidades, política de cancelación real). Cada corrida queda registrada en `sincronizaciones_log` (módulo Integraciones) con su cuota consumida.

### RF-HOT-005 — Refrescar reseñas junto con el catálogo
El sistema debe cachear las reseñas de cada hotel (`hoteles_resenas`) en el mismo ciclo de sincronización, vía `GET /api/v1/hotels/reviews`, para evitar consultar ese endpoint en cada vista de detalle (rate limit estricto por minuto del plan BASIC de HotelLens).

### RNF-HOT-002 — El catálogo nunca escribe sobre tablas de otro módulo
Este proceso solo escribe en las 3 tablas propias de este módulo (`hoteles_catalogo`, `hoteles_tarifas`, `hoteles_resenas`); no crea, modifica ni elimina registros de `proveedores_comerciales` (Facturación) más allá de leer la relación cuando existe comisión pactada directamente.

---

## Funcionalidad 4: Seleccionar habitación y tarifa (CU-O57)

### RF-HOT-006 — Seleccionar habitación y tarifa
El sistema debe mostrar, para un hotel, sus habitaciones disponibles (`hoteles_tarifas`: tipo de habitación, cama, ocupación máxima, tamaño, desayuno incluido) con su precio final y si es reembolsable, comparando explícitamente cancelación reembolsable vs. no reembolsable (REG-G2 — transparencia de precio) antes de que el pasajero elija.

### RN-HOT-001 — Cupo real, no aproximado
`hoteles_tarifas.cupos_disponibles` es el dato real del proveedor (`rooms_left` de Booking.com vía HotelLens), no una simulación — a diferencia de `tarifas_vuelo.cupos_disponibles` (sintético) o de Actividades/Cruceros (disponibilidad por regla de negocio). Ninguna funcionalidad de este módulo debe decrementarlo localmente sin revalidar contra la fuente al momento de reservar, dado que es un snapshot point-in-time del proveedor.

### RN-HOT-002 — Reembolsable es un dato real del proveedor, no una política interna
`hoteles_tarifas.reembolsable`/`cancelacion_hasta` reflejan lo que Booking.com informa para esa habitación específica. `politica_reembolso_id` es una capa **opcional** que la agencia puede superponer (p. ej. un seguro de cancelación de pago extra) — nunca sustituye al dato real, que siempre se muestra primero.

---

## Funcionalidad 5: Ver reseñas verificadas de hotel (CU-O58)

Extiende a CU-O55 (ver detalle).

### RF-HOT-007 — Ver reseñas verificadas
El sistema debe mostrar las reseñas cacheadas de un hotel (`hoteles_resenas`): autor, calificación (con su propia escala — no todas las fuentes usan 5 estrellas), comentario, fecha relativa tal como la entrega el proveedor ("hace 2 meses" — no hay fecha absoluta real, cualquier fecha calculada es una aproximación al momento de la sincronización) y fuente (texto libre: Trip.com, Tripadvisor, Google u otra, varía por hotel).

---

## Funcionalidad 6: Consultar cargos adicionales en destino (CU-O59)

Extiende a CU-O55/O57 — información complementaria antes de reservar, no bloqueante.

### RF-HOT-008 — Consultar cargos adicionales en destino
El sistema debe mostrar, cuando exista un registro vigente en `cargos_locales_destino` para la ciudad del hotel, la regla completa de impuestos/tasas locales tal como la publica la fuente (`regla_texto`, texto autoritativo — las reglas reales varían por categoría de hotel, rango de precio o temporada, no son un monto único). Si la regla es simple, se complementa con un estimado rápido ("desde $X" o "desde X%"); si es compuesta, solo se muestra `regla_texto`.

### RN-HOT-003 — Fuente de cargos locales es un CSV, importado por un DAG propio de este módulo
Los datos de `cargos_locales_destino` provienen de `fuentes_extra/holidu_tourist_tax_por_ciudad.csv` (~100 ciudades) — no es una API con sincronización periódica como `hoteles_catalogo`. Se carga vía un DAG **propio de AeroTrack Travel** (`dags/dag_importar_cargos_locales.py`, ver `plan.md`), disparo manual/infrecuente (los datos de Holidu no cambian a diario) — **corregido 2026-07-18: no se importa como script suelto ni se agrega al DAG `aerotrack_extend_global_dims` del proyecto Analytics (`minio-elt`)**, aunque ese es el único DAG existente que también carga CSVs. Ese DAG llena el modelo dimensional de MinIO (capa analítica, solo lectura); `cargos_locales_destino` es una tabla operativa de `pocketbase-travel` — mezclarlas violaría REG-A1/A2 (separación transaccional/analítica). Ningún hotel fuera de esas ~100 ciudades muestra esta sección (se omite, no se inventa un valor).

---

## Funcionalidad 7: Reservar hotel con pago diferido (CU-O60)

"Reservar sin pagar ahora" — captura de pago manual posterior, `<<extend>>` hacia CU-O86 en `facturacion-spec.md`.

### RF-HOT-009 — Reservar hotel con pago diferido
El sistema debe permitir, además del pago inmediato estándar (vía Reservas/Carrito, `reserva_items.modalidad_pago = pagar_ahora`), una modalidad `pago_diferido`: la reserva se confirma sin cobrar de inmediato, y el cobro real se completa cuando el hotel confirma la disponibilidad (dispara `<<extend>>` CU-O86, `facturacion-spec.md` — flujo Stripe authorize-then-capture).

### RN-HOT-004 — Pago diferido solo disponible si la tarifa lo permite
La modalidad `pago_diferido` solo se ofrece cuando la habitación/tarifa seleccionada la admite explícitamente (no todas las tarifas de HotelLens la soportan); si no está disponible, el sistema no la muestra como opción, en vez de ofrecerla y rechazarla después.

---

## Reglas de negocio

- **RN-HOT-001** — *(Funcionalidad 4)* Cupo real del proveedor, revalidar antes de reservar, nunca decrementar localmente sin confirmar.
- **RN-HOT-002** — *(Funcionalidad 4)* Reembolsable/cancelación son datos reales del proveedor; `politica_reembolso_id` es una capa opcional, nunca un sustituto.
- **RN-HOT-003** — *(Funcionalidad 6)* Cargos locales vienen de una importación manual de ~100 ciudades; fuera de esas ciudades, la sección se omite.
- **RN-HOT-004** — *(Funcionalidad 7)* Pago diferido solo se ofrece si la tarifa lo admite explícitamente.
- **RN-HOT-005** — Toda mutación de este módulo (reserva, no la generación de catálogo que es de solo lectura hacia otras capas) se audita (CU-O41), igual que cualquier otro módulo.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /hoteles/buscar` | Destino, check-in/check-out, huéspedes, filtros opcionales | HTML/JSON con lista de hoteles y precio desde |
| `GET /hoteles/{id}` | ID de hotel | HTML/JSON con detalle completo del hotel |
| `GET /hoteles/{id}/resenas` | ID de hotel | HTML/JSON con reseñas cacheadas |
| `GET /hoteles/{id}/cargos-locales` | ID de hotel | HTML/JSON con regla de cargos locales, o vacío si la ciudad no está cubierta |
| `POST /internal/hoteles/generar-catalogo` | Disparado por temporizador (Integraciones), sin input de usuario | Hoteles/tarifas/reseñas creados o actualizados; corrida registrada en `sincronizaciones_log` |
| `POST /hoteles/{id}/tarifas/{tarifa_id}/seleccionar` | Cookie JWT (opcional para autoservicio anónimo hasta checkout), modalidad de pago | Ítem listo para Carrito/Reservas con la tarifa elegida |

---

## Historias de usuario

- **HU-HOT-01:** Como pasajero, quiero buscar hoteles por destino y fechas, para encontrar opciones de hospedaje para mi viaje.
- **HU-HOT-02:** Como pasajero, quiero ver el detalle completo de un hotel, para decidir si se ajusta a lo que busco antes de comparar precio.
- **HU-HOT-03:** Como pasajero, quiero filtrar resultados por estrellas, precio y servicios, para acotar rápido entre muchas opciones.
- **HU-HOT-04:** Como pasajero, quiero comparar habitaciones reembolsables vs. no reembolsables, para elegir según mi tolerancia a cambios de plan.
- **HU-HOT-05:** Como pasajero, quiero ver reseñas verificadas, para confiar en la calidad real del hotel antes de reservar.
- **HU-HOT-06:** Como pasajero, quiero saber de antemano los cargos locales que pagaré en destino, para no sorprenderme al hacer check-in.
- **HU-HOT-07:** Como pasajero, quiero poder reservar sin pagar de inmediato cuando la tarifa lo permite, para asegurar el hotel sin comprometer el dinero hasta que se confirme.
- **HU-HOT-08:** Como sistema, quiero generar automáticamente el catálogo de hoteles, para que siempre haya opciones vigentes disponibles para búsqueda.

---

## Objetivo

Sostener un catálogo de hoteles siempre vigente con datos reales de inventario y precio (no sintéticos), que permita al pasajero comparar habitaciones con transparencia total sobre reembolso, cargos locales y reseñas, replicando la misma exigencia de "integraciones reales donde es posible" que ya rige a Vuelos (`consideraciones.md` sección 1).

---

## Escenarios

### Camino feliz
1. El sistema genera el catálogo de hoteles cada ciclo (CU-O118), incluyendo reseñas.
2. Un pasajero busca hoteles por destino/fechas (CU-O54) y filtra por estrellas y precio (CU-O56).
3. Selecciona un hotel y revisa su detalle, reseñas y cargos locales (CU-O55, O58, O59).
4. Compara habitaciones reembolsables vs. no reembolsables y selecciona una (CU-O57).
5. Reserva con pago diferido porque su tarjeta no está a mano (CU-O60); el hotel confirma días después y se dispara el cobro real (`facturacion-spec.md`, CU-O86).

### Manejo de errores
- **Sin resultados de búsqueda:** se muestra mensaje claro, sin sugerencia automática (a diferencia de Vuelos, este módulo no tiene aún un CU de predicción/tendencia equivalente).
- **Cupo real agotado entre la búsqueda y la selección:** se revalida contra la fuente antes de confirmar; si ya no hay cupo, se informa explícitamente (mismo principio que RNF-RES-001 en `reservas-spec.md`).
- **Ciudad sin datos de cargos locales:** la sección se omite silenciosamente, nunca se muestra un estimado inventado.
- **Tarifa sin modalidad de pago diferido:** no se ofrece esa opción en el flujo de reserva.

---

## Criterios de aceptación

- **CU-O54:** Dado que existe catálogo de hoteles generado, cuando un pasajero busca por destino/fechas, entonces ve una lista de hoteles con precio desde, o un mensaje claro si no hay resultados.
- **CU-O55:** Dado que un pasajero selecciona un hotel, cuando accede a su detalle, entonces ve fotos, descripción, servicios, ubicación y horarios de check-in/check-out.
- **CU-O56:** Dado que existen resultados de búsqueda, cuando el pasajero aplica un filtro, entonces la lista se actualiza al instante sin botón "Aplicar".
- **CU-O57:** Dado que un hotel tiene habitaciones disponibles, cuando el pasajero las compara, entonces ve claramente cuáles son reembolsables y hasta cuándo, con su precio final.
- **CU-O58:** Dado que un hotel tiene reseñas cacheadas, cuando el pasajero las consulta, entonces ve autor, calificación, comentario y fecha relativa.
- **CU-O59:** Dado que la ciudad del hotel está en la base de cargos locales, cuando el pasajero consulta, entonces ve la regla completa de impuestos/tasas.
- **CU-O60:** Dado que una tarifa admite pago diferido, cuando el pasajero elige esa modalidad, entonces la reserva se confirma sin cobro inmediato y queda marcada para captura posterior.
- **CU-O118:** Dado que existe una fuente HotelLens configurada y activa, cuando corre el ciclo automático, entonces se crean/actualizan hoteles y tarifas con datos reales, y la corrida queda registrada en `sincronizaciones_log`.

---

## Dependencias

- **Seguridad:** sesión (CU-O42, solo para acciones que la requieran — la búsqueda es pública), auditoría (CU-O41) de mutaciones.
- **Integraciones:** configuración de frecuencia de sincronización y bitácora de corridas (CU-T37/T38) de la fuente HotelLens.
- **Carrito/Reservas:** consumen la habitación/tarifa seleccionada (CU-O57) como ítem — dependen de la migración `reserva_items` documentada en `reservas-spec.md` (no implementada todavía).
- **Facturación:** CU-O60 dispara CU-O86 (captura de pago diferido) cuando el hotel confirma.

---

## Casos de uso relacionados

- CU-O94 (Agregar ítem al carrito, Carrito) — consume la selección de CU-O57.
- CU-O21, O22 (Crear reserva, Reservas) — destino final de la selección de habitación, vía Carrito o directo.
- CU-O85 (Convertir moneda, Facturación) — si el hotel se presenta en moneda distinta a USD.
- CU-O86 (Capturar pago diferido de hotel, Facturación) — extend de CU-O60.
- CU-T09 (Comparar hasta 5 propiedades, este módulo, Táctico) — extiende a CU-O54/O55.
- CU-T10 (Ver reporte de hoteles más reservados, este módulo, Táctico) — consume reservas confirmadas de este módulo.

---

## Fuera de alcance

- Clima del destino en el detalle de hotel (mencionado en el catálogo, CU-O55) — fuente externa (OpenWeatherMap) evaluada pero no confirmada en esta ronda; se muestra el detalle sin esa sección hasta que se resuelva.
- Reserva de más de una habitación/hotel en la misma transacción fuera del flujo de Carrito — Carrito es el mecanismo para combinar múltiples ítems, este módulo solo resuelve la selección de un ítem a la vez.
- Negociación o edición manual de la comisión pactada con un hotel/cadena — vive en `proveedores_comerciales` (Facturación/backoffice general), no en este módulo.
- Reseñas escritas directamente por pasajeros de AeroTrack Travel — todas las reseñas de este módulo son cacheadas de fuentes externas (HotelLens), no hay reseñas propias del sistema.
