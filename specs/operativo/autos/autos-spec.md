# Especificación Operativa — Autos

**Módulo:** Autos
**Prefijo:** AUT
**Código fuente:** `app/autos/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O61 (Buscar autos disponibles por aeropuerto/ciudad y fechas), CU-O62 (Ver detalle de vehículo), CU-O63 (Filtrar autos), CU-O64 (Seleccionar auto y modalidad de pago), CU-O119 (Generar catálogo de autos desde fuente externa)
**Actor:** Pasajero / Sistema (automático)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Fuente de datos real confirmada con pruebas en vivo: **Global Rental Cars** (agrega Priceline/Booking/Expedia), ver `docs/fuentes-datos-por-tabla.md` sección Autos y `docs/aerotrack-travel-propuesta-tablas-v3.dbml` (tabla `autos_catalogo`, única de este módulo — a diferencia de Hoteles, no hay tabla de tarifas ni de reseñas separadas).

---

## Funcionalidad 1: Buscar y consultar autos (CU-O61, CU-O62)

Mismo patrón que Vuelos/Hoteles, adaptado a renta de vehículos.

### RF-AUT-001 — Buscar autos disponibles por aeropuerto/ciudad y fechas
El sistema debe permitir a un pasajero ingresar ciudad o aeropuerto de recogida, fecha/hora de recogida y devolución, y consultar `autos_catalogo` filtrando por esos criterios. Muestra resultados con marca, modelo, categoría, transmisión, proveedor y precio por día. Si no hay autos que cumplan los criterios, muestra un mensaje claro.

### RF-AUT-002 — Ver detalle de vehículo
El sistema debe mostrar, para un vehículo seleccionado, sus especificaciones (marca, modelo, categoría, transmisión), el proveedor real cuando esté identificado (`proveedores_comerciales`, vía `proveedor_comercial_id`), la ubicación exacta de recogida y la política de cancelación asociada.

### RNF-AUT-001 — Identificación del agregador de origen
Toda oferta muestra de cuál sub-proveedor vino (`proveedor_agregador`: Priceline/Booking/Expedia) de forma interna para efectos de revalidación (RN-AUT-001), aunque al pasajero solo se le presente el proveedor comercial real (rentadora) cuando se conoce.

---

## Funcionalidad 2: Filtrar autos (CU-O63)

Extiende a CU-O61 — no es un CU independiente, es una capacidad adicional sobre los resultados.

### RF-AUT-003 — Filtrar autos por tipo, marca, proveedor, transmisión, kilometraje y precio
El sistema debe permitir filtrar los resultados de CU-O61 por categoría/tipo, marca, proveedor, transmisión y rango de precio, aplicando cada filtro de forma instantánea sin botón "Aplicar" (REG-J9). **Kilometraje** solo se filtra cuando la oferta lo expone (no todos los proveedores lo informan) — si el dato no existe para una oferta, esa oferta no se excluye por ese filtro, simplemente no participa en el ordenamiento por esa columna.

---

## Funcionalidad 3: Generar catálogo de autos (CU-O119)

Proceso automático — mismo patrón que CU-O19 (Vuelos) y CU-O118 (Hoteles), generalizado por Integraciones (CU-T37/T38).

### RF-AUT-004 — Generar catálogo de autos desde fuente externa
El sistema debe generar periódicamente, mediante un proceso automático, registros en `autos_catalogo` a partir de Global Rental Cars, priorizando el sub-proveedor **Expedia** cuando esté disponible para una ruta/fecha (único de los tres sin el problema de RN-AUT-001). Cada corrida queda registrada en `sincronizaciones_log` (Integraciones) con su cuota consumida.

### RNF-AUT-002 — El catálogo nunca escribe sobre tablas de otro módulo
Este proceso solo escribe en `autos_catalogo`; la relación con `proveedores_comerciales` es de solo lectura cuando existe comisión pactada directamente con la rentadora.

---

## Funcionalidad 4: Seleccionar auto y modalidad de pago (CU-O64)

### RF-AUT-005 — Seleccionar auto y modalidad de pago
El sistema debe permitir a un pasajero seleccionar un vehículo y, cuando el proveedor lo ofrezca, elegir entre pagar ahora o pagar al recoger (`modalidad_pago_disponible`). Antes de confirmar la selección, **revalida la oferta contra la fuente** usando `fuente_oferta_ref` (token/id de oferta del proveedor) — los precios de estas APIs son point-in-time y pueden cambiar entre la búsqueda y la confirmación.

### RN-AUT-001 — Priceline/Booking no garantizan fecha/ubicación exactas — revalidar siempre antes de cobrar
Confirmado con pruebas en vivo: Priceline ignora las fechas de recogida/devolución pedidas (siempre resuelve a "mañana, 2 días") y Booking ignora las coordenadas pedidas (siempre resuelve a EWR/Newark). Ambos devuelven un vehículo e inventario reales, pero no necesariamente correspondientes a lo que el pasajero pidió. **Ninguna oferta de estos dos agregadores se confirma sin revalidar** contra la fuente en el momento de reservar (RF-AUT-005); Expedia no tiene este problema y puede revalidarse con menor margen de discrepancia esperada.
Kiwi fue evaluado y descartado por completo (los 4 endpoints relevantes caídos, sin workaround) — no es una fuente de este módulo.

---

## Reglas de negocio

- **RN-AUT-001** — *(Funcionalidad 4)* Priceline/Booking requieren revalidación obligatoria antes de cobrar; Expedia es la fuente preferida cuando está disponible.
- **RN-AUT-002** — Toda mutación de este módulo (selección/reserva) se audita (CU-O41), igual que cualquier otro módulo.
- **RN-AUT-003** — La modalidad de pago ofrecida (`pagar_ahora`/`pagar_al_recoger`) es siempre la que informa el proveedor para esa oferta específica; el sistema nunca ofrece una modalidad que el proveedor no soporta para esa oferta.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /autos/buscar` | Ciudad/aeropuerto, fecha/hora recogida y devolución, filtros opcionales | HTML/JSON con lista de vehículos disponibles |
| `GET /autos/{id}` | ID de vehículo | HTML/JSON con detalle del vehículo |
| `POST /internal/autos/generar-catalogo` | Disparado por temporizador (Integraciones), sin input de usuario | Vehículos creados/actualizados en `autos_catalogo`; corrida registrada en `sincronizaciones_log` |
| `POST /autos/{id}/seleccionar` | Cookie JWT (opcional hasta checkout), modalidad de pago | Revalidación contra la fuente + ítem listo para Carrito/Reservas, o mensaje si la oferta ya no es válida |

