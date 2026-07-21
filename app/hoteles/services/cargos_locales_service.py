"""RF-HOT-008/RN-HOT-003 (CU-O59) — importa `cargos_locales_destino` desde
`fuentes_extra/holidu_tourist_tax_por_ciudad.csv` (snapshot de Holidu,
~100 ciudades). Disparo manual/infrecuente (los datos no cambian a
diario) — no es una API con sincronización periódica como
`hoteles_catalogo`, ver `dags/dag_importar_cargos_locales.py`.

El CSV real trae DOS tablas concatenadas (confirmado al inspeccionar el
archivo): "TABLA 1 - Tourist Tax per City" (City/Country/regla de texto
libre — la que necesita `cargos_locales_destino`) y "TABLA 2 - Ranking
Nightly Tourist Tax (GBP)" (un ranking derivado, sin regla completa, no
mapea a este esquema). Solo se importa la Tabla 1.

`regla_texto` es siempre el dato autoritativo (RN-HOT-003); el estimado
rápido (`tipo_valor_estimado`/`monto_estimado`/`porcentaje_estimado`) solo
se completa cuando el texto es un patrón simple de un solo valor —
reglas compuestas ("Accommodation over $30/night: 3.5%...") se dejan sin
estimado, nunca se inventa un número para una regla condicional."""

import csv
import re

from app.hoteles.repositories.hoteles_repo import HotelesRepository

_PATRON_PORCENTAJE_SIMPLE = re.compile(r"^(\d+(?:\.\d+)?)\s*%\s+of\s+.+$", re.IGNORECASE)
_PATRON_MONTO_SIMPLE = re.compile(r"^[\$€£]\s?(\d+(?:\.\d+)?)\s*(?:USD|EUR|GBP)?\s+per\s+.+$", re.IGNORECASE)
_PALABRAS_COMPUESTAS = ("over", "under", "up to", "depending", "varies", "plus", "additional", ";", " if ")


def parsear_csv(ruta: str) -> list[dict]:
    """Solo la Tabla 1 (City/Country/regla de texto) — se detiene al
    llegar a la línea en blanco que la separa de la Tabla 2."""
    filas: list[dict] = []
    with open(ruta, encoding="utf-8") as f:
        en_tabla_1 = False
        for row in csv.reader(f):
            if not row:
                if en_tabla_1:
                    break
                continue
            if row[0].startswith("TABLA"):
                if en_tabla_1:
                    break
                continue
            if row == ["City", "Country", "Tourist Accommodation Tax Per Night"]:
                en_tabla_1 = True
                continue
            if en_tabla_1 and len(row) == 3:
                filas.append({"ciudad": row[0], "pais": row[1], "regla_texto": row[2]})
    return filas


def _clasificar(regla_texto: str) -> tuple[str | None, float | None, float | None]:
    """(tipo_valor_estimado, monto_estimado, porcentaje_estimado) — los
    tres `None` si la regla es "No tourist tax" o compuesta (nada que
    estimar sin inventar un número)."""
    texto = regla_texto.strip()
    if texto.lower() == "no tourist tax":
        return None, None, None
    if any(palabra in texto.lower() for palabra in _PALABRAS_COMPUESTAS):
        return None, None, None

    m = _PATRON_PORCENTAJE_SIMPLE.match(texto)
    if m:
        return "porcentaje", None, float(m.group(1))

    m = _PATRON_MONTO_SIMPLE.match(texto)
    if m:
        return "monto_fijo", float(m.group(1)), None

    return None, None, None


async def importar_cargos_locales(ruta: str) -> dict:
    repo = HotelesRepository()
    filas = parsear_csv(ruta)
    creados = actualizados = 0

    for fila in filas:
        tipo_valor, monto, porcentaje = _clasificar(fila["regla_texto"])
        data = {
            "ciudad": fila["ciudad"],
            "pais": fila["pais"],
            "tipo_cargo": "alojamiento",
            "regla_texto": fila["regla_texto"],
            "fuente": "holidu_csv_2026",
            "activo": True,
        }
        if tipo_valor:
            data["tipo_valor_estimado"] = tipo_valor
        if monto is not None:
            data["monto_estimado"] = monto
        if porcentaje is not None:
            data["porcentaje_estimado"] = porcentaje

        existente = await repo.cargo_local_por_ciudad_pais(fila["ciudad"], fila["pais"])
        if existente:
            await repo.actualizar_cargo_local(existente["id"], data)
            actualizados += 1
        else:
            await repo.crear_cargo_local(data)
            creados += 1

    resumen = {"procesados": len(filas), "creados": creados, "actualizados": actualizados}
    print(f"[CARGOS_LOCALES] {resumen}")
    return resumen
