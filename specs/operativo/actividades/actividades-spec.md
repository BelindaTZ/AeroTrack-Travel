# Especificación Operativa — Actividades

**Módulo:** Actividades
**Prefijo:** ACT
**Código fuente:** `app/actividades/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O65 (Buscar actividades por destino), CU-O66 (Ver detalle de actividad), CU-O67 (Filtrar actividades), CU-O68 (Verificar disponibilidad y horarios de actividad por fecha), CU-O69 (Seleccionar actividad, horario y número de participantes), CU-O70 (Ver reseñas y calificaciones de actividad), CU-O120 (Generar catálogo de actividades desde fuente externa), CU-O121 (Generar disponibilidad sintética de actividades)
**Actor:** Pasajero / Sistema (automático)

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Fuente de datos real confirmada: **Travel Advisor** (catálogo/detalle/reseñas), ver `docs/fuentes-datos-por-tabla.md` sección Actividades y `docs/aerotrack-travel-propuesta-tablas-v3.dbml` (`actividades_catalogo`, `actividades_horarios`, `actividades_resenas`). **Gap real confirmado, sin workaround:** ninguna fuente probada da disponibilidad/horarios reales por fecha (`attraction-products/v2/check-availability` reconfirmado roto, 204) — `actividades_horarios` se genera por regla de negocio (CU-O121), no por sincronización real.

---

## Funcionalidad 1: Buscar y consultar actividades (CU-O65, CU-O66)

### RF-ACT-001 — Buscar actividades por destino
El sistema debe permitir a un pasajero ingresar un destino y consultar `actividades_catalogo` filtrando por ciudad. Muestra resultados con nombre, categoría, calificación promedio, precio desde e imagen principal. Si no hay actividades que cumplan los criterios, muestra un mensaje claro.

### RF-ACT-002 — Ver detalle de actividad
El sistema debe mostrar, para una actividad seleccionada, su descripción completa y, cuando existan (curación manual — ver RN-ACT-001), inclusiones, punto de encuentro y condiciones. Si estos tres campos no están curados para una actividad, la sección correspondiente se omite en vez de mostrarse vacía.

### RN-ACT-001 — Inclusiones/punto de encuentro/condiciones son curación manual, no automática
Ninguna fuente probada expone estos tres datos como campos separados — solo existe un bloque de descripción en texto libre. `actividades_catalogo.inclusiones`/`.punto_encuentro`/`.condiciones` son nullable y se completan por curación manual cuando se considera necesario para una actividad específica; el proceso automático de catálogo (CU-O120) nunca los escribe.

---

## Funcionalidad 2: Filtrar actividades (CU-O67)

Extiende a CU-O65.

### RF-ACT-003 — Filtrar actividades por categoría, duración, precio y calificación
El sistema debe permitir filtrar los resultados de CU-O65 por categoría, precio y calificación mínima, aplicando cada filtro de forma instantánea sin botón "Aplicar" (REG-J9). **Duración** solo se filtra si la fuente la expone para esa actividad (no confirmado como campo estructurado de Travel Advisor en esta ronda — ver Fuera de alcance); mientras tanto ese filtro queda inactivo, no se simula con datos aproximados.

---

## Funcionalidad 3: Generar catálogo de actividades (CU-O120)

### RF-ACT-004 — Generar catálogo de actividades desde fuente externa
El sistema debe generar periódicamente, mediante un proceso automático, registros en `actividades_catalogo` a partir de Travel Advisor, con el flujo confirmado: (1) `attraction-products/v2/list {geoId}` (búsqueda, el campo `trackingKey` trae precio/moneda/calificación/reseñas planos) → (2) `attractions/get-details?location_id={contentId}` (**legacy** — el `v2/get-details` está confirmado roto) con el mismo id del paso 1, trae descripción real, dirección limpia, operador turístico real (`supplier_location_name`) y reseñas ya embebidas. Cada corrida queda registrada en `sincronizaciones_log` (Integraciones).

### RF-ACT-005 — Cachear reseñas junto con el catálogo
El sistema debe guardar en `actividades_resenas` las reseñas que vienen embebidas en la misma llamada de `get-details` (campo `reviews[]`) — no existe una API de reseñas separada para actividades, a diferencia de Hoteles.

### RNF-ACT-001 — El catálogo nunca escribe sobre tablas de otro módulo
Este proceso solo escribe en `actividades_catalogo`/`actividades_resenas`.

---

## Funcionalidad 4: Generar disponibilidad sintética (CU-O121)

Regla de negocio propia — no hay fuente real de disponibilidad/horarios para esta vertical.

### RF-ACT-006 — Generar disponibilidad sintética de actividades
El sistema debe generar, para cada actividad del catálogo, registros en `actividades_horarios` (fecha, hora, cupo aproximado, precio) siguiendo una regla de negocio configurable (CU-T42, `specs/tactico/actividades/`) — no un dato real de inventario del proveedor. Alimenta directamente a CU-O68.

### RN-ACT-002 — La disponibilidad sintética se comunica como tal cuando haga falta
El origen sintético de `actividades_horarios` no es un dato que deba ocultarse deliberadamente al pasajero, pero tampoco se presenta como "cupo real de proveedor" — mismo criterio de honestidad que ya aplica a `tarifas_vuelo.cupos_disponibles` (también sintético desde siempre).

---

## Funcionalidad 5: Verificar disponibilidad y seleccionar actividad (CU-O68, CU-O69)

### RF-ACT-007 — Verificar disponibilidad y horarios de actividad por fecha
El sistema debe mostrar, para una actividad y fecha, los horarios disponibles generados por CU-O121 con su cupo aproximado y precio.

### RF-ACT-008 — Seleccionar actividad, horario y número de participantes
El sistema debe permitir a un pasajero seleccionar un horario disponible (RF-ACT-007) y el número de participantes, calculando el precio total (`actividades_horarios.precio` × participantes), sujeto al cupo aproximado disponible en ese horario.

---

## Funcionalidad 6: Ver reseñas y calificaciones de actividad (CU-O70)

Extiende a CU-O66.

### RF-ACT-009 — Ver reseñas y calificaciones de actividad
El sistema debe mostrar las reseñas cacheadas de una actividad (`actividades_resenas`): autor, calificación, comentario y fecha (a diferencia de Hoteles, aquí sí hay fecha real, no solo texto relativo).

---

## Reglas de negocio

- **RN-ACT-001** — *(Funcionalidad 1)* Inclusiones/punto de encuentro/condiciones son curación manual, nunca escritos por el proceso automático.
- **RN-ACT-002** — *(Funcionalidad 4)* La disponibilidad sintética no se presenta como cupo real de proveedor.
- **RN-ACT-003** — Toda mutación de este módulo (selección) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /actividades/buscar` | Destino, filtros opcionales | HTML/JSON con lista de actividades |
| `GET /actividades/{id}` | ID de actividad | HTML/JSON con detalle completo |
| `GET /actividades/{id}/horarios` | ID de actividad, fecha | HTML/JSON con horarios disponibles (sintéticos) |
| `GET /actividades/{id}/resenas` | ID de actividad | HTML/JSON con reseñas cacheadas |
| `POST /internal/actividades/generar-catalogo` | Disparado por temporizador (Integraciones) | Actividades/reseñas creadas o actualizadas |
| `POST /internal/actividades/generar-disponibilidad` | Disparado por temporizador, parámetros de `configuracion_sistema.disponibilidad_actividades` | Horarios sintéticos generados/actualizados en `actividades_horarios` |
| `POST /actividades/{id}/horarios/{horario_id}/seleccionar` | Cookie JWT (opcional hasta checkout), número de participantes | Ítem listo para Carrito/Reservas, o mensaje si el cupo no alcanza |

