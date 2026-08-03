# AeroTrack Travel — Aclaración: Actores e Informes Simples Tácticos

> Este documento aclara un principio clave del nivel táctico:
> **el mismo dato puede ser operativo y táctico al mismo tiempo,
> dependiendo del actor que lo consulta y el propósito con que lo hace.**

---

## El principio

Un informe simple táctico NO requiere datos nuevos ni agregaciones.
Es el mismo registro que ya existe en la BD Operacional (MinIO),
consultado por un actor táctico (jefe departamental) con propósito
de supervisión o control — no de gestión registro a registro.

### Ejemplo del instructor

> "Listado de ventas por vendedor — es operativo pero que lo necesita ver el táctico."

Aplicado a AeroTrack Travel:

| Dimensión | Nivel Operativo | Nivel Táctico |
|---|---|---|
| **Actor** | Agente / Administrador | Jefe departamental |
| **Propósito** | Crear, editar, cancelar, procesar | Supervisar, auditar, controlar |
| **Acción sobre el dato** | Escritura + lectura | Solo lectura |
| **Frecuencia** | Transaccional (tiempo real) | Periódica (diaria, semanal) |
| **CU que lo define** | CU-O## (operativo) | Informe simple del objetivo táctico |

---

## Listados operativos que también son informes simples tácticos

Estos listados ya existen como CU-O. El jefe departamental los consulta
con el mismo dato pero desde una perspectiva de control.
No requieren nueva implementación de datos — solo vista de solo lectura para el rol táctico.

---

### TECNOLOGÍA Y SISTEMAS TI

**Listado de usuarios del sistema**
- CU-O base: CU-O08 (Gestionar usuarios internos)
- Vista táctico: Director de TI revisa usuarios registrados para auditar accesos
  activos, detectar cuentas inactivas o usuarios que ya no deberían tener acceso.
- Colección: usuarios (PocketBase)
- Diferencia: CU-O08 crea/edita/desactiva; el informe táctico solo lista, sin modificar.

**Log de auditoría filtrado por período y actor**
- CU-O base: CU-O12 / CU-O13 (Ver y exportar log de auditoría)
- Vista táctico: Director de TI revisa el log del período para detectar patrones
  de uso anómalo, acciones administrativas no autorizadas o frecuencia inusual
  de operaciones sensibles.
- Colección: auditoria (MinIO operacional)
- Diferencia: CU-O12 es consulta técnica puntual; el informe táctico es revisión
  periódica con foco en patrones, no en eventos individuales.

---

### GESTIÓN DE CLIENTES

**Listado completo de pasajeros registrados**
- CU-O base: CU-O14 / CU-O16 (Consultar y gestionar pasajeros)
- Vista táctico: Director de Clientes revisa el padrón completo para verificar
  calidad de datos, detectar registros incompletos (sin documentos, sin email
  válido) y auditar la base activa.
- Colección: pasajeros (MinIO operacional)
- Diferencia: CU-O16 permite gestionar un pasajero específico; el informe
  táctico muestra el universo completo con métricas de completitud.

---

### VENTAS Y RESERVAS

**Listado de reservas recientes con detalle de estado**
- CU-O base: CU-O25 (Consultar estado de una reserva)
- Vista táctico: Jefe de Ventas revisa todas las reservas del día o semana para
  tener visibilidad de la operación comercial y detectar anomalías de volumen
  o distribución por producto sin buscarlas individualmente.
- Colección: reservas (MinIO operacional)
- Diferencia: CU-O25 consulta una reserva específica a pedido del pasajero;
  el informe táctico es una vista periódica del Jefe de Ventas.

**Listado del catálogo de vuelos activo**
- CU-O base: CU-O17 / CU-O19 (Buscar vuelos / Generar catálogo)
- Vista táctico: Jefe de Ventas verifica que el catálogo publicado contiene
  las rutas esperadas, precios razonables y sin datos corruptos, antes de una
  campaña de marketing.
- Colección: aerotrack-travel-catalog (NDJSON de vuelos — MinIO)
- Diferencia: CU-O17 es para el pasajero que busca un vuelo; el informe
  táctico es una revisión interna del contenido del catálogo.

**Listado de ítems de reserva por tipo de producto**
- CU-O base: CU-O21 (Crear reserva — checkout)
- Vista táctico: Jefe de Ventas ve todos los ítems reservados en el período
  agrupados por tipo (vuelo, hotel, auto, actividad, crucero) para controlar
  la distribución de ventas sin necesidad de una agregación compleja.
