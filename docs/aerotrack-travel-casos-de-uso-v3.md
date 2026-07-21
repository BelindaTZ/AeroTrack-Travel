# AeroTrack Travel — Catálogo de Casos de Uso
**Versión:** 3.1  
**Fecha:** 2026-07-15, ampliado y renumerado 2026-07-17  
**Total:** 122 CU Operativos (CU-O) + 44 CU Tácticos (CU-T) = **166 CU** — ver "Notas de versión" (v3.1) al final para el detalle de lo agregado el 2026-07-17, y la corrección del 2026-07-18 (CU-T44). Ver "Relaciones entre casos de uso" al final para el mapa completo `base` / `<<include>>` / `<<extend>>`.

> **Nota sobre CU-O26:** eliminado en esta versión. Supersedido por CU-O91
> (Crear alerta de precio para una ruta guardada) en el módulo Cuenta / Mis Viajes,
> donde conceptualmente corresponde como función de gestión de cuenta, no de proceso de reserva.

---

## Estructura de módulos por departamento

| Departamento | Módulos |
|---|---|
| Tecnología y Sistemas TI | Seguridad, Integraciones *(nuevo)* |
| Gestión de Clientes | Pasajeros, Cuenta / Mis Viajes |
| Ventas y Reservas | Carrito, Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes, Reservas |
| Operaciones | Disrupciones, Centro de Ayuda |
| Finanzas | Facturación |
| Comercial y Marketing | Ofertas y Promociones, Asistente IA |

---

## 🔐 SEGURIDAD
**Departamento:** Tecnología y Sistemas TI

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O01 | Iniciar sesión | Pasajero / Agente / Administrador |
| CU-O02 | Cerrar sesión | Todos |
| CU-O03 | Recuperar contraseña (solicitar enlace) | Todos |
| CU-O04 | Restablecer contraseña vía enlace | Todos |
| CU-O05 | Ver y editar perfil propio | Todos |
| CU-O06 | Cambiar contraseña (autenticado) | Todos |
| CU-O07 | Registrar nuevo pasajero (autoservicio) | Pasajero |
| CU-O08 | Gestionar usuarios internos (agentes / admin) | Administrador |
| CU-O09 | Crear rol | Administrador |
| CU-O10 | Editar rol | Administrador |
| CU-O11 | Eliminar rol | Administrador |
| CU-O12 | Ver log de auditoría | Administrador |
| CU-O13 | Filtrar y exportar log de auditoría | Administrador |
| CU-O41 | Registrar evento en auditoría *(include target universal)* | Sistema |
| CU-O42 | Verificar sesión activa *(include target universal)* | Sistema |
| CU-O43 | Verificar permisos de acceso RBAC *(include target)* | Sistema |
| CU-O112 | Asignar / revocar permisos de módulo a un rol | Administrador |
| CU-O113 | Asignar / revocar permisos de tabla de BD a un rol | Administrador |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T01 | Monitorear intentos fallidos de autenticación (dashboard de seguridad) | Administrador |
| CU-T02 | Forzar expiración de sesiones activas de un usuario | Administrador |
| CU-T03 | Configurar política de contraseñas y duración de sesión | Administrador |
| CU-T35 | Ver matriz de permisos actual (roles × módulos × tablas) | Administrador |

---

## 🔌 INTEGRACIONES *(módulo nuevo, agregado en sesión de diseño de BD 2026-07-17)*
**Departamento:** Tecnología y Sistemas TI

> Generaliza a los 5 tipos de producto (vuelos, hoteles, autos, actividades, cruceros) lo que
> antes solo existía para vuelos (CU-T06/T07): configurar cada cuánto se sincroniza cada fuente
> externa y auditar si una sincronización falló. No reemplaza CU-T06/T07 (siguen siendo la
> config específica de vuelos), los generaliza para las demás fuentes de datos.

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T37 | Configurar fuente de datos externa (frecuencia de sincronización, activar/desactivar, ver cuota consumida) | Administrador |
| CU-T38 | Ver bitácora de sincronizaciones de catálogos externos (éxito / fallo / parcial, registros procesados, cuota consumida por corrida) | Administrador |

---

## 👤 PASAJEROS
**Departamento:** Gestión de Clientes

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O14 | Consultar datos y reservas de un pasajero (backoffice) | Agente / Administrador |
| CU-O15 | Editar datos de contacto propios | Pasajero |
| CU-O16 | Buscar y gestionar pasajeros (backoffice) | Agente / Administrador |
| CU-O49 | Gestionar documentos de viaje (pasaporte, cédula, fecha de vencimiento) | Pasajero |
| CU-O50 | Gestionar viajeros frecuentes guardados (agregar, editar, eliminar) | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T04 | Ver segmentación de pasajeros por frecuencia de viaje y destinos preferidos | Administrador |
| CU-T05 | Exportar base de pasajeros con filtros (período, destino, frecuencia) | Administrador |

---

