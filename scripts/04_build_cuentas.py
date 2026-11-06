"""Fase 2 · Construye data/processed/cuentas.csv (una fila por cuenta: centro / servicio / unidad).

Fuentes (todas públicas, ver data/raw/SOURCES.json):
  A. GVA · Red de hospitales públicos SVS (capa ICV)            → hospital_publico, neuropediatria
  B. GVA · Registro de centros sanitarios 2021                    → usm, usmi, hospital_dia_sm,
                                                                    hospital_psiquiatrico, privada_*
  C. OpenStreetMap (Overpass)                                     → privada_* no presentes en B

Reglas aplicadas
  · Solo cuentas (centros/unidades). Se EXCLUYEN los centros cuyo nombre identifica a una persona
    física (consultas a nombre de un profesional): regla de cero datos personales de médicos.
  · verificado = "si" solo si la existencia y el tipo constan en una fuente oficial; "no" si el tipo
    es una inferencia (p. ej. neuropediatría en un hospital) o la fuente no es oficial (OSM).
  · Departamento asignado por posición (punto en polígono de la capa oficial de departamentos).
  · Coordenadas de B geocodificadas con CartoCiudad (IGN); se comprueba que el municipio devuelto
    coincide con el del registro. Caché en data/raw/geocode_cache.json.
"""
from __future__ import annotations

import json
import re
import time
import unicodedata
from datetime import date
from pathlib import Path

import geopandas as gpd
import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.geo_names import build_index, match_with_aliases  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RAW, OUT = ROOT / "data" / "raw", ROOT / "data" / "processed"
SOURCES = {s["id"]: s for s in json.loads((RAW / "SOURCES.json").read_text())}
CACHE_PATH = RAW / "geocode_cache.json"
UA = {"User-Agent": "territory-scope-ns-valencia/0.1 (public-data research prototype)"}

COLS = ["id", "nombre", "tipo", "ambito", "poblacion_diana", "dpto", "departamento", "municipio",
        "direccion", "lat", "lon", "precision_geo", "fuente", "fuente_url", "fecha_fuente", "fecha_consulta",
        "verificado", "nota"]


# ------------------------------------------------------------------ utilidades
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", s)


GENERIC = set(norm(
    "consulta consultas clinica clinicas centro centre centros de del la las el los y e i en para con "
    "psiquiatria psiquiatrica psiquiatrico psiquiatricos medica medico psicologia psicologica psicologo "
    "clinica salud mental salut infantil infanto juvenil adolescentes ninos nios adolescentes adultos "
    "neuropediatria neurologia pediatrica neurodesarrollo neurodesenvolupament tdah polivalente "
    "psicoterapia unidad hospital dia instituto valenciano sl s l slp sa grupo gabinete integral"
).split())
ORG = re.compile(r"\b(clinica|clinicas|centro|centre|instituto|institut|hospital|unidad|gabinete|asociacion|"
                 r"fundacion|grupo|sanatorio|casa de reposo|sl|slp|sa)\b")
PERSON_TITLE = re.compile(r"\b(dr|dra|doctor|doctora)\b")
# Nombres de pila frecuentes (es/ca) para detectar consultas a nombre de una persona.
FIRST_NAMES = set(norm(
    "maria m mª jose josep juan joan antonio antoni francisco francesc manuel miguel miquel pedro pere "
    "carlos jesus javier xavier rafael david daniel luis lluis jorge jordi alberto fernando sergio pablo "
    "ana carmen isabel laura lucia marta cristina elena pilar rosa teresa mercedes amparo asuncion "
    "dolores encarna raquel silvia sonia beatriz patricia nuria eva berta neria amadeo vicente vicent "
    "enrique ramon ignacio alejandro andres mario oscar ruben victor alfonso salvador gonzalo"
).split())


def is_personal_name(name: str) -> bool:
    n = norm(name)
    toks = n.split()
    if PERSON_TITLE.search(n) or any(t in FIRST_NAMES for t in toks):
        return True
    if all(t in GENERIC for t in toks):
        return False
    return not ORG.search(n)  # quedan tokens propios y no es una organización → probablemente persona


