"""
Conversor Obsidian (.md) -> Ren'Py (.rpy)
Interfaz grafica con pestañas: Conversion + Personajes.

Los personajes se guardan en 'personajes.json', al lado del .exe/.py,
para que el usuario los edite desde la interfaz sin tocar codigo.
"""

import os
import re
import sys
import json
import threading
from dataclasses import dataclass
from difflib import SequenceMatcher

import customtkinter as ctk
from tkinter import filedialog, messagebox

# =============================================================
# RUTAS / CONFIGURACION
# =============================================================

def app_dir():
    """Carpeta donde vive el .exe (o el .py si se corre sin compilar)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_PATH = os.path.join(app_dir(), "personajes.json")
CACHE_DIR_NAME = ".md_to_rpy_cache"

DEFAULT_CHARACTERS = {
    "???": "who",
    "Ren": "r",
    "Doctor": "d",
    "Koharu": "k",
}

# Palabras reservadas / con significado especial en Ren'Py.
# No se pueden usar como variable de personaje porque generarian
# lineas ambiguas o directamente invalidas (ej: "menu "hola"").
RESERVED_WORDS = {
    "menu", "jump", "call", "label", "pass", "return", "if", "elif",
    "else", "while", "for", "in", "is", "not", "and", "or", "none",
    "true", "false", "scene", "show", "hide", "with", "play", "stop",
    "queue", "window", "define", "default", "init", "python", "image",
    "transform", "screen", "voice", "renpy", "config", "persistent",
    "store", "narrador",
}


def load_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "characters" in data:
                    return data
        except (json.JSONDecodeError, OSError):
            pass

    return {
        "characters": dict(DEFAULT_CHARACTERS),
        "last_md_dir": app_dir(),
        "last_output_dir": app_dir(),
    }


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


# =============================================================
# VALIDACION DE PERSONAJES
# =============================================================

VAR_PATTERN = re.compile(r"^[a-z_][a-z0-9_]*$")


def validate_character(name, variable, existing_characters, editing_name=None):
    """
    Devuelve (ok: bool, mensaje_error: str).
    existing_characters: dict actual {nombre: variable}
    editing_name: si se esta editando una fila existente, su nombre original,
                  para no chocar consigo misma.
    """
    name = name.strip()
    variable = variable.strip().lower()

    if not name:
        return False, "El nombre del personaje no puede estar vacio."

    if not variable:
        return False, "La variable no puede estar vacia."

    if name.lower() == "narrador":
        return False, "'Narrador' es una palabra reservada del sistema, no un personaje editable."

    if not VAR_PATTERN.match(variable):
        return False, (
            f"'{variable}' no es una variable valida. Usa solo minusculas, "
            "numeros y guion bajo, sin empezar por numero."
        )

    if variable in RESERVED_WORDS:
        return False, f"'{variable}' es una palabra reservada de Ren'Py y no se puede usar como variable."

    for existing_name, existing_var in existing_characters.items():
        if existing_name == editing_name:
            continue

        if existing_name.lower() == name.lower():
            return False, f"Ya existe un personaje llamado '{existing_name}'."

        if existing_var.lower() == variable:
            return False, f"La variable '{variable}' ya la usa '{existing_name}'."

    return True, ""


# =============================================================
# LOGICA DE CONVERSION (igual que el script original)
# =============================================================

@dataclass
class WriteResult:
    added: int = 0
    replaced: int = 0
    deleted: int = 0
    conflicts: int = 0
    bootstrapped: bool = False
    created: bool = False

    @property
    def changed(self):
        return self.added + self.replaced + self.deleted


def current_indent(base_indent, in_menu, current_option):
    if in_menu and current_option:
        return base_indent + 2
    return base_indent


def tabs(level):
    return "    " * level


def source_indent_level(line):
    expanded = line.expandtabs(4)
    leading_spaces = len(expanded) - len(expanded.lstrip(" "))
    return leading_spaces // 4


def update_label_stack(label_stack, source_indent):
    while label_stack and source_indent < label_stack[-1]:
        label_stack.pop()

    if label_stack:
        return label_stack[-1] + 1

    return 1


def finalize_menu_option(output, base_indent, option_has_content):
    if not option_has_content:
        output.append(f"{tabs(base_indent + 2)}pass")


def is_menu_command(name):
    lower = name.lower()
    return (
        lower == "label"
        or lower == "end menu"
        or lower.startswith("jump ")
        or lower.startswith("call ")
    )


def normalize_line(line):
    return line.strip()


def count_content_lines(lines):
    return len([line for line in lines if normalize_line(line)])


def read_text_lines(path):
    with open(path, "r", encoding="utf-8") as f:
        return [line.rstrip("\n\r") for line in f.readlines()]


def read_source_lines(path):
    """
    Lee un .md o .txt tolerando distintas codificaciones. Los .md de
    Obsidian siempre son UTF-8, pero un .txt hecho con el Bloc de notas
    de Windows puede venir en 'ANSI' (cp1252). Si ninguna calza, no
    revienta: reemplaza los caracteres invalidos para no perder el
    archivo entero por un caracter raro.
    """
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return [line.rstrip() for line in f]
        except UnicodeDecodeError:
            continue

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return [line.rstrip() for line in f]


def write_text_lines(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def get_cache_path(rpy_path):
    output_dir = os.path.dirname(os.path.abspath(rpy_path))
    cache_dir = os.path.join(output_dir, CACHE_DIR_NAME)
    return os.path.join(cache_dir, os.path.basename(rpy_path) + ".base")


def save_generation_snapshot(rpy_path, lines):
    cache_path = get_cache_path(rpy_path)
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    write_text_lines(cache_path, lines)


def find_sequence(lines, sequence, start=0):
    if not sequence:
        return start

    max_start = len(lines) - len(sequence)

    for index in range(max(start, 0), max_start + 1):
        if lines[index:index + len(sequence)] == sequence:
            return index

    return -1


def find_nearby_insert_position(lines, base_lines, base_index, start):
    before = base_lines[max(0, base_index - 6):base_index]
    after = base_lines[base_index:base_index + 6]

    before_pos = find_sequence(lines, before, start)

    if before and before_pos != -1:
        return before_pos + len(before)

    after_pos = find_sequence(lines, after, start)

    if after and after_pos != -1:
        return after_pos

    return len(lines)


def merge_from_snapshot(existing_lines, base_lines, new_lines):
    matcher = SequenceMatcher(None, base_lines, new_lines)
    merged = list(existing_lines)
    cursor = 0
    result = WriteResult()

    for tag, base_start, base_end, new_start, new_end in matcher.get_opcodes():
        old_block = base_lines[base_start:base_end]
        new_block = new_lines[new_start:new_end]

        if tag == "equal":
            equal_pos = find_sequence(merged, old_block, cursor)

            if equal_pos != -1:
                cursor = equal_pos + len(old_block)

            continue

        if tag == "insert":
            insert_pos = find_nearby_insert_position(
                merged, base_lines, base_start, cursor
            )
            merged[insert_pos:insert_pos] = new_block
            cursor = insert_pos + len(new_block)
            result.added += count_content_lines(new_block)
            continue

        replace_pos = find_sequence(merged, old_block, cursor)

        if replace_pos == -1:
            result.conflicts += 1
            continue

        if tag == "delete":
            del merged[replace_pos:replace_pos + len(old_block)]
            cursor = replace_pos
            result.deleted += count_content_lines(old_block)
            continue

        if tag == "replace":
            merged[replace_pos:replace_pos + len(old_block)] = new_block
            cursor = replace_pos + len(new_block)
            result.replaced += max(
                count_content_lines(old_block),
                count_content_lines(new_block),
            )

    return merged, result


def merge_with_existing(existing_lines, new_lines):
    existing_set = {
        normalize_line(line) for line in existing_lines if normalize_line(line)
    }

    lines_to_add = []

    for line in new_lines:
        normalized = normalize_line(line)

        if not normalized:
            continue

        if normalized not in existing_set:
            lines_to_add.append(line)
            existing_set.add(normalized)

    if not lines_to_add:
        return existing_lines, 0

    merged = list(existing_lines)

    if merged and normalize_line(merged[-1]):
        merged.append("")

    merged.extend(lines_to_add)

    return merged, len(lines_to_add)


def write_rpy_file(rpy_path, new_lines):
    if os.path.exists(rpy_path):
        existing_lines = read_text_lines(rpy_path)
        cache_path = get_cache_path(rpy_path)

        if os.path.exists(cache_path):
            base_lines = read_text_lines(cache_path)
            merged_lines, result = merge_from_snapshot(
                existing_lines, base_lines, new_lines
            )

            if result.conflicts:
                return WriteResult(conflicts=result.conflicts)
        else:
            merged_lines, added_count = merge_with_existing(
                existing_lines, new_lines
            )
            result = WriteResult(added=added_count, bootstrapped=True)

        write_text_lines(rpy_path, merged_lines)
        save_generation_snapshot(rpy_path, new_lines)

        return result

    write_text_lines(rpy_path, new_lines)
    save_generation_snapshot(rpy_path, new_lines)

    return WriteResult(added=count_content_lines(new_lines), created=True)


def match_character(name, characters):
    """
    Compara 'name' contra los personajes configurados sin importar
    mayusculas/minusculas ni espacios sobrantes.

    Devuelve (matched, variable):
      - (True, None)   -> es 'Narrador'
      - (True, "l")    -> es un personaje con esa variable
      - (False, None)  -> no coincide con nada
    """
    lname = name.strip().lower()

    if lname == "narrador":
        return True, None

    for cname, var in characters.items():
        if cname.strip().lower() == lname:
            return True, var

    return False, None


# Diálogo corto en una sola línea: "Lara: Hola" -> l "Hola"
INLINE_DIALOGUE_PATTERN = re.compile(r"^([^\[\]:]+):\s*(.*)$")

# Label en una sola línea: "[label nombre_label]" (alternativa a
# "[label]" + nombre en la línea siguiente, que se sigue aceptando).
LABEL_ONE_LINE_PATTERN = re.compile(r"^\[label\s+(.+?)\]$", re.IGNORECASE)


def is_special_line(line):
    """
    True si la linea es un comando (label/jump/call/menu/opcion/enlace)
    o un comentario, en vez de texto de dialogo comun. Se usa para saber
    donde termina un parrafo al fusionar lineas seguidas.
    """
    lower = line.lower()

    if line.startswith("["):
        return True

    if line.startswith("%%"):
        return True

    if lower == "menu:":
        return True

    return False


def collect_paragraph(lines, start_index, first_text, characters):
    """
    Junta 'first_text' con las lineas de continuacion que siguen
    (mismo parrafo, mismo hablante): sigue agregando lineas mientras
    no aparezca una linea en blanco, un comando especial (label, jump,
    call, menu, comentario, enlace) o una nueva etiqueta de personaje
    tipo 'Nombre: texto'.

    Las lineas se unen con un '\\n' escapado (texto literal, dos
    caracteres) para que Ren'Py genere UNA sola linea de dialogo con
    un salto de linea dentro del cuadro de texto, en vez de varias
    lineas de dialogo separadas.

    Devuelve (texto_unido, siguiente_indice_sin_consumir).
    """
    block = [first_text]
    j = start_index

    while j < len(lines):
        next_line = lines[j].strip()

        if not next_line:
            break

        if is_special_line(next_line):
            break

        inline = INLINE_DIALOGUE_PATTERN.match(next_line)

        if inline:
            candidate = inline.group(1).strip()
            matched, _ = match_character(candidate, characters)

            if matched:
                break

        block.append(next_line)
        j += 1

    return "\\n".join(block), j


def convert_file(md_path, rpy_path, characters, log_fn=None):
    """
    characters: dict {NombrePersonaje: variable}, provisto por la config
    del usuario (ya no esta hardcodeado).
    """
    output = []
    current_speaker_var = None  # None = Narrador

    in_menu = False
    current_option = None
    option_has_content = False
    label_stack = []
    base_indent = 1

    lines = read_source_lines(md_path)

    i = 0

    while i < len(lines):

        raw_line = lines[i]
        line = raw_line.strip()
        source_indent = source_indent_level(raw_line)

        if not line:
            i += 1
            continue

        base_indent = update_label_stack(label_stack, source_indent)

        # LABEL (forma corta en una linea: "[label nombre]")
        label_one_line = LABEL_ONE_LINE_PATTERN.match(line)

        if label_one_line:
            label_name = label_one_line.group(1).strip()
            label_indent = source_indent

            while label_stack and label_indent <= label_stack[-1]:
                label_stack.pop()

            label_stack.append(label_indent)
            base_indent = label_indent + 1

            output.append("")
            output.append(f"{tabs(label_indent)}label {label_name}:")
            output.append("")

            i += 1
            continue

        # LABEL (forma clasica en dos lineas: "[label]" + nombre debajo)
        if line.lower() == "[label]":
            label_name = lines[i + 1].strip()
            label_indent = max(source_indent, source_indent_level(lines[i + 1]))

            while label_stack and label_indent <= label_stack[-1]:
                label_stack.pop()

            label_stack.append(label_indent)
            base_indent = label_indent + 1

            output.append("")
            output.append(f"{tabs(label_indent)}label {label_name}:")
            output.append("")

            i += 2
            continue

        # JUMP
        jump_match = re.match(r"\[jump\s+(.+?)\]", line, re.IGNORECASE)
        if jump_match:
            jump_target = jump_match.group(1)
            indent = current_indent(base_indent, in_menu, current_option)
            output.append(f"{tabs(indent)}jump {jump_target}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # CALL
        call_match = re.match(r"\[call\s+(.+?)\]", line, re.IGNORECASE)
        if call_match:
            call_target = call_match.group(1)
            indent = current_indent(base_indent, in_menu, current_option)
            output.append(f"{tabs(indent)}call {call_target}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # BLOQUE COMENTARIOS
        if line == "%%":
            i += 1
            indent = current_indent(base_indent, in_menu, current_option)

            while i < len(lines):
                comment_line = lines[i].strip()

                if comment_line == "%%":
                    break

                output.append(f"{tabs(indent)}# {comment_line}")
                i += 1

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # COMENTARIO SIMPLE
        if line.startswith("%%") and line.endswith("%%"):
            comment = line[2:-2].strip()
            indent = current_indent(base_indent, in_menu, current_option)
            output.append(f"{tabs(indent)}# {comment}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # IGNORAR ENLACES OBSIDIAN
        if line.startswith("[[") and line.endswith("]]"):
            i += 1
            continue

        # DIALOGO EN UNA LINEA: "Nombre: texto"
        # (alternativa corta a poner "[Nombre]" y el texto en la linea de abajo)
        if not line.startswith("["):
            inline_match = INLINE_DIALOGUE_PATTERN.match(line)

            if inline_match:
                speaker_candidate = inline_match.group(1).strip()
                text = inline_match.group(2).strip()
                matched, var = match_character(speaker_candidate, characters)

                if matched and text:
                    current_speaker_var = var
                    merged_text, next_i = collect_paragraph(
                        lines, i + 1, text, characters
                    )
                    indent = current_indent(base_indent, in_menu, current_option)

                    if var is None:
                        output.append(f'{tabs(indent)}"{merged_text}"')
                    else:
                        output.append(f'{tabs(indent)}{var} "{merged_text}"')

                    if in_menu and current_option:
                        option_has_content = True

                    i = next_i
                    continue

        # MENU (se acepta tanto "menu:" como "[menu]")
        if line.lower() == "menu:" or line.lower() == "[menu]":
            output.append(f"{tabs(base_indent)}menu:")
            output.append("")

            in_menu = True
            current_option = None
            option_has_content = False

            i += 1
            continue

        # END MENU
        if line.lower() == "[end menu]":
            if in_menu and current_option:
                finalize_menu_option(output, base_indent, option_has_content)

            in_menu = False
            current_option = None
            option_has_content = False

            i += 1
            continue

        # OPCIONES MENU
        if in_menu:
            option_match = re.match(r"\[(.+?)\]", line)

            if option_match:
                option_name = option_match.group(1)

                is_character, _ = match_character(option_name, characters)

                if not is_character and not is_menu_command(option_name):
                    if current_option:
                        finalize_menu_option(output, base_indent, option_has_content)

                    current_option = option_name
                    option_has_content = False

                    output.append("")
                    output.append(f'{tabs(base_indent + 1)}"{option_name}":')

                    i += 1
                    continue

        # CAMBIO PERSONAJE (forma clasica: "[Nombre]" solo en la linea)
        speaker_match = re.match(r"\[(.+?)\]", line)

        if speaker_match:
            speaker = speaker_match.group(1)
            matched, var = match_character(speaker, characters)

            if matched:
                current_speaker_var = var
                i += 1
                continue

            if log_fn:
                log_fn(
                    f"   ! Aviso: '[{speaker}]' no coincide con ningun personaje "
                    f"configurado ni es 'Narrador'; se tratara como dialogo del "
                    f"hablante actual."
                )

        # DIALOGOS (con fusion de lineas seguidas del mismo parrafo)
        merged_text, next_i = collect_paragraph(lines, i + 1, line, characters)
        indent = current_indent(base_indent, in_menu, current_option)

        if current_speaker_var is None:
            output.append(f'{tabs(indent)}"{merged_text}"')
        else:
            output.append(f'{tabs(indent)}{current_speaker_var} "{merged_text}"')

        if in_menu and current_option:
            option_has_content = True

        i = next_i

    return write_rpy_file(rpy_path, output)


# =============================================================
# INTERFAZ GRAFICA
# =============================================================

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CharacterRow(ctk.CTkFrame):
    """Una fila editable: nombre + variable + boton eliminar."""

    def __init__(self, master, name, variable, on_delete, on_changed):
        super().__init__(master, fg_color="transparent")

        self.on_delete = on_delete
        self.on_changed = on_changed
        self.original_name = name

        self.name_entry = ctk.CTkEntry(self, placeholder_text="Nombre (ej: Lara)")
        self.name_entry.insert(0, name)
        self.name_entry.grid(row=0, column=0, padx=(0, 6), pady=4, sticky="ew")

        self.var_entry = ctk.CTkEntry(self, placeholder_text="variable (ej: l)", width=90)
        self.var_entry.insert(0, variable)
        self.var_entry.grid(row=0, column=1, padx=6, pady=4)

        self.delete_btn = ctk.CTkButton(
            self, text="Eliminar", width=80, fg_color="#8a2f2f",
            hover_color="#6e2424", command=self._delete
        )
        self.delete_btn.grid(row=0, column=2, padx=(6, 0), pady=4)

        self.grid_columnconfigure(0, weight=1)

        self.name_entry.bind("<KeyRelease>", lambda e: self.on_changed())
        self.var_entry.bind("<KeyRelease>", lambda e: self.on_changed())

    def _delete(self):
        self.on_delete(self)

    def get_values(self):
        return self.name_entry.get(), self.var_entry.get()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Obsidian -> Ren'Py")
        self.geometry("760x600")
        self.minsize(680, 520)

        self.config_data = load_config()
        self.md_files = []
        self.output_dir = self.config_data.get("last_output_dir", app_dir())

        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=14, pady=14)

        self.tab_convert = self.tabview.add("Conversion")
        self.tab_characters = self.tabview.add("Personajes")

        self._build_convert_tab()
        self._build_characters_tab()

    # ---------------------------------------------------------
    # PESTAÑA: CONVERSION
    # ---------------------------------------------------------

    def _build_convert_tab(self):
        tab = self.tab_convert

        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))

        self.md_btn = ctk.CTkButton(
            top, text="1. Seleccionar archivos (.md / .txt)",
            command=self.pick_md_files
        )
        self.md_btn.pack(side="left")

        self.md_label = ctk.CTkLabel(top, text="Ningun archivo seleccionado", anchor="w")
        self.md_label.pack(side="left", padx=10, fill="x", expand=True)

        mid = ctk.CTkFrame(tab, fg_color="transparent")
        mid.pack(fill="x", padx=10, pady=4)

        self.out_btn = ctk.CTkButton(
            mid, text="2. Seleccionar carpeta destino",
            command=self.pick_output_dir
        )
        self.out_btn.pack(side="left")

        self.out_label = ctk.CTkLabel(mid, text=self.output_dir, anchor="w")
        self.out_label.pack(side="left", padx=10, fill="x", expand=True)

        self.convert_btn = ctk.CTkButton(
            tab, text="3. Convertir", height=42, fg_color="#2f7a3d",
            hover_color="#255f30", command=self.run_conversion
        )
        self.convert_btn.pack(fill="x", padx=10, pady=(10, 6))

        self.log_box = ctk.CTkTextbox(tab, wrap="word")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        self.log_box.configure(state="disabled")

    def log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def pick_md_files(self):
        initial = self.config_data.get("last_md_dir", app_dir())

        files = filedialog.askopenfilenames(
            title="Selecciona los archivos de texto",
            initialdir=initial if os.path.isdir(initial) else app_dir(),
            filetypes=[
                ("Markdown y texto", "*.md *.txt"),
                ("Markdown", "*.md"),
                ("Texto plano", "*.txt"),
                ("Todos los archivos", "*.*"),
            ],
        )

        if files:
            self.md_files = list(files)
            self.md_label.configure(text=f"{len(files)} archivo(s) seleccionado(s)")
            self.config_data["last_md_dir"] = os.path.dirname(files[0])
            save_config(self.config_data)

    def pick_output_dir(self):
        initial = self.config_data.get("last_output_dir", app_dir())
        os.makedirs(initial, exist_ok=True)

        folder = filedialog.askdirectory(
            title="Selecciona la carpeta destino",
            initialdir=initial,
        )

        if folder:
            self.output_dir = folder
            self.out_label.configure(text=folder)
            self.config_data["last_output_dir"] = folder
            save_config(self.config_data)

    def run_conversion(self):
        if not self.md_files:
            messagebox.showwarning("Falta info", "Selecciona primero los archivos .md.")
            return

        if not self.output_dir:
            messagebox.showwarning("Falta info", "Selecciona la carpeta destino.")
            return

        self.convert_btn.configure(state="disabled", text="Convirtiendo...")
        thread = threading.Thread(target=self._convert_worker, daemon=True)
        thread.start()

    def _convert_worker(self):
        characters = self.config_data.get("characters", {})
        os.makedirs(self.output_dir, exist_ok=True)

        converted = 0
        changed_total = 0

        for md_path in self.md_files:
            filename = os.path.basename(md_path)
            rpy_name = os.path.splitext(filename)[0] + ".rpy"
            rpy_path = os.path.join(self.output_dir, rpy_name)
            existed_before = os.path.exists(rpy_path)

            result = convert_file(md_path, rpy_path, characters, log_fn=self.log)

            if existed_before:
                details = []

                if result.added:
                    details.append(f"{result.added} lineas nuevas")
                if result.replaced:
                    details.append(f"{result.replaced} lineas reemplazadas")
                if result.deleted:
                    details.append(f"{result.deleted} lineas eliminadas")
                if result.conflicts:
                    details.append(f"{result.conflicts} bloque(s) conservados por conflicto")
                if result.bootstrapped:
                    details.append("base incremental creada")

                if details:
                    self.log(f"+ {filename} ({', '.join(details)})")
                else:
                    self.log(f"= {filename} (sin cambios)")
            else:
                self.log(f"OK {filename}")

            converted += 1
            changed_total += result.changed

        self.log(f"\nConversion terminada. ({converted} archivos, {changed_total} cambios)")
        self.after(0, lambda: self.convert_btn.configure(state="normal", text="3. Convertir"))

    # ---------------------------------------------------------
    # PESTAÑA: PERSONAJES
    # ---------------------------------------------------------

    def _build_characters_tab(self):
        tab = self.tab_characters

        info = ctk.CTkLabel(
            tab,
            text=(
                "Cada personaje necesita un nombre (el que usas en el .md, ej: Lara) "
                "y una variable corta para Ren'Py (ej: l). 'Narrador' ya esta incluido "
                "por defecto y no se edita aqui."
            ),
            wraplength=680, justify="left", anchor="w"
        )
        info.pack(fill="x", padx=10, pady=(10, 6))

        self.rows_frame = ctk.CTkScrollableFrame(tab, label_text="Personajes")
        self.rows_frame.pack(fill="both", expand=True, padx=10, pady=6)

        self.character_rows = []

        for name, variable in self.config_data.get("characters", {}).items():
            self._add_row(name, variable)

        btns = ctk.CTkFrame(tab, fg_color="transparent")
        btns.pack(fill="x", padx=10, pady=(0, 6))

        add_btn = ctk.CTkButton(btns, text="+ Agregar personaje", command=lambda: self._add_row("", ""))
        add_btn.pack(side="left")

        save_btn = ctk.CTkButton(
            btns, text="Guardar cambios", fg_color="#2f7a3d", hover_color="#255f30",
            command=self.save_characters
        )
        save_btn.pack(side="right")

        self.char_status = ctk.CTkLabel(tab, text="", text_color="#e08a3c", anchor="w")
        self.char_status.pack(fill="x", padx=10, pady=(0, 10))

    def _add_row(self, name, variable):
        row = CharacterRow(
            self.rows_frame, name, variable,
            on_delete=self._delete_row,
            on_changed=lambda: self.char_status.configure(text="")
        )
        row.pack(fill="x", pady=2)
        self.character_rows.append(row)

    def _delete_row(self, row):
        row.destroy()
        self.character_rows.remove(row)

    def save_characters(self):
        new_characters = {}

        for row in self.character_rows:
            name, variable = row.get_values()
            name = name.strip()
            variable = variable.strip().lower()

            if not name and not variable:
                continue  # fila vacia, se ignora

            ok, error = validate_character(name, variable, new_characters)

            if not ok:
                self.char_status.configure(text=f"Error: {error}")
                return

            new_characters[name] = variable

        self.config_data["characters"] = new_characters
        save_config(self.config_data)
        self.char_status.configure(text=f"Guardado: {len(new_characters)} personaje(s).", text_color="#4caf6d")


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
