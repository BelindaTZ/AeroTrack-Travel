# Especificación Táctica — Ofertas y Promociones

**Módulo:** Ofertas y Promociones
**Prefijo:** OFE
**Código fuente:** `app/ofertas/` *(compartido con el nivel Operativo — ver `specs/operativo/ofertas-promociones/`)*
**Casos de uso cubiertos:** CU-T30 (Crear y gestionar cupones de descuento), CU-T31 (Configurar y enviar campaña de email promocional), CU-T32 (Ver reporte de cupones usados, descuentos aplicados y conversiones generadas), CU-T44 (Configurar acumulación de cupones con descuento de paquete — nuevo 2026-07-18)
**Actor:** Administrador

> **Estado:** módulo nuevo del catálogo v3.0/v3.1, sin código todavía. CU-T30 es **precondición real** de RF-OFE-003 (Operativo, el checkout no tiene cupones que validar sin esto) — implementar junto con esa fase. **CU-T44 es una extensión directa de CU-T30** (mismo dueño de dato, `cupones_descuento`), agregada el 2026-07-18 para resolver QP-18 (`analisis-cus-completo.md`): si un cupón es acumulable con el descuento propio de un paquete (`paquetes-spec.md`, RN-PAQ-002) ya no es una decisión implícita — es una regla configurable con default global + excepción por cupón.

---

## Funcionalidad 1: Crear y gestionar cupones de descuento (CU-T30)

### RF-OFE-T01 — Crear y gestionar cupones de descuento
El sistema debe permitir a un Administrador crear y editar cupones (`cupones_descuento`: código único, tipo — porcentaje o monto fijo —, valor, producto aplicable opcional, fecha de expiración, usos máximos opcionales) y activar/desactivar cada uno.

### RN-OFE-T01 — El código de cupón es único e inmutable tras su primer uso
Una vez que un cupón tiene al menos un registro en `cupones_uso`, su `codigo` no puede editarse (evita romper trazabilidad de canjes ya hechos); el resto de sus campos (valor, expiración, activo) sí puede seguir editándose.

---

## Funcionalidad 2: Configurar y enviar campaña de email promocional (CU-T31)

### RF-OFE-T02 — Configurar y enviar campaña de email promocional
El sistema debe permitir a un Administrador crear una campaña (`campanas_email`: nombre, criterio de segmento en JSON, plantilla), previsualizarla, y enviarla realmente vía SendGrid a los pasajeros/suscriptores que cumplen el criterio — `estado` transiciona `borrador` → `programada` → `enviada`.

### RN-OFE-T02 — Una campaña enviada no se reenvía ni se edita
Una vez que `campanas_email.estado = enviada`, ni la plantilla ni el segmento pueden modificarse — para una campaña similar se crea una nueva, nunca se reutiliza una ya enviada.

---

## Funcionalidad 3: Ver reporte de cupones (CU-T32)

### RF-OFE-T03 — Ver reporte de cupones usados, descuentos aplicados y conversiones generadas
El sistema debe mostrar a un Administrador, por cupón, el número de usos, el monto total descontado (`cupones_uso.monto_descontado`) y la tasa de conversión (usos / vistas o intentos de aplicación, si se registran) en el período filtrado. Filtros instantáneos (REG-J9).

---

## Funcionalidad 4: Configurar acumulación de cupones con descuento de paquete (CU-T44) — *(nuevo 2026-07-18, resuelve QP-18)*

Extiende a CU-T30 — mismo dueño de dato (`cupones_descuento`), no requiere colección propia.

### RF-OFE-T04 — Configurar acumulación de cupones con descuento de paquete
El sistema debe permitir a un Administrador definir: (1) un **default global** — si, en general, un cupón se puede aplicar sobre una reserva que ya es un paquete con su propio descuento (`configuracion_sistema`, clave `cupones.acumulable_con_paquete_default`); y (2) **excepciones por cupón individual** — al crear o editar un cupón (CU-T30), marcar explícitamente si ESE cupón en particular es o no acumulable con descuento de paquete (`cupones_descuento.acumulable_con_paquete`, nullable), sin importar el default global vigente.

### RN-OFE-T03 — La excepción por cupón siempre gana sobre el default global
Si `cupones_descuento.acumulable_con_paquete` no es nulo para un cupón, ese valor se usa sin importar el default global — el default solo aplica a cupones que no tienen excepción explícita (`acumulable_con_paquete = null`). Esto permite, por ejemplo, que el default global sea "no acumulable" pero un cupón promocional específico ("BIENVENIDA10") sea la excepción explícita que sí se puede combinar con un paquete.

### RN-OFE-T04 — La regla solo se evalúa cuando la reserva es un paquete
Si `reservas.es_paquete = false`, esta configuración no aplica — el cupón se valida y aplica con las reglas normales de RF-OFE-003 (`specs/operativo/ofertas-promociones/`), sin ninguna consulta adicional a esta regla.

---

## Reglas de negocio

