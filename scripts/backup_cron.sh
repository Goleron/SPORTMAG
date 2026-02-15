#!/bin/bash
# Скрипт для автоматического резервного копирования (Linux/Mac)
# Использование в cron: 0 2 * * * /path/to/backup_cron.sh

# Получаем директорию скрипта
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Активируем виртуальное окружение (если есть)
if [ -d "$PROJECT_DIR/venv" ]; then
    source "$PROJECT_DIR/venv/bin/activate"
fi

# Запускаем скрипт резервного копирования
cd "$PROJECT_DIR"
python scripts/backup.py --description "Автоматическое резервное копирование"

# Логируем результат
if [ $? -eq 0 ]; then
    echo "$(date): Резервное копирование выполнено успешно" >> "$PROJECT_DIR/logs/backup.log"
else
    echo "$(date): Ошибка при резервном копировании" >> "$PROJECT_DIR/logs/backup.log"
fi

