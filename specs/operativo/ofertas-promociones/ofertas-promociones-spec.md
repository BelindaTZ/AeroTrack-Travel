# Especificación Operativa — Ofertas y Promociones

**Módulo:** Ofertas y Promociones
**Prefijo:** OFE
**Código fuente:** `app/ofertas/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O101 (Ver ofertas destacadas por producto), CU-O102 (Ver destinos populares desde el origen del pasajero), CU-O103 (Aplicar cupón de descuento en checkout), CU-O104 (Suscribirse al newsletter de ofertas), CU-O105 (Ver términos y condiciones de una promoción vigente)
**Actor:** Pasajero

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. **CU-O102 no tiene tabla propia** en el dbml v3 (a diferencia de CU-O101/`ofertas_destacadas`) — no existe una tabla `destinos_populares` curada. Se documenta aquí como una consulta agregada sobre datos reales de otros módulos (búsquedas/reservas), no como un catálogo editorial; ver RF-OFE-002 y Fuera de alcance.

---

## Funcionalidad 1: Ver ofertas destacadas (CU-O101)

### RF-OFE-001 — Ver ofertas destacadas por producto
El sistema debe mostrar ofertas destacadas vigentes (`ofertas_destacadas.activa = true` y dentro de `fecha_inicio`/`fecha_fin`) para cualquiera de las 6 verticales de producto, cada una apuntando a un ítem real del catálogo correspondiente (`producto_ref`, resuelto según `tipo_producto`).

---

## Funcionalidad 2: Ver destinos populares (CU-O102)

### RF-OFE-002 — Ver destinos populares desde el origen del pasajero
El sistema debe mostrar los destinos con mayor volumen de búsquedas o reservas reales desde el origen habitual del pasajero (inferido de `busquedas_recientes`/`reservas` si está autenticado, o desde el origen declarado en la búsqueda actual si no). **No es un catálogo editorial** — se calcula por agregación sobre datos reales de uso, no se cura manualmente destino por destino.

### RN-OFE-001 — Destinos populares nunca se presentan como oferta editorial
A diferencia de CU-O101 (curado por Administrador vía `ofertas_destacadas`), CU-O102 es puramente estadístico — el sistema no debe mezclar ambos conceptos ni dar a entender que "destino popular" implica descuento o curación humana.

---

## Funcionalidad 3: Aplicar cupón de descuento (CU-O103)

`<<extend>>` de CU-O96/O21/O22 (checkout, `carrito-spec.md`/`reservas-spec.md`) — condicional, solo si el pasajero ingresa un código.

### RF-OFE-003 — Aplicar cupón de descuento en checkout
El sistema debe permitir, en el checkout, ingresar un código de cupón (`cupones_descuento.codigo`) y validarlo: vigente (`fecha_expiracion`), activo, con usos disponibles (`usos_actuales < usos_maximos` cuando `usos_maximos` no es nulo), aplicable al producto de la reserva (`producto_aplicable`, nulo = aplica a cualquiera) y, **si la reserva es un paquete** (`reservas.es_paquete = true`), permitido por la regla de acumulación vigente (RN-OFE-003). Si es válido, registra el canje en `cupones_uso` (monto exacto descontado) y aplica el descuento al total.

### RN-OFE-002 — Un cupón nunca se aplica dos veces a la misma reserva
`cupones_uso` es la fuente de verdad de trazabilidad de canje — antes de aplicar un cupón, el sistema verifica que esa combinación cupón-reserva no exista ya.

### RN-OFE-003 — Interacción con descuento de paquete, resuelta como regla configurable (CU-T44)
*(Corregido 2026-07-18 — ya no es una decisión pendiente.)* Si un cupón se aplica sobre una reserva que ya es un paquete con su propio descuento (`reservas.descuento_paquete_pct`, `paquetes-spec.md`), el sistema evalúa: (1) si `cupones_descuento.acumulable_con_paquete` no es nulo para ese cupón, usa ese valor; (2) si es nulo, usa el default global (`configuracion_sistema`, clave `cupones.acumulable_con_paquete_default`, configurado vía CU-T44 en `specs/tactico/ofertas-promociones/`). Si la regla resultante es "no acumulable", el cupón se rechaza con un mensaje explícito indicando que no aplica sobre paquetes, nunca se aplica silenciosamente ignorando uno de los dos descuentos.

---

## Funcionalidad 4: Suscribirse al newsletter (CU-O104)

### RF-OFE-004 — Suscribirse al newsletter de ofertas
El sistema debe permitir suscribirse al newsletter con solo un email, sin necesidad de cuenta (`newsletter_suscripciones.pasajero_id` nullable) — si el visitante está autenticado, se asocia automáticamente a su perfil.

---

## Funcionalidad 5: Ver términos y condiciones (CU-O105)

Extiende a CU-O101/O103 — información complementaria, no un flujo independiente.

### RF-OFE-005 — Ver términos y condiciones de una promoción vigente
El sistema debe mostrar, para una oferta destacada o un cupón, sus términos y condiciones completos antes de que el pasajero decida aplicarlos.

---

## Reglas de negocio

- **RN-OFE-001** — *(Funcionalidad 2)* Destinos populares nunca se presentan como curación editorial.
- **RN-OFE-002** — *(Funcionalidad 3)* Un cupón nunca se aplica dos veces a la misma reserva.
- **RN-OFE-003** — *(Funcionalidad 3)* Acumulación cupón + descuento de paquete es una regla configurable (default global + excepción por cupón, CU-T44), evaluada solo cuando la reserva es un paquete.
- **RN-OFE-004** — Toda mutación de este módulo (canje de cupón, suscripción) se audita (CU-O41).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /ofertas` | Filtro opcional de producto | HTML/JSON con ofertas destacadas vigentes |
| `GET /destinos-populares` | Origen (inferido o declarado) | HTML/JSON con destinos ordenados por volumen real |
| `POST /checkout/aplicar-cupon` | Cookie JWT (si aplica), código de cupón, reserva/carrito en curso | Descuento aplicado o mensaje de rechazo (expirado, agotado, no aplicable) |
| `POST /newsletter/suscribirse` | Email (Cookie JWT opcional) | Suscripción creada |
| `GET /ofertas/{id}/terminos` | ID de oferta o cupón | HTML/JSON con términos y condiciones |

