# Damir — виджет «Таблица фьючерсов» для Т-Инвестиции

Веб-виджет для отслеживания фьючерсов через T-Invest API.

## Возможности

- **Таблица фьючерсов:** название актива, цена закрытия, цена открытия, изменение %
- **Фильтр по категориям:** металлы, крипта, индексы, валюты, товары, акции
- **Поиск:** мгновенный поиск по названию или тикеру
- **Автообновление:** каждые 5 секунд (можно отключить)
- **Кэширование:** список фьючерсов 5 мин, свечи 30 сек
- **Тёмная тема** в стиле торгового терминала

## Требования

- Python 3.10+
- Токен T-Invest API ([получить](https://developer.tbank.ru/invest/intro/intro/))

## Установка

```bash
git clone https://github.com/YOUR_USERNAME/damir.git
cd damir
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# или .\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

## Настройка

1. Создай `env_vars.txt` на основе `env_vars.example.txt`
2. Укажи:
   - `TINKOFF_INVEST_TOKEN=твой_токен`
   - `SANDBOX=1` (песочница) или `SANDBOX=0` (боевой контур)

Сервер автоматически читает токен из `env_vars.txt` в текущей или родительской папке.

## Запуск

```bash
python server.py
```

Открой: http://127.0.0.1:5000

## Использование

1. Нажми **«Настройки»** — выбери фьючерсы
2. Используй **категории** или **поиск** для фильтрации
3. Нажми **«Сохранить»** — таблица загрузит данные
4. **Автообновление** включено по умолчанию (каждые 5 сек)

## Структура

```
damir/
├── server.py              # Flask backend + кэширование
├── static/index.html      # Frontend (таблица, настройки)
├── requirements.txt       # flask, requests
├── env_vars.example.txt   # Пример переменных окружения
└── docs/                  # Документация
```

## API

- [T-Invest API — начало работы](https://developer.tbank.ru/invest/intro/intro/)
- [T-Invest API — документация](https://developer.tbank.ru/invest/api)

## Лицензия

MIT
