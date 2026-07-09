# Especificación General — Sistema AeroTrack Travel

**Nivel:** Operativo (único nivel en alcance de esta entrega)
**Creado:** 2026-07-09
**Estado:** Draft
**Fuentes de verdad:** `docs/aerotrack-travel-documento-empresarial.md`, `docs/aerotrack-travel-casos-de-uso-operativos.md`, `docs/aerotrack-travel-propuesta-tablas.dbml`, `.specify/memory/constitution.md`

---

## Resumen ejecutivo

AeroTrack Travel es una agencia de viajes digital minorista (Miami, FL) especializada en boletos aéreos domésticos en EE. UU. Su diferenciador es la **gestión proactiva de disrupciones**: vincula cada reserva con el estado operacional real del vuelo (API de estado real, monitoreo automático de correo, estimación estadística) y notifica automáticamente cualquier cambio relevante, sin depender de que un agente humano reenvíe el aviso.

Esta entrega especifica el **nivel Operativo** completo: 48 casos de uso (CU-O01 a CU-O47 del catálogo fuente, más CU-O48 añadido durante la redacción de specs) organizados en 6 módulos, cubriendo el registro diario del negocio — sesión y RBAC, gestión de pasajeros, catálogo de vuelos, ciclo de vida de reservas, detección y notificación de disrupciones, y facturación con Stripe test mode. CU-O48 es una vía excepcional de backoffice (Administrador) para forzar puntualmente el estado de un vuelo con fines exclusivos de demo/sustentación — el catálogo sigue siendo 100% automático en producción (ver `vuelos-spec.md` y la nota en `analisis-cus-completo.md`).

## Alcance de esta entrega

**En alcance:** las 6 specs de módulo bajo `specs/operativo/`, más este directorio `000-sistema-general/` como base transversal. Solo especificación (nivel `spec.md`) — no incluye `plan.md` ni `tasks.md` de Spec Kit en esta ronda.

**Fuera de alcance (documentado, no especificado):**
- Nivel Táctico (18 CU-T previstos: permisos por tabla, panel de configuración, tendencia histórica de precio/puntualidad).
- Nivel Estratégico (2 CU-E previstos: simulador de riesgo — ya implementado como DAG, y medición de efectividad de notificación).
- Departamentos reservados sin CU redactados: Comercial y Marketing (fidelización, socios API), Ingeniería y Analítica de Datos (pipeline ELT, predictivo, asistente IA "SOFIA").
- Cualquier certificación formal de la industria aérea (IATA/IATAN, BSP/ARC, GDS, NDC completo) — ver `consideraciones.md` sección 7.

Ver el detalle completo de niveles y departamentos previstos en `docs/aerotrack-travel-casos-de-uso-operativos.md`, secciones 1, 3 y 4.

## Actores del sistema

| Actor | Naturaleza | Módulos donde actúa principalmente |
|---|---|---|
| **Pasajero** | Humano, cliente final | Pasajeros, Vuelos, Reservas, Disrupciones (consulta), Facturación |
| **Agente** | Humano, interno | Pasajeros (backoffice), Reservas (asistida), Disrupciones (consulta), Facturación (reembolsos) |
| **Administrador** | Humano, interno | Seguridad (dueño), Facturación (conciliación/remesas), backoffice en general |
| **Sistema** | Automático (Airflow, temporizadores, listeners) | Vuelos (generación/estado), Disrupciones (detección/notificación), Facturación (factura/comisión), Transversal (auditoría, sesión, RBAC, expiración) |

## Estructura organizacional (departamentos → módulos → nivel)

| Departamento | Módulo | Nivel | Estado |
|---|---|---|---|
| Tecnología y Sistemas (TI) | Seguridad (Usuarios · Roles · Auditoría) | Operativo | ✅ Esta entrega |
| *(Toda cuenta autenticada)* | Mi cuenta / Mi perfil | Operativo | ✅ Esta entrega (vive en Seguridad) |
| Ventas y Reservas | Pasajeros | Operativo | ✅ Esta entrega |
| Ventas y Reservas | Vuelos (catálogo) | Operativo | ✅ Esta entrega |
| Ventas y Reservas | Reservas | Operativo | ✅ Esta entrega |
| Operaciones | Disrupciones y Notificaciones | Operativo | ✅ Esta entrega |
| Finanzas | Facturación | Operativo | ✅ Esta entrega |
| Tecnología y Sistemas (TI) | Configuración | Táctico | 📋 Previsto |
| Tecnología y Sistemas (TI) | Seguridad → Permisos | Táctico | 📋 Previsto |
| Finanzas | Configuración de aerolíneas/comisiones, Dashboard Financiero | Táctico / Estratégico | 📋 Previsto / futuro |
| Operaciones | Simulador de riesgo, medición de efectividad | Estratégico | 📋 Previsto (simulador ya implementado como DAG) |
| Comercial y Marketing, Ingeniería y Analítica de Datos | *(reservados)* | — | 📋 Alcance futuro |

