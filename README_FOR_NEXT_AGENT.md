# Инструкция для агента — Damir

## Проект
Виджет для торгового терминала Т-Инвестиции: таблица фьючерсов (название, цена закрытия, цена открытия, изменение %), настройки выбора фьючерсов.

## Перед началом
1. Прочитай ROADMAP_DAMIR.md, DONE_LIST_DAMIR.md, последний SESSION_SUMMARY_*.md.
2. Изучи docs/agent-onboarding.md и docs/specs/widget-futures-table.md.

## API
- [T-Invest API](https://developer.tbank.ru/invest/intro/intro/) — gRPC/REST, токен обязателен.
- InstrumentsService: Futures — список фьючерсов.
- MarketDataService: GetCandles — дневные свечи (open, close).
- Токен и sandbox/prod — из переменных окружения (env_vars.txt / .env).

## Правила
- Секреты не коммитить, не хардкодить.
- Проект пока локальный (Damir в .gitignore).

---

**См. также:** RULES_CURSOR.md в корне репозитория.
