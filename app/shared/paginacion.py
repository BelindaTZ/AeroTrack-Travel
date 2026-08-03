"""Paginación reutilizable para listados de WorkPanels — evita recalcular
slice/total_páginas en cada router. Trabaja en memoria sobre una lista ya
traída del repositorio (PocketBase/MinIO en este proyecto siempre devuelven
como máximo unos cientos de registros por colección, ver `perPage`/
`listar_todos` en los repos), no reemplaza paginación a nivel de query.

Uso típico en un router:

    from app.shared.paginacion import paginar

    @router.get("/backoffice/algo")
    async def listar(request: Request, page: int = 1, ...):
        items = await repo.listar_todos()  # ya filtrado
        contexto["pagina"] = paginar(items, page)
        return templates.TemplateResponse(request, "...", contexto)

Y en el template, después de la tabla:

    {% include "_paginacion.html" %}
"""

from dataclasses import dataclass
from typing import Generic, Sequence, TypeVar

T = TypeVar("T")

TAMANO_PAGINA_DEFAULT = 25


@dataclass
class Pagina(Generic[T]):
    items: Sequence[T]
    pagina: int
    total_paginas: int
    total_items: int
    tamano_pagina: int

    @property
    def hay_anterior(self) -> bool:
        return self.pagina > 1

    @property
    def hay_siguiente(self) -> bool:
        return self.pagina < self.total_paginas

    @property
    def paginas_visibles(self) -> list[int]:
        """Ventana de hasta 5 números alrededor de la página actual —
        evita listar cientos de números en colecciones grandes."""
        inicio = max(1, self.pagina - 2)
        fin = min(self.total_paginas, self.pagina + 2)
        return list(range(inicio, fin + 1))


def paginar(items: Sequence[T], pagina: int = 1, tamano_pagina: int = TAMANO_PAGINA_DEFAULT) -> Pagina[T]:
    total_items = len(items)
    total_paginas = max(1, -(-total_items // tamano_pagina))  # ceil sin importar float
    pagina = max(1, min(pagina, total_paginas))
    inicio = (pagina - 1) * tamano_pagina
    return Pagina(
        items=items[inicio : inicio + tamano_pagina],
        pagina=pagina,
        total_paginas=total_paginas,
        total_items=total_items,
        tamano_pagina=tamano_pagina,
    )
