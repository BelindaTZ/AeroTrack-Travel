<!--
Sync Impact Report
Version change: 1.1.0 → 1.2.0
Modified principles:
  - J. Diseño de Interfaz: expandida con J9–J11 (comboboxes con búsqueda /
    filtros instantáneos sin botón, navegación de regreso predecible con
    preservación de estado, feedback inmediato y reversible), a pedido
    explícito de detalle de usabilidad adicional sobre la base J1–J8 de
    la versión 1.1.0
Added sections: none (expansión dentro de J, ya existente)
Removed sections: none
Templates requiring updates:
  - .specify/templates/plan-template.md ✅ no change needed
  - .specify/templates/spec-template.md ✅ sin referencias a la
    constitución, no requiere cambio
  - .specify/templates/tasks-template.md ✅ sin referencias a la
    constitución, no requiere cambio
Follow-up TODOs:
  - Los valores de color/tipografía en J3/J4 son direccionales (principio
    de sistema de tokens), no un theme.css cerrado — la implementación
    final de tokens vive en el repositorio de diseño/código, no aquí.
  - H. Inteligencia Artificial Responsable sigue aplicando solo cuando se
    implementen los módulos Predictivo y Asistente IA.
-->

# AeroTrack Travel Constitution

**Versión**: 1.2.0
**Aplica a**: todos los módulos y niveles (operativo, táctico, estratégico) del sistema AeroTrack Travel.

Esta constitución enuncia principios generales de arquitectura, calidad y gobernanza que toda
especificación de módulo (spec.md) debe respetar. No contiene requisitos funcionales (RF) ni
reglas de negocio (RN) específicas de una funcionalidad — esas viven exclusivamente en el
spec.md de cada módulo. Ningún principio aquí descrito está atado a una pantalla, entidad o
caso de uso puntual: son reglas transversales que cualquier funcionalidad, presente o futura,
debe cumplir.

## Core Principles

### A. Arquitectura de Datos

**A1. Separación transaccional/analítica.**
La capa operativa (reservas, pasajeros, pagos, notificaciones) y la capa analítica heredada
(modelo dimensional Kimball) son dominios separados. Ninguna funcionalidad operativa escribe
directamente sobre la capa analítica.

**A2. Modelo dimensional heredado, siempre de solo lectura.**
Cualquier módulo que consulte el modelo dimensional heredado del proyecto anterior lo hace
exclusivamente en modo lectura. Ninguna funcionalidad puede crear, modificar o eliminar
registros de esa capa, sin importar el propósito invocado.

### B. Seguridad y Privacidad

**B1. RBAC de dos niveles obligatorio.**
Toda funcionalidad nueva se registra en el catálogo de permisos por módulo y, cuando aplique,
por tabla. No puede existir una funcionalidad accesible al margen de esa matriz de permisos.

**B2. Minimización de datos personales.**
Ninguna funcionalidad solicita, almacena o expone un dato personal del pasajero que no sea
estrictamente necesario para completar una reserva, un pago o una notificación.

**B3. Cero secretos hardcodeados.**
Toda credencial de cualquier integración (correo, pagos, APIs externas) vive únicamente en
configuración persistida o variables de entorno. Nunca en código fuente ni en control de
versiones.

**B4. Auditoría inmutable y universal.**
Toda acción que cree, modifique o elimine un registro, en cualquier módulo, queda registrada
en el log de auditoría. El registro de auditoría es de solo inserción: nunca se edita ni se
elimina.

### C. Cumplimiento Normativo

**C1. Nunca se almacenan datos de tarjeta crudos.**
Toda operación de pago se delega a un proveedor tokenizado. Ninguna funcionalidad, presente o
futura, puede capturar, transmitir o persistir el número completo de una tarjeta de pago
(principio inspirado en PCI-DSS).

**C2. Propósito declarado y derecho de eliminación sobre datos personales.**
Todo dato personal recolectado debe tener un propósito identificable dentro del sistema, y el
titular debe contar con una vía para solicitar su eliminación (principio inspirado en marcos
de privacidad como CCPA/GDPR, adoptado como buena práctica).

**C3. Transparencia en cancelaciones y reembolsos.**
Toda cancelación o reembolso se resuelve mediante reglas consultables por el pasajero. Ninguna
funcionalidad puede resolver estos casos de forma discrecional u oculta al usuario afectado.

### D. Integridad Financiera y Transaccional

**D1. Idempotencia obligatoria en operaciones de dinero.**
Ninguna operación que mueva dinero (cobro, reembolso, registro de comisión) puede ejecutarse
dos veces por el mismo evento. Todo flujo de pago debe ser verificable e idempotente,
independientemente del proveedor de pago.

