# AeroTrack Travel — Documento Empresarial

> Versión consolidada y actualizada. Reemplaza el documento de negocio inicial, incorporando todas las decisiones tomadas desde entonces: modelo de facturación real, fuentes de datos reales para disrupciones, autoservicio de reserva, y la estructura organizacional definitiva.

---

## 1. Contexto de investigación

**Qué existe hoy en el sector (2025-2026):** las agencias de viajes actúan como intermediarias comerciales entre el pasajero y los proveedores (aerolíneas), con tres funciones clásicas: asesora, mediadora/gestora y productora (esta última solo en mayoristas). El estándar NDC de IATA permite a las aerolíneas comunicar cambios en tiempo real a las agencias grandes, pero muchas agencias pequeñas siguen dependiendo de procesos manuales para reenviar esa información al pasajero final.

**El hueco real (origen de este proyecto):** un aviso de cambio de itinerario puede llegar correctamente de la aerolínea a la agencia, y aun así nunca llegar al pasajero, porque el correo de contacto registrado ante la aerolínea es el de la agencia, no el del viajero — ese es el fallo de comunicación que motivó este enfoque.

**Qué se está agregando actualmente en la industria:** automatización e IA conversacional integradas al proceso de reserva, gestión predictiva de disrupciones (anticipar antes de que ocurran), y aplicaciones que monitorean directamente el correo del usuario para construir itinerarios sin intervención manual (ver sección 8).

---

## 2. Descripción de la empresa

**Nombre:** AeroTrack Travel

**2.1 Historia y contexto**
AeroTrack Travel es una agencia de viajes digital minorista, con sede en Miami, Florida, especializada en la venta y gestión de boletos aéreos domésticos dentro de Estados Unidos. Nace para resolver un problema recurrente del sector: la pérdida de información crítica entre la aerolínea y el pasajero final cuando la reserva pasa por un intermediario.

**2.2 Misión**
Gestionar de forma confiable las reservas de vuelo de sus clientes, garantizando que cualquier cambio operacional informado por la aerolínea llegue de forma inmediata y proactiva al pasajero final, combinando fuentes de datos reales (estado de vuelo en tiempo real, monitoreo de correo) con el análisis estadístico de los datos históricos del Bureau of Transportation Statistics (BTS) y la Administración Federal de Aviación (FAA).

**2.3 Visión**
Ser reconocida, hacia 2030, como una agencia de viajes digital de referencia en Estados Unidos por su fiabilidad en la comunicación con el pasajero, cerrando la brecha de información que hoy generan las cadenas de intermediación reactivas.

**2.4 Objetivo estratégico general**
Consolidar AeroTrack Travel como una agencia de viajes digital confiable, mediante el registro riguroso de reservas, la gestión proactiva de disrupciones combinando fuentes estadísticas y reales, y un modelo de facturación transparente para el pasajero.

**2.5 Propuesta de valor**
A diferencia de una agencia tradicional, AeroTrack Travel vincula cada reserva directamente con el estado operacional real del vuelo — mediante API de estado real, monitoreo automático de correo y estimación estadística — y notifica automáticamente cualquier cambio relevante, sin depender de que un agente humano reenvíe el aviso manualmente.

**2.6 Modelo de ingresos**
Replica el modelo real de la industria, con dos fuentes de ingreso simultáneas:
- **Cargo de servicio directo**, cobrado al pasajero al momento de la reserva (ingreso inmediato).
- **Comisión del proveedor** (aerolínea), pactada por contrato y cobrada días o semanas después de completado el viaje (ingreso diferido — refleja el retraso real que sufre el sector).

Money-in: el pasajero paga precio base + cargo de servicio al reservar. Money-out: la agencia remite (de forma simulada, sin integración BSP/ARC real) el neto del boleto a la aerolínea, reteniendo su cargo de servicio; la comisión del proveedor se cobra después. Si hay disrupción grave, se dispara un reembolso según la política de la tarifa comprada.

