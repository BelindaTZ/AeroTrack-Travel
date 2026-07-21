# Especificación Operativa — Paquetes

**Módulo:** Paquetes
**Prefijo:** PAQ
**Código fuente:** `app/paquetes/` *(no existe todavía)*
**Casos de uso cubiertos:** CU-O76 (Construir paquete seleccionando componentes), CU-O77 (Ver resumen de paquete con desglose de ahorro), CU-O78 (Cambiar componente individual del paquete), CU-O79 (Ver condiciones y política de cancelación por componente), CU-O80 (Agregar traslado aeropuerto al paquete)
**Actor:** Pasajero

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. **Este módulo no tiene catálogo propio ni fuente externa** — a diferencia de Vuelos/Hoteles/Autos/Actividades/Cruceros, un paquete **es** una reserva con ≥2 tipos de producto distintos en `reserva_items` (`reservas.es_paquete = true`, dbml v3). Por eso **depende por completo** de la migración `reserva_items` documentada en `reservas-spec.md` (no implementada todavía) y de que Vuelos/Hoteles/Autos/Actividades ya tengan su selección real disponible.
>
> **Paquetes es, por diseño, una regla de negocio 100% propia de la agencia** (confirmado 2026-07-18): a diferencia de las 5 verticales de producto, ningún proveedor externo "vende paquetes" — AeroTrack Travel compone el paquete combinando inventario real de otros módulos y aplica su propio descuento comercial (`tipos_paquete_descuento`, configurado vía CU-T14, `specs/tactico/paquetes/`). No hay tabla de catálogo, API externa, ni `fuentes_datos_externas` asociada a este módulo — es intencional, no un hueco. Ver RN-PAQ-004 abajo para cómo ese descuento se reconcilia con la comisión real que se le paga a cada proveedor.

---

## Funcionalidad 1: Construir paquete (CU-O76)

### RF-PAQ-001 — Construir paquete seleccionando componentes
El sistema debe permitir a un pasajero construir un paquete combinando: vuelo + hotel (ambos **obligatorios**) y, opcionalmente, auto y/o actividad — reutilizando la búsqueda/selección real de cada módulo (`vuelos-spec.md` CU-O17/O18, `hoteles-spec.md` CU-O57, `autos-spec.md` CU-O64, `actividades-spec.md` CU-O69), no una búsqueda propia duplicada. Cada componente elegido se acumula como una fila `reserva_items` pendiente de confirmar; cuando el paquete tiene al menos vuelo+hotel, `reservas.es_paquete` pasa a `true`.

### RN-PAQ-001 — Vuelo y hotel son obligatorios; auto y actividad son opcionales
Ningún paquete se considera válido sin al menos un componente de vuelo y uno de hotel. Auto y actividad pueden agregarse en cualquier combinación adicional, incluyendo ninguno de los dos.

---

## Funcionalidad 2: Ver resumen con desglose de ahorro (CU-O77)

### RF-PAQ-002 — Ver resumen de paquete con desglose de ahorro vs. reserva por separado
El sistema debe mostrar, antes de confirmar, el precio de cada componente si se reservara por separado, la suma total sin descuento, el porcentaje de descuento aplicable según la combinación exacta de tipos de producto (`tipos_paquete_descuento.combinacion`, ej. "vuelo+hotel", "vuelo+hotel+auto") y el precio final del paquete — transparencia total de dónde sale el ahorro (REG-G2), nunca solo un número final sin desglose.

### RN-PAQ-002 — El descuento se copia al confirmar, no se recalcula después
`reservas.descuento_paquete_pct` se copia del valor vigente en `tipos_paquete_descuento` al momento del checkout — si la configuración cambia después (CU-T14), los paquetes ya confirmados conservan el porcentaje con el que se vendieron.

---

## Funcionalidad 3: Cambiar componente individual (CU-O78)

### RF-PAQ-003 — Cambiar componente individual del paquete sin reiniciar el flujo
El sistema debe permitir, mientras el paquete no esté confirmado, reemplazar un componente individual (p. ej. cambiar el hotel elegido) sin perder los demás componentes ya seleccionados ni obligar a reiniciar la construcción desde cero (REG-J10 — navegación sin pérdida de estado).

---

