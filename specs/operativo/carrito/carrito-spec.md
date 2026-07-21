# Especificación Operativa — Carrito

**Módulo:** Carrito
**Prefijo:** CAR
**Código fuente:** `app/carrito/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O93 (Ver contenido del carrito con resumen de precio total), CU-O94 (Agregar ítem al carrito), CU-O95 (Eliminar ítem del carrito), CU-O96 (Proceder al checkout desde el carrito)
**Actor:** Pasajero

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. Deliberadamente **separado** de `reservas` (dbml v3): un carrito no es un PNR, no bloquea cupo, y su ciclo de vida (`activo` → `convertido`/`abandonado`) es lo que necesitan CU-T26/T27 (`specs/tactico/carrito/`) para medir recuperación de carritos abandonados. Mismo patrón polimórfico que `reserva_items` (`carrito_items`), a propósito, para que convertir carrito→reserva (CU-O96) sea un mapeo 1:1 campo a campo — **depende de que esa migración exista** (ver `reservas-spec.md`).

---

## Funcionalidad 1: Ver contenido del carrito (CU-O93)

### RF-CAR-001 — Ver contenido del carrito con resumen de precio total
El sistema debe mostrar al pasajero todos los ítems de su carrito activo (`carrito_items`, cualquier combinación de tipo_producto: vuelo, hotel, auto, actividad), con el precio de cada uno (`precio_snapshot`, capturado al agregarlo) y el total. Si el carrito está vacío, muestra un mensaje claro con acceso directo a los buscadores.

### RN-CAR-001 — El precio mostrado en el carrito es un snapshot, no garantizado
`carrito_items.precio_snapshot` es el precio al momento de agregar el ítem — puede haber cambiado en el catálogo real desde entonces. El carrito lo muestra tal cual (transparencia de que es la referencia con la que se agregó), pero el checkout (CU-O96) siempre revalida contra el catálogo vigente antes de cobrar (REG-G2), nunca cobra el snapshot ciegamente.

---

## Funcionalidad 2: Agregar ítem al carrito (CU-O94)

### RF-CAR-002 — Agregar ítem al carrito
El sistema debe permitir agregar a un carrito activo (creando uno nuevo si el pasajero no tiene uno) un ítem de cualquiera de las 5 verticales con selección directa (vuelo, hotel, auto, actividad o crucero), reutilizando la selección real de cada módulo dueño (`vuelos-spec.md` CU-O18, `hoteles-spec.md` CU-O57, `autos-spec.md` CU-O64, `actividades-spec.md` CU-O69, `cruceros-spec.md` CU-O75). Cada agregado actualiza `carritos.fecha_ultima_actividad` (insumo directo de CU-T26/T27).

> **Corrección 2026-07-18:** el catálogo original de CU-O94 no mencionaba crucero — era un olvido de texto, no una decisión deliberada (el esquema `carrito_items` ya tiene `crucero_id`/`crucero_camarote_id` desde el dbml v3). Corregido en `docs/aerotrack-travel-casos-de-uso-v3.md` y aquí.

### RN-CAR-002 — Un carrito por pasajero activo a la vez
Un pasajero autenticado tiene a lo sumo un carrito en estado `activo` — si ya existe uno, los ítems nuevos se agregan a ese carrito, nunca se crea uno paralelo.

---

## Funcionalidad 3: Eliminar ítem del carrito (CU-O95)

Extiende a CU-O93 — no es un CU independiente en el flujo.

### RF-CAR-003 — Eliminar ítem del carrito
El sistema debe permitir eliminar un ítem individual del carrito sin afectar a los demás, actualizando el total mostrado de inmediato.

---

## Funcionalidad 4: Proceder al checkout desde el carrito (CU-O96)

### RF-CAR-004 — Proceder al checkout desde el carrito
El sistema debe permitir, desde un carrito con al menos un ítem, iniciar el checkout: revalida cada `precio_snapshot` contra el catálogo real vigente de su módulo dueño (RN-CAR-001); si algún precio cambió, lo informa explícitamente antes de continuar (REG-G2). Si el pasajero confirma, dispara `<<include>>` CU-O21/O22 (Reservas, `reservas-spec.md`) mapeando cada `carrito_items` a un `reserva_items` equivalente, y marca el carrito como `convertido`.

### RN-CAR-003 — El checkout nunca convierte un carrito vacío
CU-O96 exige al menos un ítem en el carrito; un carrito vacío no tiene opción de checkout disponible en la interfaz.

---

## Reglas de negocio

- **RN-CAR-001** — *(Funcionalidad 1)* El precio del carrito es un snapshot, revalidado siempre en el checkout.
- **RN-CAR-002** — *(Funcionalidad 2)* Un pasajero tiene a lo sumo un carrito activo.
- **RN-CAR-003** — *(Funcionalidad 4)* No se puede iniciar checkout de un carrito vacío.
- **RN-CAR-004** — Toda mutación de este módulo (agregar, eliminar, convertir) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /carrito` | Cookie JWT | HTML/JSON con ítems del carrito activo y total |
| `POST /carrito/agregar` | Cookie JWT, tipo de producto, referencia del ítem seleccionado | Ítem agregado, `fecha_ultima_actividad` actualizada |
| `DELETE /carrito/items/{id}` | Cookie JWT | Ítem eliminado, total recalculado |
| `POST /carrito/checkout` | Cookie JWT | Revalidación de precios + `<<include>>` hacia CU-O21/O22, o aviso de cambio de precio antes de continuar |

