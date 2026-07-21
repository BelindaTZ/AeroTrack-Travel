# Especificación Táctica — Integraciones

**Módulo:** Integraciones
**Prefijo:** INT
**Código fuente:** `app/integraciones/` *(implementado 2026-07-19)*
**Casos de uso cubiertos:** CU-T37 (Configurar fuente de datos externa), CU-T38 (Ver bitácora de sincronizaciones de catálogos externos)
**Actor:** Administrador

> **Estado:** implementado y probado (2026-07-19, `pytest app/integraciones` 10/10). **Único módulo 100% táctico** — no tiene nivel Operativo (0 CU-O). Generaliza a las 5 verticales de producto (Vuelos, Hoteles, Autos, Actividades, Cruceros) lo que antes solo existía para Vuelos (CU-T06/T07) — **no los reemplaza**, coexiste como configuración/monitoreo transversal. **Precondición real de los 5 módulos de catálogo**: cada uno de sus jobs de generación (CU-O19, O118, O119, O120, O122) escribe en `sincronizaciones_log` y lee su frecuencia de `fuentes_datos_externas` — sin este módulo, esos jobs pueden funcionar con configuración hardcodeada temporal, pero no de la forma prevista por el catálogo. **Pendiente real (CHK010):** ningún job de catálogo de ninguna vertical llama todavía a una API externa (Vuelos sigue siendo 100% sintético) — la bitácora funciona pero no tiene todavía ninguna corrida automática real que mostrar, solo las que un Administrador dispare manualmente (que hoy se registran como `fallido`, honestamente, porque el job real no existe).

---

## Funcionalidad 1: Configurar fuente de datos externa (CU-T37)

### RF-INT-001 — Configurar fuente de datos externa
El sistema debe permitir a un Administrador ver y editar, para cada fuente registrada en `fuentes_datos_externas` (AeroDataBox, Google Flights/SerpApi, HotelLens, Global Rental Cars, Travel Advisor, Cruise Pricing API, ExchangeRate-API, Visa Requirement, SendGrid, Gmail API, OpenSky Network, Stripe, Groq, Gemini, y las filas `tipo_uso = regla_negocio_interna` de disponibilidad sintética), su frecuencia de sincronización (`frecuencia_sincronizacion_horas`, solo aplica a `catalogo_periodico`), activarla/desactivarla, y ver la cuota consumida hasta el momento (`sincronizaciones_log.unidades_cuota_consumidas` agregado).

### RN-INT-001 — No todas las fuentes son configurables de la misma forma
Según `tipo_uso` (`constante` | `catalogo_periodico` | `cache_bajo_demanda` | `regla_negocio_interna`), los campos editables difieren: solo `catalogo_periodico` tiene `frecuencia_sincronizacion_horas` real; las fuentes `constante` (SendGrid, Gmail, Stripe, Groq/Gemini, OpenSky) no tienen frecuencia, solo activar/desactivar; `regla_negocio_interna` (disponibilidad sintética) no tiene host real, solo referencia a la configuración de negocio correspondiente (`configuracion_sistema.disponibilidad_*`).

### RN-INT-002 — Desactivar una fuente no borra el último dato generado
Desactivar una fuente detiene sus corridas futuras, pero el catálogo ya generado con ella permanece disponible para búsqueda — mismo criterio de degradación ordenada que ya rige Disrupciones (constitución E3), aplicado aquí a cualquier fuente de catálogo.

---

## Funcionalidad 2: Ver bitácora de sincronizaciones (CU-T38)

Generaliza a CU-T07 (Vuelos) para las demás fuentes `catalogo_periodico`.

### RF-INT-002 — Ver bitácora de sincronizaciones de catálogos externos
El sistema debe mostrar a un Administrador el historial de corridas (`sincronizaciones_log`): fuente, tipo de producto, fecha de inicio/fin, estado (éxito/fallo/parcial), registros procesados/nuevos/actualizados, cuota consumida, y si fue automática (Airflow) o manual (`ejecutado_por` poblado). Filtrable por fuente y rango de fechas, con filtros instantáneos (REG-J9).

### RN-INT-003 — Una corrida fallida o parcial no oculta la anterior exitosa
El catálogo servido al pasajero sigue siendo el de la última corrida exitosa — una corrida fallida se registra y se hace visible aquí, pero no borra ni reemplaza datos ya generados correctamente (mismo principio que RN-INT-002).

---

## Reglas de negocio

