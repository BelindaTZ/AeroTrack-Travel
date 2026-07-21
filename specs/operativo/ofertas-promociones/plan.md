# Plan de Implementación — Ofertas y Promociones

**Módulo:** Ofertas y Promociones
**Prefijo:** OFE
**Spec:** [`ofertas-promociones-spec.md`](./ofertas-promociones-spec.md)
**Código fuente:** `app/ofertas/`
**Fecha:** 2026-07-18
**Estado:** ✅ Implementado 2026-07-19 (28 tests). Dos bugs reales encontrados y corregidos en verificación en vivo — ver `checklist.md`.

---

## Resumen

Ofertas destacadas curadas, destinos populares calculados por agregación real (sin catálogo propio), cupones de descuento aplicables en checkout con trazabilidad de canje, newsletter y términos y condiciones. Cubre 5 RF y 4 RN sobre 5 CU (CU-O101–O105). Dueño de `ofertas_destacadas`, `cupones_descuento`, `cupones_uso`, `newsletter_suscripciones`.

---

## Contexto técnico

**Lenguaje/Versión:** Python 3.12. **Dependencias:** FastAPI + Jinja2; sin cliente HTTP externo para este nivel (SendGrid vive en la config táctica, CU-T31). **Almacenamiento:** PocketBase — dueño de 4 colecciones; CU-O102 no persiste nada nuevo, es una consulta agregada sobre `busquedas_recientes`/`reservas`. **Restricciones:** RN-OFE-002 (idempotencia de canje de cupón, análogo a REG-D1 aunque no mueva dinero real por Stripe directamente — el descuento sí afecta el monto cobrado).

---

## Constitution Check

| Principio | Aplica | Verificación en este plan |
|---|---|---|
| REG-D1 (idempotencia en operaciones de dinero) | Sí | RN-OFE-002 — un cupón no se aplica dos veces a la misma reserva |
| REG-G2 (transparencia de precio) | Sí | El descuento aplicado se muestra explícito en el desglose de checkout |
| REG-B4 (auditoría) | Sí | Canje de cupón y suscripción auditan |

Sin violaciones.

---

## Estructura del proyecto

```text
app/ofertas/
├── __init__.py
├── router_ofertas.py       # RF-OFE-001,002,005
├── router_cupones.py       # RF-OFE-003
├── router_newsletter.py    # RF-OFE-004
├── schemas.py
├── services/
│   ├── ofertas_service.py
│   ├── destinos_populares_service.py   # agregación, sin colección propia
│   └── cupon_service.py                # validación + canje idempotente
├── repositories/
│   └── ofertas_repo.py
├── templates/
│   └── ofertas.html, destinos_populares.html
└── tests/
    ├── test_ofertas.py
    ├── test_cupones.py
    └── test_newsletter.py
```

---

## Fases de implementación

### Fase 1 — Ofertas destacadas y términos (RF-OFE-001, 005)
**Precondición externa:** `specs/tactico/ofertas-promociones/` no bloquea esta fase (no hay CU-T que las configure directamente, solo CU-T30 para cupones) — sembrar ofertas manualmente para pruebas si hace falta.
**Entregable:** `router_ofertas.py`.

### Fase 2 — Destinos populares (RF-OFE-002)
**Precondición externa:** datos reales de `busquedas_recientes` (retrofit pendiente en los módulos de producto, ver `cuenta-mis-viajes-spec.md`) o de `reservas`.
**Entregable:** `destinos_populares_service.py`.

### Fase 3 — Cupones en checkout (RF-OFE-003)
**Precondición externa:** `specs/tactico/ofertas-promociones/` (CU-T30) para cupones reales; Carrito/Reservas con checkout implementado (`reserva_items`, no implementado todavía).
**Entregable:** `router_cupones.py`, `cupon_service.py` con la validación idempotente de RN-OFE-002.

### Fase 4 — Newsletter (RF-OFE-004)
**Precondición externa:** ninguna — implementable de inmediato.
**Entregable:** `router_newsletter.py`.

---

## Complexity Tracking

*No aplica.*
