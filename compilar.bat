@echo off
chcp 65001 >nul
title Compilador - Mensajes Biblicos AutomaPro
cd /d "%~dp0"

echo.
echo ============================================================
echo     COMPILADOR - MENSAJES BIBLICOS AUTOMAPRO
echo ============================================================
echo.
echo Este script compila todos los ejecutables del proyecto.
echo Asegurate de tener PyInstaller instalado.
echo.
pause

set PYINSTALLER=py -m PyInstaller
set DATOS_BASE=--add-data "compartido;compartido" --add-data "iconos;iconos" --add-data "config_global.txt;." --add-data "version.txt;."
set FLAGS=--onefile --windowed --noconfirm
set FLAGS_CONSOLA=--onefile --noconfirm

echo.
echo [1/8] Compilando MensajesBiblicos.exe...
%PYINSTALLER% %FLAGS_CONSOLA% %DATOS_BASE% --add-data "publicadores;publicadores" --add-data "extractores;extractores" --add-data "mensajes;mensajes" --add-data "llamados-oracion;llamados-oracion" --icon=iconos/bible.ico --name MensajesBiblicos publicar_facebook.py
echo.

echo [2/8] Compilando PanelControl.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --icon=iconos/dashboard.ico --name PanelControl panel_control.py
echo.

echo [3/8] Compilando WizardMensajes.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --add-data "mensajes;mensajes" --icon=iconos/wizard.ico --name WizardMensajes wizard_primera_vez.py
echo.

echo [4/8] Compilando ConfiguradorMensajes.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --add-data "llamados-oracion;llamados-oracion" --icon=iconos/settings.ico --name ConfiguradorMensajes configurador_gui.py
echo.

echo [5/8] Compilando GestorMensajes.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --add-data "mensajes;mensajes" --icon=iconos/edit.ico --name GestorMensajes gestor_mensajes_gui.py
echo.

echo [6/8] Compilando GestorTareasMensajes.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --icon=iconos/calendar.ico --name GestorTareasMensajes gestor_tareas_gui.py
echo.

echo [7/8] Compilando OracionesWhatsApp.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --add-data "publicadores;publicadores" --add-data "llamados-oracion;llamados-oracion" --icon=iconos/pray.ico --name OracionesWhatsApp publicadores/whatsapp_oracion.py
echo.

echo [8/8] Compilando ExtractorPredicaciones.exe...
%PYINSTALLER% %FLAGS% %DATOS_BASE% --add-data "extractores;extractores" --add-data "cola-facebook;cola-facebook" --icon=iconos/clapper.ico --name ExtractorPredicaciones extractores/extractor_whatsapp_predicaciones.py
echo.

echo ============================================================
echo  COMPILACION COMPLETADA
echo  Los .exe estan en la carpeta: dist\
echo ============================================================
echo.
pause