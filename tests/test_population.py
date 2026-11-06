"""Tests de la Fase 1: la población por departamento cuadra con el INE."""
import json
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"


def test_24_departamentos():
    pop = pd.read_csv(P / "poblacion_departamento.csv", dtype={"dpto": str})
    assert len(pop) == 24 and pop.dpto.is_unique
    assert (pop[["pob_6_17", "pob_18_64"]] > 0).all().all()


def test_totales_cuadran_con_ine():
    val = json.loads((P / "validacion_fase1.json").read_text())
    assert val["dif_departamentos_vs_ine"] == 0
    assert val["suma_secciones_ine"] == val["total_ccaa_ine"] == val["suma_municipios_ine"]
    assert not val["secciones_sin_asignar"]


def test_grupos_de_edad_suman_total():
    pop = pd.read_csv(P / "poblacion_departamento.csv")
    parts = pop[["pob_0_5", "pob_6_17", "pob_18_64", "pob_65_mas"]].sum(axis=1)
    assert (parts - pop.pob_total).abs().max() <= 4  # redondeo de 4 grupos


def test_municipios_repartidos_suman_100():
    md = pd.read_csv(P / "municipio_departamento.csv", dtype={"muni_ine": str})
    s = md.groupby("muni_ine").pct_poblacion_municipio.sum()
    assert ((s - 100).abs() < 0.1).all()
