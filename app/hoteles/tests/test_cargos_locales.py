"""RF-HOT-008/RN-HOT-003 (CU-O59) — importación de `cargos_locales_destino`
desde el CSV de Holidu. Usa un CSV de prueba pequeño (no el real de 148
filas) que replica la forma real confirmada: dos tablas concatenadas,
solo la primera (City/Country/regla) se importa."""

from app.hoteles.services.cargos_locales_service import _clasificar, importar_cargos_locales, parsear_csv

_CSV_DOS_TABLAS = """TABLA 1 - Tourist Tax per City
"City","Country","Tourist Accommodation Tax Per Night"
"CiudadTestUno","PaisTestUno","$1.50 USD per person per night"
"CiudadTestDos","PaisTestDos","3.2% of room rate per night"
"CiudadTestTres","PaisTestTres","No tourist tax"
"CiudadTestCuatro","PaisTestCuatro","Accommodation over $30/night: 3.5% of room rate"

TABLA 2 - Ranking Nightly Tourist Tax (GBP)
"Ranking","City","Country","Nightly Tourist Tax (GBP)"
"1","CiudadRankingTest","PaisRankingTest","£31.78"
"""


def test_parsear_csv_solo_trae_tabla_1(tmp_path):
    ruta = tmp_path / "cargos.csv"
    ruta.write_text(_CSV_DOS_TABLAS, encoding="utf-8")

    filas = parsear_csv(str(ruta))
    assert len(filas) == 4
    ciudades = {f["ciudad"] for f in filas}
    assert ciudades == {"CiudadTestUno", "CiudadTestDos", "CiudadTestTres", "CiudadTestCuatro"}
    assert "CiudadRankingTest" not in ciudades  # Tabla 2 no se importa


def test_clasificar_monto_fijo_simple():
    tipo, monto, porcentaje = _clasificar("$1.50 USD per person per night")
    assert tipo == "monto_fijo"
    assert monto == 1.50
    assert porcentaje is None


def test_clasificar_porcentaje_simple():
    tipo, monto, porcentaje = _clasificar("3.2% of room rate per night")
    assert tipo == "porcentaje"
    assert porcentaje == 3.2
    assert monto is None


def test_clasificar_sin_impuesto():
    tipo, monto, porcentaje = _clasificar("No tourist tax")
    assert tipo is None
    assert monto is None
    assert porcentaje is None


def test_clasificar_regla_compuesta_no_inventa_valor():
    tipo, monto, porcentaje = _clasificar("Accommodation over $30/night: 3.5% of room rate")
    assert tipo is None
    assert monto is None
    assert porcentaje is None


async def test_importar_crea_registros_reales(pb, tmp_path):
    ruta = tmp_path / "cargos.csv"
    ruta.write_text(_CSV_DOS_TABLAS, encoding="utf-8")

    resultado = await importar_cargos_locales(str(ruta))
    assert resultado["procesados"] == 4
    assert resultado["creados"] == 4

    ciudad_dos = await pb.get_first("cargos_locales_destino", 'ciudad="CiudadTestDos" && pais="PaisTestDos"')
    assert ciudad_dos is not None
    assert ciudad_dos["tipo_valor_estimado"] == "porcentaje"
    assert ciudad_dos["porcentaje_estimado"] == 3.2
    assert ciudad_dos["activo"] is True

    ciudad_cuatro = await pb.get_first("cargos_locales_destino", 'ciudad="CiudadTestCuatro" && pais="PaisTestCuatro"')
    assert ciudad_cuatro["regla_texto"] == "Accommodation over $30/night: 3.5% of room rate"
    assert not ciudad_cuatro.get("tipo_valor_estimado")  # regla compuesta, sin estimado

    # segunda corrida es idempotente — actualiza, no duplica
    resultado_2 = await importar_cargos_locales(str(ruta))
    assert resultado_2["creados"] == 0
    assert resultado_2["actualizados"] == 4

    for ciudad, pais in [
        ("CiudadTestUno", "PaisTestUno"), ("CiudadTestDos", "PaisTestDos"),
        ("CiudadTestTres", "PaisTestTres"), ("CiudadTestCuatro", "PaisTestCuatro"),
    ]:
        registro = await pb.get_first("cargos_locales_destino", f'ciudad="{ciudad}" && pais="{pais}"')
        if registro:
            await pb.delete_record("cargos_locales_destino", registro["id"])
