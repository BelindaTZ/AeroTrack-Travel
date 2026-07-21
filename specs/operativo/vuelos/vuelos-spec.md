# Especificación Operativa — Vuelos (catálogo)

**Módulo:** Vuelos (catálogo)
**Prefijo:** VUE
**Código fuente:** `app/vuelos/`
**Casos de uso cubiertos:** CU-O17 (Buscar vuelos disponibles), CU-O18 (Ver detalle y niveles de tarifa de un vuelo), CU-O19 (Generar catálogo de vuelos programables), CU-O20 (Actualizar estado de un vuelo), CU-O45 (Verificar disponibilidad de vuelo/cupo — RF, mecanismo/dato), CU-O48 (Forzar/ajustar puntualmente un vuelo del catálogo — solo pruebas/demo), CU-O51 (Ver predicción de precio — nuevo v3.1, no implementado), CU-O52 (Ver riesgo de disrupción de un vuelo — nuevo v3.1, no implementado), CU-O53 (Filtrar resultados de vuelos — nuevo v3.1, **parcialmente implementado**), CU-O114 (Ver y seleccionar clase de cabina — nuevo v3.1, no implementado), CU-O115 (Ver mapa de asientos — nuevo v3.1, no implementado), CU-O116 (Seleccionar asiento — nuevo v3.1, no implementado), CU-O117 (Asignar asiento automáticamente — nuevo v3.1, no implementado)
**Actor:** Pasajero / Sistema (automático, Airflow) / Administrador (CU-O48, vía excepcional)

> **Notas de actualización 2026-07-18 — leer antes de tocar este módulo:**
> 1. **Referencias a "CU-T18 (tendencia histórica de precio/puntualidad)" corregidas en todo este documento.** Esa nota apuntaba a un CU-T que, al renumerar el catálogo completo, pasó a significar otra cosa (CU-T18 hoy es "Configurar política de reembolsos", en Reservas — ver `analisis-cus-completo.md` punto abierto 8). El concepto de tendencia de precio SÍ existe en el catálogo actual, pero como **CU-O51** (Ver predicción de precio, Operativo, no Táctico) — las referencias se corrigieron para apuntar ahí.
> 2. **CU-O53 (filtrar resultados) está parcialmente implementado.** El repo real (`vuelos_repo.py`) solo filtra por `aerolinea_id` server-side; el catálogo pide además escalas, equipaje, horario y duración — no implementados. Ver RF-VUE-001 y Funcionalidad 6 abajo.
> 3. **CU-O51/O52/O114–O117 son todos nuevos v3.1, ninguno implementado.** Se documentan con el detalle de esquema real del dbml v3 (`predicciones_precio_ruta`, `vuelos_catalogo.risk_score`, `tarifas_vuelo.clase_cabina`, `asientos_vuelo`) para que la implementación futura no tenga que re-investigar las fuentes de datos.

---

## Funcionalidad 1: Buscar y consultar vuelos disponibles (CU-O17, CU-O18)

Permite a cualquier pasajero, autenticado o no, explorar el catálogo de vuelos programables y sus niveles de tarifa.

### RF-VUE-001 — Buscar vuelos disponibles
El sistema debe permitir a un pasajero ingresar origen, destino, fecha(s) y número de pasajeros, y consultar el catálogo de vuelos programables (`vuelos_catalogo`) filtrando por esos criterios. Muestra resultados con aerolínea, horario, duración, escalas, precio base y niveles de tarifa disponibles (Light/Standard/Flex). **Implementado hoy:** filtro server-side por `aerolinea_id` únicamente. **Pendiente (CU-O53, Funcionalidad 6 abajo):** filtro por escalas, equipaje, rango horario y duración, y ordenar por precio/duración/escalas. Si no hay vuelos que cumplan los criterios, muestra un mensaje claro; cuando exista CU-O51 (Ver predicción de precio, Funcionalidad 7), este flujo podrá reutilizarlo para sugerir fechas cercanas — *corrección 2026-07-18: antes decía "CU-T18 (tendencia histórica)", que tras la renumeración del catálogo completo pasó a significar otra cosa (política de reembolsos, en Reservas); el concepto correcto hoy es CU-O51.*

