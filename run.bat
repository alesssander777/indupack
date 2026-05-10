@echo off
setlocal
cd /d "%~dp0"

echo [INDUPACK] Instalando dependencias (se faltarem)...
py -3 -m pip install -r requirements.txt 2>nul
if errorlevel 1 python -m pip install -r requirements.txt

echo [INDUPACK] Iniciando servidor em http://127.0.0.1:8000
echo Abra o navegador em: http://127.0.0.1:8000/login
echo.
py -3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 2>nul
if errorlevel 1 python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

pause
