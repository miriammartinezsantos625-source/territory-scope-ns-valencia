"""Contenido editorial de la app (patient journey, referencias, metodología). Tono no promocional."""

TIPO_LABEL = {
    "usmi": "USMI (salud mental infanto-juvenil)", "usm": "USM (salud mental adultos)",
    "neuropediatria": "Pediatría / neuropediatría hospitalaria", "privada_neuropediatria": "Neuropediatría privada",
    "privada_psiquiatria": "Psiquiatría privada", "privada_internamiento": "Privada · internamiento/residencial",
    "hospital_publico": "Hospital público", "hospital_privado": "Hospital privado",
    "hospital_dia_sm": "Hospital de día salud mental", "hospital_psiquiatrico": "Hospital psiquiátrico",
    "recurso_sm_otro": "Otro recurso de salud mental",
}

METRICAS_MAPA = {
    "pac_por_rec_infantil": ("Pacientes estimados 6–17 por recurso especializado", "estimación"),
    "pac_por_rec_adulto": ("Pacientes estimados 18–64 por recurso especializado", "estimación"),
    "pac_infantil": ("Pacientes TDAH estimados 6–17 años", "estimación"),
    "pac_adulto": ("Pacientes TDAH estimados 18–64 años", "estimación"),
    "pob_infantil": ("Población 6–17 años (INE 1-1-2025)", "dato"),
    "pob_adulto": ("Población 18–64 años (INE 1-1-2025)", "dato"),
}

JOURNEY_DOT = """
digraph G {
  rankdir=TB; bgcolor="transparent"; nodesep=0.45; ranksep=0.38; pad=0.2; size="11,9";
  node [shape=box, style="filled", fontname="Helvetica", fontsize=12, color="#9AA8B8", fillcolor="#FFFFFF",
        fontcolor="#1F2A37", penwidth=1, margin="0.18,0.10"];
  edge [color="#7A8899", fontname="Helvetica", fontsize=10, fontcolor="#5B6B7F", arrowsize=0.7];

  subgraph cluster_inf { label="INFANCIA Y ADOLESCENCIA (6–17)"; fontname="Helvetica"; fontsize=10; fontcolor="#5B6B7F";
    color="#DDE3EA"; style="filled"; fillcolor="#F4F6F9";
    esc  [label="Entorno escolar y familiar\ndetección de síntomas"];
    ap   [label="Pediatría de\natención primaria"];
    np   [label="Neuropediatría\nhospitalaria", fillcolor="#E6EEF6", color="#0F4C81"];
    usmi [label="USMI\nsalud mental infanto-juvenil", fillcolor="#E6EEF6", color="#0F4C81"];
    dx   [label="Diagnóstico y\nplan de tratamiento", fillcolor="#E3F2F1", color="#13807A"];
    seg  [label="Seguimiento"];
  }
  tr [label="Transición\n18 años", shape=box, style="filled,bold", fillcolor="#0B2545", fontcolor="#FFFFFF", color="#0B2545"];
  subgraph cluster_ad { label="EDAD ADULTA (18–64)"; fontname="Helvetica"; fontsize=10; fontcolor="#5B6B7F";
    color="#DDE3EA"; style="filled"; fillcolor="#F4F6F9";
    usm  [label="USM de adultos", fillcolor="#E6EEF6", color="#0F4C81"];
    priv [label="Psiquiatría privada", fillcolor="#E6EEF6", color="#0F4C81"];
    mf   [label="Medicina de familia"];
    adx  [label="Adulto sin diagnóstico\nen la infancia", color="#8A6D3B", style="filled,dashed"];
  }
  esc -> ap; ap -> np [label="sospecha"]; ap -> usmi [label="derivación"];
  np -> dx; usmi -> dx; dx -> seg; seg -> tr;
  tr -> usm [label="derivación"]; tr -> priv; tr -> mf [label="pérdida de seguimiento", style=dashed];
  adx -> mf; mf -> usm [label="derivación"]; adx -> priv [style=dashed];
}
"""

FRICCIONES = [
    {
        "titulo": "1 · Infradiagnóstico y retraso en el acceso en la infancia",
        "texto": ("El TDAH sigue infrarreconocido e infradiagnosticado en la mayoría de países, sobre todo en niñas "
                  "y en niños mayores; la revisión describe barreras de acceso a la atención en distintos puntos del circuito."),
        "en_el_mapa": "Departamentos con alta población 6–17 y pocos recursos infanto-juveniles registrados (brecha alta).",
        "refs": ["sayal2018", "nice_ng87"],
    },
    {
        "titulo": "2 · Transición infanto-adulto a los 18 años",
        "texto": ("En la vigilancia nacional británica, de los jóvenes en tratamiento que necesitaban transición, el 64 % tuvo "
                  "la derivación aceptada pero solo el 22 % acudió a la primera cita en adultos, y solo el 6 % cumplió criterios "
                  "de transición óptima."),
        "en_el_mapa": "Coordinación USMI ↔ USM dentro de cada departamento; departamentos sin USM registrada.",
        "refs": ["eke2020", "nice_ng87"],
    },
    {
        "titulo": "3 · Infradiagnóstico en adultos",
        "texto": ("El TDAH del adulto está infradiagnosticado e infratratado en muchos países europeos (consenso europeo). "
                  "En las encuestas WMH de la OMS (adultos de 18–44 años), solo el 3,3 % de las personas con TDAH en los "
                  "últimos 12 meses recibió tratamiento para el TDAH, frente al 21,8 % que recibió tratamiento por algún "
                  "problema emocional: la atención se dirigía sobre todo a las comorbilidades."),
        "en_el_mapa": "Pacientes estimados 18–64 por recurso; peso de la psiquiatría privada como puerta de entrada.",
        "refs": ["kooij2019", "fayyad2017"],
    },
]

