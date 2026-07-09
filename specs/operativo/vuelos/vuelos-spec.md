# Especificación Operativa — Vuelos (catálogo)

**Módulo:** Vuelos (catálogo)
**Prefijo:** VUE
**Código fuente:** `app/vuelos/`
**Casos de uso cubiertos:** CU-O17 (Buscar vuelos disponibles), CU-O18 (Ver detalle y niveles de tarifa de un vuelo), CU-O19 (Generar catálogo de vuelos programables), CU-O20 (Actualizar estado de un vuelo), CU-O45 (Verificar disponibilidad de vuelo/cupo — RF, mecanismo/dato), CU-O48 (Forzar/ajustar puntualmente un vuelo del catálogo — solo pruebas/demo)
**Actor:** Pasajero / Sistema (automático, Airflow) / Administrador (CU-O48, vía excepcional)

---

## Funcionalidad 1: Buscar y consultar vuelos disponibles (CU-O17, CU-O18)

Permite a cualquier pasajero, autenticado o no, explorar el catálogo de vuelos programables y sus niveles de tarifa.

### RF-VUE-001 — Buscar vuelos disponibles
El sistema debe permitir a un pasajero ingresar origen, destino, fecha(s) y número de pasajeros, y consultar el catálogo de vuelos programables (`vuelos_catalogo`) filtrando por esos criterios. Muestra resultados con aerolínea, horario, duración, escalas, precio base y niveles de tarifa disponibles (Light/Standard/Flex). Permite ordenar por precio, duración o escalas, y filtrar por aerolínea o rango horario, aplicando cada filtro secundario de forma instantánea sin botón "Aplicar" (REG-J9) — la búsqueda principal (origen/destino/fecha/pasajeros) sigue siendo una acción explícita de conversión con su propio botón. Si no hay vuelos que cumplan los criterios, muestra un mensaje claro; cuando exista el nivel Táctico, este flujo reutilizará CU-T18 (tendencia histórica) para sugerir fechas cercanas.

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
- **Sin resultados de búsqueda:** se muestra mensaje claro y sugerencia de fechas cercanas (cuando exista CU-T18).
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

---

## Dependencias

- **Seguridad:** sesión (CU-O42) y RBAC (CU-O43) para acciones de backoffice sobre vuelos, incluyendo CU-O48; búsqueda pública (CU-O17/O18) no requiere autenticación.
- **Modelo dimensional heredado (MinIO, solo lectura):** `dim_ruta`, `dim_aeropuerto`, `dim_aerolinea`, `dim_avion` — fuente de la generación de catálogo y de la resolución de nombres legibles.
- **Nivel Estratégico (previsto):** Airflow, heredado del proyecto anterior, es el motor de ejecución de CU-O19; el DAG del simulador de riesgo (CU-E01) es un consumidor futuro de este catálogo, no una dependencia de este módulo.
- **Disrupciones:** CU-O48 reutiliza el mismo flujo de detección/notificación que `disrupciones-spec.md` define para un cambio real, cuando el estado forzado corresponde a una disrupción.

---

## Casos de uso relacionados

- CU-O21, O22, O23 (Reservas) — invocan CU-O45 como precondición obligatoria.
- CU-O27, O29 (Disrupciones) — disparan CU-O20 cuando detectan un cambio real; CU-O48 dispara el mismo flujo de forma manual y excepcional.
- CU-O41, O42, O43 (Seguridad) — incluidos obligatoriamente por CU-O48, igual que cualquier otra acción de Administrador.
- CU-T18 (previsto, Táctico) — tendencia histórica de precio/puntualidad por ruta, complementará CU-O17 cuando no haya resultados.

---

## Fuera de alcance

- Tendencia histórica de precio/puntualidad por ruta (CU-T18, nivel Táctico previsto).
- Configuración de reglas de programación (frecuencia por ruta, aerolíneas activas) — hoy son parámetros del proceso Airflow, no una pantalla de configuración (pertenecería a CU-T15, Táctico).
- Alta manual de vuelos nuevos en el catálogo por backoffice — el catálogo se genera únicamente por el proceso automático (CU-O19); CU-O48 permite ajustar puntualmente un vuelo **ya existente**, nunca crear uno nuevo.
- Uso de CU-O48 en producción como mecanismo de corrección de datos reales — es exclusivamente una vía de preparación de demostraciones; cualquier corrección de datos reales fuera de ese propósito queda fuera de alcance de este RF.
