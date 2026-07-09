# Reglas del Sistema — Transformación de la Constitución

**Fuente:** `.specify/memory/constitution.md` v1.2.0 (no se reescribe la constitución; este documento la transforma a formato de reglas transversales consultables desde cada spec de módulo).

Esta constitución no contiene 19 principios como un conteo simple de secciones con letra — contiene **21 principios nucleares numerados** (A1–H1, secciones A a H), más el **Stack Tecnológico** (Sección I, mandato transversal sin numeración de "principio") y **11 principios de Diseño de Interfaz** (J1–J11, Sección J). Se transforman aquí **todos**, sin excluir ninguno, para no perder cobertura de gobernanza.

Cada regla mantiene su código original de la constitución (p. ej. `A1`, `B4`, `J9`) para trazabilidad, y se le añade un código de regla del sistema (`REG-A1`) y una columna "Aplica a" que indica qué módulo(s) operativo(s) la implementan de forma más directa. **"Aplica a" no es exhaustivo ni excluyente**: toda regla marcada como transversal aplica a los 6 módulos por igual, y cualquier módulo puede invocar cualquier regla en su propio `RN-{PREF}-NNN` citando el código de esta tabla.

---

## A. Arquitectura de Datos

| Código | Regla | Aplica a |
|---|---|---|
| **REG-A1** | Separación transaccional/analítica: la capa operativa (reservas, pasajeros, pagos, notificaciones) y la capa analítica heredada (modelo dimensional Kimball) son dominios separados. Ninguna funcionalidad operativa escribe directamente sobre la capa analítica. | Transversal — los 6 módulos |
| **REG-A2** | Modelo dimensional heredado, siempre de solo lectura: cualquier consulta al modelo dimensional heredado (`dim_*`, `agg_*`, `fact_vuelo`) es exclusivamente de lectura. Ninguna funcionalidad puede crear, modificar o eliminar registros de esa capa. | Vuelos (VUE), Reservas (RES — `alertas_precio` SOFT-REF) |

## B. Seguridad y Privacidad

| Código | Regla | Aplica a |
|---|---|---|
| **REG-B1** | RBAC de dos niveles obligatorio: toda funcionalidad nueva se registra en el catálogo de permisos por módulo y, cuando aplique, por tabla. No puede existir una funcionalidad accesible al margen de esa matriz. | Seguridad (dueño), transversal en consumo |
| **REG-B2** | Minimización de datos personales: ninguna funcionalidad solicita, almacena o expone un dato personal del pasajero que no sea estrictamente necesario para completar una reserva, un pago o una notificación. | Seguridad, Pasajeros, Reservas |
| **REG-B3** | Cero secretos hardcodeados: toda credencial de cualquier integración (correo, pagos, APIs externas) vive únicamente en configuración persistida o variables de entorno. Nunca en código fuente ni en control de versiones. | Seguridad (dueño de `configuracion_sistema`), Facturación (Stripe), Disrupciones (Gmail API, API de estado de vuelo) |
| **REG-B4** | Auditoría inmutable y universal: toda acción que cree, modifique o elimine un registro, en cualquier módulo, queda registrada en el log de auditoría. El registro es de solo inserción: nunca se edita ni se elimina. | Transversal — los 6 módulos (vía CU-O41) |

## C. Cumplimiento Normativo

| Código | Regla | Aplica a |
|---|---|---|
| **REG-C1** | Nunca se almacenan datos de tarjeta crudos: toda operación de pago se delega a un proveedor tokenizado (Stripe). Ninguna funcionalidad puede capturar, transmitir o persistir el número completo de una tarjeta (inspirado en PCI-DSS). | Facturación |
| **REG-C2** | Propósito declarado y derecho de eliminación sobre datos personales: todo dato personal recolectado debe tener un propósito identificable dentro del sistema, y el titular debe contar con una vía para solicitar su eliminación (inspirado en CCPA/GDPR). | Seguridad, Pasajeros |
| **REG-C3** | Transparencia en cancelaciones y reembolsos: toda cancelación o reembolso se resuelve mediante reglas consultables por el pasajero. Ninguna funcionalidad puede resolver estos casos de forma discrecional u oculta al usuario afectado. | Reservas, Facturación |

## D. Integridad Financiera y Transaccional

| Código | Regla | Aplica a |
|---|---|---|
| **REG-D1** | Idempotencia obligatoria en operaciones de dinero: ninguna operación que mueva dinero (cobro, reembolso, registro de comisión) puede ejecutarse dos veces por el mismo evento. Todo flujo de pago debe ser verificable e idempotente, sin importar el proveedor. | Facturación, Reservas (CU-O47) |
| **REG-D2** | Trazabilidad completa de todo movimiento monetario: todo ingreso o egreso, real o simulado, queda registrado con origen, destino y estado, permitiendo reconstruir el estado financiero de cualquier reserva en cualquier momento. | Facturación |
| **REG-D3** | Las políticas de reembolso se resuelven por reglas, no por excepción manual: cualquier reembolso disparado por el sistema se evalúa automáticamente contra la política de la tarifa comprada, sin importar qué módulo lo originó. | Facturación, Reservas (extend CU-O24/O30 → CU-O37) |

