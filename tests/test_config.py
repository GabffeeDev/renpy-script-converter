"""
Persistencia de personajes.json y validacion de la tabla de personajes.
"""

import json

import pytest
from conftest import CONFIG, CORE

load_config = CONFIG.load_config
save_config = CONFIG.save_config
validate_character = CORE.validate_character


@pytest.fixture
def config_path(tmp_path, monkeypatch):
    """Redirige CONFIG_PATH a un archivo temporal para no tocar el
    personajes.json real del usuario."""
    path = tmp_path / "personajes.json"
    monkeypatch.setattr(CONFIG, "CONFIG_PATH", str(path))
    return path


# =============================================================
# CARGA
# =============================================================

def test_sin_archivo_devuelve_defaults(config_path):
    cfg = load_config()
    assert cfg["characters"] == CONFIG.DEFAULT_CHARACTERS


def test_json_corrupto_cae_a_defaults(config_path):
    config_path.write_text("{esto no es json", encoding="utf-8")
    cfg = load_config()
    assert cfg["characters"] == CONFIG.DEFAULT_CHARACTERS


def test_lectura_correcta(config_path):
    config_path.write_text(
        json.dumps({"characters": {"Lara": "l"}, "last_output_dir": "D:/x"}),
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg["characters"] == {"Lara": "l"}
    assert cfg["last_output_dir"] == "D:/x"


def test_characters_que_no_es_dict_cae_a_defaults(config_path):
    config_path.write_text(
        json.dumps({"characters": ["no", "es", "dict"]}), encoding="utf-8"
    )
    assert load_config()["characters"] == CONFIG.DEFAULT_CHARACTERS


def test_filtra_entradas_con_tipos_raros(config_path):
    """Un personajes.json editado a mano puede tener cosas raras adentro;
    lo que no sea str/str se descarta en vez de romper la app."""
    config_path.write_text(
        json.dumps(
            {"characters": {"Lara": "l", "Ren": 5, "X": ["y"], "Doctor": "d"}}
        ),
        encoding="utf-8",
    )
    assert load_config()["characters"] == {"Lara": "l", "Doctor": "d"}


def test_las_llaves_faltantes_se_completan_con_defaults(config_path):
    config_path.write_text(
        json.dumps({"characters": {"Lara": "l"}}), encoding="utf-8"
    )
    cfg = load_config()
    assert cfg["last_md_dir"]
    assert cfg["last_output_dir"]


def test_acentos_en_los_nombres(config_path):
    config_path.write_text(
        json.dumps({"characters": {"Señor Ñoño": "n"}}, ensure_ascii=False),
        encoding="utf-8",
    )
    assert load_config()["characters"] == {"Señor Ñoño": "n"}


# =============================================================
# GUARDADO
# =============================================================

def test_roundtrip(config_path):
    cfg = {"characters": {"Lara": "l"}, "last_md_dir": "D:/a", "last_output_dir": "D:/b"}
    save_config(cfg)
    assert load_config() == cfg


def test_guarda_sin_escapar_unicode(config_path):
    """ensure_ascii=False: los nombres se leen nativos en el .json, que es
    justamente para editarlo a mano."""
    save_config({"characters": {"Señor": "s"}})
    assert "Señor" in config_path.read_text(encoding="utf-8")


def test_guardar_en_ruta_invalida_no_revienta(tmp_path, monkeypatch):
    """Un .json bloqueado o en una carpeta sin permisos no debe tirar la
    app; se ignora en silencio."""
    monkeypatch.setattr(
        CONFIG, "CONFIG_PATH", str(tmp_path / "no" / "existe" / "personajes.json")
    )
    save_config({"characters": {}})  # no debe levantar


# =============================================================
# VALIDACION
# =============================================================

def test_personaje_valido():
    ok, err = validate_character("Lara", "l", {})
    assert ok is True
    assert err == ""


def test_normaliza_espacios_y_mayusculas_en_la_variable():
    ok, _ = validate_character("Lara", "  L  ", {})
    assert ok is True


@pytest.mark.parametrize("nombre", ["", "   "])
def test_nombre_vacio_invalido(nombre):
    ok, err = validate_character(nombre, "l", {})
    assert ok is False
    assert "vac" in err.lower()


@pytest.mark.parametrize("variable", ["", "   "])
def test_variable_vacia_invalida(variable):
    ok, err = validate_character("Lara", variable, {})
    assert ok is False
    assert "vac" in err.lower()


@pytest.mark.parametrize("nombre", ["Narrador", "narrador", "NARRADOR"])
def test_narrador_esta_reservado(nombre):
    ok, err = validate_character(nombre, "n", {})
    assert ok is False
    assert "reservada" in err


@pytest.mark.parametrize("nombre", ["menu", "label", "return", "jump x", "call y"])
def test_nombre_que_choca_con_un_comando_invalido(nombre):
    ok, err = validate_character(nombre, "v", {})
    assert ok is False
    assert "choca" in err


@pytest.mark.parametrize(
    "variable", ["1abc", "con espacio", "a-b", "a.b", "ñ", "c++"]
)
def test_variable_con_formato_invalido(variable):
    ok, err = validate_character("Lara", variable, {})
    assert ok is False
    assert "valida" in err


@pytest.mark.parametrize("variable", ["menu", "show", "define", "jump", "narrador"])
def test_variable_reservada_de_renpy_invalida(variable):
    ok, err = validate_character("Lara", variable, {})
    assert ok is False
    assert "reservada" in err


def test_underscore_y_guiones_bajos_son_validos():
    ok, _ = validate_character("Lara", "lara_2", {})
    assert ok is True


def test_nombre_duplicado_invalido():
    ok, err = validate_character("Lara", "l2", {"Lara": "l"})
    assert ok is False
    assert "Ya existe" in err


def test_nombre_duplicado_no_distingue_mayusculas():
    ok, err = validate_character("LARA", "l2", {"Lara": "l"})
    assert ok is False
    assert "Ya existe" in err


def test_variable_duplicada_invalida():
    ok, err = validate_character("Ren", "l", {"Lara": "l"})
    assert ok is False
    assert "ya la usa" in err


def test_editando_una_fila_no_choca_consigo_misma():
    """Al editar 'Lara' -> 'Lara' no debe quejarse de que ya existe."""
    ok, err = validate_character("Lara", "l", {"Lara": "l"}, editing_name="Lara")
    assert ok is True
    assert err == ""


def test_editando_una_fila_sigue_chocando_con_otras():
    ok, err = validate_character("Lara", "l", {"Ren": "l"}, editing_name="Lara")
    assert ok is False
    assert "ya la usa" in err
