"""
Comportamiento del parser: .md -> lineas de Ren'Py.

Tests de caracterizacion. No describen lo que el conversor DEBERIA hacer
sino lo que HACE hoy, para que cualquier cambio futuro sea una decision
consciente y no una regresion silenciosa.
"""

import pytest
from conftest import CORE


# =============================================================
# LABELS
# =============================================================

def test_label_forma_corta_una_linea(convert):
    c = convert("[label inicio]\nLara: Hola\n")
    assert c.code == ['label inicio:', 'l "Hola"']


def test_label_forma_clasica_dos_lineas(convert):
    c = convert("[label]\ninicio\nLara: Hola\n")
    assert c.code == ['label inicio:', 'l "Hola"']


def test_label_anidado_por_sangria(convert):
    c = convert(
        "[label escena]\n"
        "Lara: Hola\n"
        "    [label .secreto]\n"
        "    Ren: Chau\n"
    )
    assert c.code == [
        "label escena:",
        'l "Hola"',
        "label .secreto:",
        'r "Chau"',
    ]


def test_label_anidado_genera_sangria_de_4(convert):
    c = convert(
        "[label escena]\n"
        "Lara: Hola\n"
        "    [label .secreto]\n"
        "    Ren: Chau\n"
    )
    # el label hijo va a base_indent 0, su contenido a 1 (4 espacios)
    assert "        r \"Chau\"" in c.lines
    assert "    l \"Hola\"" in c.lines


def test_label_seguido_de_linea_vacia_se_ignora_con_aviso(convert):
    c = convert("[label]\n\nLara: Hola\n")
    assert any("seguido de linea vacia" in w for w in c.warnings)
    # como no queda ningun label valido, el archivo se envuelve en label start:
    assert c.code == ["label start:", 'l "Hola"']


def test_label_al_final_sin_nombre_se_ignora(convert):
    c = convert("Lara: Hola\n[label]\n")
    assert any("sin nombre" in w for w in c.warnings)


# =============================================================
# DIALOGO
# =============================================================

def test_dialogo_inline(convert):
    c = convert("[label a]\nLara: Hola\n")
    assert c.code == ["label a:", 'l "Hola"']


def test_dialogo_clasico_con_corchetes(convert):
    c = convert("[label a]\n[Lara]\nHola\n")
    assert c.code == ["label a:", 'l "Hola"']


def test_dialogo_no_distingue_mayusculas(convert):
    c = convert("[label a]\nLARA: Hola\n")
    assert c.code == ["label a:", 'l "Hola"']


def test_narrador_inline_sin_variable(convert):
    c = convert("[label a]\nNarrador: Habia una vez.\n")
    assert c.code == ["label a:", '"Habia una vez."']


def test_narrador_tambien_en_mayusculas(convert):
    c = convert("[label a]\nnarrador: Habia una vez.\n")
    assert c.code == ["label a:", '"Habia una vez."']


def test_narrador_clasico(convert):
    c = convert("[label a]\n[Narrador]\nTexto\n")
    assert c.code == ["label a:", '"Texto"']


def test_varios_personajes_encadenados_cada_uno_una_linea(convert):
    c = convert(
        "[label a]\n"
        "Narrador: La puerta se abrio.\n"
        "Lara: Quien anda ahi?\n"
        "Ren: Solo soy yo.\n"
    )
    assert c.code == [
        "label a:",
        '"La puerta se abrio."',
        'l "Quien anda ahi?"',
        'r "Solo soy yo."',
    ]


# =============================================================
# FUSION DE PARRAFOS
# =============================================================

def test_parrafo_inline_se_fusiona_con_salto_n(convert):
    c = convert("[label a]\nLara: Hola\ncomo estas?\nHace tiempo.\n")
    assert c.code == ["label a:", 'l "Hola\\ncomo estas?\\nHace tiempo."']


def test_parrafo_clasico_se_fusiona(convert):
    c = convert("[label a]\n[Lara]\nPrimera\nSegunda\n")
    assert c.code == ["label a:", 'l "Primera\\nSegunda"']


def test_linea_en_blanco_corta_el_parrafo(convert):
    c = convert("[label a]\nLara: Uno\n\nLara: Dos\n")
    assert c.code == ["label a:", 'l "Uno"', 'l "Dos"']


def test_repetir_el_mismo_nombre_corta_el_parrafo(convert):
    c = convert("[label a]\nLara: Uno\nLara: Dos\n")
    assert c.code == ["label a:", 'l "Uno"', 'l "Dos"']


def test_otro_personaje_corta_el_parrafo(convert):
    c = convert("[label a]\nLara: Uno\nRen: Dos\n")
    assert c.code == ["label a:", 'l "Uno"', 'r "Dos"']


def test_comando_corta_el_parrafo(convert):
    c = convert("[label a]\nLara: Uno\n[jump b]\n")
    assert c.code == ["label a:", 'l "Uno"', "jump b"]


# =============================================================
# SALTOS
# =============================================================

def test_jump(convert):
    c = convert("[label a]\n[jump destino]\n")
    assert c.code == ["label a:", "jump destino"]


