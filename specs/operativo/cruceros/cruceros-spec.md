# Especificación Operativa — Cruceros

**Módulo:** Cruceros
**Prefijo:** CRU
**Código fuente:** `app/cruceros/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O71 (Buscar cruceros por destino, fechas y duración), CU-O72 (Ver itinerario detallado de crucero), CU-O73 (Comparar fechas de zarpe del mismo barco con precios por tipo de camarote), CU-O74 (Ver información del barco), CU-O75 (Seleccionar tipo de camarote y tarifa), CU-O122 (Generar catálogo de cruceros desde fuente externa), CU-O123 (Generar disponibilidad sintética de camarotes)
**Actor:** Pasajero / Sistema (automático)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Fuente de datos real confirmada: **Cruise Pricing API** (10/11 endpoints funcionales; `/price-history` requiere plan PRO, no usado). Ver `docs/aerotrack-travel-propuesta-tablas-v3.dbml` (`navieras`, `barcos`, `cruceros_catalogo`, `cruceros_camarotes_tarifa`). **Gap real confirmado:** la API no expone ningún campo de inventario de camarotes (revisado el JSON completo de `/cruises/{id}`, no solo el resumen) — mismo patrón que Actividades, `cruceros_camarotes_tarifa.cupos_disponibles` es sintético (CU-O123).

---

## Funcionalidad 1: Buscar cruceros (CU-O71)

### RF-CRU-001 — Buscar cruceros por destino, fechas y duración
El sistema debe permitir a un pasajero ingresar destino, rango de fechas de zarpe y duración deseada, y consultar `cruceros_catalogo` filtrando por esos criterios. Muestra resultados con naviera, barco, fecha de zarpe, duración y precio base. Si no hay cruceros que cumplan los criterios, muestra un mensaje claro.

---

## Funcionalidad 2: Ver itinerario e información del barco (CU-O72, CU-O74)

### RF-CRU-002 — Ver itinerario detallado de crucero
El sistema debe mostrar, para un crucero seleccionado, su itinerario día a día (`cruceros_catalogo.itinerario_puertos`, orden real de puertos) en formato de mapa de ruta.

### RF-CRU-003 — Ver información del barco
El sistema debe mostrar, para el barco de un crucero, sus servicios a bordo, planos de cubierta (cuando estén disponibles como archivo) y políticas generales (`barcos`).

---

## Funcionalidad 3: Comparar fechas de zarpe (CU-O73)

Extiende a CU-O71/O72 — comparación entre salidas del mismo barco, no un CU independiente en el flujo.

### RF-CRU-004 — Comparar fechas de zarpe del mismo barco con precios por tipo de camarote
El sistema debe permitir, para un barco específico, comparar sus distintas fechas de zarpe disponibles con el precio por tipo de camarote (`cruceros_camarotes_tarifa`) de cada una, para que el pasajero elija la fecha más conveniente sin repetir la búsqueda completa.

---

## Funcionalidad 4: Generar catálogo de cruceros (CU-O122)

### RF-CRU-005 — Generar catálogo de cruceros desde fuente externa
El sistema debe generar periódicamente, mediante un proceso automático, registros en `navieras`, `barcos`, `cruceros_catalogo` y `cruceros_camarotes_tarifa` (precio, no cupo) a partir de Cruise Pricing API. Cada corrida queda registrada en `sincronizaciones_log` (Integraciones).

### RNF-CRU-001 — El catálogo nunca escribe sobre tablas de otro módulo
Este proceso solo escribe en las 4 tablas propias de este módulo.

---

## Funcionalidad 5: Generar disponibilidad sintética de camarotes (CU-O123)

Regla de negocio propia — mismo patrón que CU-O121 en Actividades.

### RF-CRU-006 — Generar disponibilidad sintética de camarotes
El sistema debe generar, para cada combinación crucero×tipo de camarote, un `cupos_disponibles` aproximado según una regla de negocio configurable (CU-T43, `specs/tactico/cruceros/`) — la API no expone ningún dato de inventario real. Alimenta directamente a CU-O75.

### RN-CRU-001 — La disponibilidad sintética se comunica como tal cuando haga falta
Mismo criterio que RN-ACT-002 (Actividades) y el ya vigente para `tarifas_vuelo.cupos_disponibles`: el origen sintético no se oculta deliberadamente, pero tampoco se presenta como cupo real de la naviera.

---

## Funcionalidad 6: Seleccionar tipo de camarote y tarifa (CU-O75)

### RF-CRU-007 — Seleccionar tipo de camarote y tarifa
El sistema debe permitir a un pasajero seleccionar un tipo de camarote (BALCONY/OCEANVIEW/INTERIOR/SUITE, tal como los expone la API) para un crucero, sujeto al cupo sintético disponible (RF-CRU-006), mostrando el precio por persona.

---

## Reglas de negocio

- **RN-CRU-001** — *(Funcionalidad 5)* La disponibilidad sintética no se presenta como cupo real de la naviera.
- **RN-CRU-002** — Toda mutación de este módulo (selección) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /cruceros/buscar` | Destino, fechas, duración, filtros opcionales | HTML/JSON con lista de cruceros |
| `GET /cruceros/{id}/itinerario` | ID de crucero | HTML/JSON con itinerario día a día |
| `GET /cruceros/{id}/barco` | ID de crucero | HTML/JSON con información del barco |
| `GET /cruceros/barco/{barco_id}/fechas` | ID de barco | HTML/JSON con fechas de zarpe comparadas y precio por camarote |
| `POST /internal/cruceros/generar-catalogo` | Disparado por temporizador (Integraciones) | Navieras/barcos/cruceros/tarifas creados o actualizados |
| `POST /internal/cruceros/generar-disponibilidad` | Disparado por temporizador, parámetros de `configuracion_sistema.disponibilidad_cruceros` | Cupos sintéticos generados/actualizados |
| `POST /cruceros/{id}/camarotes/{tipo}/seleccionar` | Cookie JWT (opcional hasta checkout) | Ítem listo para Carrito/Reservas, o mensaje si el cupo no alcanza |

