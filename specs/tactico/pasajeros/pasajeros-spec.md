# Especificación Táctica — Pasajeros

**Módulo:** Pasajeros
**Prefijo:** PAS
**Código fuente:** `app/pasajeros/` *(nivel Operativo ya implementado y probado — ver `specs/operativo/pasajeros/`; corregido 2026-07-10, 14/14 tests reales pasando)*
**Casos de uso cubiertos:** CU-T04 (Ver segmentación de pasajeros por frecuencia de viaje y destinos preferidos), CU-T05 (Exportar base de pasajeros con filtros)
**Actor:** Administrador

> **Estado:** nivel nuevo, sin código propio todavía. Ambos CU dependen de `reserva_items` (Reservas, migración pendiente) para calcular frecuencia de viaje real — sin eso, solo se puede segmentar por datos de perfil (`pasajeros`), no por comportamiento de compra.

---

## Funcionalidad 1: Ver segmentación de pasajeros (CU-T04)

### RF-PAS-T01 — Ver segmentación de pasajeros por frecuencia de viaje y destinos preferidos
El sistema debe mostrar a un Administrador pasajeros agrupados por frecuencia de viaje (número de reservas confirmadas en un período) y destino preferido (el más repetido en sus reservas), calculado sobre `reservas`/`reserva_items` reales. Filtros instantáneos (REG-J9).

### RN-PAS-T01 — La segmentación se basa en reservas confirmadas, no en búsquedas
A diferencia de "destinos populares" (CU-O102, Ofertas y Promociones, que sí usa búsquedas), la segmentación de pasajeros usa exclusivamente reservas `confirmada` o posterior — es una medida de comportamiento de compra real, no de interés.

---

## Funcionalidad 2: Exportar base de pasajeros (CU-T05)

Extiende a CU-T04 — exportación del mismo dato ya segmentado, o de la base completa sin segmentar.

### RF-PAS-T02 — Exportar base de pasajeros con filtros
El sistema debe permitir a un Administrador exportar a un archivo descargable (CSV) la base de pasajeros filtrada por período, destino o frecuencia — mismos filtros que CU-T04, con la opción de exportar el resultado en vez de solo visualizarlo.

### RN-PAS-T02 — La exportación respeta minimización de datos personales
La exportación incluye solo los campos necesarios para el propósito comercial declarado (nombre, contacto, frecuencia, destino preferido) — nunca campos sensibles como número de documento completo, sin una justificación explícita adicional (REG-B2).

---

## Reglas de negocio

- **RN-PAS-T01** — *(Funcionalidad 1)* Segmentación basada en reservas confirmadas, no en búsquedas.
- **RN-PAS-T02** — *(Funcionalidad 2)* Exportación respeta minimización de datos personales (REG-B2).

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/pasajeros/segmentacion` | Cookie JWT (Admin), filtros de período/destino/frecuencia | HTML/JSON con pasajeros segmentados |
| `GET /backoffice/pasajeros/exportar` | Cookie JWT (Admin), mismos filtros | Archivo CSV descargable |

---

## Historias de usuario

- **HU-PAS-T01:** Como administrador, quiero ver pasajeros segmentados por frecuencia y destino, para dirigir campañas comerciales con datos reales.
- **HU-PAS-T02:** Como administrador, quiero exportar la base filtrada, para trabajarla fuera del sistema (ej. en una campaña de email externa).

---

## Objetivo

Dar al Administrador visibilidad de comportamiento de compra real de los pasajeros, con exportación controlada que respeta minimización de datos personales.

---

## Escenarios

### Camino feliz
1. Un Administrador consulta la segmentación de pasajeros frecuentes hacia el Caribe (CU-T04).
2. Exporta esa base filtrada para una campaña dirigida (CU-T05), con solo los campos necesarios.

### Manejo de errores
- **Segmentación sin reservas confirmadas en el período:** se muestra vacío, sin error técnico.

---

## Criterios de aceptación

- **CU-T04:** Dado que existen pasajeros con reservas confirmadas, cuando un Administrador consulta la segmentación, entonces los ve agrupados por frecuencia y destino preferido.
- **CU-T05:** Dado que un Administrador aplica filtros y exporta, cuando confirma, entonces recibe un CSV con los pasajeros filtrados y solo los campos permitidos.

---

## Dependencias

- **Reservas:** `reserva_items` (migración pendiente) es la fuente real de frecuencia/destino — sin eso, la segmentación solo puede usar datos de perfil.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42).

---

## Casos de uso relacionados

- CU-O14, O16 (Pasajeros, Operativo) — mismo dominio de datos, vista de backoffice individual vs. agregada aquí.
- CU-O21–O25 (Reservas) — fuente de la frecuencia/destino que segmenta este nivel.

---

## Fuera de alcance

- Segmentación predictiva (ej. "probabilidad de reservar en los próximos 30 días") — el catálogo define segmentación descriptiva sobre datos históricos, no predictiva.
- Exportación en formatos distintos a CSV.
