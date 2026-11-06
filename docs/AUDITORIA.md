# Auditoría · Territory Scope NS Valencia

Fecha: 2026-11-06 · Alcance: datos, modelo de scoring, insights, plan de visitas, app, privacidad y metodología.
Estado de partida: 27 tests en verde. Nada publicado.

Prioridad: **P1** = bug o error que puede verse en la demo o romper el despliegue · **P2** = sesgo o fragilidad del modelo · **P3** = pulido.

---

## P1 · Corregir antes de publicar

| # | Área | Hallazgo | Evidencia | Propuesta |
|---|---|---|---|---|
| 1 | Despliegue | `use_container_width` (7 usos) está **deprecado con retirada anunciada para después del 31-12-2025**. `requirements.txt` no fija versiones, así que Streamlit Cloud instalará la última y la app puede romperse. | El log del servidor lo avisa en cada recarga. | Sustituir por `width="stretch"` y fijar versiones probadas en `requirements.txt`. |
| 2 | Metodología | La prevalencia adulta **base (2,8 %) y alta (3,6 %) de Fayyad 2017 se midió solo entre 18 y 44 años**, y el propio estudio observa que baja con la edad. Aplicarla a 18–64 **sobreestima** los pacientes adultos. | Texto completo (PMC5325787): *"ADHD was assessed among respondents in the age range 18–44"*. | Base adulta = 2,5 % (Simon 2009, todos los adultos). Fayyad 2,8 % pasa a ser escenario alto, con la nota "medido en 18–44". |
| 3 | Capa privada | `relaciones.csv` con un **id duplicado hace caer la app** (`InvalidIndexError`). | Prueba con dos filas del mismo `id_cuenta`. | Deduplicar (si hay conflicto, gana "sí") y avisar en pantalla. |
| 4 | Capa privada | "Sí" con tilde, "SI " con espacio o "yes" se ignoran **sin avisar** (acceso = 0). Un id inexistente también se ignora en silencio. | Prueba con `relacion = "Sí"` → 0 cuentas con acceso. | Normalizar valores; mostrar cuántas filas se han cargado y cuántas no casan con ninguna cuenta. |
| 5 | Capa privada | Los **id de cuenta no son estables**: se numeran por orden alfabético dentro de tipo y departamento (`UA-07-03`). Si cambian los datos, se desplazan y la capa privada se asigna a la cuenta equivocada. | `id` se genera con `cumcount` tras ordenar por nombre. | Id derivado del identificador de la fuente (p. ej. `UA-07-R3844`), inmutable. |
| 6 | Hospitales | Has visto hospitales públicos marcados como privados. En los datos, los 17 "hospital privado" tienen dependencia **PRIVADOS** en el Registro oficial, y los de antigua concesión (La Ribera, Torrevieja, Vinalopó, Manises, Dénia) salen como públicos. | Cruce con `Codi_dependència_funcional = 20`. | **Necesito que me digas cuál** para localizar el fallo (¿en el mapa?, ¿en el ranking?). Posibles causas: un hospital con concierto público, o que en el mapa el borde de "privado" no se distingue sobre los puntos A, que son azul marino. |

## P2 · Sesgos y fragilidad del modelo

| # | Hallazgo | Efecto | Propuesta |
|---|---|---|---|
| 7 | La **neuropediatría inferida** (sin verificar) cuenta como recurso infantil, y hay una por hospital. Castellón, Arnau-Llíria y Xàtiva tienen dos hospitales, así que cuentan doble. | Reduce artificialmente la brecha infantil en esos departamentos. | Contar los recursos inferidos con peso 0,5, o solo una neuropediatría por departamento. |
| 8 | La **psiquiatría privada "ambas"** (consultas sobre todo de adultos) cuenta también como recurso infantil. | Reduce la brecha infantil en València y Alicante. | En infantil, contar solo las privadas con población diana infantil. |
| 9 | **7 cuentas privadas son "consultas" genéricas** ("Consulta de psiquiatría") con dirección. No llevan nombre, pero suelen ser consultas de un solo profesional y la dirección lo identifica indirectamente. | Riesgo de privacidad (regla 2 del briefing). | Excluir las "consultas" individuales y dejar solo centros, clínicas y hospitales. |
| 10 | **Empates de score** entre cuentas del mismo tipo y departamento (p. ej. 3 privadas de H. General con 76,4). El corte A/B los separa por orden de id. | Dos cuentas idénticas pueden caer en segmentos distintos. | Desempatar de forma explícita, o asignar el segmento por umbral de score (los empatados van juntos). |
| 11 | 36 cuentas comparten coordenadas: hospital + neuropediatría del mismo hospital (esperado), USM + USMI en el mismo centro, y 2 USM de Paterna geocodificadas al centro del municipio. | Marcadores superpuestos en el mapa; solo se ve uno. | Agrupar marcadores (clusters) o desplazarlos ligeramente; revisar a mano las de Paterna. |
| 12 | Warning de pandas en `fillna(False)` sobre una columna float (`scoring.py:91`). | Fallará con una versión futura de pandas. | Cambiar la conversión de tipos. |

## P3 · Pulido

