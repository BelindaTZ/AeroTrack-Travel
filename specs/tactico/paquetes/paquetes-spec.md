# Especificación Táctica — Paquetes

**Módulo:** Paquetes
**Prefijo:** PAQ
**Código fuente:** `app/paquetes/` *(compartido con el nivel Operativo — ver `specs/operativo/paquetes/`)*
**Casos de uso cubiertos:** CU-T14 (Configurar porcentajes de descuento por tipo de paquete), CU-T15 (Ver reporte de combinaciones de paquete más vendidas y margen generado)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0, sin código todavía. CU-T14 es **precondición real** de RF-PAQ-002 (Operativo, el desglose de ahorro lee esta configuración) — mismo caso que CU-T42/T43 en Actividades/Cruceros: implementar junto con esa fase, no después.
>
> **Este CU es la palanca comercial completa de Paquetes** (confirmado 2026-07-18, ver nota al inicio de `specs/operativo/paquetes/paquetes-spec.md`): al no existir ningún proveedor externo de "paquetes", el porcentaje que se configura aquí es el único mecanismo que define cuánto descuento ofrece la agencia — y ese costo lo absorbe siempre el margen propio de AeroTrack Travel, nunca la comisión pactada con cada proveedor (RN-PAQ-004/RN-FAC-007, `facturacion-spec.md`). Por eso el reporte de CU-T15 (Funcionalidad 2) mide "margen generado" con ese significado preciso, no una aproximación.

---

## Funcionalidad 1: Configurar porcentajes de descuento por tipo de paquete (CU-T14)

### RF-PAQ-T01 — Configurar porcentajes de descuento por tipo de paquete
El sistema debe permitir a un Administrador crear y editar combinaciones de paquete (`tipos_paquete_descuento.combinacion`: "vuelo+hotel", "vuelo+hotel+auto", "vuelo+hotel+actividad", "vuelo+hotel+auto+actividad") con su porcentaje de descuento, y activar/desactivar cada combinación. El campo `combinacion` es texto controlado por esta UI, no un enum cerrado en el esquema — permite agregar combinaciones nuevas sin migración.

### RN-PAQ-T01 — Desactivar una combinación no afecta paquetes ya confirmados
Igual que RN-PAQ-002 (Operativo): desactivar o cambiar el porcentaje de una combinación solo afecta paquetes construidos después del cambio; los ya confirmados conservan su `descuento_paquete_pct` copiado al momento del checkout.

---

## Funcionalidad 2: Ver reporte de combinaciones más vendidas (CU-T15)

### RF-PAQ-T02 — Ver reporte de combinaciones de paquete más vendidas y margen generado
El sistema debe mostrar a un Administrador un reporte de qué combinaciones de paquete (vuelo+hotel, vuelo+hotel+auto, etc.) se venden más, con el número de paquetes confirmados y el margen generado. **"Margen generado" es específicamente el costo comercial del descuento absorbido por la agencia** — la diferencia entre la suma de `reserva_items.precio_final` de todos los componentes (precio real, sin descuento — el mismo que ve Facturación para calcular comisiones, RN-FAC-007) y `reservas.total_pagar` (lo efectivamente cobrado con el descuento de paquete aplicado). No es una medida de rentabilidad neta de la agencia (no resta costos operativos ni compara contra la comisión ganada) — es puramente "cuánto costó, en descuento, generar este volumen de paquetes". Filtrable por período, con filtros instantáneos (REG-J9).

### RN-PAQ-T02 — Solo cuenta paquetes confirmados
Mismo criterio que el resto de los reportes del sistema: solo reservas con `es_paquete = true` en estado `confirmada` o posterior.

---

## Reglas de negocio

- **RN-PAQ-T01** — *(Funcionalidad 1)* Cambios de configuración no afectan paquetes ya confirmados.
- **RN-PAQ-T02** — *(Funcionalidad 2)* Solo paquetes `confirmada` o posterior cuentan en el reporte.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/paquetes/tipos-descuento` | Cookie JWT (Admin), combinación, porcentaje, activo | Tipo de paquete creado/actualizado |
| `GET /backoffice/paquetes/reporte` | Cookie JWT (Admin), filtro de período | HTML/JSON con combinaciones más vendidas y margen generado |

---

## Historias de usuario

- **HU-PAQ-T01:** Como administrador, quiero configurar el porcentaje de descuento por combinación de paquete, para ajustar la estrategia comercial sin tocar código.
- **HU-PAQ-T02:** Como administrador, quiero ver qué combinaciones de paquete se venden más y qué margen generan, para decidir si ajustar el descuento de alguna combinación.

---

## Objetivo

Dar al Administrador control sobre la estrategia de descuento por combinación de paquete y visibilidad de qué combinaciones generan más volumen y margen, para ajustar la oferta comercial con datos reales.

---

## Escenarios

### Camino feliz
1. Un Administrador crea la combinación "vuelo+hotel+actividad" con 12% de descuento (CU-T14).
2. Pasajeros construyen paquetes con esa combinación (`specs/operativo/paquetes/`, CU-O76-O80).
3. Semanas después, el Administrador consulta el reporte (CU-T15) y ve que esa combinación genera buen margen pese al descuento, y decide mantenerlo.

### Manejo de errores
- **Desactivar una combinación con paquetes en construcción (no confirmados) usándola:** esos paquetes en construcción dejan de poder confirmarse con esa combinación; se informa al pasajero antes de bloquear, no después de intentar pagar.
- **Reporte sin paquetes confirmados en el período filtrado:** mensaje claro.

---

## Criterios de aceptación

- **CU-T14:** Dado que un Administrador crea o edita una combinación con su porcentaje, cuando la guarda, entonces queda disponible (o no, si se desactiva) para nuevos paquetes; los ya confirmados no cambian.
- **CU-T15:** Dado que existen paquetes confirmados en el período filtrado, cuando un Administrador consulta el reporte, entonces ve las combinaciones ordenadas por volumen con su margen generado.

---

## Dependencias

- **Paquetes (Operativo):** RF-PAQ-002 es el consumidor real de CU-T14 — dependencia bidireccional a considerar al secuenciar.
- **Reservas:** CU-T15 depende de `reserva_items`/`reservas.es_paquete` (migración pendiente).
- **Seguridad:** RBAC (CU-O43) y sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O76, O77 (Construir paquete, ver resumen, Operativo) — consumidores/generadores de los datos de este nivel.
- CU-T18 (Configurar política de reembolsos, Reservas) — regla de negocio relacionada: si los descuentos de paquete son acumulables con cupones de Ofertas y Promociones sigue pendiente de definir (QP-18, `analisis-cus-completo.md`).

---

## Fuera de alcance

- Descuentos escalonados por temporada o anticipación de compra — el catálogo solo define descuento fijo por combinación de tipos de producto, no por fecha.
- Exportación del reporte de CU-T15 a archivo descargable.