## 🛫 VUELOS
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O17 | Buscar vuelos disponibles | Pasajero |
| CU-O18 | Ver detalle y niveles de tarifa de un vuelo | Pasajero |
| CU-O19 | Generar catálogo de vuelos (proceso automático programado) | Sistema (Airflow) |
| CU-O20 | Actualizar estado de un vuelo (proceso automático) | Sistema (Airflow) |
| CU-O45 | Verificar disponibilidad de vuelo / cupo *(include target)* | Sistema |
| CU-O48 | Forzar / ajustar puntualmente un vuelo del catálogo *(solo demo/pruebas — vía excepcional)* | Administrador |
| CU-O51 | Ver predicción de precio de vuelo ("buen momento para comprar") | Pasajero |
| CU-O52 | Ver riesgo de disrupción de un vuelo (histórico para rutas US / estimado para rutas internacionales) | Pasajero |
| CU-O53 | Filtrar resultados de vuelos (escalas, aerolínea, equipaje, horario, duración) | Pasajero |
| CU-O114 | Ver y seleccionar clase de cabina disponible (Economy / Premium Economy / Business / First) | Pasajero |
| CU-O115 | Ver mapa de asientos disponibles de un vuelo | Pasajero |
| CU-O116 | Seleccionar asiento (estándar sin costo o premium con recargo — salida de emergencia/extra legroom) *(extend de CU-O21/O22/O23)* | Pasajero / Agente |
| CU-O117 | Asignar asiento automáticamente si el pasajero no lo eligió antes del vuelo (proceso automático, disparado por temporizador) | Sistema |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T06 | Configurar parámetros del catálogo de vuelos (rutas prioritarias, frecuencia de actualización, número de resultados) | Administrador |
| CU-T07 | Monitorear estado del DAG de catálogo de vuelos y alertar si falla | Administrador |
| CU-T08 | Ver reporte de rutas más buscadas y tasa de conversión búsqueda → reserva | Administrador |
| CU-T39 | Configurar recargo y proporción de asientos premium por tipo de avión | Administrador |
| CU-T40 | Configurar ventana de check-in gratuito para selección de asiento estándar (horas antes del vuelo) | Administrador |
| CU-T41 | Configurar qué rutas/clases de cabina se sincronizan con datos reales de precio (rotación de cuota de la API de precios) | Administrador |

---

## 🏨 HOTELES
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O54 | Buscar hoteles por destino y fechas | Pasajero |
| CU-O55 | Ver detalle de hotel (fotos, descripción, servicios, mapa, clima del destino) | Pasajero |
| CU-O56 | Filtrar resultados de hoteles (estrellas, precio, servicios, calificación, zona) | Pasajero |
| CU-O57 | Seleccionar habitación y tarifa (con comparación cancelación reembolsable vs no reembolsable) | Pasajero |
| CU-O58 | Ver reseñas verificadas de hotel | Pasajero |
| CU-O59 | Consultar cargos adicionales en destino (impuestos municipales, tasas locales) | Pasajero |
| CU-O60 | Reservar hotel con pago diferido — "Reservar sin pagar ahora" (captura de pago manual posterior) | Pasajero |
| CU-O118 | Generar catálogo de hoteles desde fuente externa (proceso automático programado) | Sistema |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T09 | Comparar hasta 5 propiedades de hotel lado a lado | Pasajero |
| CU-T10 | Ver reporte de hoteles más reservados por destino y período | Administrador |

---

## 🚗 AUTOS
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O61 | Buscar autos disponibles por aeropuerto / ciudad y fechas | Pasajero |
| CU-O62 | Ver detalle de vehículo (especificaciones, proveedor, ubicación de recogida, política de cancelación) | Pasajero |
| CU-O63 | Filtrar autos por tipo, marca, proveedor, transmisión, kilometraje y precio | Pasajero |
| CU-O64 | Seleccionar auto y modalidad de pago (pagar ahora o al recoger) | Pasajero |
| CU-O119 | Generar catálogo de autos desde fuente externa (proceso automático programado) | Sistema |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T11 | Ver reporte de reservas de autos por proveedor y categoría de vehículo | Administrador |

---

## 🎭 ACTIVIDADES
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O65 | Buscar actividades por destino | Pasajero |
| CU-O66 | Ver detalle de actividad (descripción, inclusiones, punto de encuentro, condiciones) | Pasajero |
| CU-O67 | Filtrar actividades por categoría, duración, precio y calificación | Pasajero |
| CU-O68 | Verificar disponibilidad y horarios de actividad por fecha | Pasajero |
| CU-O69 | Seleccionar actividad, horario y número de participantes | Pasajero |
| CU-O70 | Ver reseñas y calificaciones de actividad | Pasajero |
| CU-O120 | Generar catálogo de actividades desde fuente externa (proceso automático programado) | Sistema |
| CU-O121 | Generar disponibilidad sintética (cupos y horarios) de actividades según regla de negocio propia — sin fuente externa real, alimenta CU-O68 *(proceso automático)* | Sistema |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T12 | Ver actividades más reservadas por destino y categoría | Administrador |
| CU-T42 | Configurar parámetros de disponibilidad sintética de actividades (cupos por defecto, horarios por día) | Administrador |

---

