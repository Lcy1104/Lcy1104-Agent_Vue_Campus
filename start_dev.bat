@echo off
setlocal

set "PROJECT_ROOT=%~dp0"
set "BACKEND_DIR=%PROJECT_ROOT%backend"
set "CONDA_ENV_DIR=D:\programfiles\Anaconda\envs\LangGraph"
set "PYTHON_EXE=%CONDA_ENV_DIR%\python.exe"
set "CELERY_EXE=%CONDA_ENV_DIR%\Scripts\celery.exe"
set "UVICORN_ARGS=app.main:app --port 8000"
set "COMMAND=%~1"

if "%COMMAND%"=="" set "COMMAND=start"

if "%USE_RELOAD%"=="1" set "UVICORN_ARGS=app.main:app --reload --port 8000"

if /i "%COMMAND%"=="stop" goto stop_services
if /i "%COMMAND%"=="restart" goto start_services
if /i "%COMMAND%"=="start" goto start_services

echo Usage: start_dev.bat [start^|stop^|restart]
echo.
echo   start    Stop old backend processes, then start API and workers.
echo   stop     Stop API and workers.
echo   restart  Same as start.
pause
exit /b 1

:start_services

if not exist "%BACKEND_DIR%" (
  echo Backend directory not found: %BACKEND_DIR%
  pause
  exit /b 1
)

if not exist "%PYTHON_EXE%" (
  echo Python executable not found: %PYTHON_EXE%
  pause
  exit /b 1
)

if not exist "%CELERY_EXE%" (
  echo Celery executable not found: %CELERY_EXE%
  echo Please install celery in LangGraph: pip install celery==5.4.0
  pause
  exit /b 1
)

call :stop_backend_services

start "Campus Agent API" cmd /k "cd /d "%BACKEND_DIR%" && "%PYTHON_EXE%" -m uvicorn %UVICORN_ARGS%"
start "Campus Agent PDF OCR Worker" cmd /k "cd /d "%BACKEND_DIR%" && "%CELERY_EXE%" -A app.celery_app worker --loglevel=info --pool=threads --concurrency=2 -Q knowledge_documents -n knowledge_documents@%%h"
start "Campus Agent URL Worker" cmd /k "cd /d "%BACKEND_DIR%" && "%CELERY_EXE%" -A app.celery_app worker --loglevel=info --pool=threads --concurrency=2 -Q knowledge_urls -n knowledge_urls@%%h"

echo Started Campus Agent backend services.
echo API: http://localhost:8000
echo Workers: knowledge_documents, knowledge_urls
echo Stop: start_dev.bat stop
echo.
echo Make sure Redis and PostgreSQL are already running.
echo Set USE_RELOAD=1 before running this script if you explicitly need uvicorn reload.
pause
exit /b 0

:stop_services
call :stop_backend_services
pause
exit /b 0

:stop_backend_services
echo Stopping Campus Agent backend services...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; $targets = @{}; Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'uvicorn app\.main:app' -or ($_.CommandLine -match 'celery' -and $_.CommandLine -match 'app\.celery_app') } | ForEach-Object { $targets[$_.ProcessId] = $true; $parent = $_.ProcessId; Get-CimInstance Win32_Process | Where-Object { $_.ParentProcessId -eq $parent } | ForEach-Object { $targets[$_.ProcessId] = $true } }; Get-NetTCPConnection -LocalPort 8000 -State Listen | ForEach-Object { $targets[$_.OwningProcess] = $true }; $targets.Keys | ForEach-Object { Stop-Process -Id $_ -Force }"
echo Stopped Campus Agent backend services.
exit /b 0
