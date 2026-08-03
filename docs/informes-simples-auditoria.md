# Auditoría de Informes Simples — AeroTrack Travel (2026-08-01)

> Metodología: se revisó cada uno de los 23 IS listados en el encargo contra
> el código real (`app/*/router_*.py`, templates, `scripts/seed_*.py` para
> RBAC). Se aplicó el principio del documento de actores: un listado
> operativo ya existente que el rol táctico puede alcanzar por RBAC cuenta
> como (al menos parcialmente) resuelto — no se exige una vista nueva
> duplicada si la que ya existe sirve.

---

## IS-01 — Listado de usuarios del sistema
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/admin/usuarios` — `app/seguridad/router_usuarios.py:28`
**Rol con acceso:** admin_ti (`seguridad`: ver/crear/editar/eliminar, `scripts/seed_roles_departamento.py:53`), Administrador
**Colección fuente:** PocketBase — `usuarios` (filtrados a `roles.tipo_panel="backoffice"`, ver `usuarios_service.py:155` — "interno" = tiene un rol de panel backoffice, excluye pasajeros)
**Filtros implementados:** período ❌ (no aplica — es un padrón de cuentas, no un log temporal) · estado ✅ (activo/inactivo) · otros: nombre, email, rol_id
**Paginación:** ✅
**Campos visibles en la tabla:** Usuario, Rol, Activo, Creado, Acciones
**Campos que debería mostrar:** ya cubre lo necesario para auditar accesos (nombre, rol, estado, fecha de alta)
**Qué falta:** nada — cumple el propósito de "revisar usuarios registrados para auditar accesos activos, detectar cuentas inactivas" del doc de actores.

---

## IS-02 — Log de auditoría por período y actor
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/admin/auditoria` — `app/seguridad/router_auditoria.py`; export CSV en `/admin/auditoria/exportar`
**Rol con acceso:** admin_ti (`seguridad`: ver — acceso completo al módulo, sin restricción Nivel 2), Administrador
**Colección fuente:** PocketBase — `auditoria` (**corrección sobre la versión anterior de este documento**: se había anotado MinIO por error; `SeguridadRepository.list_auditoria`/`insertar_auditoria` usan `self._client`, el cliente de PocketBase, no `minio_operational_client` — esta colección nunca se migró)
**Filtros implementados:** período ✅ (desde/hasta) · estado N/A (no aplica a un log) · otros: **actor por email ✅ (nuevo)**, accion ✅, tabla ✅
**Paginación:** ✅ (nuevo, 25/página) — usa paginación nativa de PocketBase (`page`/`perPage` de `list_auditoria`), envuelta en el mismo `Pagina` de `app/shared/paginacion.py` para reusar `_paginacion.html`
**Campos visibles en la tabla:** Fecha, Usuario, Acción, Tabla, Registro, IP
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada. Nota: el backend ya soportaba filtrar por `usuario_id`, pero el formulario no tenía ningún campo para usarlo — un director no conoce el id interno de un usuario. Se agregó un filtro por **email** que se resuelve a `usuario_id` en el router (`_resolver_actor_id`).

---

## IS-03 — Estado de sincronizaciones por fuente externa
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/backoffice/integraciones/bitacora`; export CSV en `/backoffice/integraciones/bitacora/exportar`
**Rol con acceso:** admin_ti (`integraciones`: ver/editar/ejecutar, `scripts/seed_roles_departamento.py:54`), Administrador
**Colección fuente:** MinIO — `sincronizaciones_log`
**Filtros implementados:** período ✅ (desde/hasta, sobre `fecha_inicio`) · estado ✅ (nuevo: exitoso/parcial/fallido) · otros: fuente_id ✅
**Paginación:** ✅ (nuevo, 25/página)
**Campos visibles en la tabla:** Inicio, Fuente, Producto, Estado, Procesados/nuevos/actualizados, Cuota, Ejecutado por
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-04 — Listado completo de pasajeros registrados
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/pasajeros` — `app/pasajeros/router_backoffice.py:146`
**Rol con acceso:** admin_clientes (`pasajeros`: ver/crear/editar/eliminar, `scripts/seed_roles_departamento.py:83`), agente, Administrador
**Colección fuente:** MinIO — `pasajeros`
**Filtros implementados:** período ❌ (no aplica — es el padrón completo) · estado N/A · otros: nombre, email, documento, teléfono
**Paginación:** ✅
**Campos visibles en la tabla:** Nombre, Correo, Teléfono, Documento, Acciones
**Campos que debería mostrar:** ya cubre lo necesario; sin filtro, ya devuelve el listado completo (`pasajeros_service.py:125`: "Sin ningún filtro, devuelve el listado completo")
**Qué falta:** nada para "verificar calidad de datos... detectar registros incompletos" — aunque no hay un indicador visual directo de "sin documento"/"sin email válido" en la tabla (haría falta mirar cada fila), no es un vacío de listado sino de una columna de calidad de dato — nota, no bloqueante.