**D2. Trazabilidad completa de todo movimiento monetario.**
Todo ingreso o egreso, real o simulado, queda registrado con origen, destino y estado,
permitiendo reconstruir el estado financiero de cualquier reserva en cualquier momento.

**D3. Las políticas de reembolso se resuelven por reglas, no por excepción manual.**
Cualquier reembolso disparado por el sistema se evalúa automáticamente contra la política de
la tarifa comprada, sin importar qué módulo lo originó.

### E. Confiabilidad de Notificación y Disrupciones

**E1. Ninguna disrupción detectada queda sin notificar.**
Sin importar cuál fuente de datos detectó el evento, toda disrupción relevante genera una
notificación verificable al pasajero afectado.

**E2. Precedencia y deduplicación entre fuentes.**
Cuando más de una fuente de datos detecta el mismo evento, el sistema aplica una regla de
precedencia y evita notificar el mismo cambio más de una vez al mismo pasajero.

**E3. Degradación ordenada ante ausencia de datos en tiempo real.**
Si una fuente de datos en tiempo real no está disponible, el sistema continúa operando con la
fuente estadística como respaldo. Nunca falla silenciosamente.

### F. Resiliencia e Integraciones Externas

**F1. Toda integración externa es reemplazable.**
Ninguna funcionalidad se acopla directamente a un proveedor específico sin una capa de
abstracción que permita sustituirlo — aplica a pagos, correo, estado de vuelo o cualquier
servicio de terceros futuro.

**F2. Timeouts y reintentos configurables por integración.**
Toda llamada a un servicio externo define un límite de tiempo y una política de reintento en
configuración. Nunca existen esperas indefinidas.

**F3. Aislamiento de fallos de terceros.**
La caída de un servicio externo no impide el uso del resto del sistema. Cada integración se
degrada de forma independiente.

### G. Experiencia de Usuario

**G1. Autoservicio como camino por defecto.**
Toda funcionalidad orientada al pasajero se diseña primero para autogestión sin intervención
humana. La asistencia de un agente es siempre un canal adicional, nunca un paso obligatorio.

**G2. Transparencia de precio y consentimiento explícito.**
Cualquier pantalla que involucre un cargo al pasajero muestra el desglose completo antes de
confirmar. Ninguna acción que comprometa dinero se ejecuta sin confirmación explícita del
usuario.

### H. Inteligencia Artificial Responsable

*(Principios previstos para cuando se implementen los módulos Predictivo y Asistente IA —
actualmente fuera de alcance operativo.)*

**H1. Contexto de IA acotado y verificable.**
Cualquier funcionalidad basada en IA opera exclusivamente sobre datos que el sistema puede
verificar. No inventa información de vuelos, tarifas o políticas, y respeta los permisos del
usuario que la invoca.

## I. Stack Tecnológico

*(Cumplimiento obligatorio — toda funcionalidad nueva se construye sobre este stack, sin
introducir alternativas no listadas aquí sin actualizar esta constitución primero.)*

- Python 3.12 unificado en todo el sistema.
- FastAPI + Jinja2 + Bootstrap 5 para el backend y frontend operativo.
- PocketBase como capa operacional transaccional (reservas, pasajeros, pagos, notificaciones,
  configuración, auditoría).
- Docker + docker-compose para entorno de desarrollo y despliegue.
- Stripe (modo de prueba / test mode) para todo el flujo de pagos, reembolsos y facturación.
- Gmail API (OAuth) para el monitor de bandeja de correo de disrupciones.
- Una API de estado de vuelo real (AviationStack o AeroDataBox) como fuente externa de
  disrupciones.
- Apache Airflow, heredado del proyecto anterior, reservado para cuando se retome el
  departamento de Ingeniería y Analítica de Datos.
- Conformidad con ISO/IEC 25010:2023 como estándar de calidad de referencia para toda
  funcionalidad.

## J. Diseño de Interfaz

*(Principios generados con la skill `ui-ux-pro-max`, a partir del documento empresarial y el
catálogo de casos de uso operativos. Son dirección de diseño transversal — ningún valor aquí
está atado a una pantalla puntual; la implementación final de tokens, componentes y layouts de
cada módulo se resuelve en su propio `plan.md`.)*

**J1. Personalidad visual: confianza operativa, no vitrina ni panel académico.**
El producto no se diseña ni como una landing de marketing (vitrina genérica) ni como un panel
de administración por defecto (tipo scaffold sin dirección). Su personalidad es la de una
herramienta de aerolínea/OTA seria en la que se confía dinero y tiempo de viaje: sobria,
profesional, con la fricción mínima posible en el camino de autoservicio (principio G1), y
honesta en la forma en que comunica precio, estado y cambios — nunca decorativa a costa de la
claridad.

