"""
Backend для виджета «Таблица фьючерсов» Т-Инвестиции.
Использует REST API T-Invest (без SDK).
Токен читается из переменной окружения TINKOFF_INVEST_TOKEN.
"""
import logging
import os
import time
import threading
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request, send_from_directory
import requests
import urllib3

# Отключаем предупреждения об SSL (для локального тестирования)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== Кэширование ==========
# TTL в секундах
CACHE_TTL_FUTURES = 300  # 5 минут - список фьючерсов редко меняется
CACHE_TTL_CANDLES = 10   # 10 секунд - для обновления раз в 5 секунд

_cache = {}
_cache_lock = threading.Lock()


def _cache_get(key):
    """Получить значение из кэша, если не истёк TTL."""
    with _cache_lock:
        item = _cache.get(key)
        if item is None:
            return None
        value, expires_at = item
        if time.time() > expires_at:
            del _cache[key]
            return None
        return value


def _cache_set(key, value, ttl_seconds):
    """Сохранить значение в кэш с TTL."""
    with _cache_lock:
        _cache[key] = (value, time.time() + ttl_seconds)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# Загружаем переменные из env_vars.txt (если есть)
def _load_env_from_file():
    """Читаем токен из env_vars.txt в родительской папке или текущей."""
    for path in ["env_vars.txt", "../env_vars.txt", "../../env_vars.txt"]:
        try:
            full_path = os.path.join(os.path.dirname(__file__), path)
            if os.path.exists(full_path):
                with open(full_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, _, value = line.partition("=")
                            key = key.strip()
                            value = value.strip()
                            if key and value and not os.environ.get(key):
                                os.environ[key] = value
                                logger.info("Loaded %s from %s", key, path)
        except Exception as e:
            logger.debug("Could not read %s: %s", path, e)

_load_env_from_file()

app = Flask(__name__, static_folder="static", static_url_path="")

# T-Invest API REST endpoints
API_URL_PROD = "https://invest-public-api.tbank.ru/rest"
API_URL_SANDBOX = "https://sandbox-invest-public-api.tbank.ru/rest"


def _get_api_url():
    use_sandbox = os.environ.get("SANDBOX", "1").strip() in ("1", "true", "yes")
    return API_URL_SANDBOX if use_sandbox else API_URL_PROD


def _get_headers():
    token = os.environ.get("TINKOFF_INVEST_TOKEN", "").strip()
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _quotation_to_float(q) -> float:
    """Quotation dict (units + nano) -> float."""
    if not q:
        return 0.0
    units = int(q.get("units", 0) or 0)
    nano = int(q.get("nano", 0) or 0)
    return units + nano / 1e9


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


# Список акций (спот), которые нужно показывать
SPOT_TICKERS = ["PLZL", "SBER", "LKOH", "GAZP", "NVTK", "VTBR", "GMKN"]


@app.route("/api/futures")
def api_futures():
    """Список фьючерсов + избранных акций (спот) для настроек. Кэшируется на 5 минут."""
    token = os.environ.get("TINKOFF_INVEST_TOKEN", "").strip()
    if not token:
        logger.warning("TINKOFF_INVEST_TOKEN not set")
        return jsonify({"error": "TINKOFF_INVEST_TOKEN not set"}), 503

    # Проверяем кэш
    cache_key = "instruments_list"
    cached = _cache_get(cache_key)
    if cached is not None:
        logger.debug("instruments list from cache")
        return jsonify({"futures": cached, "cached": True})

    base_url = _get_api_url()
    headers = _get_headers()
    items = []

    # 1. Загружаем фьючерсы
    try:
        url = f"{base_url}/tinkoff.public.invest.api.contract.v1.InstrumentsService/Futures"
        resp = requests.post(url, headers=headers, json={}, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
        for inv in data.get("instruments", []):
            items.append({
                "figi": inv.get("figi", ""),
                "ticker": inv.get("ticker", ""),
                "name": inv.get("name") or inv.get("ticker", ""),
                "instrument_uid": inv.get("uid", "") or inv.get("figi", ""),
                "instrument_type": "futures",
            })
        logger.info("futures count=%s", len(items))
    except Exception as e:
        logger.exception("Error loading futures: %s", e)

    # 2. Загружаем только избранные акции (спот)
    try:
        url = f"{base_url}/tinkoff.public.invest.api.contract.v1.InstrumentsService/Shares"
        resp = requests.post(url, headers=headers, json={}, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
        shares_count = 0
        spot_tickers_upper = [t.upper() for t in SPOT_TICKERS]
        for inv in data.get("instruments", []):
            ticker = inv.get("ticker", "")
            # Только акции из списка SPOT_TICKERS
            if ticker.upper() in spot_tickers_upper:
                items.append({
                    "figi": inv.get("figi", ""),
                    "ticker": ticker,
                    "name": inv.get("name") or ticker,
                    "instrument_uid": inv.get("uid", "") or inv.get("figi", ""),
                    "instrument_type": "shares",
                })
                shares_count += 1
        logger.info("shares (spot) count=%s", shares_count)
    except Exception as e:
        logger.exception("Error loading shares: %s", e)

    logger.info("total instruments=%s (fresh)", len(items))
    _cache_set(cache_key, items, CACHE_TTL_FUTURES)
    return jsonify({"futures": items})


def _fetch_candles_for_instrument(instrument_id, base_url, headers, from_ts, to_ts):
    """Получить свечи для одного инструмента (с кэшированием)."""
    cache_key = f"candles_{instrument_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached, True  # (result, is_cached)

    try:
        url = f"{base_url}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetCandles"
        payload = {
            "instrumentId": instrument_id,
            "from": from_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": to_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "interval": "CANDLE_INTERVAL_DAY",
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=30, verify=False)
        resp.raise_for_status()
        data = resp.json()
        candles = data.get("candles", [])

        if not candles:
            result = {
                "instrument_id": instrument_id,
                "name": instrument_id,
                "close": None,
                "open": None,
                "change_pct": None,
                "error": "no data",
            }
        elif len(candles) < 2:
            # Только одна свеча (сегодняшняя) - нет вчерашних данных
            today = candles[-1]
            open_price = _quotation_to_float(today.get("open"))
            close_price = _quotation_to_float(today.get("close"))
            result = {
                "instrument_id": instrument_id,
                "name": instrument_id,
                "close": round(close_price, 4) if close_price else None,
                "open": round(open_price, 4) if open_price else None,
                "change_pct": None,
            }
        else:
            # Вчерашняя свеча (предпоследняя) и сегодняшняя (последняя)
            yesterday = candles[-2]
            today = candles[-1]
            yesterday_close = _quotation_to_float(yesterday.get("close"))
            today_open = _quotation_to_float(today.get("open"))
            change_pct = None
            if yesterday_close and yesterday_close != 0:
                change_pct = round((today_open - yesterday_close) / yesterday_close * 100, 2)
            result = {
                "instrument_id": instrument_id,
                "name": instrument_id,
                "close": round(yesterday_close, 4) if yesterday_close else None,
                "open": round(today_open, 4) if today_open else None,
                "change_pct": change_pct,
            }
        
        _cache_set(cache_key, result, CACHE_TTL_CANDLES)
        return result, False
    except requests.RequestException as e:
        logger.warning("get_candles %s: %s", instrument_id, e)
        return {
            "instrument_id": instrument_id,
            "name": instrument_id,
            "close": None,
            "open": None,
            "change_pct": None,
            "error": str(e),
        }, False


@app.route("/api/table")
def api_table():
    """Данные для таблицы: по списку instrument_id — последняя дневная свеча (open, close) + лоты из стакана.
    Свечи кэшируются на 10 секунд для каждого инструмента."""
    token = os.environ.get("TINKOFF_INVEST_TOKEN", "").strip()
    if not token:
        return jsonify({"error": "TINKOFF_INVEST_TOKEN not set"}), 503

    ids_param = request.args.get("ids", "")
    if not ids_param:
        return jsonify({"rows": []})
    instrument_ids = [x.strip() for x in ids_param.split(",") if x.strip()]

    # Период: последние 7 дней по UTC
    to_ts = datetime.now(timezone.utc)
    from_ts = to_ts - timedelta(days=7)

    base_url = _get_api_url()
    headers = _get_headers()

    rows = []
    cached_count = 0
    for instrument_id in instrument_ids:
        result, is_cached = _fetch_candles_for_instrument(
            instrument_id, base_url, headers, from_ts, to_ts
        )
        # Добавляем лоты из стакана
        orderbook, _ = _fetch_orderbook(instrument_id, base_url, headers, depth=1)
        result["total_lots"] = orderbook.get("total_lots")
        rows.append(result)
        if is_cached:
            cached_count += 1

    logger.info("table: total=%d, cached=%d, fresh=%d", len(rows), cached_count, len(rows) - cached_count)
    return jsonify({"rows": rows})


def _is_auction_time():
    """Проверить, сейчас ли время аукциона (по московскому времени)."""
    # Московское время = UTC + 3
    now_utc = datetime.now(timezone.utc)
    moscow_offset = timedelta(hours=3)
    now_msk = now_utc + moscow_offset
    
    hour = now_msk.hour
    minute = now_msk.minute
    weekday = now_msk.weekday()  # 0=пн, 6=вс
    
    time_minutes = hour * 60 + minute
    
    # Аукцион открытия: Пн-Пт 8:50-9:00, Сб-Вс 9:50-10:00
    if weekday < 5:  # Пн-Пт
        opening_start = 8 * 60 + 50  # 8:50
        opening_end = 9 * 60  # 9:00
    else:  # Сб-Вс
        opening_start = 9 * 60 + 50  # 9:50
        opening_end = 10 * 60  # 10:00
    
    # Аукцион закрытия: 18:40-18:50 (каждый день)
    closing_start = 18 * 60 + 40  # 18:40
    closing_end = 18 * 60 + 50  # 18:50
    
    is_opening = opening_start <= time_minutes < opening_end
    is_closing = closing_start <= time_minutes < closing_end
    
    return {
        "is_auction": is_opening or is_closing,
        "auction_type": "opening" if is_opening else ("closing" if is_closing else None),
        "moscow_time": now_msk.strftime("%H:%M:%S"),
    }


def _fetch_orderbook(instrument_id, base_url, headers, depth=10):
    """Получить стакан для инструмента."""
    cache_key = f"orderbook_{instrument_id}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached, True
    
    try:
        url = f"{base_url}/tinkoff.public.invest.api.contract.v1.MarketDataService/GetOrderBook"
        payload = {
            "instrumentId": instrument_id,
            "depth": depth,
        }
        resp = requests.post(url, headers=headers, json=payload, timeout=10, verify=False)
        resp.raise_for_status()
        data = resp.json()
        
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        
        best_bid = _quotation_to_float(bids[0].get("price")) if bids else None
        best_ask = _quotation_to_float(asks[0].get("price")) if asks else None
        
        # Суммарный объём заявок
        total_bid_lots = sum(int(b.get("quantity", 0)) for b in bids)
        total_ask_lots = sum(int(a.get("quantity", 0)) for a in asks)
        
        # Приблизительная цена аукциона (середина спреда)
        auction_price = None
        if best_bid and best_ask:
            auction_price = round((best_bid + best_ask) / 2, 4)
        
        # Последняя цена
        last_price = _quotation_to_float(data.get("lastPrice"))
        close_price = _quotation_to_float(data.get("closePrice"))
        
        # Отклонение от последней цены
        deviation_pct = None
        reference_price = last_price or close_price
        if auction_price and reference_price and reference_price != 0:
            deviation_pct = round((auction_price - reference_price) / reference_price * 100, 2)
        
        result = {
            "instrument_id": instrument_id,
            "best_bid": round(best_bid, 4) if best_bid else None,
            "best_ask": round(best_ask, 4) if best_ask else None,
            "spread": round(best_ask - best_bid, 4) if (best_bid and best_ask) else None,
            "auction_price": auction_price,
            "last_price": round(last_price, 4) if last_price else None,
            "close_price": round(close_price, 4) if close_price else None,
            "deviation_pct": deviation_pct,
            "total_bid_lots": total_bid_lots,
            "total_ask_lots": total_ask_lots,
            "total_lots": total_bid_lots + total_ask_lots,
        }
        
        # Кэш на 1 секунду для стакана
        # Кэш на 5 секунд для стакана
        _cache_set(cache_key, result, 5)
        return result, False
    except Exception as e:
        logger.warning("get_orderbook %s: %s", instrument_id, e)
        return {
            "instrument_id": instrument_id,
            "error": str(e),
        }, False


@app.route("/api/orderbook")
def api_orderbook():
    """Данные стакана для аукциона."""
    token = os.environ.get("TINKOFF_INVEST_TOKEN", "").strip()
    if not token:
        return jsonify({"error": "TINKOFF_INVEST_TOKEN not set"}), 503

    ids_param = request.args.get("ids", "")
    if not ids_param:
        return jsonify({"rows": [], "auction": _is_auction_time()})
    
    instrument_ids = [x.strip() for x in ids_param.split(",") if x.strip()]
    
    base_url = _get_api_url()
    headers = _get_headers()
    
    rows = []
    for instrument_id in instrument_ids:
        result, _ = _fetch_orderbook(instrument_id, base_url, headers)
        rows.append(result)
    
    auction_info = _is_auction_time()
    logger.info("orderbook: total=%d, auction=%s", len(rows), auction_info.get("is_auction"))
    return jsonify({"rows": rows, "auction": auction_info})


def main():
    port = int(os.environ.get("PORT", "5000"))
    sandbox = "sandbox" if os.environ.get("SANDBOX", "1").strip() in ("1", "true", "yes") else "prod"
    logger.info("Starting server port=%s mode=%s", port, sandbox)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