---

## IS-05 — Pasajeros nuevos por período y canal de registro
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/pasajeros/reporte` — `app/pasajeros/router_backoffice.py:66` (comparte pantalla con CU-T05, exportar con filtros, en `/reporte/exportar` línea 109)
**Rol con acceso:** admin_clientes, agente, Administrador
**Colección fuente:** MinIO — `pasajeros`
**Filtros implementados:** período ✅ (desde/hasta) · estado N/A · otros: destino, frecuencia_min, **canal_registro ✅** — exactamente lo pedido por CU-T37
**Paginación:** ❌ — `contexto.update({"pasajeros": filas, ...})` sin `paginar()` (línea 97), la tabla completa se vuelca sin cortar.
**Campos visibles en la tabla:** Nombre, Email, Registrado, Canal, Reservas, Destinos; además un resumen por canal (`por_canal`, conteo agregado)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** paginación — con un rango de fechas amplio podría traer cientos de filas de una vez.

---

## IS-06 — Estado del DAG del catálogo de vuelos
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/vuelos/monitor-dag` — `app/vuelos/router_monitor.py:16`
**Rol con acceso:** admin_ventas (`vuelos_catalogo`: ver, `scripts/seed_roles_departamento.py:71`), admin_ti (ver), admin_operaciones (ver), Administrador
**Colección fuente:** Airflow REST API en vivo (`app/vuelos/repositories/airflow_client.py:19`) — no es una colección MinIO/PocketBase leída con filtro, es un estado consultado en tiempo real
**Filtros implementados:** período N/A (siempre muestra las últimas 10 corridas) · estado ✅ (estado de cada corrida visible)
**Paginación:** N/A — por diseño son "las últimas 10 corridas", no un listado histórico paginable
**Campos visibles en la tabla:** Fecha de ejecución, Estado, Inicio, Fin
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada para el propósito de "monitorear estado del DAG" (CU-T07); si se quisiera historial más largo que 10 corridas habría que exponer el parámetro `limite` de `estado_dag()`, no es un vacío real hoy.

---

