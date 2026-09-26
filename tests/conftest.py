"""
Fixtures compartidos de la suite.

Los modulos bajo prueba se importan ACA y se reexportan, para que ningun
test dependa de la estructura de archivos del proyecto.
"""

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import config as CONFIG  # noqa: E402
import converter as CORE  # noqa: E402

# Tabla de personajes usada por defecto en los tests del parser.
CHARS = {
    "Lara": "l",
    "Ren": "r",
    "???": "un",
    "Doctor": "d",
}


class Conversion:
    """Resultado de una conversion, con las tres cosas que importan:
    el .rpy escrito, los avisos del log y el WriteResult."""

    def __init__(self, text, logs, result):
        self.text = text
        self.logs = logs
        self.result = result

    @property
    def lines(self):
        return self.text.split("\n") if self.text is not None else []

    @property
    def code(self):
        """Solo las lineas con contenido, sin sangria. Para assert de
        contenido y orden, que es lo que suele importar."""
        return [line.strip() for line in self.lines if line.strip()]

    @property
    def warnings(self):
        return [line for line in self.logs if "! Aviso" in line]

    def __repr__(self):
        return f"<Conversion {self.code!r}>"


@pytest.fixture
def convert(tmp_path):
    """Escribe un .md, lo convierte y devuelve el Conversion."""

    def _convert(md_text, characters=None, filename="guion.md"):
        characters = CHARS if characters is None else characters

        md_path = tmp_path / filename
        md_path.write_text(md_text, encoding="utf-8")

        rpy_path = tmp_path / (os.path.splitext(filename)[0] + ".rpy")
        logs = []

        result = CORE.convert_file(
            str(md_path), str(rpy_path), characters, log_fn=logs.append
        )

        text = rpy_path.read_text(encoding="utf-8") if rpy_path.exists() else None

        return Conversion(text, logs, result)

    return _convert


@pytest.fixture
def chars():
    return dict(CHARS)