---

## Historias de usuario

- **HU-CAR-01:** Como pasajero, quiero ver el contenido de mi carrito con el total, para saber cuánto voy a pagar antes de confirmar.
- **HU-CAR-02:** Como pasajero, quiero agregar ítems de distintas verticales a un mismo carrito, para armar mi viaje en varios pasos sin perder lo ya elegido.
- **HU-CAR-03:** Como pasajero, quiero eliminar un ítem que ya no quiero, sin perder el resto del carrito.
- **HU-CAR-04:** Como pasajero, quiero proceder al checkout desde mi carrito, para convertir mi selección en una reserva real.

---

## Objetivo

Permitir acumular ítems de cualquier vertical de producto en un mismo lugar, sin comprometer cupo ni dinero hasta la conversión real a reserva, y con transparencia total cuando el precio mostrado ya no coincide con el vigente al momento de pagar.

---

## Escenarios

### Camino feliz
1. Un pasajero agrega un vuelo (CU-O94) y luego, en otra sesión, un hotel al mismo carrito.
2. Revisa el contenido y el total (CU-O93).
3. Elimina el hotel porque cambió de planes (CU-O95).
4. Procede al checkout (CU-O96); el precio del vuelo se revalida sin cambios, y se confirma como reserva real.

### Manejo de errores
- **Carrito vacío:** sin opción de checkout, con acceso directo a los buscadores.
- **Precio cambió entre agregar el ítem y el checkout:** se informa explícitamente antes de cobrar, nunca se cobra el snapshot desactualizado (RN-CAR-001).
- **Intento de crear un segundo carrito activo:** los ítems se agregan al carrito ya existente (RN-CAR-002).

---

## Criterios de aceptación

- **CU-O93:** Dado que un pasajero tiene un carrito activo con ítems, cuando lo consulta, entonces ve cada ítem con su precio snapshot y el total.
- **CU-O94:** Dado que un pasajero selecciona un ítem de cualquier vertical, cuando lo agrega, entonces queda en su carrito activo (creado si no existía).
- **CU-O95:** Dado que un carrito tiene un ítem, cuando el pasajero lo elimina, entonces desaparece del carrito y el total se actualiza.
- **CU-O96:** Dado que un carrito tiene al menos un ítem, cuando el pasajero procede al checkout, entonces los precios se revalidan y, si coinciden, se dispara la creación de la reserva; si no, se informa antes de continuar.

---

## Dependencias

- **Vuelos, Hoteles, Autos, Actividades, Cruceros:** fuente real de cada ítem agregable.
- **Reservas:** `reserva_items` (migración pendiente) es el destino de la conversión (CU-O96); sin esa migración, este módulo no puede completar su función central.
- **Seguridad:** sesión (CU-O42), auditoría (CU-O41).
- **Este módulo, nivel Táctico (`specs/tactico/carrito/`):** CU-T26 consume `carritos.estado`/`fecha_ultima_actividad` para detectar abandono.

---

## Casos de uso relacionados

- CU-O18 (Vuelos), CU-O57 (Hoteles), CU-O64 (Autos), CU-O69 (Actividades), CU-O75 (Cruceros) — fuente de ítems agregables.
- CU-O21, O22 (Crear reserva, Reservas) — incluidos obligatoriamente por CU-O96.
- CU-T26 (Configurar recuperación de carrito abandonado, este módulo, Táctico) — consume el ciclo de vida de `carritos`.
- CU-T27 (Ver reporte de carritos abandonados, este módulo, Táctico) — idem.

---

## Fuera de alcance

- Paquetes como ítem agregable al carrito — un paquete no se agrega al carrito como ítem individual, se construye directo a reserva (`paquetes-spec.md`); el carrito acumula productos sueltos, no combinaciones ya armadas.
- Carrito compartido entre varios pasajeros o dispositivos — un carrito es siempre de un único pasajero autenticado.
- Persistencia de carrito para usuarios no autenticados (invitado) — el catálogo no define este caso; se asume sesión autenticada para todo el módulo.
