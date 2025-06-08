# app.py

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    Response
)
import os
import markdown2
from datetime import datetime
import io
import re

from data_utils import (
    empresas_ibex35,
    preparar_datos_prophet,
    generar_prediccion,
    calcular_indicadores_tecnicos,
    obtener_info_fundamental,
    resumen_acciones,
    precio_actual,
    obtener_rentabilidad_ibex35,
    resumen_detallado
)

from agents_utils import (
    run_investment_crew,
    run_extended_investment_crew,
    run_chatbot_task
)

from email_utils import enviar_reporte_diario

app = Flask(__name__)
app.secret_key = os.urandom(24)


@app.route("/")
def index():
    return redirect(url_for("asistente"))


@app.route("/download_informe")
def download_informe():
    md = session.get("last_report_md")
    if not md:
        flash("No hay informe disponible para descargar.", "warning")
        return redirect(url_for("asistente"))
    # Prepara la respuesta como archivo .md
    return Response(
        md,
        mimetype="text/markdown",
        headers={
            "Content-Disposition": "attachment;filename=informe_inversion.md"
        }
    )


@app.route("/asistente", methods=["GET", "POST"])
def asistente():
    # --- Inicializaciones comunes ---
    historial  = session.get("asistente_history", [])
    perfil     = session.get("perfil", "")
    objetivo   = session.get("objetivo", "")
    modo       = session.get("modo", "conversacion")
    extendido  = session.get("extendido", False)
    has_report = "last_report_md" in session

    if request.method == "POST":
        texto = request.form["texto"].strip()
        modo  = request.form.get("modo", modo)
        session["modo"] = modo

        # === Parche: si no hay texto, es sólo un cambio de modo; recarga sin procesar chat ===
        if texto == "":
            return redirect(url_for("asistente"))

        # Si entramos al modo asesor, guardamos perfil/objetivo
        if modo == "asesor":
            perfil    = request.form.get("perfil", perfil)
            objetivo  = request.form.get("objetivo", objetivo).strip()
            extendido = request.form.get("extendido") == "on"
            session.update(perfil=perfil, objetivo=objetivo, extendido=extendido)

        # MODO CONVERSACIÓN
        if modo == "conversacion":
            # 1) Si es el primer POST y no existe ctx_base, lo calculamos aquí
            if "ctx_base" not in session:
                # 1a) Resumen fundamental
                base = "**Resumen Fundamental IBEX35**\n" + resumen_detallado() + "\n\n"
                # 1b) Crecimientos 1M / 1A
                base += "**Crecimientos**\n"
                for linea in resumen_acciones().split("\n"):
                    m1 = re.search(r"Crecimiento 1M:\s*([0-9\.]+%)", linea)
                    m2 = re.search(r"Cambio Últ\.\s*Año:\s*([0-9\.]+%)", linea)
                    if m1 or m2:
                        nombre = re.match(r"- \*\*(.*?)\*\*", linea).group(1)
                        if m1:
                            base += f"- {nombre}: 1M = {m1.group(1)}\n"
                        if m2:
                            base += f"- {nombre}: 1A = {m2.group(1)}\n"
                session["ctx_base"] = base

            # 2) Recuperamos el ctx_base ya en sesión
            ctx = session["ctx_base"]

            # 3) Añadimos “Mis acciones” con cálculo de ganancia
            owned = session.get("owned_stocks", {})
            ctx += "\n**Mis acciones**\n"
            if owned:
                for ticker, datos in owned.items():
                    shares = datos.get("shares", 0)
                    cost   = datos.get("cost", None)
                    current_price = precio_actual(ticker) or 0.0

                    if cost is not None:
                        gain_per_share = current_price - cost
                        total_gain     = gain_per_share * shares
                        ctx += (
                            f"- {ticker}: {shares} acciones, "
                            f"coste medio {cost:.2f} €, precio actual {current_price:.2f} €, "
                            f"ganancia total {total_gain:.2f} €\n"
                        )
                    else:
                        ctx += (
                            f"- {ticker}: {shares} acciones, "
                            f"precio actual {current_price:.2f} €\n"
                        )
            else:
                ctx += "- (ninguna)\n"


            # 4) Historial de las últimas 5 interacciones
            ctx += "\n**Historial Reciente**\n"
            for msg in historial[-5:]:
                ctx += f"Tú: {msg['user']}\nAsistente: {msg['assistant']}\n"

            # 5) Nueva pregunta
            ctx += f"\nTú: {texto}\nAsistente:"

            # 6) Llamamos al LLM
            respuesta = run_chatbot_task(ctx, texto)

        # MODO ASESOR IA
        else:
            if not perfil or not objetivo:
                respuesta = "<p class='text-danger'>Define perfil y objetivo primero.</p>"
                session.pop("last_report_md", None)
            else:
                data = resumen_acciones()
                if extendido:
                    md = run_extended_investment_crew(perfil, objetivo, data)
                else:
                    md = run_investment_crew(perfil, objetivo, data)
                session["last_report_md"] = md
                respuesta = markdown2.markdown(md)

        # Guardamos en historial
        historial.append({
            "user": texto,
            "assistant": respuesta,
            "modo": modo
        })
        session["asistente_history"] = historial
        has_report = "last_report_md" in session

    # Render (GET y POST)
    return render_template(
        "asistente.html",
        historial=historial,
        perfil=perfil,
        objetivo=objetivo,
        modo=modo,
        extendido=extendido,
        perfiles=["Bajo", "Moderado", "Alto"],
        has_report=has_report
    )