## ⛵ CRUCEROS
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O71 | Buscar cruceros por destino, fechas y duración | Pasajero |
| CU-O72 | Ver itinerario detallado de crucero (mapa de ruta, puertos día a día) | Pasajero |
| CU-O73 | Comparar fechas de zarpe del mismo barco con precios por tipo de camarote | Pasajero |
| CU-O74 | Ver información del barco (servicios a bordo, planos de cubierta, políticas) | Pasajero |
| CU-O75 | Seleccionar tipo de camarote y tarifa | Pasajero |
| CU-O122 | Generar catálogo de cruceros desde fuente externa (proceso automático programado) | Sistema |
| CU-O123 | Generar disponibilidad sintética (cupos) de camarotes según regla de negocio propia — la API de cruceros no expone inventario real *(proceso automático)* | Sistema |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T13 | Ver cruceros más consultados por destino y temporada | Administrador |
| CU-T43 | Configurar parámetros de disponibilidad sintética de camarotes de crucero | Administrador |

---

## 📦 PAQUETES
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O76 | Construir paquete seleccionando componentes (vuelo + hotel obligatorio; auto / actividad opcional) | Pasajero |
| CU-O77 | Ver resumen de paquete con desglose de ahorro vs. reserva por separado | Pasajero |
| CU-O78 | Cambiar componente individual del paquete sin reiniciar el flujo | Pasajero |
| CU-O79 | Ver condiciones y política de cancelación por cada componente del paquete | Pasajero |
| CU-O80 | Agregar traslado aeropuerto al paquete | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T14 | Configurar porcentajes de descuento por tipo de paquete (vuelo+hotel, vuelo+hotel+auto, etc.) | Administrador |
| CU-T15 | Ver reporte de combinaciones de paquete más vendidas y margen generado | Administrador |

---

## 📋 RESERVAS
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O21 | Crear reserva — autoservicio (checkout completo con datos de pasajero, contacto y pago) | Pasajero |
| CU-O22 | Crear reserva asistida (backoffice — agente en nombre del pasajero) | Agente |
| CU-O23 | Modificar reserva existente | Pasajero / Agente |
| CU-O24 | Cancelar reserva | Pasajero / Agente |
| CU-O25 | Consultar estado de una reserva | Pasajero |
| CU-O44 | Expirar reserva pendiente de pago (temporizador automático) | Sistema |
| CU-O47 | Cobrar / reembolsar diferencia de tarifa en modificación *(extend target)* | Sistema / Pasajero |
| CU-O81 | Consultar requisitos de documentación y visa por destino | Pasajero |
| CU-O82 | Descargar voucher de reserva en PDF | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T16 | Ver reporte de reservas por estado (confirmada, pendiente, cancelada) y período | Administrador |
| CU-T17 | Monitorear reservas próximas a vencer por pago pendiente y gestionar acciones | Agente / Administrador |
| CU-T18 | Configurar política de reembolsos por tipo de producto y tarifa | Administrador |

---

## ⚡ DISRUPCIONES
**Departamento:** Operaciones

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O27 | Consultar estado real de vuelo vía servicio externo (proceso automático) | Sistema (Airflow) |
| CU-O28 | Monitorear bandeja de correo de aerolíneas (proceso automático) | Sistema (Airflow) |
| CU-O29 | Detectar cambio de itinerario comparando estado real vs. reserva activa | Sistema (Airflow) |
| CU-O30 | Notificar al pasajero sobre disrupción detectada | Sistema (Airflow) |
| CU-O31 | Consultar historial de notificaciones recibidas | Pasajero / Agente |
| CU-O46 | Reintentar envío de notificación fallida *(extend target)* | Sistema |
| CU-O83 | Calcular y registrar risk score de vuelo (histórico BTS/FAA para rutas US / estimado para rutas internacionales) | Sistema (Airflow) |
| CU-O84 | Ver posición en tiempo real de aeronave en mapa | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T19 | Ver dashboard de vuelos activos en monitoreo con estado en tiempo real | Agente / Administrador |
| CU-T20 | Configurar umbrales de risk score que disparan alerta proactiva al pasajero | Administrador |
| CU-T21 | Ver reporte de disrupciones por aerolínea, ruta y período | Administrador |

---

## 💰 FACTURACIÓN
**Departamento:** Finanzas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O32 | Procesar pago de reserva (tarjeta de crédito / débito) | Pasajero |
| CU-O33 | Emitir factura / recibo tras pago confirmado | Sistema |
| CU-O34 | Registrar comisión por reserva confirmada | Sistema |
| CU-O35 | Conciliar comisiones pendientes vs. cobradas | Administrador |
| CU-O36 | Generar remesa simulada a aerolínea u hotel | Sistema / Administrador |
| CU-O37 | Procesar reembolso | Sistema / Agente |
| CU-O38 | Consultar historial de pagos propios | Pasajero |
| CU-O39 | Descargar factura / recibo en PDF | Pasajero |
| CU-O40 | Descargar itinerario / e-ticket en PDF | Pasajero |
| CU-O85 | Convertir moneda para presentación de precios (proceso automático, 1×día) | Sistema |
| CU-O86 | Capturar pago diferido de hotel (completar cobro del pago pendiente al confirmarlo el hotel) | Sistema / Administrador |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T22 | Ver dashboard financiero (ingresos por producto, comisiones acumuladas, remesas pendientes) | Administrador |
| CU-T23 | Generar reporte de ingresos por período y tipo de producto | Administrador |

---