def test_call(convert):
    c = convert("[label a]\n[call escena_secreta]\n")
    assert c.code == ["label a:", "call escena_secreta"]


def test_return(convert):
    c = convert("[label a]\n[return]\n")
    assert c.code == ["label a:", "return"]


def test_return_no_distingue_mayusculas(convert):
    c = convert("[label a]\n[Return]\n")
    assert c.code == ["label a:", "return"]


def test_jump_sin_destino_se_ignora_con_aviso(convert):
    c = convert("[label a]\n[jump   ]\n")
    assert any("sin destino" in w for w in c.warnings)


def test_salto_a_label_local(convert):
    c = convert("[label a]\n[jump .secreto]\n")
    assert c.code == ["label a:", "jump .secreto"]


# =============================================================
# COMENTARIOS Y ENLACES
# =============================================================

def test_comentario_simple(convert):
    c = convert("[label a]\n%% Lara Sprite Neutral %%\n")
    assert c.code == ["label a:", "# Lara Sprite Neutral"]


def test_comentario_bloque_multilinea(convert):
    c = convert("[label a]\n%%\nUno\nDos\n%%\nLara: Hola\n")
    assert c.code == ["label a:", "# Uno", "# Dos", 'l "Hola"']


def test_bloque_sin_cerrar_avisa_pero_no_rompe(convert):
    c = convert("[label a]\n%%\nUno\n")
    assert any("sin cierre" in w for w in c.warnings)
    assert "# Uno" in c.code


def test_enlaces_obsidian_se_ignoran(convert):
    c = convert("[label a]\n[[Acto 2]]\nLara: Hola\n")
    assert c.code == ["label a:", 'l "Hola"']


# =============================================================
# MENUS
# =============================================================

def test_menu_forma_corta(convert):
    c = convert(
        "[label a]\n"
        "[menu]\n"
        "[Opcion A]\n"
        "Lara: Camino A\n"
        "[end menu]\n"
    )
    assert c.code == [
        "label a:",
        "menu:",
        '"Opcion A":',
        'l "Camino A"',
    ]


def test_menu_forma_clasica_con_dos_puntos(convert):
    c = convert(
        "[label a]\n"
        "menu:\n"
        "[Opcion A]\n"
        "Lara: Camino A\n"
        "[end menu]\n"
    )
    assert c.code == ["label a:", "menu:", '"Opcion A":', 'l "Camino A"']


def test_opcion_vacia_genera_pass(convert):
    c = convert(
        "[label a]\n[menu]\n[Opcion A]\n[Opcion B]\n[end menu]\n"
    )
    assert c.code == [
        "label a:",
        "menu:",
        '"Opcion A":',
        "pass",
        '"Opcion B":',
        "pass",
    ]


def test_opcion_con_contenido_no_genera_pass(convert):
    c = convert(
        "[label a]\n[menu]\n[Opcion A]\nLara: Camino A\n[end menu]\n"
    )
    assert c.code == ["label a:", "menu:", '"Opcion A":', 'l "Camino A"']


def test_jump_dentro_de_opcion_es_contenido_no_opcion(convert):
    c = convert(
        "[label a]\n[menu]\n[Opcion A]\n[jump final]\n[Opcion B]\n[end menu]\n"
    )
    assert c.code == [
        "label a:",
        "menu:",
        '"Opcion A":',
        "jump final",
        '"Opcion B":',
        "pass",
    ]


def test_personaje_dentro_de_menu_no_es_opcion(convert):
    """Regla 7 de sintaxis.txt: [Lara] dentro de un menu es cambio de
    hablante, no una opcion, porque Lara es un personaje configurado."""
    c = convert("[label a]\n[menu]\n[Opcion A]\n[Lara]\nHola\n[end menu]\n")
    assert c.code == ["label a:", "menu:", '"Opcion A":', 'l "Hola"']


def test_menu_sin_end_menu_avisa(convert):
    c = convert("[label a]\n[menu]\n[Opcion A]\nLara: Hola\n")
    assert any("sin '[end menu]'" in w for w in c.warnings)


def test_end_menu_sin_menu_abierto_pasa_silencioso(convert):
    """Documenta una asimetria: [end menu] suelto no avisa nada."""
    c = convert("[label a]\n[end menu]\nLara: Hola\n")
    assert c.warnings == []
    assert c.code == ["label a:", 'l "Hola"']


# =============================================================
# ESCAPADO
# =============================================================

def test_escapa_comillas(convert):
    c = convert('[label a]\nLara: El dijo "hola"\n')
    assert c.code == ['label a:', 'l "El dijo \\"hola\\""']


def test_escapa_backslash(convert):
    c = convert("[label a]\nLara: C:\\directorio\n")
    assert c.code == ["label a:", 'l "C:\\\\directorio"']


# =============================================================
# PERSONAJES DESCONOCIDOS / STOP CHARACTER
# =============================================================