## IS-07 — Catálogo de vuelos activo (contenido del NDJSON en MinIO)
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 3)
**Ruta actual:** GET `/backoffice/vuelos/catalogo-publicado`; export CSV en `/backoffice/vuelos/catalogo-publicado/exportar`
**Rol con acceso:** admin_ventas, admin_operaciones, admin_ti (`vuelos_catalogo`: ver), Administrador
**Colección fuente:** MinIO — bucket `aerotrack-travel-catalog`, NDJSON leído con `leer_coleccion("vuelos_catalogo")` (`app/shared/minio_catalog_reader.py`) — confirmado que es **distinto** de `/backoffice/vuelos` (WP-16), que lee `vuelos_catalogo` directo de PocketBase
**Filtros implementados:** origen ✅, destino ✅, aerolínea ✅
**Paginación:** ✅ (50/página, según lo pedido — el resto de informes usa 25)
**Campos visibles en la tabla:** Origen, Destino, Aerolínea, Precio base, Actualizado — más un banner con la fecha de última publicación del snapshot completo (`stat_object` sobre el NDJSON, nuevo `fecha_publicacion()` en `minio_catalog_reader.py`), que es lo que realmente permite detectar el desfase de hasta 24h contra PocketBase
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-08 — Reservas por estado y período (con horas restantes en pendiente_pago)
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/reservas/reporte` — `app/reservas/router_reportes.py:24`
**Rol con acceso:** admin_ventas (`reservas`: ver/crear/editar/eliminar), agente, Administrador
**Colección fuente:** MinIO — `reservas`
**Filtros implementados:** período ✅ (desde/hasta) · estado ✅ · otros: canal, código de reserva, nombre de pasajero
**Paginación:** ✅
**Campos visibles en la tabla:** Código, Pasajero, Estado, Canal, Total, Fecha reserva, **Vence en** (horas para vencer, calculado en `reportes_service.py`), Acciones
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-09 — Reservas próximas a vencer por pago pendiente (próximas 24h)
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2) — fusionado con IS-08
**Ruta actual:** misma que IS-08, `/backoffice/reservas/reporte`; export CSV en `/backoffice/reservas/reporte/exportar`
**Rol con acceso:** mismo que IS-08
**Colección fuente:** MinIO — `reservas`
**Filtros implementados:** checkbox **"Solo próximas a vencer (<24h)" ✅ (nuevo)** — filtra a `horas_para_vencer < 24` y ordena ascendente por urgencia al activarse
**Paginación:** ✅ (heredada de IS-08)
**Campos visibles en la tabla:** los mismos que IS-08, incluida "Vence en"
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-10 — Ítems de reserva por tipo de producto
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 3)
**Ruta actual:** GET `/backoffice/reservas/items`; export CSV en `/backoffice/reservas/items/exportar`
**Rol con acceso:** admin_ventas (`reservas`: ver), agente, Administrador
**Colección fuente:** MinIO — `reserva_items`
**Filtros implementados:** tipo_producto ✅, período ✅ (sobre `created` del ítem), estado de la reserva padre ✅
**Paginación:** ✅ (25/página)
**Campos visibles en la tabla:** Tipo, Reserva (código), Descripción, Precio, Fecha, Estado de la reserva — la descripción reutiliza `describir_item()` (`app/shared/descripcion_producto.py`), ya compartida por Carrito/Mis reservas, no se reimplementó
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-11 — Vuelos activos en monitoreo con estado en tiempo real
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/backoffice/vuelos/activos`; export CSV en `/backoffice/vuelos/activos/exportar`
**Rol con acceso:** admin_operaciones (`vuelos_catalogo`: ver), admin_ventas, admin_ti, Administrador
**Colección fuente:** PocketBase — `vuelos_catalogo` (filtrado a estado programado/retrasado/desviado)
**Filtros implementados:** aerolínea ✅ (nuevo), ruta ✅ (nuevo, origen o destino) · **nivel de riesgo alto/medio/bajo ✅ (nuevo)** — el encargo pedía este filtro pero no existía ningún campo de riesgo persistido por vuelo (confirmado con el usuario antes de construir, ver decisión 2026-08-01): se calcula en vivo reutilizando `riesgo_service.py` (100 - OTP histórico por aerolínea vía `agg_otp_aerolinea_mes`), bucketeado contra el mismo umbral configurable que dispara una disrupción real (`simulador_disrupciones.umbral_riesgo_pct`, default 20%; medio = mitad de ese umbral hacia arriba)
**Paginación:** ✅ (nuevo, 25/página)
**Campos visibles en la tabla:** Vuelo, Aerolínea, Ruta, Fecha salida, Hora prog., Estado, **Riesgo (nuevo)**
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada. Nota de diseño: el badge "medio" y "alto" usan el mismo token de color base (`--at-warning-fg`/`--at-danger` son ambos tonos "coral" en este sistema de diseño, ver `aerotrack.css`) — se distinguen por tono/saturación y por el % mostrado, pero no son tan visualmente distintos como el verde de "bajo"; queda como observación, no bloqueante.

---

