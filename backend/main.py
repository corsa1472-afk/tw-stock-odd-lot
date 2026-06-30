import sys
import os
os.environ['no_proxy'] = 'localhost,127.0.0.1'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, write_through=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, write_through=True)
import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from typing import Optional, List
import threading
import time
import datetime

# Import SinoPac Connector (which is now our Mock yfinance-driven monitor)
from shiopac_connector import SinoPacConnector

app = FastAPI(title="Taiwan Stock Odd-Lot & Full Market Scanner API")

@app.get("/api/health")
def health_check():
    return {"ok": True}

# Global HEAD Request Middleware
class HeadMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "HEAD":
            request.scope["method"] = "GET"
            response = await call_next(request)
            headers = dict(response.headers)
            headers.pop("content-length", None)
            return Response(
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type
            )
        return await call_next(request)

app.add_middleware(HeadMiddleware)

# Enable CORS for the local frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

DATA_FILE = os.path.join(BASE_DIR, "trending_stocks.json")
POTENTIAL_STOCKS_FILE = os.path.join(BASE_DIR, "potential_stocks.json")
POTENTIAL_US_STOCKS_FILE = os.path.join(BASE_DIR, "potential_us_stocks.json")
MONITOR_FILE = os.path.join(BASE_DIR, "monitor_list.json")
TRAILING_FILE = os.path.join(BASE_DIR, "trailing_list.json")
ALL_STOCKS_FILE = os.path.join(DATA_DIR, "all_tw_stocks.json")
US_STOCKS_FILE = os.path.join(DATA_DIR, "us_stocks.json")
US_COMPANY_PROFILES_FILE = os.path.join(DATA_DIR, "us_company_profiles.json")

US_INDEX_ETFS = [
    {"code": "SPY", "symbol": "SPY", "name": "SPDR S&P 500 ETF", "category": "指標ETF", "market": "US"},
    {"code": "QQQ", "symbol": "QQQ", "name": "Invesco QQQ Trust", "category": "指標ETF", "market": "US"},
    {"code": "DIA", "symbol": "DIA", "name": "SPDR Dow Jones ETF", "category": "指標ETF", "market": "US"},
    {"code": "IWM", "symbol": "IWM", "name": "iShares Russell 2000 ETF", "category": "指標ETF", "market": "US"},
]

YAHOO_TW_US_INDICATORS = {
    "AAPL": "蘋果", "GOOG": "谷歌", "META": "Meta Platforms", "AMZN": "亞馬遜",
    "NFLX": "網飛", "VZ": "威訊通訊", "MSFT": "微軟", "INTC": "英特爾",
    "CSCO": "思科系統", "BABA": "阿里巴巴", "ORCL": "甲骨文", "T": "AT&T",
    "HPQ": "HP", "IBM": "IBM", "MU": "美光", "ASML": "艾司摩爾",
    "TXN": "德儀", "AMD": "AMD", "AVGO": "博通", "NXPI": "恩智浦",
    "NVDA": "NVIDIA", "V": "Visa", "MA": "Mastercard", "BAC": "美國銀行",
    "C": "花旗集團", "AXP": "美國運通", "WFC": "富國銀行",
    "BRK-B": "波克夏海瑟威B", "GS": "高盛", "JPM": "摩根大通",
    "TSLA": "特斯拉", "GM": "通用汽車", "BA": "波音", "F": "福特汽車",
    "XOM": "埃克森美孚", "JNJ": "嬌生",
}

YAHOO_TW_US_STOCKS = [
    {"code": symbol, "symbol": symbol, "name": name, "category": "Yahoo指標", "market": "US"}
    for symbol, name in YAHOO_TW_US_INDICATORS.items()
]

DEFAULT_US_STOCKS = US_INDEX_ETFS + YAHOO_TW_US_STOCKS
YAHOO_TW_US_MARKET_URL = "https://tw.stock.yahoo.com/us-market"

BUSINESS_CACHE_FILE = os.path.join(BASE_DIR, "business_desc_cache.json")
TW_ANALYSIS_CACHE_FILE = os.path.join(DATA_DIR, "tw_analysis_cache.json")
US_ANALYSIS_CACHE_FILE = os.path.join(DATA_DIR, "us_analysis_cache.json")
ANALYSIS_CACHE_TTL_SECONDS = 900
business_desc_cache = {}
institutional_daily_cache = {}
major_holder_cache = {}
chart_data_cache = {}
monitor_quote_cache = {"checked_at": 0.0, "quotes": {}}
us_monitor_quote_cache = {"checked_at": 0.0, "quotes": {}}
cached_all_us_stocks = []
us_company_profiles = {}
us_company_profiles_lock = threading.Lock()

def is_tw_market_open(now_tw=None):
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = now_tw or datetime.datetime.now(tz)
    return (
        now_tw.weekday() < 5
        and datetime.time(8, 30) <= now_tw.time() < datetime.time(13, 30)
    )

def is_us_market_open(now_utc=None):
    try:
        from zoneinfo import ZoneInfo
        tz_us = ZoneInfo("America/New_York")
    except ImportError:
        try:
            import pytz
            tz_us = pytz.timezone("America/New_York")
        except ImportError:
            tz_us = datetime.timezone(datetime.timedelta(hours=-4))
    now_us = (now_utc or datetime.datetime.now(datetime.timezone.utc)).astimezone(tz_us)
    return (
        now_us.weekday() < 5
        and datetime.time(9, 30) <= now_us.time() < datetime.time(16, 0)
    )

def get_last_market_close(market_type="TW"):
    import datetime
    if market_type == "TW":
        tz = datetime.timezone(datetime.timedelta(hours=8))
        now = datetime.datetime.now(tz)
        days_to_subtract = 0
        if now.weekday() == 5: # Saturday
            days_to_subtract = 1
        elif now.weekday() == 6: # Sunday
            days_to_subtract = 2
        elif now.weekday() == 0 and now.time() < datetime.time(13, 30): # Monday before 13:30
            days_to_subtract = 3
        elif now.time() < datetime.time(13, 30):
            days_to_subtract = 1
        
        last_close_date = now.date() - datetime.timedelta(days=days_to_subtract)
        last_close_dt = datetime.datetime.combine(last_close_date, datetime.time(13, 30), tzinfo=tz)
        return last_close_dt
    else: # US
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo("America/New_York")
        except ImportError:
            try:
                import pytz
                tz = pytz.timezone("America/New_York")
            except ImportError:
                tz = datetime.timezone(datetime.timedelta(hours=-4))
        
        now = datetime.datetime.now(datetime.timezone.utc).astimezone(tz)
        days_to_subtract = 0
        if now.weekday() == 5: # Saturday
            days_to_subtract = 1
        elif now.weekday() == 6: # Sunday
            days_to_subtract = 2
        elif now.weekday() == 0 and now.time() < datetime.time(16, 0): # Monday before 16:00
            days_to_subtract = 3
        elif now.time() < datetime.time(16, 0):
            days_to_subtract = 1
            
        last_close_date = now.date() - datetime.timedelta(days=days_to_subtract)
        last_close_dt = datetime.datetime.combine(last_close_date, datetime.time(16, 0), tzinfo=tz)
        return last_close_dt

def fetch_all_us_stocks():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    stocks = []
    seen_symbols = set()
    
    # 1. Fetch S&P 500 from Wikipedia
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find("table", {"id": "constituents"})
            if table:
                rows = table.find_all("tr")[1:] # Skip header
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        symbol = tds[0].text.strip().replace('.', '-')
                        name = tds[1].text.strip()
                        if symbol and symbol not in seen_symbols:
                            stocks.append({
                                "code": symbol,
                                "symbol": symbol,
                                "name": name,
                                "market": "US",
                                "added_by": "scan"
                            })
                            seen_symbols.add(symbol)
    except Exception as e:
        print(f"Error fetching S&P 500: {e}", flush=True)

    # 2. Fetch Nasdaq 100 from Wikipedia
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        res = requests.get(url, headers=headers, timeout=10)
        if res.ok:
            soup = BeautifulSoup(res.text, 'html.parser')
            table = soup.find("table", {"id": "constituents"})
            if table:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    tds = row.find_all("td")
                    if len(tds) >= 2:
                        t1 = tds[0].text.strip().replace('.', '-')
                        t2 = tds[1].text.strip().replace('.', '-')
                        if t2.isupper() and 1 <= len(t2) <= 5:
                            symbol = t2
                            name = tds[0].text.strip()
                        elif t1.isupper() and 1 <= len(t1) <= 5:
                            symbol = t1
                            name = tds[1].text.strip()
                        else:
                            symbol = t2
                            name = tds[0].text.strip()
                            
                        if symbol and symbol not in seen_symbols and symbol.isalnum():
                            stocks.append({
                                "code": symbol,
                                "symbol": symbol,
                                "name": name,
                                "market": "US",
                                "added_by": "scan"
                            })
                            seen_symbols.add(symbol)
    except Exception as e:
        print(f"Error fetching Nasdaq 100: {e}", flush=True)
        
    # Mega cap fallbacks if Wikipedia fails
    if len(stocks) < 50:
        fallback_symbols = [
            ("AAPL", "Apple Inc."), ("MSFT", "Microsoft Corp."), ("GOOGL", "Alphabet Inc."),
            ("AMZN", "Amazon.com Inc."), ("NVDA", "Nvidia Corp."), ("META", "Meta Platforms Inc."),
            ("TSLA", "Tesla Inc."), ("BRK-B", "Berkshire Hathaway Inc."), ("LLY", "Eli Lilly & Co."),
            ("AVGO", "Broadcom Inc."), ("V", "Visa Inc."), ("JPM", "JPMorgan Chase & Co."),
            ("TSM", "Taiwan Semiconductor"), ("UNH", "UnitedHealth Group"), ("MA", "Mastercard Inc."),
            ("WMT", "Walmart Inc."), ("XOM", "Exxon Mobil Corp."), ("JNJ", "Johnson & Johnson"),
            ("PG", "Procter & Gamble"), ("ORCL", "Oracle Corp."), ("COST", "Costco Wholesale"),
            ("HD", "Home Depot"), ("NFLX", "Netflix Inc."), ("AMD", "Advanced Micro Devices"),
            ("QCOM", "Qualcomm Inc."), ("TXN", "Texas Instruments"), ("INTC", "Intel Corp."),
            ("AMGN", "Amgen Inc."), ("HON", "Honeywell International"), ("SBUX", "Starbucks Corp.")
        ]
        for symbol, name in fallback_symbols:
            if symbol not in seen_symbols:
                stocks.append({
                    "code": symbol,
                    "symbol": symbol,
                    "name": name,
                    "market": "US",
                    "added_by": "scan"
                })
                seen_symbols.add(symbol)
                
    return stocks

def load_all_us_stocks_cache():
    global cached_all_us_stocks
    try:
        cached_all_us_stocks = fetch_all_us_stocks()
        print(f"Loaded {len(cached_all_us_stocks)} US stocks for autocomplete.", flush=True)
    except Exception as e:
        print(f"Error loading US stocks for autocomplete: {e}", flush=True)

def _twse_number(value):
    try:
        text = str(value or "").split("_", 1)[0].replace(",", "").strip()
        return float(text) if text and text != "-" else None
    except (TypeError, ValueError):
        return None

def fetch_twse_realtime_quotes(stocks):
    """Fetch current/final official quotes from TWSE MIS for TWSE and TPEx symbols."""
    channels = []
    stock_by_channel = {}
    for stock in stocks:
        code = str(stock.get("code", "")).upper()
        symbol = str(stock.get("symbol", "")).upper()
        if not code or not code[0].isdigit():
            continue
        exchange = "otc" if symbol.endswith(".TWO") else "tse"
        channel = f"{exchange}_{code}.tw"
        channels.append(channel)
        stock_by_channel[channel] = code
    if not channels:
        return {}

    result = {}
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://mis.twse.com.tw/stock/fibest.jsp",
    }
    
    batches = [channels[i:i + 50] for i in range(0, len(channels), 50)]
    
    def fetch_batch(batch):
        try:
            response = requests.get(
                "https://mis.twse.com.tw/stock/api/getStockInfo.jsp",
                params={"ex_ch": "|".join(batch), "json": "1", "delay": "0"},
                headers=headers,
                timeout=8,  # Reduced timeout to prevent long hangs
            )
            response.raise_for_status()
            return response.json().get("msgArray", [])
        except Exception as error:
            print(f"TWSE MIS quote batch fetch failed: {error}", flush=True)
            return []

    # Fetch all batches concurrently in parallel
    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        batch_results = list(executor.map(fetch_batch, batches))
        
    tz = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz)
    is_pre_opening = now_tw.weekday() < 5 and now_tw.time() < datetime.time(9, 0)

    for msg_array in batch_results:
        for item in msg_array:
            code = str(item.get("c", "")).upper()
            if not code:
                continue
            ref = _twse_number(item.get("y"))
            if is_pre_opening:
                last = ref
                open_val = None
                high_val = None
                low_val = None
                volume_val = 0
            else:
                last = _twse_number(item.get("z"))
                if last is None or last <= 0:
                    # z is '-' during intraday auction; try best bid price first
                    bid_str = item.get("b", "")
                    if bid_str and bid_str != "-":
                        first_bid = _twse_number(bid_str.split("_")[0])
                        if first_bid and first_bid > 0:
                            last = first_bid
                if last is None or last <= 0:
                    # Try best ask price (useful during limit-down)
                    ask_str = item.get("a", "")
                    if ask_str and ask_str != "-":
                        first_ask = _twse_number(ask_str.split("_")[0])
                        if first_ask and first_ask > 0:
                            last = first_ask
                if last is None or last <= 0:
                    # Try today's high price
                    last = _twse_number(item.get("h"))
                if last is None or last <= 0:
                    # Try today's open price
                    last = _twse_number(item.get("o"))
                if last is None or last <= 0:
                    last = ref
                open_val = _twse_number(item.get("o"))
                high_val = _twse_number(item.get("h"))
                low_val = _twse_number(item.get("l"))
                volume_val = _twse_number(item.get("v"))
            result[code] = {
                "price": last,
                "open": open_val,
                "high": high_val,
                "low": low_val,
                "reference": ref,
                "volume": volume_val,
                "time": item.get("t") or item.get("%") or "",
                "date": item.get("d") or item.get("^") or "",
                "limit_up": _twse_number(item.get("u")),
                "limit_down": _twse_number(item.get("w")),
                "source": "TWSE_MIS",
            }
            
    if not result:
        return fetch_fallback_quotes_from_yahoo(stocks)
    return result