## Funcionalidad 4: Ver condiciones y política de cancelación por componente (CU-O79)

### RF-PAQ-004 — Ver condiciones y política de cancelación por cada componente del paquete
El sistema debe mostrar, para cada componente del paquete, su propia política de cancelación real (la de vuelo vía `niveles_tarifa`, la de hotel vía `hoteles_tarifas.reembolsable`/`cancelacion_hasta`, etc. — cada módulo dueño de su dato, este módulo solo las agrega en una sola vista) — nunca una política única simplificada para todo el paquete, porque cada componente puede tener condiciones distintas.

---

## Funcionalidad 5: Agregar traslado aeropuerto (CU-O80)

### RF-PAQ-005 — Agregar traslado aeropuerto al paquete
El sistema debe permitir agregar un traslado aeropuerto como extra del paquete, registrado en `reserva_extras` con `tipo = traslado_aeropuerto` (mismo mecanismo que equipaje/asiento/seguro, ver `reservas-spec.md`) — no una tabla ni catálogo propio.

---

## Reglas de negocio

- **RN-PAQ-001** — *(Funcionalidad 1)* Vuelo y hotel son obligatorios; auto y actividad opcionales.
- **RN-PAQ-002** — *(Funcionalidad 2)* El descuento se copia al checkout, no se recalcula retroactivamente.
- **RN-PAQ-003** — Toda mutación de este módulo (construir, cambiar componente, confirmar) se audita (CU-O41).
- **RN-PAQ-004** — *(Nueva 2026-07-18, resuelve una ambigüedad real del esquema)* **El descuento de paquete lo absorbe exclusivamente la agencia — nunca reduce la comisión pactada con ningún proveedor individual.** Cada `reserva_items.precio_final` conserva el precio real/de lista del componente (el mismo que tendría si se reservara suelto); `reservas.descuento_paquete_pct` se aplica una sola vez, a nivel de cabecera, sobre la suma de los componentes, para llegar a `reservas.total_pagar`. Esto es coherente con el diseño del dbml v3 (el descuento vive en `reservas`, no en `reserva_items`) y es lo que permite que `comisiones` (`facturacion-spec.md`, RF-FAC-003) siga calculándose sobre el precio real de cada componente sin ningún ajuste — el "costo" del descuento de paquete lo paga el cargo de servicio/margen propio de la agencia, no el proveedor. Ver también `facturacion-spec.md` RN-FAC-007.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `POST /paquetes/iniciar` | Cookie JWT, componente de vuelo seleccionado | Paquete en construcción (borrador), redirige a seleccionar hotel |
| `POST /paquetes/{id}/agregar-componente` | Cookie JWT, tipo de componente, selección | Componente agregado al paquete en construcción |
| `PUT /paquetes/{id}/componente/{item_id}` | Cookie JWT, nueva selección | Componente reemplazado, resto del paquete intacto |
| `GET /paquetes/{id}/resumen` | Cookie JWT | HTML/JSON con desglose de ahorro y condiciones por componente |
| `POST /paquetes/{id}/traslado-aeropuerto` | Cookie JWT, detalle del traslado | Extra agregado al paquete |
| `POST /paquetes/{id}/confirmar` | Cookie JWT | `<<include>>` hacia CU-O21 (Reservas) con `es_paquete = true` |

---

## Historias de usuario

- **HU-PAQ-01:** Como pasajero, quiero construir un paquete combinando vuelo, hotel y opcionalmente auto/actividad, para planear mi viaje completo en un solo flujo.
- **HU-PAQ-02:** Como pasajero, quiero ver cuánto ahorro exactamente vs. reservar cada cosa por separado, para decidir con información real.
- **HU-PAQ-03:** Como pasajero, quiero cambiar un componente sin perder los demás, para ajustar mi paquete sin empezar de nuevo.
- **HU-PAQ-04:** Como pasajero, quiero ver la política de cancelación de cada componente por separado, para saber exactamente qué puedo cambiar y qué no.
- **HU-PAQ-05:** Como pasajero, quiero agregar un traslado al aeropuerto, para completar mi logística de viaje en la misma reserva.

---

## Objetivo

