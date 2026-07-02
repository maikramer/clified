@echo off
REM Clified — Instalador Universal (Windows CMD)
REM One-liner recomendado: irm https://raw.githubusercontent.com/maikramer/clified/main/install.ps1 | iex
REM Uso local (dev): install.bat [tool] [opcoes]

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
exit /b %errorlevel%
