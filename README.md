# Ren'Py Script Converter

Conversor de guiones escritos en Markdown (`.md`) o texto plano (`.txt`) a scripts de Ren'Py (`.rpy`), con una interfaz gráfica orientada a facilitar la escritura y organización de novelas visuales.

## Descripción

**Ren'Py Script Converter** permite escribir escenas y diálogos utilizando una sintaxis sencilla inspirada en Markdown/Obsidian y transformarlos en código compatible con Ren'Py.

El proyecto está pensado especialmente para quienes prefieren redactar primero el guion de su novela visual y convertirlo posteriormente en código, reduciendo el trabajo repetitivo de escribir estructuras básicas de Ren'Py.

La aplicación incluye una pestaña para configurar personajes y asociar sus nombres a las variables utilizadas por Ren'Py. La configuración se guarda localmente en `personajes.json`, junto al ejecutable o al script de Python.

## Características

- Conversión de archivos `.md` y `.txt` a `.rpy`.
- Interfaz gráfica basada en CustomTkinter.
- Configuración de personajes desde la propia aplicación.
- Soporte para formato corto y formato clásico de la sintaxis.
- Diálogos de personajes y narrador.
- Párrafos de varias líneas fusionados automáticamente.
- `label`, `jump` y `call`.
- Menús y opciones de menú.
- Comentarios simples y multilínea.
- Compatibilidad con enlaces de Obsidian (`[[enlace]]`), que se ignoran durante la conversión.
- Detección de variables de personaje inválidas o duplicadas.
- Compatibilidad con codificaciones comunes en archivos de texto.
- Sistema de caché para conservar una instantánea de la generación anterior y facilitar actualizaciones posteriores.
- Generación opcional de un ejecutable `.exe` para Windows mediante PyInstaller.

## Ejemplo rápido

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

Consulta [`sintaxis.txt`](sintaxis.txt) para conocer todas las reglas disponibles y los formatos compatibles.

## Sintaxis

La sintaxis utiliza dos estilos:

### Formato corto

Es el formato recomendado para escribir rápidamente.

```text
[label inicio]

Lara: Hola.
Ren: ¿Cómo estás?

[jump siguiente]
```

### Formato clásico

También se mantiene la sintaxis utilizada por versiones anteriores del proyecto.

```text
[label]
inicio

[Lara]
Hola.

[Ren]
¿Cómo estás?
```

Ambos formatos pueden utilizarse juntos en el mismo archivo.

## Personajes

Los personajes se configuran desde la pestaña **Personajes** de la aplicación.

Por ejemplo:

| Nombre | Variable Ren'Py |
|---|---|
| Lara | `l` |
| Ren | `r` |
| Doctor | `d` |

Después, una línea como:

```text
Lara: Hola, Ren.
```

se convierte en:

```renpy
l "Hola, Ren."
```

Los nombres de personajes no distinguen mayúsculas y minúsculas.

## Instalación y uso

### Ejecutable de Windows

El repositorio incluye una versión empaquetada del programa en `ConversorRenpy.rar`.

Extrae el archivo y ejecuta `ConversorRenpy.exe`.

### Ejecutar desde Python

Necesitas Python instalado en el sistema.

Instala la dependencia de la interfaz gráfica:

```bash
python -m pip install customtkinter
```

Después ejecuta:

```bash
python md_to_rpy_gui.py
```

## Generar el ejecutable

El repositorio incluye `generar_exe.bat`, que automatiza el proceso de compilación.

Ejecuta el archivo desde Windows y el script se encargará de:

1. Comprobar que Python esté disponible.
2. Instalar o actualizar `customtkinter` y `pyinstaller`.
3. Limpiar compilaciones anteriores.
4. Crear `ConversorRenpy.exe` mediante PyInstaller.

El ejecutable generado aparecerá en:

```text
dist/ConversorRenpy.exe
```

## Estructura principal

```text
renpy-script-converter/
├── md_to_rpy_gui.py       # Aplicación y lógica de conversión
├── sintaxis.txt            # Referencia de la sintaxis soportada
├── generar_exe.bat         # Script para generar el ejecutable
├── ConversorRenpy.spec     # Configuración de PyInstaller
├── ConversorRenpy.rar      # Distribución empaquetada
├── build/                  # Archivos temporales de compilación
├── dist/                   # Ejecutables generados
└── OLD/                    # Material de versiones anteriores
```

## Archivos de configuración y caché

Al utilizar la aplicación pueden generarse archivos auxiliares junto al programa o al archivo de salida.

- `personajes.json`: almacena la configuración de personajes y las últimas carpetas utilizadas.
- `.md_to_rpy_cache/`: contiene una instantánea de la generación anterior utilizada por el sistema de actualización del conversor.

Estos archivos forman parte del funcionamiento local de la aplicación y no son necesarios para definir la sintaxis del guion.

## Alcance del proyecto

El conversor está diseñado para transformar una sintaxis de guion estructurada en construcciones habituales de Ren'Py. No pretende sustituir el lenguaje de Ren'Py ni convertir de forma automática cualquier script `.rpy` arbitrario.

La sintaxis soportada está documentada en [`sintaxis.txt`](sintaxis.txt).

## Estado

El proyecto se encuentra en desarrollo. La sintaxis y las funciones del conversor pueden evolucionar con nuevas versiones.

Para reportar errores o proponer mejoras, utiliza los *Issues* del repositorio.

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta [`LICENSE`](LICENSE) para ver el texto completo.

## Autor

Desarrollado por **GabffeeDev**.

Repositorio: <https://github.com/GabffeeDev/renpy-script-converter>
