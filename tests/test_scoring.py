"""Tests del modelo de priorización (Fase 3)."""
import pandas as pd
import pytest

from src.insights import add_why, territory_insights
from src.load import load_accounts, load_config, load_population
from src.scoring import (COMPONENTS, department_metrics, normalize_weights, prevalence,
                         score_accounts)


@pytest.fixture(scope="module")
def base():
    cfg = load_config("tdah")
    acc = load_accounts()
    dept = department_metrics(load_population(), acc, cfg)
    return cfg, acc, dept


def test_prevalencias_ordenadas_y_rango_de_pacientes(base):
    cfg, _, dept = base
    for g in ["infantil", "adulto"]:
        p = cfg["prevalencia"][g]
        assert p["bajo"] < p["base"] < p["alto"]
        assert (dept[f"pac_{g}_bajo"] <= dept[f"pac_{g}_base"]).all()
        assert (dept[f"pac_{g}_base"] <= dept[f"pac_{g}_alto"]).all()


def test_pacientes_base_igual_poblacion_por_prevalencia(base):
    cfg, _, dept = base
    pop = load_population()
    esperado = (pop.pob_6_17 * cfg["prevalencia"]["infantil"]["base"] / 100).round()
    assert (dept.pac_infantil.values == esperado.values).all()


def test_pesos_normalizados_y_modo_demo():
    w = normalize_weights({"potencial": 2, "brecha": 1, "relevancia": 1, "mercado_privado": 0, "acceso": 5}, False)
    assert w["acceso"] == 0 and abs(sum(w.values()) - 1) < 1e-9
    w2 = normalize_weights({"potencial": 1, "acceso": 1}, True)
    assert w2["acceso"] == 0.5
    with pytest.raises(ValueError):
        normalize_weights({k: 0 for k in COMPONENTS}, True)


def test_componentes_y_score_en_0_100(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg)
    for k in COMPONENTS:
        assert s[f"c_{k}"].between(0, 100).all(), k
    assert s.score.between(0, 100).all() and s.score.notna().all()
    assert len(s) == len(acc) and s.id.is_unique


def test_score_es_suma_ponderada(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg)
    w = s.attrs["pesos"]
    recomputed = sum(w[k] * s[f"c_{k}"] for k in COMPONENTS)
    assert (recomputed.round(1) - s.score).abs().max() <= 0.051


def test_segmentos_20_30_50_por_umbral(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg)
    n = len(s)
    vc = s.segmento.value_counts()
    n_a, n_ab = round(0.2 * n), round(0.5 * n)
    assert vc["A"] >= n_a and vc["A"] + vc["B"] >= n_ab
    # El exceso solo puede venir de empates en el umbral
    srt = s.sort_values("score", ascending=False).score.reset_index(drop=True)
    assert (s[s.segmento == "A"].score >= srt[n_a - 1]).all()
    assert vc["A"] == (s.score >= srt[n_a - 1]).sum()
    # Orden: A >= B >= C
    assert s[s.segmento == "A"].score.min() > s[s.segmento == "B"].score.max()
    assert s[s.segmento == "B"].score.min() > s[s.segmento == "C"].score.max()


def test_empates_comparten_segmento(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg)
    assert (s.groupby("score").segmento.nunique() == 1).all()
    assert (s.groupby("score")["rank"].nunique() == 1).all()


def test_solo_brecha_ordena_por_brecha(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg, weights={"brecha": 1})
    assert s.iloc[0].c_brecha == s.c_brecha.max()


def test_capa_de_relacion_sube_el_score(base):
    cfg, acc, dept = base
    sin = score_accounts(acc, dept, cfg).set_index("id")
    target = sin.sort_values("score").index[0]  # la última del ranking
    rel = pd.DataFrame({"id_cuenta": [target], "relacion": ["si"]})
    con = score_accounts(acc, dept, cfg, relationships=rel).set_index("id")
    assert con.attrs["modo_demo"] is False and sin.attrs["modo_demo"] is True
    assert con.loc[target, "c_acceso"] == 100
    assert con.loc[target, "rank"] < sin.loc[target, "rank"]


def test_cuentas_infantiles_dependen_de_poblacion_infantil(base):
    cfg, acc, dept = base
    s = score_accounts(acc, dept, cfg)
    usmi = s[s.tipo == "usmi"]
    top = usmi.sort_values("c_potencial").iloc[-1]
    assert top.dpto == dept.sort_values("pac_infantil").iloc[-1].dpto


def test_slider_de_prevalencia(base):
    cfg, acc, _ = base
    prev = prevalence(cfg, "base", override={"infantil": 10.0})
    d = department_metrics(load_population(), acc, cfg, prev)
    assert d.pac_infantil.sum() > d.pac_infantil_alto.sum()


def test_frases_por_que_e_insights(base):
    cfg, acc, dept = base
    s = add_why(score_accounts(acc, dept, cfg))
    assert s.por_que.notna().all()
    assert (s.por_que.str[0] == s.segmento).all()
    ins = territory_insights(dept)
    assert len(ins) == 3 and all(isinstance(t, str) and t for t in ins)


def test_recursos_inferidos_ponderados_y_ambas_fuera_de_infantil(base):
    cfg, acc, dept = base
    from src.scoring import resources_by_department
    r = resources_by_department(acc, cfg, "infantil")
    # Ninguna privada "ambas" cuenta en infantil y los inferidos pesan 0,5 como máximo una vez por tipo
    usmi = acc[(acc.tipo == "usmi")].groupby("dpto").size()
    for d, val in r.items():
        assert val <= usmi.get(d, 0) + acc[(acc.dpto == d) & (acc.tipo == "privada_neuropediatria")].shape[0] + 0.5 + 1e-9


def test_capa_relacion_robusta():
    import pandas as pd
    from src.load import clean_relationships
    r = clean_relationships(pd.DataFrame({"id_cuenta": ["ui-r1 ", "UI-R1", "X"], "relacion": ["no", "Sí", "quizá"]}))
    assert r.set_index("id_cuenta").relacion.to_dict() == {"UI-R1": "si"}
    assert r.attrs["ids_duplicados"] == 1 and r.attrs["valores_no_reconocidos"] == 1
