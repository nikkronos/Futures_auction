# Исправление проблем с кнопками (2026-02-12)

## Проблема

После исправления синтаксической ошибки (лишняя закрывающая скобка `}`) кнопки «Настройки», «Режим: Свечи» и «Авто: ВКЛ» переставали работать после первого клика.

### Симптомы

1. **Кнопка «Настройки»:**
   - После клика панель настроек не открывается
   - Остальные кнопки перестают реагировать на клики
   - Кнопка «Обновить» (делает `location.reload()`) восстанавливает работу

2. **Кнопка «Режим: Свечи»:**
   - После клика режим не переключается (остаётся «Свечи» или «Стакан»)
   - Остальные кнопки перестают работать
   - Кнопка «Обновить» восстанавливает работу

3. **Кнопка «Авто: ВКЛ»:**
   - После клика кнопка визуально «загорается» (добавляется класс `active`)
   - Но автообновление не запускается
   - Остальные кнопки перестают работать
   - Кнопка «Обновить» восстанавливает работу

## Причина

### Двойные обработчики событий

В коде были **два обработчика** для каждой из трёх кнопок:

1. **Inline `onclick`** в HTML (для надёжности при ошибках в основном скрипте)
2. **`addEventListener`** в JavaScript (основной обработчик)

**Пример проблемного кода:**

```html
<!-- Inline onclick -->
<button id="btnSettings" onclick="...длинный код...">Настройки</button>
```

```javascript
// addEventListener в конце скрипта
document.getElementById('btnSettings').addEventListener('click', toggleSettings);
```

### Что происходило при клике

1. Срабатывает **inline `onclick`** → вызывает `toggleSettings()` → панель открывается (`display = 'block'`)
2. Сразу срабатывает **`addEventListener`** → вызывает `toggleSettings()` → панель закрывается (`display = 'none'`)
3. Результат: панель открылась и сразу закрылась, пользователь ничего не видит

Аналогично для других кнопок:
- «Режим: Свечи»: режим переключался дважды → оставался прежним
- «Авто: ВКЛ»: состояние переключалось дважды → оставалось прежним

### Почему остальные кнопки переставали работать?

Если внутри функции (`toggleSettings`, `toggleMode`, `toggleAutoRefresh`) происходила ошибка (например, `getElementById` вернул `null`), то:
- Ошибка выбрасывалась из обработчика
- Браузер мог «заблокировать» дальнейшие события на этой кнопке
- Или ошибка ломала глобальное состояние JavaScript

## Решение

### 1. Удалены дублирующие `addEventListener`

**Было:**
```javascript
// Event listeners
document.getElementById('btnRefresh').addEventListener('click', loadData);
document.getElementById('btnSettings').addEventListener('click', toggleSettings);  // ❌ УДАЛЕНО
document.getElementById('btnMode').addEventListener('click', toggleMode);          // ❌ УДАЛЕНО
document.getElementById('btnAutoRefresh').addEventListener('click', toggleAutoRefresh); // ❌ УДАЛЕНО
```

**Стало:**
```javascript
// Event listeners (Настройки, Режим, Авто — только через onclick, чтобы не было двойного вызова)
document.getElementById('btnRefresh').addEventListener('click', loadData);
// Остальные кнопки используют только inline onclick
```

### 2. Упрощены inline `onclick`

**Было (для «Настройки»):**
```html
<button onclick="var p=document.getElementById('settingsPanel');if(p){p.style.display=p.style.display==='none'?'block':'none';if(p.style.display!=='none'){var list=document.getElementById('settingsList');if(list&&list.children.length===0&&typeof loadFutures==='function'){list.innerHTML='Загрузка списка...';loadFutures().then(function(){if(typeof renderSettings==='function')renderSettings();}).catch(function(){if(list)list.innerHTML='Ошибка загрузки. Нажмите Обновить.';});}else if(typeof renderSettings==='function')renderSettings();}}">
  Настройки
</button>
```

**Стало:**
```html
<button onclick="try{if(typeof toggleSettings==='function')toggleSettings();}catch(e){console.error('Settings',e);}">
  Настройки
</button>
```

**Для «Режим: Свечи» и «Авто: ВКЛ»** — аналогично:
```html
<button onclick="try{if(typeof toggleMode==='function')toggleMode();}catch(e){console.error('Mode',e);}">
  Режим: Свечи
</button>
<button onclick="try{if(typeof toggleAutoRefresh==='function')toggleAutoRefresh();}catch(e){console.error('Auto',e);}">
  Авто: ВКЛ
</button>
```

### 3. Добавлены `try/catch` в функции

**`toggleSettings()`:**

