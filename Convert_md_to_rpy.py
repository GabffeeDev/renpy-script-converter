import os
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from tkinter import Tk, filedialog

CHARACTERS = {
    "Yuri": "y",
    "Player": "mc"
}

DEFAULT_MD_DIR = r"D:\GABFFEE_STUDIO\OBSIDIAN"
DEFAULT_OUTPUT_DIR = r"E:\RENPY_GAMES"
CACHE_DIR_NAME = ".md_to_rpy_cache"


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


def select_md_files():

    root = Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="Selecciona los archivos Markdown",
        initialdir=DEFAULT_MD_DIR,
        filetypes=[("Markdown", "*.md")]
    )

    root.destroy()

    return files

def select_output_folder():

    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

    root = Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="Selecciona la carpeta destino",
        initialdir=DEFAULT_OUTPUT_DIR
    )

    root.destroy()

    return folder

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
                merged,
                base_lines,
                base_start,
                cursor
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
                count_content_lines(new_block)
            )

    return merged, result


def merge_with_existing(existing_lines, new_lines):
    existing_set = {
        normalize_line(line)
        for line in existing_lines
        if normalize_line(line)
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
                existing_lines,
                base_lines,
                new_lines
            )

            if result.conflicts:
                return WriteResult(conflicts=result.conflicts)
        else:
            merged_lines, added_count = merge_with_existing(
                existing_lines,
                new_lines
            )
            result = WriteResult(
                added=added_count,
                bootstrapped=True
            )

        write_text_lines(rpy_path, merged_lines)
        save_generation_snapshot(rpy_path, new_lines)

        return result

    write_text_lines(rpy_path, new_lines)
    save_generation_snapshot(rpy_path, new_lines)

    return WriteResult(
        added=count_content_lines(new_lines),
        created=True
    )


def convert_file(md_path, rpy_path):

    output = []
    current_speaker = "Narrador"

    in_menu = False
    current_option = None
    option_has_content = False
    label_stack = []
    base_indent = 1

    with open(md_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]

    i = 0

    while i < len(lines):

        raw_line = lines[i]
        line = raw_line.strip()
        source_indent = source_indent_level(raw_line)

        if not line:
            i += 1
            continue

        base_indent = update_label_stack(label_stack, source_indent)

        # ==========================
        # LABEL
        # ==========================

        if line.lower() == "[label]":

            label_name = lines[i + 1].strip()
            label_indent = max(
                source_indent,
                source_indent_level(lines[i + 1])
            )

            while label_stack and label_indent <= label_stack[-1]:
                label_stack.pop()

            label_stack.append(label_indent)
            base_indent = label_indent + 1

            output.append("")
            output.append(f"{tabs(label_indent)}label {label_name}:")
            output.append("")

            i += 2
            continue

        # ==========================
        # JUMP
        # ==========================

        jump_match = re.match(r"\[jump\s+(.+?)\]", line, re.IGNORECASE)

        if jump_match:

            jump_target = jump_match.group(1)
            indent = current_indent(base_indent, in_menu, current_option)

            output.append(f"{tabs(indent)}jump {jump_target}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # ==========================
        # CALL
        # ==========================

        call_match = re.match(r"\[call\s+(.+?)\]", line, re.IGNORECASE)

        if call_match:

            call_target = call_match.group(1)
            indent = current_indent(base_indent, in_menu, current_option)

            output.append(f"{tabs(indent)}call {call_target}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # ==========================
        # BLOQUE COMENTARIOS
        # ==========================

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

        # ==========================
        # COMENTARIO SIMPLE
        # ==========================

        if line.startswith("%%") and line.endswith("%%"):

            comment = line[2:-2].strip()

            indent = current_indent(base_indent, in_menu, current_option)

            output.append(f"{tabs(indent)}# {comment}")

            if in_menu and current_option:
                option_has_content = True

            i += 1
            continue

        # ==========================
        # IGNORAR ENLACES OBSIDIAN
        # ==========================

        if line.startswith("[[") and line.endswith("]]"):

            i += 1
            continue

        # ==========================
        # MENU
        # ==========================

        if line.lower() == "menu:":

            output.append(f"{tabs(base_indent)}menu:")
            output.append("")

            in_menu = True
            current_option = None
            option_has_content = False

            i += 1
            continue

        # ==========================
        # END MENU
        # ==========================

        if line.lower() == "[end menu]":

            if in_menu and current_option:
                finalize_menu_option(output, base_indent, option_has_content)

            in_menu = False
            current_option = None
            option_has_content = False

            i += 1
            continue

        # ==========================
        # OPCIONES MENU
        # ==========================

        if in_menu:

            option_match = re.match(r"\[(.+?)\]", line)

            if option_match:

                option_name = option_match.group(1)

                is_character = (
                    option_name in CHARACTERS
                    or option_name == "Narrador"
                )

                if not is_character and not is_menu_command(option_name):

                    if current_option:
                        finalize_menu_option(output, base_indent, option_has_content)

                    current_option = option_name
                    option_has_content = False

                    output.append("")
                    output.append(f'{tabs(base_indent + 1)}"{option_name}":')

                    i += 1
                    continue

        # ==========================
        # CAMBIO PERSONAJE
        # ==========================

        speaker_match = re.match(r"\[(.+?)\]", line)

        if speaker_match:

            speaker = speaker_match.group(1)

            if speaker in CHARACTERS or speaker == "Narrador":

                current_speaker = speaker

                i += 1
                continue

        # ==========================
        # DIÁLOGOS
        # ==========================

        indent = current_indent(base_indent, in_menu, current_option)

        if current_speaker == "Narrador":

            output.append(f'{tabs(indent)}"{line}"')

        elif current_speaker in CHARACTERS:

            output.append(
                f'{tabs(indent)}{CHARACTERS[current_speaker]} "{line}"'
            )

        if in_menu and current_option:
            option_has_content = True

        i += 1

    return write_rpy_file(rpy_path, output)


def select_folder(title):

    root = Tk()
    root.withdraw()

    folder = filedialog.askdirectory(title=title)

    root.destroy()

    return folder


def main():

    print("Selecciona los archivos Markdown...")

    md_files = select_md_files()

    if not md_files:

        print("No se seleccionaron archivos.")
        return

    print("Selecciona la carpeta destino...")

    dest_dir = select_output_folder()

    if not dest_dir:

        print("No se seleccionó carpeta destino.")
        return

    os.makedirs(dest_dir, exist_ok=True)

    converted = 0
    changed_total = 0

    for md_path in md_files:

        filename = os.path.basename(md_path)

        rpy_name = os.path.splitext(filename)[0] + ".rpy"

        rpy_path = os.path.join(dest_dir, rpy_name)
        existed_before = os.path.exists(rpy_path)

        result = convert_file(md_path, rpy_path)

        if existed_before:
            details = []

            if result.added:
                details.append(f"{result.added} lineas nuevas")

            if result.replaced:
                details.append(f"{result.replaced} lineas reemplazadas")

            if result.deleted:
                details.append(f"{result.deleted} lineas eliminadas")

            if result.conflicts:
                details.append(
                    f"{result.conflicts} bloque(s) conservados por conflicto"
                )

            if result.bootstrapped:
                details.append("base incremental creada")

            if details:
                print(f"+ {filename} ({', '.join(details)})")
            else:
                print(f"= {filename} (sin cambios)")
        else:
            print(f"OK {filename}")

        converted += 1
        changed_total += result.changed

    print(f"\nConversion terminada. ({converted} archivos, {changed_total} cambios)")

if __name__ == "__main__":
    main()