**J2. Un único sistema de tokens, dos densidades.**
El portal de pasajero y el backoffice interno comparten la misma capa primitiva de tokens
(color, tipografía, radios, elevación): no son dos productos con identidades separadas. Lo que
cambia entre ambos es la capa semántica de densidad y composición — el portal prioriza espacio
y ritmo de conversión; el backoffice prioriza compacidad y velocidad de lectura — nunca la
paleta ni la tipografía base.

**J3. Paleta como sistema semántico primitivo → semántico, no valores cerrados.**
Todo color se define como rol semántico (`primary`/confianza, `accent`/acción que compromete
dinero, `surface`, `border`, `muted`, `destructive`, y sus pares `on-*`), nunca como hex
directo en un componente (refuerza B3 y evita deuda de theming). Dirección tonal: una familia
fría de confianza (azul/marino, asociada a aviación y a las OTAs de referencia del sector) para
`primary`, reservando un tono cálido (ámbar/naranja) exclusivamente para `accent` en momentos de
conversión o de acción sobre dinero (buscar, pagar, confirmar) — nunca para navegación o estado
neutro. El backoffice reutiliza los mismos roles sobre una escala neutra (slate) de mayor
contraste tonal, para sostener tablas densas sin fatiga visual. Los pares de contraste texto/fondo
deben cumplir WCAG AA (4.5:1) en ambas superficies, en claro y oscuro.

**J4. Tipografía por rol funcional, no por preferencia estética.**
Se definen tres roles tipográficos, no una fuente final cerrada: una familia de **display/UI**
para encabezados y controles (con carácter serio y legible, no editorial ni juguetona), una
familia de **texto** optimizada para lectura prolongada de formularios y contenido de reserva, y
una familia **tabular/monoespaciada** obligatoria para toda cifra en columnas — precios,
comisiones, montos de auditoría, IDs de transacción — de forma que las cifras alineen
verticalmente y no exista layout shift al cargar datos (refuerza D2, trazabilidad financiera
legible).

**J5. Layout de conversión vs. layout de densidad de datos, mismo lenguaje visual.**
Las pantallas de conversión (buscador, resultados, checkout, "mi reserva") siguen un principio
de una sola acción primaria por pantalla, desglose de precio siempre visible antes de confirmar
(refuerza G2), y revelado progresivo de opciones (extras, asientos) para no abrumar antes de la
decisión de compra. Las pantallas de alta densidad (tablas de auditoría, matriz de permisos,
conciliación de comisiones) siguen un principio de compacidad: escala de espaciado reducida,
cabeceras de tabla fijas, ordenamiento y filtrado como funciones de primera clase, y acciones
en bloque donde el caso de uso lo permita. Ninguna tabla de datos crudos se le presenta al
pasajero; ninguna pantalla de conversión se le presenta al agente/administrador como vista
primaria de trabajo.

**J6. El RBAC de dos niveles y la auditoría inmutable se comunican visualmente, no solo se
aplican en backend.**
Toda pantalla del backoffice donde el permiso de un rol dependa de la restricción por tabla
(nivel 2, ver B1) debe mostrar de forma persistente el alcance vigente (qué tablas del módulo
son visibles/editables), nunca ocultar la restricción como si fuera ausencia de datos. Toda
vista de auditoría se renderiza sin ningún control de edición o eliminación en su interfaz —
la ausencia de esos controles es en sí misma la señal de que el registro es de solo inserción
(refuerza B4).

**J7. El estado y las alertas nunca dependen solo del color.**
Toda comunicación de estado de vuelo, disrupción, resultado de pago o resultado de una acción
de auditoría combina color con ícono y texto explícito — nunca color aislado. Esto aplica igual
al banner de disrupción que ve el pasajero y al indicador de estado que ve el agente en
backoffice: ambos usan el mismo lenguaje visual de alerta, reforzando que la fiabilidad de
notificación (principio E1) es perceptible como parte de la identidad del producto, no solo
como un requisito funcional oculto.

**J8. Accesibilidad y responsive son un principio transversal, no una fase final de QA.**
Todo componente, en cualquiera de los dos contextos, cumple como mínimo: contraste de texto
4.5:1 (WCAG AA), objetivos táctiles de al menos 44×44px, navegación completa por teclado con
foco visible, y respeto a `prefers-reduced-motion`. El portal de pasajero se diseña mobile-first
(el buscador y el checkout deben completarse sin fricción en una pantalla de 375px); el
backoffice se diseña desktop-first pero sin romper en tablet, degradando tablas densas a un
layout de tarjetas antes que forzar scroll horizontal roto. Ninguna funcionalidad se considera
completa si solo fue validada en un tamaño de pantalla o en un solo modo de color.