- **RN-OFE-T01** — *(Funcionalidad 1)* El código de un cupón ya usado no puede editarse.
- **RN-OFE-T02** — *(Funcionalidad 2)* Una campaña enviada es inmutable.
- **RN-OFE-T03** — *(Funcionalidad 4)* La excepción por cupón siempre gana sobre el default global de acumulación con paquete.
- **RN-OFE-T04** — *(Funcionalidad 4)* La regla de acumulación solo se evalúa cuando la reserva es un paquete.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET/POST /backoffice/ofertas/cupones` | Cookie JWT (Admin), datos del cupón (incluye `acumulable_con_paquete` opcional) | Cupón creado/actualizado |
| `GET/POST /backoffice/ofertas/campanas` | Cookie JWT (Admin), datos de campaña | Campaña creada/actualizada (mientras `borrador`) |
| `POST /backoffice/ofertas/campanas/{id}/enviar` | Cookie JWT (Admin) | Envío real vía SendGrid, `estado = enviada` |
| `GET /backoffice/ofertas/reporte-cupones` | Cookie JWT (Admin), filtro de período | HTML/JSON con uso y descuento por cupón |
| `GET/POST /backoffice/ofertas/config-acumulacion-paquete` | Cookie JWT (Admin), default global (boolean) | Default global guardado |

---

## Historias de usuario

- **HU-OFE-T01:** Como administrador, quiero crear y gestionar cupones de descuento, para lanzar promociones sin depender de un desarrollador.
- **HU-OFE-T02:** Como administrador, quiero configurar y enviar campañas de email a un segmento de pasajeros, para promocionar ofertas de forma dirigida.
- **HU-OFE-T03:** Como administrador, quiero ver qué cupones se usan más y cuánto descuento representan, para medir el costo real de cada promoción.
- **HU-OFE-T04:** Como administrador, quiero definir si los cupones son acumulables con el descuento de un paquete por defecto, y poder marcar excepciones puntuales, para tener control fino sin necesidad de crear una regla distinta por cada cupón.

---

## Objetivo

Dar al Administrador control comercial completo sobre cupones y campañas de email, con envío real (no simulado) y visibilidad del costo/efectividad de cada promoción.

---

## Escenarios

### Camino feliz
1. Un Administrador crea un cupón "VERANO26" con 15% de descuento para vuelos (CU-T30).
2. Configura y envía una campaña de email promocionándolo a pasajeros frecuentes (CU-T31).
3. Pasajeros lo aplican en su checkout (`specs/operativo/ofertas-promociones/`, CU-O103).
4. El Administrador consulta el reporte (CU-T32) y ve el uso real y el descuento total otorgado.

### Manejo de errores
- **Intento de editar el código de un cupón ya usado:** se bloquea (RN-OFE-T01).
- **Intento de reenviar o editar una campaña ya enviada:** se bloquea (RN-OFE-T02).
- **Cupón sin excepción explícita aplicado sobre un paquete:** usa el default global vigente en ese momento (RN-OFE-T03).

---

## Criterios de aceptación

- **CU-T30:** Dado que un Administrador crea o edita un cupón, cuando lo guarda, entonces queda disponible (o no) para RF-OFE-003; si ya tiene usos, su código no puede cambiar.
- **CU-T31:** Dado que un Administrador configura una campaña y la envía, cuando confirma, entonces se envía realmente vía SendGrid a los destinatarios del segmento, y la campaña queda inmutable.
- **CU-T32:** Dado que existen cupones usados en el período filtrado, cuando un Administrador consulta el reporte, entonces ve uso y descuento total por cupón.
- **CU-T44:** Dado que un Administrador configura el default global y, opcionalmente, una excepción en un cupón específico, cuando se aplica ese cupón sobre un paquete (RF-OFE-003, Operativo), entonces la excepción del cupón determina si se acumula o no; si el cupón no tiene excepción, se usa el default global.

---

## Dependencias

- **Ofertas y Promociones (Operativo):** RF-OFE-003 es el consumidor real de CU-T30 y de CU-T44.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42), credenciales de SendGrid en `configuracion_sistema` (REG-B3).
- **Cuenta/Mis Viajes, Pasajeros:** fuente de los criterios de segmento de CU-T31 (frecuencia de viaje, destino preferido — mismos datos que ya usa CU-T04 en Pasajeros).
- **Paquetes:** CU-T44 resuelve la interacción entre el descuento de cupón (este módulo) y el descuento de paquete (`paquetes-spec.md`, RN-PAQ-002) — ninguno de los dos módulos decide esto unilateralmente.

---

## Casos de uso relacionados

- CU-O103 (Aplicar cupón, Operativo) — consumidor de CU-T30 y CU-T44.
- CU-O104 (Suscribirse al newsletter, Operativo) — fuente de destinatarios adicionales de CU-T31.
- CU-T04 (Ver segmentación de pasajeros, Pasajeros) — mismo tipo de criterio de segmento que CU-T31.
- CU-T14 (Configurar % de descuento por tipo de paquete, Paquetes) — la otra mitad de la regla que CU-T44 reconcilia; ver también QP-18 en `analisis-cus-completo.md`.

---

## Fuera de alcance

- Envío A/B testing de campañas — el catálogo define una campaña única por envío, no variantes.
- Cupones de un solo uso por pasajero (más allá del límite global `usos_maximos`) — no está en el esquema actual; si se necesita, requiere un campo nuevo.