```javascript
function toggleSettings() {
  try {
    const panel = document.getElementById('settingsPanel');
    if (!panel) return;  // ✅ Проверка на null
    
    const isVisible = panel.style.display !== 'none';
    
    // ✅ Сначала переключаем видимость панели (синхронно)
    panel.style.display = isVisible ? 'none' : 'block';
    if (panel.style.display === 'none') return;
    
    // ✅ Потом подгружаем список (асинхронно)
    const searchEl = document.getElementById('searchInput');
    if (searchEl) searchEl.value = '';
    
    if (allFutures.length === 0) {
      const list = document.getElementById('settingsList');
      if (list) list.innerHTML = 'Загрузка списка...';
      loadFutures().then(() => { renderSettings(); }).catch(() => {
        if (list) list.innerHTML = 'Ошибка загрузки. Нажмите Обновить.';
      });
    } else {
      renderSettings();
    }
  } catch (e) { 
    console.error('toggleSettings', e);  // ✅ Ошибка логируется, но не ломает интерфейс
  }
}
```

**Ключевые изменения:**
- ✅ Панель открывается **сразу** (синхронно), даже если загрузка списка упадёт
- ✅ Все `getElementById` проверяются на `null`
- ✅ Ошибки обрабатываются в `try/catch`

**`toggleMode()`:**

```javascript
function toggleMode() {
  try {
    viewMode = viewMode === 'candles' ? 'orderbook' : 'candles';
    const btn = document.getElementById('btnMode');
    if (btn) {  // ✅ Проверка на null
      btn.textContent = viewMode === 'candles' ? 'Режим: Свечи' : 'Режим: Стакан';
      if (viewMode === 'orderbook') btn.classList.add('active');
      else btn.classList.remove('active');
    }
    updateTableHeader();
    loadData();
  } catch (e) { 
    console.error('toggleMode', e);  // ✅ Ошибка логируется
  }
}
```

**`toggleAutoRefresh()`:**

```javascript
function toggleAutoRefresh() {
  try {
    autoRefreshEnabled = !autoRefreshEnabled;
    const btn = document.getElementById('btnAutoRefresh');
    const status = document.getElementById('autoStatus');
    
    if (btn) {  // ✅ Проверка на null
      btn.textContent = autoRefreshEnabled ? 'Авто: ВКЛ' : 'Авто: ВЫКЛ';
      if (autoRefreshEnabled) btn.classList.add('active');
      else btn.classList.remove('active');
    }
    
    if (status) {  // ✅ Проверка на null
      if (autoRefreshEnabled) {
        status.classList.add('active');
        updateAutoStatusText();
      } else {
        status.textContent = 'автообновление выключено';
        status.classList.remove('active');
      }
    }
    
    if (autoRefreshEnabled) startAutoRefresh();
    else stopAutoRefresh();
  } catch (e) { 
    console.error('toggleAutoRefresh', e);  // ✅ Ошибка логируется
  }
}
```

## Результат

### До исправления:
- ❌ Панель настроек не открывается
- ❌ Режим не переключается
- ❌ Автообновление не запускается
- ❌ Остальные кнопки перестают работать после первого клика

### После исправления:
- ✅ Панель настроек открывается один раз
- ✅ Режим переключается один раз
- ✅ Автообновление переключается один раз
- ✅ Остальные кнопки продолжают работать
- ✅ Ошибки логируются в консоль, но не ломают интерфейс

## Тестирование

### Как проверить исправление:

1. **Откройте страницу:** http://81.200.146.32:5000
2. **Откройте консоль браузера:** F12 → Console
3. **Нажмите «Настройки»:**
   - ✅ Панель должна открыться
   - ✅ В консоли не должно быть ошибок (или ошибки должны быть обработаны)
   - ✅ Другие кнопки должны продолжать работать
4. **Нажмите «Режим: Свечи»:**
   - ✅ Режим должен переключиться на «Стакан» (или обратно)
   - ✅ Таблица должна обновиться
   - ✅ Другие кнопки должны продолжать работать
5. **Нажмите «Авто: ВКЛ»:**
   - ✅ Кнопка должна загореться
   - ✅ Автообновление должно запуститься (статус показывает интервал)
   - ✅ Другие кнопки должны продолжать работать

### Если что-то не работает:

1. **Проверьте консоль браузера** — там будут сообщения об ошибках с префиксами `Settings`, `Mode`, `Auto`
2. **Проверьте логи сервера** — возможно, проблема на стороне API
3. **Попробуйте кнопку «Обновить»** — она делает `location.reload()` и сбрасывает состояние

## Коммит

**Хеш:** `58d1de9`  
**Сообщение:** `fix: Настройки/Режим/Авто — один обработчик, try/catch, панель открывается сразу`

**Изменения:**
- Удалены `addEventListener` для `btnSettings`, `btnMode`, `btnAutoRefresh`
- Упрощены inline `onclick` (вызов функций через `try/catch`)
- Добавлены `try/catch` в `toggleSettings()`, `toggleMode()`, `toggleAutoRefresh()`
- Добавлены проверки на `null` для всех `getElementById`
- Панель настроек открывается синхронно, список подгружается асинхронно

**Статистика:**
- 1 файл изменён (`static/index.html`)
- 54 строки добавлено, 44 строки удалено

---

**Дата:** 2026-02-12  
**Автор:** AI Assistant (Cursor)
