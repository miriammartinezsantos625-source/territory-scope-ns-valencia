"""Frases "por qué" por cuenta e insights automáticos del territorio (texto generado por reglas, sin IA)."""
from __future__ import annotations

import pandas as pd

TIPO_LABEL = {
    "usmi": "USMI", "usm": "USM de adultos", "neuropediatria": "pediatría/neuropediatría hospitalaria",
    "privada_neuropediatria": "neuropediatría privada", "privada_psiquiatria": "psiquiatría privada",
    "hospital_publico": "hospital público", "hospital_privado": "hospital privado",
    "hospital_dia_sm": "hospital de día de salud mental", "hospital_psiquiatrico": "hospital psiquiátrico",
    "recurso_sm_otro": "recurso de salud mental",
    "privada_internamiento": "recurso privado de internamiento",
}
COMP_LABEL = {"potencial": "potencial", "brecha": "brecha", "relevancia": "tipo de cuenta",
              "mercado_privado": "mercado privado", "acceso": "relación existente"}


def fmt(n: float) -> str:
    """Entero con separador de miles español: 44629 → '44.629'."""
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_dec(x: float, nd: int = 1) -> str:
    """Decimal con coma: 6.8 → '6,8'."""
    s = f"{x:,.{nd}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_rec(x: float) -> str:
    """Recursos ponderados: 2.0 → '2', 1.5 → '1,5'."""
    return str(int(x)) if float(x).is_integer() else fmt_dec(x)


def _dept_name(s: str) -> str:
    return str(s).title().replace(" - ", " · ")


def why(row: pd.Series, n_dept: int = 24) -> str:
    """Frase explicativa construida a partir de los componentes y métricas del departamento."""
    dep = _dept_name(row.departamento)
    diana = row.poblacion_diana
    parts = []

    if diana == "infantil":
        g, lab, rec_lab = "infantil", "6–17 años", "recursos infanto-juveniles"
    elif diana == "adulto":
        g, lab, rec_lab = "adulto", "18–64 años", "recursos de adultos"
    else:
        g, lab, rec_lab = None, "6–64 años", "recursos"

    if g:
        pac, rec, rk = row[f"pac_{g}"], row[f"rec_{g}"], row[f"rank_brecha_{g}"]
        rec_txt = "ningún recurso" if rec == 0 else f"{fmt_rec(rec)} {rec_lab}"
        parts.append(f"{dep}: ~{fmt(pac)} pacientes estimados ({lab}) y {rec_txt} especializado(s) "
                     f"(ponderados; inferidos = 0,5)")
        if rk <= 3:
            parts.append(f"brecha en el top 3 del territorio (#{rk} de {n_dept})")
        elif rk <= 8:
            parts.append(f"brecha alta (#{rk} de {n_dept})")
        if g == "infantil" and row.n_usmi == 0:
            parts.append("sin USMI en el registro público (pendiente de verificar)")
    else:
        parts.append(f"{dep}: ~{fmt(row.pac_diana)} pacientes estimados ({lab}); "
                     f"brecha infantil #{row.rank_brecha_infantil} y adulta #{row.rank_brecha_adulto} de {n_dept}")

    # Principal impulsor del score
    aportes = {k: row[f"aporte_{k}"] for k in COMP_LABEL}
    top = max(aportes, key=aportes.get)
    parts.append(f"{TIPO_LABEL.get(row.tipo, row.tipo)}; principal impulsor: {COMP_LABEL[top]}")
    if row.ambito == "privado":
        parts.append("mercado privado")
    if row.verificado == "no":
        parts.append("cuenta pendiente de verificación")
    return f"{row.segmento}: " + "; ".join(parts) + "."


def add_why(scored: pd.DataFrame) -> pd.DataFrame:
    n = scored.dpto.nunique()
    scored = scored.copy()
    scored["por_que"] = scored.apply(why, axis=1, n_dept=n)
    return scored


def territory_insights(dept: pd.DataFrame, scored: pd.DataFrame | None = None) -> list[str]:
    """Tres insights automáticos para la caja del mapa."""
    out = []
    b = dept.sort_values("pac_por_rec_infantil", ascending=False).head(3)
    out.append("Mayor brecha infanto-juvenil (pacientes estimados 6–17 por recurso especializado): "
               + ", ".join(f"{_dept_name(r.departamento)} (~{fmt(r.pac_por_rec_infantil)})" for r in b.itertuples()) + ".")
    sin = dept[dept.n_usmi == 0]
    if len(sin):
        out.append(f"{len(sin)} de {len(dept)} departamentos no tienen USMI en el registro público; suman "
                   f"~{fmt(sin.pac_infantil.sum())} pacientes 6–17 estimados ({100 * sin.pac_infantil.sum() / dept.pac_infantil.sum():.0f} % del total). "
                   "Prioridad: verificar a qué unidad derivan.")
    ba = dept.sort_values("pac_por_rec_adulto", ascending=False).head(3)
    out.append("Mayor brecha en adultos (pacientes estimados 18–64 por recurso): "
               + ", ".join(f"{_dept_name(r.departamento)} (~{fmt(r.pac_por_rec_adulto)})" for r in ba.itertuples()) + ".")
    return out
