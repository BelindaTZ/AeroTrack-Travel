# Auditoría de WorkPanels — AeroTrack Travel

Fecha: 2026-07-31. Auditoría de solo lectura sobre el estado de los 14 WorkPanels solicitados. Un WorkPanel se marca **✅ COMPLETO** solo si cumple los 5 criterios pedidos (filtros de búsqueda, lista paginada, acciones relevantes a la entidad, modal de formulario, retroalimentación visual con confirmación antes de eliminar/desactivar). Si falta alguno, es **⚠️ PARCIAL**. Si no existe ningún router/template para la entidad, es **❌ FALTANTE**.

Nota de nomenclatura: el rol **admin_general** que aparece en la tabla de requerimientos (WP-02, WP-10) no existe como tal en el sistema — fue eliminado el 27-07-2026 por duplicar a **Administrador** (mismo acceso total). Donde la tabla pide "admin_general", el rol real equivalente es **Administrador**.

---

## WP-01 — Pasajeros
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/pasajeros` (búsqueda) y GET `/backoffice/pasajeros/{id}` (detalle) — `app/pasajeros/router_backoffice.py:114,131`; PUT `/backoffice/pasajeros/{id}` (editar) — línea 153
**Departamento:** Gestión de Clientes
**Roles con acceso:** admin_clientes, agente
**Colección fuente:** MinIO — pasajeros
**Acciones implementadas:** Crear ❌ (no aplica — se auto-registran desde el portal, confirmado por ausencia total de POST en el router) · Editar ✅ · Eliminar N/A · Ver ✅ (detalle con historial de reservas embebido)
**Paginación:** ❌
**Modal de formulario:** ❌ — "Editar contacto" es un formulario que se muestra/oculta con `d-none` en la misma tarjeta, no un modal real
**Retroalimentación visual:** ⚠️ — hay error inline, pero no hay mensaje de éxito explícito ni confirmación antes de guardar
**Campos del formulario:** teléfono, dirección de facturación, contacto de emergencia
**Qué falta:** paginación en la búsqueda, modal real, mensaje de éxito explícito. "Crear" queda fuera de alcance por diseño (auto-registro), no es una carencia.

---

## WP-02 — Usuarios y Agentes del sistema
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/admin/usuarios` — `app/seguridad/router_usuarios.py:26`; POST crear — línea 33; PUT editar — línea 66
**Departamento:** TI
**Roles con acceso:** admin_ti, Administrador
**Colección fuente:** PocketBase — usuarios
**Acciones implementadas:** Crear ✅ (modal) · Editar ✅ (modal para nombre; rol/activo inline) · Desactivar ✅ (toggle inline) · Ver ❌ (no hay vista de detalle)
**Filtros de búsqueda:** ❌ — el listado trae hasta 200 registros sin filtro de nombre/email/rol/estado
**Paginación:** ❌
**Modal de formulario:** ✅ para crear y editar nombre; el cambio de rol/activo es inline
**Retroalimentación visual:** ⚠️ — hay flash de éxito/error y `confirm()` para resetear password/cerrar sesiones, pero **el toggle de activar/desactivar dispara el cambio al instante, sin confirmación**
**Campos del formulario:** nombre_completo, email, password, rol_id (crear); nombre_completo, rol_id, activo (editar)
**Qué falta:** filtros de búsqueda, paginación, confirmación antes de desactivar, vista de detalle.

---

