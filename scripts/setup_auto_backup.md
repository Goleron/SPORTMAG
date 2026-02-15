# Настройка автоматического резервного копирования

## Linux/Mac (cron)

### 1. Сделайте скрипт исполняемым:
```bash
chmod +x scripts/backup_cron.sh
```

### 2. Добавьте задачу в crontab:
```bash
crontab -e
```

### 3. Добавьте строку для ежедневного бэкапа в 2:00 ночи:
```
0 2 * * * /полный/путь/к/проекту/scripts/backup_cron.sh
```

### Примеры расписания:
- Каждый день в 2:00: `0 2 * * *`
- Каждый час: `0 * * * *`
- Каждые 6 часов: `0 */6 * * *`
- Каждое воскресенье в 3:00: `0 3 * * 0`

## Windows (Task Scheduler)

### 1. Откройте Task Scheduler (Планировщик заданий)

### 2. Создайте новую задачу:
- Нажмите "Create Basic Task" (Создать простую задачу)
- Название: "Sport Shop Backup"
- Описание: "Автоматическое резервное копирование базы данных"

### 3. Настройте триггер:
- Выберите "Daily" (Ежедневно)
- Установите время (например, 2:00)

### 4. Настройте действие:
- Выберите "Start a program" (Запустить программу)
- Программа: `C:\Python311\python.exe` (или путь к вашему Python)
- Аргументы: `scripts\backup_scheduled.bat`
- Рабочая директория: `D:\4kursach` (путь к проекту)

### 5. Сохраните задачу

## Docker (опционально)

Если используете Docker, можно добавить отдельный контейнер для бэкапа:

```yaml
# В docker-compose.yml
backup:
  build: .
  container_name: sport_shop_backup
  command: >
    sh -c "while true; do
      python scripts/backup.py --description 'Автоматическое резервное копирование';
      sleep 86400;
    done"
  volumes:
    - ./backups:/app/backups
    - .:/app
  env_file:
    - .env
  depends_on:
    - db
  networks:
    - sport_shop_network
```

## Проверка работы

После настройки проверьте:
1. Создайте тестовый бэкап вручную:
```bash
python scripts/backup.py --description "Тестовый бэкап"
```

2. Проверьте логи:
```bash
# Linux/Mac
tail -f logs/backup.log

# Windows
type logs\backup.log
```

3. Проверьте директорию backups:
```bash
ls backups/  # Linux/Mac
dir backups\  # Windows
```

## Настройка хранения бэкапов

По умолчанию бэкапы сохраняются в директории `backups/`. 

Для ограничения количества хранимых бэкапов можно добавить скрипт очистки старых бэкапов:

```bash
# Удалить бэкапы старше 30 дней
find backups/ -name "shop_backup_*.sql" -mtime +30 -delete
```