## 🗂️ CUENTA DE USUARIO / MIS VIAJES
**Departamento:** Gestión de Clientes

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O87 | Ver Mis Viajes (reservas próximas, activas y pasadas con detalle completo) | Pasajero |
| CU-O88 | Guardar / eliminar favorito (destino, hotel o actividad) | Pasajero |
| CU-O89 | Ver y retomar búsquedas recientes por producto | Pasajero |
| CU-O90 | Crear viaje personalizado (nombre + descripción, para planificación libre) | Pasajero |
| CU-O91 | Crear alerta de precio para una ruta guardada | Pasajero |
| CU-O92 | Consultar saldo y movimientos del programa de beneficios / puntos | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T24 | Configurar programa de beneficios (reglas de acumulación de puntos, niveles, fecha de vencimiento) | Administrador |
| CU-T25 | Ver reporte de alertas de precio activas y conversiones generadas | Administrador |

---

## 🛒 CARRITO
**Departamento:** Ventas y Reservas

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O93 | Ver contenido del carrito con resumen de precio total | Pasajero |
| CU-O94 | Agregar ítem al carrito (vuelo, hotel, auto, actividad o crucero) | Pasajero |
| CU-O95 | Eliminar ítem del carrito | Pasajero |
| CU-O96 | Proceder al checkout desde el carrito | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T26 | Configurar recuperación de carrito abandonado (tiempo de espera, plantilla de email) | Administrador |
| CU-T27 | Ver reporte de carritos abandonados y tasa de recuperación | Administrador |

---

## 🆘 CENTRO DE AYUDA
**Departamento:** Operaciones

> El centro de ayuda opera en primera instancia mediante el Asistente IA. Los casos no resueltos
> se escalan vía email al equipo interno de soporte — no existe chat en vivo con agente humano
> dentro de la aplicación. El agente revisa y responde desde la bandeja de soporte (Gmail API).

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O97 | Buscar artículo de ayuda por categoría o término | Pasajero |
| CU-O98 | Ver artículo de ayuda con contenido completo | Pasajero |
| CU-O99 | Calificar utilidad de artículo o respuesta (pulgar arriba / abajo) | Pasajero |
| CU-O100 | Escalar caso no resuelto a agente humano vía email | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T28 | Gestionar base de conocimiento (crear, editar y archivar artículos de ayuda por categoría) | Administrador |
| CU-T29 | Ver métricas de satisfacción del centro de ayuda (artículos más consultados, calificaciones, escalaciones) | Administrador |
| CU-T36 | Gestionar bandeja de casos escalados (revisar emails de soporte, marcar como resuelto, responder al pasajero) | Agente |

---

## 🎯 OFERTAS Y PROMOCIONES
**Departamento:** Comercial y Marketing

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O101 | Ver ofertas destacadas por producto (vuelos, hoteles, paquetes, actividades, cruceros) | Pasajero |
| CU-O102 | Ver destinos populares desde el origen del pasajero | Pasajero |
| CU-O103 | Aplicar cupón de descuento en checkout | Pasajero |
| CU-O104 | Suscribirse al newsletter de ofertas | Pasajero |
| CU-O105 | Ver términos y condiciones de una promoción vigente | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T30 | Crear y gestionar cupones de descuento (código, monto/%, producto aplicable, fecha de expiración) | Administrador |
| CU-T31 | Configurar y enviar campaña de email promocional a segmento de pasajeros | Administrador |
| CU-T32 | Ver reporte de cupones usados, descuentos aplicados y conversiones generadas | Administrador |
| CU-T44 | Configurar acumulación de cupones con descuento de paquete (regla global + excepciones por cupón) | Administrador |

---

## 🤖 ASISTENTE IA
**Departamento:** Comercial y Marketing

### Operativos

| ID | Nombre | Actor |
|---|---|---|
| CU-O106 | Iniciar conversación con el Asistente IA | Pasajero |
| CU-O107 | Hacer consulta informativa de viaje (documentos, destinos, clima, requisitos) | Pasajero |
| CU-O108 | Hacer consulta transaccional sobre reserva propia (requiere autenticación activa) | Pasajero autenticado |
| CU-O109 | Ver historial de conversaciones anteriores con el asistente | Pasajero |
| CU-O110 | Calificar respuesta del asistente (pulgar arriba / abajo) | Pasajero |
| CU-O111 | Iniciar nueva conversación (limpiar contexto, mantener historial) | Pasajero |

### Tácticos

| ID | Nombre | Actor |
|---|---|---|
| CU-T33 | Ver reporte de consultas frecuentes al asistente y temas sin respuesta | Administrador |
| CU-T34 | Configurar el asistente IA (tono, temas permitidos, respuestas predefinidas para accesos rápidos) | Administrador |

---

## Resumen numérico

| Módulo | Departamento | Operativos | Tácticos | Total módulo |
|---|---|---|---|---|
| Seguridad | TI | 18 | 4 | 22 |
| Integraciones | TI | 0 | 2 | 2 |
| Pasajeros | Clientes | 5 | 2 | 7 |
| Vuelos | Ventas | 13 | 6 | 19 |
| Hoteles | Ventas | 8 | 2 | 10 |
| Autos | Ventas | 5 | 1 | 6 |
| Actividades | Ventas | 8 | 2 | 10 |
| Cruceros | Ventas | 7 | 2 | 9 |
| Paquetes | Ventas | 5 | 2 | 7 |
| Reservas | Ventas | 9 | 3 | 12 |
| Disrupciones | Operaciones | 8 | 3 | 11 |
| Facturación | Finanzas | 11 | 2 | 13 |
| Cuenta / Mis Viajes | Clientes | 6 | 2 | 8 |
| Carrito | Ventas | 4 | 2 | 6 |
| Centro de Ayuda | Operaciones | 4 | 3 | 7 |
| Ofertas y Promociones | Comercial | 5 | 4 | 9 |
| Asistente IA | Comercial | 6 | 2 | 8 |
| **TOTAL** | | **122** | **44** | **166** |