## WP-03 — Roles del sistema
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/admin/roles` — `app/seguridad/router_roles.py:52`; editar permisos GET `/admin/roles/{id}/editar` — línea 78
**Departamento:** TI
**Roles con acceso:** admin_ti
**Colección fuente:** PocketBase — roles / permisos / roles_permisos / roles_permisos_tablas
**Acciones implementadas:** Crear ✅ (modal) · Editar/Ver permisos ✅ (página de matriz Nivel 1/Nivel 2, recién rediseñada) · Eliminar ✅ (con confirmación, bloqueado si es protegido o tiene usuarios asignados) · Ver ✅
**Filtros de búsqueda:** ❌
**Paginación:** ❌
**Modal de formulario:** ✅ para crear; editar permisos usa página aparte por diseño (matriz de permisos, no un formulario simple) — criterio aceptable dado lo que representa la pantalla
**Retroalimentación visual:** ✅ — éxito al crear, confirmación + error al eliminar, éxito/error al guardar la matriz
**Campos del formulario:** nombre, descripción, tipo_panel (crear)
**Qué falta:** solo filtros de búsqueda y paginación en el listado — es el WP más cerca de estar completo.

---

## WP-04 — Reservas (gestión interna)
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/reservas/reporte` (Ventas) y `/backoffice/reservas/mi-cartera` (Agente) — `app/reservas/router_reportes.py:30,57`; ver detalle vía `/reservas/{id}` — `app/reservas/router_reservas.py:240` (misma vista que usa el pasajero); cancelar vía POST `/reservas/{id}/cancelar` — línea 268
**Departamento:** Ventas
**Roles con acceso:** admin_ventas, agente
**Colección fuente:** MinIO — reservas
**Acciones implementadas:** Editar estado ❌ (no existe un campo "estado" editable de forma genérica — solo existe Cancelar, con sus propias reglas de negocio) · Ver detalle ✅ · Cancelar ✅ (con `confirm()` nativo)
**Filtros de búsqueda:** ✅ (estado, desde, hasta)
**Paginación:** ❌
**Modal de formulario:** ❌ — no hay formulario de edición de estado; la única confirmación es un `confirm()` nativo del navegador, no un modal propio
**Retroalimentación visual:** ⚠️ — mensajes vía query param en texto plano, sin estilo de alerta consistente
**Campos del formulario:** ninguno (cancelar no pide datos)
**Qué falta:** paginación, template de detalle propio de backoffice, y modal real en vez de `confirm()`.
**Nota:** `app/reservas/router_backoffice.py` (prefix `/backoffice/reservas`) NO es este WP — es "reserva asistida" (el agente crea una reserva a nombre de un pasajero), un flujo de venta distinto.
**Decisión de diseño (2026-07-31):** confirmado — no se construye un editor de estado genérico. El panel muestra detalle de la reserva y expone solo las acciones válidas según `estado` actual, disparando los endpoints de negocio ya existentes:
- `pendiente_pago` → Ver detalle, Cancelar
- `confirmada` → Ver detalle, Ver voucher, Iniciar reembolso
- `cancelada` → Ver detalle
- `expirada` → Ver detalle

Ya existen los servicios de negocio para las nuevas acciones, solo falta exponerlos en un router de backoffice: "Ver voucher" reutiliza `GET /reservas/{id}/voucher-pdf` (`app/facturacion/router_documentos.py:71`, ya funcional); "Iniciar reembolso" reutiliza `procesar_reembolso()` (`app/facturacion/services/reembolso_service.py:32`), pero hoy solo se dispara automáticamente (cancelación o webhook de disrupción vía `router_interno.py`) — no existe un endpoint de backoffice que lo dispare manualmente, hay que crearlo.

---

