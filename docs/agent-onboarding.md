# Онбординг агента — Damir

## Проект
Виджет для торгового терминала Т-Инвестиции (T-Invest API). Таблица фьючерсов: название актива, цена закрытия дневной свечи, цена открытия утренней свечи, изменение в процентах. Настройки: выбор фьючерсов галочками.

## Структура проекта
- `ROADMAP_DAMIR.md` — планы
- `DONE_LIST_DAMIR.md` — выполненные задачи
- `SESSION_SUMMARY_ДАТА.md` — последняя сессия
- `README_FOR_NEXT_AGENT.md` — инструкция для агента
- `docs/` — база знаний, спеки

## API
- **T-Invest API:** [developer.tbank.ru/invest](https://developer.tbank.ru/invest/intro/intro/)
- **InstrumentsService:** Futures, FutureBy — список и данные фьючерсов
- **MarketDataService:** GetCandles — исторические свечи (interval = day → дневная свеча: open, close)
- Токен: переменные окружения (env_vars.txt / .env), не коммитить

## Workflow
1. Читать ROADMAP, DONE_LIST, SESSION_SUMMARY
2. Спеки в docs/specs/
3. Реализация с тестами и логированием
4. При завершении сессии — обновить SESSION_SUMMARY, DONE_LIST, ROADMAP

## Важно
- Проект хранится локально (Damir в .gitignore)
- Секреты только в env, не в коде