ABREV = {r"\bAVDA\.?\b": "AVENIDA", r"\bAV\.?\b": "AVENIDA", r"\bPTDA\.?\b": "PARTIDA", r"\bCRA\.?\b": "CARRETERA",
         r"\bCTRA\.?\b": "CARRETERA", r"\bPZA\.?\b": "PLAZA", r"\bPSO\.?\b": "PASEO", r"\bC/": "CALLE "}


def _expand(direccion: str) -> str:
    d = re.sub(r"\s+", " ", direccion.upper()).strip()
    for k, v in ABREV.items():
        d = re.sub(k, v, d)
    # fuera añadidos que confunden al geocodificador (piso, urbanización, bajo...)
    d = re.split(r"\b(ENTLO|ENTRESUELO|BAJO|BJ|PISO|PTA|PUERTA|URBANIZACI[OÓ]N|URB|LOCAL|ESC)\b", d)[0]
    return d.strip(" ,")


def _cartociudad(q: str, cache: dict, endpoint: str = "find") -> dict | list:
    key = f"{endpoint}|{q}" if endpoint != "find" else q
    if key not in cache:
        try:
            url = "https://www.cartociudad.es/geocoder/api/geocoder/" + ("find" if endpoint == "find" else "candidates")
            r = requests.get(url, params={"q": q, "limit": 5} if endpoint != "find" else {"q": q}, headers=UA, timeout=30)
            ok = r.ok and r.text.strip()[:1] in "{["
            cache[key] = r.json() if ok else ({} if endpoint == "find" else [])
        except (requests.RequestException, ValueError):
            cache[key] = {} if endpoint == "find" else []
        time.sleep(0.2)
    return cache[key]


PREC_TIPO = {"portal": "portal", "toponimo": "portal", "callejero": "calle", "poblacion": "municipio",
             "Municipio": "municipio", "municipio": "municipio"}


def geocode(direccion: str, municipio: str, muni_ine: str | None, cache: dict, muni_ine_nombre: str = "") -> tuple[float | None, float | None, str]:
    """Dirección literal → abreviaturas expandidas → calle → candidatos → municipio.

    La precisión se toma del TIPO devuelto por CartoCiudad (portal/topónimo = exacta, callejero = calle,
    población = municipio). Se rechazan coincidencias que no son direcciones (p. ej. puntos de recarga)
    y las de otro municipio.
    """
    muni_q = (muni_ine_nombre or municipio).split("/")[0]
    exp = _expand(direccion)
    calle = re.sub(r"\b(S/N|SN|\d+[A-Z]?)\b.*$", "", exp).strip(" ,")

    def ok(g, allow_muni=False):
        prec = PREC_TIPO.get(g.get("type"))
        good = g.get("lat") and prec and (allow_muni or prec != "municipio") and (muni_ine is None or g.get("muniCode") == muni_ine)
        return prec if good else None

    for q in [f"{direccion}, {municipio}", f"{exp}, {muni_q}", f"{calle}, {muni_q}"]:
        g = _cartociudad(q, cache)
        if (prec := ok(g)):
            return g["lat"], g["lng"], prec
    for cand in _cartociudad(f"{exp}, {muni_q}", cache, "candidates"):
        if cand.get("muniCode") == muni_ine and cand.get("type") in ("portal", "callejero", "toponimo"):
            g = _cartociudad(cand.get("address", ""), cache)
            if (prec := ok(g)):
                return g["lat"], g["lng"], prec
    g = _cartociudad(muni_q, cache)
    if ok(g, allow_muni=True):
        return g["lat"], g["lng"], "municipio"
    return None, None, "no_geocodificado"


