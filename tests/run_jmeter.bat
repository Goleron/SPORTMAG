@echo off
REM Скрипт для запуска нагрузочного тестирования через JMeter (Windows)

set JMETER_HOME=%JMETER_HOME%
if "%JMETER_HOME%"=="" set JMETER_HOME=C:\Program Files\Apache JMeter

set BASE_URL=%BASE_URL%
if "%BASE_URL%"=="" set BASE_URL=http://localhost:8000

set THREADS=%THREADS%
if "%THREADS%"=="" set THREADS=50

set RAMP_UP=%RAMP_UP%
if "%RAMP_UP%"=="" set RAMP_UP=60

set LOOPS=%LOOPS%
if "%LOOPS%"=="" set LOOPS=10

echo Запуск нагрузочного тестирования...
echo URL: %BASE_URL%
echo Потоков: %THREADS%
echo Время нарастания: %RAMP_UP%с
echo Итераций: %LOOPS%

"%JMETER_HOME%\bin\jmeter.bat" ^
    -n ^
    -t tests\jmeter_test_plan.jmx ^
    -l tests\jmeter_results.jtl ^
    -e ^
    -o tests\jmeter_report ^
    -JBASE_URL=%BASE_URL% ^
    -JTHREADS=%THREADS% ^
    -JRAMP_UP=%RAMP_UP% ^
    -JLOOPS=%LOOPS%

echo Тестирование завершено. Результаты в tests\jmeter_report\