---

## Historias de usuario

- **HU-ACT-01:** Como pasajero, quiero buscar actividades por destino, para encontrar experiencias para mi viaje.
- **HU-ACT-02:** Como pasajero, quiero ver el detalle de una actividad, para saber qué incluye antes de reservar.
- **HU-ACT-03:** Como pasajero, quiero filtrar por categoría, precio y calificación, para acotar rápido entre muchas opciones.
- **HU-ACT-04:** Como pasajero, quiero ver horarios disponibles por fecha, para elegir el que se ajuste a mi itinerario.
- **HU-ACT-05:** Como pasajero, quiero seleccionar horario y número de participantes, para reservar exactamente lo que necesito.
- **HU-ACT-06:** Como pasajero, quiero ver reseñas reales, para confiar en la calidad de la actividad antes de reservar.
- **HU-ACT-07:** Como sistema, quiero generar automáticamente el catálogo y su disponibilidad sintética, para que siempre haya opciones vigentes para búsqueda.

---

## Objetivo

Sostener un catálogo de actividades con datos reales de Travel Advisor donde existen (nombre, descripción, calificación, reseñas), y una disponibilidad honestamente sintética donde ninguna fuente real la provee — sin fingir que el cupo/horario mostrado es inventario real de un proveedor.

---

## Escenarios

