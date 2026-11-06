"""Tests de la Fase 2: cuentas.csv cumple las reglas del briefing."""
import re
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
REQ = ["id", "nombre", "tipo", "ambito", "poblacion_diana", "departamento", "municipio", "direccion",
       "lat", "lon", "fuente_url", "fecha_consulta", "verificado"]


def load():
    return pd.read_csv(P / "cuentas.csv", dtype={"dpto": str})


def test_columnas_y_ids():
    c = load()
    assert set(REQ) <= set(c.columns)
    assert c.id.is_unique


def test_cada_cuenta_tiene_fuente_fecha_y_verificacion():
    c = load()
    assert c.fuente_url.notna().all() and c.fecha_consulta.notna().all()
    assert set(c.verificado) <= {"si", "no"}


def test_departamentos_validos_y_coordenadas_en_la_cv():
    c = load()
    deps = pd.read_csv(P / "poblacion_departamento.csv", dtype={"dpto": str}).dpto
    assert c.dpto.isin(deps).all()
    assert c.lat.between(37.8, 40.8).all() and c.lon.between(-1.6, 0.7).all()


def test_valores_categoricos():
    c = load()
    assert set(c.ambito) <= {"publico", "privado"}
    assert set(c.poblacion_diana) <= {"infantil", "adulto", "ambas"}


def test_sin_nombres_de_medicos_en_cuentas_privadas():
    # Los hospitales públicos con nombre de figura histórica (p. ej. "Dr. Peset") son nombres institucionales.
    c = load()
    priv = c[c.ambito == "privado"].nombre
    assert not priv.str.contains(r"\b(?:DR|DRA|DOCTOR|DOCTORA)\b", flags=re.I, regex=True).any()


def test_inferencias_marcadas_como_no_verificadas():
    c = load()
    assert (c[c.tipo == "neuropediatria"].verificado == "no").all()
    assert (c[c.fuente_url.str.contains("openstreetmap")].verificado == "no").all()


def test_ids_estables_derivados_de_la_fuente():
    c = load()
    suf = c.id.str.split("-", n=1).str[1]
    src = c.src_id.str.replace("-np", "", regex=False)
    assert (suf.str[0].map({"R": "reg", "S": "svs", "O": "osm"}) == src.str.split("-").str[0]).all()
    assert c.id.str.match(r"^[A-Z]{2}-[RSO][A-Z]?\d+$").all()


def test_sin_consultas_individuales_privadas():
    c = load()
    assert not c[c.ambito == "privado"].nombre.str.contains("CONSULTA", case=False).any()
