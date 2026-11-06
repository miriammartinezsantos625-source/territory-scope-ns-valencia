"""Fase 1 · Descarga reproducible de las fuentes públicas del mapa sanitario y la población.

Uso:  python scripts/01_download_phase1.py
Escribe los ficheros originales en data/raw/ y un registro de fuentes en data/raw/SOURCES.json
(URL, fecha de descarga, tamaño y hash) para que cada cifra de la app sea trazable.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SOURCES = [
    {
        "id": "gva_departamentos",
        "path": "gva/ca_departamentos_20261005.geojson",
        "url": "https://dadesobertes.gva.es/dataset/ff6f20ee-aee6-4def-9f9b-451610ed47f9/resource/"
               "cacd9478-1ced-4c1b-a378-30aeee992f6c/download/ca_departamentos_20261005.geojson",
        "titulo": "Capa de departamentos de salud de la Comunitat Valenciana (versión 05-10-2026)",
        "editor": "Conselleria de Sanitat · Dades Obertes GVA (CC BY 4.0)",
        "ficha": "https://dadesobertes.gva.es/es/dataset/sanidad-sip-departamentos-salud",
    },
    {
        "id": "gva_mapa_sanitario",
        "path": "gva/mapa_sanitario.csv",
        "url": "https://dadesobertes.gva.es/dataset/0f78e3f9-6137-4ece-aa3f-be951c35de69/resource/"
               "34437ccd-288e-41cc-9a95-ea29a01588fd/download/"
               "informacion-del-mapa-sanitario-correspondiente-a-la-comunitat-valenciana.csv",
        "titulo": "Información del mapa sanitario de la Comunitat Valenciana (callejero: tramo de vía → "
                  "sección censal → zona básica y departamento, adulto y pediátrico)",
        "editor": "Conselleria de Sanitat · Dades Obertes GVA (CC BY 4.0)",
        "ficha": "https://dadesobertes.gva.es/es/dataset/sanidad-sip",
    },
    {
        "id": "gva_relacion_dep_zona_muni_2020",
        "path": "gva/sip_relacion_depzonamuni_cv.csv",
        "url": "https://dadesobertes.gva.es/dataset/8918e103-a69a-43e6-a9ad-42e7beebed9b/resource/"
               "685c9c39-064d-4278-ba47-08ac19b4f1f1/download/sip_relacion_depzonamuni_cv.csv",
        "titulo": "Relación departamento – zona básica – municipio (06-05-2020). Solo para contraste.",
        "editor": "Conselleria de Sanitat · Dades Obertes GVA (CC BY 4.0)",
        "ficha": "https://dadesobertes.gva.es/es/dataset/datos-de-departamentos-de-salud-zonas-basicas-y-"
                 "municipios-de-la-comunitat-valenciana",
    },
]

# INE · Censo Anual de Población: población por sección censal, sexo y edad (grupos quinquenales)
for prov, tid in [("Alicante/Alacant", 69105), ("Castellón/Castelló", 69153), ("Valencia/València", 69277)]:
    SOURCES.append({
        "id": f"ine_censo_anual_{tid}",
        "path": f"ine/censo_anual_seccion_edad_{tid}.csv",
        "url": f"https://www.ine.es/jaxiT3/files/t/es/csv_bdsc/{tid}.csv",
        "titulo": f"INE · Censo Anual de Población. Población por sexo y edad (grupos quinquenales) "
                  f"por sección censal · {prov}",
        "editor": "Instituto Nacional de Estadística",
        "ficha": f"https://www.ine.es/jaxiT3/Tabla.htm?t={tid}",
    })


def main() -> None:
    registry = []
    for s in SOURCES:
        dest = RAW / s["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        print(f"↓ {s['id']}")
        r = requests.get(s["url"], timeout=600)
        r.raise_for_status()
        dest.write_bytes(r.content)
        registry.append({**s, "fecha_descarga": date.today().isoformat(), "bytes": len(r.content),
                         "sha256": hashlib.sha256(r.content).hexdigest()})
    (RAW / "SOURCES.json").write_text(json.dumps(registry, ensure_ascii=False, indent=2))
    print(f"OK · {len(registry)} fuentes registradas en data/raw/SOURCES.json")


if __name__ == "__main__":
    main()
