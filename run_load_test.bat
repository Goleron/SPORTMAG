@echo off
REM Нагрузочное тестирование Locust
REM API должен быть запущен на http://127.0.0.1:8000
REM Веб-интерфейс Locust: http://127.0.0.1:8089

cd /d "%~dp0"
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

echo.
echo ========================================
echo  Нагрузочное тестирование (Locust)
echo ========================================
echo  API:        http://127.0.0.1:8000 (должен быть запущен)
echo  Locust UI:  http://127.0.0.1:8090
echo ========================================
echo  Откройте в браузере http://127.0.0.1:8090
echo  Укажите число пользователей и RPS, нажмите Start.
echo  Если 8090 занят: locust -f tests/load_test.py --host=http://127.0.0.1:8000 --web-port=8091
echo.

locust -f tests/load_test.py --host=http://127.0.0.1:8000 --web-port=8090
pause
