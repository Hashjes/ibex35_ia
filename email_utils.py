import smtplib
from email.message import EmailMessage
from data_utils import resumen_acciones, precio_actual
from agents_utils import run_chatbot_task
from litellm.exceptions import RateLimitError
import os
# Configuración SMTP para Mailtrap (testing)
SMTP_HOST = "smtp.mailtrap.io"
SMTP_PORT = 2525
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")      # reemplaza con tu clave Mailtrap
EMAIL_FROM = "noreply@ibex35ia.local"

def enviar_reporte_diario(to_email, owned_stocks):
    """
    Envía un correo con:
      1) Un breve comentario generado por IA sobre el estado del mercado,
         basándose únicamente en los datos de crecimiento 1M / 1A.
      2) Detalle de la cartera del usuario.
    """
    # 1) Preparamos el fragmento de crecimientos
    acciones_texto = resumen_acciones()
    crecimiento_lines = [
        line for line in acciones_texto.split("\n")
        if "Crecimiento 1M" in line or "Cambio Últ. Año" in line
    ]
    contexto = "\n".join(crecimiento_lines)

    # 2) Generamos el comentario con ese contexto
    prompt = (
        "En base a estos datos de crecimiento del IBEX35, "
        "dime en una frase si el mercado va bien o mal hoy, y por qué:\n\n"
        f"{contexto}"
    )
    comentario = "No se pudo generar comentario de mercado."
    try:
        comentario = run_chatbot_task(contexto, prompt).strip()
    except RateLimitError:
        comentario = "El servicio de IA está limitado; no hay comentario de mercado."
    except Exception:
        comentario = "No se ha podido generar comentario de mercado."

    # 3) Montamos el cuerpo del email
    lines = [
        comentario,
        "",
        "**Tu cartera de acciones hoy**"
    ]
    for ticker, datos in owned_stocks.items():
        shares = datos.get("shares", 0)
        cost   = datos.get("cost", None)
        current = precio_actual(ticker) or 0.0
        line = f"- {ticker}: {shares} unid., precio actual {current:.2f} €"
        if cost is not None:
            gain = current - cost
            total_gain = gain * shares
            line += f", coste medio {cost:.2f} €, ganancia total {total_gain:.2f} €"
        lines.append(line)

    body = "\n".join(lines)

    # 4) Envío del correo
    msg = EmailMessage()
    msg["Subject"] = "📈 Tu reporte diario de IBEX35 IA"
    msg["From"]    = EMAIL_FROM
    msg["To"]      = to_email
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        smtp.login(SMTP_USER, SMTP_PASS)
        smtp.send_message(msg)
