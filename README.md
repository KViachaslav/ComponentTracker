# ComponentTracker

Локальное веб-приложение для учёта радиокомпонентов: наименование, инвентарный
номер, место хранения (шкаф / шуфлядка / отсек), документация, количество, корпус.

Стек: Python + Flask + SQLite (файл базы), фронтенд — один HTML-шаблон.

## Возможности

- Добавление / редактирование / удаление компонентов
- Поиск по всем полям
- Счётчик общего количества
- Экспорт и импорт CSV (резервная копия данных, перенос на другое устройство)

## Быстрый старт (локально)

Требуется Python 3.9+ (проверено на Python 3.13 и на Raspberry Pi 4, 64-bit).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Режим разработки
python app.py
```

Приложение будет доступно по адресу http://<адрес-устройства>:5000

## База данных

По умолчанию база лежит в `data/radiocomponents.db`. Путь изменяется переменной
окружения `DB_PATH`. При первом запуске старый файл `radiocomponents.db` из корня
проекта автоматически переносится в `data/`.

## Запуск на Raspberry Pi (gunicorn + systemd)

```bash
sudo apt update && sudo apt install -y python3-venv sqlite3
cd /home/pi/component-tracker
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Установка службы
sudo cp deploy/componenttracker.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now componenttracker
sudo systemctl status componenttracker
```

Логи: `journalctl -u componenttracker -f`

> Если путь к проекту или имя пользователя отличаются от `/home/pi/component-tracker`
> и `pi`, поправьте `WorkingDirectory`, `User` и `Environment` в
> `deploy/componenttracker.service`.

### Доступ из локальной сети

- Узнать IP: `hostname -I`
- Открывать с других устройств: `http://<IP>:5000` или `http://<hostname>.local:5000`
- Рекомендуется закрепить адрес устройства (статический IP или резервация DHCP на роутере).

## Резервные копии данных

Отдельные скрипты бэкапа не используются. Для сохранения данных служит
**экспорт в CSV** (кнопка «Экспорт» в интерфейсе или `GET /api/export`).
Сохраняйте полученный файл в надёжном месте; для восстановления используйте
«Импорт» (кнопка «Импорт» или `POST /api/import`).

## Переменные окружения

| Переменная    | По умолчанию              | Назначение                                          |
|---------------|---------------------------|-----------------------------------------------------|
| `DB_PATH`     | `data/radiocomponents.db` | Путь к файлу базы данных                            |
| `HOST`        | `0.0.0.0`                 | Адрес прослушивания (только для `python app.py`)    |
| `PORT`        | `5000`                    | Порт (только для `python app.py`)                   |
| `FLASK_DEBUG` | `0`                       | `1` включает отладку (только для `python app.py`)   |

## API

| Метод  | Адрес                     | Назначение                          |
|--------|---------------------------|-------------------------------------|
| GET    | `/api/components`         | Список всех компонентов             |
| GET    | `/api/components/<id>`    | Один компонент                      |
| POST   | `/api/components`         | Добавить компонент                  |
| PUT    | `/api/components/<id>`    | Обновить компонент                  |
| DELETE | `/api/components/<id>`    | Удалить компонент                   |
| GET    | `/api/search?q=`          | Поиск по всем полям                 |
| GET    | `/api/stats`              | Статистика (всего / суммарно штук)  |
| GET    | `/api/export`             | Экспорт всех компонентов в CSV      |
| POST   | `/api/import`             | Импорт CSV (поле формы `file`)      |