---

## Historias de usuario

- **HU-CRU-01:** Como pasajero, quiero buscar cruceros por destino, fechas y duración, para encontrar opciones para mi viaje.
- **HU-CRU-02:** Como pasajero, quiero ver el itinerario día a día, para saber qué puertos visitaré.
- **HU-CRU-03:** Como pasajero, quiero ver información del barco, para conocer sus servicios antes de reservar.
- **HU-CRU-04:** Como pasajero, quiero comparar fechas de zarpe del mismo barco, para elegir la más conveniente sin repetir la búsqueda.
- **HU-CRU-05:** Como pasajero, quiero seleccionar el tipo de camarote que prefiero, para reservar exactamente lo que busco.
- **HU-CRU-06:** Como sistema, quiero generar automáticamente el catálogo y su disponibilidad sintética, para que siempre haya opciones vigentes.

---

## Objetivo

Sostener un catálogo de cruceros con datos reales de itinerario, barco y precio, y una disponibilidad honestamente sintética de camarotes donde ninguna fuente real la provee — mismo estándar de transparencia que ya aplica en Vuelos y Actividades.

---

## Escenarios

### Camino feliz
1. El sistema genera el catálogo de cruceros (CU-O122) y su disponibilidad sintética (CU-O123) cada ciclo.
2. Un pasajero busca cruceros por destino/fechas/duración (CU-O71).
3. Revisa el itinerario y la información del barco (CU-O72, O74).
4. Compara fechas de zarpe del mismo barco (CU-O73) y selecciona la más conveniente.
5. Elige tipo de camarote (CU-O75) sujeto al cupo sintético disponible.

### Manejo de errores
- **Sin resultados de búsqueda:** se muestra mensaje claro.
- **Cupo sintético agotado para un tipo de camarote:** se informa antes de confirmar la selección.

---

## Criterios de aceptación

- **CU-O71:** Dado que existe catálogo de cruceros generado, cuando un pasajero busca por destino/fechas/duración, entonces ve una lista de cruceros, o un mensaje claro si no hay resultados.
- **CU-O72:** Dado que un pasajero selecciona un crucero, cuando consulta su itinerario, entonces ve el orden real de puertos día a día.
- **CU-O73:** Dado que un barco tiene múltiples fechas de zarpe, cuando el pasajero las compara, entonces ve el precio por tipo de camarote de cada una lado a lado.
- **CU-O74:** Dado que un pasajero consulta el barco de un crucero, entonces ve sus servicios a bordo y políticas.
- **CU-O75:** Dado que un tipo de camarote tiene cupo sintético disponible, cuando el pasajero lo selecciona, entonces el ítem queda listo con su precio por persona.
- **CU-O122:** Dado que existe una fuente Cruise Pricing API configurada y activa, cuando corre el ciclo automático, entonces se crean/actualizan navieras/barcos/cruceros/tarifas con datos reales.
- **CU-O123:** Dado que existen combinaciones crucero×camarote en el catálogo, cuando corre el job de disponibilidad sintética, entonces se genera un cupo aproximado según la regla configurada.

---

## Dependencias

- **Seguridad:** auditoría (CU-O41); la búsqueda es pública.
- **Integraciones:** configuración de frecuencia de sincronización y bitácora de corridas (CU-T37/T38).
- **Carrito/Reservas:** consumen la selección de CU-O75 — dependen de `reserva_items` (no implementada todavía).
- **Facturación:** CU-O85 (conversión de moneda) para presentación en moneda distinta a USD.
- **Este módulo, nivel Táctico (`specs/tactico/cruceros/`):** CU-T43 configura los parámetros que consume RF-CRU-006.

---

## Casos de uso relacionados

- CU-O94 (Agregar ítem al carrito, Carrito) — consume la selección de CU-O75.
- CU-O21, O22 (Crear reserva, Reservas) — destino final de la selección.
- CU-T13 (Ver cruceros más consultados, este módulo, Táctico) — consume búsquedas/reservas de este módulo.
- CU-T43 (Configurar disponibilidad sintética de camarotes, este módulo, Táctico) — condiciona RF-CRU-006.

---

## Fuera de alcance

- Historial de precio (`/price-history`) — requiere plan PRO de Cruise Pricing API, no contratado en esta ronda.
- Disponibilidad real de camarotes — confirmado como gap sin workaround; la API no expone inventario en ningún endpoint revisado.
- Reserva de múltiples camarotes en la misma transacción fuera del flujo de Carrito.