| # | Hallazgo | Propuesta |
|---|---|---|
| 13 | Decimales con punto ("6.8 %", "81.3") en una interfaz en español. | Formato con coma decimal. |
| 14 | Si se mueve el slider de prevalencia, la ayuda sigue citando la fuente del escenario (p. ej. Catalá 6,8 %) aunque el valor sea otro. | Mostrar "valor personalizado" cuando no coincide con el escenario. |
| 15 | La etiqueta "ESTIMACIÓN" se monta sobre el título en tarjetas KPI estrechas. | Moverla debajo del valor. |
| 16 | La referencia de la GPC del SNS enlaza a la portada de GuíaSalud, no a la guía. | Buscar la URL exacta o dejarla sin enlace. |
| 17 | En la fricción "adultos" se puede añadir un dato verificado y potente de Fayyad 2017: solo el **3,3 %** de los adultos con TDAH recibió tratamiento *para el TDAH* en 12 meses (frente al 21,8 % tratado por cualquier problema emocional). | Añadirlo con su referencia. |
| 18 | `coverage()` recibe `meses` y no lo usa. | Limpiar. |
| 19 | El arranque local depende de `.claude/launch.json` fuera del repo. | Documentar `streamlit run app.py` en el README. |

## Comprobado y correcto

- La población cuadra al habitante con el INE (5.425.182); no hay valores negativos en ningún grupo de edad por sección.
- Ningún tipo de cuenta queda sin peso de relevancia en el YAML.
- No hay nombres de profesionales: las coincidencias de "Dr." son nombres institucionales o de calle (Dr. Peset, Dr. Balmis).
- La capa `data/private/` está en `.gitignore`.
- Los hospitales de antigua concesión figuran como públicos.
- Las cifras de Sayal 2018, Eke 2020, Kooij 2019, Catalá-López 2012, Polanczyk 2007 y Simon 2009 coinciden con PubMed.
- Plan de visitas: respeta la capacidad, prioriza A al recortar y agrupa por departamento (cubierto por tests).

---

## Estado de las correcciones (2026-11-06)

| # | Estado | Qué se ha hecho |
|---|---|---|
| 1 | Corregido | `use_container_width` → `width="stretch"` en Streamlit (se mantiene el parámetro propio de `st_folium`). `requirements.txt` con versiones fijadas y probadas. Sin avisos en el log. |
| 2 | Corregido | Prevalencia adulta: Simon 2009 en los tres escenarios (2,1 / 2,5 / 3,1 %, IC95 %). Fayyad 2017 queda como contexto, con la nota "18–44 años". Pacientes adultos estimados: 95.811 → **85.544**. |
| 3 | Corregido | `clean_relationships()`: deduplica id (gana "sí") y no falla. |
| 4 | Corregido | Se normalizan "Sí", "SI", "yes", "1"…; la app avisa de filas no reconocidas, duplicados e id sin cuenta. |
| 5 | Corregido | Id estables derivados de la fuente: `UA-R3844` (Registro), `HP-S90400` (SVS), `PP-ON12345` (OSM). |
| 6 | Mejorado, **pendiente de tu confirmación** | Los datos coinciden con el Registro oficial. En el mapa: círculo = público (SVS), rombo = privado, y el tooltip dice "titularidad privada (Registro GVA)". Metodología: privado puede tener conciertos. Falta saber qué hospital viste. |
| 7 | Corregido | Recursos inferidos ponderados 0,5 y como máximo 1 por tipo y departamento (configurable). |
| 8 | Corregido | Las privadas "ambas" ya no cuentan como recurso infantil (`ambas_cuentan_en_infantil: []`). |
| 9 | Corregido | 7 consultas individuales privadas excluidas (169 cuentas). Solo se guarda el recuento por motivo. |
| 10 | Corregido | Segmentos por umbral de score: los empates comparten posición y segmento (A = 37, B = 50, C = 82). |
| 11 | Corregido | Marcadores en el mismo punto separados unos 50 m en el mapa. Geocodificación mejorada: se expanden abreviaturas y la precisión sale del tipo devuelto por CartoCiudad. Se rechazan coincidencias falsas (p. ej. un punto de recarga eléctrica que antes contaba como "portal"). Coordenadas aproximadas: 8 → 4. |
| 12 | Corregido | Eliminado el `fillna(False)`. |
| 13 | Corregido | Coma decimal en KPI, captions, tooltips, frases y tabla (formato localizado). |
| 14 | Corregido | Si el slider no coincide con el escenario, la app indica "valor personalizado, no corresponde a una fuente publicada". |
| 15 | Corregido | Etiqueta dato/estimación movida a la línea inferior de la tarjeta. |
| 16 | Corregido | Enlace exacto de la GPC en GuíaSalud. |
| 17 | Corregido | Añadido el 3,3 % frente al 21,8 % de Fayyad 2017 (texto completo) en la fricción de adultos. |
| 18 | Corregido | `coverage()` sin parámetro sobrante. |
| 19 | Pendiente (Fase 5) | Se documentará en el README. |

Extra: cabeceras de la tabla en español y filtros con "Todos" en lugar de "Choose options".
Tests: 27 → **32**, todos en verde.