- Colección: reserva_items (MinIO operacional)

---

### OPERACIONES

**Listado de notificaciones de disrupción enviadas**
- CU-O base: CU-O31 (Consultar historial de notificaciones recibidas)
- Vista táctico: Director de Operaciones revisa todas las notificaciones del
  período para controlar el volumen de disrupciones comunicadas, verificar
  que ninguna quedó sin notificar y auditar la actividad del sistema proactivo.
- Colección: disrupciones (MinIO operacional)
- Diferencia: CU-O31 es el pasajero viendo sus propias notificaciones;
  el informe táctico es el Director de Operaciones viendo el universo completo.

**Listado de artículos del centro de ayuda por categoría y estado**
- CU-O base: CU-O97 / CU-O98 (Buscar y ver artículos de ayuda)
- Vista táctico: Director de Operaciones revisa el inventario de artículos
  publicados para detectar contenido desactualizado, brechas temáticas o
  artículos archivados que deberían reactivarse.
- Colección: articulos_ayuda (PocketBase)

---

### FINANZAS

**Listado de pagos procesados por período**
- CU-O base: CU-O32 / CU-O38 (Procesar pago / Consultar historial de pagos)
- Vista táctico: Director Financiero revisa todos los pagos del período para
  conciliar con estados de cuenta de Stripe, detectar pagos en estado inesperado
  y auditar actividad financiera sin cálculos complejos.
- Colección: pagos (MinIO operacional)
- Diferencia: CU-O38 es el pasajero viendo sus propios pagos; el informe
  táctico es el CFO viendo el universo completo del período.

**Listado de facturas emitidas por período**
- CU-O base: CU-O33 / CU-O39 (Emitir factura / Descargar factura)
- Vista táctico: Director Financiero audita todas las facturas del período
  para verificar que cada reserva confirmada tiene su factura y los montos
  son correctos.
- Colección: facturas (MinIO operacional)

**Listado de comisiones registradas por estado**
- CU-O base: CU-O34 / CU-O35 (Registrar y conciliar comisiones)
- Vista táctico: Director Financiero revisa todas las comisiones del período
  (pendientes y cobradas) para controlar el ciclo de cobro sin necesitar
  las agregaciones del dashboard financiero completo.
- Colección: comisiones (MinIO operacional)

---

## Nota de implementación

Todos los listados anteriores comparten estas características:

1. **El dato ya existe** en MinIO operacional o PocketBase — no requieren ETL ni ClickHouse.
2. **Son de solo lectura** para el actor táctico — el rol de jefe departamental
   no tiene permisos de escritura sobre estas colecciones.
3. **El filtro es temporal** — el jefe selecciona un período (día, semana, mes)
   y ve todos los registros de ese rango, sin agregaciones matemáticas complejas.
4. **La diferencia con el CU-O** es el actor, el scope y el propósito,
   no la consulta técnica en sí.

Para implementarlos basta con:
- Verificar que el endpoint existente acepta el rol táctico (RBAC)
- Agregar un filtro de período si no lo tiene
- Exponer la vista en el panel de administración del rol correspondiente

---

## Resumen de informes simples adicionales identificados

| Informe | Colección | Actor táctico | CU-O base |
|---|---|---|---|
| Listado de usuarios del sistema | usuarios (PocketBase) | Director de TI | CU-O08 |
| Log de auditoría por período y actor | auditoria | Director de TI | CU-O12/13 |
| Listado completo de pasajeros | pasajeros | Director de Clientes | CU-O14/16 |
| Listado de reservas recientes por estado | reservas | Jefe de Ventas | CU-O25 |
| Listado del catálogo de vuelos activo | catálogo NDJSON | Jefe de Ventas | CU-O17/19 |
| Listado de ítems de reserva por tipo de producto | reserva_items | Jefe de Ventas | CU-O21 |
| Listado de notificaciones de disrupción enviadas | disrupciones | Director de Operaciones | CU-O31 |
| Listado de artículos del centro de ayuda | articulos_ayuda (PocketBase) | Director de Operaciones | CU-O97/98 |
| Listado de pagos procesados por período | pagos | Director Financiero | CU-O32/38 |
| Listado de facturas emitidas por período | facturas | Director Financiero | CU-O33/39 |
| Listado de comisiones registradas por estado | comisiones | Director Financiero | CU-O34/35 |
