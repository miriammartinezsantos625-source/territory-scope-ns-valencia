"""Emparejamiento de nombres de municipio (formas bilingües, artículos) con el código INE."""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

ARTICLES = {"la", "el", "l", "les", "els", "los", "las"}


def _variants(name: str) -> set[str]:
    out = set()
    for part in re.split(r"/", str(name)):
        s = unicodedata.normalize("NFKD", part).encode("ascii", "ignore").decode().lower()
        s = re.sub(r"[^a-z ]+", " ", s)
        toks = [t for t in s.split() if t not in ARTICLES]
        if toks:
            out.add("".join(toks))
    return out


def build_index(muni: pd.DataFrame, code_col: str = "muni_ine", name_col: str = "municipio") -> dict:
    idx: dict[tuple[str, str], str] = {}
    for code, name in zip(muni[code_col], muni[name_col]):
        for v in _variants(name):
            idx[(code[:2], v)] = code
    return idx


def match(prov: str, name: str, idx: dict) -> str | None:
    for v in _variants(name):
        if (prov, v) in idx:
            return idx[(prov, v)]
    return None


# Denominaciones antiguas o castellanizadas del Registro de centros → código INE
ALIASES = {
    ("03", "adsubia"): "03001", ("03", "alcocerdeplanes"): "03007", ("46", "alfarp"): "46026",
    ("46", "algimiadealfara"): "46030", ("12", "benasal"): "12026", ("46", "benisano"): "46067",
    ("46", "benisuera"): "46069", ("12", "benlloch"): "12029", ("03", "facheca"): "03067",
    ("12", "herbes"): "12068", ("46", "puig"): "46204", ("12", "sarratella"): "12103",
    ("46", "villanuevadecastellon"): "46257", ("12", "vistabelladelmaestrazgo"): "12139",
}


def match_with_aliases(prov: str, name: str, idx: dict) -> str | None:
    code = match(prov, name, idx)
    if code:
        return code
    for v in _variants(name):
        if (prov, v) in ALIASES:
            return ALIASES[(prov, v)]
    return None
