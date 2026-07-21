# Plan de Implementación — Integraciones

**Módulo:** Integraciones
**Prefijo:** INT
**Spec:** [`integraciones-spec.md`](./integraciones-spec.md)
**Código fuente:** `app/integraciones/` *(implementado 2026-07-19)*
**Fecha:** 2026-07-18 (implementado 2026-07-19)
**Estado:** ✅ Implementado y probado — Fase 1 y 2 completas, 10/10 tests. Sigue siendo precondición de configuración de los 5 módulos de catálogo nuevos (Hoteles, Autos, Actividades, Cruceros, y refuerzo de Vuelos); ninguno de esos jobs existe todavía, así que la bitácora no tiene corridas automáticas reales hasta que alguno se implemente.

---

## Resumen

Configuración centralizada de las ~18 fuentes de datos externas del sistema y bitácora de sus corridas — generaliza CU-T06/T07 (específico de Vuelos) a las otras 4 verticales de producto. Cubre 2 RF y 4 RN sobre 2 CU (CU-T37, CU-T38). Dueño de `fuentes_datos_externas`, `sincronizaciones_log`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; sin cliente HTTP propio (no llama a ninguna API externa directamente, solo configura/monitorea las que llaman otros módulos). **Almacenamiento:** PocketBase — dueño de 2 colecciones consumidas por los 5 módulos de catálogo. **Restricciones:** REG-B3 — `host_env_var` nunca expone el valor real de una credencial, solo su nombre de variable.

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B1 (RBAC) | Sí | Ambos endpoints protegidos |
| REG-B3 (cero secretos) | Sí | `host_env_var` es solo el nombre, nunca el valor |
| REG-E3 (degradación ordenada) | Sí (aplicado por analogía) | RN-INT-002/003 — desactivar/fallar una fuente no borra el catálogo ya generado |
| REG-J9 (filtros instantáneos) | Sí | Bitácora filtrable |

Sin violaciones.

---

## Estructura del proyecto

```text
app/integraciones/
├── __init__.py
├── router_fuentes.py       # RF-INT-001
├── router_bitacora.py      # RF-INT-002
├── schemas.py
├── services/
│   └── integraciones_service.py
├── repositories/
│   └── integraciones_repo.py
└── tests/
    ├── test_fuentes.py
    └── test_bitacora.py
```

---

## Modelo de datos (resumen)

| Entidad | Rol | Validaciones clave |
|---|---|---|
| `fuentes_datos_externas` | Config por fuente | Campos editables varían por `tipo_uso` (RN-INT-001); `host_env_var` nunca es el valor real |
| `sincronizaciones_log` | Bitácora, escrita por cada job de catálogo | `ejecutado_por` nullable = automático |

---

## Fases de implementación

### Fase 1 — Sembrar y configurar fuentes (RF-INT-001)
**Precondición externa:** ninguna — puede implementarse primero, antes que los módulos de catálogo que la consumen (o en paralelo, con seed manual mientras tanto).
**Entregable:** `router_fuentes.py`, seed inicial de las ~18 fuentes conocidas.

### Fase 2 — Bitácora de sincronizaciones (RF-INT-002)
**Precondición externa:** al menos un módulo de catálogo (Vuelos u otro) escribiendo en `sincronizaciones_log` para tener datos reales que mostrar.
**Entregable:** `router_bitacora.py`.

---

## Complexity Tracking

*No aplica.*
