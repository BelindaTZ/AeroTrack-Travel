# Sistema de Diseño Visual — AeroTrack Travel

**Estado:** v4 (Sky Blue × Modernist híbrido) — decisión tomada 2026-07-18, sobre la v3 (Sky Blue + Coral) del 2026-07-12.
**Relación con la constitución:** este documento es la **implementación concreta** de los
principios direccionales J1–J11 de `.specify/memory/constitution.md`. La constitución fija la
regla ("familia fría de confianza para `primary`, tono cálido exclusivo para `accent` en
conversión" — J3; "tres roles tipográficos, mono obligatoria para cifras en columna" — J4); este
archivo fija los valores exactos que cumplen esa regla hoy. Si la paleta cambia otra vez, se
actualiza este archivo — la constitución solo cambia si cambia el *principio*.

**Fuente de verdad visual (v4):** proyecto de diseño `Diseño de interfaces del sistema`
(`claude.ai/design/p/cc51aa5c-d4e2-4655-ba6d-b29322cb9ad2`, archivo `AeroTrack Travel.dc.html`),
importado vía el MCP de diseño el 2026-07-18. Ese canvas consume el design system **Modernist**
(mismo proyecto, carpeta `_ds/modernist-*`): tipografía Archivo, grid modular, reglas de 2px,
radio de esquina en cero, paleta mono (un solo rojo `#ec3013`, sin color frío). Fuente de verdad
v3 anterior (histórica, ya no vigente): guía iterada con la skill `ui-ux-pro-max`.

## Nota de migración (2026-07-18) — por qué v4 y qué cambió

El cliente aprobó el **diseño y la distribución** del canvas importado (layout de buscador, cards
de resultado, tablas de backoffice, tabs, chat del Asistente IA) pero pidió dos ajustes deliberados
frente al Modernist original:

1. **Radio de esquina suavizado.** Modernist es 100% escuadrado a propósito (su propio `readme.md`:
   *"Do not round a corner anywhere — `--radius-md` is 0 on purpose"*). Se pidió explícitamente
   quitarle ese filo — v4 usa una escala de radios suave (ver sección "Radios"), no cero.
2. **Paleta híbrida, no monocromática.** Modernist es un esquema de un solo color (`#ec3013` para
   todo, "no second accent was chosen" según su propio readme) — **esto viola directamente la
   constitución J3**, que exige un `primary` frío/confianza separado de un `accent` cálido
   exclusivo de conversión. Se resolvió manteniendo el **Sky Blue** (`#0072CE`, ya implementado en
   `aerotrack.css` y en las pantallas existentes) como `--at-primary`, y usando el rojo de
   Modernist como `--at-accent` — cumple J3 sin tocar la constitución ni requerir reescribir las
   pantallas ya construidas con azul.

Todo lo demás de Modernist se adopta tal cual: tipografía Archivo única (heading + body), reglas
gruesas de 2px como recurso estructural principal (no sombra), cards con `kicker`/`title`/`body`/
`meta`, control segmentado, tabs de backoffice invertidos (activo = fondo oscuro), tablas densas
con encabezado en mayúsculas. La única adición fuera de Modernist es la fuente monoespaciada para
cifras en columna, porque la constitución (REG-J4) la exige y Modernist no define ese rol.

## ⚠️ Estado de implementación — leer antes de tocar una pantalla nueva

**Capa de tokens migrada a v4 (2026-07-19).** `public/assets/css/aerotrack.css` ya define la
paleta, tipografía (Archivo) y radios de v4 descritos en este documento — verificado contra la
fuente real del design system (`_ds/modernist-*/styles.css`, leído vía DesignSync el mismo día).
Como los ~40 templates del portal/backoffice consumen estos tokens `--at-*` por clase compartida
(`.at-card`, `.btn-at-accent`, `.form-control-at`, `.badge-status`, etc.) en vez de hex sueltos,
este único cambio de **valores** de token actualiza la apariencia de las 42 pantallas existentes
de una sola pasada — colores, tipografía y radios, sin tocar el markup de cada template uno por
uno. Los **primitivos v3** (`--navy-*`, `--amber-*`, `--slate-*`) se conservaron como **alias**
de los nuevos `--sky-*`/`--coral-*`/`--neutral-*` (mismo valor, nombre viejo) — evita romper los
~16 templates que todavía referencian el primitivo directo en un `style=""` inline; renombrarlos
de verdad en cada template queda como limpieza futura, no bloqueante.

**Backoffice migrado a tabs superiores (2026-07-19).** El sidebar de Agente/Administrador
(`#at-sidebar`) se eliminó de `layout_app.html` y se reemplazó por la franja de tabs horizontal del
canvas importado (`#at-module-tabs` + `#at-submodule-tabs`, tabs invertidos con fondo oscuro cuando
están activos). Cambio hecho enteramente en el shell compartido (`app/shared/templates/layout_app.html`)
más CSS — ningún template de contenido de backoffice necesitó tocarse porque todos solo llenan
`{% block content %}`. Reutiliza sin cambios la estructura RBAC-filtrada de `app/shared/nav.py`
(`nav_modulos`). Verificado en navegador real (Seguridad/3 items, Facturación/2 items, Vuelos/1
item) y con la suite completa de tests (237/237, sin regresión). El sidebar de pasajero
(`#at-sidebar-pasajero`) no cambió — Modernist no define navegación de portal, solo de backoffice.

**Lo que NO se tocó en esta pasada (deliberado, no un olvido):**

1. **Botones no se forzaron a flush-left.** Modernist pide que la etiqueta de un botón ancho nunca
   se centre. Los CTAs de conversión de este proyecto (buscar, agregar al carrito, confirmar
   compra) usan `w-100 justify-content-center` (utilidad de Bootstrap) en varios templates — se
   mantiene centrado deliberadamente: para un flujo de reserva/pago, un CTA centrado es una
   convención de e-commerce más reconocible que la afectación flush-left de Modernist, y forzar el
   cambio habría requerido tocar el markup de cada CTA en cada template. Es la misma clase de
   desviación consciente que ya documenta la sección de Radios.
2. **Los íconos siguen siendo Bootstrap Icons**, no Lucide (que pide el readme de Modernist) — ya
   estaban integrados en las ~42 pantallas antes de esta migración; cambiar de librería de íconos
   es un costo alto para un beneficio bajo, no es donde vale la pena gastar el rediseño.
3. **Los primitivos v3 no se renombraron en los templates** que los usan inline (ver arriba) — el
   alias los deja funcionando con los valores nuevos, pero técnicamente siguen con el nombre viejo.

**Reglas para seguir construyendo sobre v4:**

1. **Los tokens semánticos no cambian de nombre**, solo de valor: `--at-primary`, `--at-accent`,
   `--at-surface`, `--at-bg`, `--at-muted`, `--at-border`, `--at-text` — nunca un hex directo en un
   template (refuerza constitución B3/J3). Para primitivos, usar los nombres v4 (`--sky-*`,
   `--coral-*`, `--neutral-*`) en código nuevo — los alias v3 son solo compatibilidad.
2. **Decidir densidad, no color, según el contexto.** Portal de pasajero → cards `.at-card`,
   `.at-flight-card`, radio `--at-r-lg`/`--at-r-xl`, layout de grid modular con reglas de 2px.
   Backoffice → `.at-table`, radio `--at-r-sm`/`--at-r-md`, casi sin sombra (los tabs invertidos
   siguen pendientes, ver punto 1 arriba).
3. **Estado nunca solo por color** (constitución J7): todo `.tag`/badge de estado lleva ícono +
   texto, nunca un tag de color solo — Modernist no lo exige por defecto, pero la constitución sí.
4. Si una pantalla nueva necesita un color que no existe en la escala actual, es señal de que falta
   un rol semántico, no de que hay que inventar un hex suelto — agregarlo acá primero.

## Paleta

| Token semántico | Primitivo | Hex | Rol |
|---|---|---|---|
| `--at-primary` | `--sky-800` | `#0072CE` | **Sky vívido.** Botón principal, links, foco, identidad de marca — se mantiene de v3, es el ancla "fría/confianza" que exige J3 |
| `--at-primary-hover` | `--sky-900` | `#123A63` | Hover/pressed del primario |
| `--at-primary-tint` | `--sky-100` | `#DCEEFB` | Fondos de chip/tinte sobre el primario |
| `--at-accent` | `--coral-600` | `#ec3013` | **Rojo Modernist.** Badges de acción, CTA secundario de conversión, foco de componentes Modernist (`:focus-visible`) |
| `--at-accent-hover` | `--coral-700` | `#ae1800` | Hover/pressed del accent; también texto de párrafo sobre fondo claro (el accent base falla AA en texto pequeño) |
| `--at-accent-tint` | `--coral-100` | `#fff2ef` | Fondo de tag/badge de accent |
| `--at-bg` (backoffice) | `--neutral-100` | `#f8f4f4` | Fondo global de backoffice — gris cálido neutro de Modernist, reemplaza el `--slate-50` de v3 |
| `--at-bg` (portal) | — | `#F5F9FC` | Portal conserva el tinte Sky Mist de v3 (blanco con mínima tintura de cielo) — es donde más pesa la identidad "confianza" de J1 |
| `--at-surface` | `--neutral-200` | `#eae7e7` | Fondo de card/superficie elevada |
| `--at-border` / `--at-divider` | `--neutral-400` (mezcla 40% sobre texto) | `color-mix(#201e1d 40%, transparent)` | Regla estructural de 2px (secciones) y borde de 1px (filas, inputs) |
| `--at-text` | `--neutral-900` | `#201e1d` | Texto principal — reemplaza `--navy-950` como ink |
| `--at-muted` | `--neutral-700` (mezcla 55-60% sobre texto) | `color-mix(#201e1d 55%, transparent)` | Texto secundario, metadata |
| `--red-600` / `--green-600` | — | `#dc3545` / `#198754` | Sin cambios — destructivo / éxito, fuera de la paleta de marca |

**Rampa completa del accent** (misma que Modernist, generada en OKLCH — reutilizar los escalones,
no inventar tintes con `color-mix` ad-hoc): `100 #fff2ef · 200 #ffe0d9 · 300 #ffc4b8 · 400 #ff9783 ·
500 #ff563c · 600 #dd2b0f (base) · 700 #ae1800 · 800 #7c1405 · 900 #4d170e`. Usar 100–300 para
tintes/hover suaves, 600 como base del rol, 700–900 para texto sobre fondo tintado y estados
presionados — igual criterio que ya usaba v3, ahora aplicado a la rampa Modernist.

**Rampa completa del neutral** (fondo/superficie/texto de todo el sistema, sustituye la escala
`--slate-*` de v3): `100 #f8f4f4 · 200 #eae7e7 · 300 #d7d3d3 · 400 #bab6b6 · 500 #9b9797 · 600
#7d7979 · 700 #605d5d · 800 #444141 · 900 #2d2b2b`.

La rampa del primario (Sky) no cambia respecto a v3 — sigue viva en `aerotrack.css` bajo los
nombres `--navy-800/900/500/300/...`; se renombran acá a `--sky-*` para que el nombre primitivo
combine con el resto de la paleta v4, pero el valor hex es idéntico. **Pendiente de código:**
renombrar las variables en `aerotrack.css` cuando se migre cada pantalla — no se hace en este
documento, que es solo la especificación.

Cada par texto/fondo debe verificarse contra WCAG AA (4.5:1) al implementar — Modernist ya diseñó
su rampa de accent para ≥3:1 contra el fondo (suficiente para íconos/chrome, no para texto de
párrafo, de ahí la regla de usar el escalón 700 en texto). Verificar puntualmente el resto de
pares al construir cada pantalla, igual que exigía v3.

## Tipografía

| Rol | Familia | Uso |
|---|---|---|
| Display + Texto (`--font-heading` / `--font-body`) | **Archivo** (pesos 400/600/800) | H1–H6, body, formularios, tablas, botones — v4 unifica en una sola familia (Modernist), reemplaza el par Manrope/Inter de v3 |
| Tabular (`--font-mono`) | JetBrains Mono | Precios en columna, PNR, timestamps, IDs de auditoría — `font-variant-numeric: tabular-nums`. **Se conserva de v3**: Modernist no define un rol monoespaciado y la constitución (REG-J4) lo exige explícitamente para cifras en columna — es la única adición fuera del design system importado |

Escala de tamaño (de Modernist, adoptada tal cual): H1 42px · H2 32px · H3 25px · H4 20px · H5
16px · H6 13px (mayúsculas, `letter-spacing: 0.08em`). Peso de heading 800 (`--font-heading-weight`),
`letter-spacing: -0.015em`, `line-height: 1.12`. Body 15px/1.55, peso 400.

## Radios (bordes) — la desviación deliberada frente a Modernist

Modernist define `--radius-sm/md/lg: 0px` a propósito. v4 los reemplaza por una escala suave —
esta es la única sección donde AeroTrack Travel se aparta explícitamente de la guía del design
system importado, por pedido directo del cliente:

| Token | Valor | Uso |
|---|---|---|
| `--at-r-sm` | `6px` | Backoffice: inputs, botones, tags pequeños |
| `--at-r-md` | `10px` | Backoffice: cards, contenedores de tabla; portal: elementos secundarios |
| `--at-r-lg` | `16px` | Portal: cards de resultado, diálogos |
| `--at-r-xl` | `24px` | Portal: panel del buscador (hero), cards de feature grandes |

Las reglas gruesas de 2px (`--at-divider`) siguen siendo el recurso estructural principal —
Modernist las usa en vez de sombra para separar secciones, y eso **no cambia**: solo se suaviza la
esquina de los contenedores individuales (inputs, cards, botones), nunca se agrega sombra donde
Modernist usa una regla.

## Estructura y componentes (adoptados de Modernist, referencia: `components/*.html` del proyecto de diseño)

- **Reglas de 2px** (`border-bottom: 2px solid var(--at-border)`) para separar secciones mayores —
  nav, cabecera de tabla, tabs de backoffice, franjas del checkout. Reglas de 1px para filas
  dentro de una lista (notificaciones, ítems de carrito, log de auditoría).
- **Botones** (`.btn` + `.btn-primary/-secondary/-ghost/-icon/-block`): label **flush-left**, nunca
  centrado, salvo que el botón sea de ancho ajustado al contenido — detalle propio de Modernist que
  se conserva. Primario = fondo `--at-accent` (rojo) para conversión; para acciones de navegación
  no transaccional (login, "Continuar" sin cargo de dinero) usar `--at-primary` (azul) como fondo
  del botón primario — la constitución J3 reserva el accent para conversión con dinero de por
  medio, Modernist no distinguía esto porque solo tenía un color.
- **Cards** (`.card` + `.card-kicker/-title/-body/-meta`, `.elev-sm/md/lg`): patrón único para
  stat tiles de backoffice, cards de resultado de búsqueda y resúmenes de checkout — mismo
  componente, distinta densidad de contenido.
- **Tags/badges** (`.tag` + `.tag-accent/-accent-2/-neutral/-outline`): Modernist los deja
  color+texto; AeroTrack Travel **añade ícono obligatorio en todo tag de estado** (retrasado,
  cancelado, riesgo alto/bajo, disrupción activa) — refuerza J7, no está en el design system
  importado por defecto.
- **Control segmentado** (`.seg` + `.seg-opt`): toggle Pasajero/Administrador en la nav, tabs de
  modo login/registro, sub-tabs dentro de un módulo (ej. Vuelos y Reservas → Catálogo / Reservas).
- **Tabs de backoffice** (franja superior, botón activo con fondo `--at-text` invertido —
  texto claro sobre fondo oscuro): patrón para navegar entre secciones de Administrador (Seguridad,
  Usuarios, Pasajeros, Vuelos y Reservas, Disrupciones, Facturación, Marketing y Ofertas, Asistente
  IA, Centro de Ayuda, Dashboard) sin sidebar — implementado en `layout_app.html` (2026-07-19),
  `#at-module-tabs` con sub-tabs opcionales en `#at-submodule-tabs` cuando el módulo activo tiene
  más de una sección.
- **Tablas** (`.table`): encabezado en mayúsculas 11px con `letter-spacing`, regla de 2px bajo el
  encabezado, filas con regla de 1px, hover con tinte sutil de `--at-text` al 4%.
- **Chat flotante del Asistente IA**: panel fijo `bottom:0; right:24px; width:360px`, con borde de
  2px (no sombra sola), header con regla de 2px, burbujas de mensaje alineadas por rol — patrón
  confirmado en el canvas para CU-O106–O111.
- **Diálogo/modal** (`.dialog-backdrop` + `.dialog`): usar `--at-r-lg` en vez del `--radius-lg: 0`
  de Modernist, mismo backdrop semitransparente sobre `--neutral-900`.

## Fondo — diferenciador portal vs. backoffice

- Backoffice (`--at-bg` global): `#f8f4f4` (Modernist `--color-neutral-100`) — gris cálido neutro,
  reemplaza el `--slate-50` de v3.
- Portal (`#portal-main`, override local): `#F5F9FC` (Sky Mist) — **se conserva de v3**, sin
  cambios. Es la única superficie donde el tinte azul de marca vive fuera de botones/links; se
  mantiene deliberadamente para no perder toda presencia de "confianza" fría en el portal al
  adoptar la paleta cálida de Modernist.

## Imágenes — grayscale de Modernist adaptado, no copiado literal

Modernist prescribe fotografía 100% blanco y negro (`.grayscale`, sin excepción — "Do not tint or
colorize imagery"). AeroTrack Travel adapta esto en vez de copiarlo literal: mantiene el
tratamiento en escala de grises como base (`filter: grayscale(1)`, confirmado en el hero de Inicio
y las cards de destino del canvas importado) pero conserva el **overlay de scrim en tonos ink/sky**
que ya usa `login_hero.jpg` sobre las fotos reales — la foto se ve en blanco y negro, el overlay
que la enmarca lleva el degradado de marca (`--at-text` → `--at-primary`, no gris puro). Esto es
un punto medio deliberado: honra el "nada de color en la fotografía" de Modernist sin perder toda
seña de marca en las imágenes grandes (hero, destinos, mapa de disrupción).

## Pendiente de este documento

- **Migración de código:** `aerotrack.css` y las pantallas ya construidas (login, registro,
  buscar/detalle de vuelo, checkout, detalle de reserva) siguen en v3 — se migran a v4 pantalla por
  pantalla cuando se retome cada módulo, nunca a medias.
- **Backoffice:** la navegación (tabs superiores) ya está migrada; el contenido de cada pantalla de
  Administrador (tablas, cards de stat, formularios) sigue en v3 dentro de `{% block content %}` —
  el canvas importado cubre Seguridad, Usuarios, Pasajeros, Vuelos y Reservas, Disrupciones,
  Facturación, Marketing y Ofertas, Asistente IA, Centro de Ayuda y Dashboard financiero como
  referencia directa para cuando se migre cada una.
- **Iconografía:** Modernist recomienda Lucide (`lucide.dev`) en todo el sistema — no había una
  librería de íconos fijada en v3; adoptar Lucide para consistencia al migrar.
- Si se suma fotografía real adicional de destino, documentar acá las fuentes/licencias usadas
  (nota heredada de v3, sigue pendiente).
