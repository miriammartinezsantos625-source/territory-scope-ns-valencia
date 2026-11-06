# SPEC · Territory Scope NS Valencia — vídeo promocional

GOAL:    En ~41 s, quien lo ve entiende que la app localiza la brecha diagnóstica del TDAH por
         departamento y la convierte en un plan de visitas priorizado y explicable, y recuerda
         que la creó la Dra. Miriam Martínez Santos.
OUTPUT:  HyperFrames, 1920 x 1080, 30 fps. Sin intro (petición de la autora): el frame 0 es la app.
TIME:    41.0 s x 30 = 1230 frames. Música 110–120 bpm cuando esté disponible (pendiente CLI heygen).

LOOK:    El medio es la propia app (capturas reales 3840x2160 de 14 estados, a 2x para zooms nítidos).
         Fondo #F5F7FB, tinta #0B2545, acento de marca #21A99F solo en el cierre.
         Subrayado: rotulador amarillo #FFD60A al 48 % en multiply, radio 4 px, aparece de izquierda a
         derecha en 0,35 s (power2.out). Ese amarillo es el ÚNICO color añadido sobre la app.
         Rótulos: Inter 700, 40 px, -1 % tracking, blanco sobre barra #0B2545 al 92 %, radio 10 px,
         abajo a la izquierda dentro del 80 % title-safe (x ≥ 192, y ≤ 972). Una línea, ≤ 6 palabras.
         Cursor: flecha macOS negra con borde blanco, 54 px (5 % del alto).
OBJECTS: La app real: KPIs, mapa coroplético, insights, selector de métrica, ranking con "Por qué",
         filtro de segmento, slider de pesos, diagrama del patient journey, tarjetas de fricción,
         plan de visitas. El banner azul marino de la app es el objeto que se convierte en el cierre.
MOTION:  Cámara (wrapper con transform-origin 0 0): movimientos 0,6–0,8 s power2.inOut, sostiene
         mientras el cursor actúa. Llegada de pantalla nueva tras clic: escala 1,03 → 1 en 0,35 s
         expo.out (corte por clic). Cursor: desplazamientos 0,5–0,7 s power3.inOut; clic = escala
         0,82 durante 0,12 s. Rótulos: entrada blur 8 → 0 + opacity en 0,18 s; salida 0,15 s.
SHOTS:   S1 mapa 0–9,6: KPIs subrayados → push al mapa → insight "mayor brecha" → clic selector de
            métrica → clic "Pacientes TDAH estimados 6–17" → el mapa cambia. Clics: 2.
         S2 ranking 9,6–17,0: clic pestaña Ranking (whoosh) → push a la tabla → subrayado score y
            "Por qué" de la n.º 1 → clic filtro Segmento → clic A → subrayado "Segmento A".
         S3 estrategia 17,0–24,0: encuadre barra lateral + tabla → clic en el extremo del slider
            Brecha → el ranking se reordena: subrayado "1.00" y La Ribera sube al n.º 2.
         S4 journey 24,0–31,0: clic pestaña Patient journey → diagrama: "Transición 18 años" y
            "pérdida de seguimiento" → fricciones: "solo el 6 %" y "el 3,3 %".
         S5 plan 31,0–35,6: clic pestaña Plan de visitas → capacidad y cobertura → agenda por día.
         S6 cierre 35,6–41,0: vuelta al inicio y la cámara entra en el banner azul de la app, que
            llena el plano; el nombre de la app se revela y debajo "Creado por la Dra. Miriam
            Martínez Santos". Se sostiene 2,5 s.
SOUND:   Clic (sfx_001) en cada clic real de cursor, pico 1 frame después de la imagen
         (inicio = clic − 0,04 s). Whoosh (sfx_003) solo en los cambios de pestaña y en la entrada al
         cierre. Música: pendiente (catálogo HeyGen requiere el CLI heygen).
BANNED:  Vacío oscuro con elementos flotando; glow, partículas, gradientes morados; tres tarjetas en
         fila; título sobre captura oscurecida; logo en una esquina; anillos de clic; títulos que se
         mueven mientras se leen; UI inventada; UI inclinada en 3D.
QA:      t=0 la app completa (miniatura); t=2,8 insight subrayado legible; t=6,5 mapa con la métrica
         nueva; t=12,5 fila 1 y "Por qué" legibles; t=20,5 La Ribera n.º 2 subrayada; t=26,5
         "Transición 18 años"; t=29,5 "solo el 6 %"; t=33 capacidad; t=39,5 crédito completo.
