"""Fase 2 · Lista de lo que NO se ha podido confirmar con fuentes oficiales (para revisión manual)."""
from pathlib import Path

import pandas as pd

P = Path(__file__).resolve().parents[1] / "data" / "processed"
c = pd.read_csv(P / "cuentas.csv", dtype={"dpto": str})
deps = pd.read_csv(P / "poblacion_departamento.csv", dtype={"dpto": str})[["dpto", "departamento"]]

rows = []
for _, r in c[c.verificado == "no"].iterrows():
    rows.append({"tipo_pendiente": "cuenta_no_verificada", "dpto": r.dpto, "departamento": r.departamento,
                 "cuenta_id": r.id, "detalle": r.nota})
for tipo, label in [("usmi", "USMI"), ("usm", "USM de adultos")]:
    for _, d in deps[~deps.dpto.isin(c[c.tipo == tipo].dpto)].iterrows():
        rows.append({"tipo_pendiente": f"departamento_sin_{tipo}_en_registro", "dpto": d.dpto,
                     "departamento": d.departamento, "cuenta_id": "",
                     "detalle": f"No consta {label} en el Registro de centros 2021. Puede estar integrada en un centro "
                                f"de salud o atenderse desde otro departamento: confirmar en la web del departamento. "
                                f"No se crea ninguna cuenta hasta confirmarlo."})
for _, r in c[c.precision_geo == "municipio"].iterrows():
    rows.append({"tipo_pendiente": "coordenadas_aproximadas", "dpto": r.dpto, "departamento": r.departamento,
                 "cuenta_id": r.id, "detalle": "Geocodificada al centro del municipio; revisar ubicación exacta."})
out = pd.DataFrame(rows).sort_values(["tipo_pendiente", "dpto"])
out.to_csv(P / "pendientes_verificacion.csv", index=False)
print(out.tipo_pendiente.value_counts().to_string())
