@echo off
chcp 65001 > nul
echo ============================================ > "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo TESTE MANUAL - 2025-12-19 08:46:34.709899 >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo ============================================ >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo. >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo Executando comando: >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo "C:\Users\CAIO MAXIMUS\AppData\Local\Programs\Python\Python312\python.exe" "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\app.py" --auto "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\scheduled_tasks\test_manual.json" >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo. >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
"C:\Users\CAIO MAXIMUS\AppData\Local\Programs\Python\Python312\python.exe" "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\app.py" --auto "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\scheduled_tasks\test_manual.json" >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log" 2>&1
echo. >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo Codigo de saida: %ERRORLEVEL% >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
echo ============================================ >> "c:\Users\CAIO MAXIMUS\Documents\GitHub\meu-teste\logs\test_manual.log"
pause
