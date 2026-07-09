# Consideraciones — Sistema AeroTrack Travel (Nivel Operativo)

**Fuente principal:** `docs/aerotrack-travel-documento-empresarial.md`. Este documento reúne el contexto de negocio y las decisiones de alcance que condicionan cómo se interpreta cada RF/RN en los 6 módulos-spec, para no repetirlas en cada uno.

---

## 1. Naturaleza del proyecto

AeroTrack Travel es un proyecto académico que **simula** una agencia de viajes digital minorista, pero usa **integraciones reales donde es posible** (Stripe test mode, Gmail API, APIs de estado de vuelo) en lugar de mocks completos, precisamente para validar que el diferenciador del negocio (comunicación proactiva de disrupciones) funciona contra fuentes de datos reales. Ninguna spec de módulo debe diseñar una integración externa "de juguete" cuando existe una alternativa real de bajo costo/gratuita ya validada en el documento empresarial (sección 8).

## 2. El problema que origina el proyecto

Un aviso de cambio de itinerario puede llegar correctamente de la aerolínea a la agencia y aun así nunca llegar al pasajero final, porque el correo de contacto registrado ante la aerolínea es el de la agencia, no el del viajero. Esto es el porqué de fondo del módulo Disrupciones y de la regla constitucional E1 (ninguna disrupción detectada queda sin notificar) — toda RN de ese módulo debe evaluarse contra si cierra o reabre este hueco.

## 3. Alcance de producto: solo vuelos, solo EE. UU. doméstico

- **Solo vuelos** — sin hospedaje, paquetes ni actividades. Mantiene el foco en el diferenciador (gestión de disrupciones) y la coherencia con el dataset heredado (BTS/FAA es de vuelos, no de hospedaje).
- **Vuelos domésticos EE. UU.** — para pasajeros no se pide ni sube ningún documento de identidad; solo se declara nombre y, opcionalmente, número de identificación, sin verificación ni imágenes. Ninguna spec debe introducir flujos de verificación documental (pasaportes, visados) fuera de este alcance.
- **Moneda única: USD.**

## 4. Tres niveles organizacionales — solo uno se entrega ahora

| Nivel | Qué define | Estado en esta entrega |
|---|---|---|
| Estratégico | Metas de negocio: fidelización, expansión de proveedores, madurez analítica | Solo objetivos planteados, sin spec |
| Táctico | Configuración de reglas de negocio, roles, parámetros | Solo objetivos planteados, sin spec |
| **Operativo** | Registro diario: reservas, clientes, vuelos, notificaciones, pagos | **Esta es la entrega actual** |

Ninguna spec de nivel Operativo debe intentar resolver una necesidad de configuración general (SMTP, credenciales, umbrales, plantillas) dentro de sí misma — esas necesidades quedan documentadas como referencia a un CU-T previsto (catálogo en `docs/aerotrack-travel-casos-de-uso-operativos.md`, sección 3) y se resuelven cuando exista el nivel Táctico. Mientras tanto, los valores que normalmente vivirían en configuración táctica (tiempos de expiración, umbrales, credenciales) se leen de `configuracion_sistema` con un valor por defecto documentado en la spec del módulo que lo consume.

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

| Servicio | Rol en el sistema | Por qué se eligió |
|---|---|---|
| **TripIt** | Precedente comercial, no una integración — valida que "monitorear una bandeja de correo" es una estrategia real usada en producción | Referencia de diseño para Disrupciones |
| **Gmail API (OAuth)** | Monitorea la bandeja de correo de la agencia para detectar avisos reales de cambio/cancelación (CU-O28) | Inspirado en TripIt, sin requerir certificación |
| **API de estado de vuelo** (AviationStack, FlightAware AeroAPI, AeroDataBox) | Estado real y actual de un vuelo específico (CU-O27) | Sin necesidad de certificación IATA, planes gratuitos/bajo costo |
| **OpenSky Network** | Posición ADS-B en tiempo real — complemento secundario | Gratuito para uso académico; no entrega retrasos/cancelaciones directamente, solo posición — no debe tratarse como fuente primaria de disrupción |
| **Stripe (test mode)** | Pasarela de pago para todo el flujo de Facturación | Mecánica real (autorización, captura, reembolso) sin mover dinero real ni requerir certificación |

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
