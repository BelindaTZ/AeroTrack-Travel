# Flight API (skdeveloper, host `flight-api18.p.rapidapi.com`) — hallazgos

> Doc de trabajo, no pulido — para ir guardando lo que se descubra de esta API mientras
> se arma la BD, sin gastar de más la cuota (**solo 5 requests/mes en total**, plan
> gratis). Cuando se sepa algo definitivo se traslada a `docs/apis-reference.md`.

## Estado: 1/5 requests usadas, resultado inconcluso pero muy revelador

**Prueba 1 (2026-07-16):** `GET /industry/faa-ladd/N833MH/status`
- Headers: `x-rapidapi-key` + `x-rapidapi-host: flight-api18.p.rapidapi.com` (estándar)
- **Resultado: `403 Forbidden`, cuerpo = página de bloqueo de Cloudflare**, no JSON.
- El texto del bloqueo dice explícitamente: *"You are unable to access **aerodatabox.com**"*.
- Headers de cuota tras esta llamada: `X-RateLimit-Requests-Limit: 5`, `X-RateLimit-Requests-Remaining: 4`.

### Por qué esto es importante

El mensaje de Cloudflare **nombra el dominio real detrás del wrapper: `aerodatabox.com`** — el mismo backend que la AeroDataBox oficial (`aerodatabox.p.rapidapi.com`, ya confirmada funcionando en `docs/apis-reference.md` sección 2). Comparando el catálogo de rutas que diste (`searchBy` con `number/callsign/reg/icao24`, `/industry/faa-ladd/{id}/status`, `/airports/{codeType}/{code}/delays/{dateLocal}/{dateToLocal}`, `/airports/{codeType}/{code}/stats/routes/daily/{dateLocal}`) contra las rutas ya probadas de AeroDataBox: son **estructuralmente idénticas**, mismos nombres de parámetro y mismos valores de enum.

**Conclusión provisional (con 1 sola llamada, hay que confirmarla):** "Flight API" de skdeveloper probablemente **no es una fuente de datos distinta** — es un revendedor de RapidAPI que empaqueta el mismo backend de AeroDataBox bajo otro listado/precio. Si se confirma, no aporta datos históricos que la AeroDataBox oficial no tenga ya, y su cuota (5/mes) es muchísimo peor que la oficial (600/mes).

### Por qué el bloqueo probablemente es temporal, no del listado

El origen (`aerodatabox.com`) está bloqueando vía Cloudflare — muy probablemente porque hoy mismo se le hicieron ~58 llamadas de prueba a la AeroDataBox oficial desde esta misma sesión/IP, y el WAF del proveedor puede haber marcado el tráfico como sospechoso temporalmente. No es necesariamente que la key de este nuevo listado esté mal — es plausible que cualquier llamada a `aerodatabox.com` (por cualquiera de los dos listados de RapidAPI) esté afectada ahora mismo.

## Recomendación

1. **No gastar las 4 requests restantes hoy** — esperar un tiempo (horas, no minutos — los bloqueos de Cloudflare por patrón de tráfico suelen tardar en limpiarse) y reintentar UNA vez con un endpoint distinto para confirmar si el bloqueo ya se levantó.
2. Si se confirma que es el mismo backend que AeroDataBox: **descartar esta API como fuente independiente** en `fuentes_datos_externas` — no vale la pena modelarla como fuente separada de `risk_score_fuente = estimado_intl` (eso ya lo cubre la AeroDataBox oficial, con mucha más cuota).
3. Si en el próximo intento SÍ devuelve datos reales distintos (ej. rango histórico más largo que los 14 días típicos de AeroDataBox, dado que este catálogo menciona rangos de "7-30 días según el plan"), documentarlo aquí con el JSON real antes de decidir si conviene integrarla — a esa cuota (5/mes), como mucho serviría para una validación puntual manual, nunca para un sync periódico automático.

## Próxima prueba sugerida (cuando se reintente)

Usar el endpoint con más probabilidad de traer un dato genuinamente distinto a lo ya visto, no repetir el mismo:
- `GET /airports/{codeType}/{code}/stats/routes/daily/{dateLocal}` con una fecha pasada real (ej. hace 30-60 días) — si trae datos reales de una fecha vieja, sería evidencia de que sí tiene retención histórica más profunda que la AeroDataBox oficial (que es más bien tiempo real/reciente).
