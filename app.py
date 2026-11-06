"""Territory Scope NS Valencia · inteligencia territorial con datos públicos (TDAH)."""
from __future__ import annotations

import html
import json

import folium
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

from src import content as C
from src.insights import add_why, fmt, fmt_dec, territory_insights
from src.load import (PROCESSED, ROOT, available_areas, load_accounts, load_config, load_departments_geo,
                      load_population, load_relationships)
from src.scoring import COMPONENTS, department_metrics, prevalence, score_accounts
from src.visit_plan import build_plan, coverage, department_route

st.set_page_config(page_title="Territory Scope NS Valencia", layout="wide")

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
:root { --navy:#0B2545; --blue:#0F4C81; --blue2:#1D6FB8; --teal:#13807A; --teal2:#21A99F; --slate:#5B6B7F;
        --line:#E3E8EF; --bg:#F5F7FB; --card:#FFFFFF; --shadow:0 1px 2px rgba(16,24,40,.05), 0 6px 18px rgba(16,24,40,.06); }
html, body, [class*="css"], .stMarkdown, .stText, button, input, select, textarea { font-family: "Inter", "Helvetica Neue", Arial, sans-serif !important; }
.stApp { background: var(--bg); }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.2rem; max-width: 1440px; }
h1, h2, h3, h4 { color: var(--navy); font-weight: 700; letter-spacing: -0.015em; }
h3 { font-size: 1.08rem; margin-top: 1.4rem; }

