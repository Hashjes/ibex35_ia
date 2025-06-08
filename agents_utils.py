import re
from crewai import Agent, Task, LLM, Crew, Process
import os

# Configuración del LLM (reemplaza "TU_KEY" por tu clave válida si la tienes)
llm = LLM(
    model="groq/gemma2-9b-it",
    temperature=0.5,
    base_url="https://api.groq.com/openai/v1",
    api_key=os.getenv("GROQ_API_KEY") 
)

# --------------------------------------------------
# Definición de agentes
# --------------------------------------------------

market_analyst = Agent(
    role="Analista de Mercado",
    goal="Analizar la información actual del mercado del IBEX35 para detectar tendencias, oportunidades y riesgos de inversión.",
    backstory="Eres un experto en mercados financieros con un profundo conocimiento del mercado español.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

investment_advisor = Agent(
    role="Asesor de Inversiones",
    goal="Combinar el análisis de mercado con el perfil y objetivos del usuario para generar recomendaciones de inversión personalizadas, señalando tickers del IBEX35 que sean interesantes.",
    backstory="Eres un asesor financiero experimentado que utiliza datos reales y análisis profundo para ofrecer recomendaciones de inversión.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

risk_analyst = Agent(
    role="Analista de Riesgos",
    goal="Evaluar y calcular métricas de riesgo para las acciones, incluyendo volatilidad anualizada, para ofrecer un análisis adicional del perfil de riesgo.",
    backstory="Eres un experto en gestión de riesgos financieros, especializado en evaluar la estabilidad y volatilidad de los mercados.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

data_visualizer = Agent(
    role="Visualizador de Datos",
    goal="Generar gráficos y visualizaciones que ayuden a comprender la evolución histórica de las acciones, facilitando la toma de decisiones.",
    backstory="Eres un analista experto en visualización de datos, capaz de transformar datos financieros en gráficos claros e informativos.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

report_editor = Agent(
    role="Editor de Reportes Financieros",
    goal="Revisar y organizar la información generada para producir un informe final claro, profesional y bien estructurado en formato markdown.",
    backstory="Eres un editor especializado en contenido financiero, capaz de transformar datos complejos en un informe accesible.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

stock_chatbot = Agent(
    role="Chatbot de Acciones",
    goal="Responder preguntas en tiempo real sobre las acciones que posee el usuario, utilizando el estado actual de los tickers del IBEX35 y sus acciones compradas como contexto.",
    backstory="Eres un experto en análisis financiero y conoces profundamente el mercado de valores. Responde preguntas y ofrece recomendaciones en base a la información actual.",
    allow_delegation=False,
    verbose=True,
    llm=llm
)

# --------------------------------------------------
# Definición de tasks para cada agente
# --------------------------------------------------

market_analysis = Task(
    description=(
        "Utiliza la siguiente información actual del mercado del IBEX35:\n\n"
        "{acciones_data}\n\n"
        "Analiza las tendencias del mercado, identificando oportunidades y riesgos basados en el comportamiento reciente de estas acciones."
    ),
    expected_output="Informe detallado con análisis de tendencias y datos relevantes de las acciones del IBEX35.",
    agent=market_analyst,
)

investment_recommendation = Task(
    description=(
        "Utilizando el análisis de mercado anterior y considerando el perfil de riesgo: \"{perfil}\" "
        "y el objetivo de inversión: \"{objetivo}\", genera recomendaciones personalizadas de inversión. "
        "Indica qué tickers del IBEX35 resultan interesantes, justificando cada recomendación con los datos reales proporcionados."
    ),
    expected_output="Lista de recomendaciones de inversión personalizadas con tickers y justificaciones basadas en datos reales.",
    agent=investment_advisor,
)

risk_assessment = Task(
    description=(
        "Usa los datos históricos de los tickers del IBEX35 para calcular la volatilidad anualizada de cada acción. "
        "Integra esta métrica en un análisis que evalúe el riesgo asociado a cada activo, y proporciona recomendaciones "
        "en función de la tolerancia al riesgo."
    ),
    expected_output="Informe de análisis de riesgo con métricas como volatilidad anualizada y recomendaciones según el riesgo.",
    agent=risk_analyst,
)

visualization_task = Task(
    description=(
        "Genera gráficos que muestren la evolución histórica de precios (último año) para las acciones del IBEX35, "
        "destacando tendencias importantes y eventos significativos."
    ),
    expected_output="Colección de gráficos de evolución histórica para cada acción.",
    agent=data_visualizer,
)

report_generation = Task(
    description=(
        "Revisa el contenido generado por el Analista de Mercado, el Asesor de Inversiones y el Analista de Riesgos. "
        "Edita y organiza la información para producir un informe final en formato markdown, claro y profesional, "
        "sin mensajes extra o de confirmación."
    ),
    expected_output="Informe final de inversiones en formato markdown, bien estructurado y sin mensajes adicionales.",
    agent=report_editor,
)

chat_query = Task(
    description=(
        "Contexto:\n{contexto}\n\n"
        "Pregunta: {pregunta}\n\n"
        "Responde **siempre en español**, basándote en el contexto proporcionado debes guiar al usuario con lo que te pregunte y siempre ser asertivo nunca decirle que no puedes hacer algo/que consulte otras cosas"
    ),
    expected_output="Respuesta en español basada en el contexto.",
    agent=stock_chatbot,
)


# --------------------------------------------------
# Funciones para ejecutar los crews
# --------------------------------------------------

def run_investment_crew(perfil: str, objetivo: str, acciones_data: str) -> str:
    """
    Ejecuta los agentes para análisis básico de mercado + recomendaciones + generación de informe.
    Retorna el texto del informe (Markdown).
    """
    inputs = {
        "perfil": perfil,
        "objetivo": objetivo,
        "acciones_data": acciones_data
    }
    crew = Crew(
        agents=[market_analyst, investment_advisor, report_editor],
        tasks=[market_analysis, investment_recommendation, report_generation],
        process=Process.sequential,
        verbose=True
    )
    result = crew.kickoff(inputs=inputs)
    # El resultado suele estar en result.agents o result.tasks, convertimos a string plano
    return str(result)

def run_extended_investment_crew(perfil: str, objetivo: str, acciones_data: str) -> str:
    """
    Ejecuta los agentes para análisis extendido (incluye riesgo y visualizaciones).
    Retorna el texto del informe (Markdown).
    """
    inputs = {
        "perfil": perfil,
        "objetivo": objetivo,
        "acciones_data": acciones_data
    }
    crew = Crew(
        agents=[market_analyst, investment_advisor, risk_analyst, data_visualizer, report_editor],
        tasks=[market_analysis, investment_recommendation, risk_assessment, visualization_task, report_generation],
        process=Process.sequential,
        verbose=True
    )
    result = crew.kickoff(inputs=inputs)
    return str(result)

def run_chatbot_task(contexto: str, pregunta: str) -> str:
    """
    Ejecuta el agente de chatbot con el contexto y la pregunta del usuario.
    Retorna la respuesta generada por el agente.
    """
    inputs = {
        "contexto": contexto,
        "pregunta": pregunta
    }
    crew = Crew(
        agents=[stock_chatbot],
        tasks=[chat_query],
        process=Process.sequential,
        verbose=True
    )
    result = crew.kickoff(inputs=inputs)
    # Se asume que result contiene la respuesta directa
    return str(result)