@app.route("/analisis_combinado", methods=["GET","POST"])
def analisis_combinado():
    empresas = list(empresas_ibex35.keys())
    selected_empresa = empresas[0]
    selected_tipo = "largo"  # Siempre predicción a 1 año
    grafico_prediccion = grafico_precio = grafico_rsi = None
    tabla_fundamental = None

    if request.method == "POST":
        selected_empresa = request.form.get("empresa")
        ticker = empresas_ibex35[selected_empresa]

        # 1) Predicción de precio (siempre largo)
        df_prophet = preparar_datos_prophet(ticker, anios=5)
        if df_prophet is not None and not df_prophet.empty:
            fig_pred = generar_prediccion(df_prophet, selected_tipo, selected_empresa)
            grafico_prediccion = fig_pred.to_html(
                include_plotlyjs="cdn",
                full_html=False,
                div_id="prediccion-plot"
            )

        # 2) Análisis técnico: Precio y medias
        tech = calcular_indicadores_tecnicos(ticker)
        if tech:
            fig_precio, fig_rsi = tech
            grafico_precio = fig_precio.to_html(
                include_plotlyjs=False,
                full_html=False,
                div_id="precio-plot"
            )
            grafico_rsi = fig_rsi.to_html(
                include_plotlyjs=False,
                full_html=False,
                div_id="rsi-plot"
            )

        # 3) Análisis fundamental
        tabla_fundamental = obtener_info_fundamental(ticker)

    return render_template(
        "combined_analysis_prediction.html",
        empresas=empresas,
        selected_empresa=selected_empresa,
        selected_tipo=selected_tipo,
        grafico_prediccion=grafico_prediccion,
        grafico_precio=grafico_precio,
        grafico_rsi=grafico_rsi,
        tabla_fundamental=tabla_fundamental
    )



@app.route("/rentabilidad", methods=["GET"])
def rentabilidad():
    df = obtener_rentabilidad_ibex35()
    tabla = df.to_dict(orient="records")
    columnas = list(df.columns)
    return render_template("rentabilidad.html", tabla=tabla, columnas=columnas)


@app.route("/mis_acciones", methods=["GET", "POST"])
def mis_acciones():
    tickers = list(empresas_ibex35.values())

    if request.method == "POST":
        owned = {}
        for t in tickers:
            cantidad = request.form.get(f"shares_{t}", type=int, default=0)
            raw_cost = request.form.get(f"cost_{t}", "").strip()
            # Si el usuario dejó el campo vacío, cost queda como None
            cost = float(raw_cost) if raw_cost not in ("", None) else None

            if cantidad > 0:
                owned[t] = {
                    "shares": cantidad,
                    "cost": cost  # None si no se indicó
                }

        session["owned_stocks"] = owned
        flash("Acciones guardadas correctamente.", "success")
        return redirect(url_for("mis_acciones"))

    # GET
    owned = session.get("owned_stocks", {})

    # Calculamos ganancia total de la cartera, solo para posiciones con coste
    ganancia_total = 0.0
    for t, datos in owned.items():
        actual = precio_actual(t) or 0.0
        if datos["cost"] is not None:
            gan_unit = actual - datos["cost"]
            ganancia_total += gan_unit * datos["shares"]

    return render_template(
        "mis_acciones.html",
        tickers=tickers,
        owned=owned,
        precio_actual=precio_actual,
        ganancia_total=ganancia_total
        
    )



@app.route("/enviar_reporte", methods=["POST"])
def enviar_reporte():
    emails_raw = request.form.get("emails", "")
    owned = session.get("owned_stocks", {})

    if not owned:
        flash("Debes guardar al menos una acción antes de enviar el reporte.", "danger")
        return redirect(url_for("mis_acciones"))

    if emails_raw.strip():
        emails = [e.strip() for e in emails_raw.split(",") if e.strip()]
        for email in emails:
            enviar_reporte_diario(email, owned)
        flash(f"Reporte enviado a: {', '.join(emails)} (simulado).", "success")
    else:
        flash("No se ingresaron correos; no se enviará reporte.", "info")

    return redirect(url_for("mis_acciones"))


if __name__ == "__main__":
    app.run(debug=True)
