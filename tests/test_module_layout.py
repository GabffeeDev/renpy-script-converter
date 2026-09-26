"""
Garantias estructurales de la separacion de responsabilidades.

El nucleo (converter.py) y la config (config.py) tienen que poder
importarse sin tkinter: es lo que permite testearlos y reutilizarlos
sin abrir una ventana. Estos tests vigilan para que nadie rompa eso
por accidente metiendo un import arriba.
"""

import subprocess
import sys

import pytest

from conftest import ROOT


def source(name):
    with open(f"{ROOT}/{name}", encoding="utf-8") as f:
        return f.read()


@pytest.mark.parametrize("modulo", ["converter.py", "config.py"])
@pytest.mark.parametrize("prohibido", ["tkinter", "customtkinter"])
def test_el_nucleo_no_importa_tkinter(modulo, prohibido):
    assert prohibido not in source(modulo), f"{modulo} no debe tocar {prohibido}"


@pytest.mark.parametrize("modulo", ["converter.py", "config.py"])
def test_importar_el_nucleo_no_carga_tkinter_en_memoria(modulo):
    """Mas fuerte que greppear el source: se comprueba en el interprete
    real, en un proceso limpio."""
    code = (
        f"import {modulo[:-3]}, sys; "
        f"assert 'tkinter' not in sys.modules, 'tkinter se cargo'; "
        f"assert 'customtkinter' not in sys.modules, 'customtkinter se cargo'"
    )
    r = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True
    )
    assert r.returncode == 0, r.stderr


def test_la_gui_depende_del_nucleo():
    texto = source("md_to_rpy_gui.py")
    assert "from converter import" in texto
    assert "from config import" in texto


def test_la_gui_no_reimplementa_logica_de_conversion():
    """Si aparece un 'def render' o 'def merge' en la GUI, la logica se
    duplico y hay que volver a moverla al nucleo."""
    texto = source("md_to_rpy_gui.py")
    for prohibido in ("def render", "def merge", "def write_rpy", "SequenceMatcher"):
        assert prohibido not in texto, f"la GUI no deberia definir {prohibido}"


def test_render_lines_no_toca_el_disco(tmp_path, monkeypatch):
    """El render puro se puede usar como vista previa: no escribe nada.
    Se monkeypatchea open() en modo escritura para que cualquier intento
    de escribir reviente el test."""
    import converter

    monkeypatch.chdir(tmp_path)
    lines = converter.render_lines(["[label a]", "Lara: Hola"], {"Lara": "l"})

    assert [l.strip() for l in lines if l.strip()] == ['label a:', 'l "Hola"']
    assert list(tmp_path.iterdir()) == []


def test_render_file_lee_del_disco_pero_no_escribe(tmp_path):
    import converter

    md = tmp_path / "guion.md"
    md.write_text("[label a]\nLara: Hola\n", encoding="utf-8")

    lines = converter.render_file(str(md), {"Lara": "l"})

    assert [l.strip() for l in lines if l.strip()] == ['label a:', 'l "Hola"']
    assert not (tmp_path / "guion.rpy").exists()
