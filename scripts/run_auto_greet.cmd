@echo off
setlocal
chcp 65001 >nul

set "PYTHON="
for /d %%D in ("D:\Program Files (x86)\*") do (
    if exist "%%~fD\python-embed\python.exe" (
        set "PYTHON=%%~fD\python-embed\python.exe"
    )
)

if not defined PYTHON (
    echo Python environment was not found.
    exit /b 1
)

set "SCRIPT=%~dp0auto_greet.py"
set "PYTHONIOENCODING=utf-8"

"%PYTHON%" "%SCRIPT%" %*
exit /b %ERRORLEVEL%