---

## Notas de versión

**Corrección 2026-07-18 (2)** — Agregado **CU-T44** (Configurar acumulación de cupones con descuento de paquete, Ofertas y Promociones), numerado al final de la secuencia CU-T existente (después de CU-T43) siguiendo la misma convención de numeración del resto del catálogo. Resuelve QP-18 (`analisis-cus-completo.md`): si un cupón de descuento es acumulable con el descuento propio de un paquete quedaba explícitamente sin definir — ahora es una regla de negocio configurable (default global + excepción por cupón individual), no una decisión de código implícita. Total del catálogo pasa de 165 a 166 CU (44 CU-T).

**Corrección 2026-07-18 (1)** — CU-O94 (Agregar ítem al carrito, módulo Carrito) decía "vuelo, hotel, auto o actividad", sin crucero. Era un olvido accidental de texto, no una decisión deliberada: el esquema `carrito_items` del dbml v3 (`crucero_id`, `crucero_camarote_id`) ya soportaba cruceros desde que se escribió. Corregido a "vuelo, hotel, auto, actividad o crucero".

**v3.1 — 2026-07-17**
- Agregados 17 CU nuevos (10 Operativos + 7 Tácticos) surgidos de la sesión de diseño de BD
  (pruebas reales de APIs + revisión del esquema `docs/aerotrack-travel-propuesta-tablas-v3.dbml`).
  Numerados al final de cada secuencia existente (CU-O114–O123, CU-T37–T43) para no romper
  referencias ya existentes a los CU previos en las specs de módulo.
- **Módulo nuevo Integraciones** (Tecnología y Sistemas TI): generaliza a los 5 tipos de producto
  lo que antes solo existía para vuelos (CU-T06/T07) — configurar frecuencia de sincronización de
  cada fuente externa y auditar sus corridas.
- **Vuelos**: selección de clase de cabina (Economy/Premium/Business/First, con datos reales
  confirmados de Google Flights), mapa de asientos y selección de asiento (estándar gratis o
  premium con recargo — salida de emergencia/extra legroom), asignación automática de asiento si
  el pasajero no eligió, y su configuración táctica correspondiente.
- **Hoteles/Autos/Actividades/Cruceros**: se agregó el CU de "generar catálogo desde fuente
  externa (proceso automático)" — existía el equivalente para Vuelos (CU-O19) pero nunca se había
  agregado para los 4 módulos de producto añadidos en v3.0, quedó como hueco hasta ahora.
- **Actividades y Cruceros**: se agregó "generar disponibilidad sintética (proceso automático)" +
  su configuración táctica — ninguna API probada da disponibilidad/cupos real para estos dos
  productos (confirmado con pruebas en vivo), así que se genera por regla de negocio propia; esto
  alimenta CU-O68 (Actividades) y la selección de camarote (Cruceros), que ya existían en el
  catálogo pero sin que constara de dónde sale el dato de cupos.

**v3.0 — 2026-07-15**
- Catálogo ampliado de 48 CU-O a 112 CU-O + 36 CU-T = 148 CU totales
- Añadidos 10 módulos nuevos: Hoteles, Autos, Actividades, Cruceros, Paquetes,
  Cuenta / Mis Viajes, Carrito, Centro de Ayuda, Ofertas y Promociones, Asistente IA
- CU-O26 eliminado: supersedido por CU-O91 en módulo Cuenta / Mis Viajes
- CU-O14 ajustado: renombrado a consulta de backoffice; vista rica de historial → CU-O87
- CU-O63 ajustado: añadido filtro por marca de vehículo
- CU-O112 / CU-O113 añadidos: permisos granulares de módulo y tabla BD por rol
- CU-T35 añadido: matriz de permisos roles × módulos × tablas
- Nivel táctico introducido en todos los módulos (CU-T01 a CU-T36)
- Referencias a servicios externos removidas del catálogo (se documentan en .env y en specs)
- Geolocalización para campo origen de vuelos: documentada como regla de negocio en spec
  de Vuelos (no como CU independiente) — comportamiento condicional al permiso del browser

**v2.0 — anterior**
- 48 CU operativos (CU-O01 – CU-O48), 6 módulos

**v1.0 — base inicial**
- 47 CU operativos (CU-O01 – CU-O47)

---

## Relaciones entre casos de uso (base / `<<include>>` / `<<extend>>`)

**Semántica UML usada:** en `<<include>>` el CU origen dispara **siempre** al CU incluido como parte obligatoria de su flujo normal. En `<<extend>>` el CU de extensión se dispara **solo si** se cumple una condición, insertándose en un punto de extensión del CU base — la relación es opcional/condicional, nunca obligatoria.

