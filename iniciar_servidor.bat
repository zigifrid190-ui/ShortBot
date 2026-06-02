@echo off
title ShortBot Webhook Gateway
cd /d "%~dp0"
echo Iniciando o Servidor Webhook do ShortBot...

:: Verifica e ativa o ambiente virtual do Python
if exist .venv\Scripts\activate.bat (
    echo Ativando ambiente virtual (.venv)...
    call .venv\Scripts\activate.bat
) else if exist venv\Scripts\activate.bat (
    echo Ativando ambiente virtual (venv)...
    call venv\Scripts\activate.bat
)

python youtube-shorts-automation\webhook_server.py
pause
