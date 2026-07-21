# Especificación Operativa — Cuenta de Usuario / Mis Viajes

**Módulo:** Cuenta / Mis Viajes
**Prefijo:** CTA
**Código fuente:** `app/cuenta/` *(no existe todavía, salvo CU-O91 — ver nota)*
**Casos de uso cubiertos:** CU-O87 (Ver Mis Viajes), CU-O88 (Guardar/eliminar favorito), CU-O89 (Ver y retomar búsquedas recientes), CU-O90 (Crear viaje personalizado), CU-O91 (Crear alerta de precio — **ya implementado**, ver nota), CU-O92 (Consultar saldo y movimientos del programa de beneficios)
**Actor:** Pasajero

> **Estado:** módulo nuevo del catálogo v3.0, sin código propio todavía — **con una excepción real**: CU-O91 (Crear alerta de precio) ya está implementado y probado bajo el número original CU-O26, en `app/reservas/` (`RF-RES-006`, endpoint `POST /alertas-precio`, colección `alertas_precio`). El catálogo lo reubicó conceptualmente aquí (gestión de cuenta, no proceso de reserva — ver nota en `docs/aerotrack-travel-casos-de-uso-v3.md`), pero el código no se mueve en esta ronda. Cuando se implemente este módulo, `router_alertas.py` puede simplemente re-exponer/mover el servicio ya existente de Reservas en vez de reconstruirlo — no es trabajo nuevo, es una reubicación.

---

## Funcionalidad 1: Ver Mis Viajes (CU-O87)

Sin tabla propia — es una vista agregada sobre `reservas`/`reserva_items` (Reservas).

### RF-CTA-001 — Ver Mis Viajes
El sistema debe mostrar a un pasajero autenticado sus reservas próximas, activas y pasadas (`reservas` filtrado por `pasajero_titular_id`, vía `reserva_items` para el detalle de cada componente), con detalle completo de cada una, organizadas por estado temporal (próxima/activa/pasada) en vez de solo por fecha de creación. **Depende por completo** de la migración `reserva_items` documentada en `reservas-spec.md` (no implementada todavía).

---

## Funcionalidad 2: Guardar/eliminar favorito (CU-O88)

### RF-CTA-002 — Guardar / eliminar favorito
El sistema debe permitir a un pasajero guardar y eliminar favoritos de tipo destino, hotel o actividad (`favoritos.tipo`), donde `producto_ref` apunta al id real del catálogo correspondiente (hotel/actividad) o es texto libre cuando `tipo = destino`.

---

## Funcionalidad 3: Ver y retomar búsquedas recientes (CU-O89)

### RF-CTA-003 — Ver y retomar búsquedas recientes por producto
El sistema debe registrar automáticamente cada búsqueda que un pasajero autenticado realiza en cualquier módulo de producto (Vuelos, Hoteles, Autos, Actividades, Cruceros) en `busquedas_recientes` (`criterios` json, tal como se enviaron), y permitir relanzar esa búsqueda exacta desde "Mis búsquedas recientes" con un clic.

### RN-CTA-001 — El registro de búsqueda es responsabilidad de cada módulo de producto, no de este
Cada módulo dueño de una búsqueda (`vuelos-spec.md` CU-O17, `hoteles-spec.md` CU-O54, etc.) es quien escribe en `busquedas_recientes` al ejecutarse; este módulo solo lee y expone la relanzada. Evita que este módulo tenga que conocer los criterios de búsqueda específicos de cada vertical.

---

## Funcionalidad 4: Crear viaje personalizado (CU-O90)

### RF-CTA-004 — Crear viaje personalizado
El sistema debe permitir a un pasajero crear una agrupación libre (`viajes_personalizados`: nombre + descripción) para planificación, sin atarla a ninguna reserva existente — es una nota de planificación, no un mecanismo de reserva.

---

## Funcionalidad 5: Crear alerta de precio (CU-O91) — *(ya implementado, ver nota al inicio)*

### RF-CTA-005 — Crear alerta de precio para una ruta guardada
El sistema debe permitir a un pasajero autenticado suscribirse a un umbral de precio para una ruta y fecha objetivo (`alertas_precio`), sin necesidad de tener una reserva existente. **Ya implementado** en `app/reservas/` bajo `RF-RES-006` — este módulo, al implementarse, decide si reubica el código o solo lo referencia desde su propia navegación de "Mis Viajes".

---

## Funcionalidad 6: Consultar saldo y movimientos del programa de beneficios (CU-O92)

### RF-CTA-006 — Consultar saldo y movimientos del programa de beneficios
El sistema debe mostrar a un pasajero su saldo actual de puntos (suma de `programa_beneficios_movimientos.puntos`, con signo según `tipo`) y su historial de movimientos, cada uno con su tipo, puntos, fecha y, si vino de una compra, la reserva asociada. El nivel actual del pasajero se deriva comparando su saldo contra `programa_beneficios_niveles.puntos_minimos` (configurado vía CU-T24, `specs/tactico/cuenta-mis-viajes/`).

### RN-CTA-002 — Los puntos pueden vencer según el nivel
Si `programa_beneficios_niveles.vencimiento_meses` no es nulo para el nivel vigente del pasajero, los puntos acumulados antes de esa ventana vencen — el saldo mostrado siempre refleja únicamente puntos vigentes, nunca incluye puntos ya vencidos como si estuvieran disponibles.

---

## Reglas de negocio

