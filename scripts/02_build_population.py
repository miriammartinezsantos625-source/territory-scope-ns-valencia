"""Fase 1 · Población por departamento de salud (Comunitat Valenciana).

Método
------
1. El callejero sanitario de la GVA asigna cada tramo de vía (con su distrito y sección censal)
   a un departamento de salud, por separado para población adulta y pediátrica.
   → cada sección censal se asigna al departamento que concentra más tramos de vía de esa sección
     (moda). Las pocas secciones partidas entre dos departamentos se registran en el informe.
2. El INE (Censo Anual de Población, 1-1-2025) da la población por sección censal y edad quinquenal.
3. Se suman las secciones por departamento. Secciones del INE que no aparecen en el callejero
   (cambios de seccionado) se asignan al departamento dominante de su municipio.

Grupos de edad (aproximación documentada, el INE publica grupos quinquenales a nivel de sección):
  6–17  = 4/5 · (5–9) + (10–14) + 3/5 · (15–19)
  18–64 = 2/5 · (15–19) + (20–24) + … + (60–64)
Se supone distribución uniforme dentro de cada grupo quinquenal.

Salidas (data/processed/)
  seccion_departamento.csv     sección → departamento (adulto / pediátrico) + método de asignación
  municipio_departamento.csv   municipio → departamento(s), con % de su población en cada uno
  poblacion_departamento.csv   24 departamentos · población total, 0–5, 6–17, 18–64, 65+
  departamentos.geojson        geometría simplificada (WGS84) + población
  validacion_fase1.json        cuadres frente al total del INE y frente a la población SIP de la GVA
"""
from __future__ import annotations

import json
from pathlib import Path

import geopandas as gpd
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)
YEAR = "2025"
INE_TABLES = [69105, 69153, 69277]

AGE_COLS = ["De 0 a 4 años", "De 5 a 9 años", "De 10 a 14 años", "De 15 a 19 años", "De 20 a 24 años",
            "De 25 a 29 años", "De 30 a 34 años", "De 35 a 39 años", "De 40 a 44 años", "De 45 a 49 años",
            "De 50 a 54 años", "De 55 a 59 años", "De 60 a 64 años"]


def ine_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s.str.replace(".", "", regex=False).str.replace(",", ".", regex=False),
                         errors="coerce").fillna(0)


# ---------------------------------------------------------------- 1. INE por sección
def load_ine() -> tuple[pd.DataFrame, pd.DataFrame, float]:
    frames = []
    for t in INE_TABLES:
        d = pd.read_csv(RAW / f"ine/censo_anual_seccion_edad_{t}.csv", sep=";", dtype=str)
        d = d[(d.Periodo == YEAR) & (d.Sexo == "Total")]
        d["valor"] = ine_num(d.Total)
        frames.append(d)
    d = pd.concat(frames)
    ccaa_total = d[d.Municipios.isna() & (d.Edad == "Todas las edades")].valor.sum()
    muni = d[d.Municipios.notna() & d.Secciones.isna() & (d.Edad == "Todas las edades")].copy()
    muni["muni_ine"] = muni.Municipios.str[:5]
    muni["municipio"] = muni.Municipios.str[6:]
    muni = muni[["muni_ine", "municipio", "valor"]].rename(columns={"valor": "pob_ine_municipio"})

    sec = d[d.Secciones.notna()].copy()
    sec["seccion"] = sec.Secciones.str[:10]
    w = sec.pivot_table(index="seccion", columns="Edad", values="valor", aggfunc="sum").fillna(0)
    out = pd.DataFrame(index=w.index)
    out["pob_total"] = w["Todas las edades"]
    out["pob_0_5"] = w["De 0 a 4 años"] + w["De 5 a 9 años"] * 1 / 5
    out["pob_6_17"] = w["De 5 a 9 años"] * 4 / 5 + w["De 10 a 14 años"] + w["De 15 a 19 años"] * 3 / 5
    out["pob_18_64"] = w["De 15 a 19 años"] * 2 / 5 + w[AGE_COLS[4:]].sum(axis=1)
    out["pob_65_mas"] = out.pob_total - out.pob_0_5 - out.pob_6_17 - out.pob_18_64
    out = out.reset_index()
    out["muni_ine"] = out.seccion.str[:5]
    return out, muni, ccaa_total