### RF-VUE-002 — Ver detalle y niveles de tarifa de un vuelo
El sistema debe mostrar, para un vuelo seleccionado, su detalle completo (aerolínea, tramo, horarios, duración, avión si aplica) y sus niveles de tarifa disponibles (`tarifas_vuelo` + `niveles_tarifa`), cada uno con su precio final, equipaje incluido, política de cambios y política de reembolso asociada, para que el pasajero compare antes de reservar (REG-G2 — transparencia de precio).

### RNF-VUE-001 — Legibilidad de origen/destino
Toda pantalla que muestre `vuelos_catalogo.origen_codigo`/`destino_codigo` los resuelve contra el modelo dimensional heredado (`dim_aeropuerto`, SOFT-REF) para mostrar nombre de ciudad y aeropuerto legibles, nunca solo el código IATA crudo.

---

## Funcionalidad 2: Generar catálogo de vuelos programables (CU-O19)

Proceso automático que puebla el catálogo operativo de vuelos disponibles para búsqueda y reserva.

### RF-VUE-003 — Generar catálogo de vuelos programables
El sistema debe generar periódicamente, mediante un proceso automático (Airflow), registros en `vuelos_catalogo` con `generado_por = sistema`, a partir de las rutas conocidas en el modelo dimensional heredado (`dim_ruta`, solo lectura — REG-A2) y reglas de programación (aerolíneas activas, frecuencia por ruta). Cada vuelo generado nace en estado `programado` y con sus niveles de tarifa (`tarifas_vuelo`) inicializados con cupo disponible.

### RNF-VUE-002 — El catálogo nunca escribe sobre el modelo dimensional heredado
Este proceso solo lee `dim_ruta` y tablas `dim_*`/`agg_*` relacionadas; no crea, modifica ni elimina ningún registro en esa capa (REG-A1/REG-A2).

---

## Funcionalidad 3: Actualizar estado de un vuelo (CU-O20)

Mantiene el estado operativo de cada vuelo del catálogo sincronizado con la realidad.

### RF-VUE-004 — Actualizar estado de un vuelo
El sistema debe permitir actualizar `vuelos_catalogo.estado` (`programado`, `retrasado`, `cancelado`, `completado`, `desviado`) de forma automática, registrando `fecha_actualizacion_estado`. Este RF es el punto de escritura que consume `disrupciones-spec.md` (CU-O27/O29) cuando detecta un cambio real; también es quien, al marcar un vuelo `completado`, habilita el bloqueo de cancelación de reserva documentado en `reservas-spec.md` (flujo alterno de CU-O24).

---

## Funcionalidad 4: Verificar disponibilidad de vuelo/cupo (CU-O45 — RF, mecanismo/dato)

Servicio transversal `<<include>>` de CU-O21/O22/O23 en `reservas-spec.md`. Este módulo documenta el **mecanismo**: cómo se consulta y decrementa el cupo, dado que `tarifas_vuelo` es una tabla propiedad de Vuelos. La **orquestación de negocio** (cuándo se invoca y qué pasa si falla dentro del flujo de reserva) se documenta como regla de negocio en `reservas-spec.md`.

### RF-VUE-005 — Verificar y reservar cupo disponible
El sistema debe exponer un servicio que, dado un `tarifas_vuelo.id`, consulte `cupos_disponibles` y — si es mayor a cero — lo decremente de forma atómica en el mismo paso de la verificación, para evitar que dos solicitudes concurrentes reserven el último cupo (condición de carrera, ver QP-08 en `analisis-cus-completo.md`). Si el cupo es cero, el servicio responde que no hay disponibilidad sin decrementar nada.

### RNF-VUE-003 — Atomicidad de la verificación de cupo
La lectura y el decremento de `cupos_disponibles` se ejecutan como una única operación atómica a nivel de datos; ninguna otra funcionalidad puede leer un valor de cupo intermedio entre la verificación y la reserva efectiva.

---

## Funcionalidad 5: Forzar/ajustar puntualmente un vuelo del catálogo — solo pruebas/demo (CU-O48)

