import pandas as pd
import pytest
from data_utils import calcular_RSI, preparar_datos_prophet

def test_calcular_RSI_valores_constantes():
    # Si la serie es constante, el RSI debería tender a 50
    series = pd.Series([100] * 20)
    rsi = calcular_RSI(series, period=14)
    # En las últimas posiciones, RSI debería ser cercano a 50
    assert pytest.approx(50, rel=0.05) == rsi.iloc[-1]

def test_preparar_datos_prophet_empty(monkeypatch):
    # Simular que yf.download devuelve DataFrame vacío
    monkeypatch.setattr("data_utils.yf.download", lambda *args, **kwargs: pd.DataFrame())
    assert preparar_datos_prophet("FOO", anios=5) is None

# Puedes añadir más tests para generadores de predicción, indicadores, etc.