# ---------------------------------------------------------------- 2. callejero sanitario GVA
def load_callejero() -> pd.DataFrame:
    c = pd.read_csv(RAW / "gva/mapa_sanitario.csv", sep="|", dtype=str)
    c.columns = [x.strip() for x in c.columns]
    loc = c.cd_localidad.astype(int)
    assert (loc % 100 == 0).all(), "cd_localidad no sigue el patrón código INE × 100"
    c["muni_ine"] = c.cd_provincia.str.zfill(2) + (loc // 100).astype(str).str.zfill(3)
    c["seccion"] = c.muni_ine + c.distrito.str.zfill(2) + c.seccion.str.zfill(3)
    return c


def modal_dept(c: pd.DataFrame, key: str, col: str) -> pd.DataFrame:
    g = c.groupby([key, col]).size().rename("n").reset_index()
    g["share"] = g.n / g.groupby(key).n.transform("sum")
    g = g.sort_values([key, "n"], ascending=[True, False]).drop_duplicates(key)
    return g.set_index(key)[[col, "share"]]


# ---------------------------------------------------------------- 3. agregación
def main() -> None:
    sec, muni, ccaa_total = load_ine()
    c = load_callejero()

    ad_s, ni_s = modal_dept(c, "seccion", "cd_dpto_adulto"), modal_dept(c, "seccion", "cd_dpto_ninyo")
    ad_m, ni_m = modal_dept(c, "muni_ine", "cd_dpto_adulto"), modal_dept(c, "muni_ine", "cd_dpto_ninyo")
    c["distrito_ine"] = c.seccion.str[:7]
    ad_d, ni_d = modal_dept(c, "distrito_ine", "cd_dpto_adulto"), modal_dept(c, "distrito_ine", "cd_dpto_ninyo")

    sec["dpto_adulto"] = sec.seccion.map(ad_s.cd_dpto_adulto)
    sec["dpto_pediatrico"] = sec.seccion.map(ni_s.cd_dpto_ninyo)
    sec["share_tramos_adulto"] = sec.seccion.map(ad_s.share)
    sec["metodo"] = "callejero_seccion"
    miss = sec.dpto_adulto.isna()
    dist = sec.seccion.str[:7]
    sec.loc[miss, "dpto_adulto"] = dist[miss].map(ad_d.cd_dpto_adulto)
    sec.loc[miss, "dpto_pediatrico"] = dist[miss].map(ni_d.cd_dpto_ninyo)
    sec.loc[miss, "metodo"] = "dominante_distrito"
    miss = sec.dpto_adulto.isna()
    sec.loc[miss, "dpto_adulto"] = sec.loc[miss, "muni_ine"].map(ad_m.cd_dpto_adulto)
    sec.loc[miss, "dpto_pediatrico"] = sec.loc[miss, "muni_ine"].map(ni_m.cd_dpto_ninyo)
    sec.loc[miss, "metodo"] = "dominante_municipio"
    unassigned = sec[sec.dpto_adulto.isna()]
    for col in ["dpto_adulto", "dpto_pediatrico"]:
        sec[col] = sec[col].astype("Int64").astype(str).str.zfill(2)

    sec.round(2).to_csv(OUT / "seccion_departamento.csv", index=False)

    # Población: los grupos infantiles se asignan al departamento pediátrico; el resto al adulto.
    child = sec.groupby("dpto_pediatrico")[["pob_0_5", "pob_6_17"]].sum()
    adult = sec.groupby("dpto_adulto")[["pob_18_64", "pob_65_mas"]].sum()
    tot_ad = sec.groupby("dpto_adulto").pob_total.sum().rename("pob_total_dpto_adulto")
    pop = child.join(adult, how="outer").join(tot_ad).fillna(0)
    pop["pob_total"] = pop[["pob_0_5", "pob_6_17", "pob_18_64", "pob_65_mas"]].sum(axis=1)
    pop.index.name = "dpto"

    geo = gpd.read_file(RAW / "gva/ca_departamentos_20261005.geojson")
    geo = geo.rename(columns={"DPTOCRC": "dpto", "NOMBRE": "departamento", "POB_TOTAL_": "pob_sip_total",
                              "POB_TOT_01": "pob_sip_pediatrica"})
    pop = geo[["dpto", "departamento", "pob_sip_total", "pob_sip_pediatrica"]].merge(
        pop.reset_index(), on="dpto", how="left")
    pop["n_secciones"] = pop.dpto.map(sec.groupby("dpto_adulto").size())
    pop["pct_6_17"] = 100 * pop.pob_6_17 / pop.pob_total
    pop["pct_18_64"] = 100 * pop.pob_18_64 / pop.pob_total
    pop["dif_vs_sip_pct"] = 100 * (pop.pob_total / pop.pob_sip_total - 1)
    for col in ["pob_0_5", "pob_6_17", "pob_18_64", "pob_65_mas", "pob_total", "pob_total_dpto_adulto"]:
        pop[col] = pop[col].round().astype(int)
    pop["fuente"] = f"INE Censo Anual de Población 1-1-{YEAR} (sección censal) + callejero sanitario GVA"
    pop.drop(columns="pob_total_dpto_adulto").round(2).to_csv(OUT / "poblacion_departamento.csv", index=False)

    # municipio → departamento(s)
    md = sec.groupby(["muni_ine", "dpto_adulto"]).pob_total.sum().reset_index()
    md["pct_poblacion_municipio"] = 100 * md.pob_total / md.groupby("muni_ine").pob_total.transform("sum")
    md = md.merge(muni, on="muni_ine", how="left").merge(
        geo[["dpto", "departamento"]], left_on="dpto_adulto", right_on="dpto").drop(columns="dpto")
    md = md[["muni_ine", "municipio", "dpto_adulto", "departamento", "pob_total", "pct_poblacion_municipio"]]
    md.round(2).sort_values(["muni_ine", "pct_poblacion_municipio"], ascending=[True, False]).to_csv(
        OUT / "municipio_departamento.csv", index=False)

    # geometría para la app (WGS84, simplificada ~50 m)
    g = geo[["dpto", "departamento", "geometry"]].copy()
    g["geometry"] = g.geometry.simplify(50, preserve_topology=True)
    g = g.to_crs(4326).merge(pop.drop(columns=["departamento", "fuente"]), on="dpto")
    g.to_file(OUT / "departamentos.geojson", driver="GeoJSON")

    # validación
    split_secs = ad_s[ad_s.share < 1]
    val = {
        "anio_poblacion": YEAR,
        "total_ccaa_ine": int(ccaa_total),
        "suma_municipios_ine": int(muni.pob_ine_municipio.sum()),
        "suma_secciones_ine": int(round(sec.pob_total.sum())),
        "suma_24_departamentos": int(pop.pob_total.sum()),
        "dif_departamentos_vs_ine": int(pop.pob_total.sum() - ccaa_total),
        "suma_pob_campos_capa_gva": int(pop.pob_sip_total.sum()),
        "nota_campos_capa_gva": "Los campos POB_* de la capa de departamentos suman ~4,66 M (orden de la "
                                "población CV ~2005); se consideran heredados y NO se usan como dato.",
        "secciones_ine": int(len(sec)),
        "secciones_asignadas_por_callejero": int((sec.metodo == "callejero_seccion").sum()),
        "secciones_asignadas_por_distrito": int((sec.metodo == "dominante_distrito").sum()),
        "secciones_asignadas_por_municipio": int((sec.metodo == "dominante_municipio").sum()),
        "poblacion_asignada_sin_callejero": int(sec.loc[sec.metodo != "callejero_seccion", "pob_total"].sum()),
        "secciones_sin_asignar": unassigned.seccion.tolist(),
        "secciones_partidas_en_callejero": int(len(split_secs)),
        "municipios_multidepartamento": int((md.groupby("muni_ine").size() > 1).sum()),
        "secciones_dpto_pediatrico_distinto": int((sec.dpto_adulto != sec.dpto_pediatrico).sum()),
    }
    (OUT / "validacion_fase1.json").write_text(json.dumps(val, ensure_ascii=False, indent=2))
    print(json.dumps(val, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
