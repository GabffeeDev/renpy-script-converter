import os
import re
from tkinter import Tk, filedialog

CHARACTERS = {
    "Yuri": "y",
    "Player": "mc"
}

def select_md_files():

    root = Tk()
    root.withdraw()

    files = filedialog.askopenfilenames(
        title="Selecciona los archivos Markdown",
        filetypes=[("Markdown", "*.md")]
    )

    root.destroy()

    return files

def select_output_folder():

    root = Tk()
    root.withdraw()

    folder = filedialog.askdirectory(
        title="Selecciona la carpeta destino"
    )

    root.destroy()

    return folder

def current_indent(in_menu, current_option):

    if in_menu and current_option:
        return 3

    return 1


def tabs(level):
    return "    " * level


def finalize_menu_option(output, option_has_content):
    if not option_has_content:
        output.append(f"{tabs(3)}pass")


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
        with open(rpy_path, "r", encoding="utf-8") as f:
            existing_lines = [line.rstrip("\n\r") for line in f.readlines()]

        merged_lines, added_count = merge_with_existing(existing_lines, new_lines)
        content = "\n".join(merged_lines)

        with open(rpy_path, "w", encoding="utf-8") as f:
            f.write(content)

        return added_count

    with open(rpy_path, "w", encoding="utf-8") as f:
        f.write("\n".join(new_lines))

    return len([line for line in new_lines if normalize_line(line)])


def convert_file(md_path, rpy_path):

    output = []
    current_speaker = "Narrador"

    in_menu = False
    current_option = None
    option_has_content = False

    with open(md_path, "r", encoding="utf-8") as f:
        lines = [line.rstrip() for line in f]

    i = 0

    while i < len(lines):

        line = lines[i].strip()

        if not line:
            i += 1
            continue

        # ==========================
        # LABEL
        # ==========================

        if line.lower() == "[label]":

            label_name = lines[i + 1].strip()

            output.append("")
            output.append(f"label {label_name}:")
            output.append("")

            i += 2
            continue

        # ==========================
        # JUMP
        # ==========================

        jump_match = re.match(r"\[jump\s+(.+?)\]", line, re.IGNORECASE)

        if jump_match:

            jump_target = jump_match.group(1)
            indent = current_indent(in_menu, current_option)

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
            indent = current_indent(in_menu, current_option)

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
            indent = current_indent(in_menu, current_option)

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

            indent = current_indent(in_menu, current_option)

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

            output.append(f"{tabs(1)}menu:")
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
                finalize_menu_option(output, option_has_content)

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
                        finalize_menu_option(output, option_has_content)

                    current_option = option_name
                    option_has_content = False

                    output.append("")
                    output.append(f'{tabs(2)}"{option_name}":')

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

        indent = current_indent(in_menu, current_option)

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
    added_total = 0

    for md_path in md_files:

        filename = os.path.basename(md_path)

        rpy_name = os.path.splitext(filename)[0] + ".rpy"

        rpy_path = os.path.join(dest_dir, rpy_name)
        existed_before = os.path.exists(rpy_path)

        added_lines = convert_file(md_path, rpy_path)

        if existed_before:
            if added_lines:
                print(f"+ {filename} ({added_lines} lineas nuevas)")
            else:
                print(f"= {filename} (sin cambios)")
        else:
            print(f"OK {filename}")

        converted += 1
        added_total += added_lines

    print(f"\nConversion terminada. ({converted} archivos, {added_total} lineas nuevas)")

if __name__ == "__main__":
    main()