Permitir componer un viaje completo (vuelo + hotel + opcionalmente auto/actividad) con ahorro real y transparente frente a reservar cada cosa por separado, reutilizando la selección real de cada módulo dueño de su producto — nunca un catálogo ni una política de cancelación propia inventada por este módulo.

---

## Escenarios

### Camino feliz
1. Un pasajero selecciona un vuelo (CU-O17/O18) e inicia un paquete (CU-O76).
2. Agrega un hotel (obligatorio) y una actividad (opcional).
3. Ve el resumen con el ahorro exacto vs. reservar cada cosa por separado (CU-O77).
4. Decide cambiar el hotel elegido sin perder el vuelo ni la actividad ya elegidos (CU-O78).
5. Revisa la política de cancelación de cada componente (CU-O79) y agrega un traslado al aeropuerto (CU-O80).
6. Confirma — el paquete se convierte en una reserva real (`reservas-spec.md`, CU-O21) con `es_paquete = true`.

### Manejo de errores
- **Intentar confirmar sin hotel o sin vuelo:** se bloquea con mensaje explícito (RN-PAQ-001).
- **Configuración de descuento cambia mientras el pasajero está construyendo el paquete:** el precio final se recalcula con el valor vigente hasta el momento de la confirmación real, no con un valor cacheado desde el inicio de la construcción.

---

## Criterios de aceptación

- **CU-O76:** Dado que un pasajero selecciona vuelo y hotel (obligatorios) y opcionalmente auto/actividad, cuando construye el paquete, entonces `reservas.es_paquete` queda `true` con los componentes acumulados.
- **CU-O77:** Dado que un paquete tiene sus componentes seleccionados, cuando el pasajero ve el resumen, entonces ve el desglose completo de precio por componente, el descuento aplicable y el precio final.
- **CU-O78:** Dado que un paquete no está confirmado, cuando el pasajero reemplaza un componente, entonces los demás componentes permanecen intactos.
- **CU-O79:** Dado que un paquete tiene componentes seleccionados, cuando el pasajero consulta condiciones, entonces ve la política de cancelación real de cada componente por separado.
- **CU-O80:** Dado que un paquete está en construcción, cuando el pasajero agrega un traslado al aeropuerto, entonces queda registrado como extra del paquete.

---

## Dependencias

- **Vuelos, Hoteles, Autos, Actividades:** fuente real de cada componente — este módulo no duplica ninguna búsqueda ni catálogo.
- **Reservas:** `reserva_items` (migración pendiente) es la estructura de datos completa de este módulo; CU-O76 confirma hacia CU-O21.
- **Este módulo, nivel Táctico (`specs/tactico/paquetes/`):** CU-T14 configura el `porcentaje_descuento` que consume RF-PAQ-002.
- **Seguridad:** sesión (CU-O42), auditoría (CU-O41).
- **Facturación:** RN-PAQ-004/RN-FAC-007 — el descuento de paquete nunca reduce la comisión calculada por componente; ambos módulos deben mantener esta regla en sincronía si cambia.

---

## Casos de uso relacionados

- CU-O17/O18 (Vuelos), CU-O57 (Hoteles), CU-O64 (Autos), CU-O69 (Actividades) — fuente de cada componente.
- CU-O21 (Crear reserva, Reservas) — destino final de la confirmación de un paquete.
- CU-O34 (Registrar comisión por reserva, Facturación) — se calcula por componente sobre el precio real, sin el descuento de paquete (RN-PAQ-004).
- CU-T14 (Configurar % de descuento por tipo de paquete, este módulo, Táctico) — condiciona RF-PAQ-002.
- CU-T15 (Ver reporte de combinaciones más vendidas, este módulo, Táctico) — consume paquetes confirmados.

---

## Fuera de alcance

- Catálogo o búsqueda propia de "paquetes prearmados" — todo paquete se construye a demanda combinando la selección real de cada módulo, no existe un catálogo de paquetes preconfigurados en este catálogo de CU.
- Descuentos combinables con cupones de Ofertas y Promociones — es una regla de negocio pendiente de definir (ver QP-18 en `analisis-cus-completo.md`), no asumida en esta ronda.
- Paquetes con más de un componente del mismo tipo (ej. 2 hoteles en el mismo paquete) — el catálogo de CU no lo contempla; un paquete tiene como máximo un componente por tipo de producto.