**Cobertura y confianza de este análisis:**
- **CU-O01–O48 (nivel v1/v2):** relaciones **confirmadas**, ya expandidas en formato Jacobson completo (FB/FA/RN) en [`analisis-cus-completo.md`](../specs/000-sistema-general/analisis-cus-completo.md) secciones 3 y 4 de `specs/000-sistema-general/`. Se reproducen aquí sin cambios.
- **CU-O49 en adelante (módulos añadidos en v3.0/v3.1):** este catálogo solo los documenta en formato tabular resumen, sin expandir su flujo Jacobson todavía. Las relaciones de esta sección para ese rango son un **análisis editorial de esta sesión**, inferido del flujo de negocio descrito en el nombre/descripción de cada CU — quedan abiertas a ajuste cuando se redacte el `spec.md` de cada módulo nuevo (mismo tratamiento que recibieron CU-O45/O47 en su momento).

**Regla transversal universal — no se repite CU por CU en las tablas de abajo:**
1. Todo CU interactivo que **crea, modifica o elimina** un registro `<<include>>` a **CU-O41** (Registrar evento en auditoría), salvo que se marque explícitamente "solo lectura".
2. Todo CU que requiere sesión iniciada `<<include>>` a **CU-O42** (Verificar sesión activa) — excepto CU-O01/O03/O04/O07 (ocurren *antes* de tener sesión) y las búsquedas/vistas públicas sin autenticación (buscadores y detalle de Vuelos, Hoteles, Autos, Actividades, Cruceros; Centro de Ayuda; Ofertas y Promociones).
3. Todo CU cuyo actor incluye Agente o Administrador `<<include>>` a **CU-O43** (Verificar permisos de acceso RBAC).

Un CU no listado en la columna "Relación adicional" de las tablas siguientes es **CU base**: no depende de que otro lo dispare, y su única relación es la transversal universal (1)-(3) según le corresponda por su naturaleza (mutación / autenticado / rol interno).

### Seguridad
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O11 Eliminar rol | Bloqueo si el rol tiene usuarios activos asignados (QP-10, `analisis-cus-completo.md`) | Base, con flujo alterno |
| CU-O13 Filtrar y exportar log de auditoría | Extiende a CU-O12 (Ver log) | `<<extend>>` de O12 |
| CU-O41 Registrar evento en auditoría | Incluido por prácticamente todo CU mutante de los 17 módulos | `<<include>>` — target universal |
| CU-O42 Verificar sesión activa | Incluido por todos excepto O01/O03/O04/O07 y las vistas públicas | `<<include>>` — target universal |
| CU-O43 Verificar permisos RBAC | Incluido por toda acción de Agente/Administrador | `<<include>>` — target (roles internos) |
| CU-O112 Asignar/revocar permisos de módulo a un rol | Extiende a CU-O10 (Editar rol) — asignación granular como paso opcional; alimenta la matriz que consulta O43 | `<<extend>>` de O10 |
| CU-O113 Asignar/revocar permisos de tabla a un rol | Extiende a CU-O10 (Editar rol); alimenta la matriz que consulta O43 | `<<extend>>` de O10 |
| CU-T35 Ver matriz de permisos | Consume los datos generados por O112/O113 | Base (lectura), consumidor |

### Integraciones
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-T37 Configurar fuente de datos externa | Generaliza a CU-T06 (config específica de Vuelos) para Hoteles/Autos/Actividades/Cruceros; condiciona CU-O19/O118/O119/O120/O122 | Base, generaliza T06 |
| CU-T38 Ver bitácora de sincronizaciones | Generaliza a CU-T07 (monitoreo específico de Vuelos); consume corridas de O19/O118/O119/O120/O122 | Base (lectura), generaliza T07 |

### Pasajeros
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O50 Gestionar viajeros frecuentes guardados | Alimenta datos opcionales de autocompletado a CU-O21/O22 (checkout) | Base, alimenta a O21/O22 |
| CU-T05 Exportar base de pasajeros con filtros | Extiende a CU-T04 (segmentación) | `<<extend>>` de T04 |

### Vuelos
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O18 Ver detalle y niveles de tarifa | Precondición de CU-O114 (selección de cabina) | Base |
| CU-O19 Generar catálogo de vuelos | Alimenta a O17/O18; configurado por T06, monitoreado por T07, generalizado en T37/T38 | Base automático |
| CU-O45 Verificar disponibilidad de vuelo/cupo | Incluido por CU-O21, O22, O23 | `<<include>>` — target |
| CU-O51 Ver predicción de precio | Complementa la vista de O17/O18, no es un paso obligatorio del flujo | Base, complementario |
| CU-O52 Ver riesgo de disrupción de un vuelo | Consume el risk score calculado por CU-O83 (Disrupciones) | Base, consumidor de O83 |
| CU-O53 Filtrar resultados de vuelos | Extiende a CU-O17 (búsqueda) | `<<extend>>` de O17 |
| CU-O114 Ver y seleccionar clase de cabina | Extiende a CU-O18 (ver detalle); precede a O21/O22 | `<<extend>>` de O18 |
| CU-O115 Ver mapa de asientos | Extiende a CU-O114; precondición de O116 | `<<extend>>` de O114 |
| CU-O116 Seleccionar asiento | Extiende a CU-O21/O22/O23 *(ya documentado en el catálogo)* | `<<extend>>` de O21/O22/O23 |
| CU-O117 Asignar asiento automáticamente | Disparado por temporizador cuando no hubo O116 antes de la ventana de check-in (config. T40) — mismo patrón que O44 | Independiente, disparado por tiempo |
| CU-T39 Configurar recargo asientos premium | Condiciona O116 | Base |
| CU-T40 Configurar ventana de check-in gratuito | Condiciona el disparo de O117 | Base |
| CU-T41 Configurar rotación de cuota API de precios | Condiciona O51 y qué clases de O114 tienen precio real vs. estimado | Base |

