@echo off
REM Скрипт для автоматического резервного копирования (Windows)
REM Использование в Task Scheduler

REM Получаем директорию скрипта
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%\..

REM Активируем виртуальное окружение
if exist "%PROJECT_DIR%\venv\Scripts\activate.bat" (
    call "%PROJECT_DIR%\venv\Scripts\activate.bat"
)

REM Переходим в директорию проекта
cd /d "%PROJECT_DIR%"

REM Запускаем скрипт резервного копирования
python scripts\backup.py --description "Автоматическое резервное копирование"

REM Логируем результат
if %ERRORLEVEL% EQU 0 (
    echo %date% %time%: Резервное копирование выполнено успешно >> "%PROJECT_DIR%\logs\backup.log"
) else (
    echo %date% %time%: Ошибка при резервном копировании >> "%PROJECT_DIR%\logs\backup.log"
)

