from src.constants import CHART_KEYWORDS, MAP_KEYWORDS, CHART_WORDS_ES, RATE_LIMIT_PER_DAY, SQL_ROW_LIMIT
from src.ui_copy import ABOUT_AND_LIMITS, CHARTS_INFO, HOW_IT_WORKS

# UI_ES: {english_string: spanish_string} — widget labels, prose, templates.
UI_ES = {
    # Page / top bar
    "Colombia statistics chat": "Chat de estadísticas de Colombia",
    "Support": "Apoyar",
    "Donate": "Donar",
    "Copy key": "Copiar llave",
    "Copy email": "Copiar correo",
    "Copied to clipboard": "Copiado al portapapeles",
    "Contact": "Contacto",
    "Bugs, suggestions or questions? Do not hesitate to contact me at:":
        "¿Errores, sugerencias o preguntas? No dudes en escribirme a:",
    # Landing
    "Ask a question": "Haz una pregunta",
    "About": "Acerca de",
    "Charts": "Gráficos",
    "How it works": "Cómo funciona",
    "Want to use your own API key or a higher limit? Run it locally":
        "¿Quieres usar tu propia API key o un límite mayor? Úsalo localmente",
    "**Topics it can help with:**": "**Temas en los que puede ayudar:**",
    "*StatsCo AI can make mistakes. Always verify important information.*":
        "*StatsCo AI puede cometer errores. Verifica siempre la información importante.*",
    # Answer status / errors
    "Thinking…": "Pensando…",
    "Thought for {s:.1f}s": "Pensó durante {s:.1f}s",
    "Failed after {s:.1f}s": "Falló tras {s:.1f}s",
    "I couldn't get a response from the AI model (it may be overloaded "
    "or rate-limited). Please retry in a minute.":
        "No pude obtener respuesta del modelo de IA (puede estar saturado o "
        "limitado). Inténtalo de nuevo en un minuto.",
    "Something went wrong on our side. Please try again in a moment.":
        "Algo salió mal de nuestra parte. Inténtalo de nuevo en un momento.",
    # Pipeline stages and fixed replies
    "Checking the question…": "Revisando la pregunta…",
    "Finding relevant tables…": "Buscando tablas relevantes…",
    "Titling the chart…": "Titulando el gráfico…",
    "Writing the answer…": "Escribiendo la respuesta…",
    "Writing the SQL query…": "Escribiendo la consulta SQL…",
    "Adjusting the SQL query…": "Ajustando la consulta SQL…",
    "Running the query…": "Ejecutando la consulta…",
    "Please provide a question and I'll look it up in the data.":
        "Escribe una pregunta y la buscaré en los datos.",
    "I'm not sure what you're asking. Could you rephrase with the specific "
    "indicator, place and time period you have in mind?":
        "No estoy seguro de qué preguntas. ¿Podrías reformularla indicando el "
        "indicador, el lugar y el periodo que te interesan?",
    "Sorry, I can't answer that with the data I currently have. "
    "Here's what I can help with:\n\n":
        "Lo siento, no puedo responder eso con los datos que tengo. "
        "Esto es en lo que puedo ayudar:\n\n",
    "That question is too long. Please keep it under {n} characters.":
        "Esa pregunta es demasiado larga. Por favor, mantenla por debajo de {n} caracteres.",
    "I can only answer questions about Colombian statistics.":
        "Solo puedo responder preguntas sobre estadísticas de Colombia.",
    'We couldn\'t find data for your question: "{question}". Could you try '
    "being more specific about the indicator, place and time period?":
        'No encontramos datos para tu pregunta: "{question}". ¿Podrías ser más '
        "específico sobre el indicador, el lugar y el periodo?",
    "Sorry, we couldn't answer your question this time. Please try again "
    "or rephrase it.":
        "Lo sentimos, no pudimos responder tu pregunta esta vez. Intenta de nuevo "
        "o reformúlala.",
    "**Source:**": "**Fuente:**",
    # Rate limit
    "Please wait a moment before asking another question.":
        "Espera un momento antes de hacer otra pregunta.",
    "You've reached today's limit of {limit} questions. "
    "Try again after midnight (Colombia time).":
        "Alcanzaste el límite de hoy de {limit} preguntas. "
        "Inténtalo de nuevo después de medianoche (hora de Colombia).",
    "The app has reached its daily limit of questions for everyone. "
    "Try again after midnight (Colombia time).":
        "La aplicación alcanzó su límite diario de preguntas para todos los usuarios. "
        "Inténtalo de nuevo después de medianoche (hora de Colombia).",
    "This chat is set to English. Please ask your question in English, or reload the "
    "page to change the language.":
        "Este chat está en español. Por favor haz tu pregunta en español, o recarga la "
        "página para cambiar el idioma.",
    "Only the first {n} rows of the result are shown.":
        "Solo se muestran las primeras {n} filas del resultado.",
    "Your question was interrupted before it was answered. Please ask it again.":
        "Tu pregunta se interrumpió antes de ser respondida. Por favor hazla de nuevo.",
    # Charts
    "Line": "Línea", "Bar": "Barras", "Map": "Mapa", "Table": "Tabla",
    "Highlight": "Resaltar",
    "No data": "Sin datos",
    "Departments in grey have no data.": "Los departamentos en gris no tienen datos.",
    "(none)": "(ninguno)",
    # Popover prose
    ABOUT_AND_LIMITS: (
        "Las conversaciones se envían a la API Gemini de Google. Google puede "
        "conservarlas y usarlas para entrenar sus modelos.\n\n"
        "StatsCoAI no recopila ni guarda información sobre ti o tu conversación, "
        "más allá de lo que Streamlit o Google recopilen por su cuenta.\n\n"
        "El modelo no tiene memoria entre preguntas: cada una se responde por "
        "separado, sin saber lo que preguntaste antes.\n\n"
        "Funciona más rápido y más barato, y en general incluso mejor, con "
        "preguntas en inglés.\n\n"
        "Los datos se actualizan solo dos veces al mes. "
        "Última actualización: {date}.\n\n"
        f"Para que siga siendo gratis para todos, hay un máximo de "
        f"{RATE_LIMIT_PER_DAY} preguntas por día, y cada respuesta devuelve como "
        f"máximo {SQL_ROW_LIMIT} filas.\n\n"
        "En ciertos horarios puede haber alta latencia, o el modelo puede no "
        "devolver ninguna respuesta. Si eso ocurre, por favor intenta de nuevo."
    ),
    CHARTS_INFO: (
        f"Un gráfico reemplaza la respuesta en texto cuando tu pregunta incluye una "
        f"de estas palabras: "
        + ", ".join(f"**{CHART_WORDS_ES[w]}**" for w in CHART_KEYWORDS) + ".\n\n"
        "El tipo de gráfico se elige automáticamente: **línea** para resultados con "
        "más de una fila, **barras** para una sola fila.\n\n"
        "Pide algo como "
        + ", ".join(f'"**{CHART_WORDS_ES[w]}**"' for w in MAP_KEYWORDS)
        + " y obtendrás un **mapa** de Colombia.\n\n"
        "Junto al gráfico siempre hay una vista en tabla con los mismos datos."
    ),
    HOW_IT_WORKS: (
        "**Prueba a preguntar:**\n"
        "- ¿Cuál fue la tasa de desempleo en Colombia en 2024?\n"
        "- Grafica el salario mínimo de 2000 a 2026\n"
        "- Población en 2025, departamento por departamento\n\n"
        "Preguntas en lenguaje natural. Primero, la app revisa si sus datos pueden "
        "responder la pregunta: si no, te dice en qué puede ayudar; si la pregunta es "
        "ambigua, te pide ser más específico.\n\n"
        "Luego busca las tablas más relevantes entre ~30 conjuntos de datos oficiales "
        "(DANE, Banco de la República, MinHacienda…) y escribe una consulta a la base "
        "de datos para obtener las cifras. Si la consulta falla o no devuelve nada, "
        "la ajusta y lo intenta de nuevo.\n\n"
        "Por último, redacta la respuesta en lenguaje sencillo, o dibuja un gráfico o "
        "mapa cuando lo pides. Cada respuesta indica sus fuentes."
    ),
}

