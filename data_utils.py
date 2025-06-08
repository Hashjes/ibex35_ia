import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
from prophet import Prophet
from datetime import datetime
from cachetools import TTLCache, cached

# Diccionario de tickers del IBEX 35
empresas_ibex35 = {
    "Acciona": "ANA.MC",
    "Acciona Energías": "ANE.MC",
    "Acerinox": "ACX.MC",
    "ACS": "ACS.MC",
    "Aena": "AENA.MC",
    "Amadeus": "AMS.MC",
    "ArcelorMittal": "MTS.MC",
    "Banco Sabadell": "SAB.MC",
    "Banco Santander": "SAN.MC",
    "Bankinter": "BKT.MC",
    "BBVA": "BBVA.MC",
    "CaixaBank": "CABK.MC",
    "Cellnex": "CLNX.MC",
    "Colonial": "COL.MC",
    "Enagás": "ENG.MC",
    "Endesa": "ELE.MC",
    "Ferrovial": "FER.MC",
    "Fluidra": "FDR.MC",
    "Grifols": "GRF.MC",
    "IAG": "IAG.MC",
    "Iberdrola": "IBE.MC",
    "Inditex": "ITX.MC",
    "Indra": "IDR.MC",
    "Logista": "LOG.MC",
    "Mapfre": "MAP.MC",
    "Merlin Properties": "MRL.MC",
    "Naturgy": "NTGY.MC",
    "Puig": "PUIG.MC",
    "Redeia": "RED.MC",
    "Repsol": "REP.MC",
    "Rovi": "ROVI.MC",
    "Sacyr": "SCYR.MC",
    "Solaria": "SLR.MC",
    "Telefónica": "TEF.MC",
    "Unicaja": "UNI.MC"
}

def descargar_historico(ticker: str, start: str, end: str) -> pd.DataFrame:
    """
    Descarga datos históricos de Yahoo Finance para el ticker entre fechas start y end.
    Devuelve un DataFrame con columna 'Precio'.
    """
    try:
        data = yf.download(ticker, start=start, end=end, progress=False)
    except Exception:
        return pd.DataFrame()
    if data.empty:
        return data
    precio_col = "Adj Close" if "Adj Close" in data.columns else "Close"
    data = data.rename(columns={precio_col: "Precio"})
    return data[["Precio"]].copy()

def generar_figura_historica(df: pd.DataFrame, nombre_empresa: str) -> go.Figure:
    """
    Genera un gráfico Plotly de la evolución histórica de precios para df.
    """
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df["Precio"],
        mode="lines",
        name=f'Precio {nombre_empresa}'
    ))
    fig.update_layout(
        title=f"Evolución Histórica de {nombre_empresa}",
        xaxis_title="Fecha",
        yaxis_title="Precio (€)",
        template="plotly_white"
    )
    return fig