## IS-12 — Historial de notificaciones de disrupción enviadas
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/notificaciones` — `app/disrupciones/router_notificaciones.py:78`
**Rol con acceso:** admin_operaciones (`disrupciones`: ver — acceso completo al módulo, sin restricción Nivel 2), Administrador
**Colección fuente:** MinIO — `notificaciones` (nota: el encargo dice colección `disrupciones`, pero el registro de "notificación enviada" vive en su propia colección `notificaciones`, vinculada a `disrupciones` por `disrupcion_id` — ver `app/disrupciones/repositories/disrupciones_repo.py`)
**Filtros implementados:** período ❌ · estado ✅ (`estado_envio`) · otros: canal ✅
**Paginación:** ❌ — `listar_notificaciones()` sin `paginar()`, vuelca todo
**Campos visibles en la tabla:** Fecha, Reserva, Canal, Asunto, Estado
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** filtro de período (desde/hasta) y paginación — para "controlar el volumen de disrupciones comunicadas... auditar la actividad del sistema proactivo" un director necesita acotar por fecha, hoy no puede.

---

## IS-13 — Bandeja de tickets de soporte escalados por estado y antigüedad
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/backoffice/ayuda/casos`; export CSV en `/backoffice/ayuda/casos/exportar`
**Rol con acceso:** admin_operaciones (`centro_ayuda`: ver/crear/editar), agente (Nivel 2 restringido solo a tabla `casos_escalados`, `scripts/seed_centro_ayuda_rbac.py:30`), Administrador
**Colección fuente:** MinIO — `casos_escalados` (el encargo lo llama `tickets_soporte`, es la misma entidad con otro nombre en este proyecto)
**Filtros implementados:** período ✅ (nuevo, desde/hasta sobre `fecha_creacion`) · estado ✅ · otros: mi_bandeja ✅ (ver IS-17)
**Paginación:** ✅ (agregada en WP-11, sesión 2026-07-31)
**Campos visibles en la tabla:** vista de tarjetas, cada una con asunto, pasajero, fecha, mensaje, estado, hilo Gmail, y **"X días abierto" (nuevo)** — calculado contra `fecha_resolucion` si ya está resuelto o contra "ahora" si sigue abierto
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-14 — Listado de artículos de ayuda por categoría y estado
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/ayuda/articulos` — `app/centro_ayuda/router_backoffice.py:54`
**Rol con acceso:** admin_operaciones (`centro_ayuda`: ver/crear/editar), Administrador — agente está excluido por RBAC Nivel 2 (correcto, coincide con el actor de IS-14)
**Colección fuente:** PocketBase — `articulos_ayuda`
**Filtros implementados:** período ❌ (no aplica — es un catálogo de contenido, no un log temporal) · estado ✅ (activo/archivado) · otros: categoría, texto
**Paginación:** ✅
**Campos visibles en la tabla:** los del listado con filtros ya construido en WP-05
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-15 — Reservas asistidas propias por período (vista del agente)
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/reservas/mi-cartera` — `app/reservas/router_reportes.py:64`
**Rol con acceso:** agente (`reservas`: ver), Administrador
**Colección fuente:** MinIO — `reservas` (mismo `listar_reservas_backoffice`, recortado a `agente_id == usuario.id`)
**Filtros implementados:** período ✅ (desde/hasta) · estado ✅ · otros: canal, código, nombre de pasajero — idénticos a IS-08 pero autoscopeados al agente logueado
**Paginación:** ✅
**Campos visibles en la tabla:** los mismos que IS-08
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-16 — Cola de reservas con pago próximo a vencer en mi cartera
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2) — fusionado con IS-15
**Ruta actual:** misma que IS-15, `/backoffice/reservas/mi-cartera`; export CSV en `/backoffice/reservas/mi-cartera/exportar`
**Rol con acceso:** agente, Administrador
**Colección fuente:** MinIO — `reservas`
**Filtros implementados:** los de IS-15, más el mismo checkbox **"Solo próximas a vencer (<24h)" ✅ (nuevo)** de IS-09; la vista ya ordenaba por `horas_para_vencer` ascendente
**Paginación:** ✅
**Campos visibles en la tabla:** los mismos que IS-15
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-17 — Casos de soporte escalados pendientes propios
**Estado:** ✅ COMPLETO
**Ruta actual:** misma que IS-13, `/backoffice/ayuda/casos?mi_bandeja=true`
**Rol con acceso:** agente (Nivel 2 restringido a `casos_escalados`)
**Colección fuente:** MinIO — `casos_escalados`
**Filtros implementados:** `mi_bandeja=true` filtra a "abiertos (pool disponible) + los que yo ya resolví" (`router_backoffice.py:140-148`) — exactamente "mi bandeja activa" de CU-T46
**Paginación:** ✅
**Campos visibles en la tabla:** los mismos que IS-13
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada — comparte el mismo gap de período que IS-13 pero el requisito de IS-17 ("pendientes propios") no pide período explícitamente.

---

