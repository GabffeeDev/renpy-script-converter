# Ren'Py Script Converter

**Ren'Py Script Converter** es una herramienta para escribir y organizar guiones de novelas visuales utilizando una sintaxis sencilla inspirada en Markdown/Obsidian y convertirlos automáticamente en scripts compatibles con Ren'Py (`.rpy`).

La herramienta está pensada para separar el proceso creativo de la programación: primero puedes escribir tu historia de forma cómoda y estructurada, y después convertirla en código de Ren'Py sin tener que escribir manualmente muchas de las estructuras básicas.

## ¿Qué puedes hacer?

- Convertir archivos `.md` y `.txt` a `.rpy`.
- Escribir diálogos de personajes y narrador con una sintaxis sencilla.
- Crear `label`, `jump` y `call`.
- Crear menús y opciones.
- Utilizar comentarios simples y multilínea.
- Trabajar con una configuración de personajes desde la propia aplicación.
- Utilizar enlaces de Obsidian (`[[enlace]]`) que se ignoran durante la conversión.
- Detectar variables de personajes inválidas o duplicadas.
- Generar un ejecutable `.exe` para Windows.

## Documentación de Ren'Py en español

Si estás aprendiendo Ren'Py, puedes consultar mi documentación en español:

**[Documentación de Ren'Py en Español](https://gabffeedev.github.io/renpy-docs-esp/)**

En ella encontrarás explicaciones y ejemplos para aprender a desarrollar novelas visuales con Ren'Py desde cero.

## Ejemplo

Puedes escribir un guion como este:

```text
[label inicio]

Narrador: La puerta se abrió lentamente.
Lara: ¿Hay alguien ahí?
Ren: Solo soy yo.

[menu]

[Seguir a Ren]

[Quedarse en la habitación]

[end menu]

[jump siguiente_escena]
```

Y obtener una estructura de Ren'Py equivalente:

```renpy
label inicio:

    "La puerta se abrió lentamente."
    l "¿Hay alguien ahí?"
    r "Solo soy yo."

    menu:
        "Seguir a Ren":
            pass

        "Quedarse en la habitación":
            pass

    jump siguiente_escena
```

Consulta [`sintaxis.txt`](sintaxis.txt) para conocer las reglas disponibles y los formatos compatibles.

## Instalación

### Windows

El repositorio incluye una versión empaquetada del programa en `ConversorRenpy.rar`.

Extrae el archivo y ejecuta `ConversorRenpy.exe`.

### Desde Python

Necesitas Python instalado en el sistema. Instala la dependencia de la interfaz gráfica:

```bash
python -m pip install customtkinter
```

Después ejecuta:

```bash
python md_to_rpy_gui.py
```

## Generar el ejecutable

El repositorio incluye `generar_exe.bat`, que automatiza la generación del ejecutable mediante PyInstaller.

El ejecutable generado aparecerá en:

```text
dist/ConversorRenpy.exe
```

## Documentación de la sintaxis

La sintaxis completa compatible con el conversor está disponible en [`sintaxis.txt`](sintaxis.txt).

También puedes consultar la documentación general de Ren'Py en español:

https://gabffeedev.github.io/renpy-docs-esp/

## Estado del proyecto

El proyecto continúa en desarrollo y la sintaxis puede ampliarse con nuevas funciones.

Para reportar errores, sugerir mejoras o solicitar nuevas características, utiliza los *Issues* del repositorio.

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta [`LICENSE`](LICENSE) para ver el texto completo.

## Autor

Desarrollado por **GabffeeDev**.

Repositorio: https://github.com/GabffeeDev/renpy-script-converter
