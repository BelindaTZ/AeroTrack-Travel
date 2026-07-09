# Checklist de Validación: Vuelos (catálogo)

**Propósito:** Validar que la implementación del módulo Vuelos cumple los RF/RNF y RN definidos en `vuelos-spec.md`.
**Creado:** 2026-07-09
**Feature:** [`vuelos-spec.md`](./vuelos-spec.md) · [`plan.md`](./plan.md)

---

## Requisitos funcionales

- [ ] CHK001 RF-VUE-001 — Búsqueda por origen/destino/fecha/pasajeros filtra correctamente el catálogo; sin resultados muestra mensaje claro.
- [ ] CHK002 RF-VUE-001 — Filtros secundarios (aerolínea, horario) y ordenamiento se aplican sin botón "Aplicar" (REG-J9); la búsqueda principal conserva su botón explícito.
- [ ] CHK003 RF-VUE-002 — Detalle de vuelo muestra los 3 niveles de tarifa con precio, equipaje, cambios y política de reembolso.
- [ ] CHK004 RF-VUE-003 — Generación automática crea vuelos en estado `programado`, sin escribir en el modelo heredado.
- [ ] CHK005 RF-VUE-004 — Actualización de estado registra `fecha_actualizacion_estado` y es invocable desde `disrupciones-spec.md`.
- [ ] CHK006 RF-VUE-005 — Verificación de cupo decrementa atómicamente; cupo cero responde sin disponibilidad sin alterar el dato.
- [ ] CHK007 RF-VUE-006 — Ajuste puntual (CU-O48) exige sesión válida, RBAC de Administrador y motivo obligatorio; sin alguno de los tres, se bloquea.
- [ ] CHK008 RF-VUE-006 — Ajuste puntual queda marcado como manual/demo y dispara el flujo de notificación cuando el estado forzado es una disrupción.

## Reglas de negocio

- [ ] CHK009 RN-VUE-001 — Todo vuelo `generado_por = sistema` nace en `programado`.
- [ ] CHK010 RN-VUE-002 — Cada nivel de tarifa tiene precio y cupo independientes del `precio_base` del vuelo.
- [ ] CHK011 RN-VUE-003 — Ninguna prueba de integración detecta escritura sobre `dim_*`/`agg_*`/`fact_vuelo`.
- [ ] CHK012 RN-VUE-004 — Prueba de concurrencia confirma que dos solicitudes simultáneas por el último cupo nunca ambas tienen éxito.
- [ ] CHK013 RN-VUE-005 — Un vuelo ajustado vía CU-O48 es distinguible en su registro (origen manual/demo) de uno actualizado por CU-O20.
- [ ] CHK014 RN-VUE-006 — CU-O48 rechaza el ajuste si no se ingresa motivo; no existe ninguna ruta que lo invoque automáticamente desde un DAG o proceso de producción.

## No funcionales

- [ ] CHK015 RNF-VUE-001 — Origen/destino se muestran siempre legibles (ciudad/aeropuerto), nunca solo el código IATA crudo.
- [ ] CHK016 RNF-VUE-002 — Auditoría de código confirma que `catalogo_service.py` no tiene ninguna ruta de escritura hacia `dim_*`/`agg_*`.
- [ ] CHK017 RNF-VUE-003 — Prueba de carga concurrente confirma atomicidad de `cupo_service.py` bajo al menos 50 solicitudes simultáneas sobre el mismo cupo.

## Trazabilidad de casos de uso

- [ ] CHK018 CU-O17 — prueba automatizada cubre el criterio de aceptación.
- [ ] CHK019 CU-O18 — ídem.
- [ ] CHK020 CU-O19 — ídem, incluyendo verificación de no escritura sobre el modelo heredado.
- [ ] CHK021 CU-O20 — ídem.
- [ ] CHK022 CU-O45 — ídem (mecanismo atómico; complementar con CHK de `reservas-spec.md` para el lado de orquestación).
- [ ] CHK023 CU-O48 — ídem, incluyendo los tres casos de bloqueo (sesión, RBAC, motivo faltante) y el disparo de notificación cuando corresponde.

## Notas

- Marcar `[x]` solo con evidencia verificable.
- El ítem CHK023 (CU-O48) debe probarse explícitamente como **camino excepcional**: ninguna prueba de regresión del flujo normal (CU-O19/O20) debe depender de que CU-O48 exista.
- Ítems no completables tal como están escritos se registran en `specs/000-sistema-general/errores-conocidos.md`.
