#!/bin/bash
# Скрипт для запуска нагрузочного тестирования через JMeter

JMETER_HOME="${JMETER_HOME:-/opt/jmeter}"
BASE_URL="${BASE_URL:-http://localhost:8000}"
THREADS="${THREADS:-50}"
RAMP_UP="${RAMP_UP:-60}"
LOOPS="${LOOPS:-10}"

echo "Запуск нагрузочного тестирования..."
echo "URL: $BASE_URL"
echo "Потоков: $THREADS"
echo "Время нарастания: ${RAMP_UP}с"
echo "Итераций: $LOOPS"

"$JMETER_HOME/bin/jmeter" \
    -n \
    -t tests/jmeter_test_plan.jmx \
    -l tests/jmeter_results.jtl \
    -e \
    -o tests/jmeter_report \
    -JBASE_URL="$BASE_URL" \
    -JTHREADS="$THREADS" \
    -JRAMP_UP="$RAMP_UP" \
    -JLOOPS="$LOOPS"

echo "Тестирование завершено. Результаты в tests/jmeter_report/"