## WP-05 — Artículos de ayuda / FAQ
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/ayuda/articulos` — `app/centro_ayuda/router_backoffice.py:46`; POST crear — línea 53; POST editar — línea 62
**Departamento:** Operaciones
**Roles con acceso:** admin_operaciones
**Colección fuente:** MinIO — articulos_ayuda
**Acciones implementadas:** Crear ✅ · Editar ✅ · Archivar ⚠️ (se logra destildando el checkbox "activo" dentro del mismo formulario de edición, no es una acción independiente) · Ver ❌ (no hay vista de detalle separada)
**Filtros de búsqueda:** ❌ (el repo tiene `buscar_articulos()` con término/categoría, pero no se usa en esta pantalla)
**Paginación:** ❌
**Modal de formulario:** ❌ — usa un acordeón `<details>/<summary>`, no un modal real (otros paneles del mismo sistema sí usan modal Bootstrap, confirmando que es el patrón esperado)
**Retroalimentación visual:** ⚠️ — éxito sí, error no, ni confirmación antes de archivar
**Campos del formulario:** categoría, título, contenido, activo (checkbox, solo en edición)
**Qué falta:** filtros, paginación, vista "Ver", modal real, confirmación antes de archivar, feedback de error.

---

## WP-06 — Cupones de descuento
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET/POST `/backoffice/ofertas/cupones` — `app/ofertas/router_backoffice.py:44,51`; POST editar `/backoffice/ofertas/cupones/{id}` — línea 68
**Departamento:** Comercial
**Roles con acceso:** admin_comercial
**Colección fuente:** MinIO — cupones_descuento
**Acciones implementadas:** Crear ✅ · Editar ✅ · Desactivar ✅ (checkbox dentro del mismo formulario de editar, no acción independiente) · Ver ✅ (en el listado, sin vista de detalle separada)
**Filtros de búsqueda:** ❌
**Paginación:** ❌ (`perPage: 200` fijo)
**Modal de formulario:** ❌ — usa acordeón `<details>/<summary>` en la misma página, no modal
**Retroalimentación visual:** ⚠️ — mensaje genérico de éxito/error, pero sin confirmación antes de desactivar
**Campos del formulario:** código, tipo (porcentaje/monto fijo), valor, producto aplicable, fecha de expiración, usos máximos, acumulable con paquete
**Qué falta:** filtros, paginación real, modal verdadero, confirmación antes de desactivar.

---

## WP-07 — Suscriptores al newsletter
**Estado:** ❌ FALTANTE
**Ruta actual:** no existe — confirmado por búsqueda exhaustiva. Lo único relacionado es el POST público `/ofertas/newsletter/suscribirse` (`app/ofertas/router_ofertas.py:54`), que es la suscripción desde el portal, no gestión de backoffice
**Departamento:** Comercial
**Roles con acceso:** admin_comercial
**Colección fuente:** MinIO — newsletter_suscripciones
**Acciones implementadas:** Editar estado ❌ · Eliminar ❌ · Ver ❌
**Qué falta:** todo el panel. El repositorio (`app/ofertas/repositories/ofertas_repo.py`) ya tiene `crear_suscripcion`, `reactivar_suscripcion` y `listar_suscriptores_activos` (usado solo internamente para segmentar campañas de email), pero falta `desactivar_suscripcion`, `obtener_suscripcion` por id, un método para listar TODOS los suscriptores (activos e inactivos), el router de backoffice y el template completo.

---

## WP-08 — Configuración del sistema
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET/POST `/admin/configuracion` — `app/seguridad/router_configuracion.py:36,43`
**Departamento:** TI
**Roles con acceso:** admin_ti, Administrador
**Colección fuente:** PocketBase — configuracion_sistema
**Acciones implementadas:** Editar ✅ · Ver ✅ · Crear/Eliminar N/A (correcto, son parámetros fijos)
**Filtros de búsqueda / Paginación:** N/A — no es una lista de registros, es un formulario único
**Modal de formulario:** ❌ — usa página completa en vez de modal
**Retroalimentación visual:** ✅ éxito vía redirect, errores de validación inline; sin confirmación previa (impacto menor, no elimina/desactiva nada)
**Campos del formulario:** longitud mínima de contraseña, requiere número, duración de sesión (días)
**Qué falta:** modal en vez de página completa. Ver también "Tu análisis" — este panel solo cubre `configuracion_sistema`; **metodos_pago** y **niveles_tarifa**, que son tablas del mismo módulo "Configuración" (`modulo_tablas`), no tienen ningún panel de gestión.

---

## WP-09 — Políticas de reembolso
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/politicas-reembolso` — `app/facturacion/router_backoffice.py:169`; POST crear — línea 208; POST editar `/backoffice/politicas-reembolso/{id}` — línea 183
**Departamento:** Finanzas
**Roles con acceso:** admin_finanzas
**Colección fuente:** **PocketBase** (una de las pocas tablas de facturación que no migró a MinIO)
**Acciones implementadas:** Crear ✅ (modal) · Editar ✅ (edición inline en la fila, no modal) · Ver ⚠️ (la edición inline hace de "ver", no hay vista de detalle separada)
**Filtros de búsqueda:** ❌
**Paginación:** ❌ (`perPage: 200` fijo)
**Modal de formulario:** ✅ solo para crear; editar es inline
**Retroalimentación visual:** ✅ mensaje de éxito vía query param; sin confirmación previa (no aplica, no hay eliminar)
**Campos del formulario:** nombre, condiciones, porcentaje de reembolso, ventana en horas
**Qué falta:** filtros y paginación — es el segundo WP más cerca de estar completo.

