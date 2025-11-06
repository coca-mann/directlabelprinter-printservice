@echo off
set SERVICE_PATH=C:\print_service
echo "Iniciando Servico de Impressao..."
cd /d %SERVICE_PATH%
call .\venv\Scripts\activate.bat
python print_service.py