- **RN-CTA-001** — *(Funcionalidad 3)* El registro de búsquedas es responsabilidad de cada módulo de producto, no de este.
- **RN-CTA-002** — *(Funcionalidad 6)* Los puntos vencidos nunca se cuentan en el saldo disponible.
- **RN-CTA-003** — Toda mutación de este módulo (favorito, viaje personalizado, alerta) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /mis-viajes` | Cookie JWT | HTML/JSON con reservas próximas/activas/pasadas |
| `POST /favoritos` | Cookie JWT, tipo, referencia | Favorito guardado |
| `DELETE /favoritos/{id}` | Cookie JWT | Favorito eliminado |
| `GET /mis-busquedas-recientes` | Cookie JWT | HTML/JSON con búsquedas recientes por producto |
| `POST /mis-busquedas-recientes/{id}/relanzar` | Cookie JWT | Redirección al buscador del módulo correspondiente con los criterios precargados |
| `POST /viajes-personalizados` | Cookie JWT, nombre, descripción | Viaje personalizado creado |
| `POST /alertas-precio` | Cookie JWT, origen, destino, fecha objetivo, precio umbral | *(ya implementado en `app/reservas/`, ver nota)* |
| `GET /mi-cuenta/puntos` | Cookie JWT | HTML/JSON con saldo y movimientos del programa de beneficios |

---

## Historias de usuario

- **HU-CTA-01:** Como pasajero, quiero ver todas mis reservas organizadas por próximas/activas/pasadas, para tener una vista completa de mis viajes.
- **HU-CTA-02:** Como pasajero, quiero guardar destinos, hoteles o actividades como favoritos, para volver a ellos fácilmente.
- **HU-CTA-03:** Como pasajero, quiero retomar una búsqueda reciente con un clic, para no reingresar los mismos criterios.
- **HU-CTA-04:** Como pasajero, quiero crear un viaje personalizado para planificar libremente, sin comprometerme a una reserva todavía.
- **HU-CTA-05:** Como pasajero, quiero ver mi saldo de puntos y mi historial de movimientos, para saber qué beneficios tengo disponibles.

---

## Objetivo

Dar al pasajero un panel único de autogestión sobre todo su historial y planificación de viaje — reservas, favoritos, búsquedas, planes libres y puntos de fidelización — agregando datos que en su mayoría son propiedad de otros módulos, sin duplicar su fuente de verdad.

---

## Escenarios

### Camino feliz
1. Un pasajero guarda un destino como favorito (CU-O88) mientras explora el sitio.
2. Días después, retoma una búsqueda reciente de hoteles para ese destino (CU-O89).
3. Crea un viaje personalizado para agrupar sus ideas (CU-O90) y una alerta de precio para el vuelo (CU-O91, ya implementado).
4. Tras confirmar una reserva, la ve reflejada en Mis Viajes (CU-O87) y gana puntos que consulta en su saldo (CU-O92).

### Manejo de errores
- **Consultar Mis Viajes sin ninguna reserva:** se muestra un mensaje claro con acceso a los buscadores.
- **Saldo de puntos con parte vencida:** el saldo mostrado excluye lo vencido, sin necesidad de que el pasajero lo calcule.

---

## Criterios de aceptación

- **CU-O87:** Dado que un pasajero tiene reservas propias, cuando accede a Mis Viajes, entonces las ve organizadas por próximas/activas/pasadas con su detalle completo.
- **CU-O88:** Dado que un pasajero guarda un destino/hotel/actividad como favorito, cuando lo consulta después, entonces lo encuentra en su lista; al eliminarlo, desaparece.
- **CU-O89:** Dado que un pasajero realizó una búsqueda reciente, cuando la retoma, entonces vuelve al buscador correspondiente con los mismos criterios precargados.
- **CU-O90:** Dado que un pasajero crea un viaje personalizado con nombre, cuando lo guarda, entonces queda disponible en su lista de planificación.
- **CU-O91:** Dado que un pasajero define origen/destino/fecha/precio umbral, cuando confirma, entonces se crea una alerta activa — criterio ya validado en `reservas-spec.md`.
- **CU-O92:** Dado que un pasajero tiene movimientos de puntos registrados, cuando consulta su saldo, entonces ve el total vigente (excluyendo vencidos) y el historial completo.

---

## Dependencias

- **Reservas:** CU-O87 depende de `reserva_items` (migración pendiente); CU-O91 ya vive ahí.
- **Vuelos, Hoteles, Autos, Actividades, Cruceros:** cada uno escribe sus propias `busquedas_recientes` (RN-CTA-001) y expone los ids reales que resuelve `favoritos.producto_ref`.
- **Este módulo, nivel Táctico (`specs/tactico/cuenta-mis-viajes/`):** CU-T24 configura los niveles del programa de beneficios que consume RF-CTA-006.
- **Seguridad:** sesión (CU-O42), auditoría (CU-O41).

---

## Casos de uso relacionados

- CU-O17/O54/O61/O65/O71 (buscadores de cada vertical) — generan las `busquedas_recientes` que CU-O89 relanza.
- CU-O21–O25 (Reservas) — fuente de los datos que agrega CU-O87.
- CU-O26 (eliminado, catálogo original) — mismo CU que CU-O91, ver nota de migración al inicio.
- CU-T24 (Configurar programa de beneficios, este módulo, Táctico) — condiciona RF-CTA-006.
- CU-T25 (Ver reporte de alertas de precio, este módulo, Táctico) — consume alertas creadas por CU-O91.

---

## Fuera de alcance

- Movimiento manual de puntos por un Administrador fuera de una compra real — el catálogo no define un CU de ajuste manual de puntos; si se necesita, se amplía como RF nuevo del nivel Táctico, no se asume aquí.
- Compartir favoritos o viajes personalizados entre pasajeros — ambos son estrictamente privados del pasajero dueño.
