"""Modelo de priorización explicable.

score = Σ peso_i × componente_i   (componentes 0–100, pesos normalizados a suma 1)

Componentes por cuenta
  potencial        pacientes TDAH estimados en su departamento para su población diana
  brecha           pacientes estimados por recurso especializado del departamento (población diana)
  relevancia       peso del tipo de cuenta (config) × factor si no está verificada
  mercado_privado  100 si la cuenta es privada, 0 si es pública
  acceso           100 si hay relación existente (capa privada); sin capa → modo demo, peso 0

Normalización: potencial y brecha se escalan a 0–100 dividiendo por el máximo del territorio DENTRO de
cada grupo de edad (escala proporcional, no min–max: 0 = "cero pacientes"/"sin brecha"). Las cuentas con
población diana "ambas" reciben la media de su valor infantil y adulto.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

COMPONENTS = ["potencial", "brecha", "relevancia", "mercado_privado", "acceso"]
GROUPS = ["infantil", "adulto"]


def prevalence(cfg: dict, escenario: str = "base", override: dict | None = None) -> dict:
    """Prevalencia (proporción) por grupo. `override` permite fijar % desde un slider."""
    out = {g: cfg["prevalencia"][g][escenario] / 100 for g in GROUPS}
    if override:
        out.update({g: v / 100 for g, v in override.items() if v is not None})
    return out


def department_metrics(pop: pd.DataFrame, accounts: pd.DataFrame, cfg: dict,
                       prev: dict | None = None) -> pd.DataFrame:
    """Pacientes estimados (bajo/base/alto y escenario elegido), recursos y brecha por departamento."""
    prev = prev or prevalence(cfg)
    d = pop[["dpto", "departamento", "pob_total"]].copy()
    for g in GROUPS:
        col = cfg["grupos"][g]["columna"]
        d[f"pob_{g}"] = pop[col]
        for esc in ["bajo", "base", "alto"]:
            d[f"pac_{g}_{esc}"] = (pop[col] * cfg["prevalencia"][g][esc] / 100).round()
        d[f"pac_{g}"] = (pop[col] * prev[g]).round()

        d[f"rec_{g}"] = d.dpto.map(resources_by_department(accounts, cfg, g)).fillna(0.0)
        d[f"pac_por_rec_{g}"] = d[f"pac_{g}"] / (d[f"rec_{g}"] + cfg.get("suavizado_recursos", 1))
        d[f"rank_brecha_{g}"] = d[f"pac_por_rec_{g}"].rank(ascending=False, method="min").astype(int)

    d["pac_total"] = d.pac_infantil + d.pac_adulto
    d["n_usmi"] = d.dpto.map(accounts[accounts.tipo == "usmi"].groupby("dpto").size()).fillna(0).astype(int)
    d["n_usm"] = d.dpto.map(accounts[accounts.tipo == "usm"].groupby("dpto").size()).fillna(0).astype(int)
    return d


def resources_by_department(accounts: pd.DataFrame, cfg: dict, g: str) -> pd.Series:
    """Recursos especializados ponderados por departamento para el grupo g.

    · diana == g cuenta; diana "ambas" cuenta en adulto y, en infantil, solo si su tipo está en
      `ambas_cuentan_en_infantil`.
    · Recursos no verificados pesan `peso_recurso_no_verificado` y, como máximo,
      `max_inferidos_por_tipo_y_departamento` por tipo y departamento.
    """
    tipos = cfg["recursos_especializados"][g]
    a = accounts[accounts.tipo.isin(tipos)]
    if g == "infantil":
        ok_ambas = set(cfg.get("ambas_cuentan_en_infantil", []))
        a = a[(a.poblacion_diana == "infantil") | ((a.poblacion_diana == "ambas") & a.tipo.isin(ok_ambas))]
    else:
        a = a[a.poblacion_diana.isin([g, "ambas"])]
    ver = a[a.verificado == "si"].groupby("dpto").size().astype(float)
    nov = a[a.verificado != "si"].groupby(["dpto", "tipo"]).size()
    nov = nov.clip(upper=cfg.get("max_inferidos_por_tipo_y_departamento", 99)).groupby("dpto").sum()
    nov = nov.astype(float) * cfg.get("peso_recurso_no_verificado", 1.0)
    return ver.add(nov, fill_value=0.0)


def _scale(s: pd.Series) -> pd.Series:
    m = s.max()
    return (100 * s / m).fillna(0) if m and m > 0 else s * 0


def normalize_weights(w: dict, has_access_layer: bool) -> dict:
    w = {k: float(w.get(k, 0)) for k in COMPONENTS}
    if not has_access_layer:
        w["acceso"] = 0.0
    tot = sum(w.values())
    if tot <= 0:
        raise ValueError("Al menos un peso debe ser > 0")
    return {k: v / tot for k, v in w.items()}


def score_accounts(accounts: pd.DataFrame, dept: pd.DataFrame, cfg: dict, weights: dict | None = None,
                   relationships: pd.DataFrame | None = None) -> pd.DataFrame:
    w = normalize_weights(weights or cfg["pesos"], relationships is not None)
    a = accounts.merge(dept, on=["dpto"], how="left", suffixes=("", "_dpto"))

    inf, adu = a.poblacion_diana.isin(["infantil", "ambas"]), a.poblacion_diana.isin(["adulto", "ambas"])
    a["pac_diana"] = np.where(inf, a.pac_infantil, 0) + np.where(adu, a.pac_adulto, 0)
    # Escala DENTRO de cada grupo (infantil vs. máximo infantil; adulto vs. máximo adulto) para que
    # las cuentas "ambas" no acumulen el doble de potencial. "ambas" = media de los dos grupos.
    pot = {g: _scale(dept.set_index("dpto")[f"pac_{g}"]) for g in GROUPS}
    bre = {g: _scale(dept.set_index("dpto")[f"pac_por_rec_{g}"]) for g in GROUPS}
    n_g = inf.astype(int) + adu.astype(int)
    a["c_potencial"] = (np.where(inf, a.dpto.map(pot["infantil"]), 0) + np.where(adu, a.dpto.map(pot["adulto"]), 0)) / n_g
    a["c_brecha"] = (np.where(inf, a.dpto.map(bre["infantil"]), 0) + np.where(adu, a.dpto.map(bre["adulto"]), 0)) / n_g
    rel = a.tipo.map(cfg["relevancia_tipo"]).fillna(0)
    a["c_relevancia"] = rel * np.where(a.verificado == "si", 1.0, cfg.get("factor_no_verificado", 1.0))
    a["c_mercado_privado"] = np.where(a.ambito == "privado", 100.0, 0.0)
    if relationships is not None:
        rel_ids = set(relationships.loc[relationships.relacion == "si", "id_cuenta"])
        a["c_acceso"] = np.where(a.id.isin(rel_ids), 100.0, 0.0)
    else:
        a["c_acceso"] = 0.0

    for k in COMPONENTS:
        a[f"aporte_{k}"] = w[k] * a[f"c_{k}"]
    a["score"] = a[[f"aporte_{k}" for k in COMPONENTS]].sum(axis=1).round(1)
    a = segment(a, cfg)
    a.attrs["pesos"] = w
    a.attrs["modo_demo"] = relationships is None
    return a


def segment(a: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """A = top 20 %, B = siguiente 30 %, C = resto, por UMBRAL de score.

    Los empates en el umbral se quedan juntos en el segmento superior (por eso A puede superar
    ligeramente el 20 %): dos cuentas con el mismo score nunca caen en segmentos distintos.
    """
    a = a.sort_values(["score", "id"], ascending=[False, True]).reset_index(drop=True)
    n = len(a)
    a["rank"] = a.score.rank(ascending=False, method="min").astype(int)
    n_a = max(1, int(round(n * cfg["segmentos"]["A"])))
    n_ab = max(n_a, int(round(n * (cfg["segmentos"]["A"] + cfg["segmentos"]["B"]))))
    thr_a = a.score.iloc[n_a - 1]
    thr_b = a.score.iloc[n_ab - 1]
    a["segmento"] = np.where(a.score >= thr_a, "A", np.where(a.score >= thr_b, "B", "C"))
    return a