---

## WP-10 — Proveedores comerciales
**Estado:** ❌ FALTANTE
**Ruta actual:** no existe
**Departamento:** Ventas
**Roles con acceso:** admin_ventas, Administrador
**Colección fuente:** PocketBase — proveedores_comerciales (existe el esquema, sembrado por `scripts/pb_schema_proveedores_comerciales.py`)
**Acciones implementadas:** Crear ❌ Editar ❌ Eliminar ❌ Ver ❌
**Qué falta:** todo. La colección **existe y se usa activamente** — `app/autos/services/catalogo_service.py` y `app/hoteles/services/catalogo_service.py`/`hoteles_repo.py` la leen para resolver tarifas/comisiones — pero es puramente un catálogo de referencia sembrado por script, sin ningún router que exponga crear/editar/eliminar. Si una comisión o tarifa de proveedor cambia, hoy solo se puede corregir editando la base directamente o rehaciendo el script de siembra.

---

## WP-11 — Tickets de soporte escalados
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/ayuda/casos` — `app/centro_ayuda/router_backoffice.py:83`; POST resolver `/backoffice/ayuda/casos/{id}/resolver` — línea 118
**Departamento:** Operaciones
**Roles con acceso:** admin_operaciones, agente
**Colección fuente:** MinIO — casos_escalados
**Acciones implementadas:** Crear N/A (correcto, el sistema los crea automáticamente al escalar) · Editar estado ✅ (único destino: "resuelto") · Ver conversación ❌ — solo se muestra el mensaje único de la escalación original, no existe un hilo de mensajes ni vista de detalle (la respuesta real ocurre en Gmail, fuera del sistema)
**Filtros de búsqueda:** ✅ (estado, "mi bandeja")
**Paginación:** ❌
**Modal de formulario:** N/A (no requiere formulario, solo un botón de acción)
**Retroalimentación visual:** ⚠️ — éxito sí, sin confirmación antes de marcar resuelto (acción irreversible)
**Campos del formulario:** ninguno
**Qué falta:** paginación, confirmación antes de resolver, y — la carencia más importante — no hay forma de ver la conversación completa de un caso, solo el mensaje inicial.

---

## WP-12 — Disrupciones (gestión manual)
**Estado:** ❌ FALTANTE
**Ruta actual:** no existe gestión de disrupciones individuales. Lo único en `app/disrupciones/router_backoffice.py:20,35` es GET/POST `/backoffice/disrupciones/config-riesgo`, que configura un **umbral global de risk score**, no un listado/edición de disrupciones puntuales
**Departamento:** Operaciones
**Roles con acceso:** admin_operaciones
**Colección fuente:** MinIO — disrupciones
**Acciones implementadas:** Editar ❌ Ver detalle ❌
**Qué falta:** todo el panel. `DisrupcionesRepository.actualizar_disrupcion`/`obtener_disrupcion` solo se invocan desde servicios automáticos (`riesgo_service.py`, `notificacion_service.py`), nunca desde un router de backoffice; tampoco existe `listar_disrupciones`. Lo más cercano es `/backoffice/notificaciones` (historial de notificaciones), pero es de solo lectura y no expone el detalle de la disrupción en sí.

---

## WP-13 — Comisiones
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/comisiones` — `app/facturacion/router_backoffice.py:29`; POST marcar cobrada `/backoffice/comisiones/{id}/marcar-cobrada` — línea 78
**Departamento:** Finanzas
**Roles con acceso:** admin_finanzas
**Colección fuente:** MinIO — comisiones
**Acciones implementadas:** Crear N/A (se generan automáticamente al confirmarse un pago) · Editar ✅ (marcar cobrada) · Ver ✅
**Filtros de búsqueda:** ✅ (estado, aerolínea)
**Paginación:** ❌
**Modal de formulario:** N/A (no requiere formulario)
**Retroalimentación visual:** ⚠️ — corregido 2026-07-31: sí se renderiza (vía el fallback de `layout_app.html` que lee `request.query_params.get('mensaje')`, no hace falta que el template lo mencione explícitamente), pero **siempre con estilo de éxito (verde)**, incluso para los mensajes de error ("Esa comisión ya estaba cobrada", "Comisión no encontrada" — `router_backoffice.py:67,69`). Corregido junto con el Fix global 2 (ver más abajo).
**Campos del formulario:** ninguno
**Qué falta:** paginación y arreglar el bug de feedback silencioso.

