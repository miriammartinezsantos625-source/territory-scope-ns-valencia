"""Smoke test de la app Streamlit (sin navegador)."""
from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_app_arranca_y_responde_a_parametros():
    at = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py"), default_timeout=120).run()
    assert not at.exception
    assert len(at.tabs) == 5
    by_label = lambda els, lab: next(e for e in els if e.label == lab)  # noqa: E731
    by_label(at.radio, "Escenario").set_value("alto").run()
    assert not at.exception
    by_label(at.slider, "Potencial").set_value(0.0).run()
    by_label(at.slider, "Brecha").set_value(1.0).run()
    assert not at.exception
    assert any("Modo demo" in w.value for w in at.warning)
