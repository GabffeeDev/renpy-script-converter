"""
Conversor Obsidian (.md) -> Ren'Py (.rpy)
Interfaz grafica con pestañas: Conversion + Personajes.

Este archivo es SOLO la capa de presentacion. Toda la logica de
conversion vive en converter.py y la persistencia en config.py.
"""

import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox

from config import app_dir, load_config, save_config
from converter import convert_file, validate_character


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
        try:
            self.after(0, self._append_log, text)
        except RuntimeError:
            self._append_log(text)

    def _append_log(self, text):
        try:
            self.log_box.configure(state="normal")
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
            self.log_box.configure(state="disabled")
        except Exception:
            pass

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
        if not initial or not isinstance(initial, str):
            initial = app_dir()
        try:
            os.makedirs(initial, exist_ok=True)
        except OSError:
            initial = app_dir()

        folder = filedialog.askdirectory(
            title="Selecciona la carpeta destino",
            initialdir=initial if os.path.isdir(initial) else app_dir(),
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
        def thread_log(text):
            try:
                self.after(0, self._append_log, text)
            except RuntimeError:
                pass

        try:
            characters = self.config_data.get("characters", {})
            if not isinstance(characters, dict):
                thread_log("! Error: 'characters' corrupto en personajes.json, se usa vacio.")
                characters = {}
            try:
                os.makedirs(self.output_dir, exist_ok=True)
            except OSError as exc:
                thread_log(f"! Error: no se pudo crear la carpeta destino: {exc}")
                return

            converted = 0
            changed_total = 0

            for md_path in self.md_files:
                filename = os.path.basename(md_path)
                rpy_name = os.path.splitext(filename)[0] + ".rpy"
                rpy_path = os.path.join(self.output_dir, rpy_name)
                existed_before = os.path.exists(rpy_path)

                try:
                    result = convert_file(md_path, rpy_path, characters, log_fn=thread_log)
                except Exception as exc:
                    thread_log(f"X {filename} (error: {exc})")
                    continue

                if result.conflicts:
                    thread_log(
                        f"! {filename} ({result.conflicts} bloque(s) en conflicto: "
                        f"archivo .rpy NO actualizado para no pisar tus cambios manuales)"
                    )
                    continue

                if existed_before:
                    details = []

                    if result.added:
                        details.append(f"{result.added} lineas nuevas")
                    if result.replaced:
                        details.append(f"{result.replaced} lineas reemplazadas")
                    if result.deleted:
                        details.append(f"{result.deleted} lineas eliminadas")
                    if result.bootstrapped:
                        details.append("base incremental creada")

                    if details:
                        thread_log(f"+ {filename} ({', '.join(details)})")
                    else:
                        thread_log(f"= {filename} (sin cambios)")
                else:
                    thread_log(f"OK {filename}")

                converted += 1
                changed_total += result.changed

            thread_log(f"\nConversion terminada. ({converted} archivos, {changed_total} cambios)")
        finally:
            try:
                self.after(0, lambda: self.convert_btn.configure(state="normal", text="3. Convertir"))
            except RuntimeError:
                pass

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
        try:
            row.destroy()
        finally:
            if row in self.character_rows:
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
