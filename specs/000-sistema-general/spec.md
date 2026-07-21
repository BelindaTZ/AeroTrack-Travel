# Especificación General — Sistema AeroTrack Travel

**Nivel:** Operativo y Táctico (los dos niveles en alcance de esta entrega; Estratégico sigue previsto)
**Creado:** 2026-07-09 · **Actualizado:** 2026-07-18 (alcance ampliado a 165 CU / 17 módulos, ver nota de migración)
**Estado:** Draft
**Fuentes de verdad:** `docs/aerotrack-travel-casos-de-uso-v3.md` (catálogo de CU, v3.1),
`docs/aerotrack-travel-propuesta-tablas-v3.dbml` (esquema de datos), `docs/aerotrack-travel-documento-empresarial.md`,
`.specify/memory/constitution.md`. `specs/000-sistema-general/analisis-cus-completo.md` es el análisis
derivado (relaciones, escenarios, matriz técnica) sobre ese catálogo.

> **Nota de migración (2026-07-18):** esta especificación describía originalmente 48 CU-O en 6
> módulos, un único nivel Operativo, y un alcance de producto limitado a vuelos. El catálogo fuente
> evolucionó (sesión de diseño de BD 2026-07-17): ahora son **165 CU (122 CU-O + 43 CU-T) en 17
> módulos**, con el nivel Táctico ya redactado como catálogo (antes "previsto"), y el alcance de
> producto se amplió a seis verticales (vuelos, hoteles, autos, actividades, cruceros, paquetes).
> Este documento se actualiza para reflejar ese alcance. Los 6 módulos-spec ya redactados
> (Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación) no se tocan en esta pasada —
> solo este documento y el resto de `000-sistema-general/`.

---

## Resumen ejecutivo

AeroTrack Travel es una agencia de viajes digital minorista (Miami, FL) que vende y gestiona
**seis verticales de producto** — vuelos, hoteles, autos de renta, actividades, cruceros y
paquetes combinados — con alcance internacional (ya no limitado a EE. UU. doméstico). Su
diferenciador es la **gestión proactiva de disrupciones**: vincula cada reserva de vuelo con el
estado operacional real (API de estado real, monitoreo automático de correo, estimación
estadística) y notifica automáticamente cualquier cambio relevante, sin depender de que un agente
humano reenvíe el aviso. Ese diferenciador sigue siendo exclusivo de Vuelos — las demás verticales
no tienen equivalente de disrupciones en este catálogo.

Esta entrega especifica los **165 CU del catálogo v3.1** (122 Operativos + 43 Tácticos) en
**17 módulos**: los seis de venta/producto (Vuelos, Hoteles, Autos, Actividades, Cruceros,
Paquetes) más Reservas y Carrito como flujo de compra transversal a todos ellos, Seguridad e
Integraciones (Tecnología y Sistemas), Pasajeros y Cuenta/Mis Viajes (Gestión de Clientes),
Disrupciones y Centro de Ayuda (Operaciones), Facturación (Finanzas), y Ofertas y Promociones más
Asistente IA (Comercial y Marketing). CU-O48 (forzar/ajustar puntualmente un vuelo, vía excepcional
de demo) sigue siendo el único CU fuera del catálogo fuente original, añadido durante la redacción
de `vuelos-spec.md`.

## Alcance de esta entrega

**En alcance:** las 16 specs de módulo Operativo bajo `specs/operativo/` y las 17 specs de módulo
Táctico bajo `specs/tactico/` (una carpeta por módulo en cada nivel — nunca CU-O y CU-T mezclados
en el mismo `spec.md`, ver `analisis-cus-completo.md` sección 4), más este directorio
`000-sistema-general/` como base transversal. Solo especificación (nivel `spec.md`) — no incluye
`plan.md`/`tasks.md`/`checklist.md` de Spec Kit para los módulos nuevos todavía; los 6 módulos ya
redactados (Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación) sí los tienen, de
una ronda anterior.

**Fuera de alcance (documentado, no especificado):**
- Nivel Estratégico (2 CU-E previstos: simulador de riesgo — ya implementado como DAG, y medición
  de efectividad de notificación).
- Cualquier certificación formal de la industria aérea (IATA/IATAN, BSP/ARC, GDS, NDC completo) —
  ver `consideraciones.md` sección 7.
- Pipeline ELT/predictivo heredado del proyecto anterior (AeroTrack Analytics) — el catálogo v3
  ya no reserva un departamento "Ingeniería y Analítica de Datos" separado; lo que antes se
  proyectaba ahí (predictivo, Asistente IA) se resolvió distinto: el simulador de riesgo quedó
  como mecanismo Estratégico consumido por Disrupciones, y **Asistente IA es ahora un módulo
  Operativo/Táctico en scope** (Comercial y Marketing) — ya no es alcance futuro reservado, es
  parte de esta entrega (CU-O106–O111, CU-T33–T34).