---

## Historias de usuario

- **HU-OFE-01:** Como pasajero, quiero ver ofertas destacadas por producto, para descubrir promociones vigentes.
- **HU-OFE-02:** Como pasajero, quiero ver destinos populares desde mi origen, para inspirarme con opciones reales de otros viajeros.
- **HU-OFE-03:** Como pasajero, quiero aplicar un cupón de descuento en mi checkout, para pagar menos si tengo un código válido.
- **HU-OFE-04:** Como visitante, quiero suscribirme al newsletter sin crear cuenta, para enterarme de futuras promociones.
- **HU-OFE-05:** Como pasajero, quiero ver los términos y condiciones de una promoción antes de aplicarla, para saber exactamente qué estoy aceptando.

---

## Objetivo

Dar visibilidad de promociones reales y vigentes, distinguir claramente entre curación editorial (ofertas destacadas) y estadística de uso real (destinos populares), y aplicar cupones de forma segura y trazable sin doble canje.

---

## Escenarios

### Camino feliz
1. Un pasajero ve ofertas destacadas de vuelos (CU-O101) y destinos populares desde su origen (CU-O102).
2. Se suscribe al newsletter (CU-O104) sin necesidad de cuenta.
3. En su checkout, ingresa un cupón válido (CU-O103); el descuento se aplica y queda registrado en `cupones_uso`.
4. Antes de confirmar, revisa los términos del cupón (CU-O105).

### Manejo de errores
- **Cupón expirado, agotado o no aplicable al producto:** se rechaza con mensaje específico de la razón.
- **Intento de reaplicar un cupón ya canjeado en la misma reserva:** se bloquea (RN-OFE-002).
- **Cupón sobre un paquete con descuento propio:** se resuelve según la regla configurada (excepción del cupón, o default global si no tiene) — si el resultado es "no acumulable", se rechaza con mensaje explícito (RN-OFE-003).

---

## Criterios de aceptación

- **CU-O101:** Dado que existen ofertas destacadas vigentes, cuando un pasajero las consulta, entonces las ve filtrables por producto.
- **CU-O102:** Dado que existen búsquedas/reservas reales desde un origen, cuando el pasajero consulta destinos populares, entonces ve los de mayor volumen real, sin mezclarlos con ofertas curadas.
- **CU-O103:** Dado que un pasajero ingresa un cupón válido en checkout, cuando lo aplica, entonces el descuento se refleja en el total y queda registrado en `cupones_uso`; si es inválido, se rechaza con el motivo.
- **CU-O104:** Dado que un visitante ingresa un email, cuando se suscribe, entonces queda registrado en `newsletter_suscripciones`.
- **CU-O105:** Dado que un pasajero consulta una oferta o cupón, cuando accede a sus términos, entonces ve el texto completo antes de aplicarlo.

---

## Dependencias

- **Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes:** fuente de `producto_ref` para ofertas destacadas y de los datos de uso real para destinos populares.
- **Carrito/Reservas:** CU-O103 es `<<extend>>` de su checkout.
- **Seguridad:** sesión (CU-O42, opcional para newsletter/destinos, obligatoria si se asocia a perfil); auditoría (CU-O41).
- **Este módulo, nivel Táctico (`specs/tactico/ofertas-promociones/`):** CU-T30 gestiona los cupones que consume RF-OFE-003; CU-T31 gestiona campañas que consumen `newsletter_suscripciones`; CU-T44 gestiona la regla de acumulación con paquete que también consume RF-OFE-003.
- **Paquetes:** RN-OFE-003 lee `reservas.es_paquete`/`descuento_paquete_pct` para decidir si la regla de acumulación aplica.

---

## Casos de uso relacionados

- CU-O96/O21/O22 (Checkout, Carrito/Reservas) — CU-O103 los extiende.
- CU-O76 (Construir paquete, Paquetes) — origen de `reservas.es_paquete`, condición de RN-OFE-003.
- CU-T14 (Configurar % de descuento por tipo de paquete, Paquetes) — la otra mitad de la regla que CU-T44 reconcilia.
- CU-T30 (Crear y gestionar cupones, este módulo, Táctico) — dueño de `cupones_descuento`.
- CU-T31 (Configurar y enviar campaña de email, este módulo, Táctico) — consume `newsletter_suscripciones`.
- CU-T32 (Ver reporte de cupones usados, este módulo, Táctico) — consume `cupones_uso`.
- CU-T44 (Configurar acumulación de cupones con descuento de paquete, este módulo, Táctico) — condiciona RF-OFE-003, resuelve QP-18.

---

## Fuera de alcance

- Tabla o catálogo editorial de "destinos populares" — es una consulta agregada sobre datos reales, no un contenido curado (ver RN-OFE-001).
- Segmentación avanzada de ofertas destacadas por perfil de pasajero (más allá de producto/vigencia) — el esquema actual no lo soporta.
