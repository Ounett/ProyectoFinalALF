@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
    echo ERROR: Instala Python 3.9 o posterior desde https://www.python.org/downloads/windows/
    exit /b 2
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 9) else 1)"
if errorlevel 1 (
    echo ERROR: Se requiere Python 3.9 o posterior.
    exit /b 2
)

py -3 -m erafd.web.server %*
endlocal