### Camino feliz
1. El sistema genera el catálogo de actividades (CU-O120) y su disponibilidad sintética (CU-O121) cada ciclo.
2. Un pasajero busca actividades por destino (CU-O65) y filtra por categoría (CU-O67).
3. Revisa el detalle y las reseñas de una actividad (CU-O66, O70).
4. Verifica horarios disponibles para su fecha de viaje (CU-O68) y selecciona uno con 2 participantes (CU-O69).

### Manejo de errores
- **Sin resultados de búsqueda:** se muestra mensaje claro.
- **Actividad sin inclusiones/punto de encuentro/condiciones curados:** esas secciones se omiten, no se muestran vacías.
- **Cupo sintético insuficiente para el número de participantes pedido:** se informa antes de confirmar la selección.

---

## Criterios de aceptación

- **CU-O65:** Dado que existe catálogo de actividades generado, cuando un pasajero busca por destino, entonces ve una lista de actividades, o un mensaje claro si no hay resultados.
- **CU-O66:** Dado que un pasajero selecciona una actividad, cuando accede a su detalle, entonces ve su descripción completa y, si están curados, inclusiones/punto de encuentro/condiciones.
- **CU-O67:** Dado que existen resultados de búsqueda, cuando el pasajero aplica un filtro, entonces la lista se actualiza al instante.
- **CU-O68:** Dado que una actividad tiene disponibilidad sintética generada, cuando el pasajero consulta una fecha, entonces ve los horarios disponibles con su cupo aproximado.
- **CU-O69:** Dado que un horario tiene cupo suficiente, cuando el pasajero selecciona horario y número de participantes, entonces el ítem queda listo con el precio total calculado.
- **CU-O70:** Dado que una actividad tiene reseñas cacheadas, cuando el pasajero las consulta, entonces ve autor, calificación, comentario y fecha.
- **CU-O120:** Dado que existe una fuente Travel Advisor configurada y activa, cuando corre el ciclo automático, entonces se crean/actualizan actividades y reseñas con datos reales.
- **CU-O121:** Dado que existen actividades en el catálogo, cuando corre el job de disponibilidad sintética, entonces se generan horarios con cupo aproximado según la regla configurada.

---

## Dependencias

- **Seguridad:** auditoría (CU-O41) de mutaciones; la búsqueda es pública.
- **Integraciones:** configuración de frecuencia de sincronización y bitácora de corridas (CU-T37/T38).
- **Carrito/Reservas:** consumen la selección de CU-O69 — dependen de `reserva_items` (no implementada todavía).
- **Facturación:** CU-O85 (conversión de moneda) para presentación en moneda distinta a USD.
- **Este módulo, nivel Táctico (`specs/tactico/actividades/`):** CU-T42 configura los parámetros que consume RF-ACT-006.

---

## Casos de uso relacionados

- CU-O94 (Agregar ítem al carrito, Carrito) — consume la selección de CU-O69.
- CU-O21, O22 (Crear reserva, Reservas) — destino final de la selección.
- CU-T12 (Ver actividades más reservadas, este módulo, Táctico) — consume reservas confirmadas.
- CU-T42 (Configurar disponibilidad sintética, este módulo, Táctico) — condiciona RF-ACT-006.

---

## Fuera de alcance

- Filtro por duración — no confirmado como campo estructurado de la fuente en esta ronda; se agrega si se confirma un campo real, no se simula mientras tanto.
- Disponibilidad real de inventario — confirmado como gap sin workaround en las fuentes evaluadas; si aparece una alternativa mejor a futuro, reemplaza solo `actividades_horarios`, el resto del módulo no cambia (nota heredada de `docs/apis-reference.md`, sección "Pendiente / en pausa").
- Curación automática de inclusiones/punto de encuentro/condiciones — es y seguirá siendo manual mientras ninguna fuente los exponga estructurados.