Ver el detalle completo de módulos, rangos de CU y relaciones en `docs/aerotrack-travel-casos-de-uso-v3.md`
y en `analisis-cus-completo.md`.

## Actores del sistema

| Actor | Naturaleza | Módulos donde actúa principalmente |
|---|---|---|
| **Pasajero** | Humano, cliente final | Los 17 módulos, salvo Integraciones (sin superficie de pasajero) |
| **Agente** | Humano, interno | Pasajeros (backoffice), Reservas (asistida), Disrupciones (consulta), Facturación (reembolsos), Centro de Ayuda (casos escalados) |
| **Administrador** | Humano, interno | Seguridad e Integraciones (dueño), Facturación (conciliación/remesas), backoffice en general de los 17 módulos |
| **Sistema** | Automático (Airflow, temporizadores, listeners, sincronizadores de catálogo) | Vuelos/Hoteles/Autos/Actividades/Cruceros (generación de catálogo), Disrupciones (detección/notificación), Facturación (factura/comisión/conversión de moneda), Integraciones (corridas de sincronización), Transversal (auditoría, sesión, RBAC, expiración) |

## Estructura organizacional (departamentos → módulos → nivel)

El catálogo v3.1 organiza los 17 módulos en **6 departamentos** (el catálogo original preveía un
7º, "Ingeniería y Analítica de Datos", que no sobrevivió a la reorganización — ver nota de
migración arriba):

| Departamento | Módulos | Nivel Operativo | Nivel Táctico |
|---|---|---|---|
| Tecnología y Sistemas (TI) | Seguridad | ✅ Esta entrega | ✅ Esta entrega |
| Tecnología y Sistemas (TI) | Integraciones *(nuevo v3.1)* | — (0 CU-O) | ✅ Esta entrega |
| Gestión de Clientes | Pasajeros | ✅ Esta entrega | ✅ Esta entrega |
| Gestión de Clientes | Cuenta / Mis Viajes | ✅ Esta entrega | ✅ Esta entrega |
| Ventas y Reservas | Vuelos, Hoteles, Autos, Actividades, Cruceros, Paquetes, Reservas, Carrito | ✅ Esta entrega | ✅ Esta entrega |
| Operaciones | Disrupciones, Centro de Ayuda | ✅ Esta entrega | ✅ Esta entrega |
| Finanzas | Facturación | ✅ Esta entrega | ✅ Esta entrega |
| Comercial y Marketing | Ofertas y Promociones, Asistente IA | ✅ Esta entrega | ✅ Esta entrega |
| *(reservado)* | Nivel Estratégico (simulador de riesgo, medición de efectividad) | 📋 Previsto (simulador ya implementado como DAG) | — |

## Los 16 módulos-spec Operativos + 17 módulos-spec Tácticos

Ver la tabla completa (rango de CU, prefijo, carpeta) en `analisis-cus-completo.md` sección 1 y 4.
Resumen de dependencias entre módulos-spec y orden de lectura sugerido: sección 3.4 del mismo
documento. Los 6 módulos con contenido ya redactado (de la ronda anterior, un único nivel
Operativo): Seguridad, Pasajeros, Vuelos, Reservas, Disrupciones, Facturación — sus `spec.md`
actuales referencian numeración de CU-T que cambió de significado al renumerar el catálogo
completo (ver `analisis-cus-completo.md` punto abierto 8); se revisan en una ronda posterior, no
en esta.

## Mecanismos transversales

Tres CU se invocan desde prácticamente todos los demás y se documentan una única vez en
`specs/operativo/seguridad/`, no se repiten módulo por módulo:

- **CU-O41 — Registrar evento en auditoría**: toda mutación, en cualquier módulo, dispara este CU
  (constitución B4 / `reglas.md` REG-B4).
- **CU-O42 — Verificar sesión activa**: toda acción autenticada, excepto login/recuperación de
  contraseña/registro, requiere un token válido.
- **CU-O43 — Verificar permisos de acceso (RBAC)**: toda acción de Agente/Administrador pasa por
  la matriz de permisos de dos niveles (constitución B1 / REG-B1).

CU transversales adicionales que se documentan en dos módulos-spec cada uno, con enfoque distinto
(mecanismo/dato en un lado, orquestación/negocio en el otro — ver `analisis-cus-completo.md`
sección 4.1/4.2 para el detalle completo):