## E. Confiabilidad de Notificación y Disrupciones

| Código | Regla | Aplica a |
|---|---|---|
| **REG-E1** | Ninguna disrupción detectada queda sin notificar: sin importar cuál fuente de datos detectó el evento, toda disrupción relevante genera una notificación verificable al pasajero afectado. | Disrupciones |
| **REG-E2** | Precedencia y deduplicación entre fuentes: cuando más de una fuente detecta el mismo evento, el sistema aplica una regla de precedencia y evita notificar el mismo cambio más de una vez al mismo pasajero. | Disrupciones |
| **REG-E3** | Degradación ordenada ante ausencia de datos en tiempo real: si una fuente de datos en tiempo real no está disponible, el sistema continúa operando con la fuente estadística como respaldo. Nunca falla silenciosamente. El peor caso normal (fuente en tiempo real disponible) nunca debe depender de que esta degradación se dispare. | Disrupciones |
| **REG-F1** | Toda integración externa es reemplazable: ninguna funcionalidad se acopla directamente a un proveedor específico sin una capa de abstracción que permita sustituirlo. Aplica a pagos, correo, estado de vuelo o cualquier servicio de terceros futuro. | Facturación (Stripe), Disrupciones (Gmail API, API de estado de vuelo), Seguridad (SMTP) |

## F. Resiliencia e Integraciones Externas

| Código | Regla | Aplica a |
|---|---|---|
| **REG-F2** | Timeouts y reintentos configurables por integración: toda llamada a un servicio externo define un límite de tiempo y una política de reintento en configuración. Nunca existen esperas indefinidas. | Facturación, Disrupciones, Seguridad (correo) |
| **REG-F3** | Aislamiento de fallos de terceros: la caída de un servicio externo no impide el uso del resto del sistema. Cada integración se degrada de forma independiente. | Facturación, Disrupciones, Seguridad |

## G. Experiencia de Usuario

| Código | Regla | Aplica a |
|---|---|---|
| **REG-G1** | Autoservicio como camino por defecto: toda funcionalidad orientada al pasajero se diseña primero para autogestión sin intervención humana. La asistencia de un agente es siempre un canal adicional, nunca un paso obligatorio. | Pasajeros, Vuelos, Reservas |
| **REG-G2** | Transparencia de precio y consentimiento explícito: cualquier pantalla que involucre un cargo al pasajero muestra el desglose completo antes de confirmar. Ninguna acción que comprometa dinero se ejecuta sin confirmación explícita del usuario. | Reservas, Facturación |

## H. Inteligencia Artificial Responsable

| Código | Regla | Aplica a |
|---|---|---|
| **REG-H1** | Contexto de IA acotado y verificable: cualquier funcionalidad basada en IA opera exclusivamente sobre datos que el sistema puede verificar. No inventa información de vuelos, tarifas o políticas, y respeta los permisos del usuario que la invoca. | *(Ninguno de los 6 módulos operativos actuales — previsto para Predictivo/Asistente IA, fuera de alcance de esta entrega. Se transforma igual para trazabilidad futura.)* |

## I. Stack Tecnológico

*(Mandato transversal de cumplimiento obligatorio, no un principio de diseño — se incluye aquí porque ninguna spec de módulo puede introducir una alternativa no listada aquí sin actualizar primero la constitución.)*

| Código | Regla | Aplica a |
|---|---|---|
| **REG-I1** | Python 3.12 unificado en todo el sistema. | Transversal |
| **REG-I2** | FastAPI + Jinja2 + Bootstrap 5 para backend y frontend operativo. | Transversal |
| **REG-I3** | PocketBase como capa operacional transaccional (reservas, pasajeros, pagos, notificaciones, configuración, auditoría). | Transversal |
| **REG-I4** | Docker + docker-compose para entorno de desarrollo y despliegue. | Transversal |
| **REG-I5** | Stripe (test mode) para todo el flujo de pagos, reembolsos y facturación. | Facturación |
| **REG-I6** | Gmail API (OAuth) para el monitor de bandeja de correo de disrupciones. | Disrupciones |
| **REG-I7** | Una API de estado de vuelo real (AviationStack o AeroDataBox) como fuente externa de disrupciones. | Disrupciones |
| **REG-I8** | Apache Airflow, heredado, reservado para cuando se retome Ingeniería y Analítica de Datos. | Vuelos (CU-O19, generación de catálogo) |
| **REG-I9** | Conformidad con ISO/IEC 25010:2023 como estándar de calidad de referencia para toda funcionalidad. | Transversal |