---

## Historias de usuario

- **HU-AUT-01:** Como pasajero, quiero buscar autos disponibles por ciudad/aeropuerto y fechas, para encontrar opciones de renta para mi viaje.
- **HU-AUT-02:** Como pasajero, quiero ver el detalle de un vehículo, para confirmar que se ajusta a mi necesidad antes de elegirlo.
- **HU-AUT-03:** Como pasajero, quiero filtrar por tipo, marca, proveedor, transmisión y precio, para acotar rápido entre muchas opciones.
- **HU-AUT-04:** Como pasajero, quiero elegir si pago ahora o al recoger el auto, cuando el proveedor lo permite, para decidir según mi preferencia.
- **HU-AUT-05:** Como sistema, quiero generar automáticamente el catálogo de autos, para que siempre haya opciones vigentes disponibles para búsqueda.

---

## Objetivo

Sostener un catálogo de autos de renta con inventario y precio reales, priorizando la fuente sin discrepancias de fecha/ubicación (Expedia) y revalidando siempre antes de cobrar cuando la fuente es una de las dos con caveats conocidos (Priceline/Booking) — nunca confiar ciegamente en el snapshot del catálogo para una operación de dinero.

---

## Escenarios

### Camino feliz
1. El sistema genera el catálogo de autos cada ciclo (CU-O119), priorizando Expedia.
2. Un pasajero busca autos por ciudad/fechas (CU-O61) y filtra por categoría y precio (CU-O63).
3. Revisa el detalle de un vehículo (CU-O62) y lo selecciona con modalidad "pagar al recoger" (CU-O64).
4. El sistema revalida la oferta contra la fuente antes de confirmar la selección.

### Manejo de errores
- **Sin resultados de búsqueda:** se muestra mensaje claro.
- **Oferta de Priceline/Booking ya no coincide con lo pedido al revalidar:** se informa explícitamente al pasajero antes de cobrar, nunca se confirma con un dato desactualizado (RN-AUT-001).
- **Modalidad de pago no soportada por el proveedor de esa oferta:** no se ofrece esa opción en el flujo de selección (RN-AUT-003).

---

## Criterios de aceptación

- **CU-O61:** Dado que existe catálogo de autos generado, cuando un pasajero busca por ciudad/aeropuerto y fechas, entonces ve una lista de vehículos disponibles, o un mensaje claro si no hay resultados.
- **CU-O62:** Dado que un pasajero selecciona un vehículo, cuando accede a su detalle, entonces ve especificaciones, proveedor, ubicación de recogida y política de cancelación.
- **CU-O63:** Dado que existen resultados de búsqueda, cuando el pasajero aplica un filtro, entonces la lista se actualiza al instante.
- **CU-O64:** Dado que un pasajero selecciona un vehículo y una modalidad de pago soportada, cuando confirma, entonces el sistema revalida la oferta contra la fuente y la deja lista para Carrito/Reservas, o informa si ya no es válida.
- **CU-O119:** Dado que existe una fuente Global Rental Cars configurada y activa, cuando corre el ciclo automático, entonces se crean/actualizan vehículos con datos reales, priorizando Expedia, y la corrida queda registrada en `sincronizaciones_log`.

---

## Dependencias

- **Seguridad:** auditoría (CU-O41) de mutaciones; la búsqueda es pública, no requiere sesión.
- **Integraciones:** configuración de frecuencia de sincronización y bitácora de corridas (CU-T37/T38) de Global Rental Cars.
- **Carrito/Reservas:** consumen la selección de CU-O64 como ítem — dependen de la migración `reserva_items` documentada en `reservas-spec.md` (no implementada todavía).
- **Facturación:** CU-O85 (conversión de moneda) si el auto se presenta en moneda distinta a USD.

---

## Casos de uso relacionados

- CU-O94 (Agregar ítem al carrito, Carrito) — consume la selección de CU-O64.
- CU-O21, O22 (Crear reserva, Reservas) — destino final de la selección, vía Carrito o directo.
- CU-T11 (Ver reporte de reservas de autos, este módulo, Táctico) — consume reservas confirmadas de este módulo.

---

## Fuera de alcance

- Kiwi como fuente de datos — descartado por completo (4 endpoints caídos, sin workaround); no se reevalúa en esta ronda.
- Filtro por kilometraje cuando el proveedor no lo informa — se omite silenciosamente para esa oferta, nunca se asume un valor.
- Seguros adicionales de renta (cobertura de daños, conductor adicional) como línea de producto propia — si el proveedor los expone, quedan dentro de `politica_reembolso_id`/detalle de la oferta, no como CU independiente en este catálogo.