/* Hero */
.ts-hero { position: relative; overflow: hidden; border-radius: 18px; padding: 1.6rem 1.9rem 1.5rem 1.9rem; margin-bottom: 1.1rem;
  background: radial-gradient(1200px 300px at 85% -40%, rgba(33,169,159,.35), transparent 60%),
              linear-gradient(120deg, #0B2545 0%, #0F3B66 55%, #0F4C81 100%);
  box-shadow: 0 10px 30px rgba(11,37,69,.25); }
.ts-hero:after { content:""; position:absolute; right:-60px; top:-60px; width:260px; height:260px; border-radius:50%;
  border: 1px solid rgba(255,255,255,.12); box-shadow: 0 0 0 40px rgba(255,255,255,.03), 0 0 0 80px rgba(255,255,255,.02); }
.ts-eyebrow { color: #8FE3DA; font-size: .72rem; font-weight: 700; letter-spacing: .18em; text-transform: uppercase; }
.ts-title { color: #fff; font-size: 2.1rem; font-weight: 800; margin: .2rem 0 .35rem 0; letter-spacing: -0.02em; }
.ts-sub { color: rgba(255,255,255,.78); font-size: .92rem; max-width: 900px; line-height: 1.5; }
.ts-chips { margin-top: .9rem; display:flex; flex-wrap:wrap; gap:.45rem; }
.ts-chip { font-size: .72rem; font-weight: 600; color: #fff; background: rgba(255,255,255,.10);
  border: 1px solid rgba(255,255,255,.18); padding: .25rem .65rem; border-radius: 999px; backdrop-filter: blur(4px); }

/* KPI */
.ts-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:.9rem; margin:.2rem 0 1.3rem 0; }
.ts-kpi { position:relative; background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1rem 1.1rem .9rem 1.1rem;
  box-shadow: var(--shadow); cursor:help; transition: transform .15s ease, box-shadow .15s ease; overflow:hidden; }
.ts-kpi:before { content:""; position:absolute; left:0; top:0; right:0; height:3px; background: linear-gradient(90deg, var(--blue), var(--teal2)); }
.ts-kpi:hover { transform: translateY(-2px); box-shadow: 0 10px 24px rgba(16,24,40,.10); }
.ts-kpi-l { color:var(--slate); font-size:.7rem; font-weight:700; text-transform:uppercase; letter-spacing:.08em; }
.ts-kpi-v { color:var(--navy); font-size:1.85rem; font-weight:800; margin:.25rem 0 .2rem 0; letter-spacing:-0.02em; }
.ts-kpi-s { color:var(--slate); font-size:.74rem; line-height:1.45; }
.ts-tag { display:inline-block; font-size:.58rem; font-weight:700; padding:2px 7px; border-radius:999px; letter-spacing:.06em;
  text-transform:uppercase; margin-right:6px; vertical-align:1px; }
.ts-dato { background:#E7F0FA; color:#0F4C81; }
.ts-estimación { background:#FFF4E0; color:#8A5A00; }

/* Tabs: píldoras (Streamlit ≥1.5x usa role=tablist / data-testid=stTab) */
div[role="tablist"] { gap:.35rem; background: var(--card); padding:.35rem; border-radius:12px; border:1px solid var(--line) !important;
  box-shadow: var(--shadow); width: fit-content; max-width: 100%; }
div[role="tablist"] > div[data-testid="stTab"] { border-radius:9px; padding:.5rem 1.05rem; transition: background .15s ease;
  border-bottom: none !important; }
div[role="tablist"] > div[data-testid="stTab"] p { font-size:.88rem; font-weight:600; color:var(--slate); margin:0; }
div[role="tablist"] > div[data-testid="stTab"]:hover { background: #EEF3F9; }
div[role="tablist"] > div[data-testid="stTab"][aria-selected="true"] { background: var(--navy); }
div[role="tablist"] > div[data-testid="stTab"][aria-selected="true"] p { color:#fff !important; }
div[role="tablist"] > div[data-testid="stTab"]::after, div[role="tablist"]::after { display:none !important; }

/* Tarjetas y tablas */
div[data-testid="stVerticalBlockBorderWrapper"] { background: var(--card); border-radius:14px !important; border-color: var(--line) !important;
  box-shadow: var(--shadow); }
div[data-testid="stDataFrame"], div[data-testid="stTable"], iframe[title="streamlit_folium.st_folium"] {
  border-radius:14px; overflow:hidden; box-shadow: var(--shadow); border:1px solid var(--line); }
.stDownloadButton button, .stButton button { border-radius:10px; font-weight:600; border:1px solid var(--navy);
  background: var(--navy); color:#fff; }
.stDownloadButton button:hover, .stButton button:hover { background: var(--blue); border-color: var(--blue); color:#fff; }

/* Sidebar */
section[data-testid="stSidebar"] { background: #fff; border-right: 1px solid var(--line); }
section[data-testid="stSidebar"] h2 { font-size: .72rem; text-transform: uppercase; letter-spacing: .16em; color: var(--slate); font-weight:700; }
section[data-testid="stSidebar"] h3 { font-size: .92rem; margin-top: 1.1rem; padding-top: .9rem; border-top: 1px solid var(--line); }

/* Insights y etiquetas */
.ts-insight { background: linear-gradient(180deg, #FFFFFF, #F8FBFD); border:1px solid var(--line); border-left: 4px solid var(--teal2);
  padding: .7rem .85rem; margin-bottom: .65rem; font-size: .84rem; color: #1F2A37; border-radius: 12px; box-shadow: var(--shadow); line-height:1.45; }
.ts-label { color: var(--slate); font-size: .7rem; font-weight: 700; letter-spacing: .12em; text-transform: uppercase; margin: .6rem 0 .45rem 0; }
.ts-legend span.dot { display:inline-block; width:10px; height:10px; border-radius:50%; margin:0 4px 0 10px; vertical-align:middle; }
.ts-footer { color: var(--slate); font-size: .74rem; border-top: 1px solid var(--line); margin-top: 2rem; padding-top: .7rem; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

SEG_COLOR = {"A": "#0B2545", "B": "#21A99F", "C": "#A0AEC0"}
FUENTE_POB = "INE · Censo Anual de Población 1-1-2025 (sección censal), agregado con el callejero sanitario GVA (oct-2026)"


# ------------------------------------------------------------------ datos (cache)
@st.cache_data
def _data():
    return load_population(), load_accounts(), load_relationships()


@st.cache_resource
def _geo():
    return load_departments_geo()


@st.cache_data
def _route(start: str):
    return department_route(_geo(), start=start)


@st.cache_data
def _json(name: str):
    p = PROCESSED / name
    return json.loads(p.read_text()) if p.exists() else {}


@st.cache_data
def _sources():
    p = ROOT / "data" / "raw" / "SOURCES.json"
    return json.loads(p.read_text()) if p.exists() else []


pop, acc, rel = _data()

# ------------------------------------------------------------------ barra lateral
with st.sidebar:
    st.header("Parámetros")
    area = st.selectbox("Área terapéutica", available_areas(), format_func=lambda a: a.upper(),
                        help="Cada área se define en config/areas/<area>.yaml (prevalencias, recursos, pesos).")
    cfg = load_config(area)
    st.caption(cfg["area"]["nombre"])

    st.subheader("Prevalencia (estimación)")
    esc = st.radio("Escenario", ["bajo", "base", "alto"], index=1, horizontal=True)
    notas = cfg["prevalencia"]["notas"]
    p_inf = st.slider("Infanto-juvenil 6–17 (%)", 2.0, 12.0, float(cfg["prevalencia"]["infantil"][esc]), 0.1,
                      help=notas[f"infantil_{esc}"])
    p_adu = st.slider("Adultos 18–64 (%)", 1.0, 6.0, float(cfg["prevalencia"]["adulto"][esc]), 0.1,
                      help=notas[f"adulto_{esc}"] + " · " + " ".join(str(notas.get("adulto_contexto", "")).split()))

    def nota_prev(g: str, val: float) -> str:
        ref = cfg["prevalencia"][g][esc]
        if abs(val - ref) < 1e-9:
            return notas[f"{g}_{esc}"]
        return f"Valor personalizado ({fmt_dec(val)} %); el escenario «{esc}» es {fmt_dec(ref)} % · {notas[f'{g}_{esc}']}"
    for g, v_ in [("infantil", p_inf), ("adulto", p_adu)]:
        if abs(v_ - cfg["prevalencia"][g][esc]) > 1e-9:
            st.caption(f"{'6–17' if g == 'infantil' else '18–64'}: valor personalizado, no corresponde a una fuente publicada.")

    st.subheader("Pesos del score")
    st.caption("Se normalizan para sumar 100 %.")
    w = {}
    for k, lab in [("potencial", "Potencial"), ("brecha", "Brecha"), ("relevancia", "Relevancia del tipo"),
                   ("mercado_privado", "Mercado privado"), ("acceso", "Acceso (relación)")]:
        w[k] = st.slider(lab, 0.0, 1.0, float(cfg["pesos"][k]), 0.05, disabled=(k == "acceso" and rel is None))
    if rel is None:
        st.warning("**Modo demo**: no hay capa privada `data/private/relaciones.csv`. El componente *acceso* "
                   "no se aplica (peso 0).")
    else:
        sin_cuenta = len(set(rel.id_cuenta) - set(acc.id))
        st.success(f"Capa privada de relación cargada (no se publica): {int((rel.relacion == 'si').sum())} cuentas "
                   "con relación.")
        avisos = []
        if rel.attrs.get("ids_duplicados"):
            avisos.append(f"{rel.attrs['ids_duplicados']} id duplicados (se ha tomado «sí» si alguno lo era)")
        if rel.attrs.get("valores_no_reconocidos"):
            avisos.append(f"{rel.attrs['valores_no_reconocidos']} filas con valor de relación no reconocido (ignoradas)")
        if sin_cuenta:
            avisos.append(f"{sin_cuenta} id que no corresponden a ninguna cuenta actual")
        if avisos:
            st.warning("Revisa relaciones.csv: " + "; ".join(avisos) + ".")

prev = prevalence(cfg, esc, override={"infantil": p_inf, "adulto": p_adu})
dept = department_metrics(pop, acc, cfg, prev)
try:
    scored = add_why(score_accounts(acc, dept, cfg, weights=w, relationships=rel))
except ValueError:
    st.error("Al menos un peso debe ser mayor que 0.")
    st.stop()
pesos_ef = scored.attrs["pesos"]

# ------------------------------------------------------------------ cabecera
st.markdown(
    "<div class='ts-hero'><div class='ts-eyebrow'>Neurociencias · TDAH · Comunitat Valenciana</div>"
    "<div class='ts-title'>Territory Scope NS Valencia</div>"
    "<div class='ts-sub'>Inteligencia territorial construida exclusivamente con datos públicos y agregados. "
    "Sin datos de pacientes individuales, prescripción ni ventas. Análisis a nivel de cuenta (centro, servicio, "
    "unidad), nunca de profesional.</div>"
    f"<div class='ts-chips'><span class='ts-chip'>24 departamentos de salud</span>"
    f"<span class='ts-chip'>{len(scored)} cuentas</span><span class='ts-chip'>INE · Censo 1-1-2025</span>"
    f"<span class='ts-chip'>Registro GVA · OSM</span><span class='ts-chip'>Scoring explicable A/B/C</span></div></div>",
    unsafe_allow_html=True)
def kpi(label: str, value: str, sub: str, help_: str, tag: str) -> str:
    return (f"<div class='ts-kpi' title='{html.escape(help_, quote=True)}'><div class='ts-kpi-l'>{label}</div>"
            f"<div class='ts-kpi-v'>{value}</div><div class='ts-kpi-s'><span class='ts-tag ts-{tag}'>{tag}</span>"
            f"{sub}</div></div>")


st.markdown("<div class='ts-kpis'>" + "".join([
    kpi("Población 6–17", fmt(dept.pob_infantil.sum()), "INE · 1-1-2025", f"Dato · {FUENTE_POB}", "dato"),
    kpi("Pacientes 6–17", fmt(dept.pac_infantil.sum()),
        f"rango {fmt(dept.pac_infantil_bajo.sum())}–{fmt(dept.pac_infantil_alto.sum())} · prev. {fmt_dec(p_inf)} %",
        f"Estimación = población × prevalencia. {nota_prev('infantil', p_inf)}", "estimación"),
    kpi("Pacientes 18–64", fmt(dept.pac_adulto.sum()),
        f"rango {fmt(dept.pac_adulto_bajo.sum())}–{fmt(dept.pac_adulto_alto.sum())} · prev. {fmt_dec(p_adu)} %",
        f"Estimación = población × prevalencia. {nota_prev('adulto', p_adu)}", "estimación"),
    kpi("Cuentas", str(len(scored)), "centros y unidades", "Fuentes públicas: GVA y OpenStreetMap. Ver Metodología.", "dato"),
    kpi("Cuentas verificadas", f"{100 * (scored.verificado == 'si').mean():.0f} %", "en fuente oficial",
        "Existencia y tipo confirmados en fuente oficial; el resto está marcado como pendiente.", "dato"),
]) + "</div>", unsafe_allow_html=True)

tabs = st.tabs(["Mapa del territorio", "Ranking de cuentas", "Patient journey TDAH",
                "Plan de visitas", "Metodología y limitaciones"])

# ------------------------------------------------------------------ 1. MAPA
with tabs[0]:
    c1, c2 = st.columns([3, 1.25])
    with c2:
        metrica = st.selectbox("Métrica del mapa", list(C.METRICAS_MAPA), format_func=lambda m: C.METRICAS_MAPA[m][0])
        lab, kind = C.METRICAS_MAPA[metrica]
        st.caption(f"Tipo: **{kind}** · Población: {FUENTE_POB}." +
                   (f" Prevalencia aplicada: {fmt_dec(p_inf)} % (6–17) / {fmt_dec(p_adu)} % (18–64)." if kind == "estimación" else ""))
        segs = st.multiselect("Segmentos visibles", ["A", "B", "C"], default=["A", "B", "C"], placeholder="Ninguno")
        st.markdown("<div class='ts-legend'><span class='ts-label'>Segmento</span>" + "".join(
            f"<span class='dot' style='background:{c}'></span>{s}" for s, c in SEG_COLOR.items()) +
            "<br><span style='font-size:.78rem;color:#5B6B7F'>● círculo = público (SVS) · ◆ rombo = privado</span></div>",
            unsafe_allow_html=True)
        st.markdown("<div class='ts-label'>Insights del territorio</div>", unsafe_allow_html=True)
        for t in territory_insights(dept):
            st.markdown(f"<div class='ts-insight'>{t}</div>", unsafe_allow_html=True)
        st.caption("Insights generados por reglas a partir de estimaciones (no de casos reales).")

    with c1:
        g = _geo()[["dpto", "geometry"]].merge(dept, on="dpto")
        g["valor_fmt"] = g[metrica].map(fmt)
        m = folium.Map(location=[39.35, -0.55], zoom_start=8, tiles=None)
        folium.TileLayer(
            "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ", name="Gris claro").add_to(m)
        folium.Choropleth(geo_data=g.to_json(), data=g, columns=["dpto", metrica], key_on="feature.properties.dpto",
                          fill_color="Blues", fill_opacity=0.7, line_opacity=0.5, legend_name=lab,
                          nan_fill_color="white").add_to(m)
        folium.GeoJson(g.to_json(), style_function=lambda f: {"fillOpacity": 0, "weight": 0},
                       tooltip=folium.GeoJsonTooltip(fields=["dpto", "departamento", "valor_fmt", "n_usmi", "n_usm"],
                                                     aliases=["Dpto", "Departamento", lab, "USMI registradas",
                                                              "USM registradas"])).add_to(m)
        pts = scored[scored.segmento.isin(segs)].copy()
        # Cuentas en el mismo punto (p. ej. hospital + su neuropediatría): se separan ~50 m para que se vean todas.
        k = pts.groupby(["lat", "lon"]).cumcount()
        n_same = pts.groupby(["lat", "lon"]).id.transform("size")
        ang = 2 * np.pi * k / n_same.clip(lower=1)
        pts["mlat"] = pts.lat + np.where(n_same > 1, 0.00045 * np.sin(ang), 0)
        pts["mlon"] = pts.lon + np.where(n_same > 1, 0.00058 * np.cos(ang), 0)
        for r in pts.itertuples():
            amb = ("Privado · titularidad privada (Registro GVA)" if r.ambito == "privado"
                   else "Público · Sistema Valenciano de Salud")
            tip = (f"<b>{html.escape(r.nombre)}</b><br>{C.TIPO_LABEL.get(r.tipo, r.tipo)}<br>{amb}<br>"
                   f"Segmento <b>{r.segmento}</b> · score {fmt_dec(r.score)}<br>Verificado: {r.verificado} · "
                   f"Fuente: {r.fecha_fuente}")
            size = 7 if r.segmento == "A" else 5.5
            if r.ambito == "privado":   # privado = rombo
                folium.RegularPolygonMarker([r.mlat, r.mlon], number_of_sides=4, rotation=45, radius=size + 1.5,
                                            color="#1F2A37", weight=1.2, fill=True, fill_color=SEG_COLOR[r.segmento],
                                            fill_opacity=0.95, tooltip=tip).add_to(m)
            else:                       # público = círculo
                folium.CircleMarker([r.mlat, r.mlon], radius=size, color="white", weight=1.2, fill=True,
                                    fill_color=SEG_COLOR[r.segmento], fill_opacity=0.95, tooltip=tip).add_to(m)
        st_folium(m, height=620, use_container_width=True, returned_objects=[])

# ------------------------------------------------------------------ 2. RANKING
with tabs[1]:
    f1, f2, f3, f4 = st.columns(4)
    ft = f1.multiselect("Tipo", sorted(scored.tipo.unique()), format_func=lambda t: C.TIPO_LABEL.get(t, t), placeholder="Todos")
    fa = f2.multiselect("Ámbito", ["publico", "privado"], placeholder="Todos")
    fd = f3.multiselect("Departamento", sorted(scored.departamento.unique()), placeholder="Todos")
    fs = f4.multiselect("Segmento", ["A", "B", "C"], placeholder="Todos")
    v = scored.copy()
    v["tipo_label"] = v.tipo.map(C.TIPO_LABEL).fillna(v.tipo)
    for col, sel in [("tipo", ft), ("ambito", fa), ("departamento", fd), ("segmento", fs)]:
        if sel:
            v = v[v[col].isin(sel)]
    st.caption(f"{len(v)} cuentas · pesos efectivos: " +
               " · ".join(f"{k.replace('_', ' ')} {100 * x:.0f} %" for k, x in pesos_ef.items()) +
               ". Componentes 0–100; potencial y brecha son estimaciones. Segmentos por umbral de score: "
               "las cuentas empatadas comparten segmento.")
    cols = ["rank", "segmento", "score", "nombre", "por_que", "tipo_label", "ambito", "departamento", "municipio",
            "c_potencial", "c_brecha", "c_relevancia", "c_mercado_privado", "c_acceso",
            "verificado", "fecha_fuente", "fuente_url"]
    st.dataframe(
        v[cols].round(1), hide_index=True, width="stretch", height=560,
        column_config={
            "score": st.column_config.ProgressColumn("Score", min_value=0, max_value=100, format="localized"),
            "segmento": st.column_config.TextColumn("Segmento"),
            "nombre": st.column_config.TextColumn("Cuenta"),
            "ambito": st.column_config.TextColumn("Ámbito"),
            "departamento": st.column_config.TextColumn("Departamento"),
            "municipio": st.column_config.TextColumn("Municipio"),
            "verificado": st.column_config.TextColumn("Verificado"),
            "fecha_fuente": st.column_config.TextColumn("Fecha fuente"),
            "tipo_label": st.column_config.TextColumn("Tipo"),
            "rank": st.column_config.NumberColumn("Rank", help="Empates comparten posición y segmento"),
            "c_potencial": st.column_config.NumberColumn("Potencial", format="localized", help="Pacientes estimados del departamento (población diana), 0–100"),
            "c_brecha": st.column_config.NumberColumn("Brecha", format="localized", help="Pacientes estimados por recurso especializado, 0–100"),
            "c_relevancia": st.column_config.NumberColumn("Relevancia", format="localized", help="Peso por tipo de cuenta (×0,8 si no verificada)"),
            "c_mercado_privado": st.column_config.NumberColumn("Privado", format="localized"),
            "c_acceso": st.column_config.NumberColumn("Acceso", format="localized"),
            "por_que": st.column_config.TextColumn("Por qué", width="large"),
            "fuente_url": st.column_config.LinkColumn("Fuente", display_text="ver"),
        })
    st.download_button("Exportar ranking (CSV)", v[cols + ["id", "lat", "lon"]].to_csv(index=False).encode("utf-8-sig"),
                       "ranking_cuentas_tdah.csv", "text/csv")

# ------------------------------------------------------------------ 3. PATIENT JOURNEY
with tabs[2]:
    st.subheader("Circuito asistencial del TDAH (modelo general)")
    st.caption("Esquema simplificado basado en guías clínicas; la organización concreta varía entre departamentos.")
    _, gcol, _ = st.columns([1, 6, 1])
    with gcol:
        st.graphviz_chart(C.JOURNEY_DOT, width="stretch")

    st.subheader("Puntos de fricción")
    cols3 = st.columns(3)
    for col, f in zip(cols3, C.FRICCIONES):
        with col:
            with st.container(border=True):
                st.markdown(f"**{f['titulo']}**")
                st.write(f["texto"])
                st.caption(f"En este mapa: {f['en_el_mapa']}")
                for rid in f["refs"]:
                    txt, url = C.REFERENCIAS[rid]
                    st.caption(f"Ref.: [{C.REF_CORTA[rid]}]({url})")

    st.subheader("Dónde aporta valor un KAM")
    for col, (t, d) in zip(st.columns(3), C.VALOR_KAM):
        with col:
            with st.container(border=True):
                st.markdown(f"**{t}**")
                st.write(d)
    with st.expander("Referencias completas"):
        for txt, url in C.REFERENCIAS.values():
            st.markdown(f"- {txt} [{url}]({url})")
        st.caption("Artículos verificados en PubMed (título, autores, año y cifra) el 06-11-2026.")

# ------------------------------------------------------------------ 4. PLAN DE VISITAS
with tabs[3]:
    vc = cfg["visitas"]
    p1, p2, p3, p4, p5, p6 = st.columns(6)
    vd = p1.number_input("Visitas/día", 1, 15, vc["visitas_dia"])
    dm = p2.number_input("Días de campo/mes", 1, 23, vc["dias_campo_mes"])
    fa_ = p3.selectbox("Frecuencia A", [1.0, 0.5, 0.33], index=0, format_func=lambda x: {1.0: "mensual", 0.5: "bimensual", 0.33: "trimestral"}[x])
    fb_ = p4.selectbox("Frecuencia B", [1.0, 0.5, 0.33], index=1, format_func=lambda x: {1.0: "mensual", 0.5: "bimensual", 0.33: "trimestral"}[x])
    fc_ = p5.selectbox("Frecuencia C", [1.0, 0.5, 0.33], index=2, format_func=lambda x: {1.0: "mensual", 0.5: "bimensual", 0.33: "trimestral"}[x])
    meses = p6.number_input("Meses del ciclo", 1, 6, 3)
    base = st.selectbox("Departamento de salida (ruta)", dept.dpto, index=6,
                        format_func=lambda d: f"{d} · {dept.set_index('dpto').departamento[d].title()}")
    plan, res, no_cub = build_plan(scored, _route(base), int(vd), int(dm), {"A": fa_, "B": fb_, "C": fc_}, int(meses))

    st.dataframe(res.rename(columns={"visitas_planificadas": "planificadas", "dias_usados": "días usados"}),
                 hide_index=True, width="stretch")
    if len(no_cub):
        st.warning(f"La capacidad ({int(vd * dm)} visitas/mes) no cubre toda la demanda: {len(no_cub)} visitas quedan "
                   "fuera (las de menor score, empezando por C).")
    cov = coverage(plan, scored)
    st.caption("Cobertura en el ciclo: " + " · ".join(
        f"{r.segmento}: {r.cuentas_visitadas}/{r.cuentas} cuentas, {r.visitas} visitas" for r in cov.itertuples()))

    mes_sel = st.radio("Mes", list(range(1, int(meses) + 1)), horizontal=True, format_func=lambda x: f"Mes {x}")
    pm = plan[plan.mes == mes_sel]
    dias = pm.groupby("dia").agg(departamentos=("departamento", lambda s: " → ".join(dict.fromkeys(s.str.title()))),
                                 visitas=("id", "size"), A=("segmento", lambda s: (s == "A").sum())).reset_index()
    cA, cB = st.columns([1, 2])
    cA.markdown("**Agenda por día**")
    cA.dataframe(dias, hide_index=True, width="stretch", height=420)
    cB.markdown("**Detalle de visitas**")
    cB.dataframe(pm[["dia", "orden_en_dia", "departamento", "nombre", "tipo", "segmento", "score"]], hide_index=True,
                 width="stretch", height=420)
    st.download_button("Exportar plan completo (CSV)", plan.to_csv(index=False).encode("utf-8-sig"),
                       "plan_visitas_tdah.csv", "text/csv")
    st.caption("Ruta: departamentos ordenados por vecino más próximo (centroides). Las visitas de un mismo "
               "departamento van en bloque para reducir desplazamientos. Las cuentas B y C se escalonan entre meses.")

# ------------------------------------------------------------------ 5. METODOLOGÍA
with tabs[4]:
    st.subheader("Qué es dato y qué es estimación")
    st.table(pd.DataFrame([
        ["Población por departamento y edad", "Dato", FUENTE_POB],
        ["Departamentos de salud (geometría)", "Dato", "GVA · capa de departamentos de salud (05-10-2026)"],
        ["Cuentas: hospitales públicos", "Dato", "GVA · red de hospitales SVS (oct-2026)"],
        ["Cuentas: USM, USMI, privada", "Dato (2021)", "GVA · Registro de centros sanitarios 2021 · OSM (no verificado)"],
        ["Neuropediatría hospitalaria", "Inferencia", "Hospital general con pediatría · pendiente de verificar"],
        ["Pacientes TDAH potenciales", "Estimación", "Población × prevalencia publicada (rango bajo/base/alto)"],
        ["Brecha (pacientes por recurso)", "Estimación", "Pacientes estimados / (recursos especializados ponderados + 1); "
         "recursos inferidos = 0,5 y máx. 1 por tipo y departamento"],
        ["Ámbito público / privado", "Dato", "Público = red SVS o dependencia pública en el Registro; privado = dependencia "
         "funcional «PRIVADOS» (puede tener conciertos con la sanidad pública)"],
        ["Score y segmento A/B/C", "Modelo", "Suma ponderada de componentes 0–100; pesos editables"],
    ], columns=["Elemento", "Naturaleza", "Fuente / método"]))

    st.subheader("Prevalencias utilizadas")
    st.table(pd.DataFrame([[g, cfg["prevalencia"][g]["bajo"], cfg["prevalencia"][g]["base"], cfg["prevalencia"][g]["alto"]]
                           for g in ["infantil", "adulto"]], columns=["Grupo", "Bajo %", "Base %", "Alto %"]).style.format(precision=1))
    if cfg["prevalencia"]["notas"].get("adulto_contexto"):
        st.caption(" ".join(str(cfg["prevalencia"]["notas"]["adulto_contexto"]).split()))
    for r in cfg["referencias"]:
        st.markdown(f"- {r['cita']} PMID {r['pmid']} · [doi:{r['doi']}](https://doi.org/{r['doi']})")

    st.subheader("Modelo de priorización")
    st.markdown(
        "`score = Σ peso × componente` · componentes 0–100:\n"
        "- **Potencial**: pacientes estimados del departamento para la población diana de la cuenta (escalado dentro de cada grupo de edad).\n"
        "- **Brecha**: pacientes estimados por recurso especializado del departamento (más pacientes por recurso = más brecha). "
        "Recursos no verificados cuentan 0,5; las privadas de diana «ambas» no cuentan como recurso infantil.\n"
        "- **Relevancia**: peso por tipo de cuenta definido en el YAML; ×0,8 si la cuenta no está verificada.\n"
        "- **Mercado privado**: 100 si la cuenta es privada.\n"
        "- **Acceso**: relación existente (solo con capa privada; en modo demo, peso 0).\n\n"
        "Segmentos: **A** = top 20 %, **B** = siguiente 30 %, **C** = resto, por umbral de score "
        "(las cuentas empatadas comparten segmento, por lo que A o B pueden superar ligeramente su porcentaje).")

    st.subheader("Fuentes (descarga reproducible)")
    src = pd.DataFrame(_sources())
    if len(src):
        st.dataframe(src[["titulo", "editor", "ficha", "fecha_descarga"]], hide_index=True, width="stretch",
                     column_config={"ficha": st.column_config.LinkColumn("Ficha", display_text="abrir")})

    st.subheader("Validación")
    v1, v2 = _json("validacion_fase1.json"), _json("validacion_fase2.json")
    if v1:
        st.markdown(f"- Suma de los 24 departamentos = **{fmt(v1['suma_24_departamentos'])}** habitantes = total INE "
                    f"({fmt(v1['total_ccaa_ine'])}); diferencia {v1['dif_departamentos_vs_ine']}.")
        st.markdown(f"- {v1['secciones_asignadas_por_callejero']} de {v1['secciones_ine']} secciones censales asignadas por "
                    f"callejero sanitario; {v1['secciones_asignadas_por_distrito']} por distrito ({fmt(v1['poblacion_asignada_sin_callejero'])} hab.).")
    if v2:
        st.markdown(f"- {v2['n_cuentas']} cuentas, {v2['pct_verificado']} % verificadas. "
                    f"{v2['excluidas_por_privacidad']} centros privados excluidos por privacidad: nombre de persona física "
                    "o consulta individual (solo se guarda el recuento).")

    st.subheader("Limitaciones")
    for l in C.LIMITACIONES:
        st.markdown(f"- {l}")

    st.subheader("Qué cambiaría con datos internos")
    for t, d in C.CON_DATOS_INTERNOS:
        st.markdown(f"- **{t}**: {d}")
    st.markdown("<div class='ts-insight'>Construido solo con datos públicos. Con datos de CRM y ventas, el mismo modelo sustituiría las "
            "estimaciones por cobertura y rendimiento reales.</div>", unsafe_allow_html=True)
    st.markdown("<div class='ts-footer'>Territory Scope NS Valencia · Prototipo con datos públicos (INE, Generalitat "
                "Valenciana, OpenStreetMap). Herramienta de análisis territorial, no material promocional.</div>",
                unsafe_allow_html=True)