def fetch_fallback_quotes_from_yahoo(stocks):
    """Fallback quote fetcher using Yahoo Finance (yfinance) in a single batch request."""
    tickers = []
    stock_by_symbol = {}
    for stock in stocks:
        symbol = stock.get("symbol")
        code = str(stock.get("code", "")).upper()
        if symbol and code:
            tickers.append(symbol)
            stock_by_symbol[symbol] = code
            
    if not tickers:
        return {}
        
    result = {}
    try:
        print(f"TWSE MIS failed or rate-limited. Falling back to Yahoo Finance for {len(tickers)} tickers...", flush=True)
        # Download 2 days of daily data
        df = yf.download(tickers, period="2d", interval="1d", progress=False, group_by="ticker", timeout=15, auto_adjust=False)
        if df.empty:
            return {}
            
        import datetime
        now = datetime.datetime.now()
        time_str = now.strftime("%H:%M:%S")
        date_str = now.strftime("%Y%m%d")
        
        for symbol in tickers:
            code = stock_by_symbol.get(symbol)
            if not code:
                continue
                
            # If only a single ticker was queried, yf.download might not return a multi-index DataFrame
            if len(tickers) == 1:
                ticker_df = df.dropna()
            else:
                ticker_df = df[symbol].dropna() if symbol in df else pd.DataFrame()
                
            if not ticker_df.empty:
                last_row = ticker_df.iloc[-1]
                price = float(last_row.get("Close")) if last_row.get("Close") is not None else None
                open_val = float(last_row.get("Open")) if last_row.get("Open") is not None else None
                high_val = float(last_row.get("High")) if last_row.get("High") is not None else None
                low_val = float(last_row.get("Low")) if last_row.get("Low") is not None else None
                volume_shares = float(last_row.get("Volume")) if last_row.get("Volume") is not None else 0.0
                volume_lots = int(volume_shares // 1000)
                
                reference = None
                if len(ticker_df) >= 2:
                    reference = float(ticker_df.iloc[-2].get("Close"))
                else:
                    # Fallback reference to open if no previous close
                    reference = open_val
                    
                result[code] = {
                    "price": price,
                    "open": open_val,
                    "high": high_val,
                    "low": low_val,
                    "reference": reference,
                    "volume": volume_lots,
                    "time": time_str,
                    "date": date_str,
                    "source": "Yahoo_Finance",
                }
    except Exception as e:
        print(f"Yahoo Finance fallback quotes fetch failed: {e}", flush=True)
        
    return result

def refresh_us_monitor_quotes(orders):
    us_orders = [
        order for order in orders
        if str(order.get("market", "TW")).upper() == "US"
        and order.get("status") != "CANCELLED"
    ]
    if not us_orders:
        return False
        
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    market_open = is_us_market_open(now_utc)
    
    checked_at = us_monitor_quote_cache.get("checked_at", 0.0)
    quotes = us_monitor_quote_cache.get("quotes", {})
    
    # Self-populate memory cache from saved orders if empty on startup
    if not quotes:
        for order in us_orders:
            sym = order.get("symbol")
            if sym and order.get("last_price") is not None:
                quotes[sym] = {
                    "price": order["last_price"],
                    "reference": order.get("reference_price"),
                    "date": order.get("quote_date"),
                    "time": order.get("quote_time"),
                    "source": order.get("quote_source"),
                }
        if quotes:
            us_monitor_quote_cache["checked_at"] = time.time()
            us_monitor_quote_cache["quotes"] = quotes
            checked_at = us_monitor_quote_cache["checked_at"]
            
    # Check if all orders are present in the cache
    all_cached = all(
        order.get("symbol") in quotes
        for order in us_orders if order.get("symbol")
    )
    
    if market_open:
        if all_cached and (time.time() - checked_at < 15.0):
            return update_us_orders_from_cache(us_orders)
    else:
        last_close = get_last_market_close("US")
        if all_cached and (checked_at >= last_close.timestamp()):
            return update_us_orders_from_cache(us_orders)
            
    symbols = list({order["symbol"] for order in us_orders if "symbol" in order})
    if not symbols:
        return False
        
    print(f"Refreshing US monitor quotes for {symbols}...", flush=True)
    try:
        df = yf.download(symbols, period="5d", interval="1d", progress=False, threads=False, timeout=15, auto_adjust=False)
        if df.empty:
            return False
            
        quotes_new = {}
        for sym in symbols:
            df_sym = None
            if isinstance(df.columns, pd.MultiIndex):
                if ('Close', sym) in df.columns:
                    df_sym = pd.DataFrame({
                        'Close': df[('Close', sym)],
                        'Open': df[('Open', sym)] if ('Open', sym) in df.columns else df[('Close', sym)]
                    }).dropna()
            else:
                if 'Close' in df.columns:
                    df_sym = pd.DataFrame({
                        'Close': df['Close'],
                        'Open': df['Open'] if 'Open' in df.columns else df['Close']
                    }).dropna()
                    
            if df_sym is not None and not df_sym.empty:
                latest_price = float(df_sym['Close'].iloc[-1])
                prev_close = float(df_sym['Close'].iloc[-2]) if len(df_sym) >= 2 else latest_price
                quotes_new[sym] = {
                    "price": latest_price,
                    "reference": prev_close,
                    "date": df_sym.index[-1].strftime("%Y%m%d"),
                    "time": now_utc.strftime("%H:%M:%S"),
                    "source": "yfinance"
                }
                
        if quotes_new:
            # Merge with existing cache
            existing_quotes = us_monitor_quote_cache.get("quotes", {})
            merged_quotes = {**existing_quotes, **quotes_new}
            us_monitor_quote_cache["checked_at"] = time.time()
            us_monitor_quote_cache["quotes"] = merged_quotes
            
        return update_us_orders_from_cache(us_orders)
    except Exception as e:
        print(f"Error refreshing US monitor quotes: {e}", flush=True)
        return False

def update_us_orders_from_cache(us_orders):
    quotes = us_monitor_quote_cache.get("quotes", {})
    updated = False
    for order in us_orders:
        sym = order.get("symbol")
        if not sym or sym not in quotes:
            continue
        quote = quotes[sym]
        
        previous = (
            order.get("last_price"),
            order.get("reference_price"),
            order.get("quote_date"),
            order.get("quote_time"),
            order.get("quote_source"),
        )
        
        order["last_price"] = round(quote["price"], 2)
        order["reference_price"] = round(quote["reference"], 2)
        order["quote_date"] = quote["date"]
        order["quote_time"] = quote["time"]
        order["quote_source"] = quote["source"]
        
        current = (
            order.get("last_price"),
            order.get("reference_price"),
            order.get("quote_date"),
            order.get("quote_time"),
            order.get("quote_source"),
        )
        
        updated = updated or (current != previous)
    return updated

def update_tw_orders_from_cache(tw_orders):
    quotes = monitor_quote_cache.get("quotes", {})
    updated = False
    for order in tw_orders:
        code = str(order.get("code", "")).upper()
        if not code or code not in quotes:
            continue
        quote = quotes[code]
        if quote.get("price") is None:
            continue
            
        previous = (
            order.get("last_price"),
            order.get("reference_price"),
            order.get("quote_date"),
            order.get("quote_time"),
            order.get("quote_source"),
        )
        
        def normalized_quote_date(value):
            text = str(value or "").replace("-", "")
            return text if len(text) == 8 and text.isdigit() else ""
            
        order["last_price"] = quote["price"]
        order["reference_price"] = quote.get("reference")
        order["quote_date"] = normalized_quote_date(quote.get("date"))
        order["quote_time"] = quote.get("time") or ""
        order["quote_source"] = quote.get("source") or "TWSE_MIS"
        if "limit_up" in quote:
            order["limit_up"] = quote["limit_up"]
        if "limit_down" in quote:
            order["limit_down"] = quote["limit_down"]
            
        current = (
            order.get("last_price"),
            order.get("reference_price"),
            order.get("quote_date"),
            order.get("quote_time"),
            order.get("quote_source"),
        )
        updated = updated or current != previous
    return updated

def refresh_tw_monitor_quotes(orders):
    """Refresh TW risk-list prices and validate completed-session quote caches using cache-first policy."""
    tw_orders = [
        order for order in orders
        if str(order.get("market", "TW")).upper() == "TW"
        and str(order.get("code", ""))[:1].isdigit()
        and order.get("status") != "CANCELLED"
    ]
    if not tw_orders:
        return False

    now_tw = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
    
    # Load prices from tw_analysis_cache.json first to synchronize with the left list's prices.
    # The analysis cache already excludes pre-opening simulated prices.
    cache_prices = {}
    if os.path.exists(TW_ANALYSIS_CACHE_FILE):
        try:
            with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cache_data = json.load(file)
                for item in cache_data:
                    code = str(item.get("code", "")).upper()
                    if code and item.get("current_price") is not None:
                        cache_prices[code] = {
                            "price": item["current_price"],
                            "reference": item.get("reference_price") or item["current_price"],
                            "date": item.get("quote_date") or now_tw.strftime("%Y%m%d"),
                            "time": item.get("quote_time") or "13:30:00",
                            "source": "Analysis_Cache",
                        }
                        if "limit_up" in item:
                            cache_prices[code]["limit_up"] = item["limit_up"]
                        if "limit_down" in item:
                            cache_prices[code]["limit_down"] = item["limit_down"]
        except Exception as e:
            print(f"Error reading tw_analysis_cache for monitor quotes: {e}", flush=True)

    market_open = is_tw_market_open(now_tw)

    checked_at = monitor_quote_cache.get("checked_at", 0.0)
    quotes = monitor_quote_cache.get("quotes", {})
    
    # Pre-populate memory cache from analysis cache to override old/stale prices
    for code, val in cache_prices.items():
        quotes[code] = val
    
    # Self-populate memory cache from saved orders if empty on startup
    if not quotes:
        for order in tw_orders:
            code = str(order.get("code", "")).upper()
            if code and order.get("last_price") is not None:
                quotes[code] = {
                    "price": order["last_price"],
                    "reference": order.get("reference_price"),
                    "date": order.get("quote_date"),
                    "time": order.get("quote_time"),
                    "source": order.get("quote_source"),
                }
        if quotes:
            monitor_quote_cache["checked_at"] = time.time()
            monitor_quote_cache["quotes"] = quotes
            checked_at = monitor_quote_cache["checked_at"]
            
    # Check if all orders are present in the cache
    all_cached = all(
        str(order.get("code", "")).upper() in quotes
        for order in tw_orders
    )
    
    if market_open:
        # During trading hours, allow reusing cache if it is less than 15 seconds old
        if all_cached and (time.time() - checked_at < 15.0):
            return update_tw_orders_from_cache(tw_orders)
    else:
        # Outside trading hours, check if cache was checked after the last close
        last_close = get_last_market_close("TW")
        if all_cached and (checked_at >= last_close.timestamp()):
            return update_tw_orders_from_cache(tw_orders)

    # Fetch new quotes
    print(f"Refreshing TW monitor quotes for {[o.get('code') for o in tw_orders]}...", flush=True)
    quotes_new = fetch_twse_realtime_quotes(tw_orders)
    if quotes_new:
        # Merge with existing cache to avoid losing other symbols
        existing_quotes = monitor_quote_cache.get("quotes", {})
        merged_quotes = {**existing_quotes, **quotes_new}
        monitor_quote_cache["checked_at"] = time.time()
        monitor_quote_cache["quotes"] = merged_quotes
        
    return update_tw_orders_from_cache(tw_orders)

def load_business_cache():
    global business_desc_cache
    if os.path.exists(BUSINESS_CACHE_FILE):
        try:
            with open(BUSINESS_CACHE_FILE, "r", encoding="utf-8") as f:
                business_desc_cache = json.load(f)
        except Exception as e:
            print(f"Error loading business desc cache: {e}", flush=True)

def save_business_cache():
    try:
        with open(BUSINESS_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(business_desc_cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving business desc cache: {e}", flush=True)

load_business_cache()

def load_us_company_profiles():
    global us_company_profiles
    try:
        with open(US_COMPANY_PROFILES_FILE, "r", encoding="utf-8") as file:
            us_company_profiles = json.load(file)
    except Exception:
        us_company_profiles = {}

def save_us_company_profiles():
    os.makedirs(DATA_DIR, exist_ok=True)
    with us_company_profiles_lock:
        temp_file = f"{US_COMPANY_PROFILES_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(us_company_profiles, file, ensure_ascii=False, indent=2)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_file, US_COMPANY_PROFILES_FILE)

load_us_company_profiles()

US_SECTOR_BUSINESS_ZH = {
    "Technology": "科技產品、軟體、半導體或資訊基礎設施相關業務",
    "Communication Services": "通訊、網路平台、媒體與數位娛樂服務",
    "Financial Services": "銀行、支付、投資、保險與金融服務",
    "Consumer Cyclical": "汽車、電商、零售與非必需消費產品服務",
    "Consumer Defensive": "食品、飲料、民生用品與必需消費產品",
    "Energy": "石油、天然氣、能源開採、煉製與銷售",
    "Healthcare": "醫療保健、製藥、生技與醫療器材",
    "Industrials": "工業設備、航太、運輸與製造服務",
    "Basic Materials": "原物料、化學、金屬與礦業相關業務",
    "Real Estate": "不動產開發、經營與不動產投資信託",
    "Utilities": "電力、天然氣與公用事業服務",
}

US_SECTOR_ZH = {
    "Technology": "科技",
    "Communication Services": "通訊服務",
    "Financial Services": "金融服務",
    "Consumer Cyclical": "非必需消費",
    "Consumer Defensive": "民生消費",
    "Energy": "能源",
    "Healthcare": "醫療保健",
    "Industrials": "工業",
    "Basic Materials": "原物料",
    "Real Estate": "不動產",
    "Utilities": "公用事業",
}

CONCEPT_RULES = [
    ("AI", ("artificial intelligence", "ai ", "人工智慧", "gpu", "資料中心", "data center")),
    ("半導體", ("semiconductor", "半導體", "積體電路", "晶圓", "ic設計", "ic 設計")),
    ("雲端運算", ("cloud", "雲端", "伺服器", "server", "資料中心")),
    ("網路通訊", ("network", "網路", "通訊", "telecom", "wireless", "5g", "寬頻")),
    ("消費電子", ("consumer electronics", "消費電子", "智慧型手機", "手機", "筆記型電腦")),
    ("電子代工", ("筆記型電腦", "電腦系統設備", "電子產品之製造", "組裝及製造")),
    ("電動車", ("electric vehicle", "電動車", "ev ", "充電樁", "車用電子")),
    ("電子商務", ("e-commerce", "ecommerce", "電商", "線上零售")),
    ("金融科技", ("payment", "fintech", "支付", "信用卡", "數位金融")),
    ("影音串流", ("streaming", "串流", "數位娛樂", "影音", "媒體")),
    ("生技醫療", ("biotech", "pharmaceutical", "medical", "醫療", "製藥", "生技", "藥品")),
    ("綠能", ("renewable", "solar", "wind", "綠能", "太陽能", "風電", "儲能", "氫能")),
    ("電網建設", ("變壓器", "配電盤", "輸配電", "重電", "電力設備", "power grid")),
    ("能源", ("oil", "gas", "energy", "石油", "天然氣", "能源")),
    ("航太國防", ("aerospace", "defense", "航太", "航空器", "國防")),
    ("機器人", ("robot", "機器人", "自動化")),
    ("PCB", ("pcb", "印刷電路板", "電路板")),
    ("散熱", ("散熱", "cooling", "thermal")),
    ("面板", ("display", "顯示器", "面板", "液晶")),
    ("航運", ("shipping", "航運", "海運", "貨櫃")),
]

TW_CATEGORY_RULES = [
    ("半導體業", ("半導體", "積體電路", "晶圓", "ic設計", "ic 設計")),
    ("電腦及週邊", ("電腦", "伺服器", "主機板", "筆記型", "資料中心")),
    ("通信網路業", ("通訊", "網路", "電信", "寬頻", "天線")),
    ("光電業", ("光電", "顯示器", "面板", "led", "光學")),
    ("電子零組件", ("電子零組件", "連接器", "電路板", "pcb", "被動元件", "電感", "電容", "電阻")),
    ("電子通路業", ("電子產品之通路", "代理銷售", "電腦週邊產品之通路")),
    ("金融保險業", ("銀行", "金融", "保險", "證券", "期貨")),
    ("航運業", ("海運", "航運", "貨櫃", "船舶運送", "航空運輸")),
    ("生技醫療業", ("醫療", "製藥", "生技", "藥品", "醫療器材")),
    ("汽車工業", ("汽車", "車用", "機車及其零件")),
    ("電機機械", ("電機", "機械", "自動化設備", "工具機")),
    ("建材營造", ("建築", "營造", "建設", "不動產")),
    ("鋼鐵工業", ("鋼鐵", "線材", "螺絲", "金屬製品")),
    ("塑膠工業", ("塑膠", "聚氨基甲酸酯", "pet")),
    ("化學工業", ("化學", "化工", "化學品")),
    ("食品工業", ("食品", "飲料")),
    ("觀光餐旅", ("觀光", "旅館", "餐飲", "旅遊")),
]

GROUP_PROFILE_VERSION = 2
US_SYMBOL_CONCEPTS = {
    "AAPL": ["消費電子", "AI"],
    "NVDA": ["AI", "半導體", "資料中心"],
    "AMD": ["AI", "半導體", "資料中心"],
    "AVGO": ["AI", "半導體", "網路通訊"],
    "MSFT": ["AI", "雲端運算", "企業軟體"],
    "GOOG": ["AI", "雲端運算", "數位廣告"],
    "META": ["AI", "社群平台", "數位廣告"],
    "AMZN": ["電子商務", "雲端運算", "AI"],
    "TSLA": ["電動車", "儲能", "AI"],
    "NFLX": ["影音串流", "數位娛樂"],
    "JPM": ["金融科技", "銀行"],
    "V": ["金融科技", "支付"],
    "MA": ["金融科技", "支付"],
    "SPY": ["指數投資", "大型股"],
    "QQQ": ["指數投資", "科技股"],
    "DIA": ["指數投資", "大型股"],
    "IWM": ["指數投資", "小型股"],
}

def infer_concepts(*values):
    text = " ".join(str(value or "") for value in values).lower()
    concepts = [
        label for label, keywords in CONCEPT_RULES
        if any(keyword.lower() in text for keyword in keywords)
    ]
    return concepts[:3]

def infer_us_concepts(symbol, industry, name):
    preferred = US_SYMBOL_CONCEPTS.get(symbol, [])
    inferred = infer_concepts(industry, name)
    concepts = list(dict.fromkeys([*preferred, *inferred]))[:3]
    return concepts

def infer_tw_group(code, name, business_desc):
    text = f"{name or ''} {business_desc or ''}".lower()
    category = next(
        (label for label, keywords in TW_CATEGORY_RULES if any(keyword.lower() in text for keyword in keywords)),
        "其他類股",
    )
    concepts = infer_concepts(name, business_desc)
    if str(code).startswith("00"):
        category = "ETF"
        concepts = ["指數投資", *concepts]
    if not concepts:
        concepts = [category.replace("業", "") if category != "其他類股" else "個股題材"]
    return {"group_category": category, "concepts": list(dict.fromkeys(concepts))[:3]}

US_COMMON_NAMES_ZH = {
    **YAHOO_TW_US_INDICATORS,
    "SPY": "標普500指數ETF", "QQQ": "那斯達克100指數ETF",
    "DIA": "道瓊工業指數ETF", "IWM": "羅素2000指數ETF",
    "NOK": "諾基亞", "AAL": "美國航空", "SPCX": "SpaceX",
}

def ensure_us_company_profile(stock):
    symbol = str(stock.get("symbol") or stock.get("code") or "").upper()
    if not symbol:
        return {}
    cached = us_company_profiles.get(symbol)
    if (
        cached
        and cached.get("business_zh")
        and cached.get("group_category") is not None
        and cached.get("group_profile_version") == GROUP_PROFILE_VERSION
    ):
        return cached
    if cached and cached.get("business_zh"):
        cached["group_category"] = (
            "ETF"
            if str(stock.get("category", "")).endswith("ETF")
            else US_SECTOR_ZH.get(cached.get("sector", ""), cached.get("sector") or "其他板塊")
        )
        cached["concepts"] = infer_us_concepts(symbol, cached.get("industry"), stock.get("name"))
        if not cached["concepts"]:
            cached["concepts"] = [f"{cached['group_category']}概念"]
        cached["group_profile_version"] = GROUP_PROFILE_VERSION
        us_company_profiles[symbol] = cached
        save_us_company_profiles()
        return cached
    info = {}
    try:
        info = yf.Ticker(symbol).get_info()
    except Exception:
        pass
    name_zh = US_COMMON_NAMES_ZH.get(symbol)
    if not name_zh:
        candidate = str(stock.get("name") or "")
        name_zh = candidate if any(ord(char) > 127 for char in candidate) else candidate
    sector = info.get("sector") or (cached or {}).get("sector") or ""
    industry = info.get("industry") or (cached or {}).get("industry") or ""
    business_base = US_SECTOR_BUSINESS_ZH.get(sector, "美國上市公司之主要產品與服務")
    business_zh = f"{business_base}。產業分類：{industry or sector or '未分類'}。"
    profile = {
        "symbol": symbol,
        "name_zh": name_zh or symbol,
        "name_en": info.get("longName") or info.get("shortName") or stock.get("name") or symbol,
        "sector": sector,
        "industry": industry,
        "business_zh": business_zh,
        "group_category": "ETF" if str(stock.get("category", "")).endswith("ETF") else US_SECTOR_ZH.get(sector, sector or "其他板塊"),
        "concepts": infer_us_concepts(symbol, industry, stock.get("name")) or [
            f"{US_SECTOR_ZH.get(sector, sector or '其他板塊')}概念"
        ],
        "group_profile_version": GROUP_PROFILE_VERSION,
    }
    us_company_profiles[symbol] = profile
    save_us_company_profiles()
    return profile

disposition_cache = {}
DISPOSITIONS_SW_FILE = os.path.join(DATA_DIR, "dispositions_sw.json")

UNKNOWN_STOCK_NAME = "自訂股票"
SPECIAL_STOCK_NAMES = {
    "00981A": "主動統一台股增長",
    "00991A": "復華台灣未來50",
    "00403A": "主動統一台股升級50",
    "00402A": "主動安聯美國科技",
}
stock_name_lookup = {}
ADDED_BY_LABELS = {
    "manual": "手動加入",
    "text": "文字加入",
    "new_popular": "新增",
    "scan": "全市場掃描新增",
    "web": "網",
}

def is_bad_stock_name(name):
    if not name:
        return True
    text = str(name).strip()
    if not text:
        return True
    return "?" in text or "\ufffd" in text

def repair_mojibake(text):
    if not text:
        return ""
    value = str(text)
    mojibake_markers = ("Ã", "Â", "å", "æ", "ç", "è", "é", "ï", "ã", "ä", "º", "¿", "¤", "¥", "ª", "", "")
    # Some stored values were UTF-8 decoded as Latin-1 more than once
    # (for example "Ã¦Â..." -> "æ..." -> Chinese). Repair every valid layer.
    for _ in range(3):
        if not any(marker in value for marker in mojibake_markers):
            break
        try:
            repaired = value.encode("latin1").decode("utf-8")
            if repaired == value:
                break
            value = repaired
        except Exception:
            break
    return value

def clean_stock_name(name):
    if not name:
        return UNKNOWN_STOCK_NAME
    text = repair_mojibake(name).strip()
    if not text:
        return UNKNOWN_STOCK_NAME
    if "?" in text or "\ufffd" in text:
        prefix = re.split(r"\s*[\(（]", text, maxsplit=1)[0].strip()
        if prefix and "?" not in prefix and "\ufffd" not in prefix:
            return prefix
        return UNKNOWN_STOCK_NAME
    return text

def load_stock_name_lookup():
    global stock_name_lookup
    if stock_name_lookup:
        return stock_name_lookup
    try:
        with open(ALL_STOCKS_FILE, "r", encoding="utf-8") as file:
            items = json.load(file)
        stock_name_lookup = {
            str(item.get("code", "")).strip().upper(): clean_stock_name(item.get("name"))
            for item in items
            if item.get("code")
        }
    except Exception as error:
        print(f"Unable to load stock name lookup: {error}", flush=True)
        stock_name_lookup = {}
    return stock_name_lookup

def resolve_stock_name(code, current_name=None):
    normalized_code = str(code or "").strip().upper()
    if normalized_code in SPECIAL_STOCK_NAMES:
        return SPECIAL_STOCK_NAMES[normalized_code]
    cleaned = clean_stock_name(current_name)
    if cleaned != UNKNOWN_STOCK_NAME:
        return cleaned

    resolved = load_stock_name_lookup().get(normalized_code, UNKNOWN_STOCK_NAME)
    return resolved if resolved != UNKNOWN_STOCK_NAME else cleaned

def fetch_disposition_stocks():
    global disposition_cache
    
    # 1. Load from local cache first if exists
    cached_data = None
    if os.path.exists(DISPOSITIONS_SW_FILE):
        try:
            with open(DISPOSITIONS_SW_FILE, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
                print("Successfully loaded StockWarden disposition cache from disk.", flush=True)
        except Exception as e:
            print(f"Error loading StockWarden cache from disk: {e}", flush=True)
            
    # 2. Fetch fresh data from StockWarden GCS JSON
    try:
        print("Fetching fresh disposition data from StockWarden GCS...", flush=True)
        r = requests.get("https://storage.googleapis.com/stockwarden-prod-public/api/dispositions.json", timeout=15)
        if r.status_code == 200:
            fresh_data = r.json()
            # Save to disk cache
            os.makedirs(os.path.dirname(DISPOSITIONS_SW_FILE), exist_ok=True)
            with open(DISPOSITIONS_SW_FILE, "w", encoding="utf-8") as f:
                json.dump(fresh_data, f, ensure_ascii=False, indent=2)
            cached_data = fresh_data
            print("Successfully updated and cached StockWarden dispositions.", flush=True)
    except Exception as e:
        print(f"Error downloading StockWarden dispositions: {e}", flush=True)
        
    if not cached_data:
        disposition_cache = {}
        return
        
    # Process the cached_data into a dictionary for quick lookup of currently active dispositions
    import datetime
    tz_offset = datetime.timezone(datetime.timedelta(hours=8))
    today_tw = datetime.datetime.now(tz_offset).date()
    
    def parse_minguo_date(date_str):
        if not date_str:
            return None
        try:
            clean_str = date_str.replace("-", "/").replace("~", "/").replace(".", "/")
            parts = clean_str.split("/")
            if len(parts) == 3:
                year = int(parts[0]) + 1911
                month = int(parts[1])
                day = int(parts[2])
                return datetime.date(year, month, day)
        except Exception:
            pass
        return None
        
    def extract_disposition_fields(detail_text):
        if not detail_text:
            return "", "", ""
        return detail_text.strip(), "", ""

    active_cache = {}
    raw_data_dict = cached_data.get("data", {})
    for code, history in raw_data_dict.items():
        for date_key, disp in history.items():
            start = parse_minguo_date(disp.get("k"))
            end = parse_minguo_date(disp.get("f"))
            if start and end and start <= today_tw <= end:
                reason, _, _ = extract_disposition_fields(disp.get("e", ""))
                if not reason:
                    reason = disp.get("i", "")
                
                reason = reason.strip().lstrip("0123456789.、)）-：: ")
                while reason and reason[-1].isdigit():
                    reason = reason[:-1].rstrip()
                
                # Format period as YYMMDD-YYMMDD
                start_fmt = start.strftime("%y%m%d")
                end_fmt = end.strftime("%y%m%d")
                period = f"{start_fmt}-{end_fmt}"
                
                # Format measures as "蝝???桀?" using g interval, default to 5
                g_val = disp.get("g") or 5
                measures = f"{g_val}分"
                
                active_cache[code] = {
                    "market": disp.get("j", "TWSE"),
                    "period": period,
                    "measures": measures,
                    "reason": reason
                }
                break
                
    disposition_cache = active_cache
    print(f"Successfully processed {len(disposition_cache)} currently active disposition stocks from StockWarden.", flush=True)

# Fetch once on startup
try:
    fetch_disposition_stocks()
except Exception as e:
    print(f"Initial fetch of disposition stocks failed: {e}", flush=True)

def get_yahoo_tw_business_desc(symbol_or_code: str) -> str:
    code = symbol_or_code.split('.')[0].strip()
    if not code:
        return ""
    
    if code in business_desc_cache:
        return business_desc_cache[code]
        
    # Skip ETFs as they do not have business descriptions on Yahoo profile pages
    is_etf = code.startswith("00") or code.startswith("01") or len(code) >= 5
    if is_etf:
        business_desc_cache[code] = ""
        save_business_cache()
        return ""
        
    symbol = symbol_or_code
    if "." not in symbol:
        symbol = f"{code}.TW"
        
    # Query only the correct exchange to avoid duplicate or invalid requests
    if symbol.endswith(".TW"):
        urls = [f"https://tw.stock.yahoo.com/quote/{code}.TW/profile"]
    elif symbol.endswith(".TWO"):
        urls = [f"https://tw.stock.yahoo.com/quote/{code}.TWO/profile"]
    else:
        urls = [
            f"https://tw.stock.yahoo.com/quote/{code}.TW/profile",
            f"https://tw.stock.yahoo.com/quote/{code}.TWO/profile"
        ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
    }
    
    desc = ""
    for url in urls:
        try:
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                r.encoding = 'utf-8'
                soup = BeautifulSoup(r.text, 'html.parser')
                elem = soup.find(string=lambda x: x and '銝餉?蝬?璆剖?' in x)
                if elem:
                    p = elem.find_parent('div')
                    sibling_div = p.find('div') if p else None
                    if sibling_div:
                        desc = sibling_div.text.strip().replace('\n', '').replace('\r', '')
                        if desc:
                            break
        except Exception as e:
            print(f"Scraper error for {url}: {e}", flush=True)
            
    # Always cache the description (even if empty) to prevent repeated scraping attempts
    business_desc_cache[code] = desc
    save_business_cache()
        
    return desc

# Global state for scanner
us_market_scan_progress = 0
us_market_scan_total = 0
us_market_scan_active = False
potential_us_stocks = []
all_market_scan_progress = 0
all_market_scan_total = 0
all_market_scan_active = False
potential_stocks = []
monitor_signal_cache = {"updated_at": 0.0, "codes": "", "data": {}}

class StockItem(BaseModel):
    code: str
    symbol: str
    name: str
    added_by: Optional[str] = "popular"

class AddStockRequest(BaseModel):
    code: str
    added_by: Optional[str] = "manual"

class BulkAddRequest(BaseModel):
    codes: List[str]

class SaveListsRequest(BaseModel):
    stockList: List[dict] = []
    monitorList: List[dict] = []
    trailingList: List[dict] = []

class SinoPacSetupRequest(BaseModel):
    api_key: str
    secret_key: str
    person_id: Optional[str] = ""
    ca_path: Optional[str] = ""
    ca_password: Optional[str] = ""
    enabled: Optional[bool] = True

class PlaceOrderRequest(BaseModel):
    code: str
    action: str
    price: float
    quantity: int
    stop_loss_price: Optional[float] = None
    stop_profit_price: Optional[float] = None
    lot_type: Optional[str] = "ODD" # ODD or ROUND
    dry_run: Optional[bool] = True
    market: Optional[str] = "TW"

class UpdateOrderRequest(BaseModel):
    buy_price: Optional[float] = None
    quantity: Optional[int] = None
    stop_loss_price: Optional[float] = None
    stop_profit_price: Optional[float] = None


class ToggleOrderActionRequest(BaseModel):
    action: str

class MoveToTrailingRequest(BaseModel):
    stop_loss_price: float
    stop_profit_price: float
    trailing_reference: float

# Helper to convert nan / inf to None recursively for JSON compliance
def clean_nan(obj):
    if isinstance(obj, dict):
        return {k: clean_nan(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_nan(x) for x in obj]
    elif isinstance(obj, float):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return obj
    elif isinstance(obj, np.floating):
        val = float(obj)
        if np.isnan(val) or np.isinf(val):
            return None
        return val
    elif isinstance(obj, np.integer):
        return int(obj)
    elif pd.isna(obj):
        return None
    return obj

# Helper functions for calculations
def calculate_kd(df, n=60, m1=3, m2=3):
    df = df.copy()
    low_n = df['Low'].rolling(window=n).min()
    high_n = df['High'].rolling(window=n).max()
    
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50.0)
    
    k_list = []
    d_list = []
    k_val = 50.0
    d_val = 50.0
    
    factor_k = 1.0 / m1
    factor_d = 1.0 / m2
    
    for r in rsv:
        k_val = (1.0 - factor_k) * k_val + factor_k * r
        d_val = (1.0 - factor_d) * d_val + factor_d * k_val
        k_list.append(k_val)
        d_list.append(d_val)
        
    df['K'] = k_list
    df['D'] = d_list
    return df

# Local minima calculation (Higher Lows)
def find_local_minima(arr, order=5):
    minima_indices = []
    n = len(arr)
    for i in range(order, n - order):
        is_min = True
        for j in range(i - order, i + order + 1):
            if j == i:
                continue
            if arr[j] <= arr[i]:
                is_min = False
                break
        if is_min:
            minima_indices.append(i)
    return minima_indices

def normalize_unreported_split(df, code=None):
    """Repair suspicious TW Yahoo discontinuities with official TWSE daily data."""
    if df is None or df.empty or len(df) < 2 or not code or not str(code).isdigit():
        return df, []
    import math
    event_index = None
    suspected_factor = None
    for index in range(1, len(df)):
        previous_close = float(df["Close"].iloc[index - 1])
        current_open = float(df["Open"].iloc[index])
        if math.isnan(previous_close) or math.isnan(current_open) or previous_close <= 0 or current_open <= 0:
            continue
        ratio = previous_close / current_open
        factor = round(ratio)
        if 2 <= factor <= 10 and abs(ratio - factor) / factor <= 0.08:
            event_index, suspected_factor = index, factor
            break
    if event_index is None:
        return df, []

    official_rows = {}
    start = df.index[0].date()
    end = df.index[-1].date()
    cursor = datetime.date(start.year, start.month, 1)
    while cursor <= end:
        try:
            payload = requests.get(
                "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
                params={"date": cursor.strftime("%Y%m01"), "stockNo": str(code), "response": "json"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            ).json()
            for row in payload.get("data", []):
                year, month, day = map(int, row[0].split("/"))
                date_value = datetime.date(year + 1911, month, day)
                official_rows[date_value] = {
                    "Volume": float(row[1].replace(",", "")),
                    "Open": float(row[3].replace(",", "")),
                    "High": float(row[4].replace(",", "")),
                    "Low": float(row[5].replace(",", "")),
                    "Close": float(row[6].replace(",", "")),
                }
        except Exception as error:
            print(f"TWSE official history repair failed for {code} {cursor}: {error}", flush=True)
        cursor = datetime.date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1)

    if not official_rows:
        # Do not guess a split without official confirmation.
        return df, []
    repaired = df.copy()
    for column in ("Open", "High", "Low", "Close", "Adj Close", "Volume"):
        if column in repaired:
            repaired[column] = pd.to_numeric(repaired[column], errors="coerce").astype(float)
    for index_value in repaired.index:
        official = official_rows.get(index_value.date())
        if official:
            for column, value in official.items():
                repaired.at[index_value, column] = value
    event_time = repaired.index[event_index]
    yahoo_close = float(df["Close"].iloc[-1])
    official_close = official_rows.get(df.index[-1].date(), {}).get("Close")
    correction_factor = (official_close / yahoo_close) if official_close and yahoo_close else suspected_factor
    return repaired, [{"date": event_time, "factor": correction_factor}]

def fetch_twse_daily_history(code, months=12):
    """Fetch official TWSE OHLCV data, including symbols Yahoo does not support."""
    rows = {}
    today = datetime.date.today()
    cursor = datetime.date(today.year, today.month, 1)
    for _ in range(months):
        try:
            payload = requests.get(
                "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY",
                params={"date": cursor.strftime("%Y%m01"), "stockNo": str(code), "response": "json"},
                headers={"User-Agent": "Mozilla/5.0"},
                timeout=15,
            ).json()
            for row in payload.get("data", []):
                year, month, day = map(int, row[0].split("/"))
                date_value = datetime.datetime(year + 1911, month, day)
                rows[date_value] = {
                    "Open": float(row[3].replace(",", "")),
                    "High": float(row[4].replace(",", "")),
                    "Low": float(row[5].replace(",", "")),
                    "Close": float(row[6].replace(",", "")),
                    "Volume": float(row[1].replace(",", "")),
                }
        except Exception as error:
            print(f"TWSE official history fetch failed for {code} {cursor}: {error}", flush=True)
        cursor = datetime.date(cursor.year - (cursor.month == 1), 12 if cursor.month == 1 else cursor.month - 1, 1)
    if not rows:
        return pd.DataFrame(columns=["Open", "High", "Low", "Close", "Volume"])
    frame = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    frame.index = pd.DatetimeIndex(frame.index).tz_localize("Asia/Taipei")
    return frame

def ensure_tw_daily_history(df, code, months=12):
    if df is not None and not df.empty:
        return df
    if not code or not str(code)[0].isdigit():
        return df
    return fetch_twse_daily_history(code, months)

def apply_split_events(df, events):
    if df is None or df.empty or not events:
        return df
    normalized = df.copy()
    if "Volume" in normalized:
        normalized["Volume"] = normalized["Volume"].astype(float)
    for event in events:
        event_time = event["date"]
        factor = event["factor"]
        if getattr(event_time, "tzinfo", None) is not None and getattr(normalized.index, "tz", None) is not None:
            event_time = event_time.tz_convert(normalized.index.tz)
        price_columns = [column for column in ("Open", "High", "Low", "Close", "Adj Close") if column in normalized]
        normalized.loc[normalized.index >= event_time, price_columns] = (
            normalized.loc[normalized.index >= event_time, price_columns] * factor
        )
        if "Volume" in normalized:
            normalized.loc[normalized.index >= event_time, "Volume"] = (
                normalized.loc[normalized.index >= event_time, "Volume"] / factor
            )
    return normalized

def validate_hourly_against_daily(df_hourly, df_daily):
    """Drop hourly bars that are clearly outside that day's official range."""
    if df_hourly is None or df_hourly.empty or df_daily is None or df_daily.empty:
        return df_hourly
    daily_ranges = {
        index.date(): (float(row["Low"]), float(row["High"]))
        for index, row in df_daily.iterrows()
    }
    valid = []
    for index, row in df_hourly.iterrows():
        day_range = daily_ranges.get(index.date())
        if not day_range:
            valid.append(True)
            continue
        daily_low, daily_high = day_range
        bar_low, bar_high = float(row["Low"]), float(row["High"])
        tolerance = max(daily_high * 0.03, 1.0)
        valid.append(bar_low >= daily_low - tolerance and bar_high <= daily_high + tolerance)
    return df_hourly.loc[valid]

def calculate_higher_low_breakout(df):
    result = {"morph_ok": False, "morph_breakout": False, "neckline": None}
    if df is None or len(df) < 12:
        return result
    minima = find_local_minima(df["Low"].values, order=5)
    if len(minima) < 2:
        return result
    previous_index, latest_index = minima[-2], minima[-1]
    if float(df["Low"].iloc[latest_index]) <= float(df["Low"].iloc[previous_index]):
        return result
    result["morph_ok"] = True
    neckline = float(df["Close"].iloc[previous_index:latest_index + 1].max())
    result["neckline"] = round(neckline, 2)
    # A breakout must actually cross the neckline within the latest two
    # sessions. Merely remaining far above an old neckline is not a breakout.
    breakout_index = None
    start_index = max(latest_index + 1, len(df) - 2)
    for index in range(start_index, len(df)):
        previous_close = float(df["Close"].iloc[index - 1])
        breakout_close = float(df["Close"].iloc[index])
        if previous_close <= neckline and breakout_close > neckline:
            breakout_index = index
            break
    if breakout_index is not None:
        volume_start = max(0, breakout_index - 20)
        prior_volumes = df["Volume"].iloc[volume_start:breakout_index]
        average_volume = float(prior_volumes.mean()) if len(prior_volumes) else 0
        breakout_volume = float(df["Volume"].iloc[breakout_index])
        volume_confirmed = average_volume > 0 and breakout_volume >= average_volume * 1.2
        held_above = all(
            float(value) > neckline
            for value in df["Close"].iloc[breakout_index:]
        )
        result["morph_breakout"] = volume_confirmed and held_above
    return result

# Calculate 5 strategy lights/signals
def calculate_strategy_signals(df_daily):
    if df_daily.empty or len(df_daily) < 20:
        return {
            "vol_breakout": False,
            "undervalued": False,
            "breakout_5ma": False,
            "momentum": False,
            "mean_reversion": False
        }
        
    df = df_daily.copy()
    
    # Calculate MAs
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['MA60'] = df['Close'].rolling(window=60).mean()
    
    # Calculate Vol MA20
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    
    # Latest data points
    close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2]) if len(df) >= 2 else close
    volume = float(df['Volume'].iloc[-1])
    vol_ma20 = float(df['Vol_MA20'].iloc[-1]) if not pd.isna(df['Vol_MA20'].iloc[-1]) else 1.0
    
    # 1. 撣園?蝒 (Volume Breakout)
    vol_breakout = (close > prev_close) and (volume > 1.5 * vol_ma20)
    
    # 2. ?孵潔?隡?(Value Undervalued)
    # Check if close is in the lower 30% of its last 120 days high/low range
    n_days = min(len(df), 120)
    recent_low = float(df['Low'].tail(n_days).min())
    recent_high = float(df['High'].tail(n_days).max())
    range_span = recent_high - recent_low
    undervalued = False
    if range_span > 0:
        undervalued = close < (recent_low + 0.3 * range_span)
        
    # 3. ?游?擃?蝛?5 ?亙?蝺?(Breakout Prev High & Stand on 5MA)
    # Check if close is higher than the max close of the previous 20 days, and close > MA5
    ma5 = float(df['MA5'].iloc[-1]) if not pd.isna(df['MA5'].iloc[-1]) else close
    prev_high_20 = float(df['High'].iloc[-21:-1].max()) if len(df) >= 21 else float(df['High'].iloc[:-1].max()) if len(df) > 1 else close
    breakout_5ma = (close > prev_high_20) and (close > ma5)
    
    # 4. ?? (Momentum Trend-following)
    ma10 = float(df['MA10'].iloc[-1]) if not pd.isna(df['MA10'].iloc[-1]) else close
    ma20 = float(df['MA20'].iloc[-1]) if not pd.isna(df['MA20'].iloc[-1]) else close
    momentum = (close > ma5) and (ma5 > ma10) and (ma10 > ma20)
    
    # 5. ?澆?甇?(Mean Reversion)
    # Check if Close is below MA20 by more than 5% and today close > prev close (oversold rebound)
    mean_reversion = (close < ma20 * 0.95) and (close > prev_close)
    
    return {
        "vol_breakout": bool(vol_breakout),
        "undervalued": bool(undervalued),
        "breakout_5ma": bool(breakout_5ma),
        "momentum": bool(momentum),
        "mean_reversion": bool(mean_reversion)
    }

# Fetch all TW common stocks
def fetch_all_tw_stocks():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }
    
    stocks = []
    # 1. Fetch TSE (銝?)
    try:
        url_tse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        res = requests.get(url_tse, headers=headers, timeout=10)
        html_content = res.content.decode('cp950', errors='ignore')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table = soup.find("table", class_="h4")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 6:
                    val = tds[0].get_text().strip()
                    parts = val.split('\u3000')
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        market = tds[3].get_text().strip()
                        cfi = tds[5].get_text().strip()
                        
                        if re.match(r'^\d{4}$', code) and market == "銝?" and cfi.startswith("ES"):
                            stocks.append({
                                "code": code,
                                "name": name,
                                "symbol": f"{code}.TW",
                                "market": "TSE"
                            })
    except Exception as e:
        print(f"Main API: Error fetching TSE stock list: {e}")
        
    # 2. Fetch OTC (銝?)
    try:
        url_otc = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        res = requests.get(url_otc, headers=headers, timeout=10)
        html_content = res.content.decode('cp950', errors='ignore')
        soup = BeautifulSoup(html_content, 'html.parser')
        
        table = soup.find("table", class_="h4")
        if table:
            rows = table.find_all("tr")
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 6:
                    val = tds[0].get_text().strip()
                    parts = val.split('\u3000')
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        market = tds[3].get_text().strip()
                        cfi = tds[5].get_text().strip()
                        
                        if re.match(r'^\d{4}$', code) and market == "銝?" and cfi.startswith("ES"):
                            stocks.append({
                                "code": code,
                                "name": name,
                                "symbol": f"{code}.TWO",
                                "market": "OTC"
                            })
    except Exception as e:
        print(f"Main API: Error fetching OTC stock list: {e}")
        
    return stocks

def format_stock_name(stock):
    name = clean_stock_name(stock.get("name"))
    added_by = stock.get("added_by", "popular")
    if stock.get("market") == "US":
        if added_by == "web":
            if " (網)" not in name and "(網)" not in name:
                return f"{name} (網)"
        return name
    label = ADDED_BY_LABELS.get(added_by)
    if label and f"({label})" not in name and f" ({label})" not in name:
        return f"{name} ({label})"
    return name

def analyze_single_stock(stock):
    symbol = stock["symbol"]
    code = stock["code"]
    name = format_stock_name(stock)
    is_us = stock.get("market") == "US" or not re.match(r"^\d", str(code))
    
    import datetime
    tz_offset = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_offset)
    if is_us:
        from zoneinfo import ZoneInfo
        now_market = datetime.datetime.now(ZoneInfo("America/New_York"))
        clock_intraday = now_market.weekday() < 5 and (datetime.time(9, 30) <= now_market.time() <= datetime.time(16, 0))
        market_date = now_market.date()
    else:
        clock_intraday = now_tw.weekday() < 5 and (datetime.time(9, 0) <= now_tw.time() <= datetime.time(13, 35))
        market_date = now_tw.date()
    is_intraday = False
    
    try:
        ticker = yf.Ticker(symbol)
        
        # Fetch industry/sector (best-effort, won't block analysis if fails)
        industry = ""
        company_profile = {}
        try:
            if is_us:
                company_profile = ensure_us_company_profile(stock)
                industry = company_profile.get("business_zh", "")
                name = company_profile.get("name_en") or name
            else:
                industry = get_yahoo_tw_business_desc(symbol)
        except Exception:
            pass
        group_info = (
            {
                "group_category": company_profile.get("group_category", "其他板塊"),
                "concepts": company_profile.get("concepts", []),
            }
            if is_us else infer_tw_group(code, name, industry)
        )
        
        # 1. Fetch Daily Data
        df_daily = ticker.history(period="1y", interval="1d")
        if not is_us:
            df_daily = ensure_tw_daily_history(df_daily, code, 12)
        df_daily, split_events = normalize_unreported_split(df_daily, code if not is_us else None)
        df_daily = df_daily[df_daily["Volume"] > 0]
        df_daily = df_daily.dropna(subset=["Open", "High", "Low", "Close"])
        has_today_data = not df_daily.empty and df_daily.index[-1].date() == market_date
        is_intraday = clock_intraday and has_today_data
        live_close = float(df_daily["Close"].iloc[-1]) if not df_daily.empty else None
        live_volume = float(df_daily["Volume"].iloc[-1]) if not df_daily.empty else 0
        if is_intraday and not df_daily.empty and df_daily.index[-1].date() == market_date:
            df_daily = df_daily.iloc[:-1]
        if df_daily.empty or len(df_daily) < 60:
            ref_price = None
            price_change = None
            price_change_percent = 0.0
            if not df_daily.empty:
                last_date_str = df_daily.index[-1].strftime("%Y-%m-%d")
                if last_date_str == market_date:
                    ref_price = float(df_daily['Close'].iloc[-2]) if len(df_daily) >= 2 else float(df_daily['Close'].iloc[-1])
                else:
                    ref_price = float(df_daily['Close'].iloc[-1])
                if ref_price is not None and live_close is not None:
                    ref_price = round(ref_price, 2)
                    price_change = round(live_close - ref_price, 2)
                    price_change_percent = round((price_change / ref_price) * 100, 2) if ref_price else 0.0

            return clean_nan({
                "code": code,
                "symbol": symbol,
                "name": name,
                "market": "US" if is_us else "TW",
                "category": stock.get("category", ""),
                "group_category": group_info.get("group_category", ""),
                "concepts": group_info.get("concepts", []),
                "current_price": live_close,
                "reference_price": ref_price,
                "price_change": price_change,
                "price_change_percent": price_change_percent,
                "volume_lots": int(live_volume // 1000),
                "daily_trend_ok": None, "hourly_kd_ok": None, "golden_cross_count": None,
                "morph_ok": False, "morph_breakout": False, "system_a_signal": False,
                "r_value": None, "signals": None, "insufficient_history": True, "error": None
            })
            
        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
        df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
        
        analysis_close = float(df_daily['Close'].iloc[-1])
        latest_close = live_close if is_intraday and live_close is not None else analysis_close
        latest_ma20 = float(df_daily['MA20'].iloc[-1])
        latest_ma60 = float(df_daily['MA60'].iloc[-1])
        
        # Daily trend condition
        daily_trend_ok = analysis_close > latest_ma20 and analysis_close > latest_ma60 and latest_ma20 > latest_ma60
        prev_high = float(df_daily['High'].tail(60).max())
        
        # 5 technical strategy lights
        signals = calculate_strategy_signals(df_daily)
        
        # Calculate reference price and price change
        reference_price = None
        if not df_daily.empty:
            last_date_str = df_daily.index[-1].strftime("%Y-%m-%d")
            if last_date_str == market_date:
                reference_price = float(df_daily['Close'].iloc[-2]) if len(df_daily) >= 2 else float(df_daily['Close'].iloc[-1])
            else:
                reference_price = float(df_daily['Close'].iloc[-1])
        reference_price = round(reference_price, 2) if reference_price is not None else latest_close
        price_change = round(latest_close - reference_price, 2)
        price_change_percent = round((price_change / reference_price) * 100, 2) if reference_price else 0.0
        
        disposition_info = disposition_cache.get(code, None)
        
        # 2. Fetch Hourly Data
        df_hourly = ticker.history(period="2mo", interval="60m")
        if not is_us:
            df_hourly = validate_hourly_against_daily(df_hourly, df_daily)
        df_hourly = df_hourly.dropna(subset=["High", "Low", "Close"])
        if is_intraday and not df_hourly.empty:
            df_hourly = df_hourly[df_hourly.index.date < market_date]
        hourly_available = not df_hourly.empty and len(df_hourly) >= 20
        latest_k = latest_d = None
        golden_cross_count = None
        hourly_kd_ok = None
        kd_under_50 = None
        if hourly_available:
            df_hourly = calculate_kd(df_hourly)
            latest_k = float(df_hourly['K'].iloc[-1])
            latest_d = float(df_hourly['D'].iloc[-1])
        
        # KD under 50 condition
            kd_under_50 = latest_k < 50 and latest_d < 50
        
        # Count golden crosses < 40 in last 60 hourly bars
            recent_hourly = df_hourly.tail(60)
            crosses = []
            for i in range(1, len(recent_hourly)):
                if recent_hourly['K'].iloc[i-1] <= recent_hourly['D'].iloc[i-1] and recent_hourly['K'].iloc[i] > recent_hourly['D'].iloc[i] and recent_hourly['K'].iloc[i] < 40:
                    crosses.append(float(recent_hourly['K'].iloc[i]))
            golden_cross_count = len(crosses)
            hourly_kd_ok = 2 <= golden_cross_count <= 3
        
        # Daily volume lots
        volume = live_volume if is_intraday else float(df_daily['Volume'].iloc[-1])
        volume_lots = int(volume // 1000)
        
        # Morphological: Higher Lows (摨?擃?
        morph = calculate_higher_low_breakout(df_daily)

        # System A signal
        system_a_signal = bool(daily_trend_ok and kd_under_50 and hourly_kd_ok)
        
        # Position risk parameters
        stop_loss_price = round(latest_close * 0.95, 2)
        r_value = 0.0
        risk = latest_close - stop_loss_price
        if risk > 0:
            r_value = round((prev_high - latest_close) / risk, 2)
            
        # 5 technical strategy lights
        signals = calculate_strategy_signals(df_daily)
        
        disposition_info = disposition_cache.get(code, None)
            
        return clean_nan({
            "code": code,
            "symbol": symbol,
            "name": name,
            "added_by": stock.get("added_by", "popular"),
            "market": "US" if is_us else "TW",
            "category": stock.get("category", ""),
            "industry": industry,
            "name_zh": company_profile.get("name_zh", "") if is_us else "",
            "business_zh": company_profile.get("business_zh", "") if is_us else "",
            "group_category": group_info.get("group_category", ""),
            "concepts": group_info.get("concepts", []),
            "current_price": round(latest_close, 2),
            "reference_price": reference_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "volume_lots": volume_lots,
            "daily_ma20": round(latest_ma20, 2),
            "daily_ma60": round(latest_ma60, 2),
            "daily_trend_ok": daily_trend_ok,
            "latest_k": round(latest_k, 2) if latest_k is not None else None,
            "latest_d": round(latest_d, 2) if latest_d is not None else None,
            "kd_under_50": kd_under_50,
            "golden_cross_count": golden_cross_count,
            "hourly_kd_ok": hourly_kd_ok,
            **morph,
            "system_a_signal": system_a_signal,
            "prev_high": round(prev_high, 2),
            "stop_loss_price": stop_loss_price,
            "r_value": r_value,
            "signals": signals,
            "disposition": disposition_info,
            "is_intraday": is_intraday,
            "error": None
        })
    except Exception as e:
        return clean_nan({
            "code": code,
            "symbol": symbol,
            "name": name,
            "market": "US" if is_us else "TW",
            "category": stock.get("category", ""),
            "is_intraday": is_intraday,
            "error": f"???航炊: {str(e)}",
            "system_a_signal": False
        })

# Read/Write helpers

# Read/Write helpers
LISTS_DIR = DATA_DIR
LISTS_FILE = os.path.join(LISTS_DIR, "lists.json")

def init_lists_file():
    if not os.path.exists(LISTS_DIR):
        os.makedirs(LISTS_DIR, exist_ok=True)
    if not os.path.exists(LISTS_FILE):
        defaults = [
            {"symbol": "2330.TW", "code": "2330", "name": "台積電", "added_by": "popular"},
            {"symbol": "2317.TW", "code": "2317", "name": "鴻海", "added_by": "popular"},
            {"symbol": "2454.TW", "code": "2454", "name": "聯發科", "added_by": "popular"},
            {"symbol": "2382.TW", "code": "2382", "name": "廣達", "added_by": "popular"},
            {"symbol": "3231.TW", "code": "3231", "name": "緯創", "added_by": "popular"},
            {"symbol": "2308.TW", "code": "2308", "name": "台達電", "added_by": "popular"},
            {"symbol": "2603.TW", "code": "2603", "name": "長榮", "added_by": "popular"},
            {"symbol": "2881.TW", "code": "2881", "name": "富邦金", "added_by": "popular"},
            {"symbol": "2882.TW", "code": "2882", "name": "國泰金", "added_by": "popular"},
            {"symbol": "2303.TW", "code": "2303", "name": "聯電", "added_by": "popular"}
        ]
        with open(LISTS_FILE, "w", encoding="utf-8") as f:
            json.dump({"stockList": defaults, "monitorList": []}, f, ensure_ascii=False, indent=2)

init_lists_file()

def read_stock_list():
    init_lists_file()
    try:
        with open(LISTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            stocks = data.get("stockList", [])
            changed = False
            for s in stocks:
                if "added_by" not in s:
                    s["added_by"] = "popular"
                    changed = True
                resolved_name = resolve_stock_name(s.get("code"), s.get("name"))
                if resolved_name != s.get("name"):
                    s["name"] = resolved_name
                    changed = True
            if changed:
                data["stockList"] = stocks
                with open(LISTS_FILE, "w", encoding="utf-8") as output:
                    json.dump(data, output, ensure_ascii=False, indent=2)
            return stocks
    except Exception:
        return []

def write_stock_list(stocks):
    init_lists_file()
    try:
        existing = {"stockList": [], "monitorList": []}
        if os.path.exists(LISTS_FILE):
            try:
                with open(LISTS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            except Exception:
                pass
        existing["stockList"] = stocks
        with open(LISTS_FILE, "w", encoding="utf-8") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        if os.path.exists(TW_ANALYSIS_CACHE_FILE):
            try:
                with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                    cached = json.load(file)
                if isinstance(cached, list):
                    active_codes = {str(s["code"]).upper() for s in stocks}
                    filtered_cache = [row for row in cached if str(row.get("code", "")).upper() in active_codes]
                    with open(TW_ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as file:
                        json.dump(filtered_cache, file, ensure_ascii=False)
            except Exception as e:
                print(f"Error updating TW analysis cache: {e}", flush=True)
                try:
                    os.remove(TW_ANALYSIS_CACHE_FILE)
                except Exception:
                    pass
        return True
    except Exception:
        return False

def read_us_stock_list():
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(US_STOCKS_FILE):
        write_us_stock_list(DEFAULT_US_STOCKS)
    try:
        with open(US_STOCKS_FILE, "r", encoding="utf-8") as file:
            stocks = json.load(file)
        return stocks if stocks else list(DEFAULT_US_STOCKS)
    except Exception as error:
        print(f"Unable to load US stock list: {error}", flush=True)
        return list(DEFAULT_US_STOCKS)

def write_us_stock_list(stocks):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(US_STOCKS_FILE, "w", encoding="utf-8") as file:
        json.dump(stocks, file, ensure_ascii=False, indent=2)
    if os.path.exists(US_ANALYSIS_CACHE_FILE):
        try:
            with open(US_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cached = json.load(file)
            if isinstance(cached, list):
                active_codes = {str(s["code"]).upper() for s in stocks}
                filtered_cache = [row for row in cached if str(row.get("code", "")).upper() in active_codes]
                with open(US_ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as file:
                    json.dump(filtered_cache, file, ensure_ascii=False)
        except Exception as e:
            print(f"Error updating US analysis cache: {e}", flush=True)
            try:
                os.remove(US_ANALYSIS_CACHE_FILE)
            except Exception:
                pass

def read_analysis_cache(path, market_type="TW"):
    try:
        if not os.path.exists(path):
            return None
            
        if market_type == "TW":
            market_open = is_tw_market_open()
        else:
            market_open = is_us_market_open()
            
        mtime = os.path.getmtime(path)
        
        if market_open:
            # During trading, cache expires in 15 minutes
            if time.time() - mtime > ANALYSIS_CACHE_TTL_SECONDS:
                return None
        else:
            # Outside trading hours, check if cache was written after the most recent market close
            last_close = get_last_market_close(market_type)
            if mtime < last_close.timestamp():
                return None
                
        with open(path, "r", encoding="utf-8") as file:
            cached = json.load(file)
        return cached if isinstance(cached, list) else None
    except Exception:
        return None

def write_analysis_cache(path, rows):
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(rows, file, ensure_ascii=False)
        os.replace(temp_path, path)
    except Exception as error:
        print(f"Unable to save analysis cache {path}: {error}", flush=True)

# Potential Stocks Loader & background scanner
def load_potential_stocks():
    global potential_stocks
    if os.path.exists(POTENTIAL_STOCKS_FILE):
        try:
            with open(POTENTIAL_STOCKS_FILE, "r", encoding="utf-8") as f:
                potential_stocks = json.load(f)
                for item in potential_stocks:
                    item["name"] = resolve_stock_name(item.get("code"), item.get("name"))
                    group_info = infer_tw_group(item.get("code"), item.get("name"), item.get("industry"))
                    item["group_category"] = group_info["group_category"]
                    item["concepts"] = group_info["concepts"]
                save_potential_stocks()
                print(f"Main API: Loaded {len(potential_stocks)} potential stocks from cache.", flush=True)
        except Exception as e:
            print(f"Main API: Error loading potential stocks cache: {e}", flush=True)

def save_potential_stocks():
    try:
        with open(POTENTIAL_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump(potential_stocks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Main API: Error saving potential stocks cache: {e}", flush=True)

def load_potential_us_stocks():
    global potential_us_stocks
    if os.path.exists(POTENTIAL_US_STOCKS_FILE):
        try:
            with open(POTENTIAL_US_STOCKS_FILE, "r", encoding="utf-8") as f:
                potential_us_stocks = json.load(f)
                print(f"Main API: Loaded {len(potential_us_stocks)} potential US stocks from cache.", flush=True)
        except Exception as e:
            print(f"Main API: Error loading potential US stocks cache: {e}", flush=True)

def save_potential_us_stocks():
    try:
        with open(POTENTIAL_US_STOCKS_FILE, "w", encoding="utf-8") as f:
            json.dump(potential_us_stocks, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Main API: Error saving potential US stocks cache: {e}", flush=True)

def process_scanned_stock_data(stock_info, df_daily):
    ticker = stock_info["symbol"]
    code = stock_info["code"]
    name = stock_info["name"]
    
    import datetime
    tz_offset = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_offset)
    clock_intraday = now_tw.weekday() < 5 and (datetime.time(9, 0) <= now_tw.time() <= datetime.time(13, 35))
    is_intraday = False
    
    try:
        df_daily, split_events = normalize_unreported_split(df_daily, stock_info.get("code"))
        df_daily = df_daily[df_daily['Volume'] > 0]
        is_intraday = (
            clock_intraday
            and not df_daily.empty
            and df_daily.index[-1].date() == now_tw.date()
        )
        live_close = float(df_daily['Close'].iloc[-1]) if not df_daily.empty else None
        live_volume = float(df_daily['Volume'].iloc[-1]) if not df_daily.empty else 0
        if is_intraday and not df_daily.empty and df_daily.index[-1].date() == now_tw.date():
            df_daily = df_daily.iloc[:-1]
        if df_daily.empty or len(df_daily) < 60:
            return None
        
        # Fetch industry (best-effort)
        industry = stock_info.get("industry", "")
        if not industry:
            try:
                industry = get_yahoo_tw_business_desc(ticker)
            except Exception:
                pass
        # 1. Liquidity Filter: Today's Volume > 500 lots (500,000 shares)
        today_volume = df_daily['Volume'].iloc[-1]
        if today_volume < 500000:
            return None
            
        # Calculate MAs
        df_daily['MA5'] = df_daily['Close'].rolling(window=5).mean()
        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
        df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
        
        close_price = float(df_daily['Close'].iloc[-1])
        ma5 = float(df_daily['MA5'].iloc[-1])
        ma20 = float(df_daily['MA20'].iloc[-1])
        ma60 = float(df_daily['MA60'].iloc[-1])
        
        # 2. Large Timeframe Filter: Close > MA20 and MA60, and MA20 > MA60 (Bullish arrangement)
        if not (close_price > ma20 and close_price > ma60 and ma20 > ma60):
            return None
            
        # 3. Morphological Filter: Higher Lows (摨?擃?
        lows = df_daily['Low'].values
        minima_indices = find_local_minima(lows, order=5)
        if len(minima_indices) < 2:
            return None
            
        last_min = lows[minima_indices[-1]]
        prev_min = lows[minima_indices[-2]]
        if last_min <= prev_min:
            return None
        morph = calculate_higher_low_breakout(df_daily)
            
        # Optional: Grab hourly KD features
        latest_k = 0.0
        latest_d = 0.0
        golden_cross_count = 0
        try:
            t = yf.Ticker(ticker)
            df_hourly = t.history(period="2mo", interval="60m")
            df_hourly = validate_hourly_against_daily(df_hourly, df_daily)
            if is_intraday and not df_hourly.empty:
                df_hourly = df_hourly[df_hourly.index.date < now_tw.date()]
            if not df_hourly.empty and len(df_hourly) >= 20:
                df_hourly_kd = calculate_kd(df_hourly)
                latest_k = float(df_hourly_kd['K'].iloc[-1])
                latest_d = float(df_hourly_kd['D'].iloc[-1])
                
                # Count crosses
                recent_hourly = df_hourly_kd.tail(60)
                crosses = []
                for i in range(1, len(recent_hourly)):
                    k_prev = recent_hourly['K'].iloc[i-1]
                    d_prev = recent_hourly['D'].iloc[i-1]
                    k_curr = recent_hourly['K'].iloc[i]
                    d_curr = recent_hourly['D'].iloc[i]
                    if k_prev <= d_prev and k_curr > d_curr:
                        if k_curr < 40:
                            crosses.append(float(k_curr))
                golden_cross_count = len(crosses)
        except Exception as hourly_err:
            print(f"Background Scanner: Error fetching hourly KD for {ticker}: {hourly_err}", flush=True)
            
        prev_high = float(df_daily['High'].tail(60).max())
        latest_close = live_close if is_intraday and live_close is not None else close_price
        stop_loss_price = round(latest_close * 0.95, 2)
        r_value = 0.0
        risk = latest_close - stop_loss_price
        if risk > 0:
            r_value = round((prev_high - latest_close) / risk, 2)
            
        signals = calculate_strategy_signals(df_daily)
        
        # Calculate reference price and price change
        reference_price = None
        if not df_daily.empty:
            last_date_str = df_daily.index[-1].strftime("%Y-%m-%d")
            market_date = now_tw.strftime("%Y-%m-%d")
            if last_date_str == market_date:
                reference_price = float(df_daily['Close'].iloc[-2]) if len(df_daily) >= 2 else float(df_daily['Close'].iloc[-1])
            else:
                reference_price = float(df_daily['Close'].iloc[-1])
        reference_price = round(reference_price, 2) if reference_price is not None else latest_close
        price_change = round(latest_close - reference_price, 2)
        price_change_percent = round((price_change / reference_price) * 100, 2) if reference_price else 0.0
        
        disposition_info = disposition_cache.get(code, None)
        group_info = infer_tw_group(code, name, industry)
            
        return {
            "code": code,
            "symbol": ticker,
            "name": name,
            "added_by": stock_info.get("added_by", "popular"),
            "industry": industry,
            "group_category": group_info["group_category"],
            "concepts": group_info["concepts"],
            "current_price": round(latest_close, 2),
            "reference_price": reference_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "daily_ma20": round(ma20, 2),
            "daily_ma60": round(ma60, 2),
            "daily_trend_ok": close_price > ma20 and close_price > ma60 and ma20 > ma60,
            "is_intraday": is_intraday,
            "latest_k": round(latest_k, 2),
            "latest_d": round(latest_d, 2),
            "kd_under_50": latest_k < 50 and latest_d < 50,
            "golden_cross_count": golden_cross_count,
            "hourly_kd_ok": 2 <= golden_cross_count <= 3,
            "system_a_signal": (close_price > ma20 and close_price > ma60 and ma20 > ma60) and (latest_k < 50 and latest_d < 50) and (2 <= golden_cross_count <= 3),
            "prev_high": round(prev_high, 2),
            "stop_loss_price": stop_loss_price,
            "r_value": r_value,
            "volume_lots": int(today_volume // 1000),
            **morph,
            "signals": signals,
            "disposition": disposition_info,
            "error": None
        }
    except Exception as e:
        print(f"Background Scanner: Error processing data for {ticker}: {e}", flush=True)
        return None

def scan_single_stock(stock_info):
    ticker = stock_info["symbol"]
    try:
        t = yf.Ticker(ticker)
        df_daily = t.history(period="6mo", interval="1d")
        return process_scanned_stock_data(stock_info, df_daily)
    except Exception:
        return None

def process_scanned_us_stock_data(stock_info, df_daily):
    ticker = stock_info["symbol"]
    code = stock_info["code"]
    name = stock_info["name"]
    
    import datetime
    try:
        from zoneinfo import ZoneInfo
        tz_us = ZoneInfo("America/New_York")
    except ImportError:
        try:
            import pytz
            tz_us = pytz.timezone("America/New_York")
        except ImportError:
            tz_us = datetime.timezone(datetime.timedelta(hours=-4))
            
    now_us = datetime.datetime.now(tz_us)
    clock_intraday = now_us.weekday() < 5 and (datetime.time(9, 30) <= now_us.time() <= datetime.time(16, 0))
    is_intraday = False
    
    try:
        df_daily = df_daily[df_daily['Volume'] > 0]
        is_intraday = (
            clock_intraday
            and not df_daily.empty
            and df_daily.index[-1].date() == now_us.date()
        )
        live_close = float(df_daily['Close'].iloc[-1]) if not df_daily.empty else None
        live_volume = float(df_daily['Volume'].iloc[-1]) if not df_daily.empty else 0
        if is_intraday and not df_daily.empty and df_daily.index[-1].date() == now_us.date():
            df_daily = df_daily.iloc[:-1]
        if df_daily.empty or len(df_daily) < 60:
            return None
            
        today_volume = df_daily['Volume'].iloc[-1]
        if today_volume < 500000:
            return None
            
        df_daily['MA5'] = df_daily['Close'].rolling(window=5).mean()
        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
        df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
        
        close_price = float(df_daily['Close'].iloc[-1])
        ma5 = float(df_daily['MA5'].iloc[-1])
        ma20 = float(df_daily['MA20'].iloc[-1])
        ma60 = float(df_daily['MA60'].iloc[-1])
        
        if not (close_price > ma20 and close_price > ma60 and ma20 > ma60):
            return None
            
        lows = df_daily['Low'].values
        minima_indices = find_local_minima(lows, order=5)
        if len(minima_indices) < 2:
            return None
            
        last_min = lows[minima_indices[-1]]
        prev_min = lows[minima_indices[-2]]
        if last_min <= prev_min:
            return None
            
        morph = calculate_higher_low_breakout(df_daily)
        
        latest_k = 0.0
        latest_d = 0.0
        golden_cross_count = 0
        try:
            t = yf.Ticker(ticker)
            df_hourly = t.history(period="2mo", interval="60m")
            if is_intraday and not df_hourly.empty:
                df_hourly = df_hourly[df_hourly.index.date < now_us.date()]
            if not df_hourly.empty and len(df_hourly) >= 20:
                df_hourly_kd = calculate_kd(df_hourly)
                latest_k = float(df_hourly_kd['K'].iloc[-1])
                latest_d = float(df_hourly_kd['D'].iloc[-1])
                
                recent_hourly = df_hourly_kd.tail(60)
                crosses = []
                for i in range(1, len(recent_hourly)):
                    k_prev = recent_hourly['K'].iloc[i-1]
                    d_prev = recent_hourly['D'].iloc[i-1]
                    k_curr = recent_hourly['K'].iloc[i]
                    d_curr = recent_hourly['D'].iloc[i]
                    if k_prev <= d_prev and k_curr > d_curr:
                        if k_curr < 40:
                            crosses.append(float(k_curr))
                golden_cross_count = len(crosses)
        except Exception as hourly_err:
            print(f"Background US Scanner: Error fetching hourly KD for {ticker}: {hourly_err}", flush=True)
            
        prev_high = float(df_daily['High'].tail(60).max())
        latest_close = live_close if is_intraday and live_close is not None else close_price
        stop_loss_price = round(latest_close * 0.95, 2)
        r_value = 0.0
        risk = latest_close - stop_loss_price
        if risk > 0:
            r_value = round((prev_high - latest_close) / risk, 2)
            
        signals = calculate_strategy_signals(df_daily)
        company_profile = ensure_us_company_profile(stock_info)
        
        # Calculate reference price and price change
        reference_price = None
        if not df_daily.empty:
            last_date_str = df_daily.index[-1].strftime("%Y-%m-%d")
            market_date = now_us.strftime("%Y-%m-%d")
            if last_date_str == market_date:
                reference_price = float(df_daily['Close'].iloc[-2]) if len(df_daily) >= 2 else float(df_daily['Close'].iloc[-1])
            else:
                reference_price = float(df_daily['Close'].iloc[-1])
        reference_price = round(reference_price, 2) if reference_price is not None else latest_close
        price_change = round(latest_close - reference_price, 2)
        price_change_percent = round((price_change / reference_price) * 100, 2) if reference_price else 0.0

        return {
            "code": code,
            "symbol": ticker,
            "name": company_profile.get("name_en") or name,
            "name_zh": company_profile.get("name_zh", ""),
            "business_zh": company_profile.get("business_zh", ""),
            "added_by": "scan",
            "market": "US",
            "category": "美股掃描",
            "industry": company_profile.get("business_zh", ""),
            "group_category": company_profile.get("group_category", "其他板塊"),
            "concepts": company_profile.get("concepts", []),
            "current_price": round(latest_close, 2),
            "reference_price": reference_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "daily_ma20": round(ma20, 2),
            "daily_ma60": round(ma60, 2),
            "daily_trend_ok": close_price > ma20 and close_price > ma60 and ma20 > ma60,
            "is_intraday": is_intraday,
            "latest_k": round(latest_k, 2),
            "latest_d": round(latest_d, 2),
            "kd_under_50": latest_k < 50 and latest_d < 50,
            "golden_cross_count": golden_cross_count,
            "hourly_kd_ok": 2 <= golden_cross_count <= 3,
            "system_a_signal": (close_price > ma20 and close_price > ma60 and ma20 > ma60) and (latest_k < 50 and latest_d < 50) and (2 <= golden_cross_count <= 3),
            "prev_high": round(prev_high, 2),
            "stop_loss_price": stop_loss_price,
            "r_value": r_value,
            "volume_lots": int(today_volume // 1000),
            **morph,
            "signals": signals,
            "disposition": None,
            "error": None
        }
    except Exception as e:
        print(f"Background US Scanner: Error processing data for {ticker}: {e}", flush=True)
        return None

def run_us_market_scan():
    global us_market_scan_active, us_market_scan_progress, us_market_scan_total, potential_us_stocks
    if us_market_scan_active:
        return
    us_market_scan_active = True
    
    def worker():
        global us_market_scan_progress, us_market_scan_total, us_market_scan_active, potential_us_stocks
        try:
            print("Background US Scanner: Fetching US stock constituents...", flush=True)
            stocks = cached_all_us_stocks if cached_all_us_stocks else fetch_all_us_stocks()
            us_market_scan_total = len(stocks)
            us_market_scan_progress = 0
            
            if not stocks:
                us_market_scan_active = False
                return
                
            temp_potentials = []
            chunk_size = 150
            stock_chunks = [stocks[i:i + chunk_size] for i in range(0, len(stocks), chunk_size)]
            
            print(f"Background US Scanner: Divided {len(stocks)} stocks into {len(stock_chunks)} batches.", flush=True)
            
            for chunk_idx, chunk in enumerate(stock_chunks):
                symbols = [s["symbol"] for s in chunk]
                print(f"Background US Scanner: Downloading batch {chunk_idx + 1}/{len(stock_chunks)}...", flush=True)
                
                try:
                    df = yf.download(symbols, period="6mo", interval="1d", progress=False, threads=True, timeout=15, auto_adjust=False)
                except Exception as dl_err:
                    print(f"Background US Scanner: Failed batch {chunk_idx + 1}: {dl_err}", flush=True)
                    us_market_scan_progress += len(chunk)
                    time.sleep(2)
                    continue
                
                if df.empty:
                    us_market_scan_progress += len(chunk)
                    time.sleep(2)
                    continue
                
                for s in chunk:
                    us_market_scan_progress += 1
                    sym = s["symbol"]
                    
                    try:
                        df_sym = None
                        if isinstance(df.columns, pd.MultiIndex):
                            if ('Close', sym) in df.columns:
                                df_sym = pd.DataFrame({
                                    'Open': df[('Open', sym)],
                                    'High': df[('High', sym)],
                                    'Low': df[('Low', sym)],
                                    'Close': df[('Close', sym)],
                                    'Volume': df[('Volume', sym)]
                                }).dropna(subset=['Close'])
                        else:
                            if 'Close' in df.columns:
                                df_sym = pd.DataFrame({
                                    'Open': df['Open'],
                                    'High': df['High'],
                                    'Low': df['Low'],
                                    'Close': df['Close'],
                                    'Volume': df['Volume']
                                }).dropna(subset=['Close'])

                        if df_sym is not None and not df_sym.empty:
                            res = process_scanned_us_stock_data(s, df_sym)
                            if res is not None:
                                temp_potentials.append(res)
                    except Exception as parse_err:
                        continue
                
                # Add delay to prevent Yahoo rate-limiting
                time.sleep(1.5)
            
            temp_potentials.sort(key=lambda x: x.get("volume_lots", 0), reverse=True)
            potential_us_stocks = temp_potentials
            save_potential_us_stocks()
            
            # Update US stock list (preserve manual stocks and default indicators)
            refreshed = list(DEFAULT_US_STOCKS)
            manual_stocks = [
                item for item in read_us_stock_list()
                if item.get("added_by") == "manual"
            ]
            known_symbols = {item["symbol"] for item in refreshed}
            for item in manual_stocks:
                symbol = str(item.get("symbol") or item.get("code") or "").upper()
                if symbol and symbol not in known_symbols:
                    refreshed.append(item)
                    known_symbols.add(symbol)
                    
            added_count = 0
            for ps in potential_us_stocks:
                sym = ps["symbol"]
                if sym not in known_symbols:
                    refreshed.append({
                        "code": ps["code"],
                        "symbol": sym,
                        "name": ps["name"],
                        "category": "美股掃描",
                        "market": "US",
                        "added_by": "scan"
                    })
                    known_symbols.add(sym)
                    added_count += 1
                    if added_count >= 120:
                        break
            
            write_us_stock_list(refreshed)
            
            # Pre-populate cache
            existing_cache = []
            if os.path.exists(US_ANALYSIS_CACHE_FILE):
                try:
                    with open(US_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                        existing_cache = json.load(file)
                except Exception:
                    pass
            if not isinstance(existing_cache, list):
                existing_cache = []
                
            cache_map = {row["symbol"]: row for row in existing_cache if isinstance(row, dict) and "symbol" in row}
            for ps in potential_us_stocks:
                cache_map[ps["symbol"]] = ps
                
            active_symbols = {item["symbol"] for item in refreshed}
            final_cache = [row for sym, row in cache_map.items() if sym in active_symbols]
            write_analysis_cache(US_ANALYSIS_CACHE_FILE, final_cache)
            print(f"Background US Scanner: Completed. Added {added_count} stocks to Watchlist.", flush=True)
        except Exception as e:
            print(f"Background US Scanner: Error: {e}", flush=True)
        finally:
            us_market_scan_active = False
            
    threading.Thread(target=worker, daemon=True).start()

def run_all_market_scan():
    global all_market_scan_active, all_market_scan_progress, all_market_scan_total, potential_stocks
    if all_market_scan_active:
        return
    all_market_scan_active = True
    
    def worker():
        global all_market_scan_progress, all_market_scan_total, all_market_scan_active, potential_stocks
        try:
            print("Background Scanner: Fetching TWSE/TPEx stock listings...", flush=True)
            stocks = fetch_all_tw_stocks()
            all_market_scan_total = len(stocks)
            all_market_scan_progress = 0
            
            if not stocks:
                all_market_scan_active = False
                return
                
            temp_potentials = []
            
            # Divide stocks into chunks of 150 to prevent rate limits and hangs
            chunk_size = 150
            stock_chunks = [stocks[i:i + chunk_size] for i in range(0, len(stocks), chunk_size)]
            
            print(f"Background Scanner: Divided {len(stocks)} stocks into {len(stock_chunks)} batches.", flush=True)
            
            for chunk_idx, chunk in enumerate(stock_chunks):
                symbols = [s["symbol"] for s in chunk]
                print(f"Background Scanner: Downloading batch {chunk_idx + 1}/{len(stock_chunks)} ({len(symbols)} symbols)...", flush=True)
                
                try:
                    df = yf.download(symbols, period="6mo", interval="1d", progress=False, threads=True, timeout=15, auto_adjust=False)
                except Exception as dl_err:
                    print(f"Background Scanner: Failed to download batch {chunk_idx + 1}: {dl_err}", flush=True)
                    all_market_scan_progress += len(chunk)
                    time.sleep(2)
                    continue
                
                if df.empty:
                    print(f"Background Scanner: Empty data for batch {chunk_idx + 1}", flush=True)
                    all_market_scan_progress += len(chunk)
                    time.sleep(2)
                    continue
                
                for s in chunk:
                    all_market_scan_progress += 1
                    sym = s["symbol"]
                    
                    try:
                        # 瑼Ｘ閰脰蟡冽?衣Ⅱ撖血??冽銝??????葉
                        df_sym = None
                        if isinstance(df.columns, pd.MultiIndex):
                            if ('Close', sym) in df.columns:
                                df_sym = pd.DataFrame({
                                    'Open': df[('Open', sym)],
                                    'High': df[('High', sym)],
                                    'Low': df[('Low', sym)],
                                    'Close': df[('Close', sym)],
                                    'Volume': df[('Volume', sym)]
                                }).dropna(subset=['Close'])
                        else:
                            # 憒?銝??桐?瑼??芣? Close 甈?
                            if 'Close' in df.columns:
                                df_sym = pd.DataFrame({
                                    'Open': df['Open'],
                                    'High': df['High'],
                                    'Low': df['Low'],
                                    'Close': df['Close'],
                                    'Volume': df['Volume']
                                }).dropna(subset=['Close'])

                        if df_sym is not None and not df_sym.empty:
                            res = process_scanned_stock_data(s, df_sym)
                            if res is not None:
                                temp_potentials.append(res)
                        else:
                            continue
                            
                    except Exception as parse_err:
                        print(f"Background Scanner: parse error for {sym}: {parse_err}", flush=True)
                        continue
                
                # Add delay to prevent Yahoo rate-limiting
                time.sleep(1.5)
            
            # Sort potential stocks: highest volume first
            temp_potentials.sort(key=lambda x: x.get("volume_lots", 0), reverse=True)
            potential_stocks = temp_potentials
            save_potential_stocks()
            print(f"Background Scanner: Completed. Found {len(potential_stocks)} stocks passing filters.", flush=True)
        except Exception as e:
            print(f"Background Scanner: Error: {e}", flush=True)
        finally:
            all_market_scan_active = False
            
    threading.Thread(target=worker, daemon=True).start()

# Visitor Stats and All Stocks APIs
VISITOR_STATS_FILE = os.path.join(DATA_DIR, "visitor_stats.json")
ALL_STOCKS_FILE = os.path.join(DATA_DIR, "all_tw_stocks.json")

def read_visitor_stats():
    if os.path.exists(VISITOR_STATS_FILE):
        try:
            with open(VISITOR_STATS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "home": 0,
        "company": 0,
        "phone": 0,
        "other": 0,
        "home_ip": "",
        "company_ip": ""
    }

def save_visitor_stats(stats):
    try:
        os.makedirs(os.path.dirname(VISITOR_STATS_FILE), exist_ok=True)
        with open(VISITOR_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving visitor stats: {e}", flush=True)

@app.get("/api/visit")
def record_visit(request: Request, loc: Optional[str] = None):
    stats = read_visitor_stats()
    
    # Get client IP
    client_ip = request.client.host if request.client else "127.0.0.1"
    
    # Get user agent
    ua = request.headers.get("user-agent", "").lower()
    is_mobile = any(m in ua for m in ["mobi", "android", "iphone", "ipad"])
    
    # If explicitly setting the mapping
    if loc in ["home", "company"]:
        if loc == "home":
            stats["home_ip"] = client_ip
        elif loc == "company":
            stats["company_ip"] = client_ip
        save_visitor_stats(stats)
    
    # Classify the current visit
    determined_loc = "other"
    if is_mobile or loc == "phone":
        stats["phone"] += 1
        determined_loc = "phone"
    elif client_ip == stats.get("home_ip") or loc == "home":
        stats["home"] += 1
        determined_loc = "home"
    elif client_ip == stats.get("company_ip") or loc == "company":
        stats["company"] += 1
        determined_loc = "company"
    else:
        stats["other"] += 1
        determined_loc = "other"
        
    save_visitor_stats(stats)
    
    return {
        "stats": {
            "home": stats["home"],
            "company": stats["company"],
            "phone": stats["phone"],
            "other": stats["other"]
        },
        "current_ip": client_ip,
        "determined_loc": determined_loc,
        "home_ip": stats.get("home_ip", ""),
        "company_ip": stats.get("company_ip", "")
    }

@app.get("/api/visitor_stats")
def get_visitor_stats():
    stats = read_visitor_stats()
    return {
        "home": stats["home"],
        "company": stats["company"],
        "phone": stats["phone"],
        "other": stats["other"]
    }

@app.get("/api/all_stocks")
def get_all_stocks():
    if os.path.exists(ALL_STOCKS_FILE):
        try:
            with open(ALL_STOCKS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading all stocks file: {e}")
    return []

# Route Endpoints
@app.get("/api/stocks")
def get_stocks():
    stocks = read_stock_list()
    formatted = []
    for s in stocks:
        item = s.copy()
        item["name"] = format_stock_name(s)
        formatted.append(item)
    return formatted

@app.post("/api/stocks")
def add_stock(req: AddStockRequest):
    input_val = req.code.strip()
    if not input_val:
        raise HTTPException(status_code=400, detail="No market data available for this symbol")
        
    stocks = read_stock_list()
    
    # Check if we can search by stock name mapping first
    from fetch_data import get_stock_name_map
    stock_map = get_stock_name_map()
    
    code = ""
    name = ""
    
    # Try direct code matching
    if re.fullmatch(r'\d{4,6}[a-zA-Z]?', input_val):
        code = input_val.upper()
    else:
        # Search by name in get_stock_name_map
        for k, v in stock_map.items():
            if v == input_val or input_val in v:
                code = k
                name = v
                break
                
    if not code:
        # Try finding code as-is using Yahoo search or fallback
        code = input_val.upper()
        
    if any(str(s["code"]).upper() == code for s in stocks):
        raise HTTPException(status_code=400, detail=f"{code} 已在台股追蹤清單")
        
    symbol = f"{code}.TW"
    if name == "":
        name = resolve_stock_name(code, stock_map.get(code, UNKNOWN_STOCK_NAME))
    
    try:
        # Check using yfinance checking
        ticker = yf.Ticker(symbol)
        info = ticker.history(period="5d")
        if info.empty:
            symbol = f"{code}.TWO"
            ticker = yf.Ticker(symbol)
            info = ticker.history(period="5d")
            
        if info.empty:
            raise HTTPException(status_code=400, detail="No market data available for this symbol")
            
        if name == UNKNOWN_STOCK_NAME:
            url = f"https://tw.stock.yahoo.com/quote/{symbol}"
            headers = {"User-Agent": "Mozilla/5.0"}
            res = requests.get(url, headers=headers, timeout=5)
            if res.status_code == 200:
                soup = BeautifulSoup(res.content, "lxml")
                title = soup.title.text if soup.title else ""
                match_name = re.match(r'^([^\s(]+)', title)
                if match_name:
                    name = match_name.group(1)
                        
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"撽??∠巨隞????隤? {str(e)}")
        
    new_stock = {"code": code, "symbol": symbol, "name": name, "added_by": req.added_by}
    stocks.append(new_stock)
    write_stock_list(stocks)
    
    # Analyze the new stock immediately and merge it into tw_analysis_cache.json
    try:
        analysis_result = analyze_single_stock(new_stock)
        
        # Merge official quote information
        official_quotes = fetch_twse_realtime_quotes([new_stock])
        quote = official_quotes.get(code)
        if quote:
            if quote.get("price") is not None and quote["price"] > 0:
                price = round(quote["price"], 2)
                analysis_result["current_price"] = price
                analysis_result["stop_loss_price"] = round(price * 0.95, 2)
                prev_high = analysis_result.get("prev_high")
                risk = price - analysis_result["stop_loss_price"]
                if prev_high is not None and risk > 0:
                    analysis_result["r_value"] = round((prev_high - price) / risk, 2)
                
                ref_price = quote.get("reference") or analysis_result.get("reference_price")
                if ref_price:
                    analysis_result["reference_price"] = ref_price
                    analysis_result["price_change"] = round(price - ref_price, 2)
                    analysis_result["price_change_percent"] = round(((price - ref_price) / ref_price) * 100, 2)
            if quote.get("volume") is not None and int(quote["volume"]) > 0:
                analysis_result["volume_lots"] = int(quote["volume"])
            if quote.get("limit_up"):
                analysis_result["limit_up"] = quote["limit_up"]
            if quote.get("limit_down"):
                analysis_result["limit_down"] = quote["limit_down"]
            analysis_result["quote_source"] = quote["source"]
            analysis_result["quote_time"] = quote["time"]
            analysis_result["is_intraday"] = is_tw_market_open()
        
        if os.path.exists(TW_ANALYSIS_CACHE_FILE):
            with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cached = json.load(file)
            if isinstance(cached, list):
                cached = [row for row in cached if str(row.get("code", "")).upper() != code]
                cached.append(analysis_result)
                with open(TW_ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as file:
                    json.dump(cached, file, ensure_ascii=False)
    except Exception as ex:
        print(f"Error appending new stock to cache: {ex}", flush=True)

    return_stock = new_stock.copy()
    return_stock["name"] = format_stock_name(new_stock)
    return return_stock

@app.delete("/api/stocks/{code}")
def remove_stock(code: str):
    stocks = read_stock_list()
    filtered_stocks = [s for s in stocks if s["code"] != code]
    
    if len(filtered_stocks) == len(stocks):
        raise HTTPException(status_code=404, detail="?曆??啗府?∠巨隞??")
        
    write_stock_list(filtered_stocks)
    return {"message": f"???芷?∠巨 {code}"}

def do_tw_analysis():
    stocks = read_stock_list()
    results = []
    market_open = is_tw_market_open()
    
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(analyze_single_stock, stock) for stock in stocks]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as e:
                results.append({
                    "code": "ERROR",
                    "symbol": "ERROR",
                    "name": UNKNOWN_STOCK_NAME,
                    "error": str(e),
                    "system_a_signal": False
                })
                
    cleaned = clean_nan(results)
    official_quotes = fetch_twse_realtime_quotes(stocks)
    for row in cleaned:
        code = str(row.get("code", "")).upper()
        quote = official_quotes.get(code)
        if not quote:
            row["is_intraday"] = market_open
            continue
        if quote.get("price") is not None and quote["price"] > 0:
            price = round(quote["price"], 2)
            row["current_price"] = price
            row["stop_loss_price"] = round(price * 0.95, 2)
            prev_high = row.get("prev_high")
            risk = price - row["stop_loss_price"]
            if prev_high is not None and risk > 0:
                row["r_value"] = round((prev_high - price) / risk, 2)
            
            ref_price = quote.get("reference") or row.get("reference_price")
            if ref_price:
                row["reference_price"] = ref_price
                row["price_change"] = round(price - ref_price, 2)
                row["price_change_percent"] = round(((price - ref_price) / ref_price) * 100, 2)
        if quote.get("volume") is not None and int(quote["volume"]) > 0:
            row["volume_lots"] = int(quote["volume"])
        if quote.get("limit_up"):
            row["limit_up"] = quote["limit_up"]
        if quote.get("limit_down"):
            row["limit_down"] = quote["limit_down"]
        row["quote_source"] = quote["source"]
        row["quote_time"] = quote["time"]
        row["is_intraday"] = market_open
        
    write_analysis_cache(TW_ANALYSIS_CACHE_FILE, cleaned)
    return cleaned

def do_us_analysis():
    stocks = read_us_stock_list()
    results = []
    with ThreadPoolExecutor(max_workers=30) as executor:
        futures = [executor.submit(analyze_single_stock, stock) for stock in stocks]
        for future in futures:
            try:
                results.append(future.result())
            except Exception as error:
                results.append({
                    "code": "ERROR",
                    "symbol": "ERROR",
                    "name": "US Stock",
                    "market": "US",
                    "error": str(error),
                    "system_a_signal": False,
                })
    cleaned = clean_nan(results)
    write_analysis_cache(US_ANALYSIS_CACHE_FILE, cleaned)
    return cleaned

# Keep track of active background scans to prevent duplicate concurrent scans
active_scans = set()

def run_tw_analysis_in_background():
    if "TW" in active_scans:
        return
    active_scans.add("TW")
    try:
        print("Starting background TW stocks analysis...", flush=True)
        do_tw_analysis()
        print("Background TW stocks analysis completed.", flush=True)
    except Exception as e:
        print(f"Background TW stocks analysis failed: {e}", flush=True)
    finally:
        active_scans.discard("TW")

def run_us_analysis_in_background():
    if "US" in active_scans:
        return
    active_scans.add("US")
    try:
        print("Starting background US stocks analysis...", flush=True)
        do_us_analysis()
        print("Background US stocks analysis completed.", flush=True)
    except Exception as e:
        print(f"Background US stocks analysis failed: {e}", flush=True)
    finally:
        active_scans.discard("US")

def overlay_realtime_quotes(stocks, cached_data, market_open):
    # Create lookup map for cached rows by stock code
    cache_map = {}
    if cached_data:
        for row in cached_data:
            code = str(row.get("code", "")).upper()
            if code:
                cache_map[code] = row
                
    # Fetch latest quotes from TWSE MIS
    official_quotes = {}
    try:
        official_quotes = fetch_twse_realtime_quotes(stocks)
    except Exception as e:
        print(f"Error fetching real-time quotes in overlay: {e}", flush=True)
        
    results = []
    for stock in stocks:
        code = str(stock.get("code", "")).upper()
        # Find if it is cached
        cached_row = cache_map.get(code)
        if cached_row:
            row = dict(cached_row)
        else:
            # Create a placeholder row with default/missing technical indicators
            row = {
                "code": stock["code"],
                "symbol": stock.get("symbol") or f"{stock['code']}.TW",
                "name": stock.get("name") or UNKNOWN_STOCK_NAME,
                "added_by": stock.get("added_by", "popular"),
                "market": "TW",
                "category": stock.get("category", ""),
                "industry": "",
                "group_category": "",
                "concepts": [],
                "current_price": None,
                "reference_price": None,
                "price_change": None,
                "price_change_percent": None,
                "volume_lots": 0,
                "daily_ma20": 0.0,
                "daily_ma60": 0.0,
                "daily_trend_ok": False,
                "latest_k": None,
                "latest_d": None,
                "kd_under_50": False,
                "golden_cross_count": 0,
                "hourly_kd_ok": False,
                "pattern_ok": False,
                "morph_info": "",
                "system_a_signal": False,
                "prev_high": 0.0,
                "stop_loss_price": 0.0,
                "r_value": 0.0,
                "signals": {
                    "light_1": False,
                    "light_2": False,
                    "light_3": False,
                    "light_4": False,
                    "light_5": False
                },
                "disposition": None,
                "is_intraday": market_open,
                "insufficient_history": True,
                "error": None
            }
            
        # Overlay the fresh quote if available
        quote = official_quotes.get(code)
        if quote:
            if quote.get("price") is not None and quote["price"] > 0:
                price = round(quote["price"], 2)
                row["current_price"] = price
                row["stop_loss_price"] = round(price * 0.95, 2)
                
                prev_high = row.get("prev_high")
                risk = price - row["stop_loss_price"]
                if prev_high is not None and prev_high > 0 and risk > 0:
                    row["r_value"] = round((prev_high - price) / risk, 2)
                
                ref_price = quote.get("reference") or row.get("reference_price")
                if ref_price:
                    row["reference_price"] = ref_price
                    row["price_change"] = round(price - ref_price, 2)
                    row["price_change_percent"] = round(((price - ref_price) / ref_price) * 100, 2)
            
            if quote.get("volume") is not None and int(quote["volume"]) > 0:
                row["volume_lots"] = int(quote["volume"])
            if quote.get("limit_up"):
                row["limit_up"] = quote["limit_up"]
            if quote.get("limit_down"):
                row["limit_down"] = quote["limit_down"]
            row["quote_source"] = quote["source"]
            row["quote_time"] = quote["time"]
            row["is_intraday"] = market_open
        else:
            row["is_intraday"] = market_open
            
        results.append(row)
        
    return results

@app.get("/api/stocks/analyze")
def analyze_stocks(background_tasks: BackgroundTasks, force: bool = False):
    # Check if we have any cached data at all (expired or not)
    cached_data = None
    cache_exists = os.path.exists(TW_ANALYSIS_CACHE_FILE)
    
    if cache_exists:
        try:
            with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cached_data = json.load(file)
        except Exception:
            pass

    # If force is True, or if we don't have any cache at all, we must run it synchronously
    if force or not cached_data:
        return do_tw_analysis()

    # Otherwise (force=False and we have some cached data):
    # Check if the cache is expired
    mtime = os.path.getmtime(TW_ANALYSIS_CACHE_FILE)
    market_open = is_tw_market_open()
    expired = False
    if market_open:
        if time.time() - mtime > ANALYSIS_CACHE_TTL_SECONDS:
            expired = True
    else:
        last_close = get_last_market_close("TW")
        if mtime < last_close.timestamp():
            expired = True

    # If it is expired, trigger background update
    if expired and "TW" not in active_scans:
        background_tasks.add_task(run_tw_analysis_in_background)
        
    # Return the cached data immediately to guarantee instant page load.
    return cached_data

@app.get("/api/us-stocks/analyze")
def analyze_us_stocks(background_tasks: BackgroundTasks, force: bool = False):
    # Check if we have any cached data at all (expired or not)
    cached_data = None
    cache_exists = os.path.exists(US_ANALYSIS_CACHE_FILE)
    
    if cache_exists:
        try:
            with open(US_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cached_data = json.load(file)
        except Exception:
            pass

    # If force is True, or if we don't have any cache at all, we must run it synchronously
    if force or not cached_data:
        return do_us_analysis()

    # Otherwise (force=False and we have some cached data):
    # Check if the cache is expired
    mtime = os.path.getmtime(US_ANALYSIS_CACHE_FILE)
    market_open = is_us_market_open()
    expired = False
    if market_open:
        if time.time() - mtime > ANALYSIS_CACHE_TTL_SECONDS:
            expired = True
    else:
        last_close = get_last_market_close("US")
        if mtime < last_close.timestamp():
            expired = True

    # If it is expired, trigger background update
    if expired and "US" not in active_scans:
        background_tasks.add_task(run_us_analysis_in_background)
        
    # Return the cached data immediately!
    return cached_data

@app.post("/api/us-stocks")
def add_us_stock(req: AddStockRequest):
    code = str(req.code or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9][A-Z0-9.\-]{0,14}", code):
        raise HTTPException(status_code=400, detail="請輸入有效的美股代號")

    stocks = read_us_stock_list()
    if any(str(item.get("code", "")).upper() == code for item in stocks):
        raise HTTPException(status_code=400, detail=f"{code} 已在美股追蹤清單")

    try:
        ticker = yf.Ticker(code)
        history = ticker.history(period="5d", interval="1d")
        if history.empty:
            raise HTTPException(status_code=400, detail=f"查無美股代號 {code}")
        profile = ensure_us_company_profile({
            "code": code,
            "symbol": code,
            "name": code,
        })
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail=f"無法取得 {code} 的市場資料")

    added_by = req.added_by or "manual"
    category = "網頁加入" if added_by == "web" else "手動加入"

    new_stock = {
        "code": code,
        "symbol": code,
        "name": profile.get("name_en") or code,
        "category": category,
        "market": "US",
        "added_by": added_by,
    }
    stocks.append(new_stock)
    write_us_stock_list(stocks)
    
    # Analyze the new US stock immediately and merge it into us_analysis_cache.json
    try:
        analysis_result = analyze_single_stock(new_stock)
        if os.path.exists(US_ANALYSIS_CACHE_FILE):
            with open(US_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cached = json.load(file)
            if isinstance(cached, list):
                cached = [row for row in cached if str(row.get("code", "")).upper() != code]
                cached.append(analysis_result)
                with open(US_ANALYSIS_CACHE_FILE, "w", encoding="utf-8") as file:
                    json.dump(cached, file, ensure_ascii=False)
    except Exception as ex:
        print(f"Error appending new US stock to cache: {ex}", flush=True)

    return {
        **new_stock,
        "name_zh": profile.get("name_zh", ""),
        "business_zh": profile.get("business_zh", ""),
    }

@app.delete("/api/us-stocks/{code}")
def remove_us_stock(code: str):
    normalized = code.strip().upper()
    stocks = read_us_stock_list()
    filtered = [
        item for item in stocks
        if str(item.get("code", "")).upper() != normalized
    ]
    if len(filtered) == len(stocks):
        raise HTTPException(status_code=404, detail=f"{normalized} 不在美股追蹤清單")
    write_us_stock_list(filtered)
    return {"success": True, "code": normalized}

@app.post("/api/us-stocks/refresh-popular")
def refresh_us_popular_stocks():
    indicator_symbols = {item["symbol"] for item in DEFAULT_US_STOCKS}
    refreshed = list(DEFAULT_US_STOCKS)
    manual_stocks = [
        item for item in read_us_stock_list()
        if item.get("added_by") == "manual"
    ]
    known_symbols = {item["symbol"] for item in refreshed}
    for item in manual_stocks:
        symbol = str(item.get("symbol") or item.get("code") or "").upper()
        if symbol and symbol not in known_symbols:
            refreshed.append(item)
            known_symbols.add(symbol)
    popular_count = 0
    try:
        screen = yf.screen("most_actives", count=20)
        for quote in screen.get("quotes", []):
            symbol = str(quote.get("symbol", "")).strip().upper()
            quote_type = str(quote.get("quoteType", "")).upper()
            if not symbol or symbol in known_symbols or quote_type not in ("EQUITY", "ETF"):
                continue
            if any(char in symbol for char in ("^", "=", ".", "-")):
                continue
            refreshed.append({
                "code": symbol,
                "symbol": symbol,
                "name": quote.get("shortName") or quote.get("longName") or symbol,
                "category": "Yahoo熱門",
                "market": "US",
                "added_by": "popular",
            })
            known_symbols.add(symbol)
            popular_count += 1
            if popular_count >= 16:
                break
        write_us_stock_list(refreshed)
        return {
            "success": True,
            "count": len(refreshed),
            "indicator_count": len(DEFAULT_US_STOCKS),
            "popular_count": popular_count,
            "indicator_source": YAHOO_TW_US_MARKET_URL,
        }
    except Exception as error:
        print(f"Unable to refresh Yahoo US popular stocks: {error}", flush=True)
        if not os.path.exists(US_STOCKS_FILE):
            write_us_stock_list(refreshed)
        return {"success": False, "count": len(read_us_stock_list()), "message": str(error)}

@app.get("/api/stocks/potential")
def get_potential_stocks(realtime: bool = True):
    cleaned = clean_nan(potential_stocks)
    
    # Override potential stock indicators with latest self-selected cache if available
    if os.path.exists(TW_ANALYSIS_CACHE_FILE):
        try:
            with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cache_data = json.load(file)
            cache_map = {str(item.get("code", "")).strip(): item for item in cache_data if item.get("code")}
            for s in cleaned:
                code = str(s.get("code", "")).strip()
                cached = cache_map.get(code)
                if cached:
                    # Sync all technical indicators and signals to guarantee 100% consistency
                    s["current_price"] = cached.get("current_price", s.get("current_price"))
                    s["reference_price"] = cached.get("reference_price", s.get("reference_price"))
                    s["price_change"] = cached.get("price_change", s.get("price_change"))
                    s["price_change_percent"] = cached.get("price_change_percent", s.get("price_change_percent"))
                    s["volume_lots"] = cached.get("volume_lots", s.get("volume_lots"))
                    s["daily_ma20"] = cached.get("daily_ma20", s.get("daily_ma20"))
                    s["daily_ma60"] = cached.get("daily_ma60", s.get("daily_ma60"))
                    s["daily_trend_ok"] = cached.get("daily_trend_ok", s.get("daily_trend_ok"))
                    s["latest_k"] = cached.get("latest_k", s.get("latest_k"))
                    s["latest_d"] = cached.get("latest_d", s.get("latest_d"))
                    s["kd_under_50"] = cached.get("kd_under_50", s.get("kd_under_50"))
                    s["golden_cross_count"] = cached.get("golden_cross_count", s.get("golden_cross_count"))
                    s["hourly_kd_ok"] = cached.get("hourly_kd_ok", s.get("hourly_kd_ok"))
                    s["system_a_signal"] = cached.get("system_a_signal", s.get("system_a_signal"))
                    s["prev_high"] = cached.get("prev_high", s.get("prev_high"))
                    s["stop_loss_price"] = cached.get("stop_loss_price", s.get("stop_loss_price"))
                    s["r_value"] = cached.get("r_value", s.get("r_value"))
                    s["signals"] = cached.get("signals", s.get("signals"))
                    s["morph_ok"] = cached.get("morph_ok", s.get("morph_ok"))
                    s["morph_breakout"] = cached.get("morph_breakout", s.get("morph_breakout"))
                    s["morph_signal"] = cached.get("morph_signal", s.get("morph_signal"))
        except Exception as cache_err:
            print(f"Error aligning potential stocks with self-selected cache: {cache_err}", flush=True)

    market_open = is_tw_market_open()
    if not realtime or not market_open:
        return cleaned
    try:
        overlaid = overlay_realtime_quotes(cleaned, cleaned, market_open)
        return overlaid
    except Exception as e:
        print(f"Error overlaying real-time quotes for potential stocks: {e}", flush=True)
        return cleaned

@app.get("/api/stocks/monitor-signals")
def get_monitor_signals():
    connector = SinoPacConnector.get_instance()
    items_by_code = {}
    for order in connector.orders + getattr(connector, "trailing_orders", []):
        code = str(order.get("code", "")).strip()
        if code and code not in items_by_code:
            items_by_code[code] = {
                "code": code,
                "symbol": str(order.get("symbol") or f"{code.upper()}.TW").upper(),
                "name": resolve_stock_name(code, order.get("name")),
                "added_by": "monitor",
            }

    codes_key = ",".join(sorted(items_by_code))
    now = time.time()
    if (
        monitor_signal_cache["codes"] == codes_key
        and now - monitor_signal_cache["updated_at"] < 300
    ):
        return monitor_signal_cache["data"]

    results = {}
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = {
            executor.submit(analyze_single_stock, item): code
            for code, item in items_by_code.items()
        }
        for future, code in futures.items():
            try:
                analysis = future.result()
                results[code] = {
                    "system_a_signal": bool(analysis.get("system_a_signal")),
                    "daily_trend_ok": bool(analysis.get("daily_trend_ok")),
                    "hourly_kd_ok": bool(analysis.get("hourly_kd_ok")),
                    "golden_cross_count": analysis.get("golden_cross_count", 0),
                    "error": analysis.get("error"),
                }
            except Exception as error:
                results[code] = {"system_a_signal": False, "error": str(error)}

    monitor_signal_cache.update({
        "updated_at": now,
        "codes": codes_key,
        "data": results,
    })
    return clean_nan(results)

@app.get("/api/all_us_stocks")
def get_all_us_stocks():
    return cached_all_us_stocks

@app.post("/api/us-stocks/scan")
def trigger_us_market_scan():
    if us_market_scan_active:
        return {"success": False, "message": "US Market Scan already running"}
    run_us_market_scan()
    return {"success": True, "message": "US Market Scan started"}

@app.get("/api/us-stocks/scan/status")
def get_us_scan_status():
    last_updated = ""
    if os.path.exists(US_ANALYSIS_CACHE_FILE):
        try:
            mtime = os.path.getmtime(US_ANALYSIS_CACHE_FILE)
            last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        except Exception:
            pass
            
    total_count = us_market_scan_total
    if total_count == 0:
        total_count = len(cached_all_us_stocks) if cached_all_us_stocks else 515
        
    return {
        "active": us_market_scan_active,
        "progress": us_market_scan_progress,
        "total": total_count,
        "last_updated": last_updated,
        "potentials_count": len(potential_us_stocks)
    }

@app.post("/api/stocks/scan")
def trigger_all_market_scan():
    if all_market_scan_active:
        return {"success": False, "message": "Scan already running"}
    run_all_market_scan()
    return {"success": True, "message": "Scan started"}

@app.get("/api/stocks/scan/status")
def get_scan_status():
    last_updated = ""
    if os.path.exists(POTENTIAL_STOCKS_FILE):
        try:
            mtime = os.path.getmtime(POTENTIAL_STOCKS_FILE)
            last_updated = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(mtime))
        except Exception:
            pass
            
    total_count = all_market_scan_total
    if total_count == 0:
        if os.path.exists(ALL_STOCKS_FILE):
            try:
                with open(ALL_STOCKS_FILE, "r", encoding="utf-8") as f:
                    total_count = len(json.load(f))
            except Exception:
                total_count = 2096
        else:
            total_count = 2096
            
    return {
        "active": all_market_scan_active,
        "progress": all_market_scan_progress,
        "total": total_count,
        "last_updated": last_updated
    }

@app.post("/api/stocks/refresh_popular")
def refresh_popular_stocks():
    try:
        from fetch_data import fetch_trending_stocks
        trending = fetch_trending_stocks()
        
        stocks = read_stock_list()
        
        # Discard old popular stocks, keep user-added stocks (manual, web, text, scan, new_popular)
        final_stocks = [s for s in stocks if s.get("added_by") != "popular"]
        final_codes = {s["code"] for s in final_stocks}
        
        # Add new trending stocks
        for s in trending:
            if s["code"] not in final_codes:
                final_codes.add(s["code"])
                final_stocks.append({
                    "code": s["code"],
                    "symbol": s["symbol"],
                    "name": s["name"],
                    "added_by": "popular"
                })
                
        write_stock_list(final_stocks)
        
        # Format names for API return
        formatted = []
        for s in final_stocks:
            item = s.copy()
            item["name"] = format_stock_name(s)
            formatted.append(item)
        return formatted
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"??梢??∪仃?? {str(e)}")

@app.post("/api/stocks/bulk_add")
def bulk_add_stocks(req: BulkAddRequest):
    added_stocks = []
    stocks = read_stock_list()
    
    for code in req.codes:
        code = code.strip()
        if not code.isdigit():
            continue
        if any(s["code"] == code for s in stocks):
            continue
            
        symbol = f"{code}.TW"
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.history(period="5d")
            if info.empty:
                symbol = f"{code}.TWO"
                ticker = yf.Ticker(symbol)
                info = ticker.history(period="5d")
                
            if info.empty:
                continue
                
            from fetch_data import get_stock_name_map
            name = get_stock_name_map().get(code, UNKNOWN_STOCK_NAME)
            
            if name == UNKNOWN_STOCK_NAME:
                url = f"https://tw.stock.yahoo.com/quote/{symbol}"
                headers = {"User-Agent": "Mozilla/5.0"}
                res = requests.get(url, headers=headers, timeout=5)
                if res.status_code == 200:
                    soup = BeautifulSoup(res.content, "lxml")
                    title = soup.title.text if soup.title else ""
                    match_name = re.match(r'^([^\s(]+)', title)
                    if match_name:
                        name = match_name.group(1)
                        
            new_stock = {"code": code, "symbol": symbol, "name": name, "added_by": "text"}
            stocks.append(new_stock)
            added_stocks.append(new_stock)
        except Exception:
            continue
            
    if added_stocks:
        write_stock_list(stocks)
        
    formatted_added = []
    for s in added_stocks:
        item = s.copy()
        item["name"] = format_stock_name(s)
        formatted_added.append(item)
        
    return {"added": formatted_added, "total_added": len(formatted_added)}

class ImportTextRequest(BaseModel):
    text: str

@app.post("/api/stocks/import-text")
def import_text_stocks(req: ImportTextRequest):
    text_content = req.text.strip()
    
    # Extract Taiwan stock codes
    from fetch_data import get_stock_name_map
    stock_map = get_stock_name_map()
    
    matches = re.findall(r"\b\d{4,6}\b", text_content)
    unique_matches = sorted(list(set(matches)))
    
    valid_codes = [c for c in unique_matches if c in stock_map]
    
    stocks = read_stock_list()
    
    total_found = len(valid_codes)
    duplicates_count = 0
    to_validate = []
    
    for code in valid_codes:
        if any(s["code"] == code for s in stocks):
            duplicates_count += 1
        else:
            to_validate.append(code)
            
    added_count = 0
    added_list = []
    
    if to_validate:
        def validate_tw_code(code):
            for suffix in (".TW", ".TWO"):
                symbol = f"{code}{suffix}"
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.history(period="5d", timeout=5)
                    if not info.empty:
                        return code, symbol, True
                except Exception:
                    pass
            return code, None, False
            
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = executor.map(validate_tw_code, to_validate)
            for code, symbol, is_valid in results:
                if is_valid:
                    name = stock_map.get(code, UNKNOWN_STOCK_NAME)
                    new_stock = {"code": code, "symbol": symbol, "name": name, "added_by": "text"}
                    stocks.append(new_stock)
                    added_list.append(new_stock)
                    added_count += 1
                    
    if added_list:
        write_stock_list(stocks)
        
    return {
        "success": True,
        "total_found": total_found,
        "duplicates": duplicates_count,
        "added": added_count
    }

@app.post("/api/us-stocks/import-text")
def import_text_us_stocks(req: ImportTextRequest):
    text_content = req.text.strip()
    
    # Extract US stock tickers: 1-5 letters
    matches = re.findall(r"\b[A-Z]{1,5}\b", text_content)
    unique_matches = sorted(list(set(matches)))
    
    # Filter out common English grammar words to avoid noise
    GRAMMAR_WORDS = {
        "THE", "AND", "OR", "BUT", "FOR", "OF", "TO", "IN", "ON", "AT", "BY", "AN", "IS", "AM", "ARE", "WAS", "WERE", 
        "BE", "BEING", "BEEN", "HAVE", "HAS", "HAD", "DO", "DOES", "DID", "IT", "ITS", "THEY", "THEM", "THEIR", 
        "THIS", "THAT", "THESE", "THOSE", "WHO", "WHICH", "WHAT", "IF", "THEN", "ELSE", "WITH", "FROM", "ABOUT", 
        "INTO", "OVER", "AFTER", "US"
    }
    candidate_tickers = [t for t in unique_matches if t not in GRAMMAR_WORDS]
    
    # Get all known US stock symbols from our cache and default list
    known_symbols = {}
    
    global cached_all_us_stocks
    if not cached_all_us_stocks:
        try:
            cached_all_us_stocks = fetch_all_us_stocks()
        except Exception:
            cached_all_us_stocks = []
            
    for s in cached_all_us_stocks:
        known_symbols[s["symbol"].upper()] = s["name"]
        
    for s in DEFAULT_US_STOCKS:
        known_symbols[s["symbol"].upper()] = s["name"]
        
    stocks = read_us_stock_list()
    
    total_found = 0
    duplicates_count = 0
    to_validate = []
    
    for symbol in candidate_tickers:
        if any(str(s.get("code", "")).upper() == symbol for s in stocks):
            total_found += 1
            duplicates_count += 1
        elif symbol in known_symbols:
            total_found += 1
            # Mark it for addition directly using its known name
            to_validate.append((symbol, True, known_symbols[symbol]))
        else:
            # Mark for online validation
            to_validate.append((symbol, False, None))
            
    added_count = 0
    added_list = []
    
    if to_validate:
        def validate_us_ticker(item):
            symbol, is_known, name = item
            if is_known:
                return symbol, True, name
            try:
                ticker = yf.Ticker(symbol)
                df = ticker.history(period="1d", timeout=5)
                if not df.empty:
                    return symbol, True, symbol
            except Exception:
                pass
            return symbol, False, None
            
        with ThreadPoolExecutor(max_workers=30) as executor:
            results = executor.map(validate_us_ticker, to_validate)
            for symbol, is_valid, name in results:
                if is_valid:
                    if name is None:
                        name = symbol
                    total_found += 1
                    new_stock = {
                        "code": symbol,
                        "symbol": symbol,
                        "name": name,
                        "category": "檔案加入",
                        "market": "US",
                        "added_by": "text"
                    }
                    stocks.append(new_stock)
                    added_list.append(new_stock)
                    added_count += 1
                    
    if added_list:
        write_us_stock_list(stocks)
        
    return {
        "success": True,
        "total_found": total_found,
        "duplicates": duplicates_count,
        "added": added_count
    }

# -------------------------------------------------------
# Lists Sync Endpoints (Cross-device stock list sync)
# -------------------------------------------------------
def read_monitor_list():
    if not os.path.exists(MONITOR_FILE):
        return []
    try:
        with open(MONITOR_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def write_monitor_list(data: list):
    with open(MONITOR_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def read_trailing_list():
    if not os.path.exists(TRAILING_FILE):
        return []
    try:
        with open(TRAILING_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def write_trailing_list(data: list):
    with open(TRAILING_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def normalize_order_names(items: list):
    for item in items:
        code = str(item.get("code", "")).strip().upper()
        item["code"] = code
        if item.get("symbol"):
            item["symbol"] = str(item["symbol"]).upper()
        if str(item.get("market", "TW")).upper() == "US":
            profile = us_company_profiles.get(item.get("symbol") or code, {})
            item["name"] = profile.get("name_en") or item.get("name") or code
            item["name_zh"] = profile.get("name_zh") or item.get("name_zh", "")
            item["industry"] = profile.get("business_zh") or item.get("industry", "")
            item["group_category"] = profile.get("group_category") or item.get("group_category", "")
            item["concepts"] = profile.get("concepts") or item.get("concepts", [])
        else:
            item["name"] = resolve_stock_name(code, item.get("name"))
            item["industry"] = repair_mojibake(item.get("industry"))
            if not item["industry"]:
                try:
                    item["industry"] = get_yahoo_tw_business_desc(code)
                except Exception:
                    item["industry"] = ""
            group_info = infer_tw_group(code, item.get("name"), item.get("industry"))
            item["group_category"] = group_info["group_category"]
            item["concepts"] = group_info["concepts"]
    return items

def normalize_stock_names(items: list):
    for item in items:
        item["name"] = resolve_stock_name(item.get("code"), item.get("name"))
    return items

def sync_connector_lists():
    connector = SinoPacConnector.get_instance()
    if getattr(connector, "trailing_orders", []):
        existing_ids = {item.get("order_id") for item in connector.orders}
        for item in connector.trailing_orders:
            item["status"] = item.get("status") or "MONITORING"
            item["control_mode"] = "TRAILING"
            if item.get("order_id") not in existing_ids:
                connector.orders.append(item)
        connector.trailing_orders = []
    connector.orders = getattr(connector, "orders", [])
    connector.trailing_orders = getattr(connector, "trailing_orders", [])
    write_monitor_list(connector.orders)
    write_trailing_list(connector.trailing_orders)
    connector.save_orders()

@app.get("/api/lists")
def get_lists():
    """Return current stock list and monitor list so all devices stay in sync."""
    stocks = normalize_stock_names(read_stock_list())
    connector = SinoPacConnector.get_instance()
    if getattr(connector, "trailing_orders", []):
        sync_connector_lists()
    monitor_names_before = [item.get("name") for item in getattr(connector, "orders", [])]
    trailing_names_before = [item.get("name") for item in getattr(connector, "trailing_orders", [])]
    monitors = normalize_order_names(getattr(connector, "orders", []) or read_monitor_list())
    trailings = normalize_order_names(getattr(connector, "trailing_orders", []) or read_trailing_list())
    monitor_names_after = [item.get("name") for item in monitors]
    trailing_names_after = [item.get("name") for item in trailings]
    if monitor_names_before != monitor_names_after or trailing_names_before != trailing_names_after:
        connector.orders = monitors
        connector.trailing_orders = trailings
        sync_connector_lists()
    
    # Populate industry if missing
    for o in monitors:
        if "industry" not in o or not o["industry"]:
            try:
                o["industry"] = get_yahoo_tw_business_desc(o["code"])
            except Exception:
                pass
    for o in trailings:
        if "industry" not in o or not o["industry"]:
            try:
                o["industry"] = get_yahoo_tw_business_desc(o["code"])
            except Exception:
                pass
                
    return {
        "stockList": stocks,
        "monitorList": monitors,
        "trailingList": trailings
    }

@app.post("/api/lists")
def save_lists(req: SaveListsRequest):
    """Save the full stock list and monitor list sent from any device."""
    try:
        for s in req.stockList:
            if "added_by" not in s:
                s["added_by"] = "popular"
                
        monitor_list = normalize_order_names(req.monitorList)
        trailing_list = normalize_order_names(req.trailingList)
        for item in trailing_list:
            item["control_mode"] = "TRAILING"
            if not any(existing.get("order_id") == item.get("order_id") for existing in monitor_list):
                monitor_list.append(item)
        trailing_list = []
        connector = SinoPacConnector.get_instance()
        existing_us_orders = [
            item for item in connector.orders
            if str(item.get("market", "TW")).upper() == "US"
        ]
        submitted_ids = {item.get("order_id") for item in monitor_list}
        monitor_list.extend(
            item for item in existing_us_orders
            if item.get("order_id") not in submitted_ids
        )
        trailing_codes = {str(item.get("code", "")).upper() for item in trailing_list}
        trailing_source_ids = {
            item.get("source_order_id") or item.get("order_id")
            for item in trailing_list
        }
        monitor_list = [
            item for item in monitor_list
            if str(item.get("code", "")).upper() not in trailing_codes
            and item.get("order_id") not in trailing_source_ids
        ]
        stock_list = normalize_stock_names(req.stockList)
        write_stock_list(stock_list)
        write_monitor_list(monitor_list)
        write_trailing_list(trailing_list)
        
        # Sync to mock SinoPacConnector database
        connector.orders = monitor_list
        connector.trailing_orders = trailing_list
        connector.save_orders()
        
        return {"ok": True}
    except Exception as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=500, detail=str(e))

# SinoPac Settings Endpoints (Mock/Simulated)
@app.get("/api/sinopac/status")
def get_sinopac_status():
    connector = SinoPacConnector.get_instance()
    return {
        "enabled": connector.enabled,
        "is_logged_in": connector.is_logged_in,
        "api_key": "YahooFinance",
        "person_id": connector.person_id if connector.person_id else "SimulatedUser",
        "has_ca": True
    }

@app.post("/api/sinopac/setup")
def setup_sinopac(req: SinoPacSetupRequest):
    connector = SinoPacConnector.get_instance()
    success, message = connector.login(
        person_id=req.person_id,
        enabled=req.enabled
    )
    return {
        "success": True,
        "message": "Sinopac login succeeded",
        "status": {
            "enabled": connector.enabled,
            "is_logged_in": connector.is_logged_in
        }
    }

@app.post("/api/sinopac/disable")
def disable_sinopac():
    connector = SinoPacConnector.get_instance()
    connector.disable()
    return {
        "success": True,
        "message": "Sinopac disabled",
    }

@app.post("/api/sinopac/order")
def place_order_endpoint(req: PlaceOrderRequest):
    connector = SinoPacConnector.get_instance()
    market = str(req.market or "TW").upper()
    code = req.code.upper() if market == "US" else req.code
    
    stocks = read_stock_list()
    stock = next((s for s in stocks if s["code"] == code), None)
    if market == "US":
        stock = next((s for s in read_us_stock_list() if s["code"] == code), None)
    if market == "US":
        profile = us_company_profiles.get(code, {}) or {
            "name_en": (stock or {}).get("name") or code,
            "name_zh": US_COMMON_NAMES_ZH.get(code, ""),
            "business_zh": "",
            "group_category": "",
            "concepts": [],
        }
        name = profile.get("name_en") or (stock or {}).get("name") or code
    else:
        profile = {}
        name = resolve_stock_name(code, stock["name"] if stock else None)
    if stock and market != "US":
        name = format_stock_name({**stock, "name": name})
    
    industry = ""
    if market == "US":
        industry = profile.get("business_zh", "")
        group_info = {
            "group_category": profile.get("group_category", ""),
            "concepts": profile.get("concepts", []),
        }
    else:
        try:
            industry = get_yahoo_tw_business_desc(code)
        except Exception:
            pass
        group_info = infer_tw_group(code, name, industry)

    try:
        res = connector.place_odd_lot_order(
            code=code,
            action=req.action,
            price=req.price,
            quantity=req.quantity,
            lot_type=req.lot_type,
            dry_run=req.dry_run
        )
        
        new_order = {
            "code": code,
            "symbol": code if market == "US" else (f"{code}.TW" if not stock else stock["symbol"]),
            "name": name,
            "industry": industry,
            "action": req.action,
            "buy_price": req.price,
            "quantity": req.quantity,
            "stop_loss_price": req.stop_loss_price,
            "stop_profit_price": req.stop_profit_price,
            "lot_type": req.lot_type,
            "status": "MONITORING",
            "order_id": res["order_id"],
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "last_price": req.price,
            "dry_run": req.dry_run,
            "trigger_order_id": None,
            "message": "simulated risk order",
            "market": market,
            "name_zh": profile.get("name_zh", "") if market == "US" else "",
            "group_category": group_info.get("group_category", ""),
            "concepts": group_info.get("concepts", []),
        }
        
        connector.orders.append(new_order)
        sync_connector_lists()
        
        lot_text = "?嗉" if req.lot_type == "ODD" else "?渲"
        return {
            "success": True,
            "message": f"simulated order placed: {lot_text}",
            "order": new_order
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail="No market data available for this symbol")

@app.get("/api/sinopac/orders")
def get_orders_endpoint(market: Optional[str] = None):
    connector = SinoPacConnector.get_instance()
    updated_tw = False
    updated_us = False
    if market is None or market.upper() == "TW":
        updated_tw = refresh_tw_monitor_quotes(connector.orders)
    if market is None or market.upper() == "US":
        updated_us = refresh_us_monitor_quotes(connector.orders)
    if updated_tw or updated_us:
        sync_connector_lists()
    # Keep this endpoint fast: repair stored text only; do not scrape profiles
    # for every order whenever the risk list refreshes.
    for item in connector.orders:
        item["name"] = resolve_stock_name(item.get("code"), repair_mojibake(item.get("name")))
        item["industry"] = repair_mojibake(item.get("industry"))
    if market:
        requested = market.upper()
        return [item for item in connector.orders if str(item.get("market", "TW")).upper() == requested]
    return connector.orders

@app.post("/api/sinopac/orders/{code}/cancel")
def cancel_order_endpoint(code: str):
    connector = SinoPacConnector.get_instance()
    cancelled_count = 0
    for o in connector.orders:
        if o["code"] == code and o["status"] == "MONITORING":
            o["status"] = "CANCELLED"
            o["message"] = "monitor cancelled"
            cancelled_count += 1
            
    if cancelled_count > 0:
        sync_connector_lists()
        return {"success": True, "message": "cancelled"}
    else:
        raise HTTPException(status_code=404, detail=f"?曆??唬誨??{code} 銝??銝剔?隞餃?")

@app.delete("/api/sinopac/orders/{order_id}")
def delete_order_endpoint(order_id: str):
    connector = SinoPacConnector.get_instance()
    initial_len = len(connector.orders)
    connector.orders = [o for o in connector.orders if o.get("order_id") != order_id]
    
    if len(connector.orders) < initial_len:
        sync_connector_lists()
        return {"success": True, "message": "deleted"}
    else:
        raise HTTPException(status_code=404, detail="order not found")

@app.post("/api/sinopac/orders/{order_id}/update")
def update_order_endpoint(order_id: str, req: UpdateOrderRequest):
    connector = SinoPacConnector.get_instance()
    for o in connector.orders + connector.trailing_orders:
        if o.get("order_id") == order_id:
            if req.buy_price is not None:
                o["buy_price"] = req.buy_price
            if req.quantity is not None:
                o["quantity"] = req.quantity
            if req.stop_loss_price is not None:
                o["stop_loss_price"] = req.stop_loss_price
            if req.stop_profit_price is not None:
                o["stop_profit_price"] = req.stop_profit_price
            sync_connector_lists()
            return {"success": True, "message": "updated"}
    raise HTTPException(status_code=404, detail="order not found")


@app.post("/api/sinopac/orders/{order_id}/toggle-action")
def toggle_order_action_endpoint(order_id: str, req: ToggleOrderActionRequest):
    connector = SinoPacConnector.get_instance()
    if req.action not in ["BUY", "NOT_BUY"]:
        raise HTTPException(status_code=400, detail="invalid action")
    for o in connector.orders:
        if o.get("order_id") == order_id:
            o["action"] = req.action
            sync_connector_lists()
            return {"success": True, "message": "action updated", "action": req.action}
    raise HTTPException(status_code=404, detail="order not found")

@app.post("/api/sinopac/orders/{order_id}/move-to-trailing")
def move_order_to_trailing_endpoint(order_id: str, req: MoveToTrailingRequest):
    connector = SinoPacConnector.get_instance()
    source = next((item for item in connector.orders if item.get("order_id") == order_id), None)
    if not source:
        existing = next(
            (item for item in connector.trailing_orders if item.get("source_order_id") == order_id),
            None,
        )
        if existing:
            return {"success": True, "order": existing, "already_moved": True}
        raise HTTPException(status_code=404, detail="order not found")
    if source.get("action") != "BUY":
        raise HTTPException(status_code=400, detail="only purchased stocks can use trailing control")

    code = str(source.get("code", "")).upper()
    trailing_order = {
        **source,
        "code": code,
        "symbol": str(source.get("symbol") or f"{code}.TW").upper(),
        "name": resolve_stock_name(code, source.get("name")),
        "source_order_id": order_id,
        "order_id": f"T-{int(time.time() * 1000)}",
        "original_stop_loss": source.get("stop_loss_price"),
        "original_take_profit": source.get("stop_profit_price"),
        "stop_loss_price": req.stop_loss_price,
        "stop_profit_price": req.stop_profit_price,
        "trailing_reference": req.trailing_reference,
        "status": "MONITORING",
        "trigger_order_id": None,
    }

    connector.orders = [
        item for item in connector.orders
        if item.get("order_id") != order_id
        and str(item.get("code", "")).upper() != code
    ]
    connector.trailing_orders = [
        item for item in connector.trailing_orders
        if str(item.get("code", "")).upper() != code
    ]
    connector.trailing_orders.append(trailing_order)
    monitor_signal_cache["updated_at"] = 0.0
    sync_connector_lists()
    return {"success": True, "order": trailing_order}

def fetch_institutional_data(symbol):
    url = f"https://tw.stock.yahoo.com/quote/{symbol}/institutional-trading"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return []
        html = response.text
        match = re.search(r'root\.App\.main\s*=\s*(.*?);\s*\(function', html, re.DOTALL)
        if not match:
            match = re.search(r'root\.App\.main\s*=\s*(.*?);\n', html, re.DOTALL)
            
        if match:
            json_str = match.group(1)
            json_str = re.sub(r':\s*undefined', ': null', json_str)
            json_str = re.sub(r':\s*NaN', ': null', json_str)
            data = json.loads(json_str)
            
            stores = data.get("context", {}).get("dispatcher", {}).get("stores", {})
            chip_store = stores.get("QuoteChipStore", {})
            data_key = chip_store.get("institutionBuySellDataKey", f"institutionBuySell-100-day-{symbol}")
            
            trades = chip_store.get(data_key, {}).get("data", {}).get("trades", [])
            if not trades:
                return []
                
            result = []
            for t in trades:
                date_val = t.get("date", "")[:10]
                if not date_val:
                    continue
                result.append({
                    "date": date_val,
                    "foreign_buy": float(t.get("foreignBuyVolK") or 0.0),
                    "foreign_sell": float(t.get("foreignSellVolK") or 0.0),
                    "foreign": float(t.get("foreignDiffVolK") or 0.0),
                    "trust_buy": float(t.get("investmentTrustBuyVolK") or 0.0),
                    "trust_sell": float(t.get("investmentTrustSellVolK") or 0.0),
                    "trust": float(t.get("investmentTrustDiffVolK") or 0.0),
                    "dealer_buy": float(t.get("dealerBuyVolK") or 0.0),
                    "dealer_sell": float(t.get("dealerSellVolK") or 0.0),
                    "dealer": float(t.get("dealerDiffVolK") or 0.0),
                    "total_diff": float(t.get("totalDiffVolK") or 0.0),
                })
            return result[-60:]
    except Exception as e:
        print(f"Error fetching institutional data from Yahoo for {symbol}: {e}", flush=True)
    return []

MAJOR_HOLDER_STORE_FILE = os.path.join(os.path.dirname(__file__), "major_holders_store.json")
major_holders_store = {}
if os.path.exists(MAJOR_HOLDER_STORE_FILE):
    try:
        with open(MAJOR_HOLDER_STORE_FILE, "r", encoding="utf-8") as f:
            major_holders_store = json.load(f)
    except Exception as e:
        print(f"Failed to load major holders store: {e}", flush=True)

def save_major_holders_store():
    try:
        with open(MAJOR_HOLDER_STORE_FILE, "w", encoding="utf-8") as f:
            json.dump(major_holders_store, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Failed to save major holders store: {e}", flush=True)

def fetch_major_holder_data(symbol):
    if not symbol.endswith((".TW", ".TWO")):
        return []
    code = symbol.split(".")[0].upper()
    
    # Check if cached and within throttle limit (12 hours = 43200 seconds)
    now = time.time()
    meta_key = f"_meta_{code}"
    meta = major_holders_store.get(meta_key, {})
    last_checked = meta.get("last_checked", 0.0)
    cached_list = major_holders_store.get(code, [])
    if cached_list and (now - last_checked < 43200):
        return sorted(cached_list, key=lambda x: x["date"])

    base_url = "https://www.tdcc.com.tw/portal/zh/smWeb/qryStock"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        session = requests.Session()
        first = session.get(base_url, headers=headers, timeout=20)
        soup = BeautifulSoup(first.text, "html.parser")
        date_options = [option.get("value") for option in soup.select('select[name="scaDate"] option') if option.get("value")]
        if not date_options:
            cached_list = major_holders_store.get(code, [])
            return sorted(cached_list, key=lambda x: x["date"])
            
        selected_dates = date_options[:52]
        existing_records = major_holders_store.get(code, [])
        existing_by_tdcc_date = {r["date"].replace("-", ""): r for r in existing_records}
        
        missing_dates = [d for d in selected_dates if d not in existing_by_tdcc_date]
        
        if missing_dates:
            # Sort descending (newest first) and limit to top 26 to avoid overload/timeouts on first fetch
            missing_dates = sorted(missing_dates, reverse=True)[:26]
            print(f"Fetching {len(missing_dates)} missing TDCC major holder dates for {code}: {missing_dates}", flush=True)
            
            token = soup.select_one('input[name="SYNCHRONIZER_TOKEN"]')
            uri = soup.select_one('input[name="SYNCHRONIZER_URI"]')
            
            def fetch_week(date_value):
                local = requests.Session()
                page = local.get(base_url, headers=headers, timeout=15)
                form = BeautifulSoup(page.text, "html.parser")
                local_token = form.select_one('input[name="SYNCHRONIZER_TOKEN"]')
                local_uri = form.select_one('input[name="SYNCHRONIZER_URI"]')
                
                response = local.post(base_url, headers=headers, data={
                    "SYNCHRONIZER_TOKEN": local_token.get("value", "") if local_token else "",
                    "SYNCHRONIZER_URI": local_uri.get("value", "") if local_uri else "",
                    "method": "submit", "firDate": date_value, "scaDate": date_value,
                    "sqlMethod": "StockNo", "stockNo": code, "stockName": "",
                }, timeout=15)
                
                parsed = BeautifulSoup(response.text, "html.parser")
                major_ratio = None
                retail_ratio = 0.0
                retail_rows_found = 0
                for row in parsed.select("table tr"):
                    cells = [cell.get_text(" ", strip=True) for cell in row.select("td")]
                    if len(cells) < 5:
                        continue
                    level = cells[0]
                    try:
                        ratio = float(cells[4].replace(",", ""))
                    except (TypeError, ValueError):
                        continue
                    if level in {"1", "2", "3"}:
                        retail_ratio += ratio
                        retail_rows_found += 1
                    elif level == "15":
                        major_ratio = ratio
                if major_ratio is not None:
                    return {
                        "date": f"{date_value[:4]}-{date_value[4:6]}-{date_value[6:]}",
                        "ratio": major_ratio,
                        "retail_ratio": round(retail_ratio, 2) if retail_rows_found == 3 else None,
                    }
                return None

            with ThreadPoolExecutor(max_workers=5) as executor:
                new_records = [item for item in executor.map(fetch_week, missing_dates) if item]
                
            if new_records:
                if code not in major_holders_store:
                    major_holders_store[code] = []
                store_by_date = {r["date"]: r for r in major_holders_store[code]}
                for nr in new_records:
                    store_by_date[nr["date"]] = nr
                major_holders_store[code] = list(store_by_date.values())
                
        # Update meta stamp even if no new records were found, since we successfully checked TDCC
        major_holders_store[meta_key] = {"last_checked": now}
        save_major_holders_store()
                
        result = []
        updated_records = major_holders_store.get(code, [])
        updated_by_tdcc_date = {r["date"].replace("-", ""): r for r in updated_records}
        for d in selected_dates:
            if d in updated_by_tdcc_date:
                result.append(updated_by_tdcc_date[d])
                
        result.sort(key=lambda item: item["date"])
        return result
    except Exception as error:
        print(f"TDCC major holder fetch failed for {code}: {error}", flush=True)
        cached_list = major_holders_store.get(code, [])
        return sorted(cached_list, key=lambda x: x["date"])


single_quote_cache = {}

def get_cached_stock_price(code):
    code_str = str(code).strip().upper()
    # Check potential_stocks list
    for s in potential_stocks:
        if str(s.get("code", "")).strip().upper() == code_str:
            return s.get("current_price"), s.get("reference_price")
    # Check TW_ANALYSIS_CACHE_FILE
    if os.path.exists(TW_ANALYSIS_CACHE_FILE):
        try:
            with open(TW_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                cache_data = json.load(file)
            for item in cache_data:
                if str(item.get("code", "")).strip().upper() == code_str:
                    return item.get("current_price"), item.get("reference_price")
        except Exception:
            pass
    return None, None

@app.get("/api/stocks/{code}/quote")
def get_stock_quote(code: str):
    code_upper = code.upper()
    is_us = not re.match(r"^\d", str(code))
    
    # Caching check
    now = time.time()
    market_open = is_us_market_open() if is_us else is_tw_market_open()
    
    if not market_open:
        # Check cache
        last_close = get_last_market_close("US" if is_us else "TW")
        cached = single_quote_cache.get(code_upper)
        if cached and cached.get("checked_at", 0.0) >= last_close.timestamp():
            return cached["data"]
            
        # Try to get from analysis cache if available to avoid any network fetch
        if not is_us:
            c_price, r_price = get_cached_stock_price(code)
            if c_price is not None:
                q_data = clean_nan({
                    "code": code,
                    "symbol": f"{code}.TW",
                    "open": c_price,
                    "reference": r_price,
                    "close": c_price,
                    "high": c_price,
                    "low": c_price,
                    "volume_lots": 0,
                    "quote_time": "13:30:00",
                    "source": "AnalysisCache",
                })
                single_quote_cache[code_upper] = {
                    "checked_at": now,
                    "data": q_data
                }
                return q_data
        else:
            # Check US analysis cache for US stocks
            if os.path.exists(US_ANALYSIS_CACHE_FILE):
                try:
                    with open(US_ANALYSIS_CACHE_FILE, "r", encoding="utf-8") as file:
                        cache_data = json.load(file)
                    for item in cache_data:
                        if str(item.get("code", "")).strip().upper() == code_upper:
                            c_price = item.get("current_price")
                            r_price = item.get("reference_price")
                            if c_price is not None:
                                q_data = clean_nan({
                                    "code": code,
                                    "symbol": item.get("symbol", code_upper),
                                    "open": c_price,
                                    "reference": r_price,
                                    "close": c_price,
                                    "high": c_price,
                                    "low": c_price,
                                    "volume_lots": 0,
                                    "quote_time": "16:00:00",
                                    "source": "AnalysisCache",
                                })
                                single_quote_cache[code_upper] = {
                                    "checked_at": now,
                                    "data": q_data
                                }
                                return q_data
                except Exception:
                    pass

    # If we get here, we either are in market hours, or cache is missing/expired.
    # Proceed to fetch from internet...
    if not is_us:
        stocks = read_stock_list()
        stock = next((s for s in stocks if s["code"] == code), None)
        if not stock:
            stock = next((s for s in potential_stocks if s["code"] == code), None)
        if not stock:
            stock = {"code": code, "symbol": f"{code}.TW"}
            
        official = fetch_twse_realtime_quotes([stock]).get(str(code).upper())
        if official and official.get("price") is not None:
            q_data = clean_nan({
                "code": code,
                "symbol": stock.get("symbol", f"{code}.TW"),
                "open": official.get("open"),
                "reference": official.get("reference"),
                "close": official.get("price"),
                "high": official.get("high"),
                "low": official.get("low"),
                "volume_lots": int(official.get("volume") or 0),
                "quote_time": official.get("time"),
                "source": official.get("source"),
                "limit_up": official.get("limit_up"),
                "limit_down": official.get("limit_down"),
            })
            single_quote_cache[code_upper] = {
                "checked_at": now,
                "data": q_data
            }
            return q_data

    # For US stocks or TW fallback
    symbol = code_upper if is_us else f"{code}.TW"
    try:
        ticker = yf.Ticker(symbol)
        # Use history with auto_adjust=False to prevent adjusted close overriding actual close!
        df = ticker.history(period="2d", auto_adjust=False)
        if not df.empty:
            df = df.dropna(subset=["Open", "Close"])
        if df.empty and not is_us:
            # Try TWO if TW fails
            symbol = f"{code}.TWO"
            ticker = yf.Ticker(symbol)
            df = ticker.history(period="2d", auto_adjust=False)
            if not df.empty:
                df = df.dropna(subset=["Open", "Close"])
                
        if df.empty:
            raise Exception("No quote data found for symbol")
            
        if len(df) >= 2:
            ref_price = float(df['Close'].iloc[-2])
            open_price = float(df['Open'].iloc[-1])
            close_price = float(df['Close'].iloc[-1])
        else:
            close_price = float(df['Close'].iloc[-1])
            open_price = float(df['Open'].iloc[-1])
            ref_price = open_price
            
        q_data = clean_nan({
            "code": code,
            "symbol": symbol,
            "open": open_price,
            "reference": ref_price,
            "close": close_price,
            "high": float(df['High'].iloc[-1]) if 'High' in df.columns else close_price,
            "low": float(df['Low'].iloc[-1]) if 'Low' in df.columns else close_price,
            "volume_lots": int(df['Volume'].iloc[-1] // 1000) if 'Volume' in df.columns else 0,
            "quote_time": datetime.datetime.now().strftime("%H:%M:%S"),
            "source": "yfinance"
        })
        single_quote_cache[code_upper] = {
            "checked_at": now,
            "data": q_data
        }
        return q_data
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/stocks/{code}/chart-data")
def get_stock_chart_data(code: str, force: bool = False):
    stocks = read_stock_list()
    stock = next((s for s in stocks if s["code"] == code), None)
    if not stock:
        # Check potential stocks list
        stock = next((s for s in potential_stocks if s["code"] == code), None)
    if not stock:
        stock = next((s for s in read_us_stock_list() if s["code"] == code.upper()), None)
    if not stock:
        if len(code) == 4 and code.isdigit():
            symbol = f"{code}.TW"
            ticker = yf.Ticker(symbol)
            try:
                info = ticker.history(period="1d")
                if info.empty:
                    symbol = f"{code}.TWO"
            except Exception:
                symbol = f"{code}.TWO"
            from fetch_data import get_stock_name_map
            name = get_stock_name_map().get(code, UNKNOWN_STOCK_NAME)
            stock = {"code": code, "symbol": symbol, "name": name}
        else:
            stock = {"code": code.upper(), "symbol": code.upper(), "name": code.upper(), "market": "US"}
        
    symbol = stock["symbol"]
    is_us = stock.get("market") == "US" or not re.match(r"^\d", str(code))
    import datetime
    tz_offset = datetime.timezone(datetime.timedelta(hours=8))
    now_tw = datetime.datetime.now(tz_offset)
    if is_us:
        from zoneinfo import ZoneInfo
        ny_timezone = ZoneInfo("America/New_York")
        taipei_timezone = ZoneInfo("Asia/Taipei")
        now_market = datetime.datetime.now(ny_timezone)
        is_intraday = now_market.weekday() < 5 and (datetime.time(9, 30) <= now_market.time() < datetime.time(16, 0))
        market_date = now_market.strftime("%Y-%m-%d")
    else:
        is_intraday = now_tw.weekday() < 5 and (datetime.time(9, 0) <= now_tw.time() < datetime.time(13, 30))
        market_date = now_tw.strftime("%Y-%m-%d")
    cache_key = f"{'US' if is_us else 'TW'}:{str(code).upper()}"
    cached = chart_data_cache.get(cache_key)
    if cached and not force:
        # Outside trading hours, only reuse a snapshot that was built as a completed session.
        if not is_intraday and cached.get("market_complete"):
            return cached["data"]
        # During trading hours, allow reusing cache if it is less than 120 seconds old.
        if is_intraday and (time.time() - cached.get("updated_at", 0.0) < 120):
            return cached["data"]
    try:
        ticker = yf.Ticker(symbol)
        official_quote = None if is_us else fetch_twse_realtime_quotes([stock]).get(str(code).upper())
        
        # Fetch intraday, daily, and hourly history in parallel to speed up loading
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_intra = executor.submit(ticker.history, period="5d", interval="1m")
            future_daily = executor.submit(ticker.history, period="6mo", interval="1d", auto_adjust=False)
            future_hourly = executor.submit(ticker.history, period="2mo", interval="60m", auto_adjust=False)
            
            df_intra = future_intra.result()
            df_daily = future_daily.result()
            df_hourly = future_hourly.result()
            
        if not df_intra.empty:
            df_intra = df_intra.dropna(subset=["Close"])
        intraday_data = []
        prev_intraday_data = []
        latest_date = ""
        prev_date = ""
        intraday_session = None
        prev_intraday_session = None
        if not df_intra.empty:
            def market_datetime(index_value):
                if not is_us:
                    return index_value
                if index_value.tzinfo is None:
                    return index_value.tz_localize(ny_timezone)
                return index_value.tz_convert(ny_timezone)

            def session_metadata(date_str):
                if not is_us or not date_str:
                    return {
                        "timezone": "Asia/Taipei",
                        "label": "台灣時間",
                        "start": "09:00",
                        "end": "13:30",
                        "is_dst": False,
                    }
                session_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                start_ny = datetime.datetime.combine(session_date, datetime.time(9, 30), tzinfo=ny_timezone)
                end_ny = datetime.datetime.combine(session_date, datetime.time(16, 0), tzinfo=ny_timezone)
                start_tw = start_ny.astimezone(taipei_timezone)
                end_tw = end_ny.astimezone(taipei_timezone)
                return {
                    "timezone": "Asia/Taipei",
                    "label": "台灣時間",
                    "start": start_tw.strftime("%H:%M"),
                    "end": end_tw.strftime("%H:%M"),
                    "is_dst": bool(start_ny.dst()),
                    "market_timezone": "America/New_York",
                    "market_start": "09:30",
                    "market_end": "16:00",
                }

            df_intra['market_dt'] = [market_datetime(index_value) for index_value in df_intra.index]
            if is_us:
                df_intra = df_intra[
                    df_intra['market_dt'].map(
                        lambda value: datetime.time(9, 30) <= value.time() <= datetime.time(16, 0)
                    )
                ]
            df_intra['date_str'] = df_intra['market_dt'].map(lambda x: x.strftime("%Y-%m-%d"))
            unique_dates = sorted(df_intra['date_str'].unique())
            
            if len(unique_dates) >= 1:
                latest_date = unique_dates[-1]
                intraday_session = session_metadata(latest_date)
                df_latest = df_intra[df_intra['date_str'] == latest_date]
                for idx, row in df_latest.iterrows():
                    market_dt = row["market_dt"]
                    display_dt = market_dt.astimezone(taipei_timezone) if is_us else market_dt
                    minute_index = (
                        (market_dt.hour * 60 + market_dt.minute) - (9 * 60 + 30)
                        if is_us else None
                    )
                    intraday_data.append({
                        "time": display_dt.strftime("%H:%M"),
                        "market_time": market_dt.strftime("%H:%M"),
                        "minute_index": minute_index,
                        "price": float(row["Close"]),
                        "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                    })
                    
            if len(unique_dates) >= 2:
                prev_date = unique_dates[-2]
                prev_intraday_session = session_metadata(prev_date)
                df_prev = df_intra[df_intra['date_str'] == prev_date]
                for idx, row in df_prev.iterrows():
                    market_dt = row["market_dt"]
                    display_dt = market_dt.astimezone(taipei_timezone) if is_us else market_dt
                    minute_index = (
                        (market_dt.hour * 60 + market_dt.minute) - (9 * 60 + 30)
                        if is_us else None
                    )
                    prev_intraday_data.append({
                        "time": display_dt.strftime("%H:%M"),
                        "market_time": market_dt.strftime("%H:%M"),
                        "minute_index": minute_index,
                        "price": float(row["Close"]),
                        "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                    })

        # 2. Daily K-line (last 60 days) with SMA5, SMA20, and BBAND (Bollinger Bands)
        # df_daily is already fetched in parallel at the start of get_stock_chart_data
        if not is_us:
            df_daily = ensure_tw_daily_history(df_daily, code, 12)
        df_daily, split_events = normalize_unreported_split(df_daily, code if not is_us else None)
        if not df_daily.empty:
            df_daily = df_daily.dropna(subset=["Open", "High", "Low", "Close"])

        # Ensure today/recent trading day's daily bar is present in df_daily
        if not df_daily.empty and latest_date:
            daily_dates = df_daily.index.map(lambda value: value.strftime("%Y-%m-%d"))
            matching = df_daily.index[daily_dates == latest_date]
            
            # Fetch default values from intraday data
            f_open = None
            f_high = None
            f_low = None
            f_close = None
            f_volume = 0
            if intraday_data:
                prices = [float(x["price"]) for x in intraday_data if x.get("price") is not None]
                if prices:
                    f_open = prices[0]
                    f_close = prices[-1]
                    f_high = max(prices)
                    f_low = min(prices)
                f_volume = sum(int(x["volume"]) for x in intraday_data if x.get("volume") is not None)
            
            # If official_quote is available and matches latest_date, update
            if not is_us and official_quote and official_quote.get("price") is not None:
                quote_date = str(official_quote.get("date") or "")
                quote_date = (
                    f"{quote_date[:4]}-{quote_date[4:6]}-{quote_date[6:8]}"
                    if len(quote_date) == 8 else latest_date
                )
                if quote_date == latest_date:
                    f_close = official_quote["price"]
                    if official_quote.get("open") is not None:
                        f_open = official_quote["open"]
                    if official_quote.get("high") is not None:
                        f_high = official_quote["high"]
                    if official_quote.get("low") is not None:
                        f_low = official_quote["low"]
                    if official_quote.get("volume") is not None:
                        f_volume = int(official_quote["volume"] * 1000)
            
            # If it's missing, add it
            if not len(matching):
                new_idx = pd.to_datetime(latest_date)
                if df_daily.index.tz is not None:
                    new_idx = new_idx.tz_localize(df_daily.index.tz)
                
                # Check that we actually have open/close
                if f_open is None and not df_daily.empty:
                    # Fallback to last known daily close if no intraday data
                    f_open = f_close = f_high = f_low = float(df_daily['Close'].iloc[-1])
                
                if f_open is not None:
                    df_daily.loc[new_idx] = {
                        "Open": f_open,
                        "High": f_high if f_high is not None else f_open,
                        "Low": f_low if f_low is not None else f_open,
                        "Close": f_close if f_close is not None else f_open,
                        "Volume": f_volume,
                        "Adj Close": f_close if f_close is not None else f_open
                    }
                    df_daily = df_daily.sort_index()
            else:
                # If it already exists, update it with official_quote values to ensure correctness
                idx = matching[-1]
                if not is_us and official_quote and official_quote.get("price") is not None:
                    quote_date = str(official_quote.get("date") or "")
                    quote_date = (
                        f"{quote_date[:4]}-{quote_date[4:6]}-{quote_date[6:8]}"
                        if len(quote_date) == 8 else latest_date
                    )
                    if quote_date == latest_date:
                        for field, column in (("open", "Open"), ("high", "High"), ("low", "Low")):
                            if official_quote.get(field) is not None:
                                df_daily.at[idx, column] = official_quote[field]
                        df_daily.at[idx, "Close"] = official_quote["price"]
                        if official_quote.get("volume") is not None:
                            df_daily.at[idx, "Volume"] = int(official_quote["volume"] * 1000)

        kline_data = []
        if not df_daily.empty:
            df_daily['SMA5'] = df_daily['Close'].rolling(window=5).mean()
            df_daily['SMA20'] = df_daily['Close'].rolling(window=20).mean()
            df_daily['SMA60'] = df_daily['Close'].rolling(window=60).mean()
            df_daily['STD20'] = df_daily['Close'].rolling(window=20).std()
            df_daily['BB_upper'] = df_daily['SMA20'] + 2 * df_daily['STD20']
            df_daily['BB_lower'] = df_daily['SMA20'] - 2 * df_daily['STD20']

            # --- Inject closing auction bar (13:25) using official daily close ---
            # yfinance 1m data often misses the closing call auction (13:25-13:30).
            # We use the daily close price to add a definitive "13:25" endpoint so
            # the intraday chart line terminates at the correct official closing price.
            def _inject_close_bar(intra_list, daily_df, date_str):
                """Add a 13:25 bar with the official daily close if not already present."""
                if not intra_list or not date_str:
                    return
                # Check if date_str is today and current TW time is before 13:30
                import datetime
                tz_offset = datetime.timezone(datetime.timedelta(hours=8))
                now_tw = datetime.datetime.now(tz_offset)
                today_str = now_tw.strftime("%Y-%m-%d")
                if date_str == today_str and now_tw.time() < datetime.time(13, 30):
                    return

                # Find daily row matching the intraday date
                daily_df_copy = daily_df.copy()
                daily_df_copy['date_str'] = daily_df_copy.index.map(lambda x: x.strftime("%Y-%m-%d"))
                daily_row = daily_df_copy[daily_df_copy['date_str'] == date_str]
                if daily_row.empty:
                    return
                official_close = float(daily_row['Close'].iloc[-1])
                official_daily_volume = int(daily_row['Volume'].iloc[-1])
                # Sum of all 1m volumes already captured
                intra_volume_sum = sum(item['volume'] for item in intra_list)
                 # Closing auction volume = daily total minus 1m sum (floor at 0)
                closing_vol = max(0, official_daily_volume - intra_volume_sum)
                
                # Check times inside intra_list
                times_in_list = {item['time'] for item in intra_list}
                
                # Inject 13:25 if not present
                if "13:25" not in times_in_list:
                    # Find a nearby price or use close
                    price_val = official_close
                    # find closest before 13:25
                    before_prices = [item['price'] for item in intra_list if item['time'] < "13:25"]
                    if before_prices:
                        price_val = before_prices[-1]
                    intra_list.append({
                        "time": "13:25",
                        "price": price_val,
                        "volume": 0
                    })
                
                # Always add the official closing auction bar at 13:30 (with official closing price and remaining volume)
                if "13:30" not in times_in_list:
                    intra_list.append({
                        "time": "13:30",
                        "price": official_close,
                        "volume": closing_vol
                    })
                else:
                    # Update existing 13:30 point
                    for item in intra_list:
                        if item['time'] == "13:30":
                            item['price'] = official_close
                            item['volume'] = closing_vol
                            break

                # Sort by time to preserve order
                intra_list.sort(key=lambda x: x['time'])

            def _inject_open_price(intra_list, daily_df, date_str):
                """Ensure there is a 09:00 bar with the official daily open price."""
                if not intra_list or not date_str or daily_df.empty:
                    return
                daily_df_copy = daily_df.copy()
                daily_df_copy['date_str'] = daily_df_copy.index.map(lambda x: x.strftime("%Y-%m-%d"))
                daily_row = daily_df_copy[daily_df_copy['date_str'] == date_str]
                if daily_row.empty:
                    return
                official_open = float(daily_row['Open'].iloc[-1])
                
                found_0900 = False
                for item in intra_list:
                    if item['time'] == "09:00":
                        item['price'] = official_open
                        found_0900 = True
                        break
                if not found_0900:
                    intra_list.append({
                        "time": "09:00",
                        "price": official_open,
                        "volume": 0
                    })
                
                # Sort by time to preserve order
                intra_list.sort(key=lambda x: x['time'])

            if not is_us:
                _inject_open_price(intraday_data, df_daily, latest_date)
                _inject_open_price(prev_intraday_data, df_daily, prev_date)
                _inject_close_bar(intraday_data, df_daily, latest_date)
                _inject_close_bar(prev_intraday_data, df_daily, prev_date)
                if official_quote and official_quote.get("price") is not None:
                    quote_date = str(official_quote.get("date") or "")
                    quote_date = (
                        f"{quote_date[:4]}-{quote_date[4:6]}-{quote_date[6:8]}"
                        if len(quote_date) == 8 else latest_date
                    )
                    if quote_date == latest_date:
                        quote_time = official_quote.get("time") or ("13:30" if not is_intraday else "")
                        quote_time = quote_time[:5]
                        point = next((item for item in intraday_data if item["time"] == quote_time), None)
                        quote_volume = int((official_quote.get("volume") or 0) * 1000)
                        if point:
                            point["price"] = official_quote["price"]
                        elif quote_time:
                            intraday_data.append({
                                "time": quote_time,
                                "price": official_quote["price"],
                                "volume": 0,
                            })
                            intraday_data.sort(key=lambda item: item["time"])
                        daily_df_copy = df_daily.copy()
                        daily_dates = daily_df_copy.index.map(lambda value: value.strftime("%Y-%m-%d"))
                        matching = daily_df_copy.index[daily_dates == latest_date]
                        if len(matching):
                            idx = matching[-1]
                            for field, column in (("open", "Open"), ("high", "High"), ("low", "Low")):
                                if official_quote.get(field) is not None:
                                    df_daily.at[idx, column] = official_quote[field]
                            df_daily.at[idx, "Close"] = official_quote["price"]
                            if quote_volume:
                                df_daily.at[idx, "Volume"] = quote_volume
            # -------------------------------------------------------------------

            df_daily_recent = df_daily.tail(60)
            
            for idx, row in df_daily_recent.iterrows():
                date_str = idx.strftime("%Y/%m/%d")
                
                sma5_val = float(row["SMA5"]) if not pd.isna(row["SMA5"]) else None
                sma20_val = float(row["SMA20"]) if not pd.isna(row["SMA20"]) else None
                sma60_val = float(row["SMA60"]) if not pd.isna(row["SMA60"]) else None
                bb_upper_val = float(row["BB_upper"]) if not pd.isna(row["BB_upper"]) else None
                bb_lower_val = float(row["BB_lower"]) if not pd.isna(row["BB_lower"]) else None
                
                kline_data.append({
                    "date": date_str,
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                    "sma5": sma5_val,
                    "sma20": sma20_val,
                    "sma60": sma60_val,
                    "bb_upper": bb_upper_val,
                    "bb_lower": bb_lower_val
                })

                
        # 3. KD lines & K-line (60m, last 40 bars) with SMA60
        # df_hourly is already fetched in parallel at the start of get_stock_chart_data
        if not is_us:
            df_hourly = validate_hourly_against_daily(df_hourly, df_daily)
        if not df_hourly.empty:
            df_hourly = df_hourly.dropna(subset=["Open", "High", "Low", "Close"])
        kd_data = []
        if not df_hourly.empty:
            df_hourly['SMA60'] = df_hourly['Close'].rolling(window=60).mean()
            df_hourly_kd = calculate_kd(df_hourly)
            df_hourly_recent = df_hourly_kd.tail(100)
            for idx, row in df_hourly_recent.iterrows():
                datetime_str = idx.strftime("%m/%d %H:%M")
                kd_data.append({
                    "time": datetime_str,
                    "k": float(row["K"]),
                    "d": float(row["D"]),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "sma60": float(row["SMA60"]) if not pd.isna(row["SMA60"]) else None
                })
                
        # 4. Institutional (Foreign Investor net buy/sell)
        inst_data = [] if is_us else fetch_institutional_data(symbol)
        major_holder_data = [] if is_us else fetch_major_holder_data(symbol)
        if not df_daily.empty:
            df_daily_copy = df_daily.copy()
            df_daily_copy['date_str'] = df_daily_copy.index.map(lambda x: x.strftime("%Y-%m-%d"))
            price_map = dict(zip(df_daily_copy['date_str'], df_daily_copy['Close']))
            volume_map = dict(zip(df_daily_copy['date_str'], df_daily_copy['Volume']))
            for item in inst_data:
                item_date = item['date']
                item['close'] = price_map.get(item_date, None)
                item['volume'] = float(volume_map.get(item_date, 0) or 0) / 1000.0
                item['concentration'] = round(
                    (item.get('total_diff', 0) / item['volume']) * 100.0,
                    2,
                ) if item['volume'] > 0 else None
        
        disposition_info = disposition_cache.get(code, None)
        
        response_data = clean_nan({
            "symbol": symbol,
            "intraday": intraday_data,
            "prev_intraday": prev_intraday_data,
            "intraday_date": latest_date,
            "prev_intraday_date": prev_date,
            "intraday_session": intraday_session,
            "prev_intraday_session": prev_intraday_session,
            "market": "US" if is_us else "TW",
            "is_intraday": is_intraday and latest_date == market_date,
            "kline": kline_data,
            "kd": kd_data,
            "institutional": inst_data,
            "major_holders": major_holder_data,
            "disposition": disposition_info,
            "quote_source": official_quote.get("source") if official_quote else "Yahoo",
            "quote_time": official_quote.get("time") if official_quote else "",
        })
        chart_data_cache[cache_key] = {
            "updated_at": time.time(),
            "data": response_data,
            "market_complete": not is_intraday,
        }
        return response_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"?脣??”?豢?憭望?: {str(e)}")

# Mount static files to serve the frontend directly from FastAPI
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")
else:
    print(f"Warning: Frontend directory not found at {frontend_dir}")

# Load potentials and start scanner automatically on startup event
@app.on_event("startup")
def startup_event():
    load_potential_stocks()
    load_potential_us_stocks()
    sync_connector_lists()
    run_all_market_scan()
    import threading
    threading.Thread(target=load_all_us_stocks_cache, daemon=True).start()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)

