"""
Configuracion persistente del usuario (personajes.json).

Se guarda al lado del .exe (o del .py si se corre sin compilar) para que
los personajes se editen desde la interfaz sin tocar codigo.
"""

import json
import os
import sys


# =============================================================
# RUTAS / CONFIGURACION
# =============================================================

def app_dir():
    """Carpeta donde vive el .exe (o el .py si se corre sin compilar)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "personajes.json")
DEFAULT_CHARACTERS = {
    "???": "who",
    "Ren": "r",
    "Doctor": "d",
    "Koharu": "k",
}


def load_config():
    defaults = {
        "characters": dict(DEFAULT_CHARACTERS),
        "last_md_dir": app_dir(),
        "last_output_dir": app_dir(),
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict) and isinstance(data.get("characters"), dict):
                    merged = dict(defaults)
                    merged.update(data)
                    chars = {}
                    for k, v in data["characters"].items():
                        if isinstance(k, str) and isinstance(v, str):
                            chars[k] = v
                    merged["characters"] = chars
                    return merged
        except (json.JSONDecodeError, OSError, AttributeError):
            pass

    return defaults


def save_config(config):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