---

## WP-14 — Remesas a proveedores
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/remesas` — `app/facturacion/router_backoffice.py:81`; POST generar — línea 100
**Departamento:** Finanzas
**Roles con acceso:** admin_finanzas
**Colección fuente:** MinIO — remesas (no confundir con remesa_comisiones, su tabla de detalle)
**Acciones implementadas:** Crear ✅ (generar remesa) · Editar estado ❌ — no existe transición a "pagada"; confirmado por comentario explícito en el código ("no hay transición a 'pagada' en el flujo actual") · Ver ✅
**Filtros de búsqueda:** ⚠️ — solo dos enlaces fijos ("Todas"/"Pendientes de pago"), no un formulario de filtros combinables
**Paginación:** ❌
**Modal de formulario:** ❌ — formulario "Generar remesa" embebido en la página, no modal
**Retroalimentación visual:** ⚠️ — corregido 2026-07-31: mismo caso que Comisiones, sí se renderiza pero siempre en verde/éxito incluso el error "Sin comisiones para remesa". Corregido junto con el Fix global 2.
**Campos del formulario:** aerolínea, período (texto libre tipo "2026-07")
**Qué falta:** la acción "editar estado" (marcar como pagada) no existe en absoluto; modal real, paginación, feedback visual, filtro combinable.

---

## WP-15 — Pagos y Facturas
**Estado:** ❌ FALTANTE (agregado por criterio propio, aprobado 2026-07-31)
**Ruta actual:** parcialmente relacionado — `/backoffice/pagos-diferidos` (`app/facturacion/router_backoffice.py:124`) captura pagos de hotel en estado "autorizado", pero no es un panel general de pagos ni de facturas
**Departamento:** Finanzas
**Roles con acceso:** admin_finanzas
**Colección fuente:** MinIO — pagos, facturas
**Acciones esperadas:** Solo Ver (sin edición) — según lo definido en priorización
**Qué falta:** todo — listado con filtros (estado, reserva, pasajero, rango de fechas), vista de detalle, sin acciones de escritura.

---

## WP-16 — Vuelos, Tarifas y Aerolíneas
**Estado:** ❌ FALTANTE / sin auditar en detalle (agregado por criterio propio, aprobado 2026-07-31)
**Departamento:** (a definir — probablemente Ventas u Operaciones, no especificado en la tabla original)
**Roles con acceso:** (a definir)
**Colección fuente:** PocketBase/MinIO — vuelos_catalogo, tarifas_vuelo, aerolineas (confirmar ubicación exacta antes de implementar)
**Acciones esperadas:** Ver y editar puntualmente — según lo definido en priorización
**Qué falta:** auditar primero qué existe hoy en `app/vuelos/` antes de implementar (no se revisó en el Paso 1 de esta auditoría) — no asumir que está vacío.

---

## WP-17 — Ofertas destacadas y Campañas de email
**Estado:** ❌ FALTANTE (agregado por criterio propio, aprobado 2026-07-31)
**Departamento:** Comercial
**Roles con acceso:** admin_comercial
**Colección fuente:** MinIO — ofertas_destacadas, campanas_email
**Acciones esperadas:** a definir con el mismo patrón CRUD de WP-06 (Cupones)
**Qué falta:** todo — no existe router ni template para ninguna de las dos tablas.

---

## WP-18 — Métodos de pago y Niveles de tarifa
**Estado:** ❌ FALTANTE (agregado por criterio propio, aprobado 2026-07-31)
**Departamento:** TI / Finanzas (mismo módulo "Configuración" que WP-08)
**Roles con acceso:** admin_ti, admin_finanzas
**Colección fuente:** PocketBase — metodos_pago, niveles_tarifa
**Acciones esperadas:** a definir — probablemente Crear/Editar/Ver (son catálogos de configuración, no transaccionales)
**Qué falta:** todo — el panel de Configuración actual (WP-08) solo cubre `configuracion_sistema`.

---

## Tu análisis — ¿Falta algún WorkPanel?

**Entidades con datos que deberían tener gestión CRUD y no están en la lista:**

- **Pagos y Facturas** (`pagos`, `facturas`, MinIO — módulo Facturación): de los 6 tipos de tabla de Facturación, la lista de WPs solo cubre Comisiones y Remesas. Ya existe `/backoffice/pagos-diferidos` (`router_backoffice.py:124`), pero es una pantalla angosta para un solo caso (capturar pagos de hotel en estado "autorizado"), no un panel general de pagos. **Facturas** no tiene ningún panel. Sigue siendo un punto ciego real cuando un cliente reclama un cargo o pide una factura reemitida.
- **Vuelos, tarifas y aerolíneas** (`vuelos_catalogo`, `tarifas_vuelo`, `aerolineas`): el módulo "Vuelos (catálogo)" existe en el RBAC (con permisos ver/crear/editar) pero ninguno de los 14 WPs cubre su catálogo. Dado que es el producto central del sistema, sorprende que no esté en la lista.
- **Ofertas destacadas y campañas de email** (`ofertas_destacadas`, `campanas_email`, módulo Ofertas): WP-06 solo cubre cupones. El módulo se llama "Ofertas y Promociones", pero las ofertas destacadas en sí (lo que se muestra en el home) y las campañas de email no tienen panel propio en la lista.
- **Métodos de pago y niveles de tarifa** (`metodos_pago`, `niveles_tarifa`, mismo módulo que WP-08): quedaron fuera del panel de Configuración actual y no aparecen en ningún otro WP.
- Los catálogos de **Hoteles, Autos, Cruceros, Actividades y Paquetes** tampoco están en la lista — no los marco como bloqueantes porque cada uno ya tiene su propio `router_backoffice.py`/reporte en su módulo (fuera del alcance de esta auditoría, no los revisé en detalle), pero si el criterio para armar la lista de 14 fue "todo lo que necesita gestión interna", valdría la pena confirmar que no falten.

**¿Algún WP de la lista es innecesario tal como está redactado?**

- **WP-04 (Reservas — "Editar estado")**: tal como está descrito no encaja con el modelo real del sistema. Los cambios de estado de una reserva son siempre consecuencia de una acción de negocio con sus propias reglas (cancelar dentro de la ventana de reembolso, confirmar pago, etc.), nunca un campo "estado" editable a mano. No lo sacaría de la lista, pero recomendaría redefinirlo como "Ver detalle + ejecutar las acciones de negocio existentes (cancelar, reenviar confirmación, etc.)" en vez de un editor de estado genérico — construir un dropdown libre de estado podría saltarse las validaciones que ya protegen `cancelar_reserva_service`/`modificar_reserva_service`.
- El resto de los 13 tienen sentido tal como están planteados dado lo que ya existe en el sistema.

**Colecciones sin ningún tipo de gestión interna que pueden ser un problema operativo:**

- **`proveedores_comerciales`** (WP-10, ya marcado como faltante): alimenta comisiones de autos/hoteles pero solo se puede tocar editando la base o re-corriendo un script — cualquier cambio de tarifa de un proveedor real requiere intervención técnica directa.
- **`facturas`** (ver arriba): sin ningún panel — cualquier disputa de cobro o reemisión de factura depende de consultar la base directamente. `pagos` tiene cobertura parcial vía `/backoffice/pagos-diferidos`, pero solo para el caso de captura diferida de hoteles.
- **`disrupciones`** (WP-12, ya marcado como faltante): Operaciones no tiene forma de revisar o corregir manualmente una disrupción individual detectada por el sistema automático, solo de configurar el umbral global de riesgo.

---

## Resumen

- **Total WP requeridos originalmente:** 14 — **más WP-15 a WP-18 agregados por criterio propio (aprobado 2026-07-31):** 18
- **Completos (✅):** 0
- **Parciales (⚠️):** 11 — WP-01 (Pasajeros: falta paginación/modal/mensaje éxito), WP-02 (Usuarios: falta filtros/paginación/confirmación al desactivar/vista detalle), WP-03 (Roles: falta filtros/paginación — el más cerca de completo), WP-04 (Reservas: falta paginación/template de detalle propio/modal — acciones según estado ya definidas, ver decisión de diseño), WP-05 (Artículos: falta filtros/paginación/vista/modal real/confirmación), WP-06 (Cupones: falta filtros/paginación/modal real/confirmación), WP-08 (Configuración: falta modal, resto N/A por diseño), WP-09 (Políticas de reembolso: falta filtros/paginación — segundo más cerca de completo), WP-11 (Tickets: falta paginación/confirmación/vista de conversación), WP-13 (Comisiones: falta paginación y arreglar bug de feedback silencioso), WP-14 (Remesas: falta acción de "marcar pagada"/modal/paginación/feedback)
- **Faltantes (❌):** 3 — WP-07 (Suscriptores newsletter, sin router ni template), WP-10 (Proveedores comerciales, catálogo de solo lectura sembrado por script), WP-12 (Disrupciones, solo existe configuración de umbral, no gestión de registros individuales)
- **Agregados por mi criterio (aprobados):** 4 — WP-15 Pagos/Facturas (solo Ver), WP-16 Vuelos/Tarifas/Aerolíneas (sin auditar en detalle todavía, revisar antes de implementar), WP-17 Ofertas destacadas + Campañas de email, WP-18 Métodos de pago + Niveles de tarifa

**Patrón transversal a marcar aparte:** ningún WP tiene paginación real y casi ninguno tiene filtros de búsqueda — no son fallas puntuales de cada panel sino un patrón repetido en todo el backoffice. Y el flash global (`layout_app.html`) siempre renderiza en verde/éxito sin importar el contenido del mensaje — confirmado en Comisiones/Remesas, donde los mensajes de error de negocio ("ya estaba cobrada", "sin comisiones para remesa") se ven idénticos a los de éxito. **Corrección 2026-07-31:** el hallazgo original decía que el mensaje "nunca se renderiza" en esos dos WP — verificado en navegador real, eso era incorrecto (sí se renderiza vía el fallback de query params del layout); el bug real es la falta de distinción visual éxito/error/advertencia, que es justamente el Fix global 2 de la implementación.

**Plan de implementación (aprobado 2026-07-31):** fixes globales primero (paginación reutilizable + feedback visual global), luego WP-01 → WP-04 → WP-05 (prioridad video), después el resto de los parciales, y por último WP-15 a WP-18. Seguimiento del progreso vía todo list de la sesión, no un documento aparte.