## IS-18 — Pagos procesados por período
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/pagos` — `app/facturacion/router_backoffice.py:257` (WP-15, sesión 2026-08-01)
**Rol con acceso:** admin_finanzas (`facturacion`: ver — acceso completo al módulo, sin restricción Nivel 2), Administrador
**Colección fuente:** MinIO — `pagos`
**Filtros implementados:** período ✅ (desde/hasta) · estado ✅ · otros: código de reserva, nombre de pasajero
**Paginación:** ✅
**Campos visibles en la tabla:** Fecha, Reserva, Pasajero, Monto, Estado, Acciones (Ver detalle)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-19 — Facturas emitidas por período
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/backoffice/facturas` — `app/facturacion/router_backoffice.py:285` (WP-15)
**Rol con acceso:** admin_finanzas (`facturacion`: ver — acceso completo al módulo), Administrador
**Colección fuente:** MinIO — `facturas`
**Filtros implementados:** período ✅ (desde/hasta) · estado N/A (una factura no tiene estado, es un documento emitido) · otros: código de reserva, nombre de pasajero
**Paginación:** ✅
**Campos visibles en la tabla:** Número, Fecha, Reserva, Pasajero, Total, Acciones (Ver + descargar PDF)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-20 — Comisiones pendientes de cobro por aerolínea
**Estado:** ⚠️ PARCIAL
**Ruta actual:** GET `/backoffice/comisiones` — `app/facturacion/router_backoffice.py:37`
**Rol con acceso:** admin_finanzas (`facturacion`: ver — acceso completo al módulo), Administrador
**Colección fuente:** MinIO — `comisiones`
**Filtros implementados:** período ❌ · estado ✅ (`pendiente_cobro`/`cobrada`) · otros: aerolínea ✅ — cubre literalmente "por aerolínea" de CU-T51
**Paginación:** ✅ (agregada en WP-13, sesión 2026-07-31)
**Campos visibles en la tabla:** Fecha, Aerolínea, Monto, Estado, (acción marcar cobrada)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** filtro de período (desde/hasta) — el resto ya está completo, es el WP más cerca de cerrar esta categoría.

---

