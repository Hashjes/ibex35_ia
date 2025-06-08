# Proyecto IBEX 35 IA

Esta aplicación web, desarrollada con Flask, integra análisis financiero, inteligencia artificial y gestión de cartera para usuarios interesados en el IBEX 35. Está pensada para ofrecer:

- **Asistente Financiero IA**: chatbot y “asesor” de inversión basado en agentes CrewAI.  
- **Mis Acciones**: registro de posiciones, cálculo de ganancias y envío de reportes diarios por correo.  
- **Análisis & Predicción**: gráficos interactivos (Plotly, Prophet) de históricos, predicción y métricas técnicas (SMA, RSI).  

---

## Tabla de contenidos

1. [Requisitos](#requisitos)  
2. [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)  
3. [Configuración](#configuración)  
4. [Guía de uso](#guía-de-uso)  
   1. [Asistente IA](#asistente-ia)  
   2. [Mis Acciones](#mis-acciones)  
   3. [Envío de reporte diario](#envío-de-reporte-diario)  
   4. [Análisis & Predicción](#análisis--predicción)  
5. [Ejecución de pruebas](#ejecución-de-pruebas)  
6. [Despliegue en Render](#despliegue-en-render)  
7. [Buenas prácticas y estructura](#buenas-prácticas-y-estructura)  
8. [Extensiones futuras](#extensiones-futuras)  

---

## Requisitos

- Python 3.9+  
- Git  
- Cuenta en Mailtrap (solo pruebas SMTP)  
- Clave de API Groq (CrewAI)  

---

## Instalación y puesta en marcha

```bash
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo
python -m venv venv

# Windows PowerShell
.env\Scripts\Activate.ps1  

# Linux / macOS
source venv/bin/activate

pip install -r requirements.txt
```

---

## Configuración

Cree un archivo `.env` en la raíz con las siguientes variables (o configúrelas en Render):

\`\`\`
GROQ_API_KEY="tu_api_key_groq"
SMTP_USER="tu_usuario_mailtrap"
SMTP_PASS="tu_pass_mailtrap"
SECRET_KEY="clave_secreta_flask"
\`\`\`

- **GROQ_API_KEY**: credenciales para el LLM de CrewAI.  
- **SMTP_USER/SMTP_PASS**: para Mailtrap.  
- **SECRET_KEY**: protege la sesión de Flask.

---

## Guía de uso

### Asistente IA

1. Abra la pestaña **Asistente IA**.  
2. Elija “Conversación” o “Asesor IA” en el selector.  
3. En modo **Conversación**, escriba su consulta y presione ↵.  
4. En modo **Asesor IA**, seleccione perfil (Bajo/Moderado/Alto), defina un objetivo, marque “Extendido” para incluir riesgo y visualizaciones, y envíe.  
5. La respuesta se muestra en burbujas estilo chat; el historial mantiene contexto de las últimas 5 interacciones y sus posiciones.

### Mis Acciones

1. Vaya a **Mis Acciones**.  
2. Para cada ticker del IBEX 35, introduzca **unidades** y **coste medio** (opcional).  
3. Pulse **Guardar**; se actualizará la tabla con:
   - Cantidad  
   - Precio medio de compra  
   - Precio actual  
   - Ganancia por acción  
   - Ganancia total  
   - Ganancia total de la cartera (recuadro destacado)  

### Envío de reporte diario

1. En **Mis Acciones**, tras registrar posiciones, ingrese uno o varios correos separados por comas.  
2. Pulse **Enviar Reporte**.  
3. El sistema:
   1. Extrae crecimientos 1 M y 1 A del IBEX 35.  
   2. Genera un breve comentario de mercado vía IA.  
   3. Monta y envía (simulado) un correo con el comentario y su cartera.  
4. Revise la bandeja de Mailtrap para ver el email.

### Análisis & Predicción

1. Abra **Análisis & Predicción**.  
2. Seleccione una empresa del dropdown.  
3. Pulse **Analizar**.  
4. Se generarán:
   - **Predicción a 1 año** (Prophet + banda de incertidumbre).  
   - **RSI y medias móviles** (SMA50, SMA200).  
   - **Tabla** con ratios fundamentales (P/E, P/B, dividend yield, beta, market cap).

---

## Ejecución de pruebas

```bash
python -m pytest --maxfail=1 --disable-warnings -q
```

- **test_app.py** cubre rutas Flask y flujos de “Mis Acciones” y “Enviar Reporte”.  
- **test_data_utils.py** valida cálculo de RSI y preparación de datos para Prophet.

---

## Despliegue en Render

1. **Conectar repo**: vincule su repositorio GitHub con Render, rama \`main\`.  
2. **Variables de entorno**: añada \`GROQ_API_KEY\`, \`SMTP_USER\`, \`SMTP_PASS\`, \`SECRET_KEY\`.  
3. **Build Command**:
   \`\`\`
   pip install -r requirements.txt
   \`\`\`
4. **Start Command**:
   \`\`\`
   gunicorn app:app --bind 0.0.0.0 $PORT
   \`\`\`
5. Verifique en el *live tail* que todo arranca sin errores y responde HTTP 200.

---

## Buenas prácticas y estructura

- **Modularidad**:  
  - \`app.py\`: rutas y controladores.  
  - \`data_utils.py\`: obtención y procesamiento de datos (yfinance, Prophet, cache).  
  - \`agents_utils.py\`: agentes IA (CrewAI).  
  - \`email_utils.py\`: corrreos SMTP.  
  - \`templates/\` y \`static/\`: presentación y estilos.  

- **Sesión segura**: uso de \`SECRET_KEY\` y \`session\` de Flask.  
- **Cache**: \`cachetools.TTLCache\` para no sobrecargar yfinance.  
- **Control de errores**: manejo de excepciones en llamadas a LLM y SMTP.  
- **Testing**: cobertura mínima del 80 % en lógica crítica con pytest.

---

## Posibles extensiones futuras

1. **RAG**: integrar documentos o noticias financieras para enriquecer al asistente.  
2. **Autenticación**: usar Flask-Login o JWT para cuentas de usuario y persistencia en base de datos.  
3. **Workflow/MCP**: con Celery o Step Functions para programar envíos de correo diarios y alertas.  
4. **Más indicadores**: MACD, bandas de Bollinger, VaR; dashboards interactivos con Dash o Bokeh.  
5. **Histórico de compras**: estimar fecha de adquisición y graficar crecimiento monetario.  
6. **CI/CD completo**: GitHub Actions para tests, linting (Black/Flake8) y despliegue automático.

---