### Hoteles
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O56 Filtrar resultados de hoteles | Extiende a CU-O54 (búsqueda) | `<<extend>>` de O54 |
| CU-O58 Ver reseñas verificadas | Extiende a CU-O55 (ver detalle) | `<<extend>>` de O55 |
| CU-O59 Consultar cargos adicionales en destino | Extiende a CU-O55/O57 | `<<extend>>` de O55/O57 |
| CU-O60 Reservar hotel con pago diferido | Extiende hacia CU-O86 (Facturación — capturar pago diferido) cuando el hotel confirma | `<<extend>>` hacia O86 |
| CU-O118 Generar catálogo de hoteles | Alimenta a O54/O55; análogo a O19; generalizado en T37/T38 | Base automático |
| CU-T09 Comparar hasta 5 propiedades | Extiende a CU-O54/O55 | `<<extend>>` de O54/O55 |

### Autos
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O63 Filtrar autos | Extiende a CU-O61 (búsqueda) | `<<extend>>` de O61 |
| CU-O119 Generar catálogo de autos | Alimenta a O61/O62; análogo a O19/O118; generalizado en T37/T38 | Base automático |

### Actividades
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O67 Filtrar actividades | Extiende a CU-O65 (búsqueda) | `<<extend>>` de O65 |
| CU-O68 Verificar disponibilidad y horarios | Incluido por CU-O69; consume la disponibilidad generada por O121 | `<<include>>` — target |
| CU-O69 Seleccionar actividad, horario y participantes | Incluye a CU-O68 | `<<include>>` → O68 |
| CU-O70 Ver reseñas y calificaciones | Extiende a CU-O66 (ver detalle) | `<<extend>>` de O66 |
| CU-O120 Generar catálogo de actividades | Alimenta a O65/O66; análogo a O19; generalizado en T37/T38 | Base automático |
| CU-O121 Generar disponibilidad sintética | Alimenta a O68 *(ya documentado en el catálogo)* | Base automático, alimenta a O68 |
| CU-T42 Configurar disponibilidad sintética | Condiciona O121 | Base |

### Cruceros
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O72 Ver itinerario detallado | Extiende a CU-O71 (búsqueda) | `<<extend>>` de O71 |
| CU-O73 Comparar fechas de zarpe | Extiende a CU-O71/O72 | `<<extend>>` de O71/O72 |
| CU-O74 Ver información del barco | Extiende a CU-O72 | `<<extend>>` de O72 |
| CU-O75 Seleccionar tipo de camarote y tarifa | Consume la disponibilidad generada por O123 | Base, consumidor de O123 |
| CU-O122 Generar catálogo de cruceros | Alimenta a O71/O72; análogo a O19; generalizado en T37/T38 | Base automático |
| CU-O123 Generar disponibilidad sintética de camarotes | Alimenta a O75 | Base automático, alimenta a O75 |
| CU-T43 Configurar disponibilidad sintética de camarotes | Condiciona O123 | Base |

### Paquetes
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O76 Construir paquete | Consume la selección de componentes de O18/O57/O64/O69 (Vuelos/Hoteles/Autos/Actividades) | Base, compone otros módulos |
| CU-O77 Ver resumen de paquete | Extiende a CU-O76 | `<<extend>>` de O76 |
| CU-O78 Cambiar componente individual | Extiende a CU-O76 | `<<extend>>` de O76 |
| CU-O79 Ver condiciones y política de cancelación | Extiende a CU-O76/O77 | `<<extend>>` de O76/O77 |
| CU-O80 Agregar traslado aeropuerto | Extiende a CU-O76 (extra opcional) | `<<extend>>` de O76 |
| CU-T14 Configurar % de descuento por tipo de paquete | Condiciona el desglose de O77 | Base |

### Reservas
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O21 Crear reserva (autoservicio) | Incluye a O32, O45; puede incluir a O116 | `<<include>>` → O32,O45 |
| CU-O22 Crear reserva asistida | Incluye a O32, O45 | `<<include>>` → O32,O45 |
| CU-O23 Modificar reserva | Incluye a O45; extendida por O47 y por O116 | Base, `<<extend>>` target de O47/O116 |
| CU-O24 Cancelar reserva | Extendida por O37 (si la tarifa da derecho a reembolso); bloqueo si el vuelo ya está "completado" (O20) | Base, `<<extend>>` target de O37 |
| CU-O44 Expirar reserva pendiente de pago | Disparado por temporizador sobre O21/O22 | Independiente, disparado por tiempo |
| CU-O47 Cobrar/reembolsar diferencia de tarifa | Extiende a CU-O23 *(ya documentado en el catálogo)*; RF de mecanismo de cobro también en Facturación | `<<extend>>` de O23 |
| CU-O81 Consultar requisitos de documentación y visa | Relacionado con CU-O49 (Pasajeros — documentos de viaje) | Base, relacionado con O49 |
| CU-T17 Monitorear reservas próximas a vencer | Vigila el mismo mecanismo de expiración que O44 | Base, relacionado con O44 |
| CU-T18 Configurar política de reembolsos | Condiciona O37/O47 | Base |