> **Vía EXCEPCIONAL, fuera del flujo de negocio normal.** El catálogo de vuelos sigue siendo 100% automático en producción (CU-O19 genera, CU-O20 actualiza estado a partir de fuentes reales vía `disrupciones-spec.md`). Esta funcionalidad existe **únicamente** para que un Administrador pueda preparar escenarios reproducibles de demostración/sustentación (p. ej. forzar un retraso o cancelación sobre un vuelo concreto para mostrar el flujo de notificación en vivo), no para operación diaria ni para corregir datos reales.

### RF-VUE-006 — Forzar/ajustar puntualmente un vuelo del catálogo (demo)
El sistema debe permitir a un Administrador seleccionar un vuelo existente en `vuelos_catalogo` y forzar manualmente su `estado` (y, si se requiere para el escenario, otros campos operativos como horario) fuera del flujo automático de CU-O19/O20. La acción exige un motivo obligatorio y queda marcada de forma distinguible de un cambio real (RN-VUE-005). Incluye `<<include>>` la verificación de sesión activa (CU-O42), la verificación de permisos RBAC (CU-O43) y el registro en auditoría (CU-O41), igual que cualquier otra acción de Administrador. Si el nuevo estado forzado corresponde a una disrupción (`retrasado`, `cancelado`, `desviado`), dispara el mismo flujo de detección/notificación que usaría un cambio real (`disrupciones-spec.md`, CU-O29/O30), para que el escenario de demo sea reproducible de punta a punta.

---

## Funcionalidad 6: Filtrar resultados de vuelos (CU-O53) — *(nuevo v3.1, parcialmente implementado)*

Extiende a CU-O17 (búsqueda) — no es un CU independiente en el flujo, es una capacidad adicional sobre el mismo resultado.

### RF-VUE-007 — Filtrar y ordenar resultados de búsqueda *(parcial: solo aerolínea implementado)*
El sistema debe permitir filtrar los resultados de CU-O17 por escalas, aerolínea, equipaje incluido, rango horario y duración, y ordenarlos por precio, duración o número de escalas, aplicando cada filtro de forma instantánea sin botón "Aplicar" (REG-J9). **Estado real:** `vuelos_repo.py` solo soporta `aerolinea_id` como filtro server-side hoy; escalas/equipaje/horario/duración y el ordenamiento no están implementados.

## Funcionalidad 7: Ver predicción de precio de vuelo (CU-O51) — *(nuevo v3.1, no implementado)*

### RF-VUE-008 — Ver predicción de precio de vuelo *(pendiente de implementación)*
El sistema debe mostrar, para una ruta/fecha consultada, una predicción de precio ("buen momento para comprar") a partir de `predicciones_precio_ruta`: precio mínimo histórico, nivel de precio (`typical`/`low`/`high`), rango típico y tendencia (subir/bajar/estable), calculados por un job propio a partir del histórico de precios de Google Flights (`price_insights`). Tabla de resultados pre-calculados, no se computa en el momento de la búsqueda del pasajero.

## Funcionalidad 8: Ver riesgo de disrupción de un vuelo (CU-O52 — RF, mecanismo/dato) — *(nuevo v3.1, no implementado)*

Mismo patrón de doble documentación que CU-O45/O47: el **dato** (`vuelos_catalogo.risk_score`/`risk_score_fuente`) es propiedad de este módulo porque vive en su tabla; el **cálculo** (CU-O83) es responsabilidad de `disrupciones-spec.md`, que lo escribe en el mismo job de catálogo.

### RF-VUE-009 — Ver riesgo de disrupción de un vuelo *(pendiente de implementación)*
El sistema debe mostrar al pasajero, junto al detalle de un vuelo, su `risk_score` (0-1) y de qué fuente proviene: `historico_us` (MinIO `agg_otp_aerolinea_mes`/`agg_causas_retraso_mes`, para rutas dentro de EE. UU.) o `estimado_intl` (AeroDataBox `/airports/{code}/delays`, única fuente disponible para rutas internacionales — insumo real confirmado: `delayIndex`). El cálculo/escritura del campo es de CU-O83 (`disrupciones-spec.md`); este módulo solo lo lee y lo presenta.

