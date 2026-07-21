# Consideraciones — Sistema AeroTrack Travel (Niveles Operativo y Táctico)

**Fuente principal:** `docs/aerotrack-travel-documento-empresarial.md`, actualizado con las decisiones de la sesión de diseño de BD (`docs/aerotrack-travel-casos-de-uso-v3.md`, `docs/aerotrack-travel-propuesta-tablas-v3.dbml`, `docs/fuentes-datos-por-tabla.md`, 2026-07-17). Este documento reúne el contexto de negocio y las decisiones de alcance que condicionan cómo se interpreta cada RF/RN en los 17 módulos-spec, para no repetirlas en cada uno.

> **Nota (2026-07-18):** la sección 3 de este documento decía "solo vuelos, sin hospedaje, paquetes ni actividades" — eso dejó de ser cierto con el catálogo v3.0 (2026-07-15), que amplió el alcance a seis verticales de producto y a rutas internacionales. Se corrige abajo; el resto del documento (secciones 1, 2, 4-11) se actualiza donde corresponde, sin tocar lo que sigue vigente.

---

## 1. Naturaleza del proyecto

AeroTrack Travel es un proyecto académico que **simula** una agencia de viajes digital minorista, pero usa **integraciones reales donde es posible** (Stripe test mode, Gmail API, APIs de estado de vuelo) en lugar de mocks completos, precisamente para validar que el diferenciador del negocio (comunicación proactiva de disrupciones) funciona contra fuentes de datos reales. Ninguna spec de módulo debe diseñar una integración externa "de juguete" cuando existe una alternativa real de bajo costo/gratuita ya validada en el documento empresarial (sección 8).

## 2. El problema que origina el proyecto

Un aviso de cambio de itinerario puede llegar correctamente de la aerolínea a la agencia y aun así nunca llegar al pasajero final, porque el correo de contacto registrado ante la aerolínea es el de la agencia, no el del viajero. Esto es el porqué de fondo del módulo Disrupciones y de la regla constitucional E1 (ninguna disrupción detectada queda sin notificar) — toda RN de ese módulo debe evaluarse contra si cierra o reabre este hueco.

## 3. Alcance de producto: seis verticales, alcance internacional (ampliado en v3.0)

> **Decisión revisada 2026-07-15/17** (supersede la versión original de este documento, que
> limitaba el alcance a "solo vuelos, solo EE. UU. doméstico"): el catálogo creció a seis
> verticales de producto y a rutas internacionales, validado contra integraciones reales
> probadas en vivo (ver sección 7). El diferenciador de negocio (gestión proactiva de
> disrupciones) **sigue siendo exclusivo de Vuelos** — ninguna de las otras cinco verticales tiene
> monitoreo de disrupciones en el catálogo actual; eso no cambió.

- **Seis verticales de producto** — Vuelos, Hoteles, Autos de renta, Actividades, Cruceros y
  Paquetes (combinación de las anteriores, vuelo+hotel obligatorio como mínimo). Cada una tiene su
  propio módulo-spec de catálogo/búsqueda, y todas confluyen en Carrito → Reservas → Facturación.
- **Alcance internacional** — ya no limitado a EE. UU. doméstico. Esto reabre la necesidad de
  documentación de viaje (pasaporte, vencimiento — CU-O49, módulo Pasajeros) y de consulta de
  requisitos de visa por destino (CU-O81, módulo Reservas, vía Visa Requirement API) para rutas que
  sí lo requieran; sigue sin pedirse verificación documental con imágenes, solo declaración de
  datos, igual que en el alcance doméstico original.
- **El dataset heredado (BTS/FAA, modelo dimensional Kimball) sigue siendo de vuelos únicamente**
  — no se amplió a las otras verticales. El risk score histórico (CU-O83) y el simulador
  estratégico solo aplican a Vuelos; las demás verticales no tienen equivalente de riesgo de
  disrupción en este catálogo.
- **Moneda de presentación:** se muestra en la moneda local relevante cuando aplica, convertida
  para consistencia vía CU-O85 (ExchangeRate-API, 1×/día) — dejó de ser estrictamente USD único al
  ampliarse a alcance internacional; el cobro real vía Stripe sigue siendo en USD.

## 4. Tres niveles organizacionales — dos se entregan ahora (ampliado 2026-07-18)

| Nivel | Qué define | Estado en esta entrega |
|---|---|---|
| Estratégico | Metas de negocio: fidelización, expansión de proveedores, madurez analítica | Solo objetivos planteados, sin spec — el único nivel que sigue fuera de alcance |
| **Táctico** | Configuración de reglas de negocio, roles, parámetros, reportes operativos | **Catálogo redactado (43 CU-T, 17 módulos), carpetas creadas bajo `specs/tactico/` — `spec.md` pendiente de redactar módulo por módulo** |
| **Operativo** | Registro diario: búsqueda/reserva de las 6 verticales, clientes, notificaciones, pagos | **122 CU-O, 16 módulos — 6 ya redactados de una ronda anterior, 10 con carpeta creada, `spec.md` pendiente** |

