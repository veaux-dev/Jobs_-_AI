@echo off
cd /d "D:\Data\Projects\Python\Jobspy\analyzer"

echo Activating virtual environment...
call ..\.venv\Scripts\activate

echo Running analyzer...
python run_analyzer.py

echo Done.
pause