## Funcionalidad 9: Clase de cabina y selección de asiento (CU-O114–O117) — *(nuevo v3.1, no implementado)*

Flujo completo confirmado con datos reales (Google Flights da Economy/Business/First con precios reales) y reglas de negocio de industria confirmadas por el cliente durante la sesión de diseño de BD.

### RF-VUE-010 — Ver y seleccionar clase de cabina disponible (CU-O114) *(pendiente de implementación)*
El sistema debe mostrar, para un vuelo, las clases de cabina disponibles (`tarifas_vuelo.clase_cabina`: economy/business/first) con su precio real cuando la ruta tiene datos frescos de Google Flights (rotación de cuota, ver CU-T41), extendiendo a CU-O18 (ver detalle).

### RF-VUE-011 — Ver mapa de asientos disponibles de un vuelo (CU-O115) *(pendiente de implementación)*
El sistema debe mostrar el mapa de asientos real de un vuelo concreto (`asientos_vuelo`: fila, columna, tipo, `es_premium`, `recargo`, `disponible`), generado por el mismo job de catálogo como regla de negocio (no hay fuente externa de mapas de asiento reales). **Regla confirmada:** el recargo depende únicamente de `es_premium` (salida de emergencia/extra legroom/primeras filas), no del tipo de asiento (ventana/pasillo/medio) — un asiento de ventana estándar es gratis igual que uno de pasillo.

### RF-VUE-012 — Seleccionar asiento (CU-O116, `<<extend>>` de CU-O21/O22/O23) *(pendiente de implementación)*
El sistema debe permitir elegir un asiento del mapa (RF-VUE-011) al reservar o modificar una reserva, cobrando el recargo si `es_premium = true`. **Regla confirmada por ventana de check-in:** en tarifa Standard/Flex (`niveles_tarifa.seleccion_asiento_temprana = true`) se puede elegir un asiento estándar desde el momento de la reserva; en tarifa Light (`= false`) el estándar solo se habilita cuando abre el check-in gratuito (`configuracion_sistema.disponibilidad_asientos.horas_antes_checkin_gratis`, ver CU-T40) — antes de eso, en Light solo se puede pagar por un asiento premium de inmediato. El asiento elegido se registra en `reserva_pasajeros.asiento_id` (relation real a `asientos_vuelo`, ver nota de migración en `reservas-spec.md`) con `asiento_asignado_por = pasajero`.

### RF-VUE-013 — Asignar asiento automáticamente (CU-O117) *(pendiente de implementación)*
El sistema debe, mediante un proceso automático disparado por temporizador (análogo a CU-O44), asignar un asiento a todo pasajero que no eligió ninguno antes de que se cumpla la ventana configurada, registrando `asiento_asignado_por = sistema`. **Regla de negocio confirmada, no es un bug a prevenir:** en vuelos llenos, la asignación automática puede separar a un grupo que viaja junto si no eligieron a tiempo.

### RNF-VUE-004 — Recargo de asiento premium configurable *(pendiente de implementación)*
El recargo de un asiento premium y la proporción de asientos premium por tipo de avión se leen de `configuracion_sistema.disponibilidad_asientos` (categoría nueva del dbml v3); mientras el nivel Táctico (CU-T39) no tenga su `spec.md` redactado, se usa un valor por defecto documentado en código.

---

## Reglas de negocio

