"""Carga de datos procesados y configuración por área terapéutica."""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import yaml

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
PRIVATE = ROOT / "data" / "private"


def load_config(area: str = "tdah") -> dict:
    return yaml.safe_load((ROOT / "config" / "areas" / f"{area}.yaml").read_text())


def available_areas() -> list[str]:
    return sorted(p.stem for p in (ROOT / "config" / "areas").glob("*.yaml"))


def load_population() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "poblacion_departamento.csv", dtype={"dpto": str})


def load_accounts() -> pd.DataFrame:
    return pd.read_csv(PROCESSED / "cuentas.csv", dtype={"dpto": str})


def load_departments_geo():
    import geopandas as gpd
    return gpd.read_file(PROCESSED / "departamentos.geojson")


YES = {"si", "s", "yes", "y", "1", "true", "verdadero", "x"}
NO = {"no", "n", "0", "false", "falso", ""}


def _norm_flag(v) -> str | None:
    import unicodedata
    t = unicodedata.normalize("NFKD", str(v)).encode("ascii", "ignore").decode().strip().lower()
    return "si" if t in YES else ("no" if t in NO else None)


def clean_relationships(r: pd.DataFrame) -> pd.DataFrame:
    """Normaliza la capa privada: id sin espacios, relacion → si/no, duplicados (gana "si").

    Devuelve un DataFrame (id_cuenta, relacion) con estadísticas en `.attrs`.
    """
    r = r.rename(columns=lambda c: str(c).strip().lower())
    if not {"id_cuenta", "relacion"} <= set(r.columns):
        raise ValueError("relaciones.csv debe tener las columnas id_cuenta y relacion")
    r = r[["id_cuenta", "relacion"]].copy()
    r["id_cuenta"] = r.id_cuenta.astype(str).str.strip().str.upper()
    r["relacion"] = r.relacion.map(_norm_flag)
    stats = {"filas": int(len(r)), "valores_no_reconocidos": int(r.relacion.isna().sum())}
    r = r.dropna(subset=["relacion"])
    stats["ids_duplicados"] = int(r.id_cuenta.duplicated().sum())
    r = (r.assign(_si=r.relacion.eq("si")).groupby("id_cuenta", as_index=False)._si.any()
         .assign(relacion=lambda d: d._si.map({True: "si", False: "no"})).drop(columns="_si"))
    r.attrs.update(stats)
    return r


def load_relationships() -> pd.DataFrame | None:
    """Capa privada opcional (NO va al repositorio). Columnas: id_cuenta, relacion (si/no)."""
    p = PRIVATE / "relaciones.csv"
    if not p.exists():
        return None
    return clean_relationships(pd.read_csv(p, dtype=str, keep_default_na=False))