# ------------------------------------------------------------------ A. hospitales públicos
def hospitales_publicos() -> pd.DataFrame:
    s = SOURCES["gva_hospitales_svs"]
    h = pd.read_csv(RAW / s["path"], dtype=str)
    pts = gpd.GeoDataFrame(h, geometry=gpd.points_from_xy(h.x_coord.astype(float), h.y_coord.astype(float)),
                           crs=25830).to_crs(4326)
    base = pd.DataFrame({
        "src": "svs-" + h.cen_cod, "nombre": h.cen_desclar.str.strip(), "municipio": h.municipio,
        "direccion": (h.cen_nombcall.fillna("") + " " + h.cen_numcall.fillna("")).str.strip(),
        "lat": pts.geometry.y.round(6), "lon": pts.geometry.x.round(6), "ambito": "publico",
        "fuente": s["titulo"], "fuente_url": s["ficha"], "fecha_fuente": "2026-10",
        "fecha_consulta": s["fecha_descarga"], "_dpto_svs": h.codigo_departamento})
    largo = base._dpto_svs == "00"   # hospitales de atención a crónicos y larga estancia (HACLE)
    psiq = base.nombre.str.contains("PSIQUIATRIC", case=False)
    malva = base.nombre.str.contains("MALVA-ROSA", case=False)

    hosp = base[~largo & ~psiq & ~malva].assign(
        tipo="hospital_publico", poblacion_diana="ambas", verificado="si",
        nota="Hospital general de agudos de la red pública (servicio de psiquiatría y pediatría no desglosado en la fuente)")
    hpsq = base[psiq].assign(tipo="hospital_psiquiatrico", poblacion_diana="adulto", verificado="si", nota="")
    neuro = base[~largo & ~psiq & ~malva].assign(
        src=lambda d: d.src + "-np", nombre=lambda d: "Pediatría / Neuropediatría · " + d.nombre,
        tipo="neuropediatria", poblacion_diana="infantil", verificado="no",
        nota="Servicio inferido (hospital general con pediatría). Pendiente de confirmar neuropediatría en la web del hospital.")
    return pd.concat([hosp, hpsq, neuro])