## Los 6 módulos-spec operativos

| Módulo | Prefijo | Código fuente | CU cubiertos | Depende de |
|---|---|---|---|---|
| Seguridad | SEG | `app/seguridad/` | CU-O01–O13, O41, O42, O43 | (ninguno — base del sistema) |
| Pasajeros | PAS | `app/pasajeros/` | CU-O14–O16 | Seguridad |
| Vuelos (catálogo) | VUE | `app/vuelos/` | CU-O17–O20, O45 (RF), O48 (excepcional, añadido) | Seguridad |
| Reservas | RES | `app/reservas/` | CU-O21–O26, O44, O45 (RN), O47 (RN) | Seguridad, Pasajeros, Vuelos |
| Disrupciones y Notificaciones | DIS | `app/disrupciones/` | CU-O27–O31, O46 | Vuelos, Reservas |
| Facturación | FAC | `app/facturacion/` | CU-O32–O40, O47 (RF) | Reservas, Seguridad |

Detalle completo de asignación, relaciones `<<include>>`/`<<extend>>` y justificación de los CU transversales (O41–O47): ver `analisis-cus-completo.md`, secciones 3 y 4.

## Mecanismos transversales

Tres CU se invocan desde prácticamente todos los demás y se documentan una única vez en `seguridad-spec.md`, no se repiten módulo por módulo:

- **CU-O41 — Registrar evento en auditoría**: toda mutación, en cualquier módulo, dispara este CU (constitución B4 / `reglas.md` REG-B4).
- **CU-O42 — Verificar sesión activa**: toda acción autenticada, excepto login/recuperación de contraseña/registro, requiere un token válido.
- **CU-O43 — Verificar permisos de acceso (RBAC)**: toda acción de Agente/Administrador pasa por la matriz de permisos de dos niveles (constitución B1 / REG-B1).

Dos CU transversales adicionales se documentan en dos módulos cada uno, con enfoque distinto (ver `analisis-cus-completo.md` sección 4 para el detalle completo):

- **CU-O45 — Verificar disponibilidad de vuelo/cupo**: mecanismo/dato en Vuelos, orquestación/negocio en Reservas.
- **CU-O47 — Cobrar/reembolsar diferencia de tarifa**: disparador/negocio en Reservas, mecanismo de cobro en Facturación.

## Relación con los demás documentos de esta carpeta

| Archivo | Contenido |
|---|---|
| `analisis-cus-completo.md` | Catálogo de los 47 CU-O, mapa de relaciones/dependencias, escenarios "qué pasa si", matriz técnica |
| `glosario.md` | Términos de dominio y técnicos usados en todas las specs de módulo |
| `reglas.md` | Los 21 principios constitucionales (A1–H1) + Stack (I) + Diseño de Interfaz (J1–J11), transformados a reglas consultables con código `REG-XX` |
| `consideraciones.md` | Contexto de negocio, alcance de producto, modelo de ingresos, fuentes de datos reales, y decisiones que condicionan la interpretación de cada spec de módulo |
| `errores-conocidos.md` | Vacío — se completa durante la implementación |

## Criterios de éxito a nivel de sistema

- **CE-01:** Un pasajero puede completar el flujo completo de autoservicio (buscar → reservar → pagar → recibir confirmación) sin intervención de un agente humano en ningún paso obligatorio.
- **CE-02:** Ninguna disrupción detectada por cualquiera de las fuentes operativas (API real, monitor de correo) queda sin generar una notificación verificable al pasajero afectado.
- **CE-03:** Todo movimiento de dinero (cobro, comisión, remesa, reembolso) es trazable de origen a destino y no puede duplicarse por reintento del mismo evento.
- **CE-04:** Ninguna acción de creación, modificación o eliminación, en ningún módulo, queda sin su registro correspondiente en el log de auditoría.
- **CE-05:** Ninguna funcionalidad de Agente/Administrador es accesible fuera de la matriz de permisos de dos niveles.
- **CE-06:** El sistema continúa notificando disrupciones (vía fuente estadística) aun cuando la API de estado de vuelo en tiempo real no esté disponible.

## Dependencias externas al nivel Operativo

- El nivel Táctico previsto es quien eventualmente proveerá configuración editable (tiempos de expiración, umbrales, credenciales, plantillas) — mientras no exista, cada módulo Operativo lee esos valores desde `configuracion_sistema` con un default documentado en su propia spec.
- El nivel Estratégico previsto (simulador de riesgo) ya existe técnicamente como DAG de Airflow; el módulo Disrupciones (Operativo) solo consume sus resultados cuando corresponda documentarlo, no lo reimplementa.