---

## 3. Niveles organizacionales y alcance actual

| Nivel | Qué define | Qué se entrega ahora |
|---|---|---|
| Estratégico | Metas de negocio: fidelización, expansión de proveedores, madurez analítica | Solo objetivos planteados (sección 5) |
| Táctico | Configuración de reglas de negocio, roles, parámetros | Solo objetivos planteados (sección 5) |
| **Operativo** | **Registro diario: reservas, clientes, vuelos, notificaciones, pagos** | **✅ Esta es la entrega actual** |

---

## 4. Estructura organizacional

Departamentos fundamentados en la estructura estándar de una agencia de viajes minorista (Ventas/Reservas, Comercial, Finanzas, Dirección), con Tecnología como pieza moderna añadida — **deliberadamente no se usa "Administración"** para la capa técnica, ya que en esta industria ese término corresponde al área contable/financiera.

| Departamento | Módulos | Estado |
|---|---|---|
| Ventas y Reservas | Pasajeros, Vuelos (catálogo), Reservas | ✅ Esta entrega |
| Operaciones | Disrupciones y Notificaciones | ✅ Esta entrega |
| Finanzas | Facturación | ✅ Esta entrega |
| Tecnología y Sistemas (TI) | Seguridad (con Auditoría anidada), Configuración | ✅ Esta entrega |
| Comercial y Marketing *(reservado)* | Fidelización, Socios API, Dashboard Comercial | 📋 Alcance futuro |
| Ingeniería y Analítica de Datos *(reservado)* | Pipeline ELT, Modelo Dimensional (heredados, solo lectura), Predictivo, Asistente IA ("SOFIA") | 📋 Alcance futuro |

---

## 5. Objetivos estratégicos, tácticos y operativos (planteados)

### OE-1: Adquisición digital y fidelización de viajeros
- OT-1.1: Captar pasajeros mediante autoservicio digital (buscador de vuelos, sin necesidad de llamar a un agente)
- OT-1.2: Fidelizar pasajeros mediante confiabilidad del servicio

### OE-2: Gestión proactiva de disrupciones e itinerarios (núcleo diferenciador)
- OT-2.1: Combinar tres fuentes de detección según cercanía a la fecha del viaje:
  - Simulador estadístico (histórico BTS/FAA) para reservas lejanas
  - API de estado de vuelo real cuando se acerca la fecha
  - Monitor de bandeja de correo (estilo TripIt) para avisos reales de la aerolínea
- OT-2.2: Notificar proactivamente al pasajero, sin importar cuál fuente detectó el cambio
- OT-2.3: Medir efectividad de la notificación y de cada fuente

### OE-3: Expansión de la red de proveedores y canales de distribución
- OT-3.1: Ampliar acuerdos comerciales con aerolíneas (catálogo de comisiones pactadas)
- OT-3.2: Integrar estándares modernos de distribución (visión futura, tipo NDC)

### OE-4: Inteligencia predictiva y personalización del servicio
- OT-4.1: Anticipar riesgo de disrupción antes de que ocurra (Predictivo, Prophet)
- OT-4.2: Personalizar la asesoría al pasajero (Asistente IA "SOFIA", RAG)

---

## 6. Modelo de facturación

Dos niveles de tarifa con distinta política de reembolso (inspirado en KLM: Light/Standard/Flex), aplicados de forma transparente en el desglose de precio (precio base + cargo de servicio + impuestos = total, estilo Despegar):

| Elemento | Descripción |
|---|---|
| Pago | Procesado vía Stripe en modo de prueba (test mode) — real en su mecánica, sin mover dinero real ni requerir certificación |
| Comisión | Registrada como "pendiente de cobro" al momento de la venta, marcada "cobrada" semanas después (simula el retraso real del sector) |
| Remesa a la aerolínea | Registro contable simulado (sin integración BSP/ARC real, que sí requeriría acreditación IATA) |
| Reembolso | Disparado automáticamente ante disrupción grave, según la política de la tarifa comprada, procesado también vía Stripe test mode |