REFERENCIAS = {
    "sayal2018": ("Sayal K, Prasad V, Daley D, Ford T, Coghill D. ADHD in children and young people: prevalence, care "
                  "pathways, and service provision. Lancet Psychiatry. 2018;5(2):175-186.",
                  "https://doi.org/10.1016/S2215-0366(17)30167-0"),
    "eke2020": ("Eke H, Ford T, Newlove-Delgado T, et al. Transition between child and adult services for young people with "
                "ADHD: findings from a British national surveillance study. Br J Psychiatry. 2020;217(5):616-622.",
                "https://doi.org/10.1192/bjp.2019.131"),
    "kooij2019": ("Kooij JJS, Bijlenga D, Salerno L, et al. Updated European Consensus Statement on diagnosis and treatment "
                  "of adult ADHD. Eur Psychiatry. 2019;56:14-34.", "https://doi.org/10.1016/j.eurpsy.2018.11.001"),
    "fayyad2017": ("Fayyad J, Sampson NA, Hwang I, et al. The descriptive epidemiology of DSM-IV adult ADHD in the World "
                   "Health Organization World Mental Health Surveys. Atten Defic Hyperact Disord. 2017;9(1):47-65.",
                   "https://doi.org/10.1007/s12402-016-0208-3"),
    "nice_ng87": ("NICE. Attention deficit hyperactivity disorder: diagnosis and management (NG87). 2018, actualizada.",
                  "https://www.nice.org.uk/guidance/ng87"),
    "gpc_sns": ("Grupo de trabajo de la GPC sobre las Intervenciones Terapéuticas en el TDAH. Guía de Práctica Clínica sobre "
                "las Intervenciones Terapéuticas en el TDAH. Ministerio de Sanidad / IACS; 2017. Guías de Práctica Clínica en el SNS.",
                "https://portal.guiasalud.es/gpc/trastorno-deficit-atencion-hiperactividad/"),
}

VALOR_KAM = [
    ("Formación y actualización científica",
     "Sesiones acreditadas y no promocionales sobre diagnóstico en el ciclo vital, guías (NICE NG87, GPC del SNS) y "
     "herramientas de cribado para atención primaria, pediatría y salud mental."),
    ("Apoyo a los circuitos de derivación",
     "Facilitar que pediatría de AP, neuropediatría, USMI y USM compartan criterios de derivación y protocolos de "
     "transición a los 18 años, a petición de los propios servicios."),
    ("Coordinación con Medical",
     "Canalizar preguntas científicas al equipo médico (MSL) y proyectos de mejora asistencial o de datos de vida real "
     "a través de los cauces formales de la compañía."),
]

LIMITACIONES = [
    "Los pacientes potenciales son ESTIMACIONES (población × prevalencia publicada), no casos diagnosticados ni tratados.",
    "La prevalencia se aplica de forma uniforme a todos los departamentos; no recoge diferencias socioeconómicas locales.",
    "Los grupos 6–17 y 18–64 se aproximan desde grupos quinquenales del INE suponiendo distribución uniforme dentro de cada grupo.",
    "El Registro de centros sanitarios publicado más reciente es de 2021: puede haber unidades abiertas o cerradas después.",
    "Muchas USM/USMI funcionan dentro de centros de salud y no constan como centro independiente: un departamento "
    "'sin USMI registrada' debe verificarse antes de concluir que no la tiene.",
    "La oferta privada está infrarrepresentada: solo entran centros, clínicas y hospitales con nombre de organización; "
    "las consultas individuales (con o sin nombre de profesional) se excluyen por privacidad.",
    "Privado significa titularidad privada según el Registro; algunos centros privados tienen conciertos con la "
    "sanidad pública que esta app no recoge.",
    "Los servicios de neuropediatría se infieren (hospital general con pediatría), están marcados como no verificados "
    "y cuentan solo 0,5 como recurso.",
    "La prevalencia adulta (Simon et al., 2009) es una media para todas las edades adultas; la prevalencia baja con la edad.",
    "El recuento de recursos no mide capacidad (profesionales, agendas, listas de espera), solo número de puntos de atención.",
]

CON_DATOS_INTERNOS = [
    ("CRM", "Relación existente y cobertura real de visitas (componente 'acceso'), histórico de interacciones."),
    ("Ventas / datos de mercado (p. ej. IQVIA)", "Sustituirían las estimaciones de potencial por demanda real y permitirían medir evolución."),
    ("Datos asistenciales agregados", "Tiempos de espera o actividad por unidad medirían la brecha real en lugar de inferirla del nº de recursos."),
]

REF_CORTA = {"sayal2018": "Sayal et al., Lancet Psychiatry 2018", "eke2020": "Eke et al., Br J Psychiatry 2020",
             "kooij2019": "Kooij et al., Eur Psychiatry 2019", "fayyad2017": "Fayyad et al., ADHD 2017",
             "nice_ng87": "NICE NG87", "gpc_sns": "GPC TDAH del SNS, 2017"}
