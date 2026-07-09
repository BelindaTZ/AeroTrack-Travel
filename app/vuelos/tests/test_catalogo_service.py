"""RF-VUE-003 (CU-O19/O30) — verificación del catálogo ya generado por el
DAG de Airflow existente (`dags/dag_generar_catalogo_vuelos.py`). No se
reescribe la generación aquí — se importa la función real (idempotente) y
se verifican sus invariantes contra datos reales de `pocketbase-travel`.
"""

import datetime
import sys
from pathlib import Path

DAGS_DIR = str(Path(__file__).resolve().parents[3] / "dags")
if DAGS_DIR not in sys.path:
    sys.path.insert(0, DAGS_DIR)


# ── RN-SEG-001 / RN-VUE-001 (CHK009) ──────────────────────────────────────

async def test_vuelos_generados_por_sistema_nacen_programados(pb):
    import catalogo_vuelos_tasks  # noqa: E402  (requiere el sys.path de arriba)

    creados = catalogo_vuelos_tasks.generar_vuelos_programables()
    assert creados >= 0  # idempotente: puede no crear nada si ya está cubierto

    hoy_iso = datetime.date.today().strftime("%Y-%m-%d")
    resultado = await pb.list_records(
        "vuelos_catalogo",
        {"filter": f'generado_por="sistema" && fecha_salida>="{hoy_iso}"', "perPage": 200},
    )
    vuelos_futuros = resultado["items"]
    assert len(vuelos_futuros) > 0
    for vuelo in vuelos_futuros:
        assert vuelo["estado"] == "programado", (
            f"{vuelo['numero_vuelo']} ({vuelo['fecha_salida']}) generado por sistema "
            f"pero no nació en 'programado': {vuelo['estado']}"
        )


# ── RN-VUE-002 (CHK010) ───────────────────────────────────────────────────

async def test_cada_vuelo_tiene_tres_tarifas_independientes(pb):
    algun_vuelo = await pb.get_first("vuelos_catalogo", 'generado_por="sistema"')
    assert algun_vuelo is not None

    tarifas = await pb.list_records(
        "tarifas_vuelo", {"filter": f'vuelo_id="{algun_vuelo["id"]}"', "perPage": 10}
    )
    items = tarifas["items"]
    assert len(items) == 3

    niveles_distintos = {t["nivel_tarifa_id"] for t in items}
    assert len(niveles_distintos) == 3  # un nivel por tarifa, sin duplicados

    precios = [t["precio_final"] for t in items]
    assert len(set(precios)) >= 2  # Standard/Flex difieren entre sí (Light puede igualar precio_base)

    cupos = [t["cupos_disponibles"] for t in items]
    assert len(set(cupos)) >= 2  # cada nivel tiene su propio cupo, no comparten un único valor


# ── RNF-VUE-002 / RN-VUE-003 (CHK011, CHK016) ─────────────────────────────

def test_generacion_no_tiene_ninguna_llamada_de_escritura_a_minio():
    dags_dir = Path(DAGS_DIR)
    fuentes = [
        (dags_dir / "catalogo_vuelos_tasks.py").read_text(encoding="utf-8"),
        (dags_dir / "minio_dims_reader.py").read_text(encoding="utf-8"),
    ]
    llamadas_de_escritura = ["put_object", "fput_object", "remove_object", "copy_object", "compose_object"]
    for fuente in fuentes:
        for llamada in llamadas_de_escritura:
            assert llamada not in fuente