---

## 7. Experiencia de reserva (autoservicio primero)

Validado contra apps reales (SKY, Despegar, Kiwi.com, KLM): el pasajero busca, selecciona, paga y gestiona su reserva sin necesidad de hablar con nadie. El agente humano queda como canal de respaldo (grupos, soporte, corrección de errores), no como paso obligatorio.

Flujo: Buscador (origen/destino/fecha/pasajeros) → Resultados filtrables → Selección de vuelo y nivel de tarifa → Extras opcionales → Datos del pasajero → Pago → Confirmación y autogestión posterior ("mi reserva").

**Solo vuelos** — sin hospedaje, paquetes ni actividades, para mantener el foco en el diferenciador (gestión de disrupciones) y la coherencia con el dataset BTS/FAA, que es de vuelos, no de hospedaje.

---

## 8. Consideraciones — fuentes de datos y servicios reales incorporados

Estas herramientas se investigaron y validaron específicamente para que el sistema use datos e integraciones reales donde es posible, sin requerir certificaciones formales (IATA/NDC) fuera del alcance de un proyecto académico:

- **TripIt** — precedente comercial que resuelve casi literalmente el problema que motivó el proyecto: permite reenviar o sincronizar automáticamente (vía Gmail) los correos de confirmación/cambio de la aerolínea, y notifica disrupciones a veces antes que la propia aerolínea. Valida que monitorear una bandeja de correo es una estrategia real y usada en producción.
- **Gmail API (OAuth)** — mecanismo que AeroTrack Travel construye inspirado en TripIt: monitorea automáticamente la bandeja de correo de la agencia para detectar y parsear avisos reales de cambio/cancelación enviados por la aerolínea, disparando la notificación al pasajero.
- **APIs de estado de vuelo en tiempo real** (AviationStack, FlightAware AeroAPI, AeroDataBox) — dan estado real y actual de un vuelo específico, sin necesitar certificación IATA, con planes gratuitos o de bajo costo. Complementan al simulador estadístico cuando la reserva se acerca a la fecha de viaje.
- **OpenSky Network** — datos de posición en tiempo real (ADS-B) de aeronaves, gratuito para uso académico/investigación; complemento secundario, ya que no entrega retrasos/cancelaciones directamente, solo posición.
- **Stripe (modo de prueba / test mode)** — pasarela de pago real en su mecánica (autorización, captura, reembolso) pero sin mover dinero real ni requerir certificación, usada para todo el flujo de Facturación (sección 6).

**Explícitamente fuera de alcance (certificaciones formales):** acreditación IATA/IATAN, integración real con BSP/ARC, conexión directa a GDS (Amadeus, Sabre, Travelport) y el estándar NDC completo — todos requieren procesos de certificación institucional inviables para un proyecto académico, y se sustituyen por los mecanismos simulados/reales listados arriba.

---

## 9. Diferencia clave frente al planteamiento original (consultora B2B)

| AeroTrack Analytics (original) | AeroTrack Travel (actual) |
|---|---|
| Consultora B2B que vende informes a aerolíneas | Agencia que gestiona reservas de sus propios pasajeros |
| Cliente final: aerolínea/operador | Cliente final: el pasajero, con autoservicio digital |
| Modelo dimensional = el producto (editable, explorable) | Modelo dimensional = sustento estadístico interno, solo lectura |
| KPIs tipo CAC/MRR de un SaaS B2B | KPIs de fiabilidad de notificación, retención de pasajeros y comisiones cobradas |
| Sin mecanismo de pago real | Stripe test mode + comisión diferida, modelo de facturación real de la industria |
| Datos de disrupción solo estadísticos | Combinación de simulador + API real + monitor de correo (Gmail) |
