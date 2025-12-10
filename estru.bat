@echo off
setlocal enabledelayedexpansion

echo ESTRUCTURA DEL PROYECTO FLASK > estructura_proyecto.txt
echo ============================= >> estructura_proyecto.txt
echo Fecha: %date% %time% >> estructura_proyecto.txt
echo. >> estructura_proyecto.txt

echo [ARCHIVOS PRINCIPALES .PY] >> estructura_proyecto.txt
echo -------------------------- >> estructura_proyecto.txt
for /r %%f in (*.py) do (
    set "file=%%f"
    set "file=!file:%cd%\=!"
    echo !file! >> estructura_proyecto.txt
)
echo. >> estructura_proyecto.txt

echo [ARCHIVOS HTML en /templates/] >> estructura_proyecto.txt
echo ------------------------------ >> estructura_proyecto.txt
if exist "templates" (
    for /r templates %%f in (*.html) do (
        set "file=%%f"
        set "file=!file:%cd%\=!"
        echo !file! >> estructura_proyecto.txt
    )
) else (
    echo No existe carpeta templates >> estructura_proyecto.txt
)
echo. >> estructura_proyecto.txt

echo [ARCHIVOS CSS en /static/] >> estructura_proyecto.txt
echo ------------------------- >> estructura_proyecto.txt
if exist "static" (
    for /r static %%f in (*.css) do (
        set "file=%%f"
        set "file=!file:%cd%\=!"
        echo !file! >> estructura_proyecto.txt
    )
) else (
    echo No existe carpeta static >> estructura_proyecto.txt
)
echo. >> estructura_proyecto.txt

echo [ARCHIVOS JS en /static/] >> estructura_proyecto.txt
echo ------------------------- >> estructura_proyecto.txt
if exist "static" (
    for /r static %%f in (*.js) do (
        set "file=%%f"
        set "file=!file:%cd%\=!"
        echo !file! >> estructura_proyecto.txt
    )
)
echo. >> estructura_proyecto.txt

echo [ARCHIVOS DE CONFIGURACION] >> estructura_proyecto.txt
echo --------------------------- >> estructura_proyecto.txt
for %%f in (requirements.txt Dockerfile .env .flaskenv config.py config.ini) do (
    if exist "%%f" echo %%f >> estructura_proyecto.txt
)

echo. >> estructura_proyecto.txt
echo Resumen: >> estructura_proyecto.txt
echo --------- >> estructura_proyecto.txt
dir /b *.py | find /c /v "" > temp_count.txt
set /p py_count=<temp_count.txt
echo Archivos .py: !py_count! >> estructura_proyecto.txt

if exist "templates" (
    dir /b templates\*.html 2>nul | find /c /v "" > temp_count.txt
    set /p html_count=<temp_count.txt
    echo Archivos HTML: !html_count! >> estructura_proyecto.txt
)

if exist "static" (
    dir /b static\*.css 2>nul | find /c /v "" > temp_count.txt
    set /p css_count=<temp_count.txt
    echo Archivos CSS: !css_count! >> estructura_proyecto.txt
    
    dir /b static\*.js 2>nul | find /c /v "" > temp_count.txt
    set /p js_count=<temp_count.txt
    echo Archivos JS: !js_count! >> estructura_proyecto.txt
)

del temp_count.txt 2>nul
echo. >> estructura_proyecto.txt
echo Proceso completado. Estructura guardada en estructura_proyecto.txt