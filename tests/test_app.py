import pytest
from app import app

@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        with client.session_transaction() as sess:
            # Inicializar sesión si hace falta
            sess.clear()
        yield client

def test_index_redirect(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/asistente" in resp.headers["Location"]

def test_mis_acciones_get_empty(client):
    resp = client.get("/mis_acciones")
    assert resp.status_code == 200
    assert b"Registrar / Actualizar Acciones" in resp.data

def test_mis_acciones_post_and_report(client):
    # Registrar 10 acciones de BBVA sin coste
    resp = client.post("/mis_acciones", data={
        "shares_BBVA.MC": "10",
        "cost_BBVA.MC": ""
    }, follow_redirects=True)
    assert b"Acciones guardadas correctamente" in resp.data

    # Ahora enviar reporte
    resp2 = client.post("/enviar_reporte", data={
        "emails": "test@example.com"
    }, follow_redirects=True)
    assert b"Reporte enviado a:" in resp2.data

# Tests para /asistente, /analisis_combinado, etc., pueden simul­arse con texto mínimo
