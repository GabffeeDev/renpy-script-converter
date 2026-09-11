@echo off
setlocal

echo ===============================================
echo   Generador de ConversorRenpy.exe
echo ===============================================
echo.

rem Este .bat debe estar en la MISMA carpeta que md_to_rpy_gui.py
if not exist "md_to_rpy_gui.py" (
    echo No encuentro "md_to_rpy_gui.py" en esta carpeta.
    echo Copia este .bat junto al script y volve a ejecutarlo.
    pause
    exit /b 1
)

rem Verifica que Python este instalado y en el PATH
where python >nul 2>nul
if errorlevel 1 (
    echo No se encontro Python en el PATH.
    echo Instalalo desde https://www.python.org/downloads/
    echo ^(marca la casilla "Add python.exe to PATH" durante la instalacion^)
    echo y volve a ejecutar este archivo.
    pause
    exit /b 1
)

echo Instalando/actualizando dependencias necesarias...
echo ^(customtkinter y pyinstaller^)
echo.
python -m pip install --upgrade pip >nul
python -m pip install --upgrade customtkinter pyinstaller

if errorlevel 1 (
    echo.
    echo Hubo un error instalando las dependencias. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo Limpiando compilaciones anteriores...
if exist "build" rmdir /s /q "build"
if exist "dist" rmdir /s /q "dist"
if exist "ConversorRenpy.spec" del /q "ConversorRenpy.spec"

echo.
echo Generando el ejecutable, esto puede tardar un minuto...
echo.
python -m PyInstaller --onefile --noconsole --name "ConversorRenpy" "md_to_rpy_gui.py"

if errorlevel 1 (
    echo.
    echo Hubo un error generando el .exe. Revisa el mensaje de arriba.
    pause
    exit /b 1
)

echo.
echo ===============================================
echo   Listo! El ejecutable quedo en:
echo   %cd%\dist\ConversorRenpy.exe
echo ===============================================
echo.
echo Podes copiar ese .exe a donde quieras y usarlo directo,
echo sin necesidad de tener Python instalado en esa PC.
echo.
pause