- **CU-O45 — Verificar disponibilidad de vuelo/cupo**: mecanismo/dato en Vuelos, orquestación/negocio en Reservas.
- **CU-O47 — Cobrar/reembolsar diferencia de tarifa**: disparador/negocio en Reservas, mecanismo de cobro en Facturación.
- **CU-O86 — Capturar pago diferido de hotel** *(v3.0)*: disparador/negocio en Hoteles, mecanismo de cobro en Facturación.
- **CU-O100 — Escalar caso no resuelto a agente** *(v3.0)*: se dispara como extend de Asistente IA (CU-O106–O108) cuando no puede resolver la consulta; vive en Centro de Ayuda.
- **CU-T37/T38 — Configurar fuente de datos externa / Ver bitácora de sincronizaciones** *(v3.1, módulo Integraciones)*: generalizan a Hoteles/Autos/Actividades/Cruceros el patrón que CU-T06/T07 ya resolvían solo para Vuelos — no los reemplazan, son paralelos.

## Relación con los demás documentos de esta carpeta

| Archivo | Contenido |
|---|---|
| `analisis-cus-completo.md` | Resumen de los 165 CU por módulo, expansión Jacobson del subconjunto confirmado (CU-O01–O48), mapa de relaciones/dependencias entre módulos-spec, escenarios "qué pasa si" (QP-01 a QP-19), asignación a la estructura `specs/operativo/`/`specs/tactico/`, matriz técnica |
| `glosario.md` | Términos de dominio y técnicos usados en todas las specs de módulo — incluye ahora los 11 módulos añadidos en v3.0/v3.1 |
| `reglas.md` | Los 21 principios constitucionales (A1–H1) + Stack (I) + Diseño de Interfaz (J1–J11), transformados a reglas consultables con código `REG-XX` |
| `consideraciones.md` | Contexto de negocio, alcance de producto (ahora multi-vertical), modelo de ingresos, fuentes de datos reales, y decisiones que condicionan la interpretación de cada spec de módulo |
| `diseno-visual.md` | Sistema de diseño visual v4 (Sky Blue × Modernist híbrido, 2026-07-18) — paleta, tipografía, radios, componentes de referencia |
| `pendientes-implementacion-codigo.md` | Backlog consolidado de lo que falta en código en los 6 módulos ya implementados, tras ampliar sus specs al catálogo v3.0/v3.1 — orden sugerido y dependencias cruzadas |
| `errores-conocidos.md` | Vacío — se completa durante la implementación |

## Criterios de éxito a nivel de sistema

- **CE-01:** Un pasajero puede completar el flujo completo de autoservicio (buscar → seleccionar → pagar → recibir confirmación) para cualquiera de las seis verticales de producto, sin intervención de un agente humano en ningún paso obligatorio.
- **CE-02:** Ninguna disrupción de vuelo detectada por cualquiera de las fuentes operativas (API real, monitor de correo) queda sin generar una notificación verificable al pasajero afectado.
- **CE-03:** Todo movimiento de dinero (cobro, comisión, remesa, reembolso, pago diferido) es trazable de origen a destino y no puede duplicarse por reintento del mismo evento, sin importar la vertical de producto que lo originó.
- **CE-04:** Ninguna acción de creación, modificación o eliminación, en ningún módulo, queda sin su registro correspondiente en el log de auditoría.
- **CE-05:** Ninguna funcionalidad de Agente/Administrador es accesible fuera de la matriz de permisos de dos niveles.
- **CE-06:** El sistema continúa notificando disrupciones de vuelo (vía fuente estadística) aun cuando la API de estado de vuelo en tiempo real no esté disponible.
- **CE-07:** Ninguna fuente de datos externa nueva (Hoteles, Autos, Actividades, Cruceros) que se agote en cuota o falle deja el catálogo de esa vertical sin servir — sigue mostrando el último dato generado y la corrida queda registrada como fallida/parcial en Integraciones.

## Dependencias externas al alcance de esta entrega

- El nivel Táctico ya no es "previsto" — su catálogo de 43 CU-T está en alcance de esta entrega
  (carpetas creadas bajo `specs/tactico/`), pendiente de redactar `spec.md` módulo por módulo. Los
  valores que hoy leerían de configuración táctica y aún no tienen su `spec.md` redactado siguen
  leyéndose de `configuracion_sistema` con un valor por defecto documentado en el módulo Operativo
  que los consume, hasta que se redacte su spec Táctico correspondiente.
- El nivel Estratégico previsto (simulador de riesgo) ya existe técnicamente como DAG de Airflow;
  el módulo Disrupciones (Operativo) solo consume sus resultados cuando corresponda documentarlo,
  no lo reimplementa.