- **RN-INT-001** — *(Funcionalidad 1)* Los campos configurables dependen de `tipo_uso` de cada fuente.
- **RN-INT-002** — *(Funcionalidad 1)* Desactivar una fuente no borra el catálogo ya generado.
- **RN-INT-003** — *(Funcionalidad 2)* Una corrida fallida no reemplaza datos de una corrida exitosa anterior.
- **RN-INT-004** — Toda edición de configuración de fuente se audita (CU-O41), con `fuentes_datos_externas.modificado_por` como registro adicional específico del dominio.

---

## Entradas y salidas

| Endpoint | Entradas | Salidas |
|----------|----------|---------|
| `GET /backoffice/integraciones/fuentes` | Cookie JWT (Admin) | HTML/JSON con las fuentes registradas y su estado |
| `PUT /backoffice/integraciones/fuentes/{id}` | Cookie JWT (Admin), campos según `tipo_uso` | Fuente actualizada |
| `GET /backoffice/integraciones/bitacora` | Cookie JWT (Admin), filtros de fuente/fecha | HTML/JSON con el historial de corridas |
| `POST /backoffice/integraciones/fuentes/{id}/resincronizar` | Cookie JWT (Admin) | Corrida manual disparada, `ejecutado_por` poblado |

---

## Historias de usuario

- **HU-INT-01:** Como administrador, quiero configurar la frecuencia y el estado de cada fuente de datos externa, para controlar el consumo de cuota sin tocar código.
- **HU-INT-02:** Como administrador, quiero ver la bitácora de sincronizaciones, para detectar rápido si una fuente empezó a fallar.
- **HU-INT-03:** Como administrador, quiero disparar una resincronización manual, para forzar una actualización sin esperar el ciclo automático.

---

## Objetivo

Dar visibilidad y control centralizado sobre las ~18 fuentes de datos externas del sistema (catálogos periódicos, integraciones constantes y reglas de negocio internas), generalizando lo que antes solo existía para Vuelos, sin duplicar su mecanismo específico.

---

## Escenarios

### Camino feliz
1. Un Administrador ve las fuentes registradas (`fuentes_datos_externas`) y ajusta la frecuencia de HotelLens de 6h a 12h para no agotar cuota (CU-T37).
2. El siguiente ciclo respeta la nueva frecuencia.
3. Días después, revisa la bitácora (CU-T38) y ve que una corrida de Travel Advisor falló por rate limit — la actividad sigue mostrando el último catálogo exitoso.
4. Dispara una resincronización manual de esa fuente.

### Manejo de errores
- **Fuente `regla_negocio_interna` con intento de editar `frecuencia_sincronizacion_horas`:** el campo no aplica, se bloquea o se oculta según `tipo_uso` (RN-INT-001).
- **Corrida fallida:** se registra en la bitácora, sin afectar el catálogo ya servido (RN-INT-002/003).

---

## Criterios de aceptación

- **CU-T37:** Dado que un Administrador edita una fuente, cuando guarda, entonces los campos editados respetan las reglas de su `tipo_uso`; desactivarla no borra el catálogo ya generado.
- **CU-T38:** Dado que existen corridas registradas, cuando un Administrador consulta la bitácora, entonces las ve filtrables por fuente y fecha, con su estado y cuota consumida; una corrida fallida no oculta el dato de la última exitosa.

---

## Dependencias

- **Vuelos, Hoteles, Autos, Actividades, Cruceros:** cada uno dispara sus jobs de catálogo (CU-O19, O118–O122) leyendo `fuentes_datos_externas` y escribiendo en `sincronizaciones_log` que este módulo expone.
- **Seguridad:** RBAC (CU-O43), sesión (CU-O42), auditoría (CU-O41).
- **Vuelos (`vuelos-spec.md`):** CU-T06/T07 siguen siendo la config/monitoreo específica de Vuelos — este módulo los generaliza para las otras 4 verticales, sin reemplazarlos.

---

## Casos de uso relacionados

- CU-O19 (Vuelos), CU-O118 (Hoteles), CU-O119 (Autos), CU-O120 (Actividades), CU-O122 (Cruceros) — todos consumen la configuración y alimentan la bitácora de este módulo.
- CU-T06, T07 (Vuelos, Táctico) — configuración/monitoreo específico de Vuelos, paralelo a este módulo, no reemplazado.

---

## Fuera de alcance

- Alertas automáticas (email/Slack) cuando una fuente falla repetidamente — el catálogo de CU solo define visualización de la bitácora, no un sistema de alertas proactivas; si se necesita, es un RF nuevo.
- Edición de credenciales (API keys) desde esta UI — `fuentes_datos_externas.host_env_var` solo referencia el *nombre* de la variable de entorno, nunca su valor (REG-B3); el valor real se gestiona fuera de la aplicación.
