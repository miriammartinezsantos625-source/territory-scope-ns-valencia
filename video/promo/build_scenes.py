"""Genera las escenas HyperFrames del vídeo promocional a partir de una especificación de planos.

Las escenas resultantes (compositions/*.html e index.html) son HTML normal y editable en Studio;
este script solo evita escribir a mano cientos de números (cámara, cursor, subrayados, audio).
Coordenadas: píxeles CSS del viewport 1920x1080 de la app (las capturas son 2x).
Uso: python build_scenes.py
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
W, H = 1920, 1080
CLICK_LEAD = 0.04          # el pico del clic llega ~0,07 s tras el inicio del archivo → 1 frame tras la imagen
WHOOSH_LEAD = 0.12

YELLOW = "rgba(255, 214, 10, 0.50)"


# ------------------------------------------------------------------ cámara
def cam_for(region):
    """region = 'full' o (x0, y0, x1, y1) → (x, y, s) con transform-origin 0 0, sin salirse del plano."""
    if region == "full":
        return (0.0, 0.0, 1.0)
    x0, y0, x1, y1 = region
    s = min(W / (x1 - x0), H / (y1 - y0))
    s = max(1.0, min(s, 2.2))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    x, y = W / 2 - cx * s, H / 2 - cy * s
    x = min(0.0, max(W - W * s, x))
    y = min(0.0, max(H - H * s, y))
    return (round(x, 1), round(y, 1), round(s, 4))


class Scene:
    def __init__(self, sid: str, dur: float, title: str):
        self.id, self.dur, self.title = sid, dur, title
        self.states, self.cams, self.marks, self.moves, self.clicks = [], [], [], [], []
        self.captions, self.pops, self.sounds, self.cursor_show = [], [], [], []
        self.cam0 = (0.0, 0.0, 1.0)

    # API de planos -------------------------------------------------
    def state(self, img, t0, t1):
        self.states.append((img, t0, t1))

    def cam(self, t, region, d=0.7, ease="power2.inOut"):
        self.cams.append((t, d, cam_for(region), ease))

    def mark(self, t, rect, until=None, pad=4):
        x, y, w, h = rect
        self.marks.append((t, (x - pad, y - pad, w + 2 * pad, h + 2 * pad), until if until is not None else self.dur))

    def cursor(self, t_in, t_out, start_xy):
        self.cursor_show.append((t_in, t_out, start_xy))

    def move(self, t, xy, d=0.6):
        self.moves.append((t, d, xy))

    def click(self, t, pop=True, whoosh=False):
        self.clicks.append(t)
        self.sounds.append(("click", t - CLICK_LEAD))
        if whoosh:
            self.sounds.append(("whoosh", t + 0.02 - WHOOSH_LEAD))
        if pop:
            self.pops.append(t + 1 / 30)

    def caption(self, t0, t1, text):
        self.captions.append((t0, t1, text))

    # evaluación de la cámara en un instante (el cursor solo se mueve con la cámara quieta)
    def cam_at(self, t):
        cur = self.cam0
        for (t0, d, c, _e) in sorted(self.cams):
            if t >= t0 + d - 1e-6:
                cur = c
            elif t > t0:
                f = (t - t0) / d
                cur = tuple(a + (b - a) * f for a, b in zip(cur, c))
        return cur

    def to_screen(self, t, xy):
        x, y, s = self.cam_at(t)
        return (round(x + xy[0] * s, 1), round(y + xy[1] * s, 1))

    # HTML ----------------------------------------------------------
    def html(self) -> str:
        p = self.id
        imgs = "\n".join(
            f'        <img id="{p}-img{i}" class="clip shot" src="assets/screens/{img}.png" alt="" '
            f'data-start="{t0}" data-duration="{round(t1 - t0, 3)}" data-track-index="{i + 1}" />'
            for i, (img, t0, t1) in enumerate(self.states))
        marks = "\n".join(
            f'        <div id="{p}-mk{i}" class="mark" style="left:{r[0]}px;top:{r[1]}px;width:{r[2]}px;height:{r[3]}px"></div>'
            for i, (_t, r, _u) in enumerate(self.marks))
        caps = "\n".join(
            f'    <div id="{p}-cap{i}" class="cap"><span>{txt}</span></div>' for i, (_a, _b, txt) in enumerate(self.captions))

        js = [f'const tl = gsap.timeline({{ paused: true }});',
              f'tl.set("#{p}-cam", {{ x: {self.cam0[0]}, y: {self.cam0[1]}, scale: {self.cam0[2]} }}, 0);',
              f'tl.set("#{p}-pop", {{ scale: 1 }}, 0);']
        for (t, d, (x, y, s), e) in sorted(self.cams):
            js.append(f'tl.to("#{p}-cam", {{ x: {x}, y: {y}, scale: {s}, duration: {d}, ease: "{e}" }}, {t});')
        for t in self.pops:
            js.append(f'tl.fromTo("#{p}-pop", {{ scale: 1.03 }}, {{ scale: 1, duration: 0.35, ease: "expo.out" }}, {round(t, 3)});')
        for i, (t, _r, until) in enumerate(self.marks):
            js.append(f'tl.fromTo("#{p}-mk{i}", {{ scaleX: 0, opacity: 1 }}, {{ scaleX: 1, duration: 0.35, ease: "power2.out" }}, {t});')
            if until < self.dur:
                js.append(f'tl.to("#{p}-mk{i}", {{ opacity: 0, duration: 0.2, ease: "power1.out" }}, {until});')
        # cursor
        js.append(f'tl.set("#{p}-cur", {{ opacity: 0 }}, 0);')
        for (t_in, t_out, xy) in self.cursor_show:
            sx, sy = self.to_screen(t_in, xy)
            js.append(f'tl.set("#{p}-cur", {{ x: {sx}, y: {sy} }}, {t_in});')
            js.append(f'tl.to("#{p}-cur", {{ opacity: 1, duration: 0.15 }}, {t_in});')
            js.append(f'tl.to("#{p}-cur", {{ opacity: 0, duration: 0.2 }}, {t_out});')
        for (t, d, xy) in sorted(self.moves):
            sx, sy = self.to_screen(t + d, xy)
            js.append(f'tl.to("#{p}-cur", {{ x: {sx}, y: {sy}, duration: {d}, ease: "power3.inOut" }}, {t});')
        for t in self.clicks:
            js.append(f'tl.to("#{p}-curi", {{ scale: 0.82, duration: 0.06, ease: "power2.out" }}, {round(t - 0.06, 3)});')
            js.append(f'tl.to("#{p}-curi", {{ scale: 1, duration: 0.14, ease: "power2.out" }}, {t});')
        for i, (a, b, _txt) in enumerate(self.captions):
            js.append(f'tl.fromTo("#{p}-cap{i}", {{ opacity: 0, filter: "blur(8px)" }}, '
                      f'{{ opacity: 1, filter: "blur(0px)", duration: 0.18, ease: "power4.out" }}, {a});')
            js.append(f'tl.to("#{p}-cap{i}", {{ opacity: 0, filter: "blur(6px)", duration: 0.15, ease: "power2.in" }}, {b});')
        js.append(f'window.__timelines["{p}"] = tl;')
        script = "\n    ".join(js)

        return f'''<template>
  <style>
    #root {{ position: absolute; inset: 0; overflow: hidden; background: #F5F7FB; font-family: "Inter", sans-serif; }}
    #root .pop {{ position: absolute; inset: 0; transform-origin: 50% 50%; }}
    #root .cam {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }}
    #root .shot {{ position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; object-fit: cover; }}
    #root .mark {{ position: absolute; background: {YELLOW}; mix-blend-mode: multiply; border-radius: 4px;
                  transform-origin: 0 50%; opacity: 0; z-index: 50; }}
    #root .cursor {{ position: absolute; left: 0; top: 0; width: 54px; height: 54px; z-index: 90; opacity: 0; }}
    #root .cursor .ci {{ width: 54px; height: 54px; transform-origin: 6px 4px; }}
    #root .cap {{ position: absolute; left: 192px; bottom: 132px; z-index: 80; opacity: 0; }}
    #root .cap span {{ display: inline-block; background: rgba(11, 37, 69, 0.92); color: #fff; font-weight: 700;
                      font-size: 40px; letter-spacing: -0.01em; padding: 16px 28px; border-radius: 10px;
                      box-shadow: 0 10px 30px rgba(11, 37, 69, 0.25); }}
  </style>
  <div id="root" data-composition-id="{p}" data-width="1920" data-height="1080" data-start="0" data-duration="{self.dur}">
    <div id="{p}-pop" class="pop">
      <div id="{p}-cam" class="cam" data-layout-allow-overflow>
{imgs}
{marks}
      </div>
    </div>
{caps}
    <div id="{p}-cur" class="cursor" data-layout-ignore>
      <svg id="{p}-curi" class="ci" viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 2.5 L5 19.5 L9.4 15.4 L12.3 21.6 L15.2 20.3 L12.4 14.2 L18.6 14.2 Z"
              fill="#111827" stroke="#ffffff" stroke-width="1.4" stroke-linejoin="round"/>
      </svg>
    </div>
  </div>
  <script>
    {script}
  </script>
</template>
'''


def ctr(r):
    x, y, w, h = r
    return (x + w / 2, y + h / 2)


boxes = json.loads((ROOT / "assets/screens/boxes.json").read_text())
B1 = boxes["01_map"]
TABS = {t["t"]: (t["x"], t["y"], t["w"], t["h"]) for t in B1["tabs"]}
scenes: list[Scene] = []

# ---------------------------------------------------------------- S1 · mapa (9,6 s)
s = Scene("s1map", 9.6, "Mapa")
s.state("01_map", 0, 4.45); s.state("02_map_dropdown", 4.45, 5.93); s.state("03_map_pacientes", 5.93, 9.6)
s.mark(0.45, (746, 320, 92, 34), until=1.9)                      # 44.629 pacientes 6–17
s.mark(0.65, (1004, 320, 92, 34), until=1.9)                     # 85.544 pacientes 18–64
s.caption(0.3, 1.9, "Pacientes TDAH estimados")
s.cam(1.7, (470, 480, 1760, 1080), d=0.8)                        # mapa + panel derecho
ins = B1["insights"][0]
s.mark(2.7, (ins["x"] + 10, ins["y"] + 8, ins["w"] - 20, ins["h"] - 16), until=4.3)
s.caption(2.6, 4.2, "¿Dónde falta atención?")
sel = boxes["02_map_dropdown"]["select"]
s.cursor(3.5, 6.6, (1780, 760)); s.move(3.55, ctr((sel["x"], sel["y"], sel["w"], sel["h"])), d=0.75)
s.click(4.45)
opt = [o for o in boxes["02_map_dropdown"]["options"] if "Pacientes TDAH estimados 6–17" in o["t"]][0]
s.move(4.95, ctr((opt["x"], opt["y"], opt["w"], opt["h"])), d=0.6)
s.click(5.93)
s.mark(6.35, (sel["x"] + 6, sel["y"] + 6, 300, sel["h"] - 12), until=8.6)
s.cam(6.5, (470, 500, 1366, 1080), d=0.8)                        # solo el mapa
s.caption(6.6, 8.5, "Mapa por departamento de salud")
s.cam(8.75, "full", d=0.8)
scenes.append(s)

# ---------------------------------------------------------------- S2 · ranking (7,4 s)
s = Scene("s2rank", 7.4, "Ranking")
s.state("03_map_pacientes", 0, 0.83); s.state("04_ranking", 0.83, 4.23); s.state("05_ranking_dropdown", 4.23, 5.03)
s.state("06_ranking_A", 5.03, 7.4)
s.cursor(0.0, 6.2, (1240, 900)); s.move(0.05, ctr(TABS["Ranking de cuentas"]), d=0.7)
s.click(0.83, whoosh=True)
s.cam(1.35, (430, 520, 1760, 900), d=0.75)
s.move(1.35, (1600, 980), d=0.6)                                 # el cursor se aparta del contenido
s.mark(2.2, (606, 690, 166, 26), until=4.2)                      # score n.º 1
s.mark(2.45, (1257, 690, 392, 26), until=4.2)                    # "Por qué" n.º 1
s.caption(2.0, 4.0, "Ranking A/B/C con su porqué")
seg_btn = (1442, 531, 308, 40)
s.move(3.3, ctr(seg_btn), d=0.7)
s.click(4.23, pop=False)
optA = [o for o in boxes["05_ranking_dropdown"]["options"] if o["t"].strip() == "A"][0]
s.move(4.45, ctr((optA["x"], optA["y"], optA["w"], optA["h"])), d=0.5)
s.click(5.03, pop=False)
s.mark(5.45, (470, 590, 76, 22), until=7.4)                      # "37 cuentas"
s.mark(5.6, (523, 690, 74, 216), until=7.4)                      # columna segmento A
s.caption(5.4, 7.2, "Segmento A: visita mensual")
scenes.append(s)

# ---------------------------------------------------------------- S3 · estrategia (7,0 s)
s = Scene("s3strat", 7.0, "Estrategia")
s.state("07_weights_before", 0, 2.03); s.state("08_weights_after", 2.03, 7.0)
s.cam(0.0, (0, 560, 1300, 1000), d=0.8)
s.cursor(0.7, 4.2, (900, 1000)); s.move(0.75, (273, 856), d=0.8)
s.mark(1.0, (20, 805, 70, 26), until=1.95)                       # etiqueta "Brecha"
s.click(2.03)
s.mark(2.45, (247, 794, 42, 22), until=7.0)                      # 1.00
s.move(2.6, (420, 1000), d=0.5)
s.mark(2.95, (756, 725, 490, 26), until=7.0)                     # La Ribera sube al n.º 2
s.caption(2.7, 5.6, "Más peso a la brecha: cambia el orden")
s.cam(6.1, "full", d=0.8)
scenes.append(s)

# ---------------------------------------------------------------- S4 · patient journey (7,0 s)
s = Scene("s4journey", 7.0, "Journey")
s.state("08_weights_after", 0, 0.73); s.state("10_journey_diagram", 0.73, 3.83); s.state("11_journey_frictions", 3.83, 7.0)
s.cursor(0.0, 1.1, (700, 700)); s.move(0.0, ctr(TABS["Patient journey TDAH"]), d=0.65)
s.click(0.73, whoosh=True)
s.cam(1.15, (700, 620, 1560, 1080), d=0.75)
s.mark(1.95, (866, 875, 141, 76), until=3.8)                     # Transición 18 años
s.mark(2.25, (1180, 973, 166, 24), until=3.8)                    # pérdida de seguimiento
s.caption(1.9, 3.6, "La transición a los 18 años")
s.sounds.append(("whoosh", 3.83 - WHOOSH_LEAD)); s.pops.append(3.83 + 1 / 30)
s.cam(3.83, (900, 220, 1760, 470), d=0.01, ease="none")
s.mark(4.3, (1046, 355, 196, 24), until=7.0)                     # solo el 6 % cumplió criterios de
s.mark(4.45, (918, 380, 122, 24), until=7.0)                     # transición óptima
s.mark(4.85, (1350, 355, 250, 24), until=7.0)                    # el 3,3 % de las personas con TDAH
s.caption(4.4, 6.8, "Fricciones con evidencia")
scenes.append(s)

# ---------------------------------------------------------------- S5 · plan de visitas (4,6 s)
s = Scene("s5plan", 4.6, "Plan")
s.state("09_journey_top", 0, 0.68); s.state("12_plan", 0.68, 2.83); s.state("13_plan_agenda", 2.83, 4.6)
s.cursor(0.0, 1.0, (1300, 700)); s.move(0.0, ctr(TABS["Plan de visitas"]), d=0.6)
s.click(0.68, whoosh=True)
s.cam(1.0, (470, 600, 1760, 880), d=0.7)
s.mark(1.6, (900, 712, 142, 96), until=2.8)                      # capacidad 96
s.mark(1.85, (469, 830, 620, 24), until=2.8)                     # cobertura del ciclo
s.caption(1.5, 4.4, "Plan de visitas automático")
s.sounds.append(("whoosh", 2.83 - WHOOSH_LEAD)); s.pops.append(2.83 + 1 / 30)
s.cam(2.83, (470, 360, 900, 640), d=0.01, ease="none")
s.mark(3.2, (515, 447, 370, 62), until=4.6)                      # días 1-2 agrupados por departamento
scenes.append(s)

SCENE_SLOTS = []
t = 0.0
for sc in scenes:
    SCENE_SLOTS.append((sc, round(t, 3)))
    t += sc.dur
END_START = round(t, 3)
END_DUR = 5.4
TOTAL = round(END_START + END_DUR, 3)

# ---------------------------------------------------------------- S6 · cierre
END_HTML = '''<template>
  <style>
    #root { position: absolute; inset: 0; overflow: hidden; background: #F5F7FB; font-family: "Inter", sans-serif; }
    #root .cam { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; transform-origin: 0 0; }
    #root .shot { position: absolute; left: 0; top: 0; width: 1920px; height: 1080px; }
    #root .ground { position: absolute; inset: 0; opacity: 0;
      background: radial-gradient(1400px 520px at 82% -10%, rgba(33,169,159,.30), transparent 60%),
                  linear-gradient(120deg, #0B2545 0%, #0F3B66 55%, #0F4C81 100%); }
    #root .lock { position: absolute; left: 192px; right: 192px; top: 390px; color: #fff; }
    #root .eyebrow { font-size: 28px; font-weight: 700; letter-spacing: .18em; color: #8FE3DA; text-transform: uppercase; opacity: 0; }
    #root .word { font-size: 104px; font-weight: 900; letter-spacing: -0.03em; line-height: 1.05; margin-top: 18px;
                  clip-path: inset(0 100% 0 0); }
    #root .rule { width: 160px; height: 6px; border-radius: 3px; background: #21A99F; margin: 34px 0 30px 0;
                  transform-origin: 0 50%; transform: scaleX(0); }
    #root .credit { font-size: 42px; font-weight: 400; color: rgba(255,255,255,.86); opacity: 0; }
    #root .credit b { font-weight: 700; color: #ffffff; }
  </style>
  <div id="root" data-composition-id="s6end" data-width="1920" data-height="1080" data-start="0" data-duration="__DUR__">
    <div id="s6end-cam" class="cam" data-layout-allow-overflow>
      <img id="s6end-img" class="clip shot" src="assets/screens/01_map.png" alt="" data-start="0" data-duration="1.4" data-track-index="1" />
    </div>
    <div id="s6end-ground" class="ground"></div>
    <div id="s6end-lock" class="lock">
      <div id="s6end-eyebrow" class="eyebrow">Neurociencias · TDAH · Comunitat Valenciana</div>
      <div id="s6end-word" class="word" data-var-text="appName">Territory Scope NS Valencia</div>
      <div id="s6end-rule" class="rule"></div>
      <div id="s6end-credit" class="credit">Creado por la <b data-var-text="author">Dra. Miriam Martínez Santos</b></div>
    </div>
  </div>
  <script>
    const tl = gsap.timeline({ paused: true });
    tl.set("#s6end-cam", { x: 0, y: 0, scale: 1 }, 0);
    // la cámara entra en el banner azul de la app hasta que llena el plano
    tl.to("#s6end-cam", { x: -1500 * 8 + 960, y: -150 * 8 + 540, scale: 8, duration: 1.0, ease: "power3.in" }, 0.15);
    tl.to("#s6end-ground", { opacity: 1, duration: 0.25, ease: "none" }, 1.05);
    tl.fromTo("#s6end-eyebrow", { opacity: 0, filter: "blur(6px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.2, ease: "power4.out" }, 1.35);
    tl.fromTo("#s6end-word", { clipPath: "inset(0 100% 0 0)" }, { clipPath: "inset(0 0% 0 0)", duration: 0.7, ease: "expo.out" }, 1.5);
    tl.fromTo("#s6end-rule", { scaleX: 0 }, { scaleX: 1, duration: 0.45, ease: "expo.out" }, 2.05);
    tl.fromTo("#s6end-credit", { opacity: 0, filter: "blur(8px)" }, { opacity: 1, filter: "blur(0px)", duration: 0.2, ease: "power4.out" }, 2.35);
    window.__timelines["s6end"] = tl;
  </script>
</template>
'''.replace("__DUR__", str(END_DUR))

# ---------------------------------------------------------------- escribir
comp = ROOT / "compositions"
comp.mkdir(exist_ok=True)
for sc, _t0 in SCENE_SLOTS:
    (comp / f"{sc.id}.html").write_text(sc.html())
(comp / "s6end.html").write_text(END_HTML)

hosts, audios = [], []
for i, (sc, t0) in enumerate(SCENE_SLOTS):
    hosts.append(f'''      <div id="{sc.id}" data-composition-id="{sc.id}" data-composition-src="compositions/{sc.id}.html"
        data-start="{t0}" data-duration="{sc.dur}" data-track-index="{i + 1}" data-track-kind="graphics"
        data-width="1920" data-height="1080"></div>''')
    for j, (kind, ts) in enumerate(sc.sounds):
        src = {"click": "assets/audio/click.mp3", "whoosh": "assets/audio/whoosh.mp3"}[kind]
        vol = {"click": 1.5, "whoosh": 0.7}[kind]
        dur = {"click": 0.37, "whoosh": 0.6}[kind]
        audios.append(f'      <audio id="{sc.id}-{kind}{j}" class="clip" src="{src}" data-start="{round(t0 + ts, 3)}" '
                      f'data-duration="{dur}" data-track-index="{20 + (j % 2)}" data-volume="{vol}"></audio>')
hosts.append(f'''      <div id="s6end" data-composition-id="s6end" data-composition-src="compositions/s6end.html"
        data-start="{END_START}" data-duration="{END_DUR}" data-track-index="{len(SCENE_SLOTS) + 1}" data-track-kind="graphics"
        data-width="1920" data-height="1080" data-variable-values='{{"appName":"Territory Scope NS Valencia","author":"Dra. Miriam Martínez Santos"}}'></div>''')
audios.append(f'      <audio id="end-whoosh" class="clip" src="assets/audio/whoosh.mp3" data-start="{round(END_START + 0.55, 3)}" '
              f'data-duration="0.6" data-track-index="22" data-volume="0.8"></audio>')

MUSIC = ROOT / "assets/audio/music.mp3"
music = (f'      <audio id="music" class="clip" src="assets/audio/music.mp3" data-start="0" data-duration="{TOTAL}" '
         f'data-media-start="16.015" data-track-index="30" data-volume="0.62" data-fade-in="0.4" data-fade-out="1.8"></audio>') if MUSIC.exists() else \
        "      <!-- música: pendiente (assets/audio/music.mp3); vuelve a ejecutar build_scenes.py cuando exista -->"

index = f'''<!doctype html>
<html lang="es" data-composition-variables='[{{"id":"author","type":"string","label":"Autora","default":"Dra. Miriam Martínez Santos"}},{{"id":"appName","type":"string","label":"Nombre de la app","default":"Territory Scope NS Valencia"}}]'>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1920, height=1080" />
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.15.0/dist/gsap.min.js"></script>
    <style>
      * {{ margin: 0; padding: 0; box-sizing: border-box; }}
      html, body {{ margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #F5F7FB; }}
      #root {{ width: 100%; height: 100%; position: relative; font-family: "Inter", sans-serif; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-duration="{TOTAL}" data-width="1920" data-height="1080">
{chr(10).join(hosts)}
{chr(10).join(audios)}
{music}
    </div>
    <script>
      window.__timelines = window.__timelines || {{}};
      window.__timelines["main"] = gsap.timeline({{ paused: true }});
    </script>
  </body>
</html>
'''
(ROOT / "index.html").write_text(index)
print(f"escenas: {[sc.id for sc, _ in SCENE_SLOTS] + ['s6end']} · duración total {TOTAL} s · sonidos {len(audios)}")