def preparar_datos_prophet(ticker: str, anios: int = 5) -> pd.DataFrame | None:
    """
    Prepara DataFrame para Prophet: columnas 'ds' y 'y' con los últimos 'anios' años.
    """
    try:
        data_full = yf.download(
            ticker,
            start="2000-01-01",
            end=(datetime.today() + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
            progress=False
        )
    except Exception:
        return None
    if data_full.empty:
        return None
    precio_col = "Adj Close" if "Adj Close" in data_full.columns else "Close"
    data_full["Precio"] = data_full[precio_col]
    fecha_lim = datetime.today() - pd.DateOffset(years=anios)
    data_reciente = data_full[data_full.index >= fecha_lim].copy()
    if data_reciente.empty:
        return None
    df_prophet = data_reciente.reset_index()[["Date", "Precio"]].dropna()
    df_prophet.rename(columns={"Date": "ds", "Precio": "y"}, inplace=True)
    return df_prophet

def generar_prediccion(df_prophet: pd.DataFrame, tipo: str, nombre_empresa: str) -> go.Figure:
    """
    Ajusta un modelo Prophet sobre df_prophet. 'tipo' = "corto" (30 días) o "largo" (365 días).
    Devuelve un Figure con:
      - Banda de incertidumbre suavizada (lower_smooth, upper_smooth)
      - Línea de predicción media suavizada (yhat_smooth)
      - Línea histórico real (y)
    El primer punto de la predicción coincide exactamente con el último dato histórico, para que no haya desconexión.
    """
    model = Prophet()
    model.fit(df_prophet)

    periodo = 30 if tipo == "corto" else 365
    future = model.make_future_dataframe(periods=periodo)
    forecast = model.predict(future)

    ultimo = df_prophet["ds"].max()
    y_ultimo = df_prophet["y"].iloc[-1]

    forecast_sel = forecast[forecast["ds"] >= ultimo].copy()

    forecast_sel["yhat_smooth"] = forecast_sel["yhat"].rolling(window=7, min_periods=1, center=True).mean()
    forecast_sel["lower_smooth"] = forecast_sel["yhat_lower"].rolling(window=7, min_periods=1, center=True).mean()
    forecast_sel["upper_smooth"] = forecast_sel["yhat_upper"].rolling(window=7, min_periods=1, center=True).mean()

    punto_inicio = pd.DataFrame({
        "ds": [ultimo],
        "yhat_smooth": [y_ultimo],
        "lower_smooth": [y_ultimo],
        "upper_smooth": [y_ultimo]
    })

    forecast_sel = pd.concat([punto_inicio, forecast_sel], ignore_index=True)
    forecast_sel.sort_values(by="ds", inplace=True)
    forecast_sel.reset_index(drop=True, inplace=True)

    fig = go.Figure()

    # Banda de incertidumbre suavizada
    fig.add_trace(go.Scatter(
        x=forecast_sel["ds"],
        y=forecast_sel["upper_smooth"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        name="Upper (suavizado)"
    ))
    fig.add_trace(go.Scatter(
        x=forecast_sel["ds"],
        y=forecast_sel["lower_smooth"],
        mode="lines",
        fill="tonexty",
        fillcolor="rgba(0, 100, 80, 0.2)",
        line=dict(width=0),
        showlegend=True,
        name="Intervalo confianza"
    ))

    # Línea de predicción media suavizada
    fig.add_trace(go.Scatter(
        x=forecast_sel["ds"],
        y=forecast_sel["yhat_smooth"],
        mode="lines",
        line=dict(color="darkgreen", width=2),
        name="Predicción (suavizada)"
    ))

    # Línea histórico real
    fig.add_trace(go.Scatter(
        x=df_prophet["ds"],
        y=df_prophet["y"],
        mode="lines",
        line=dict(color="black", width=1),
        name="Histórico real"
    ))

    titulo = "Predicción" + (" 30 días" if tipo == "corto" else " 1 año")
    fig.update_layout(
        title=f"{titulo} para {nombre_empresa}",
        xaxis_title="Fecha",
        yaxis_title="Precio (€)",
        template="plotly_white"
    )

    return fig

def calcular_RSI(serie: pd.Series, period: int = 14) -> pd.Series:
    """
    Calcula el RSI de una serie de precios. Para series constantes (sin cambios),
    devuelve 50 en lugar de NaN.
    """
    delta = serie.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Rellenar valores NaN (p.ej. avg_gain=avg_loss=0) con 50
    rsi = rsi.fillna(50)

    return rsi


def calcular_indicadores_tecnicos(ticker: str) -> tuple[go.Figure, go.Figure] | None:
    """
    Descarga histórico de 1 año y calcula SMA50, SMA200, RSI.
    Retorna (fig_precio, fig_rsi) o None si no hay datos.
    """
    end = datetime.today().strftime("%Y-%m-%d")
    start = (datetime.today() - pd.DateOffset(years=1)).strftime("%Y-%m-%d")
    df = descargar_historico(ticker, start, end)
    if df is None or df.empty:
        return None

    df["SMA50"] = df["Precio"].rolling(window=50).mean()
    df["SMA200"] = df["Precio"].rolling(window=200).mean()
    df["RSI"] = calcular_RSI(df["Precio"])

    fig_precio = go.Figure()
    fig_precio.add_trace(go.Scatter(
        x=df.index,
        y=df["Precio"],
        mode="lines",
        name="Precio"
    ))
    fig_precio.add_trace(go.Scatter(
        x=df.index,
        y=df["SMA50"],
        mode="lines",
        name="SMA 50"
    ))
    fig_precio.add_trace(go.Scatter(
        x=df.index,
        y=df["SMA200"],
        mode="lines",
        name="SMA 200"
    ))
    fig_precio.update_layout(
        title=f"Análisis Técnico: {ticker}",
        xaxis_title="Fecha",
        yaxis_title="Precio (€)",
        template="plotly_white"
    )

    fig_rsi = go.Figure()
    fig_rsi.add_trace(go.Scatter(
        x=df.index,
        y=df["RSI"],
        mode="lines",
        name="RSI"
    ))
    fig_rsi.update_layout(
        title=f"RSI para {ticker}",
        xaxis_title="Fecha",
        yaxis_title="RSI",
        template="plotly_white"
    )

    return fig_precio, fig_rsi

def obtener_info_fundamental(ticker: str) -> dict:
    """
    Obtiene información fundamental (P/E, P/B, dividend yield, etc.).
    Normaliza Dividend Yield si viene > 1.
    """
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception:
        return {}

    # Normalizamos Dividend Yield
    dy_raw = info.get("dividendYield", None)
    if dy_raw is not None:
        try:
            dy_val = float(dy_raw)
            if dy_val > 1:
                dy_val = dy_val / 100
            dividend_yield = round(dy_val * 100, 2)
        except:
            dividend_yield = "N/A"
    else:
        dividend_yield = "N/A"

    datos = {
        "Nombre": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "País": info.get("country", "N/A"),
        "P/E (TTM)": info.get("trailingPE", "N/A"),
        "P/B": info.get("priceToBook", "N/A"),
        "Dividend Yield (%)": dividend_yield,
        "Beta": info.get("beta", "N/A"),
        "Market Cap": f"{info.get('marketCap', 0)/1e9:.2f}B €" if info.get("marketCap") else "N/A"
    }
    return datos

def resumen_acciones() -> str:
    """
    Compila un resumen en texto de todas las empresas del IBEX35:
    Precio actual, Dividend Yield, Market Cap, Crecimiento último mes.
    """
    resumen = ""
    for nombre, ticker in empresas_ibex35.items():
        try:
            accion = yf.Ticker(ticker)
            df_1d = accion.history(period="1d")
            precio_actual = df_1d["Close"].iloc[-1] if not df_1d.empty else None
            precio_str = f"{precio_actual:.2f}" if precio_actual is not None else "N/A"
            info = accion.info or {}
            dy = info.get("dividendYield")
            if dy is not None:
                try:
                    # Normalizamos si viene >1
                    if dy > 1:
                        dy = dy / 100
                    dy_str = f"{dy*100:.2f}%"
                except:
                    dy_str = "N/A"
            else:
                dy_str = "N/A"
            mc = info.get("marketCap")
            mc_str = f"{mc/1e6:.0f} M€" if mc is not None else "N/A"
            df_1m = accion.history(period="1mo")
            if not df_1m.empty and len(df_1m["Close"]) >= 2:
                precio_ini = df_1m["Close"].iloc[0]
                precio_fin = df_1m["Close"].iloc[-1]
                crecimiento = ((precio_fin - precio_ini)/precio_ini)*100
                crecimiento_str = f"{crecimiento:.2f}%"
            else:
                crecimiento_str = "N/A"
            resumen += (
                f"- **{nombre}** ({ticker}): Precio: {precio_str} €, "
                f"Dividend Yield: {dy_str}, Market Cap: {mc_str}, Crecimiento 1M: {crecimiento_str}\n"
            )
        except Exception:
            resumen += f"- **{nombre}** ({ticker}): Error obteniendo datos\n"
    return resumen
def resumen_detallado() -> str:
    """
    Genera un resumen extendido de todas las empresas del IBEX35,
    incluyendo precio actual, dividendo bruto (€) y porcentaje, y market cap.
    """
    resumen = ""
    for nombre, ticker in empresas_ibex35.items():
        # 1) Obtenemos precio actual
        try:
            df_1d = yf.Ticker(ticker).history(period="1d")
            precio = df_1d["Close"].iloc[-1]
        except:
            precio = None

        precio_str = f"{precio:.2f} €" if precio else "N/A"

        # 2) Dividendo bruto y %
        try:
            info = yf.Ticker(ticker).info or {}
            raw_div = info.get("trailingAnnualDividendRate") or info.get("dividendRate") or 0.0
            div_bruto = float(raw_div)
            div_pct = f"{(div_bruto / precio * 100):.2f}%" if precio else "N/A"
        except:
            div_bruto, div_pct = 0.0, "N/A"

        # 3) Market cap
        try:
            mc = info.get("marketCap")
            mc_str = f"{mc/1e9:.2f}B €" if mc else "N/A"
        except:
            mc_str = "N/A"

        resumen += (
            f"- **{nombre}** ({ticker}): Precio {precio_str}, "
            f"Dividendo {div_bruto:.2f} € ({div_pct}), Market Cap {mc_str}\n"
        )
    return resumen

def precio_actual(ticker: str) -> float | None:
    """
    Devuelve el precio de cierre más reciente (último día) para el ticker.
    """
    try:
        df = yf.Ticker(ticker).history(period="1d")
    except Exception:
        return None
    if df.empty:
        return None
    return df["Close"].iloc[-1]

# Cache para rentabilidad, TTL de 1 hora (3600 segundos)
rent_cache = TTLCache(maxsize=1, ttl=3600)

@cached(rent_cache)
def obtener_rentabilidad_ibex35() -> pd.DataFrame:
    """
    Compila un DataFrame con las métricas de rentabilidad/dividendos para cada empresa del IBEX35:
      - Precio actual (último cierre)
      - Dividendos Anuales
      - Rentabilidad Dividendaria (%) = (dividendos / precio) * 100
      - Capitalización (en miles de millones €)
      - Cambio en el último año (%)
    Se cachea 1 hora para no sobrecargar yfinance.
    """
    resultados = []

    for empresa, ticker in empresas_ibex35.items():
        precio_actual = None
        dividend = 0.0
        rentabilidad = None
        market_cap_str = "N/A"
        cambio = None

        # 1) Precio actual (último cierre)
        try:
            hist1d = yf.Ticker(ticker).history(period="1d")
            if not hist1d.empty:
                precio_actual = round(hist1d["Close"].iloc[-1], 2)
        except:
            precio_actual = None

        # 2) Info fundamental
        try:
            info_dict = yf.Ticker(ticker).info or {}
        except:
            info_dict = {}

        # 3) Dividendos anuales
        raw_div = info_dict.get("trailingAnnualDividendRate") or info_dict.get("dividendRate") or 0.0
        try:
            dividend = float(raw_div)
        except:
            dividend = 0.0

        # 4) Rentabilidad dividendaria
        if precio_actual is not None and dividend:
            try:
                rentabilidad = round((dividend / precio_actual) * 100, 2)
            except:
                rentabilidad = None

        # 5) Capitalización
        mc = info_dict.get("marketCap")
        if mc:
            try:
                market_cap_str = f"{mc / 1e9:.2f}B €"
            except:
                market_cap_str = "N/A"

        # 6) Cambio Últ. Año: usar history(period="1y") para mayor fiabilidad
        try:
            hist_year = yf.Ticker(ticker).history(period="1y")
            if not hist_year.empty:
                precio_year = hist_year["Close"].iloc[0]
                precio_actual_adj = precio_actual - dividend if (precio_actual is not None and dividend) else precio_actual
                if precio_year and precio_actual_adj is not None:
                    cambio = round(((precio_actual_adj - precio_year) / precio_year) * 100, 2)
                else:
                    cambio = None
            else:
                cambio = None
        except:
            cambio = None

        resultados.append({
            "Empresa": empresa,
            "Ticker": ticker,
            "Precio (€/acción)": precio_actual,
            "Dividendos Anuales (€/acción)": round(dividend, 2),
            "Rentab. Dividendaria (%)": rentabilidad,
            "Capitalización": market_cap_str,
            "Cambio Últ. Año (%)": cambio
        })

    return pd.DataFrame(resultados)

_resumen_cache = TTLCache(maxsize=1, ttl=3600)

@cached(_resumen_cache)
def resumen_detallado() -> str:
    resumen = ""
    for nombre, ticker in empresas_ibex35.items():
        accion = yf.Ticker(ticker)
        # 1) Intentar sacar info con try/except
        try:
            info = accion.info or {}
        except Exception:
            info = {}

        # 2) Precio actual
        try:
            df_1d = accion.history(period="1d")
            precio = df_1d["Close"].iloc[-1] if not df_1d.empty else 0
        except Exception:
            precio = 0.0

        # 3) Dividendos brutos y porcentaje
        try:
            raw_div = info.get("trailingAnnualDividendRate") or info.get("dividendRate") or 0.0
            div_bruto = float(raw_div)
        except Exception:
            div_bruto = 0.0
        pct = round(div_bruto / precio * 100, 2) if precio else 0.0

        # 4) Market cap por defecto
        try:
            mc = info.get("marketCap", 0)
            mc_b = mc / 1e9
        except Exception:
            mc_b = 0.0

        resumen += (
            f"- **{nombre}** ({ticker}): "
            f"Precio {precio:.2f} €, "
            f"Dividendo {div_bruto:.2f} € ({pct}% ), "
            f"Market Cap {mc_b:.2f} B€\n"
        )
    return resumen
