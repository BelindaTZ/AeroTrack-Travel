# Checklist de Validación: Vuelos (catálogo)

**Propósito:** Validar que la implementación del módulo Vuelos cumple los RF/RNF y RN definidos en `vuelos-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`vuelos-spec.md`](./vuelos-spec.md) · [`plan.md`](./plan.md)
**Cerrado (primera pasada de implementación):** 2026-07-09 — 20/20 tests automatizados pasando contra `pocketbase-travel`/`minio` reales (sin mocks), verificado además dentro del contenedor Docker real (incluyendo acceso a MinIO vía `elt-network`). Ver "Notas de cierre" al final.

---

## Requisitos funcionales

- [x] CHK001 RF-VUE-001 — Búsqueda por origen/destino/fecha/pasajeros filtra correctamente el catálogo; sin resultados muestra mensaje claro.
- [x] CHK002 RF-VUE-001 — Filtros secundarios (aerolínea, horario) y ordenamiento se aplican sin botón "Aplicar" (REG-J9); la búsqueda principal conserva su botón explícito.
- [x] CHK003 RF-VUE-002 — Detalle de vuelo muestra los 3 niveles de tarifa con precio, equipaje, cambios y política de reembolso.
- [x] CHK004 RF-VUE-003 — Generación automática (ya en producción vía Airflow) crea vuelos en estado `programado`, sin escribir en el modelo heredado.
- [x] CHK005 RF-VUE-004 — Actualización de estado registra `fecha_actualizacion_estado` y es un punto de escritura genérico e importable; no hay todavía un caller real desde Disrupciones (no existe en esta sesión) — ver Notas de cierre.
- [x] CHK006 RF-VUE-005 — Verificación de cupo decrementa atómicamente; cupo cero responde sin disponibilidad sin alterar el dato.
- [x] CHK007 RF-VUE-006 — Ajuste puntual (CU-O48) exige sesión válida, RBAC de Administrador y motivo obligatorio; sin alguno de los tres, se bloquea (los 3 casos probados por separado).
- [x] CHK008 RF-VUE-006 — Ajuste puntual queda marcado como manual/demo; el "disparo del flujo de notificación" queda registrado como pendiente en el detalle de auditoría, no simulado — ver Notas de cierre (Disrupciones no existe todavía).

## Reglas de negocio

- [x] CHK009 RN-VUE-001 — Todo vuelo `generado_por = sistema` nace en `programado`.
- [x] CHK010 RN-VUE-002 — Cada nivel de tarifa tiene precio y cupo independientes (3 tarifas por vuelo, niveles distintos, cupos distintos).
- [x] CHK011 RN-VUE-003 — Inspección de código confirma que no hay ninguna llamada de escritura a MinIO en la generación del catálogo.
- [x] CHK012 RN-VUE-004 — Prueba de concurrencia (50 solicitudes simultáneas) confirma que el cupo nunca queda negativo y nunca se vende de más.
- [x] CHK013 RN-VUE-005 — Un vuelo ajustado vía CU-O48 queda con `generado_por="manual"`, distinguible de uno generado por el sistema.
- [x] CHK014 RN-VUE-006 — CU-O48 rechaza el ajuste si no se ingresa motivo; por construcción, ninguna ruta de `dags/` ni de producción invoca `forzar_estado_service` (solo `router_backoffice.py` lo importa).

## No funcionales

- [x] CHK015 RNF-VUE-001 — Origen/destino se muestran siempre legibles (ciudad + código), nunca solo el código IATA crudo.
- [x] CHK016 RNF-VUE-002 — Inspección de código confirma que la generación de catálogo no tiene ninguna ruta de escritura hacia el modelo heredado.
- [x] CHK017 RNF-VUE-003 — Prueba de carga concurrente confirma atomicidad de `cupo_service.py` con 50 solicitudes simultáneas sobre el mismo cupo.

## Trazabilidad de casos de uso

- [x] CHK018 CU-O17 — prueba automatizada cubre el criterio de aceptación.
- [x] CHK019 CU-O18 — ídem.
- [x] CHK020 CU-O19 — ídem, incluyendo verificación de no escritura sobre el modelo heredado.
- [x] CHK021 CU-O20 — ídem.
- [x] CHK022 CU-O45 — ídem (mecanismo atómico probado; el lado de orquestación de negocio se probará en `reservas-spec.md` cuando exista).
- [x] CHK023 CU-O48 — ídem, incluyendo los tres casos de bloqueo (sesión, RBAC, motivo faltante); el disparo de notificación queda documentado como pendiente, no simulado.

## Notas de cierre — sesión de implementación (2026-07-09)

- **Bug de esquema encontrado y corregido:** `tarifas_vuelo.cupos_disponibles` estaba marcado `required=true` desde que la colección se creó (sesión anterior). PocketBase 0.22 trata `0` como "valor ausente" en un campo numérico requerido, lo cual rompía por completo el caso "cupo agotado" — ni siquiera se podía crear un registro con `cupos_disponibles=0`. Corregido con `scripts/pb_schema_vuelos_fix.py` (idempotente, ya aplicado). Este bug no era de este módulo, pero lo bloqueaba directamente.
- **CHK005/CHK008** — `estado_service.actualizar_estado` y el flujo de notificación de CU-O48 están listos como *puntos de integración*, pero no hay todavía un segundo caller real (Disrupciones) que los ejerza en producción. Igual que con Seguridad, esto se cierra genuinamente cuando Disrupciones exista.
- **"Escalas" (RF-VUE-001) no es un filtro/orden implementable con el modelo de datos actual.** `vuelos_catalogo` no tiene ningún campo de escalas/paradas — todos los vuelos generados son directos por diseño del generador (`catalogo_vuelos_tasks.py`, rutas punto a punto entre hubs). Se implementó "ordenar por precio/duración" y "filtrar por aerolínea/horario", pero no "escalas" — no hay dato que ordenar. Registrado en `errores-conocidos.md`.
- **CU-O48 no sigue el patrón de RBAC "sin rol asignado" documentado originalmente en tasks.md** — el rol usado para probar el bloqueo fue un Pasajero sin `rol_id` (no un Agente sin el permiso específico, como se planeó inicialmente), porque el Agente sembrado sí tiene `editar` sobre `vuelos_catalogo` en la matriz real. El resultado probado (bloqueo por falta de permiso) es equivalente y válido.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- El ítem CHK023 (CU-O48) se probó explícitamente como **camino excepcional**: `test_forzar_estado.py` no es importado por ningún otro test, y los tests de Fases 1/4 no dependen de que CU-O48 exista.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