Ninguna spec de nivel Operativo debe intentar resolver una necesidad de configuración general
(SMTP, credenciales, umbrales, plantillas) dentro de sí misma — esas necesidades se documentan
como referencia al CU-T correspondiente (catálogo completo en `docs/aerotrack-travel-casos-de-uso-v3.md`,
mapa de asignación por módulo en `analisis-cus-completo.md` sección 4) y se resuelven cuando se
redacte el `spec.md` Táctico de ese módulo. Mientras tanto, los valores que vivirían en
configuración táctica (tiempos de expiración, umbrales, credenciales, frecuencia de sincronización)
se leen de `configuracion_sistema` con un valor por defecto documentado en la spec Operativa del
módulo que los consume — igual criterio que cuando el nivel Táctico completo estaba sin redactar,
ahora aplicado módulo por módulo según se vaya redactando cada `spec.md` Táctico.

## 5. Modelo de ingresos y facturación

Dos fuentes de ingreso simultáneas, con temporalidad distinta:
- **Cargo de servicio directo** — cobrado al pasajero al momento de la reserva (ingreso inmediato).
- **Comisión del proveedor** (aerolínea) — pactada por contrato, cobrada días o semanas después de completado el viaje (ingreso diferido, refleja el retraso real del sector).

Money-in: el pasajero paga precio base + cargo de servicio al reservar. Money-out: la agencia remite (de forma simulada, sin integración BSP/ARC real) el neto del boleto a la aerolínea, reteniendo su cargo de servicio; la comisión se cobra después. Si hay disrupción grave, se dispara un reembolso según la política de la tarifa comprada. Toda spec de Facturación debe modelar explícitamente este desfase temporal entre cargo de servicio (inmediato) y comisión (diferida) — nunca tratarlos como el mismo evento contable.

Dos niveles de tarifa con distinta política de reembolso (Light/Standard/Flex, inspirado en KLM), aplicados de forma transparente en el desglose de precio (precio base + cargo de servicio + impuestos = total, estilo Despegar).

## 6. Experiencia de reserva: autoservicio primero

Validado contra apps reales (SKY, Despegar, Kiwi.com, KLM): el pasajero busca, selecciona, paga y gestiona su reserva sin necesidad de hablar con nadie. El agente humano es un canal de respaldo (grupos, soporte, corrección de errores), **nunca un paso obligatorio** — esto es la regla constitucional G1 y debe leerse como restricción de diseño en Pasajeros, Vuelos y Reservas: cualquier flujo que obligue a pasar por un agente para completar una acción de autoservicio está fuera de especificación, salvo que el propio catálogo de CU lo defina como "asistida" explícitamente (CU-O22).

Flujo de referencia: Buscador (origen/destino/fecha/pasajeros) → Resultados filtrables → Selección de vuelo y nivel de tarifa → Extras opcionales → Datos del pasajero → Pago → Confirmación y autogestión posterior ("mi reserva").

## 7. Fuentes de datos y servicios reales incorporados (y su motivo)

Ampliada 2026-07-17 con las fuentes probadas en vivo durante la sesión de diseño de BD para las
cinco verticales nuevas — detalle endpoint-por-endpoint en `docs/apis-reference.md` y
`docs/fuentes-datos-por-tabla.md`; esta tabla queda como el resumen de alto nivel.