# TOPICS_ES: {table_name: (title, topic)} — Spanish display text for list_topics.
# The English originals live in colombia.db's dataset_catalog.
TOPICS_ES = {
    "population_national": ("Población, nacional",
        "Población de todo el país sin desagregación por departamento o municipio, por "
        "edad simple y sexo, según las proyecciones del censo del DANE."),
    "population_departmental": ("Población por departamento",
        "Población a nivel departamental — p. ej. Antioquia, Valle del Cauca, Bogotá D.C. "
        "— por edad simple y sexo, según las proyecciones del censo del DANE."),
    "births": ("Nacimientos",
        "Nacidos vivos registrados por el DANE cada año, por grupo de edad de la madre, "
        "nivel educativo de la madre, departamento, municipio y sexo."),
    "child_labor": ("Trabajo infantil",
        "Encuesta anual de trabajo infantil del DANE para menores de 5 a 17 años: cuántos "
        "trabajan o hacen oficios del hogar no remunerados, por edad, asistencia escolar, "
        "horas trabajadas, ingresos, razón para trabajar, tipo de empleo, rama de "
        "actividad y geografía urbana/rural (nacional, cabeceras, centros poblados y "
        "rural disperso)."),
    "deaths_national": ("Defunciones, nacional",
        "Defunciones de todo el país sin desagregación por departamento o municipio, por "
        "área de residencia, edad al morir y sexo; incluye rangos finos de edad infantil "
        "para la mortalidad infantil."),
    "deaths_by_department_and_cause": ("Defunciones por departamento y causa",
        "Defunciones a nivel departamental — p. ej. Antioquia, Valle del Cauca, Bogotá "
        "D.C. — por causa de muerte, edad al morir y sexo, desde 2019."),
    "deaths_by_municipality_and_cause": ("Defunciones por municipio y causa",
        "Defunciones a nivel municipal — p. ej. Medellín, Cali, Bogotá — por causa de "
        "muerte, edad al morir y sexo, desde 2019."),
    "public_debt_balances": ("Saldos de deuda pública",
        "Saldos de la deuda del Gobierno Nacional Central (GNC) al cierre de cada mes "
        "desde 2001, divididos en interna y externa, en miles de millones de COP y como "
        "porcentaje del PIB."),
    "public_debt_composition": ("Composición de la deuda pública",
        "Composición porcentual de la deuda del Gobierno Nacional Central, mensual, por "
        "fuente de financiación (p. ej. TES, BIRF, BID, CAF, bonos Fogafín, bonos "
        "agrarios, bonos de paz, créditos comerciales), tipo de tasa de interés y moneda."),
    "public_debt_indicators": ("Indicadores de deuda pública",
        "Indicadores de riesgo de la deuda del Gobierno Nacional Central, mensuales: "
        "duración de Macaulay, vida media y cupón promedio."),
    "public_debt_maturity_profile": ("Perfil de vencimientos de la deuda pública",
        "Calendario de pagos de la deuda del Gobierno Nacional Central: proyección del "
        "capital e intereses que vencen en cada año futuro, por fecha de reporte."),
    "economic_activity_index": ("Indicador de seguimiento a la economía (ISE)",
        "Indicador mensual de actividad económica del DANE (ISE), un indicador adelantado "
        "del PIB, para la economía total y sus sectores primario, secundario y terciario "
        "y sus actividades, en series originales y desestacionalizadas."),
    "labor_market": ("Mercado laboral",
        "Tasa de desempleo anual de hombres y mujeres (encuesta GEIH), además de "
        "desagregaciones por departamento y región: fuerza laboral, ocupación, "
        "informalidad, educación, rama de actividad, tipo de empleo, sitio de trabajo, "
        "tamaño de empresa y afiliación a salud y pensión (seguridad social)."),
    "traveler_flows": ("Flujos de viajeros",
        "Cruces fronterizos mensuales registrados por Migración Colombia desde 2012, por "
        "país y sexo: extranjeros que llegan y colombianos que salen."),
    "net_migration": ("Migración neta",
        "Migración neta anual de Colombia según el Banco Mundial (llegadas menos salidas) "
        "desde 1960, solo total nacional, con una tasa por cada 1.000 habitantes."),
    "exchange_rate": ("Tasa de cambio (TRM)",
        "Tasa de cambio oficial del dólar en Colombia (COP por USD, la TRM / Tasa "
        "Representativa del Mercado), diaria desde 1991, más promedios mensuales y "
        "anuales."),
    "interest_rates": ("Tasas de interés",
        "Dos tasas de interés del Banco de la República: la tasa de política monetaria "
        "(diaria) y la tasa de colocación promedio (mensual)."),
    "minimum_wage": ("Salario mínimo",
        "Salario mínimo mensual legal y auxilio de transporte en Colombia desde 1984, en "
        "pesos nominales, pesos reales, dólares y crecimiento anual."),
    "unemployment_monthly": ("Desempleo, mensual",
        "Tasa de desempleo mensual nacional de Colombia sin desagregación por "
        "departamento o región, original y desestacionalizada, además de la tasa global "
        "de participación, la tasa de ocupación y los conteos relacionados."),
    "misery_index": ("Índice de miseria",
        "Índice de Miseria anual de Hanke para Colombia y sus componentes: tasa de "
        "desempleo, inflación, tasa de colocación y crecimiento real del PIB per cápita."),
    "population_municipal": ("Población por municipio",
        "Población a nivel municipal — p. ej. Medellín, Cali, Bogotá — por edad simple y "
        "sexo, según las proyecciones del censo del DANE."),
    "poverty_indicators": ("Indicadores de pobreza",
        "Principales indicadores de pobreza monetaria: incidencia de pobreza y pobreza "
        "extrema, personas en pobreza, brecha y severidad, líneas de pobreza, coeficiente "
        "de Gini e ingreso per cápita del hogar, por dominio geográfico."),
    "poverty_by_household_profile": ("Pobreza por perfil del hogar",
        "Incidencia de pobreza monetaria y pobreza extrema según características del jefe "
        "de hogar y del hogar (sexo, edad, educación, empleo, cotización a pensión, "
        "tamaño del hogar, niños), desde 2024."),
    "poverty_by_sex": ("Pobreza por sexo",
        "Incidencia de pobreza monetaria y pobreza extrema de hombres frente a mujeres, "
        "por dominio geográfico, desde 2024."),
    "productivity": ("Productividad",
        "Estadísticas anuales de productividad del DANE desde 2005: productividad laboral "
        "por persona ocupada y por hora trabajada, además de descomposiciones del "
        "crecimiento de la producción por actividad económica en productividad total de "
        "los factores (PTF), servicios de capital (capital TIC y no TIC), composición del "
        "trabajo, energía, materiales y consumo intermedio."),
    "consumer_price_index": ("Índice de precios al consumidor",
        "Índice de Precios al Consumidor (IPC) mensual de Colombia e inflación: nacional, "
        "para las 23 ciudades encuestadas y para las 12 divisiones de gasto — alimentos y "
        "bebidas no alcohólicas, bebidas alcohólicas y tabaco, prendas de vestir y "
        "calzado, alojamiento, agua, electricidad, gas y otros combustibles, muebles y "
        "artículos para el hogar, salud, transporte, información y comunicación, "
        "recreación y cultura, educación, restaurantes y hoteles, y bienes y servicios "
        "diversos."),
    "fiscal_balance": ("Balance fiscal",
        "Déficit/superávit del Gobierno Nacional Central (GNC), anual, trimestral y "
        "mensual, en miles de millones de COP y como porcentaje del PIB — el balance "
        "(déficit/superávit de caja, déficit total, balance primario, préstamo neto, "
        "déficit por financiar), ingresos tributarios (renta, IVA, impuesto al consumo, "
        "aranceles, impuesto al patrimonio, GMF, impuesto al carbono, sobretasa a la "
        "gasolina, timbre, CREE), ingresos no tributarios y de capital (concesiones, "
        "contribución de hidrocarburos, excedentes financieros de empresas estatales como "
        "Ecopetrol, el Banco de la República e ISA/ISAGEN, fondos especiales), gastos "
        "(intereses de deuda interna y externa, inversión, servicios personales, gastos "
        "generales, transferencias incluidas pensiones y transferencias regionales) y "
        "costos de reestructuración financiera (Fogafín, liquidación de la Caja Agraria, "
        "alivios hipotecarios de la Ley 546, reducción de deuda TRD)."),
    "gdp_quarterly": ("PIB, cuentas nacionales trimestrales",
        "PIB trimestral de Colombia (cuentas nacionales del DANE) por los enfoques de "
        "producción, gasto e ingreso, con desagregaciones por sector y componente y tasas "
        "de crecimiento — incluido el gasto de consumo final de los hogares por finalidad "
        "(alimentos, bebidas alcohólicas y tabaco, vestido y calzado, vivienda, agua, "
        "electricidad y gas, muebles, salud, transporte, comunicaciones, recreación y "
        "cultura, educación, restaurantes y hoteles, diversos) y por durabilidad (bienes "
        "durables, semidurables y no durables, y servicios), consumo del gobierno, "
        "formación bruta de capital (vivienda, maquinaria y equipo, productos de "
        "propiedad intelectual, recursos biológicos cultivados, otros edificios y "
        "estructuras), exportaciones e importaciones de bienes y servicios, y "
        "desagregaciones por industria (manufactura, minería, construcción, actividades "
        "financieras y de seguros, etc.)."),
    "gdp_annual": ("PIB, anual",
        "PIB anual de Colombia desde 1975 (Banco de la República), real y nominal, en "
        "miles de millones de COP, con tasas de crecimiento y cifras per cápita."),
}