- **RN-VUE-001** — Un vuelo generado por el sistema (`generado_por = sistema`) nace siempre en estado `programado`, nunca en un estado que implique un evento ya ocurrido.
- **RN-VUE-002** — El precio final por nivel de tarifa (`tarifas_vuelo.precio_final`) es independiente del `precio_base` del vuelo; cada nivel (Light/Standard/Flex) tiene su propio precio y su propio cupo.
- **RN-VUE-003** — Ningún proceso de este módulo crea, modifica o elimina registros del modelo dimensional heredado (`dim_*`, `agg_*`, `fact_vuelo`); toda lectura es de solo consulta (REG-A2).
- **RN-VUE-004** — La verificación de disponibilidad de cupo (CU-O45) nunca deja el sistema en un estado donde se venda más cupo del disponible, sin importar cuántas solicitudes concurrentes lo invoquen (resuelve la mitad "mecanismo" de QP-08; la mitad "negocio" se resuelve en `reservas-spec.md`).
- **RN-VUE-005** — *(Nueva, CU-O48)* Todo ajuste manual vía CU-O48 queda marcado de forma distinguible de un cambio real (p. ej. `origen_generacion = manual` u origen equivalente registrado en el detalle de auditoría), nunca mezclado silenciosamente con datos generados por CU-O19/O20.
- **RN-VUE-006** — *(Nueva, CU-O48)* CU-O48 no reemplaza ni interfiere con el catálogo automático (CU-O19) ni con la actualización real de estado (CU-O20); es exclusivamente una vía de preparación de demostraciones reproducibles, nunca una funcionalidad de operación diaria. Sin motivo explícito ingresado, el ajuste se rechaza.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /vuelos/buscar` | Origen, destino, fecha(s), pasajeros, filtros/orden opcionales | HTML/JSON con lista de vuelos y niveles de tarifa disponibles |
| `GET /vuelos/{id}` | ID de vuelo | HTML/JSON con detalle del vuelo y sus niveles de tarifa |
| `POST /internal/vuelos/generar-catalogo` | Disparado por Airflow, sin input de usuario | Vuelos y tarifas creados en `vuelos_catalogo`/`tarifas_vuelo` |
| `POST /internal/vuelos/{id}/estado` | Nuevo estado, origen del cambio (API real / correo / manual) | Vuelo actualizado, dispara notificación si aplica (Disrupciones) |
| `POST /internal/tarifas/{id}/verificar-cupo` | ID de tarifa, cantidad solicitada | Confirmación de cupo reservado o mensaje de no disponibilidad |
| `POST /backoffice/vuelos/{id}/forzar-estado` | Cookie JWT (Admin), nuevo estado/campos, motivo obligatorio | Vuelo ajustado marcado como manual/demo + auditoría, o mensaje de bloqueo RBAC/motivo faltante |

---

## Historias de usuario

- **HU-VUE-01:** Como pasajero, quiero buscar vuelos por origen, destino y fecha, para encontrar opciones que se ajusten a mi viaje.
- **HU-VUE-02:** Como pasajero, quiero ver el detalle y los niveles de tarifa de un vuelo, para elegir la opción que mejor se ajusta a mi presupuesto y necesidad de flexibilidad.
- **HU-VUE-03:** Como sistema, quiero generar automáticamente el catálogo de vuelos programables, para que siempre haya opciones vigentes disponibles para búsqueda.
- **HU-VUE-04:** Como sistema, quiero actualizar el estado de un vuelo cuando cambia, para que el resto del sistema (reservas, disrupciones) refleje la realidad operativa.
- **HU-VUE-05:** Como administrador, quiero forzar puntualmente el estado de un vuelo del catálogo con fines exclusivos de demostración, para poder mostrar el flujo completo de disrupción/notificación de forma reproducible sin depender de que ocurra un evento real.

---

## Objetivo

Sostener un catálogo de vuelos siempre vigente y confiable — generado automáticamente a partir del modelo dimensional heredado, con estado sincronizado a la realidad operativa — que permita al pasajero buscar y comparar opciones con transparencia total de precio, y que garantice al módulo de Reservas que ningún cupo se vende dos veces.

---

## Escenarios

### Camino feliz
1. El sistema genera el catálogo de vuelos programables cada ciclo (CU-O19).
2. Un pasajero busca vuelos por origen/destino/fecha (CU-O17) y ve resultados filtrables.
3. Selecciona un vuelo y revisa el detalle y los niveles de tarifa (CU-O18).
4. Procede a reservar; `reservas-spec.md` invoca la verificación de cupo de este módulo (CU-O45) antes de confirmar.
5. Días después, la aerolínea retrasa el vuelo; el sistema actualiza su estado (CU-O20), lo que dispara el flujo de disrupciones.

### Manejo de errores
- **Sin resultados de búsqueda:** se muestra mensaje claro y sugerencia de fechas cercanas (cuando exista CU-O51, ver nota de corrección al inicio del documento).
- **Cupo agotado al momento de reservar:** el servicio de verificación responde sin disponibilidad; `reservas-spec.md` define cómo se comunica al pasajero.
- **Dos solicitudes concurrentes por el último cupo:** solo una obtiene el decremento atómico; la otra recibe "no disponible" (RNF-VUE-003).
- **Generación de catálogo sin rutas vigentes en el modelo heredado:** el ciclo no genera vuelos para esa ruta y se registra para revisión, sin fallar el resto del proceso.
- **Ajuste puntual (CU-O48) sin permiso RBAC o sin sesión válida:** se bloquea antes de tocar datos, igual que cualquier otra acción de Administrador.
- **Ajuste puntual (CU-O48) sin motivo ingresado:** se rechaza, exigiendo justificación explícita (RN-VUE-006).

### Escenario excepcional: preparar una demo reproducible
1. Un Administrador, fuera del flujo normal, selecciona un vuelo del catálogo y fuerza su estado a `retrasado` con un motivo ("demo sustentación") (CU-O48).
2. El sistema verifica sesión y RBAC (CU-O42, CU-O43), aplica el cambio marcándolo como manual/demo (RN-VUE-005), y lo audita (CU-O41).
3. Como el nuevo estado es una disrupción, se dispara el mismo flujo de notificación que usaría un evento real (`disrupciones-spec.md`), permitiendo mostrar el flujo completo sin esperar a que ocurra un cambio real.

---

## Criterios de aceptación

- **CU-O17:** Dado que existe catálogo de vuelos generado, cuando un pasajero busca por origen/destino/fecha, entonces ve una lista filtrable y ordenable de vuelos que cumplen los criterios, o un mensaje claro si no hay resultados.
- **CU-O18:** Dado que un pasajero selecciona un vuelo, cuando accede a su detalle, entonces ve horarios, aerolínea y todos los niveles de tarifa disponibles con su precio y política de reembolso.
- **CU-O19:** Dado que existen rutas vigentes en el modelo dimensional heredado, cuando se ejecuta el ciclo automático de generación, entonces se crean nuevos registros en `vuelos_catalogo` en estado `programado`, sin escribir en la capa heredada.
- **CU-O20:** Dado que se detecta un cambio real en un vuelo (vía CU-O27/O29), cuando el sistema actualiza su estado, entonces `vuelos_catalogo.estado` y `fecha_actualizacion_estado` quedan reflejados de inmediato.
- **CU-O45:** Dado que una tarifa tiene cupo disponible, cuando se invoca la verificación, entonces el cupo se decrementa de forma atómica y se confirma la disponibilidad; si el cupo es cero, se responde sin disponibilidad sin alterar el dato.
- **CU-O48:** Dado que un Administrador con permiso RBAC y sesión activa selecciona un vuelo y proporciona un motivo, cuando fuerza puntualmente su estado, entonces el vuelo queda ajustado y marcado como manual/demo, auditado, y si el estado es de disrupción, dispara el flujo de notificación; sin motivo, la acción se rechaza.
- **CU-O51** *(pendiente):* Dado que existe histórico de precio de Google Flights para una ruta, cuando el pasajero consulta la predicción, entonces ve nivel de precio, rango típico y tendencia calculados por el job propio.
- **CU-O52** *(pendiente):* Dado que un vuelo tiene `risk_score` calculado por CU-O83, cuando el pasajero ve su detalle, entonces se muestra el score y su fuente (histórico US o estimado internacional).
- **CU-O53** *(parcial):* Dado que existen resultados de búsqueda, cuando el pasajero filtra por aerolínea, entonces la lista se actualiza al instante; los demás filtros (escalas/equipaje/horario/duración) y el ordenamiento no están implementados todavía.
- **CU-O114** *(pendiente):* Dado que un vuelo tiene tarifas en más de una clase de cabina, cuando el pasajero ve el detalle, entonces puede elegir la clase disponible con su precio real.
- **CU-O115** *(pendiente):* Dado que un vuelo tiene su mapa de asientos generado, cuando el pasajero lo consulta, entonces ve cada asiento con su disponibilidad y si es premium.
- **CU-O116** *(pendiente):* Dado que un pasajero está en el flujo de reserva/modificación y su tarifa permite elegir asiento en ese momento, cuando selecciona uno, entonces queda registrado y se cobra el recargo si es premium.
- **CU-O117** *(pendiente):* Dado que un pasajero no eligió asiento antes de la ventana configurada, cuando se cumple esa ventana, entonces el sistema le asigna uno automáticamente.

---

## Dependencias

- **Seguridad:** sesión (CU-O42) y RBAC (CU-O43) para acciones de backoffice sobre vuelos, incluyendo CU-O48; búsqueda pública (CU-O17/O18) no requiere autenticación.
- **Modelo dimensional heredado (MinIO, solo lectura):** `dim_ruta`, `dim_aeropuerto`, `dim_aerolinea`, `dim_avion` — fuente de la generación de catálogo y de la resolución de nombres legibles.
- **Nivel Estratégico (previsto):** Airflow, heredado del proyecto anterior, es el motor de ejecución de CU-O19; el DAG del simulador de riesgo (CU-E01) es un consumidor futuro de este catálogo, no una dependencia de este módulo.
- **Disrupciones:** CU-O48 reutiliza el mismo flujo de detección/notificación que `disrupciones-spec.md` define para un cambio real, cuando el estado forzado corresponde a una disrupción; CU-O83 (risk score) escribe el dato que CU-O52 solo lee.
- **Reservas:** CU-O116 es `<<extend>>` de CU-O21/O22/O23 (`reservas-spec.md`), ninguno de los dos lados implementado todavía.
- **Integraciones:** CU-T37/T38 generalizan la config/monitoreo de sincronización que CU-T06/T07 ya resuelven específicamente para este módulo.

---

## Casos de uso relacionados

- CU-O21, O22, O23 (Reservas) — invocan CU-O45 como precondición obligatoria; CU-O116 los extiende.
- CU-O27, O29 (Disrupciones) — disparan CU-O20 cuando detectan un cambio real; CU-O48 dispara el mismo flujo de forma manual y excepcional.
- CU-O41, O42, O43 (Seguridad) — incluidos obligatoriamente por CU-O48, igual que cualquier otra acción de Administrador.
- CU-O83 (Disrupciones) — calcula el `risk_score` que CU-O52 presenta.
- CU-O49 (Pasajeros) — país de emisión de pasaporte, relevante si a futuro se cruza con clase de cabina/requisitos por ruta internacional.
- CU-T39, T40, T41 (previsto, Táctico) — recargo de asiento premium, ventana de check-in gratuito, y rotación de cuota de clase de cabina, condicionan RF-VUE-010/012/013.

---

## Fuera de alcance

- **Corregido 2026-07-18:** la nota anterior aquí decía "Tendencia histórica de precio/puntualidad (CU-T18, Táctico previsto)" — ya NO es correcto en dos sentidos: (a) ese concepto es CU-O51, ya en el catálogo Operativo, no un CU-T previsto; (b) CU-T18 hoy significa otra cosa (política de reembolsos, en Reservas). CU-O51 pasó de "fuera de alcance" a "en alcance, pendiente de implementación" (Funcionalidad 7).
- Configuración de reglas de programación (frecuencia por ruta, aerolíneas activas) — hoy son parámetros del proceso Airflow, no una pantalla de configuración (pertenece a CU-T06, Táctico — *corregido 2026-07-18, antes decía CU-T15, que hoy es de Paquetes, no de Vuelos*).
- Alta manual de vuelos nuevos en el catálogo por backoffice — el catálogo se genera únicamente por el proceso automático (CU-O19); CU-O48 permite ajustar puntualmente un vuelo **ya existente**, nunca crear uno nuevo.
- Uso de CU-O48 en producción como mecanismo de corrección de datos reales — es exclusivamente una vía de preparación de demostraciones; cualquier corrección de datos reales fuera de ese propósito queda fuera de alcance de este RF.
- Ofrecer cabinas reales Business/First de forma sistemática en todas las rutas — el dbml v3 documenta que esto no se probó de forma sistemática (impacto en cuota de Google Flights, 250/mes); evaluar al implementar CU-O114.
