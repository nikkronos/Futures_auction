# Инструкция по деплою

## Быстрый деплой

### 1. Локально (коммит и пуш)

```bash
# Перейти в папку проекта
cd Damir

# Добавить изменения
git add static/index.html
# или все изменения:
git add .

# Закоммитить
git commit -m "описание изменений"

# Запушить
git push
```

### 2. На сервере (обновление)

```bash
# Подключиться к серверу
ssh root@81.200.146.32

# Перейти в рабочую папку
cd ~/Futures_auction

# Обновить код
git pull

# Скопировать в папку деплоя
cp -r . /opt/futures_auction/

# Перезапустить сервис (если нужно)
systemctl restart futures_auction

# Проверить статус
systemctl status futures_auction
```

---

## Структура деплоя

### Папки на сервере

- **`~/Futures_auction`** — рабочая папка (клон репозитория)
- **`/opt/futures_auction`** — папка деплоя (откуда запускается сервис)

### Файлы

- **`server.py`** — Flask-приложение
- **`static/index.html`** — фронтенд
- **`env_vars.txt`** — переменные окружения (токен, SANDBOX)
- **`.venv/`** — виртуальное окружение Python

---

## Переменные окружения

**Файл:** `/opt/futures_auction/env_vars.txt`

```
TINKOFF_INVEST_TOKEN=your_token_here
SANDBOX=0  # 0 = боевой контур, 1 = sandbox
```

**Важно:** файл должен быть в папке деплоя, сервер читает его автоматически.

---

## systemd сервис

### Файл сервиса

**Путь:** `/etc/systemd/system/futures_auction.service`

```ini
[Unit]
Description=Futures Auction Widget
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/futures_auction
Environment="PATH=/opt/futures_auction/.venv/bin:/usr/bin"
ExecStart=/opt/futures_auction/.venv/bin/python server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### Команды управления

```bash
# Включить автозапуск
sudo systemctl enable futures_auction

# Запустить
sudo systemctl start futures_auction

# Остановить
sudo systemctl stop futures_auction

# Перезапустить
sudo systemctl restart futures_auction

# Статус
sudo systemctl status futures_auction

# Логи
sudo journalctl -u futures_auction -f
```

---

## Проверка работы

### После деплоя проверить:

1. **Сервис запущен:**
   ```bash
   systemctl status futures_auction
   ```

2. **Виджет доступен:**
   - Открыть: http://81.200.146.32:5000
   - Должна загрузиться страница с таблицей

3. **API работает:**
   ```bash
   curl http://81.200.146.32:5000/api/futures
   ```

4. **Логи без ошибок:**
   ```bash
   journalctl -u futures_auction -n 50
   ```

---

## Откат изменений

Если что-то пошло не так:

```bash
# На сервере
cd ~/Futures_auction

# Откатить к предыдущему коммиту
git log  # найти нужный коммит
git reset --hard <commit_hash>

# Или откатить к последнему коммиту на remote
git reset --hard origin/main

# Скопировать обратно
cp -r . /opt/futures_auction/

# Перезапустить
systemctl restart futures_auction
```

---

## Первоначальная настройка сервера

### Если сервер новый:

1. **Установить Python и зависимости:**
   ```bash
   apt update
   apt install python3 python3-venv git
   ```

2. **Клонировать репозиторий:**
   ```bash
   cd ~
   git clone https://github.com/nikkronos/Futures_auction.git
   ```

3. **Создать виртуальное окружение:**
   ```bash
   cd Futures_auction
   python3 -m venv .venv
   source .venv/bin/activate
   pip install flask requests
   ```

4. **Создать `env_vars.txt`:**
   ```bash
   echo "TINKOFF_INVEST_TOKEN=your_token" > env_vars.txt
   echo "SANDBOX=0" >> env_vars.txt
   ```

5. **Скопировать в папку деплоя:**
   ```bash
   mkdir -p /opt/futures_auction
   cp -r . /opt/futures_auction/
   ```

6. **Создать systemd сервис:**
   ```bash
   nano /etc/systemd/system/futures_auction.service
   # Вставить содержимое из раздела выше
   ```

7. **Запустить сервис:**
   ```bash
   systemctl daemon-reload
   systemctl enable futures_auction
   systemctl start futures_auction
   ```

---

## Проблемы и решения

### Сервис не запускается

**Проверить логи:**
```bash
journalctl -u futures_auction -n 100
```

**Частые причины:**
- Неверный путь к Python в `.venv/bin/python`
- Отсутствует файл `env_vars.txt`
- Порт 5000 занят другим процессом

### Виджет не загружается

**Проверить:**
1. Сервис запущен: `systemctl status futures_auction`
2. Порт открыт: `netstat -tlnp | grep 5000`
3. Файрвол разрешает порт 5000

### API возвращает ошибки

**Проверить:**
1. Токен в `env_vars.txt` валидный
2. SANDBOX=0 для боевого контура, SANDBOX=1 для sandbox
3. Логи сервера: `journalctl -u futures_auction -f`

---

**Обновлено:** 2026-02-12
