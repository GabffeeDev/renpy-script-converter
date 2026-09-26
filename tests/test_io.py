"""
Escritura del .rpy y del snapshot incremental.

Aca se prueba el contrato con disco: que se escribe, que NO se escribe
y que el snapshot queda donde el proximo merge lo va a buscar.
"""

import os
import shutil

import pytest
from conftest import CORE, CHARS

MD_A = "[label a]\nLara: Uno\nLara: Dos\n"


def write_md(tmp_path, text, name="guion.md"):
    md = tmp_path / name
    md.write_text(text, encoding="utf-8")
    return md


def convert(md_path, tmp_path, characters=None):
    """Convierte y devuelve (rpy_path, logs, WriteResult)."""
    rpy = tmp_path / (os.path.splitext(md_path.name)[0] + ".rpy")
    logs = []
    result = CORE.convert_file(
        str(md_path), str(rpy),
        CHARS if characters is None else characters,
        log_fn=logs.append,
    )
    return rpy, logs, result


# =============================================================
# CREACION
# =============================================================

def test_primer_conversion_crea_el_archivo(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, res = convert(md, tmp_path)
    assert rpy.exists()
    assert res.created is True
    assert res.added > 0


def test_primer_conversion_guarda_el_snapshot(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)
    cache = CORE.get_cache_path(str(rpy))
    assert os.path.exists(cache)
    assert cache.endswith(".md_to_rpy_cache" + os.sep + "guion.rpy.base")


def test_el_snapshot_guarda_lo_que_se_genero_no_el_merge(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)
    base = open(CORE.get_cache_path(str(rpy)), encoding="utf-8").read()
    assert 'l "Uno"' in base and 'l "Dos"' in base


# =============================================================
# RECONVERSION SIN CAMBIOS
# =============================================================

def test_reconvertir_sin_cambios_no_reporta_nada(tmp_path):
    md = write_md(tmp_path, MD_A)
    convert(md, tmp_path)
    rpy, _, res = convert(md, tmp_path)
    assert res.changed == 0
    assert res.conflicts == 0
    assert res.created is False


def test_reconvertir_sin_cambios_deja_el_archivo_identico(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)
    antes = rpy.read_text(encoding="utf-8")
    convert(md, tmp_path)
    assert rpy.read_text(encoding="utf-8") == antes


# =============================================================
# EDICION MANUAL PRESERVADA (la garantia central)
# =============================================================

def test_edicion_manual_sobrevive_a_la_reconversion(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    texto = rpy.read_text(encoding="utf-8").replace(
        'l "Dos"', 'l "Dos (mi version)"'
    )
    rpy.write_text(texto, encoding="utf-8")

    convert(md, tmp_path)
    assert 'l "Dos (mi version)"' in rpy.read_text(encoding="utf-8")


def test_linea_agregada_a_mano_sobrevive(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    texto = rpy.read_text(encoding="utf-8")
    texto = texto.replace(
        '    l "Dos"',
        '    l "Dos"\n    # TODO: revisar esta escena',
    )
    rpy.write_text(texto, encoding="utf-8")

    convert(md, tmp_path)
    assert "# TODO: revisar esta escena" in rpy.read_text(encoding="utf-8")


# =============================================================
# CONFLICTOS
# =============================================================

def test_conflicto_no_sobreescribe_el_rpy(tmp_path):
    """Si editas a mano la misma linea que ademas cambiaste en el .md, el
    conversor se abstiene de escribir. El archivo tiene que quedar
    byte a byte igual."""
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    rpy.write_text(
        rpy.read_text(encoding="utf-8").replace('l "Dos"', 'l "DOS EDITADO"'),
        encoding="utf-8",
    )
    antes = rpy.read_bytes()

    write_md(tmp_path, "[label a]\nLara: Uno\nLara: Tres\n")
    _, _, res = convert(md, tmp_path)

    assert res.conflicts == 1
    assert rpy.read_bytes() == antes


def test_conflicto_no_actualiza_el_snapshot(tmp_path):
    """Si no se escribio, el snapshot tiene que seguir siendo el viejo,
    asi el proximo intento vuelve a intentar el mismo diff."""
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)
    base_path = CORE.get_cache_path(str(rpy))
    base_antes = open(base_path, encoding="utf-8").read()

    rpy.write_text(
        rpy.read_text(encoding="utf-8").replace('l "Dos"', 'l "DOS EDITADO"'),
        encoding="utf-8",
    )
    write_md(tmp_path, "[label a]\nLara: Uno\nLara: Tres\n")
    convert(md, tmp_path)

    assert open(base_path, encoding="utf-8").read() == base_antes


# =============================================================
# INCREMENTAL
# =============================================================

def test_linea_nueva_del_md_se_agrega(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    write_md(tmp_path, MD_A + "Lara: Tres\n")
    _, _, res = convert(md, tmp_path)

    assert res.added == 1
    assert 'l "Tres"' in rpy.read_text(encoding="utf-8")


def test_edicion_del_md_reemplaza_solo_esa_linea(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    write_md(tmp_path, "[label a]\nLara: Uno\nLara: Cambiada\n")
    _, _, res = convert(md, tmp_path)

    texto = rpy.read_text(encoding="utf-8")
    assert 'l "Cambiada"' in texto
    assert 'l "Dos"' not in texto
    assert 'l "Uno"' in texto
    assert res.replaced >= 1


# =============================================================
# BOOTSTRAP (no hay snapshot)
# =============================================================

def test_sin_snapshot_hace_bootstrap_y_no_pisa_nada(tmp_path):
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    rpy.write_text(
        rpy.read_text(encoding="utf-8").replace(
            '    l "Dos"', '    l "Dos"\n    # mio'
        ),
        encoding="utf-8",
    )

    # se borra el snapshot: se simula un .rpy traido de otra parte
    shutil.rmtree(tmp_path / CORE.CACHE_DIR_NAME)
    assert not os.path.exists(CORE.get_cache_path(str(rpy)))

    _, _, res = convert(md, tmp_path)
    texto = rpy.read_text(encoding="utf-8")
    assert res.bootstrapped is True
    assert "# mio" in texto


def test_bootstrap_no_borra_lineas_que_ya_no_estan_en_el_md(tmp_path):
    """Modo bootstrap es solo-agrega: si el .rpy tiene una escena que el
    .md ya no menciona, tiene que quedarse."""
    md = write_md(tmp_path, MD_A)
    rpy, _, _ = convert(md, tmp_path)

    texto = rpy.read_text(encoding="utf-8")
    texto += '\nlabel escena_que_no_esta_en_el_md:\n\n    "Hola"\n'
    rpy.write_text(texto, encoding="utf-8")

    shutil.rmtree(tmp_path / CORE.CACHE_DIR_NAME)
    convert(md, tmp_path)

    assert "label escena_que_no_esta_en_el_md:" in rpy.read_text(encoding="utf-8")


# =============================================================
# RUTAS DE CACHE
# =============================================================

def test_get_cache_path_live_al_lado_del_rpy(tmp_path):
    p = CORE.get_cache_path(str(tmp_path / "sub" / "guion.rpy"))
    assert p == str(
        tmp_path / "sub" / CORE.CACHE_DIR_NAME / "guion.rpy.base"
    )


@pytest.mark.parametrize("nombre", ["guion.md", "guion.txt"])
def test_snapshot_se_crea_para_md_y_txt(tmp_path, nombre):
    md = write_md(tmp_path, MD_A, nombre)
    rpy, _, _ = convert(md, tmp_path)
    assert os.path.exists(CORE.get_cache_path(str(rpy)))
