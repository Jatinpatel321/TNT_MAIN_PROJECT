@echo off
cd /d C:\TNT_MAIN_PROJECT-main\tnt-backend-main
if exist .venv\Scripts\activate.bat (
    call .venv\Scripts\activate.bat
)
python run.py
pause