| Servicio | Rol en el sistema | Por qué se eligió |
|---|---|---|
| **TripIt** | Precedente comercial, no una integración — valida que "monitorear una bandeja de correo" es una estrategia real usada en producción | Referencia de diseño para Disrupciones |
| **Gmail API (OAuth)** | Monitorea la bandeja de correo de la agencia para detectar avisos reales de cambio/cancelación (CU-O28) | Inspirado en TripIt, sin requerir certificación |
| **API de estado de vuelo** (AeroDataBox / AviationStack) | Estado real y actual de un vuelo específico, catálogo de vuelos, delays por aeropuerto (CU-O19, O20, O27) | Sin necesidad de certificación IATA, planes gratuitos/bajo costo; rotación de 3 hubs/día para no agotar cuota |
| **Google Flights (SerpApi)** | Precio real, clase de cabina, predicción de precio (CU-O19, O51, O114) | Único de los evaluados con precio y `price_insights` reales; rotación separada de cuota (~250/mes) |
| **OpenSky Network** | Posición ADS-B en tiempo real — complemento secundario (CU-O84) | Gratuito para uso académico; no entrega retrasos/cancelaciones directamente, solo posición — no debe tratarse como fuente primaria de disrupción |
| **HotelLens** | Catálogo de hoteles, tarifas y reseñas reales (CU-O118, módulo Hoteles) | Único evaluado con `rooms_left` real vía flujo Google Hotels → Booking.com |
| **Global Rental Cars** | Catálogo de autos de renta (CU-O119, módulo Autos) | Flujo Expedia limpio; Priceline/Booking sirven pero ignoran fecha/ubicación pedida, revalidar antes de cobrar |
| **Travel Advisor** | Catálogo y reseñas de actividades (CU-O120, módulo Actividades) | Endpoint de disponibilidad real (`check-availability`) confirmado roto — de ahí la disponibilidad sintética (CU-O121) |
| **Cruise Pricing API** | Catálogo y precio de cruceros/camarotes (CU-O122, módulo Cruceros) | 10/11 endpoints funcionales; sin inventario real de cupos — de ahí la disponibilidad sintética (CU-O123) |
| **Visa Requirement API** | Requisitos de documentación/visa por destino, cacheados (CU-O81, módulo Reservas) | Necesaria al ampliar a alcance internacional (sección 3) |
| **ExchangeRate-API** | Conversión de moneda para presentación de precio, 1×/día (CU-O85, módulo Facturación) | Necesaria al ampliar a alcance internacional |
| **Stripe (test mode)** | Pasarela de pago para todo el flujo de Facturación, incluye pago diferido de hotel (CU-O86) | Mecánica real (autorización, captura, reembolso) sin mover dinero real ni requerir certificación |
| **SendGrid** | Envío real de notificaciones y campañas de email promocional (Disrupciones, Ofertas y Promociones) | Envío real sin necesidad de infraestructura SMTP propia |
| **Groq / Gemini** | Generación de respuesta en vivo del Asistente IA (CU-O106–O111) | Constante, contexto acotado y verificable (constitución H1) |

**Explícitamente fuera de alcance (certificaciones formales):** acreditación IATA/IATAN, integración real con BSP/ARC, conexión directa a GDS (Amadeus, Sabre, Travelport), estándar NDC completo. Todos requieren procesos de certificación institucional inviables para un proyecto académico y se sustituyen por los mecanismos simulados/reales de la tabla anterior. Ninguna spec de módulo debe diseñar un flujo que asuma acceso a estos sistemas.

## 8. Tres fuentes de detección de disrupciones, combinadas según cercanía al viaje

1. **Simulador estadístico** (histórico BTS/FAA, nivel Estratégico — ya implementado como DAG de Airflow) para reservas lejanas.
2. **API de estado de vuelo real** cuando se acerca la fecha de viaje.
3. **Monitor de bandeja de correo** (estilo TripIt) para avisos reales de la aerolínea, en paralelo.

El módulo Disrupciones (nivel Operativo) es dueño de las fuentes 2 y 3; la fuente 1 pertenece al nivel Estratégico (CU-E01) pero ya existe técnicamente — cuando se redacte su spec, se formaliza sobre lo ya construido, no se rehace.

## 9. Diferencia frente al proyecto anterior (AeroTrack Analytics)

| AeroTrack Analytics (anterior) | AeroTrack Travel (actual) |
|---|---|
| Consultora B2B que vende informes a aerolíneas | Agencia que gestiona reservas de sus propios pasajeros |
| Cliente final: aerolínea/operador | Cliente final: el pasajero, con autoservicio digital |
| Modelo dimensional = el producto | Modelo dimensional = sustento estadístico interno, solo lectura |
| Sin mecanismo de pago real | Stripe test mode + comisión diferida |
| Datos de disrupción solo estadísticos | Simulador + API real + monitor de correo combinados |

Ninguna instancia, tabla ni credencial se comparte entre proyectos: `pocketbase-travel` es una instancia nueva; MinIO (`aerotrack-travel-dims`) queda de solo lectura y no recibe tablas nuevas (ver `reglas.md`, REG-A1/REG-A2).

## 10. Convención organizacional deliberada

No se usa "Administración" para la capa técnica — en la industria de agencias de viajes ese término corresponde al área contable/financiera. El departamento técnico se llama **Tecnología y Sistemas (TI)**, distinto de **Finanzas**.

## 11. Estándar de casos de uso y trazabilidad

El catálogo fuente usa el formato Ivar Jacobson/UML (Craig Larman, usecases.org): nombre en verbo infinitivo + objeto, actor principal, precondiciones/postcondiciones, flujo básico numerado, flujos alternos `X.Y`, reglas de negocio `RN-XXX` asociadas. Toda spec de módulo que amplíe un CU con nuevo detalle (RF/RNF) debe mantener esta numeración de flujos alternos como referencia, no reemplazarla por una convención distinta.
