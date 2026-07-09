# Errores conocidos — Sistema AeroTrack Travel (Nivel Operativo)

> Se completa durante la implementación de cada módulo: cada entrada debe registrar el error encontrado, el módulo/CU afectado, la causa raíz y el estado de resolución (abierto / mitigado / cerrado), para no perder el conocimiento acumulado durante el desarrollo.

## Módulo Seguridad (implementado 2026-07-09)

- **[abierto] RF-SEG-014 — alerta de fallo de auditoría es solo log, no notificación visible.**
  Causa raíz: no existe todavía ningún canal de notificaciones internas a Administrador (pertenece a un nivel Táctico/futuro). `audit_service.insertar()` hace `logger.critical(...)` cuando la inserción falla, en vez de una alerta accionable en la UI. Mitigado por ahora: el log crítico es monitoreable a nivel de infraestructura.

- **[abierto] RN-SEG-011 — retención de datos personales sin reservas/pagos reales que verificar.**
  Causa raíz: Reservas y Facturación están fuera de alcance de esta sesión. `POST /mi-perfil/solicitar-eliminacion` registra la solicitud en auditoría pero no ejecuta ninguna verificación de retención real. Se debe revisar este endpoint cuando Reservas/Facturación existan, para conectar la verificación real de "reservas o pagos en curso".

- **[abierto] RNF-SEG-002/003 — objetivos de rendimiento (login <1s, verificación de sesión <50ms) no medidos.**
  Causa raíz: sin prueba de carga ni profiling en esta sesión. `verificar_sesion` hace un round-trip HTTP a PocketBase (`auth-refresh`) en cada solicitud autenticada, lo cual es la implementación correcta funcionalmente pero no está optimizada para el objetivo de <50ms — una futura optimización razonable es cachear la validación del JWT localmente (con invalidación activa) en vez de repetir el round-trip. Pendiente de una sesión de medición dedicada.

- **[abierto] REG-J6 — banner de alcance RBAC Nivel 2 solo implementado en `admin/rol_editar.html`.**
  Causa raíz: es la única pantalla de Seguridad hoy donde Nivel 2 es relevante para quien la edita. Falta el mismo patrón en pantallas donde el usuario *actuante* navega bajo su propia restricción Nivel 2 — no hay ninguna todavía dentro de Seguridad; revisar cuando otros módulos (Reservas, Facturación) construyan sus propias pantallas de backoffice sobre restricciones Nivel 2 reales.

- **[abierto] REG-J8/J11 — accesibilidad y animaciones de feedback no verificadas en navegador real.**
  Causa raíz: sesión de implementación vía CLI, sin herramienta de accesibilidad ni navegador disponible. Verificar contraste WCAG AA y comportamiento de autodescartado antes de considerar el módulo listo visualmente.

- **[abierto] CHK048 — sin prueba de integración cruzada genuina entre módulos.**
  Causa raíz: Seguridad es el primer módulo implementado; no existe todavía un segundo módulo real que consuma `session_service`/`rbac_service`/`audit_service` desde fuera de Seguridad. Lo probado es la reutilización del patrón `Depends(...)` en apps FastAPI mínimas ad-hoc dentro de los propios tests. Cerrar este punto cuando Pasajeros (el candidato más natural) exista y los consuma de verdad.
