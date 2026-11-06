"""Plan de visitas: ciclo por meses agrupando cuentas por departamento para reducir desplazamientos.

Reglas
  · Frecuencia por segmento (visitas/mes): A = 1 (mensual), B = 0,5 (bimensual), C = 0,33 (trimestral).
    Periodo = round(1 / frecuencia) meses. Cada cuenta se reparte en un mes de su periodo
    (desfase escalonado por ranking) para equilibrar la carga mensual.
  · Capacidad mensual = visitas/día × días de campo/mes. Si un mes supera la capacidad, se quedan
    fuera las visitas de menor score (primero C, luego B) y se listan como "no cubiertas".
  · Orden de ruta: departamentos ordenados por vecino más próximo (centroides) partiendo del
    departamento con más visitas; dentro de cada día se agrupan visitas del mismo departamento.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd


def department_route(geo, start: str | None = None) -> list[str]:
    """Orden de departamentos por vecino más próximo sobre centroides (proyección métrica)."""
    c = geo.to_crs(25830).set_index("dpto").geometry.centroid
    pts = {k: (p.x, p.y) for k, p in c.items()}
    left = set(pts)
    cur = start if start in pts else sorted(pts)[0]
    route = [cur]
    left.remove(cur)
    while left:
        x, y = pts[cur]
        cur = min(left, key=lambda k: (pts[k][0] - x) ** 2 + (pts[k][1] - y) ** 2)
        route.append(cur)
        left.remove(cur)
    return route


def build_plan(scored: pd.DataFrame, route: list[str], visitas_dia: int = 6, dias_mes: int = 16,
               frecuencia: dict | None = None, meses: int = 3) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Devuelve (plan, resumen_mensual, no_cubiertas)."""
    frecuencia = frecuencia or {"A": 1.0, "B": 0.5, "C": 1 / 3}
    capacidad = int(visitas_dia * dias_mes)
    a = scored.sort_values("score", ascending=False).copy()
    a["periodo"] = a.segmento.map(lambda s: max(1, int(round(1 / frecuencia[s]))) if frecuencia[s] > 0 else 0)
    a = a[a.periodo > 0]
    a["desfase"] = a.groupby("segmento").cumcount() % a.periodo
    orden_dpto = {d: i for i, d in enumerate(route)}

    filas, fuera, resumen = [], [], []
    for m in range(1, meses + 1):
        mes = a[((m - 1) % a.periodo) == a.desfase].copy()
        demanda = len(mes)
        if demanda > capacidad:
            mes = mes.sort_values(["segmento", "score"], ascending=[True, False])
            fuera.append(mes.iloc[capacidad:].assign(mes=m))
            mes = mes.iloc[:capacidad]
        mes["_r"] = mes.dpto.map(orden_dpto)
        mes = mes.sort_values(["_r", "segmento", "score"], ascending=[True, True, False]).reset_index(drop=True)
        mes["mes"] = m
        mes["dia"] = mes.index // visitas_dia + 1
        mes["orden_en_dia"] = mes.index % visitas_dia + 1
        filas.append(mes)
        resumen.append({"mes": m, "visitas_planificadas": len(mes), "demanda": demanda, "capacidad": capacidad,
                        "dias_usados": int(math.ceil(len(mes) / visitas_dia)) if len(mes) else 0,
                        "departamentos": mes.dpto.nunique(),
                        "A": int((mes.segmento == "A").sum()), "B": int((mes.segmento == "B").sum()),
                        "C": int((mes.segmento == "C").sum())})

    cols = ["mes", "dia", "orden_en_dia", "dpto", "departamento", "id", "nombre", "tipo", "ambito",
            "municipio", "segmento", "score"]
    plan = pd.concat(filas, ignore_index=True)[cols] if filas else pd.DataFrame(columns=cols)
    no_cub = pd.concat(fuera, ignore_index=True)[["mes"] + cols[3:]] if fuera else pd.DataFrame(columns=["mes"] + cols[3:])
    return plan, pd.DataFrame(resumen), no_cub


def coverage(plan: pd.DataFrame, scored: pd.DataFrame) -> pd.DataFrame:
    """Visitas por cuenta en el horizonte frente a las esperadas por su segmento."""
    v = plan.groupby("id").size().rename("visitas")
    out = scored[["id", "segmento"]].assign(visitas=lambda d: d.id.map(v).fillna(0).astype(int))
    return out.groupby("segmento").agg(cuentas=("id", "size"), cuentas_visitadas=("visitas", lambda s: int((s > 0).sum())),
                                       visitas=("visitas", "sum")).reset_index()
