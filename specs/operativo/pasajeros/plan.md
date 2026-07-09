# Plan de Implementación — Pasajeros

**Módulo:** Pasajeros
**Prefijo:** PAS
**Spec:** [`pasajeros-spec.md`](./pasajeros-spec.md)
**Código fuente:** `app/pasajeros/`
**Fecha:** 2026-07-09
**Estado:** Draft — pendiente de revisión antes de iniciar implementación

---

## Resumen

Dar al pasajero autoservicio sobre su historial de reservas y sus datos de contacto, y dar al backoffice (Agente/Administrador) una vía de búsqueda y soporte sobre esos mismos datos. Cubre 4 RF, 2 RNF y 4 RN sobre 3 CU (CU-O14–O16).

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12 (REG-I1).
**Dependencias principales:** FastAPI + Jinja2 + Bootstrap 5 (REG-I2); cliente PocketBase para `pasajeros`; lectura de `usuarios` (dueño: Seguridad) y `reservas` (dueño: Reservas) sin escritura cruzada de colección.
**Almacenamiento:** PocketBase — este módulo es dueño de `pasajeros`; lee `usuarios` y `reservas` como colecciones externas.
**Pruebas:** pytest + `httpx.AsyncClient`.
**Plataforma objetivo:** contenedor Linux vía Docker/docker-compose.
**Tipo de proyecto:** servicio web (rutas FastAPI + templates Jinja2/Bootstrap 5).
**Objetivos de rendimiento:** búsqueda de backoffice con filtro instantáneo, sin percepción de recarga completa de página (REG-J9).
**Restricciones:** ningún dato de pasajero fuera de su alcance RBAC de Nivel 2 puede ser visible/editable desde backoffice (RN-PAS-003).
**Escala/alcance:** módulo pequeño — 4 RF, depende de Seguridad, Reservas y Disrupciones (como consumidor de sus datos de contacto).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-B1 (RBAC) | Sí | RF-PAS-003/004 pasan por `rbac_service` de Seguridad (CU-O43) antes de exponer datos de otro pasajero |
| REG-B4 (auditoría) | Sí | Toda edición desde backoffice (RF-PAS-004) audita quién hizo el cambio (propio vs. en nombre de) |
| REG-E1 (indirecta) | Sí | El dato de contacto mantenido aquí es el canal del que depende Disrupciones; no se bloquea ninguna funcionalidad por dato desactualizado (RN-PAS-002), pero se documenta el riesgo |
| REG-G1 (autoservicio) | Sí | RF-PAS-001/002 no requieren intervención de agente |
| REG-J9 (filtros instantáneos) | Sí | RNF-PAS-001 (historial) y RF-PAS-003 (búsqueda backoffice) |

Sin violaciones — no se llena Complexity Tracking.

---

## Estructura del proyecto

### Documentación (este módulo)

```text
specs/operativo/pasajeros/
├── pasajeros-spec.md
├── plan.md
└── checklist.md
```

### Código fuente

```text
app/pasajeros/
├── __init__.py
├── router_historial.py      # RF-PAS-001
├── router_contacto.py       # RF-PAS-002
├── router_backoffice.py     # RF-PAS-003, 004
├── schemas.py
├── services/
│   └── pasajeros_service.py # valida RN-PAS-001..004, coordina con Seguridad (rbac/audit) y Reservas (lectura)
├── repositories/
│   └── pocketbase_client.py
├── templates/
│   ├── mis_reservas.html
│   └── backoffice/ (buscar_pasajeros.html, detalle_pasajero.html)
└── tests/
    ├── test_historial.py
    ├── test_contacto.py
    └── test_backoffice.py
```

**Decisión de estructura:** este módulo depende de `Depends(verificar_sesion)` y `Depends(verificar_rbac)` importados de `app/seguridad/services`, sin reimplementar ninguna lógica de sesión/RBAC propia.

---

## Modelo de datos (resumen)

| Entidad | Rol en este módulo |
|---|---|
| `pasajeros` | Dueño — perfil extendido, 1:1 con `usuarios` |
| `usuarios` | Lectura (Seguridad) — nombre, correo |
| `reservas` | Lectura (Reservas) — historial de RF-PAS-001 |

---

## Contratos de API

- `GET /mis-reservas`, `POST /mi-perfil/contacto` — RF-PAS-001, 002.
- `GET /backoffice/pasajeros`, `GET /backoffice/pasajeros/{id}`, `PUT /backoffice/pasajeros/{id}` — RF-PAS-003, 004.

---

## Fases de implementación

### Fase 1 — Consultar historial de reservas propio (RF-PAS-001)
**Precondición externa:** Seguridad Fase 1 (sesión) completa; puede desarrollarse contra datos de prueba antes de que Reservas exista, pero la integración final requiere `reservas-spec.md` implementado.
**Entregable:** `router_historial.py`, filtro instantáneo por estado/fecha (RNF-PAS-001).

### Fase 2 — Editar datos de contacto (RF-PAS-002)
**Precondición externa:** Seguridad Fase 3 (perfil propio) completa — esta fase extiende esa misma superficie de UI.
**Entregable:** `router_contacto.py`, validación de formato de teléfono (RNF-PAS-002).

### Fase 3 — Backoffice: buscar y gestionar pasajeros (RF-PAS-003, 004)
**Precondición externa:** Seguridad Fase 2 (RBAC/auditoría) completa.
**Entregable:** `router_backoffice.py`, con filtro instantáneo (REG-J9) y respeto estricto de RBAC Nivel 2 (RN-PAS-003).

---

## Complexity Tracking

*No aplica.*