**J9. Filtros instantáneos; comboboxes con búsqueda para listas largas.**
Todo filtro secundario — resultados de vuelos (aerolínea, horario, escalas), tablas del
backoffice, log de auditoría — se aplica automáticamente al cambiar su valor. Ningún filtro
lleva botón de "Aplicar" o "Buscar": el resultado se actualiza solo, con un estado de carga
breve si la consulta lo requiere. Esto no aplica a la búsqueda principal del buscador de vuelos
(origen/destino/fecha/pasajeros), que sigue siendo una acción explícita de conversión con su
propio botón, no un filtro. Todo campo de selección con más de ~8 opciones (aeropuerto,
aerolínea, rol, moneda) se implementa como combobox con búsqueda por texto (type-ahead) en vez
de un `<select>` nativo de desplazamiento largo; campos con pocas opciones fijas (nivel de
tarifa, género, sí/no) usan controles simples sin buscador, para no añadir fricción donde no
hace falta.

**J10. Navegación de regreso predecible y sin pérdida de estado.**
Toda pantalla alcanzada por navegación normal (no un modal) ofrece un control de "regresar"
explícito y en la misma posición en todo el sistema. Regresar conserva el estado previo —
filtros aplicados, posición de scroll, paso alcanzado en un flujo — en vez de reiniciar la
vista. Los modales y hojas (sheets) se cierran con una acción de cierre visible además de
cualquier gesto; en flujos de varios pasos (checkout de reserva, alta de rol con permisos) el
botón de regresar retrocede un paso sin descartar los datos ya ingresados en pasos siguientes.

**J11. Feedback inmediato, no bloqueante, y reversible.**
Toda acción asíncrona (guardar, pagar, filtrar, exportar) dispara retroalimentación visual en
menos de 300ms; para esperas cortas se usa un estado de carga tipo skeleton, nunca un spinner
que bloquee el resto de la pantalla. Las confirmaciones de éxito se muestran como un mensaje
breve que se autodescarta (3–5s) sin interrumpir la siguiente interacción del usuario. Toda
acción destructiva o irreversible (cancelar reserva, eliminar rol, revocar un permiso) exige un
paso de confirmación explícito y separado visualmente de las acciones primarias — nunca se
ejecuta al primer clic (refuerza G2 y C3).

## Governance

Esta constitución prevalece sobre cualquier otra práctica de desarrollo del proyecto. Toda
especificación (`spec.md`), plan (`plan.md`) y tareas (`tasks.md`) de cada módulo debe
verificar cumplimiento contra los principios A–J antes de avanzar de fase. Cualquier
desviación debe quedar explícitamente justificada en la sección de Complexity Tracking del
plan correspondiente, indicando por qué una alternativa más simple o más alineada con estos
principios fue descartada.

**Enmiendas**: toda modificación a esta constitución debe (1) documentar el motivo del cambio,
(2) actualizar la tabla de control de versiones al final de este documento, y (3) revisar los
templates dependientes (`plan-template.md`, `spec-template.md`, `tasks-template.md`) para
confirmar que siguen siendo consistentes con los principios vigentes.

**Versionado semántico**: MAJOR para eliminaciones o redefiniciones incompatibles de
principios o secciones de gobernanza; MINOR para la adición de un principio nuevo o una
expansión material de una guía existente; PATCH para aclaraciones, correcciones de redacción o
refinamientos no semánticos.

**Revisión de cumplimiento**: toda funcionalidad nueva, antes de pasar a implementación, debe
poder trazarse contra al menos un principio de esta constitución en su `spec.md` o `plan.md`.

### Control de versiones de esta constitución

| Versión | Fecha | Cambios |
|---------|------------|---------|
| 1.0.0 | 2026-07-08 | Versión inicial de AeroTrack Travel, redactada desde cero — no hereda del proyecto AeroTrack Analytics. |
| 1.1.0 | 2026-07-08 | Se completa la Sección J (Diseño de Interfaz), antes vacía, con principios de personalidad visual, sistema de tokens de color/tipografía, diferenciación portal/backoffice, layout por densidad, RBAC/auditoría visibles, y accesibilidad transversal — generados con la skill `ui-ux-pro-max` a partir del documento empresarial y el catálogo de casos de uso. |
| 1.2.0 | 2026-07-08 | Se agregan a la Sección J los principios J9–J11: formato de combobox con búsqueda para listas largas, filtros instantáneos sin botón de aplicar, navegación de regreso predecible con preservación de estado, y feedback inmediato/reversible en acciones destructivas. |

**Version**: 1.2.0 | **Ratified**: 2026-07-08 | **Last Amended**: 2026-07-08