## IS-21 — Remesas pendientes de pago a proveedores
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/backoffice/remesas`; export CSV en `/backoffice/remesas/exportar`
**Rol con acceso:** admin_finanzas (`facturacion`: ver — acceso completo al módulo), Administrador
**Colección fuente:** MinIO — `remesas`
**Filtros implementados:** período ✅ (nuevo, desde/hasta sobre `fecha_generacion`) · estado ✅ (`pendiente`/`pagada`, WP-14) · aerolínea ✅ (nuevo)
**Paginación:** ✅ (WP-14)
**Campos visibles en la tabla:** Fecha, Aerolínea, Periodo, Monto total, Estado, Acciones
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-22 — Historial de disrupciones propias (vista del pasajero autenticado)
**Estado:** ✅ COMPLETO
**Ruta actual:** GET `/notificaciones` — `app/disrupciones/router_notificaciones.py:47`
**Rol con acceso:** pasajero (`verificar_sesion`, sin RBAC de módulo — autoservicio)
**Colección fuente:** MinIO — `notificaciones`, recortado a reservas del pasajero logueado cuyo vuelo ya salió (`_solo_reservas_pasadas`, línea 29 — "una disrupción de un vuelo futuro pertenece al flujo normal de notificaciones activas, no a 'historial'")
**Filtros implementados:** período ❌ (no aplica — ya está acotado a "mis reservas pasadas") · estado ✅ (`estado_envio`) · otros: canal ✅
**Paginación:** ❌ — no pagina, pero el volumen esperado por pasajero es bajo (no es un problema práctico como en las vistas admin)
**Campos visibles en la tabla:** Fecha, Reserva, Canal, Asunto, Estado
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada relevante para el propósito (CU-T49).

---

## IS-23 — Destinos y productos más guardados como favoritos
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 2)
**Ruta actual:** GET `/backoffice/ofertas/reporte-favoritos`; export CSV en `/backoffice/ofertas/reporte-favoritos/exportar`
**Rol con acceso:** admin_comercial (`ofertas`: ver/crear/editar), Administrador
**Colección fuente:** MinIO — `favoritos` (vía `CuentaRepository.listar_todos_favoritos()`)
**Filtros implementados:** período ✅ (nuevo, desde/hasta sobre `fecha_guardado`) · tipo ✅ (nuevo, derivado dinámicamente de los tipos realmente guardados) · ranking ya ordenado por `veces_guardado` descendente
**Paginación:** ✅ (nuevo, 25/página)
**Campos visibles en la tabla:** Tipo, Producto, Veces guardado + total de favoritos y productos distintos (ambos respetan el filtro activo)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## IS-24 — Reembolsos procesados por período
**Estado:** ✅ COMPLETO (implementado 2026-08-01, Prioridad 3)
**Ruta actual:** GET `/backoffice/reembolsos`; export CSV en `/backoffice/reembolsos/exportar`
**Rol con acceso:** admin_finanzas (`facturacion`: ver — acceso completo al módulo), Administrador
**Colección fuente:** MinIO — **`reembolsos`** (colección dedicada, confirmada en vivo)
**Filtros implementados:** período ✅ (sobre `fecha_solicitud`), estado ✅ (procesado/rechazado), motivo ✅ (texto libre), tipo de producto ✅ — resuelto vía `reserva_items` de la reserva asociada (un reembolso es de la reserva completa, no de un ítem; filtra a reservas que tengan al menos un ítem de ese tipo)
**Paginación:** ✅ (25/página)
**Campos visibles en la tabla:** Fecha, Reserva (código), Pasajero, Motivo, Monto, Estado — join con `reservas`/`pasajeros` vía `_enriquecer_con_reserva`, reusado de `reportes_service.py` (mismo patrón que Pagos/Facturas)
**Campos que debería mostrar:** ya cubre lo necesario
**Qué falta:** nada.

---

## Tu análisis — ¿Falta algún informe simple?

### ¿Hay algún dato que un jefe departamental necesitaría ver y no está en la lista de 23?

- **`reembolsos`** (MinIO, Finanzas): no aparece en la lista de 23 y **no tiene absolutamente ninguna vista de listado** — confirmado por búsqueda exhaustiva, no existe ningún router que exponga `listar_reembolsos` o similar. Un pasajero ve su reembolso indirectamente dentro del detalle de su reserva, pero admin_finanzas no tiene forma de ver "todos los reembolsos procesados este mes" pese a que es exactamente el mismo tipo de informe que IS-18/19/20/21 (mismo módulo, mismo patrón, misma colección MinIO ya usada por `reembolso_service.py`). Es el candidato más claro a agregar — completaría el cuadro de Finanzas (pagos, facturas, comisiones, remesas, **reembolsos**).
- El resto de colecciones con datos reales (`intentos_fallidos` vía `auditoria`, `carrito_abandonado` vía `carritos`) ya tienen su propio informe/reporte fuera de esta lista de 23 (`/admin/seguridad/intentos-fallidos`, CU-T01; `/backoffice/carrito/reporte`, CU-T27) — no son un vacío, solo no estaban en el alcance de este documento.

### ¿Hay algún IS ya cubierto de otra forma que no necesita vista separada?

- **IS-09 y IS-16** ya están fusionados con IS-08 e IS-15 respectivamente, tal como anticipaba el encargo — no ameritan una ruta nueva, solo un ajuste de filtro/orden en la vista existente.
- **IS-17** está totalmente cubierto por el mismo endpoint de IS-13 (`mi_bandeja=true`) — no es una vista separada y no hace falta que lo sea.
- **IS-06** (estado del DAG) es, por naturaleza, una consulta en vivo a Airflow, no un listado de una colección con filtro de período — cumple el propósito igual, pero vale aclarar que no es comparable 1:1 con el resto (no tiene "período" porque siempre muestra el estado actual).

### ¿Hay colecciones en MinIO/PocketBase sin ninguna vista de listado accesible para ningún rol admin?

- **`reserva_items`** (IS-10) — confirmado FALTANTE arriba.
- **catálogo NDJSON de vuelos en MinIO** (IS-07) — confirmado FALTANTE arriba; es distinto de `vuelos_catalogo` en PocketBase, que sí tiene panel (WP-16).
- **`reembolsos`** — ver arriba, candidato nuevo no listado originalmente.
- Verifiqué también `metodos_pago`/`niveles_tarifa` (WP-18) y `proveedores_comerciales` (WP-10) — esos ya tienen panel de gestión completo de la auditoría de WorkPanels cerrada ayer, no son informes simples faltantes.

---

## Resumen

- **Total IS requeridos:** 24 (23 originales + IS-24, agregado el 2026-08-01)
- **Completos (✅):** 24 de 24 — cierre total del catálogo, sesión 2026-08-01
  - Prioridad 1: IS-05, IS-12, IS-20
  - Prioridad 2: IS-02, IS-03, IS-09, IS-11, IS-13, IS-16, IS-21, IS-23
  - Prioridad 3: IS-07, IS-10, IS-24
- **Parciales (⚠️):** 0
- **Faltantes (❌):** 0

## IMPORTANTE
Esto es solo auditoría — no se implementó nada. Quedo a la espera de tu confirmación sobre qué priorizar antes de tocar código.