# ------------------------------------------------------------------ B. registro 2021
def registro(cache: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = SOURCES["gva_registro_centros_2021"]
    d = pd.read_csv(RAW / s["path"], sep=";", dtype=str)
    d.columns = ["anio", "cp", "prov", "cm", "muni", "reg", "centro", "ctipo", "tipo_reg", "cdep", "dep",
                 "creg", "regimen", "dir"]
    d["centro"] = d.centro.str.strip().str.replace(r"\s+", " ", regex=True)
    # El código de municipio del registro es ambiguo (p. ej. Alicante y Villena = "140"):
    # se empareja por NOMBRE con el nomenclátor INE (formas bilingües y artículos normalizados).
    md = pd.read_csv(OUT / "municipio_departamento.csv", dtype=str).drop_duplicates("muni_ine")
    idx = build_index(md)
    # "Eliana, l'" → "l'Eliana" (forma que entiende CartoCiudad)
    ine_names = {k: re.sub(r"^(.*), (l'|el|la|les|els)$", r"\2 \1", v).replace("l' ", "l'")
                 for k, v in md.set_index("muni_ine").municipio.items()}
    d["cp"] = d.cp.str.strip().str.zfill(2)
    d["muni_ine"] = [match_with_aliases(p, m, idx) for p, m in zip(d.cp, d.muni)]
    if d.muni_ine.isna().any():
        print("Municipios del registro sin código INE:", sorted(d[d.muni_ine.isna()].muni.unique()))
    n = d.centro.map(norm)
    pub, priv = d.regimen.str.startswith("PÚB") | (d.regimen == "PÚBLICO"), d.regimen == "PRIVADO"

    tipo = pd.Series(pd.NA, index=d.index, dtype="object")
    csm = d.tipo_reg == "CENTROS DE SALUD MENTAL"
    tipo[pub & csm & n.str.contains("infantil")] = "usmi"
    tipo[pub & csm & n.str.contains("unidad de salud mental") & ~n.str.contains("infantil")] = "usm"
    tipo[pub & csm & n.str.contains("hospital de dia")] = "hospital_dia_sm"
    tipo[pub & csm & n.str.contains("centro dr esquerdo|centro de dia")] = "recurso_sm_otro"

    kw = r"psiquiatr|salud mental|salut mental|tdah|neuropediatr|neurologia pediatrica|neurodesenvolupament|neurodesarrollo|paidopsiq"
    excl_tipos = {"CONSULTAS DE OTROS PROFESIONALES SANITARIOS", "CLÍNICAS DENTALES", "ÓPTICAS", "CENTROS DE RECONOCIMIENTO"}
    cand = priv & n.str.contains(kw) & ~d.tipo_reg.isin(excl_tipos) & ~n.str.contains("trastornos alimentarios|alimentaria|autismo")
    tipo[cand & n.str.contains("neuropediatr|neurologia pediatrica|neurodesenvolupament|neurodesarrollo")] = "privada_neuropediatria"
    tipo[cand & tipo.isna()] = "privada_psiquiatria"
    tipo[priv & (d.tipo_reg == "HOSPITALES GENERALES")] = "hospital_privado"
    tipo[priv & (d.tipo_reg == "HOSPITALES DE SALUD MENTAL Y TRATAMIENTO DE TOXICOMANÍAS")] = "privada_internamiento"
    # Recursos residenciales / de internamiento: no son consultas donde se diagnostica y trata el TDAH
    tipo[cand & n.str.contains("casa de reposo|residencial|internamiento")] = "privada_internamiento"
    d["tipo"] = tipo
    d = d[d.tipo.notna()].copy()
    # Misma unidad registrada dos veces (p. ej. USM de Puçol en Puig y en Puçol): se conserva la del
    # municipio que da nombre a la unidad.
    d["_own"] = [norm(m).split()[0] in norm(c) for m, c in zip(d.muni, d.centro)]
    d = d.sort_values("_own", ascending=False).drop_duplicates(["tipo", "centro"]).drop(columns="_own")

    # Privacidad: fuera las consultas a nombre de una persona física (solo se cuenta cuántas).
    personal = d.tipo.str.startswith("privada") & d.centro.map(is_personal_name)
    # "Consultas" privadas: suelen ser la consulta de un solo profesional y su dirección lo identifica
    # indirectamente aunque el nombre sea genérico → se excluyen (solo centros, clínicas y hospitales).
    consulta = d.tipo.str.startswith("privada") & ~personal & d.centro.map(norm).str.contains(r"\bconsulta")
    excluidas = pd.concat([
        d[personal][["reg", "tipo", "muni_ine"]].assign(motivo="nombre de persona física", fuente="registro_2021"),
        d[consulta][["reg", "tipo", "muni_ine"]].assign(motivo="consulta individual", fuente="registro_2021")])
    d = d[~personal & ~consulta]

    lat, lon, how = [], [], []
    for _, r in d.iterrows():
        a, b, c = geocode(str(r.dir), str(r.muni), r.muni_ine, cache, ine_names.get(r.muni_ine, ""))
        lat.append(a); lon.append(b); how.append(c)
    d["lat"], d["lon"], d["geocod"] = lat, lon, how

    diana = {"privada_internamiento": "ambas", "usmi": "infantil", "usm": "adulto", "hospital_dia_sm": "adulto", "recurso_sm_otro": "adulto",
             "privada_neuropediatria": "infantil", "privada_psiquiatria": "ambas", "hospital_privado": "ambas"}
    df = pd.DataFrame({
        "src": "reg-" + d.reg, "nombre": d.centro, "tipo": d.tipo, "municipio": d.muni.str.title(),
        "direccion": d.dir.str.strip(), "lat": d.lat, "lon": d.lon, "_muni_ine": d.muni_ine,
        "ambito": d.regimen.map(lambda x: "privado" if x == "PRIVADO" else "publico"),
        "poblacion_diana": d.tipo.map(diana), "fuente": s["titulo"], "fuente_url": s["ficha"],
        "fecha_fuente": "2021", "fecha_consulta": s["fecha_descarga"], "verificado": "si",
        "precision_geo": d.geocod,
        "nota": d.geocod.map({"portal": "", "calle": "Coordenadas a nivel de calle.",
                              "municipio": "Coordenadas aproximadas (centro del municipio).",
                              "no_geocodificado": "Sin coordenadas (dirección no geocodificada)."})})
    df.loc[df.tipo == "hospital_privado", "nota"] = (
        df.loc[df.tipo == "hospital_privado", "nota"] + " Hospital privado: servicios de psiquiatría/neuropediatría no verificados.").str.strip()
    _pp = df.tipo.isin(["privada_psiquiatria", "privada_internamiento"])
    df.loc[_pp, "poblacion_diana"] = df.loc[_pp, "nombre"].map(
        lambda x: "infantil" if re.search(r"niñ|adolesc|infant|menores", x, re.I) else "ambas")
    return df, excluidas


# ------------------------------------------------------------------ C. OpenStreetMap
def osm(existing: gpd.GeoDataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    s = SOURCES.get("osm_psiquiatria")
    p = RAW / "osm/overpass_psiquiatria_cv.json"
    if not s or not p.exists():
        return pd.DataFrame(), pd.DataFrame()
    el = json.loads(p.read_text())["elements"]
    rows = []
    for e in el:
        t = e.get("tags", {})
        name = t.get("name")
        lat = e.get("lat") or e.get("center", {}).get("lat")
        lon = e.get("lon") or e.get("center", {}).get("lon")
        if not name or lat is None:
            continue
        if t.get("healthcare") in {"hospital"} or t.get("amenity") == "hospital":
            continue  # hospitales ya cubiertos por fuentes oficiales
        spec = t.get("healthcare:speciality", "")
        nn = norm(name)
        if ("salud mental" in nn or "salut mental" in nn) and not re.search(r"clinica|centro|institut", nn) \
                and t.get("operator:type", "") != "private":
            continue  # USM públicas: ya vienen del registro oficial
        tipo = "privada_neuropediatria" if re.search(r"neuroped|paediatric_neurology", nn + spec) else "privada_psiquiatria"
        rows.append({"src": f"osm-{e['type']}{e['id']}", "nombre": name, "tipo": tipo, "lat": round(lat, 6),
                     "lon": round(lon, 6), "municipio": t.get("addr:city", ""),
                     "direccion": " ".join(x for x in [t.get("addr:street", ""), t.get("addr:housenumber", "")] if x),
                     "ambito": "privado", "poblacion_diana": "infantil" if "child" in spec or re.search(r"infant|niñ|adolesc", name, re.I) else "ambas",
                     "fuente": s["titulo"], "fuente_url": f"https://www.openstreetmap.org/{e['type']}/{e['id']}",
                     "fecha_fuente": "OSM " + s["fecha_descarga"], "fecha_consulta": s["fecha_descarga"], "verificado": "no",
                     "nota": "Fuente colaborativa (OSM): confirmar actividad y especialidad."})
    o = pd.DataFrame(rows)
    if o.empty:
        return o, pd.DataFrame()
    personal = o.nombre.map(is_personal_name)
    consulta = ~personal & o.nombre.map(norm).str.contains(r"\bconsulta")
    excl = pd.concat([o[personal][["src", "tipo"]].assign(motivo="nombre de persona física", fuente="osm"),
                      o[consulta][["src", "tipo"]].assign(motivo="consulta individual", fuente="osm")])
    o = o[~personal & ~consulta]
    # Deduplicar frente al registro: < 120 m y algún token significativo en común
    go = gpd.GeoDataFrame(o, geometry=gpd.points_from_xy(o.lon, o.lat), crs=4326).to_crs(25830)
    ex = existing.to_crs(25830)
    keep = []
    for i, r in go.iterrows():
        near = ex[ex.distance(r.geometry) < 120]
        toks = set(norm(r.nombre).split()) - GENERIC
        dup = any(toks & (set(norm(x).split()) - GENERIC) for x in near.nombre) or (len(near) and not toks)
        keep.append(not dup)
    return o[keep], excl


# ------------------------------------------------------------------ main
def main() -> None:
    cache = json.loads(CACHE_PATH.read_text()) if CACHE_PATH.exists() else {}
    a = hospitales_publicos()
    b, excl_b = registro(cache)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False))

    ab = pd.concat([a, b], ignore_index=True)
    g_ab = ab.dropna(subset=["lat"])
    g_ab = gpd.GeoDataFrame(g_ab, geometry=gpd.points_from_xy(g_ab.lon, g_ab.lat), crs=4326)
    c, excl_c = osm(g_ab)
    allc = pd.concat([ab, c], ignore_index=True)

    # Departamento por punto en polígono; sin coordenadas → departamento dominante del municipio
    deps = gpd.read_file(OUT / "departamentos.geojson")[["dpto", "departamento", "geometry"]]
    has = allc.lat.notna()
    pts = gpd.GeoDataFrame(allc[has], geometry=gpd.points_from_xy(allc[has].lon, allc[has].lat), crs=4326)
    j = gpd.sjoin(pts, deps, how="left", predicate="within")[["dpto", "departamento"]]
    j = j[~j.index.duplicated()]
    allc.loc[has, "dpto"] = j.dpto
    md = pd.read_csv(OUT / "municipio_departamento.csv", dtype={"muni_ine": str, "dpto_adulto": str})
    dom = md.sort_values("pct_poblacion_municipio", ascending=False).drop_duplicates("muni_ine").set_index("muni_ine").dpto_adulto
    miss = allc.dpto.isna() & allc.get("_muni_ine").notna()
    allc.loc[miss, "dpto"] = allc.loc[miss, "_muni_ine"].map(dom)
    allc.loc[miss, "nota"] = (allc.loc[miss, "nota"] + " Departamento asignado por municipio.").str.strip()
    allc = allc[allc.dpto.notna()].copy()  # fuera de la Comunitat (no debería ocurrir)
    allc["departamento"] = allc.dpto.map(deps.set_index("dpto").departamento)

    # Hospitales públicos: manda el departamento OFICIAL al que dan servicio (capa SVS), no el polígono
    # donde está el edificio (La Fe y Arnau de Vilanova están físicamente en otro departamento).
    svs = allc._dpto_svs.notna() & (allc._dpto_svs != "00")
    mism = allc[svs & (allc._dpto_svs != allc.dpto)].copy()
    allc.loc[svs, "dpto"] = allc.loc[svs, "_dpto_svs"]
    allc["departamento"] = allc.dpto.map(deps.set_index("dpto").departamento)

    prefix = {"hospital_publico": "HP", "hospital_privado": "HV", "neuropediatria": "NP", "usmi": "UI", "usm": "UA",
              "hospital_dia_sm": "HD", "hospital_psiquiatrico": "PQ", "recurso_sm_otro": "SM",
              "privada_psiquiatria": "PP", "privada_neuropediatria": "PN", "privada_internamiento": "PI"}
    import yaml
    manual = set(yaml.safe_load((ROOT / "config/exclusiones_privacidad.yaml").read_text())["excluir_src_id"])
    excl_m = allc[allc.src.isin(manual)][["src", "tipo"]].assign(motivo="nombre de persona física (revisión manual)", fuente="manual")
    allc = allc[~allc.src.isin(manual)]
    allc = allc.sort_values(["tipo", "dpto", "nombre"]).reset_index(drop=True)
    # Id ESTABLE: prefijo de tipo + identificador de la fuente (no depende del orden ni del departamento),
    # para que la capa privada relaciones.csv siga apuntando a la misma cuenta si cambian los datos.
    def _suffix(src: str) -> str:
        kind, rest = src.split("-", 1)
        rest = rest.replace("-np", "")
        if kind == "osm":
            return "O" + rest[0].upper() + re.sub(r"\D", "", rest)
        return {"reg": "R", "svs": "S"}[kind] + rest
    allc["id"] = allc.tipo.map(prefix) + "-" + allc.src.map(_suffix)
    assert allc.id.is_unique, "ids no únicos"
    allc["src_id"] = allc.src
    allc["precision_geo"] = allc.precision_geo.fillna("fuente")  # coordenadas de la propia fuente (SVS / OSM)
    allc[COLS + ["src_id"]].to_csv(OUT / "cuentas.csv", index=False)

    excl = pd.concat([excl_b, excl_c, excl_m], ignore_index=True)
    # Solo se guardan recuentos agregados (sin nombres ni direcciones) para la metodología.
    excl.groupby(["fuente", "motivo", "tipo"]).size().rename("n").reset_index().to_csv(OUT / "cuentas_excluidas_privacidad.csv", index=False)

    rep = {
        "fecha": date.today().isoformat(),
        "n_cuentas": int(len(allc)),
        "por_tipo": allc.tipo.value_counts().to_dict(),
        "pct_verificado": round(100 * (allc.verificado == "si").mean(), 1),
        "precision_geocodificacion": allc.precision_geo.fillna("fuente").value_counts().to_dict(),
        "excluidas_por_privacidad": int(len(excl)),
        "hospitales_ubicados_fuera_de_su_departamento": mism[["nombre", "_dpto_svs", "dpto"]].rename(columns={"_dpto_svs": "dpto_oficial", "dpto": "dpto_poligono"}).to_dict("records"),
        "departamentos_sin_usmi_registrada": sorted(set(deps.dpto) - set(allc[allc.tipo == "usmi"].dpto)),
        "departamentos_sin_usm_registrada": sorted(set(deps.dpto) - set(allc[allc.tipo == "usm"].dpto)),
    }
    (OUT / "validacion_fase2.json").write_text(json.dumps(rep, ensure_ascii=False, indent=2))
    print(json.dumps(rep, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
