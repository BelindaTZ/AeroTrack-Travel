"""Lock en memoria por `reserva_id` — serializa transiciones de estado
concurrentes (pago vs. expiración automática, RN-RES-005/QP-04) dentro de
este proceso. Mismo mecanismo y misma limitación de escalabilidad que
`app.vuelos.services.cupo_service` (ver esa nota para el razonamiento
completo): correcto porque `app-travel` corre como una sola instancia.
"""

import asyncio
from collections import defaultdict

locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
