"""
Merge incremental de 3 vias.

Estas funciones son puras (reciben y devuelven listas), asi que se testean
sin tocar disco. La garantia central del conversor es que una edicion
manual del .rpy NO se pisa cuando el .md no cambio.
"""

from conftest import CORE

merge_from_snapshot = CORE.merge_from_snapshot
merge_with_existing = CORE.merge_with_existing
find_sequence = CORE.find_sequence
find_nearby_insert_position = CORE.find_nearby_insert_position


BASE = ["label a:", "    x 1", "    x 2"]


# =============================================================
# CASOS CANONICOS
# =============================================================

def test_sin_cambios_no_toca_nada():
    merged, res = merge_from_snapshot(list(BASE), list(BASE), list(BASE))
    assert merged == BASE
    assert res.changed == 0
    assert res.conflicts == 0


def test_edicion_manual_se_preserva():
    """El caso que justifica todo el mecanismo: el .rpy tiene una linea
    extra que el .md nunca genero, y debe sobrevivir."""
    existing = ["label a:", "    x 1", "    # MI NOTA", "    x 2"]
    merged, res = merge_from_snapshot(existing, list(BASE), list(BASE))
    assert merged == existing
    assert res.changed == 0


def test_insert_al_final():
    new = BASE + ["    x 3"]
    merged, res = merge_from_snapshot(list(BASE), list(BASE), new)
    assert merged == new
    assert res.added == 1


def test_insert_al_principio():
    new = ["label a:", "    x 0", "    x 1", "    x 2"]
    merged, res = merge_from_snapshot(
        ["label a:", "    x 1", "    x 2"], list(BASE), new
    )
    assert merged == new
    assert res.added == 1


def test_delete():
    """Borrado real: la ultima linea desaparece del .md."""
    base = ["label a:", "    x 1", "    x 2", "    x 3"]
    new = ["label a:", "    x 1", "    x 2"]
    merged, res = merge_from_snapshot(list(base), base, new)
    assert merged == new
    assert res.deleted == 1


def test_replace_puede_duplicar_si_el_texto_ya_existe_mas_abajo():
    """COMPORTAMIENTO ACTUAL: cambiar 'x 2' por 'x 3' cuando el existing
    ya tiene un 'x 3' mas abajo NO se detecta como conflicto ni como
    duplicado a evitar. El replace es posicional a ciegas y deja las dos
    lineas iguales. No es un caso exotico: pasa si editas a mano la misma
    linea que cambiar en el .md."""
    existing = ["label a:", "    x 1", "    x 2", "    x 3"]
    new = ["label a:", "    x 1", "    x 3"]
    merged, res = merge_from_snapshot(existing, list(BASE), new)
    assert merged.count("    x 3") == 2
    assert res.conflicts == 0


def test_replace():
    new = ["label a:", "    x 1", "    x NUEVA"]
    merged, res = merge_from_snapshot(list(BASE), list(BASE), new)
    assert merged == new
    assert res.replaced == 1


def test_edicion_manual_sobrevive_a_un_replace_lejano():
    """Cambio en el .md + edicion manual en otra parte: conviven."""
    existing = ["label a:", "    # MI NOTA", "    x 1", "    x 2"]
    new = ["label a:", "    x 1", "    x NUEVA"]
    merged, res = merge_from_snapshot(existing, list(BASE), new)
    assert "    # MI NOTA" in merged
    assert "    x NUEVA" in merged
    assert res.conflicts == 0


# =============================================================
# CONFLICTOS
# =============================================================

def test_confecto_cuando_el_bloque_fue_editado_a_mano():
    """El .rpy tiene un bloque distinto de base Y el .md tambien lo
    cambio: no se puede saber cual gana, asi que se aborta."""
    existing = ["label a:", "    x MANUAL", "    x 2"]
    new = ["label a:", "    x OTRA", "    x 2"]
    merged, res = merge_from_snapshot(existing, list(BASE), new)
    assert res.conflicts == 1
    # el merge no aplica el cambio dudoso
    assert merged == existing


def test_cambios_contiguos_se_agrupan_en_un_solo_conflicto():
    """El contador de conflictos cuenta BLOQUES del diff, no lineas: dos
    lineas modificadas juntas son un unico opcode 'replace' y por lo tanto
    un solo conflicto."""
    existing = ["label a:", "    x M1", "    x M2"]
    new = ["label a:", "    x N1", "    x N2"]
    merged, res = merge_from_snapshot(existing, list(BASE), new)
    assert res.conflicts == 1
    assert merged == existing


# =============================================================
# CONTEO DE CAMBIOS
# =============================================================

def test_changed_suma_agregados_reemplazos_y_borrados():
    res = CORE.WriteResult(added=2, replaced=3, deleted=4)
    assert res.changed == 9


def test_lineas_vacias_no_cuentan_como_cambio():
    new = BASE + ["", "    x 3"]
    _, res = merge_from_snapshot(list(BASE), list(BASE), new)
    assert res.added == 1  # la linea vacia no se cuenta


# =============================================================
# BOOTSTRAP (sin snapshot previo)
# =============================================================

def test_bootstrap_solo_agrega_nunca_borra():
    existing = ['l "viejo"', 'r "otro"']
    new = ['l "viejo"', 'r "otro"', 'l "nuevo"']
    merged, added = merge_with_existing(existing, new)
    assert added == 1
    assert 'l "nuevo"' in merged
    assert len(merged) >= len(existing)


def test_bootstrap_no_toca_lo_que_ya_esta():
    existing = ['l "hola"']
    merged, added = merge_with_existing(existing, ['l "hola"'])
    assert added == 0
    assert merged == existing


def test_bootstrap_ignora_el_orden_y_no_deduplica_dentro_del_nuevo():
    existing = ['l "a"']
    new = ['l "b"', 'l "b"']
    merged, added = merge_with_existing(existing, new)
    assert added == 1
    assert merged.count('l "b"') == 1


# =============================================================
# HEURISTICAS DE POSICIONAMIENTO
# =============================================================

def test_find_sequence_encuentra_y_devuelve_indice():
    assert find_sequence(["a", "b", "c"], ["b", "c"]) == 1
    assert find_sequence(["a", "b", "c"], ["a", "b", "c"]) == 0


def test_find_sequence_respeta_el_cursor():
    assert find_sequence(["a", "a", "b"], ["a", "b"], 1) == 1


def test_find_sequence_no_encuentra_devuelve_menos_uno():
    assert find_sequence(["a", "b"], ["z"]) == -1


def test_find_sequence_de_Lista_vacia_no_se_mueve():
    assert find_sequence(["a", "b"], [], 0) == 0
    assert find_sequence(["a", "b"], [], 1) == 1


def test_find_nearby_insert_usa_el_bloque_previo():
    existing = ["linea mia", "    x 1", "    x 2"]
    base = ["    x 1", "    x 2"]
    pos = find_nearby_insert_position(existing, base, 0, 0)
    assert pos == 1


def test_find_nearby_insert_sin_ancla_va_al_final():
    """COMPORTAMIENTO ACTUAL: si no encuentra ni el bloque previo ni el
    siguiente, la insercion se hace al final del archivo sin avisar.
    Es un punto ciego del merge (no hay forma de saber donde iba)."""
    existing = ["nada que ver"]
    base = ["X", "Y"]
    pos = find_nearby_insert_position(existing, base, 0, 0)
    assert pos == len(existing)
