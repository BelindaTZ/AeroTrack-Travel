"""Export a CSV — Fix global de la auditoría de informes simples (sesión
2026-08-01). Exporta exactamente las filas ya filtradas que se le pasen,
nunca la colección completa sin filtrar (Regla general 5 del encargo).

Uso:
    from app.shared.csv_export import csv_response

    return csv_response(
        filas,
        [("Fecha", lambda f: f["fecha"]), ("Monto", lambda f: f["monto"])],
        "reporte.csv",
    )
"""

import csv
import io
from collections.abc import Callable
from typing import Any

from fastapi.responses import Response

Columna = tuple[str, Callable[[dict], Any]]


def csv_response(filas: list[dict], columnas: list[Columna], filename: str) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([encabezado for encabezado, _ in columnas])
    for fila in filas:
        writer.writerow([extractor(fila) for _, extractor in columnas])

    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