## J. Diseño de Interfaz

*(Dirección de diseño transversal generada con la skill `ui-ux-pro-max`; ningún valor está atado a una pantalla puntual — la implementación final de tokens/componentes se resuelve en el `plan.md` de cada módulo, fuera de alcance de esta ronda de specs.)*

| Código | Regla (resumen) | Aplica a |
|---|---|---|
| **REG-J1** | Personalidad visual de confianza operativa: ni vitrina de marketing ni panel académico genérico; sobria, profesional, fricción mínima en autoservicio (refuerza G1), honesta al comunicar precio/estado/cambios. | Transversal |
| **REG-J2** | Un único sistema de tokens (color, tipografía, radios, elevación) compartido entre portal de pasajero y backoffice; solo cambia la densidad/composición semántica, nunca la paleta ni la tipografía base. | Transversal |
| **REG-J3** | Paleta como roles semánticos (`primary`, `accent`, `surface`, `border`, `muted`, `destructive` y sus pares `on-*`), nunca hex directo en componente (refuerza B3). Frío/confianza para `primary`, cálido/acción-con-dinero para `accent`. Contraste WCAG AA 4.5:1 en claro y oscuro. | Transversal |
| **REG-J4** | Tres roles tipográficos (display/UI, texto, tabular/monoespaciada obligatoria para cifras en columnas — precios, comisiones, montos de auditoría, IDs). Refuerza D2. | Transversal, especialmente Facturación y Seguridad (auditoría) |
| **REG-J5** | Layout de conversión (una acción primaria, desglose de precio siempre visible, revelado progresivo) vs. layout de densidad de datos (compacidad, cabeceras fijas, orden/filtro de primera clase). Ninguna tabla cruda al pasajero; ninguna pantalla de conversión al agente/admin como vista primaria. | Reservas, Vuelos (conversión); Seguridad, Facturación (densidad) |
| **REG-J6** | El RBAC de dos niveles y la auditoría inmutable se comunican visualmente: toda pantalla con restricción de tabla (Nivel 2) muestra el alcance vigente de forma persistente; toda vista de auditoría se renderiza sin controles de edición/eliminación (refuerza B4). | Seguridad |
| **REG-J7** | El estado y las alertas nunca dependen solo del color: color + ícono + texto explícito, tanto en el banner de disrupción del pasajero como en el indicador de estado del agente. | Disrupciones, Vuelos (estado de vuelo) |
| **REG-J8** | Accesibilidad y responsive transversales: contraste 4.5:1, objetivos táctiles ≥44×44px, navegación por teclado con foco visible, `prefers-reduced-motion`. Portal mobile-first (checkout usable en 375px); backoffice desktop-first sin romper en tablet (tarjetas antes que scroll horizontal roto). | Transversal |
| **REG-J9** | Filtros instantáneos sin botón "Aplicar" (resultados de vuelos, tablas de backoffice, log de auditoría); comboboxes con búsqueda para listas >~8 opciones (aeropuerto, aerolínea, rol, moneda). La búsqueda principal del buscador de vuelos sigue siendo una acción explícita, no un filtro. | Vuelos, Reservas, Seguridad (auditoría) |
| **REG-J10** | Navegación de regreso predecible sin pérdida de estado: control de "regresar" consistente, preserva filtros/scroll/paso alcanzado; en flujos multi-paso (checkout, alta de rol) retrocede un paso sin descartar datos ya ingresados. | Reservas (checkout), Seguridad (alta de rol) |
| **REG-J11** | Feedback inmediato (<300ms), no bloqueante (skeleton, no spinner bloqueante), reversible; confirmaciones de éxito autodescartables (3–5s); toda acción destructiva/irreversible (cancelar reserva, eliminar rol, revocar permiso) exige confirmación explícita separada (refuerza G2, C3). | Reservas, Seguridad |

---

## Cómo se usa este documento desde cada módulo-spec

Cada `RN-{PREF}-NNN` de un módulo-spec que derive directamente de un principio constitucional debe citar su código `REG-XX` correspondiente en su descripción, para mantener trazabilidad hacia la constitución (requisito de Governance en `constitution.md`: "toda funcionalidad nueva... debe poder trazarse contra al menos un principio de esta constitución en su spec.md"). Las reglas de negocio nuevas identificadas en `analisis-cus-completo.md` (QP-04, QP-08, QP-10, QP-13) deben, además de resolver su escenario, indicar contra qué `REG-XX` se verifican (p. ej. QP-04 contra REG-D1; QP-10 contra integridad referencial, sin `REG-XX` directo — se documenta como regla nueva sin antecedente constitucional explícito).
