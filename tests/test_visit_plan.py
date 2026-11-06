"""Tests del plan de visitas (Fase 4)."""
import pytest

from src.load import load_accounts, load_config, load_departments_geo, load_population
from src.scoring import department_metrics, score_accounts
from src.visit_plan import build_plan, coverage, department_route


@pytest.fixture(scope="module")
def scored():
    cfg = load_config()
    acc = load_accounts()
    return score_accounts(acc, department_metrics(load_population(), acc, cfg), cfg)


@pytest.fixture(scope="module")
def route():
    return department_route(load_departments_geo(), start="07")


def test_ruta_incluye_24_departamentos(route):
    assert len(route) == 24 and len(set(route)) == 24 and route[0] == "07"


def test_frecuencias_por_segmento(scored, route):
    plan, _, no_cub = build_plan(scored, route, visitas_dia=8, dias_mes=20, meses=6)
    assert no_cub.empty
    v = plan.groupby("id").size()
    seg = scored.set_index("id").segmento
    assert (v[seg[seg == "A"].index] == 6).all()
    assert (v[seg[seg == "B"].index] == 3).all()
    assert (v[seg[seg == "C"].index] == 2).all()


def test_capacidad_y_dias(scored, route):
    plan, res, no_cub = build_plan(scored, route, visitas_dia=5, dias_mes=10, meses=3)
    assert (res.visitas_planificadas <= 50).all()
    assert plan.groupby(["mes", "dia"]).size().max() <= 5
    assert not no_cub.empty
    # Lo que se queda fuera nunca es A si caben todas las A
    if (res.A <= 50).all():
        assert (no_cub.segmento != "A").all()


def test_visitas_agrupadas_por_departamento(scored, route):
    plan, _, _ = build_plan(scored, route, meses=1)
    seq = plan.sort_values(["dia", "orden_en_dia"]).dpto.tolist()
    cambios = sum(1 for a, b in zip(seq, seq[1:]) if a != b)
    assert cambios == plan.dpto.nunique() - 1  # cada departamento aparece en un único bloque


def test_cobertura(scored, route):
    plan, _, _ = build_plan(scored, route, visitas_dia=8, dias_mes=20, meses=3)
    cov = coverage(plan, scored)
    assert (cov.cuentas == cov.cuentas_visitadas).all()