def test_nombre_desconocido_avisa_y_sigue_con_el_hablante_actual(convert):
    """Tras un corte de parrafo, un 'Nombre:' desconocido avisa y su texto
    se le pega al hablante que estaba hablando. OJO: el texto del nombre
    queda literal adentro del dialogo ("l 'Fantasma: Quien soy'"), no se
    descarta. Ver test_nombre_desconocido_se_absorbe_sin_aviso."""
    c = convert("[label a]\nLara: Hola\n\nFantasma: Quien soy\n")
    assert any("Fantasma" in w for w in c.warnings)
    assert c.code == ["label a:", 'l "Hola"', 'l "Fantasma: Quien soy"']


def test_nombre_desconocido_al_inicio_avisa_y_es_narracion(convert):
    c = convert("[label a]\nFantasma: Quien soy\n")
    assert any("Fantasma" in w for w in c.warnings)
    assert c.code == ["label a:", '"Fantasma: Quien soy"']


def test_nombre_desconocido_se_absorbe_sin_aviso(convert):
    """COMPORTAMIENTO ACTUAL, probablemente no deseado: si el 'Nombre:'
    desconocido va pegado a la linea anterior (sin blanco de por medio),
    collect_paragraph se lo come como texto de continuacion. No hay
    aviso, la etiqueta queda literal adentro del dialogo y el hablante
    real no cambia."""
    c = convert("[label a]\nLara: Hola\nFantasma: Quien soy\n")
    assert c.warnings == []
    assert c.code == ["label a:", 'l "Hola\\nFantasma: Quien soy"']


def test_nombre_desconocido_dentro_de_menu_se_convierte_en_opcion(convert):
    """COMPORTAMIENTO ACTUAL: dentro de un menu, cualquier [Nombre] que no
    sea personaje ni comando se interpreta como opcion (regla 7), sin
    avisar. Un nombre mal escrito se vuelve una opcion del menu."""
    c = convert("[label a]\n[menu]\n[Fantasma]\nHola\n[end menu]\n")
    assert c.warnings == []
    assert c.code == ["label a:", "menu:", '"Fantasma":', '"Hola"']


def test_corchete_desconocido_avisa_y_se_ignora_la_marca(convert):
    c = convert("[label a]\n[Fantasma]\nQuien soy\n")
    assert any("Fantasma" in w for w in c.warnings)
    assert c.code == ["label a:", '"Quien soy"']


def test_horas_no_confunden_con_personaje(convert):
    """'12:30' no es un personaje: la heuristica exige <=3 palabras."""
    c = convert("[label a]\nLara: Nos vemos a las 12:30\n")
    assert c.warnings == []
    assert c.code == ["label a:", 'l "Nos vemos a las 12:30"']


def test_stop_character_con_hablante_nuevo_no_avisa(convert):
    c = convert(
        "[label a]\n"
        "[Lara]\nYa no puedo mas.\n"
        "[stop character]\n"
        "Narrador: Silencio.\n"
    )
    assert c.warnings == []
    assert c.code == ["label a:", 'l "Ya no puedo mas."', '"Silencio."']


def test_stop_character_sin_hablante_nuevo_avisa(convert):
    c = convert(
        "[label a]\n"
        "[Lara]\nYa no puedo mas.\n"
        "[stop character]\n"
        "Silencio.\n"
    )
    assert any("stop character" in w for w in c.warnings)
    assert c.code == ["label a:", 'l "Ya no puedo mas."', '"Silencio."']


def test_stop_character_no_genera_codigo(convert):
    c = convert("[label a]\nLara: Hola\n[stop character]\n")
    assert "stop" not in c.text


# =============================================================
# ARCHIVOS SIN LABEL
# =============================================================

def test_archivo_sin_label_se_envuelve_en_label_start(convert):
    c = convert("Lara: Hola\n")
    assert c.code == ["label start:", 'l "Hola"']


def test_archivo_sin_label_avisa_del_envoltura(convert):
    c = convert("Lara: Hola\n")
    assert any("label start" in w for w in c.warnings)


# =============================================================
# MISC
# =============================================================

def test_acentos_y_enye_se_conservan(convert):
    c = convert("[label a]\nLara: ¿Cómo estás? Mañana.\n")
    assert c.code == ["label a:", 'l "¿Cómo estás? Mañana."']


def test_lectura_tolerant_a_utf8(convert):
    c = convert("[label a]\nLara: ¿Qué tal?\n")
    assert "¿Qué tal?" in c.text


@pytest.mark.parametrize("filename", ["guion.md", "guion.txt"])
def test_extensiones_md_y_txt(convert, filename):
    c = convert("[label a]\nLara: Hola\n", filename=filename)
    assert c.code == ["label a:", 'l "Hola"']


def test_lectura_de_txt_en_cp1252(tmp_path):
    """Un .txt hecho con el Bloc de notas de Windows viene en ANSI."""
    md = tmp_path / "ventano.txt"
    md.write_bytes("Lara: \u00bfC\u00f3mo est\u00e1s?\n".encode("cp1252"))
    rpy = tmp_path / "ventano.rpy"
    CORE.convert_file(str(md), str(rpy), {"Lara": "l"})
    text = rpy.read_text(encoding="utf-8")
    assert "¿Cómo estás?" in text