### Disrupciones
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O29 Detectar cambio de itinerario | Incluye a O30 (REG-E1: ninguna disrupción queda sin notificar); consume O27/O28 | `<<include>>` → O30 |
| CU-O30 Notificar al pasajero | Incluido por O29; extendida por O37 (si es cancelación) y por O46 (si falla el envío) | `<<include>>` target; `<<extend>>` target de O37/O46 |
| CU-O46 Reintentar envío de notificación fallida | Extiende a CU-O30 *(ya documentado en el catálogo)* | `<<extend>>` de O30 |
| CU-O83 Calcular y registrar risk score | Alimenta a O52 (Vuelos) | Base automático, alimenta a O52 |

### Facturación
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O32 Procesar pago de reserva | Incluye a O33, O34 | `<<include>>` → O33,O34 |
| CU-O33 Emitir factura/recibo | Incluido por O32 | `<<include>>` — target |
| CU-O34 Registrar comisión por reserva | Incluido por O32 | `<<include>>` — target |
| CU-O37 Procesar reembolso | Extiende a CU-O24 y a CU-O30 *(ya documentado en el catálogo)* | `<<extend>>` de O24/O30 |
| CU-O85 Convertir moneda | Transversal a toda presentación de precio (Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes) | Base automático, transversal |
| CU-O86 Capturar pago diferido de hotel | Extiende a CU-O60 (Hoteles) | `<<extend>>` de O60 |

### Cuenta de usuario / Mis Viajes
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O87 Ver Mis Viajes | Agrega datos de Reservas (O21-O25) | Base, agrega otros módulos |
| CU-O89 Ver y retomar búsquedas recientes | Relacionado con todos los buscadores (O17, O54, O61, O65, O71) | Base, relacionado con buscadores |
| CU-O91 Crear alerta de precio | Sucesor de CU-O26 (eliminado — ver nota al inicio del catálogo) | Base |
| CU-O92 Consultar saldo de puntos | Consume las reglas configuradas en T24 | Base, consumidor de T24 |
| CU-T25 Ver reporte de alertas de precio | Consume datos de O91 | Base (lectura), consumidor de O91 |

### Carrito
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O94 Agregar ítem al carrito | Consume la selección de O18/O57/O64/O69/O75 | Base, consumidor de otros módulos |
| CU-O95 Eliminar ítem del carrito | Extiende a CU-O93 (ver contenido) | `<<extend>>` de O93 |
| CU-O96 Proceder al checkout | Incluye a CU-O21/O22 (Reservas) | `<<include>>` → O21/O22 |

### Centro de Ayuda
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O98 Ver artículo de ayuda | Extiende a CU-O97 (buscar) | `<<extend>>` de O97 |
| CU-O99 Calificar utilidad de artículo o respuesta | Extiende a CU-O98 | `<<extend>>` de O98 |
| CU-O100 Escalar caso no resuelto a agente | Se dispara cuando el Asistente IA (O106-O108) no resuelve la consulta | `<<extend>>` de O106/O107/O108 |
| CU-T28 Gestionar base de conocimiento | Alimenta a O97/O98 | Base |
| CU-T29 Ver métricas de satisfacción | Consume O99 | Base (lectura), consumidor de O99 |
| CU-T36 Gestionar bandeja de casos escalados | Consume O100 | Base, consumidor de O100 |

### Ofertas y Promociones
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O103 Aplicar cupón de descuento en checkout | Extiende a CU-O96/O21/O22 (checkout) | `<<extend>>` de O96/O21/O22 |
| CU-O105 Ver términos y condiciones de una promoción | Extiende a CU-O101/O103 | `<<extend>>` de O101/O103 |
| CU-T30 Crear y gestionar cupones | Alimenta a O103 | Base |
| CU-T32 Ver reporte de cupones usados | Consume O103 | Base (lectura), consumidor de O103 |
| CU-T44 Configurar acumulación de cupones con descuento de paquete | Condiciona O103 cuando la reserva es un paquete (`reservas.es_paquete`, Paquetes); resuelve QP-18 | Base, relacionado con CU-T14 (Paquetes) |

### Asistente IA
| CU | Relación adicional | Tipo |
|---|---|---|
| CU-O107 Hacer consulta informativa de viaje | Incluido por O106 (flujo principal) | `<<include>>` — target |
| CU-O108 Hacer consulta transaccional sobre reserva propia | Extiende a CU-O106/O107, condicionado a autenticación activa | `<<extend>>` de O106/O107 |
| CU-O110 Calificar respuesta del asistente | Extiende a CU-O107/O108 | `<<extend>>` de O107/O108 |
| CU-O111 Iniciar nueva conversación | Extiende a CU-O106 (variante: limpia contexto, mantiene historial) | `<<extend>>` de O106 |
| CU-T33 Ver reporte de consultas frecuentes | Consume O107/O108 | Base (lectura), consumidor |
| CU-T34 Configurar el asistente IA | Condiciona O106-O111 | Base |
