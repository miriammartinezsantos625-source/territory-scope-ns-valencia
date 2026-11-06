"""Fase 2 · Descarga reproducible de fuentes de recursos asistenciales.

- GVA · Red de hospitales públicos del SVS (WFS ICV, con departamento y coordenadas)
- GVA · Registro de centros, servicios y establecimientos sanitarios (2021, último publicado)
- OpenStreetMap · centros de psiquiatría / salud mental / neuropediatría (Overpass API, ODbL)
Añade las entradas a data/raw/SOURCES.json.
"""
from __future__ import annotations

import hashlib
import json
import time
from datetime import date
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
UA = {"User-Agent": "territory-scope-ns-valencia/0.1 (public-data research prototype)"}

OVERPASS_QUERY = (
    '[out:json][timeout:180];area["ISO3166-2"="ES-VC"]->.a;('
    'nwr(area.a)["healthcare:speciality"~"psychiatry|child_psychiatry|paediatric_neurology"];'
    'nwr(area.a)["healthcare"]["name"~"psiquiatr|salud mental|salut mental|TDAH|neuropediatr|paidopsiq",i];'
    'nwr(area.a)["amenity"~"clinic|doctors"]["name"~"psiquiatr|salud mental|salut mental|TDAH|neuropediatr|paidopsiq",i];'
    ');out center tags;'
)

SOURCES = [
    {"id": "gva_hospitales_svs", "path": "gva/hospitales_svs.csv",
     "url": "https://terramapas.icv.gva.es/15_SistemaValencianoSalud?request=GetFeature&service=WFS&version=2.0.0"
            "&typename=CentrosSanitarios.Hospitales&outputformat=csv",
     "titulo": "Sistema Valenciano de Salud. Centros sanitarios: Hospitales (red pública)",
     "editor": "Conselleria de Sanitat · Institut Cartogràfic Valencià (CC BY 4.0)",
     "ficha": "https://dadesobertes.gva.es/es/dataset/sistema-valenciano-de-salud-centros-sanitarios-hospitales"},
    {"id": "gva_registro_centros_2021", "path": "gva/centros_sanitarios_2021.csv",
     "url": "https://dadesobertes.gva.es/dataset/c57f25f1-e7ea-4052-8467-09af3f574148/resource/"
            "bf116aea-6bf5-461b-97cd-ecd974a20310/download/centros-sanitarios_2021.csv",
     "titulo": "Registro de centros, servicios y establecimientos sanitarios de la Comunitat Valenciana 2021",
     "editor": "Conselleria de Sanitat · Dades Obertes GVA (CC BY 4.0)",
     "ficha": "https://dadesobertes.gva.es/es/dataset/san-reg-centros-2021"},
]


def fetch(url: str, data: dict | None = None, tries: int = 6) -> bytes:
    wait = 15
    for i in range(tries):
        r = requests.post(url, data=data, headers=UA, timeout=300) if data else requests.get(url, headers=UA, timeout=300)
        if r.ok and (not data or r.content.lstrip().startswith(b"{")):
            return r.content
        print(f"  intento {i + 1} fallido ({r.status_code}); reintento en {wait}s")
        time.sleep(wait)
        wait *= 2
    raise RuntimeError(f"No se pudo descargar {url}")


def main() -> None:
    reg_path = RAW / "SOURCES.json"
    registry = {s["id"]: s for s in json.loads(reg_path.read_text())} if reg_path.exists() else {}
    items = [(s, None) for s in SOURCES] + [({
        "id": "osm_psiquiatria", "path": "osm/overpass_psiquiatria_cv.json",
        "url": "https://overpass-api.de/api/interpreter", "query": OVERPASS_QUERY,
        "titulo": "OpenStreetMap · centros con especialidad psiquiatría / salud mental / neuropediatría en la CV",
        "editor": "© colaboradores de OpenStreetMap (ODbL)", "ficha": "https://www.openstreetmap.org/copyright"},
        {"data": OVERPASS_QUERY})]
    for s, post in items:
        print(f"↓ {s['id']}")
        content = fetch(s["url"], post)
        dest = RAW / s["path"]
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(content)
        registry[s["id"]] = {**s, "fecha_descarga": date.today().isoformat(), "bytes": len(content),
                             "sha256": hashlib.sha256(content).hexdigest()}
    reg_path.write_text(json.dumps(list(registry.values()), ensure_ascii=False, indent=2))
    print("OK")


if __name__ == "__main__":
    main()
