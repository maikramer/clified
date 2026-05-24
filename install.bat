@echo off
REM Clified — Instalador Universal (Windows CMD)
REM Uso: install.bat <tool> [opcoes]

setlocal EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "CLIFIED_ROOT=%SCRIPT_DIR%"

echo Clified — Instalador Universal
echo =================================

if not exist "%SCRIPT_DIR%tools.yaml" (
    echo tools.yaml nao encontrado. Copie tools.yaml.example para tools.yaml.
    exit /b 1
)

python --version >nul 2>&1
if errorlevel 1 (
    set PY=python3
) else (
    set PY=python
)

set "INSTALLER_VENV=%SCRIPT_DIR%.installer-venv"
set "INSTALLER_PY=%INSTALLER_VENV%\Scripts\python.exe"

if not exist "%INSTALLER_PY%" (
    %PY% -m venv "%INSTALLER_VENV%"
    "%INSTALLER_PY%" -m pip install -q --upgrade pip
    "%INSTALLER_PY%" -m pip install -q -e "%SCRIPT_DIR%"
)

"%INSTALLER_PY%" -m clified --python %PY% %*
