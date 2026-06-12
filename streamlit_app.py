import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import json
import os
import re
import time
import requests
import threading
from bs4 import BeautifulSoup

# Set page config
st.set_page_config(
    page_title="台股量化選股掘$與風控計算",
    page_icon="favicon.jpg",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for glassmorphism styling, premium typography, and table layouts
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;400;500;600;700;800&display=swap');

.stApp {
    background-color: #05020a !important;
    background-image: 
        radial-gradient(at 10% 10%, rgba(139, 92, 246, 0.15) 0px, transparent 55%),
        radial-gradient(at 90% 90%, rgba(168, 85, 247, 0.1) 0px, transparent 55%),
        radial-gradient(at 50% 10%, rgba(236, 72, 153, 0.05) 0px, transparent 50%) !important;
    background-attachment: fixed !important;
}

html, body, [class*="css"] {
    font-family: 'Inter', 'SF Pro TC', 'Heiti TC', sans-serif;
}

/* Glassmorphism Panels */
.glass-panel {
    background: rgba(13, 8, 24, 0.55);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(139, 92, 246, 0.12);
    border-radius: 16px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
}

/* Custom Table Styles */
.stock-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.825rem;
    margin-top: 0.5rem;
}
.stock-table th {
    background: rgba(15, 23, 42, 0.4);
    color: #94a3b8;
    text-align: left;
    padding: 10px 12px;
    font-weight: 600;
    border-bottom: 2px solid rgba(255, 255, 255, 0.05);
}
.stock-table td {
    padding: 12px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.03);
    color: #e2e8f0;
}
.stock-table tr:hover {
    background: rgba(255, 255, 255, 0.02);
    cursor: pointer;
}
.stock-table tr.selected {
    background: rgba(139, 92, 246, 0.15) !important;
    border-left: 3px solid #8b5cf6;
}

/* Badges and Indicators */
.added-by-badge {
    font-size: 0.65rem;
    padding: 2px 6px;
    border-radius: 4px;
    margin-left: 6px;
    font-weight: 700;
}
.added-by-badge.manual {
    background: rgba(139, 92, 246, 0.15);
    color: #a78bfa;
    border: 1px solid rgba(139, 92, 246, 0.3);
}
.added-by-badge.text {
    background: rgba(6, 182, 212, 0.15);
    color: #22d3ee;
    border: 1px solid rgba(6, 182, 212, 0.3);
}
.added-by-badge.new-popular {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.status-indicator {
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    font-weight: 600;
}
.light-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    display: inline-block;
}
.light-dot.green {
    background: #10b981;
    box-shadow: 0 0 8px #10b981;
}
.light-dot.red {
    background: #ef4444;
    box-shadow: 0 0 8px #ef4444;
}

.signal-badge {
    padding: 3px 8px;
    border-radius: 6px;
    font-size: 0.75rem;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    gap: 4px;
    white-space: nowrap;
}
.signal-badge.active {
    background: rgba(16, 185, 129, 0.1);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.25);
}
.signal-badge.inactive {
    background: rgba(239, 68, 68, 0.1);
    color: #f87171;
    border: 1px solid rgba(239, 68, 68, 0.25);
}

/* Strategy Lights */
.strategy-lights-container {
    display: flex;
    gap: 4px;
}
.strategy-light {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.65rem;
    font-weight: 800;
    user-select: none;
    border: 1px solid rgba(255, 255, 255, 0.05);
}
.strategy-light.active {
    background: #10b981;
    color: #0f172a;
    box-shadow: 0 0 6px rgba(16, 185, 129, 0.4);
}
.strategy-light.inactive {
    background: rgba(148, 163, 184, 0.1);
    color: #64748b;
}

/* Calculator suggested cards */
.suggest-card {
    background: rgba(15, 23, 42, 0.4);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 10px;
    padding: 8px;
    text-align: center;
    transition: all 0.2s;
}
.suggest-card:hover {
    background: rgba(99, 102, 241, 0.1);
    border-color: rgba(99, 102, 241, 0.3);
}
</style>
""", unsafe_allow_html=True)

# ----------------- Helper Functions -----------------

def get_file_path(filename):
    """
    Robust path locator: checks backend folder or root.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    path_in_backend = os.path.join(base_dir, "backend", filename)
    if os.path.exists(os.path.join(base_dir, "backend")) or os.path.exists(path_in_backend):
        return path_in_backend
    return os.path.join(base_dir, filename)

def read_stock_list():
    data_file = get_file_path("trending_stocks.json")
    if not os.path.exists(data_file):
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
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(defaults, f, ensure_ascii=False, indent=2)
        return defaults
    try:
        with open(data_file, "r", encoding="utf-8") as f:
            stocks = json.load(f)
            for s in stocks:
                if "added_by" not in s:
                    s["added_by"] = "popular"
            return stocks
    except Exception:
        return []

def write_stock_list(stocks):
    data_file = get_file_path("trending_stocks.json")
    try:
        os.makedirs(os.path.dirname(data_file), exist_ok=True)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(stocks, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def format_stock_name(stock):
    name = stock["name"]
    added_by = stock.get("added_by", "popular")
    if added_by == "manual":
        return f"{name} (手動加入)"
    elif added_by == "text":
        return f"{name} (文字加入)"
    elif added_by == "new_popular":
        return f"{name} (新增)"
    return name

def format_stock_name_html(name):
    if " (手動加入)" in name:
        clean = name.replace(" (手動加入)", "")
        return f'{clean}<span class="added-by-badge manual">手動</span>'
    if " (文字加入)" in name:
        clean = name.replace(" (文字加入)", "")
        return f'{clean}<span class="added-by-badge text">文字</span>'
    if " (新增)" in name:
        clean = name.replace(" (新增)", "")
        return f'{clean}<span class="added-by-badge new-popular">新增</span>'
    return name

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

def fetch_all_tw_stocks():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    stocks = []
    try:
        url_tse = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
        res = requests.get(url_tse, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content.decode('cp950', errors='ignore'), 'html.parser')
        table = soup.find("table", class_="h4")
        if table:
            for row in table.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) >= 6:
                    val = tds[0].get_text().strip()
                    parts = val.split('\u3000')
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        market = tds[3].get_text().strip()
                        cfi = tds[5].get_text().strip()
                        if re.match(r'^\d{4}$', code) and market == "上市" and cfi.startswith("ES"):
                            stocks.append({"code": code, "name": name, "symbol": f"{code}.TW", "market": "TSE"})
    except Exception as e:
        print(f"Error fetching TSE stock list: {e}")

    try:
        url_otc = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=4"
        res = requests.get(url_otc, headers=headers, timeout=10)
        soup = BeautifulSoup(res.content.decode('cp950', errors='ignore'), 'html.parser')
        table = soup.find("table", class_="h4")
        if table:
            for row in table.find_all("tr"):
                tds = row.find_all("td")
                if len(tds) >= 6:
                    val = tds[0].get_text().strip()
                    parts = val.split('\u3000')
                    if len(parts) >= 2:
                        code = parts[0].strip()
                        name = parts[1].strip()
                        market = tds[3].get_text().strip()
                        cfi = tds[5].get_text().strip()
                        if re.match(r'^\d{4}$', code) and market == "上櫃" and cfi.startswith("ES"):
                            stocks.append({"code": code, "name": name, "symbol": f"{code}.TWO", "market": "OTC"})
    except Exception as e:
        print(f"Error fetching OTC stock list: {e}")
    return stocks

# ----------------- Unified Analyzer -----------------

def analyze_stocks_batch(stocks_list):
    """
    Fetch daily and hourly data in batches to calculate all metrics, strategy lights,
    and system signals for Tab A & Tab B tables.
    """
    if not stocks_list:
        return []
    symbols = [s["symbol"] for s in stocks_list]
    
    # 1. Batch download Daily Data (1 year)
    try:
        df_daily = yf.download(symbols, period="1y", interval="1d", progress=False)
    except Exception as e:
        st.error(f"下載日線數據失敗: {e}")
        return []
    if df_daily.empty:
        return []

    # 2. Batch download Hourly Data (1 month)
    try:
        df_hourly = yf.download(symbols, period="1mo", interval="60m", progress=False)
    except Exception:
        df_hourly = pd.DataFrame()

    results = []
    for s in stocks_list:
        sym = s["symbol"]
        code = s["code"]
        name = format_stock_name(s)
        try:
            # Extract daily DataFrame
            if isinstance(df_daily.columns, pd.MultiIndex):
                if ('Close', sym) in df_daily.columns:
                    df_sym = pd.DataFrame({
                        'Open': df_daily[('Open', sym)],
                        'High': df_daily[('High', sym)],
                        'Low': df_daily[('Low', sym)],
                        'Close': df_daily[('Close', sym)],
                        'Volume': df_daily[('Volume', sym)]
                    }).dropna(subset=['Close'])
                else:
                    continue
            else:
                if 'Close' in df_daily.columns:
                    df_sym = pd.DataFrame({
                        'Open': df_daily['Open'],
                        'High': df_daily['High'],
                        'Low': df_daily['Low'],
                        'Close': df_daily['Close'],
                        'Volume': df_daily['Volume']
                    }).dropna(subset=['Close'])
                else:
                    continue

            df_sym = df_sym[df_sym['Volume'] > 0]
            if df_sym.empty or len(df_sym) < 60:
                continue

            df_sym['MA5'] = df_sym['Close'].rolling(window=5).mean()
            df_sym['MA20'] = df_sym['Close'].rolling(window=20).mean()
            df_sym['MA60'] = df_sym['Close'].rolling(window=60).mean()
            df_sym['Vol_MA20'] = df_sym['Volume'].rolling(window=20).mean()

            close = float(df_sym['Close'].iloc[-1])
            prev_close = float(df_sym['Close'].iloc[-2]) if len(df_sym) >= 2 else close
            volume = float(df_sym['Volume'].iloc[-1])
            vol_ma20 = float(df_sym['Vol_MA20'].iloc[-1]) if not pd.isna(df_sym['Vol_MA20'].iloc[-1]) else 1.0
            ma5 = float(df_sym['MA5'].iloc[-1])
            ma20 = float(df_sym['MA20'].iloc[-1])
            ma60 = float(df_sym['MA60'].iloc[-1])

            daily_trend_ok = close > ma20 and close > ma60 and ma20 > ma60
            volume_lots = int(volume // 1000)

            # Higher Lows (底底高)
            lows = df_sym['Low'].values
            minima_indices = find_local_minima(lows, order=5)
            morph_ok = False
            if len(minima_indices) >= 2:
                last_min = lows[minima_indices[-1]]
                prev_min = lows[minima_indices[-2]]
                if last_min > prev_min:
                    morph_ok = True

            # 5 Strategy lights
            vol_breakout = (close > prev_close) and (volume > 1.5 * vol_ma20)
            n_days = min(len(df_sym), 120)
            recent_low = float(df_sym['Low'].tail(n_days).min())
            recent_high = float(df_sym['High'].tail(n_days).max())
            range_span = recent_high - recent_low
            undervalued = False
            if range_span > 0:
                undervalued = close < (recent_low + 0.3 * range_span)
            prev_high_20 = float(df_sym['High'].iloc[-21:-1].max()) if len(df_sym) >= 21 else float(df_sym['High'].iloc[:-1].max()) if len(df_sym) > 1 else close
            breakout_5ma = (close > prev_high_20) and (close > ma5)
            ma10 = df_sym['Close'].rolling(window=10).mean().iloc[-1]
            momentum = (close > ma5) and (ma5 > ma10) and (ma10 > ma20)
            mean_reversion = (close < ma20 * 0.95) and (close > prev_close)

            signals = {
                "vol_breakout": vol_breakout,
                "undervalued": undervalued,
                "breakout_5ma": breakout_5ma,
                "momentum": momentum,
                "mean_reversion": mean_reversion
            }

            # Extract hourly data slice
            latest_k, latest_d, golden_cross_count, hourly_kd_ok = 0.0, 0.0, 0, False
            if not df_hourly.empty:
                try:
                    if isinstance(df_hourly.columns, pd.MultiIndex):
                        if ('Close', sym) in df_hourly.columns:
                            df_h_sym = pd.DataFrame({
                                'Open': df_hourly[('Open', sym)],
                                'High': df_hourly[('High', sym)],
                                'Low': df_hourly[('Low', sym)],
                                'Close': df_hourly[('Close', sym)],
                                'Volume': df_hourly[('Volume', sym)]
                            }).dropna(subset=['Close'])
                        else:
                            df_h_sym = pd.DataFrame()
                    else:
                        if 'Close' in df_hourly.columns:
                            df_h_sym = pd.DataFrame({
                                'Open': df_hourly['Open'],
                                'High': df_hourly['High'],
                                'Low': df_hourly['Low'],
                                'Close': df_hourly['Close'],
                                'Volume': df_hourly['Volume']
                            }).dropna(subset=['Close'])
                        else:
                            df_h_sym = pd.DataFrame()

                    if not df_h_sym.empty and len(df_h_sym) >= 20:
                        df_h_sym = calculate_kd(df_h_sym)
                        latest_k = float(df_h_sym['K'].iloc[-1])
                        latest_d = float(df_h_sym['D'].iloc[-1])
                        
                        recent_hourly = df_h_sym.tail(60)
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
                        hourly_kd_ok = 2 <= golden_cross_count <= 3
                except Exception:
                    pass

            kd_under_50 = latest_k < 50 and latest_d < 50
            system_a_signal = daily_trend_ok and kd_under_50 and hourly_kd_ok

            prev_high = float(df_sym['High'].tail(60).max())
            stop_loss_price = round(close * 0.95, 2)
            r_value = 0.0
            risk = close - stop_loss_price
            if risk > 0:
                r_value = round((prev_high - close) / risk, 2)

            results.append({
                "code": code,
                "symbol": sym,
                "name": name,
                "current_price": round(close, 2),
                "volume_lots": volume_lots,
                "daily_trend_ok": daily_trend_ok,
                "latest_k": round(latest_k, 2),
                "latest_d": round(latest_d, 2),
                "kd_under_50": kd_under_50,
                "golden_cross_count": golden_cross_count,
                "hourly_kd_ok": hourly_kd_ok,
                "morph_ok": morph_ok,
                "system_a_signal": system_a_signal,
                "prev_high": round(prev_high, 2),
                "stop_loss_price": stop_loss_price,
                "r_value": r_value,
                "signals": signals
            })
        except Exception:
            pass

    # Sort results consistently: System signal -> MA Trend -> KD Golden Crosses -> Volume
    results.sort(key=lambda x: (
        1 if x.get("system_a_signal") else 0,
        1 if x.get("daily_trend_ok") else 0,
        x.get("golden_cross_count", 0),
        x.get("volume_lots", 0)
    ), reverse=True)
    return results

# ----------------- Background Threads -----------------

class ScanState:
    active = False
    progress = 0
    total = 0
    message = ""

@st.cache_resource
def get_scan_state():
    return ScanState()

@st.cache_resource
def start_monitor_thread():
    """
    Initializes simulated order觸價風控 monitor daemon thread via cached resource.
    """
    def monitor_loop():
        cooldown_until = 0.0
        while True:
            try:
                orders_path = get_file_path("orders_store.json")
                if os.path.exists(orders_path):
                    with open(orders_path, "r", encoding="utf-8") as f:
                        orders = json.load(f)
                    
                    monitoring_orders = [o for o in orders if o.get("status") == "MONITORING"]
                    if monitoring_orders:
                        current_time = time.time()
                        if current_time >= cooldown_until:
                            symbols = list({o.get("symbol", f"{o['code']}.TW") for o in monitoring_orders})
                            try:
                                df = yf.download(symbols, period="1d", progress=False)
                                prices_map = {}
                                if not df.empty:
                                    for sym in symbols:
                                        if isinstance(df.columns, pd.MultiIndex):
                                            if ('Close', sym) in df.columns:
                                                series = df[('Close', sym)].dropna()
                                                if not series.empty:
                                                    prices_map[sym] = float(series.iloc[-1])
                                        else:
                                            if 'Close' in df.columns:
                                                series = df['Close'].dropna()
                                                if not series.empty:
                                                    prices_map[sym] = float(series.iloc[-1])
                                    
                                    updated = False
                                    for o in monitoring_orders:
                                        sym = o.get("symbol", f"{o['code']}.TW")
                                        current_price = prices_map.get(sym)
                                        if current_price is not None and current_price > 0:
                                            o["last_price"] = current_price
                                            updated = True
                                            
                                            sl = o.get("stop_loss_price")
                                            tp = o.get("stop_profit_price")
                                            triggered = False
                                            trigger_type = ""
                                            
                                            if sl and current_price <= sl:
                                                triggered = True
                                                trigger_type = "STOP_LOSS_TRIGGERED"
                                            elif tp and current_price >= tp:
                                                triggered = True
                                                trigger_type = "TAKE_PROFIT_TRIGGERED"
                                                
                                            if triggered:
                                                o["status"] = trigger_type
                                                reverse_action = "SELL" if o["action"] == "BUY" else "BUY"
                                                lot_type = o.get("lot_type", "ODD")
                                                o["trigger_order_id"] = f"mock-{lot_type.lower()}-{reverse_action.lower()}-{o['code']}-{int(time.time())}"
                                                o["message"] = f"觸發反向賣出，委託單號: {o['trigger_order_id']}"
                                    
                                    if updated:
                                        with open(orders_path, "w", encoding="utf-8") as f:
                                            json.dump(orders, f, ensure_ascii=False, indent=2)
                            except Exception as yf_err:
                                err_msg = str(yf_err)
                                if "Too Many Requests" in err_msg or "Rate limit" in err_msg or "429" in err_msg:
                                    cooldown_until = time.time() + 120
                                else:
                                    cooldown_until = time.time() + 30
            except Exception:
                pass
            time.sleep(20)
            
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    return t

# Start background monitor thread automatically
start_monitor_thread()

def run_all_market_scan_async():
    """
    Trigger all-market scanner in the background using chunks of 80 symbols.
    """
    scan_state = get_scan_state()
    if scan_state.active:
        return
    scan_state.active = True
    scan_state.progress = 0
    scan_state.total = 0
    
    def worker():
        try:
            scan_state.message = "正在獲取全市場上市櫃股票代碼..."
            stocks = fetch_all_tw_stocks()
            scan_state.total = len(stocks)
            
            if not stocks:
                scan_state.active = False
                return
                
            temp_potentials = []
            chunk_size = 80
            stock_chunks = [stocks[i:i + chunk_size] for i in range(0, len(stocks), chunk_size)]
            
            scan_state.message = f"成功獲取 {len(stocks)} 檔股票，分為 {len(stock_chunks)} 個批次進行掃描..."
            
            for chunk_idx, chunk in enumerate(stock_chunks):
                symbols = [s["symbol"] for s in chunk]
                try:
                    df = yf.download(symbols, period="6mo", interval="1d", progress=False)
                except Exception:
                    scan_state.progress += len(chunk)
                    time.sleep(2)
                    continue
                
                if df.empty:
                    scan_state.progress += len(chunk)
                    time.sleep(2)
                    continue
                
                for s in chunk:
                    scan_state.progress += 1
                    sym = s["symbol"]
                    try:
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
                                continue
                        else:
                            if 'Close' in df.columns:
                                df_sym = pd.DataFrame({
                                    'Open': df['Open'],
                                    'High': df['High'],
                                    'Low': df['Low'],
                                    'Close': df['Close'],
                                    'Volume': df['Volume']
                                }).dropna(subset=['Close'])
                            else:
                                continue
                                
                        df_sym = df_sym[df_sym['Volume'] > 0]
                        if df_sym.empty or len(df_sym) < 60:
                            continue
                            
                        # Daily indicators check
                        df_sym['MA5'] = df_sym['Close'].rolling(window=5).mean()
                        df_sym['MA20'] = df_sym['Close'].rolling(window=20).mean()
                        df_sym['MA60'] = df_sym['Close'].rolling(window=60).mean()
                        df_sym['Vol_MA20'] = df_sym['Volume'].rolling(window=20).mean()
                        
                        today_volume = df_sym['Volume'].iloc[-1]
                        close_price = df_sym['Close'].iloc[-1]
                        ma5 = df_sym['MA5'].iloc[-1]
                        ma20 = df_sym['MA20'].iloc[-1]
                        ma60 = df_sym['MA60'].iloc[-1]
                        
                        # 1. Liquidity
                        if today_volume < 500000:
                            continue
                        # 2. Daily trend
                        if not (ma20 > ma60 and close_price > ma5):
                            continue
                        # 3. Higher Lows
                        lows = df_sym['Low'].values
                        minima_indices = find_local_minima(lows, order=5)
                        morph_ok = False
                        if len(minima_indices) >= 2:
                            last_min = lows[minima_indices[-1]]
                            prev_min = lows[minima_indices[-2]]
                            if last_min > prev_min:
                                morph_ok = True
                        if not morph_ok:
                            continue
                            
                        # Grab hourly KD details (only for matching stocks)
                        latest_k, latest_d, golden_cross_count, hourly_kd_ok = 0.0, 0.0, 0, False
                        try:
                            t = yf.Ticker(sym)
                            df_hourly = t.history(period="1mo", interval="60m")
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
                                hourly_kd_ok = 2 <= golden_cross_count <= 3
                        except Exception:
                            pass
                            
                        prev_high = float(df_sym['High'].tail(60).max())
                        stop_loss_price = round(close_price * 0.95, 2)
                        r_value = 0.0
                        risk = close_price - stop_loss_price
                        if risk > 0:
                            r_value = round((prev_high - close_price) / risk, 2)
                            
                        vol_ma20 = float(df_sym['Vol_MA20'].iloc[-1]) if not pd.isna(df_sym['Vol_MA20'].iloc[-1]) else 1.0
                        vol_breakout = (close_price > df_sym['Close'].iloc[-2]) and (today_volume > 1.5 * vol_ma20)
                        undervalued = False
                        if range_span > 0:
                            undervalued = close_price < (recent_low + 0.3 * range_span)
                        breakout_5ma = (close_price > prev_high_20) and (close_price > ma5)
                        ma10 = df_sym['Close'].rolling(window=10).mean().iloc[-1]
                        momentum = (close_price > ma5) and (ma5 > ma10) and (ma10 > ma20)
                        mean_reversion = (close_price < ma20 * 0.95) and (close_price > df_sym['Close'].iloc[-2])
                        
                        signals = {
                            "vol_breakout": vol_breakout,
                            "undervalued": undervalued,
                            "breakout_5ma": breakout_5ma,
                            "momentum": momentum,
                            "mean_reversion": mean_reversion
                        }
                        
                        temp_potentials.append({
                            "code": s["code"],
                            "symbol": sym,
                            "name": s["name"],
                            "current_price": round(close_price, 2),
                            "volume_lots": int(today_volume // 1000),
                            "daily_trend_ok": ma20 > ma60,
                            "latest_k": round(latest_k, 2),
                            "latest_d": round(latest_d, 2),
                            "kd_under_50": latest_k < 50 and latest_d < 50,
                            "golden_cross_count": golden_cross_count,
                            "hourly_kd_ok": hourly_kd_ok,
                            "morph_ok": True,
                            "system_a_signal": ma20 > ma60 and (latest_k < 50 and latest_d < 50) and (2 <= golden_cross_count <= 3),
                            "prev_high": round(prev_high, 2),
                            "stop_loss_price": stop_loss_price,
                            "r_value": r_value,
                            "signals": signals
                        })
                    except Exception:
                        pass
                time.sleep(1.5)
                
            temp_potentials.sort(key=lambda x: (
                1 if x.get("system_a_signal") else 0,
                1 if x.get("daily_trend_ok") else 0,
                x.get("golden_cross_count", 0),
                x.get("volume_lots", 0)
            ), reverse=True)
            
            potentials_path = get_file_path("potential_stocks.json")
            os.makedirs(os.path.dirname(potentials_path), exist_ok=True)
            with open(potentials_path, "w", encoding="utf-8") as f:
                json.dump(temp_potentials, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"Error in scanner loop: {e}")
        finally:
            scan_state.active = False
            
    threading.Thread(target=worker, daemon=True).start()

# ----------------- ECharts Template Renderer -----------------

def render_echarts_js(chart_id, chart_type, times, data_1, data_2=None, data_3=None):
    """
    Renders pure ECharts using st.components.v1.html to ensure identical, high-premium dark themes.
    """
    if chart_type == "intraday" or chart_type == "prev_intraday":
        color = "#f59e0b" if chart_type == "intraday" else "#34d399"
        area_color = "rgba(245, 158, 11, 0.15)" if chart_type == "intraday" else "rgba(52, 211, 153, 0.15)"
        legend_name = "即時股價"
        avg_prices = []
        total_sum = 0.0
        for i, p in enumerate(data_1):
            total_sum += p
            avg_prices.append(round(total_sum / (i + 1), 2))
            
        html_content = f"""
        <div id="{chart_id}" style="width: 100%; height: 250px;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('{chart_id}');
            var myChart = echarts.init(chartDom, 'dark', {{ backgroundColor: 'transparent' }});
            var times = {json.dumps(times)};
            var prices = {json.dumps(data_1)};
            var volumes = {json.dumps(data_2 or [])};
            var avgPrices = {json.dumps(avg_prices)};
            
            var option = {{
                grid: [
                    {{ left: 45, right: 15, height: "55%", top: 20 }},
                    {{ left: 45, right: 15, top: "72%", height: "20%" }}
                ],
                tooltip: {{
                    trigger: "axis",
                    axisPointer: {{ type: "cross" }},
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    textStyle: {{ color: "#fff", fontFamily: "Outfit" }},
                    formatter: function (params) {{
                        var priceParam = params.find(p => p.seriesName === "{legend_name}");
                        var avgParam = params.find(p => p.seriesName === "均價線");
                        var volParam = params.find(p => p.seriesName === "分時成交量");
                        
                        var res = "<b>時間: " + params[0].name + "</b><br/>";
                        if (priceParam) {{
                            res += '<span style="color:{color};">●</span> 價格: $' + priceParam.value.toFixed(2) + '<br/>';
                        }}
                        if (avgParam) {{
                            res += '<span style="color:#a855f7;">●</span> 均價: $' + avgParam.value.toFixed(2) + '<br/>';
                        }}
                        if (volParam) {{
                            res += '<span style="color:{color};">●</span> 成交量: ' + volParam.value.toLocaleString() + ' 股<br/>';
                        }}
                        return res;
                    }}
                }},
                xAxis: [
                    {{
                        type: "category",
                        data: times,
                        gridIndex: 0,
                        axisLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.1)" }} }},
                        axisLabel: {{ show: false }}
                    }},
                    {{
                        type: "category",
                        data: times,
                        gridIndex: 1,
                        axisLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.1)" }} }},
                        axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                    }}
                ],
                yAxis: [
                    {{
                        type: "value",
                        scale: true,
                        gridIndex: 0,
                        axisLine: {{ show: false }},
                        splitLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.04)" }} }},
                        axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                    }},
                    {{
                        type: "value",
                        gridIndex: 1,
                        axisLine: {{ show: false }},
                        splitLine: {{ show: false }},
                        axisLabel: {{ show: false }}
                    }}
                ],
                series: [
                    {{
                        name: "{legend_name}",
                        type: "line",
                        data: prices,
                        xAxisIndex: 0,
                        yAxisIndex: 0,
                        smooth: true,
                        symbol: "none",
                        lineStyle: {{ color: "{color}", width: 2 }},
                        areaStyle: {{
                            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                                {{ offset: 0, color: "{area_color}" }},
                                {{ offset: 1, color: "rgba(0, 0, 0, 0.0)" }}
                            ])
                        }}
                    }},
                    {{
                        name: "均價線",
                        type: "line",
                        data: avgPrices,
                        xAxisIndex: 0,
                        yAxisIndex: 0,
                        smooth: true,
                        symbol: "none",
                        lineStyle: {{ color: "#a855f7", width: 1.5 }}
                    }},
                    {{
                        name: "分時成交量",
                        type: "bar",
                        data: volumes,
                        xAxisIndex: 1,
                        yAxisIndex: 1,
                        itemStyle: {{ color: "{color}" }}
                    }}
                ]
            }};
            myChart.setOption(option);
            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=270)
        
    elif chart_type == "daily_kline":
        html_content = f"""
        <div id="{chart_id}" style="width: 100%; height: 260px;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('{chart_id}');
            var myChart = echarts.init(chartDom, 'dark', {{ backgroundColor: 'transparent' }});
            var dates = {json.dumps(times)};
            var klineVal = {json.dumps(data_1)}; // [open, close, low, high]
            var sma5 = {json.dumps(data_2 or [])};
            var sma20 = {json.dumps(data_3 or [])};
            
            var option = {{
                grid: {{ left: 45, right: 15, height: "70%", top: 25 }},
                tooltip: {{
                    trigger: "axis",
                    axisPointer: {{ type: "cross" }},
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    textStyle: {{ color: "#fff", fontFamily: "Outfit" }},
                    formatter: function(params) {{
                        var kData = params.find(p => p.seriesName === "K-Line");
                        var sma5Data = params.find(p => p.seriesName === "SMA5");
                        var sma20Data = params.find(p => p.seriesName === "SMA20");
                        
                        var res = "<b>" + params[0].name + "</b><br/>";
                        if (kData) {{
                            res += '<span style="color:#ef4444;">●</span> 開盤: $' + kData.value[1] + ' ‧ 收盤: $' + kData.value[2] + '<br/>';
                            res += '<span style="color:#10b981;">●</span> 最低: $' + kData.value[3] + ' ‧ 最高: $' + kData.value[4] + '<br/>';
                        }}
                        if (sma5Data && sma5Data.value !== undefined && sma5Data.value !== null) {{
                            res += '<span style="color:#f59e0b;">●</span> SMA5: $' + Number(sma5Data.value).toFixed(2) + ' ';
                        }}
                        if (sma20Data && sma20Data.value !== undefined && sma20Data.value !== null) {{
                            res += '<span style="color:#a855f7;">●</span> SMA20: $' + Number(sma20Data.value).toFixed(2);
                        }}
                        return res;
                    }}
                }},
                legend: {{
                    data: ["SMA5", "SMA20"],
                    textStyle: {{ color: "#94a3b8", fontFamily: "Outfit", fontSize: 11 }},
                    right: 15,
                    top: 0
                }},
                xAxis: {{
                    type: "category",
                    data: dates,
                    axisLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.1)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                yAxis: {{
                    type: "value",
                    scale: true,
                    axisLine: {{ show: false }},
                    splitLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.04)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                series: [
                    {{
                        name: "K-Line",
                        type: "candlestick",
                        data: klineVal,
                        itemStyle: {{
                            color: "#ef4444",
                            color0: "#10b981",
                            borderColor: "#ef4444",
                            borderColor0: "#10b981"
                        }}
                    }},
                    {{
                        name: "SMA5",
                        type: "line",
                        data: sma5,
                        symbol: "none",
                        lineStyle: {{ color: "#f59e0b", width: 1.5 }},
                        smooth: true
                    }},
                    {{
                        name: "SMA20",
                        type: "line",
                        data: sma20,
                        symbol: "none",
                        lineStyle: {{ color: "#a855f7", width: 1.5 }},
                        smooth: true
                    }}
                ]
            }};
            myChart.setOption(option);
            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=280)
        
    elif chart_type == "hourly_kd":
        html_content = f"""
        <div id="{chart_id}" style="width: 100%; height: 160px;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('{chart_id}');
            var myChart = echarts.init(chartDom, 'dark', {{ backgroundColor: 'transparent' }});
            var times = {json.dumps(times)};
            var kVal = {json.dumps(data_1)};
            var dVal = {json.dumps(data_2)};
            
            var option = {{
                grid: {{ top: 25, bottom: 25, left: 45, right: 15 }},
                tooltip: {{
                    trigger: "axis",
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    textStyle: {{ color: "#fff", fontFamily: "Outfit" }}
                }},
                legend: {{
                    data: ["K 值", "D 值"],
                    textStyle: {{ color: "#94a3b8", fontFamily: "Outfit" }},
                    top: 0
                }},
                xAxis: {{
                    type: "category",
                    data: times,
                    axisLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.1)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                yAxis: {{
                    type: "value",
                    min: 0,
                    max: 100,
                    axisLine: {{ show: false }},
                    splitLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.04)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                series: [
                    {{
                        name: "K 值",
                        type: "line",
                        data: kVal,
                        symbol: "none",
                        lineStyle: {{ color: "#f59e0b", width: 2 }},
                        markLine: {{
                            symbol: "none",
                            data: [
                                {{ yAxis: 50, lineStyle: {{ color: "rgba(255,255,255,0.15)", type: "dashed" }}, label: {{ show: true, position: "start", formatter: "50 基準" }} }},
                                {{ yAxis: 40, lineStyle: {{ color: "rgba(244,63,94,0.25)", type: "dashed" }}, label: {{ show: true, position: "start", formatter: "40 低檔" }} }}
                            ]
                        }}
                    }},
                    {{
                        name: "D 值",
                        type: "line",
                        data: dVal,
                        symbol: "none",
                        lineStyle: {{ color: "#6366f1", width: 2 }}
                    }}
                ]
            }};
            myChart.setOption(option);
            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=180)
        
    elif chart_type == "institutional":
        html_content = f"""
        <div id="{chart_id}" style="width: 100%; height: 220px;"></div>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <script>
            var chartDom = document.getElementById('{chart_id}');
            var myChart = echarts.init(chartDom, 'dark', {{ backgroundColor: 'transparent' }});
            var dates = {json.dumps(times)};
            var foreign = {json.dumps(data_1)};
            var trust = {json.dumps(data_2 or [])};
            var dealer = {json.dumps(data_3 or [])};
            
            var option = {{
                grid: {{ top: 35, bottom: 25, left: 45, right: 15 }},
                tooltip: {{
                    trigger: "axis",
                    axisPointer: {{ type: "shadow" }},
                    backgroundColor: "rgba(15, 23, 42, 0.95)",
                    borderColor: "rgba(255, 255, 255, 0.1)",
                    textStyle: {{ color: "#fff", fontFamily: "Outfit" }},
                    formatter: function(params) {{
                        var res = "<b>" + params[0].name + " 法人買賣超</b><br/>";
                        params.forEach(p => {{
                            var sign = p.value >= 0 ? "+" : "";
                            res += p.seriesName + ": <span style='font-weight:700; color:" + (p.value >= 0 ? "#ef4444" : "#10b981") + "'>" + sign + p.value.toLocaleString() + " 張</span><br/>";
                        }});
                        return res;
                    }}
                }},
                legend: {{
                    data: ["外資", "投信", "自營商"],
                    textStyle: {{ color: "#94a3b8", fontFamily: "Outfit" }},
                    top: 0
                }},
                xAxis: {{
                    type: "category",
                    data: dates,
                    axisLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.1)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                yAxis: {{
                    type: "value",
                    axisLine: {{ show: false }},
                    splitLine: {{ lineStyle: {{ color: "rgba(255,255,255,0.04)" }} }},
                    axisLabel: {{ color: "#94a3b8", fontFamily: "Outfit" }}
                }},
                series: [
                    {{
                        name: "外資",
                        type: "bar",
                        data: foreign,
                        itemStyle: {{
                            color: function(params) {{
                                return params.value >= 0 ? "#6366f1" : "rgba(99, 102, 241, 0.45)";
                            }}
                        }}
                    }},
                    {{
                        name: "投信",
                        type: "bar",
                        data: trust,
                        itemStyle: {{
                            color: function(params) {{
                                return params.value >= 0 ? "#ec4899" : "rgba(236, 72, 153, 0.45)";
                            }}
                        }}
                    }},
                    {{
                        name: "自營商",
                        type: "bar",
                        data: dealer,
                        itemStyle: {{
                            color: function(params) {{
                                return params.value >= 0 ? "#f59e0b" : "rgba(245, 158, 11, 0.45)";
                            }}
                        }}
                    }}
                ]
            }};
            myChart.setOption(option);
            window.addEventListener('resize', function() {{ myChart.resize(); }});
        </script>
        """
        st.components.v1.html(html_content, height=240)

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
                
            recent_trades = trades[-20:]
            result = []
            for t in recent_trades:
                result.append({
                    "date": str(t.get("formattedDate", t.get("date", "")[:10])),
                    "foreign": float(t.get("foreignDiffVolK", 0.0) or 0.0),
                    "trust": float(t.get("investmentTrustDiffVolK", 0.0) or 0.0),
                    "dealer": float(t.get("dealerDiffVolK", 0.0) or 0.0)
                })
            return result
    except Exception as e:
        print(f"Error fetching institutional data: {e}")
    return []

# ----------------- UI Rendering Helpers -----------------

def render_strategy_lights_html(signals):
    strategies = [
        {"key": "vol_breakout", "char": "帶", "label": "帶量突破"},
        {"key": "undervalued", "char": "估", "label": "價質低估"},
        {"key": "breakout_5ma", "char": "破", "label": "破前高站穩5日均線"},
        {"key": "momentum", "char": "勢", "label": "動能順勢"},
        {"key": "mean_reversion", "char": "歸", "label": "均值回歸"}
    ]
    html = '<div class="strategy-lights-container">'
    for s in strategies:
        active = signals.get(s["key"]) is True
        color_class = "active" if active else "inactive"
        title = f"{s['label']}: {'符合' if active else '未符合'}"
        html += f'<span class="strategy-light {color_class}" title="{title}">{s["char"]}</span>'
    html += '</div>'
    return html

def render_stocks_table_html(analyzed_data, selected_code=None):
    """
    Renders the unified stock list table with identical columns for both tabs.
    """
    if not analyzed_data:
        return "<p style='color:#94a3b8; text-align:center;'>追蹤清單中目前沒有股票。</p>"
        
    html = """
    <table class="stock-table">
        <thead>
            <tr>
                <th>個股</th>
                <th>當前價</th>
                <th>成交量</th>
                <th>日線趨勢</th>
                <th>60分K KD</th>
                <th>底底高</th>
                <th>策略燈號</th>
                <th>進場訊號</th>
            </tr>
        </thead>
        <tbody>
    """
    for s in analyzed_data:
        tr_class = "selected" if selected_code == s["code"] else ""
        name_html = format_stock_name_html(s["name"])
        
        trend_html = '<div class="status-indicator"><span class="light-dot green"></span>符合多頭</div>' if s["daily_trend_ok"] else '<div class="status-indicator"><span class="light-dot red"></span>未符合</div>'
        kd_html = f'<div class="status-indicator"><span class="light-dot green"></span>金叉 {s["golden_cross_count"]} 次</div>' if s["hourly_kd_ok"] else f'<div class="status-indicator"><span class="light-dot red"></span>金叉 {s["golden_cross_count"]} 次</div>'
        morph_html = '<span class="signal-badge active"><i class="fa-solid fa-chart-line"></i> 符合</span>' if s["morph_ok"] else '<span class="signal-badge inactive"><i class="fa-solid fa-chart-line"></i> 未符合</span>'
        
        lights_html = render_strategy_lights_html(s["signals"])
        signal_html = '<span class="signal-badge active">符合進場</span>' if s["system_a_signal"] else '<span class="signal-badge inactive">未符合</span>'
        
        html += f"""
        <tr class="{tr_class}">
            <td>
                <span style="font-weight:700; display:block;">{name_html}</span>
                <span style="font-size:0.75rem; color:#94a3b8; font-family:'Outfit';">{s['code']}</span>
            </td>
            <td><span style="font-family:'Outfit'; font-weight:600; color:#f59e0b;">${s['current_price']:.2f}</span></td>
            <td><span style="font-family:'Outfit'; font-weight:500;">{s['volume_lots']:,} 張</span></td>
            <td>{trend_html}</td>
            <td>{kd_html}</td>
            <td style="text-align:center;">{morph_html}</td>
            <td>{lights_html}</td>
            <td>{signal_html}</td>
        </tr>
        """
    html += "</tbody></table>"
    return html

# ----------------- Main UI Construction -----------------

# Init session state
if "selected_stock_code" not in st.session_state:
    st.session_state.selected_stock_code = None

if "target_buy_price_value" not in st.session_state:
    st.session_state.target_buy_price_value = 0.0

# Render title with logo image side-by-side using st.columns
logo_col, title_col = st.columns([0.07, 0.93])
with logo_col:
    st.image("favicon.jpg", width=54)
with title_col:
    st.markdown("<h1 style='margin: 0; padding-top: 5px; font-weight: 800; background: linear-gradient(90deg, #a78bfa, #34d399); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>台股量化選股掘$與風控計算</h1>", unsafe_allow_html=True)

# Split Screen: Left column 1.3fr, Right column 1.0fr
col_left, col_right = st.columns([1.3, 1.0])

# Read popular stock list
stocks_list = read_stock_list()

# ----------------- LEFT COLUMN (TABS & TABLE LISTS) -----------------
with col_left:
    st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
    
    # Dual tab layout
    tab_a, tab_b = st.tabs(["🔥 熱門個股即時追蹤 (Tab A)", "🔍 全市場底部潛力股掃描 (Tab B)"])
    
    # Active Stock Selection drop-downs to link details
    st.write("---")
    
    # Populate data variables
    analyzed_tab_a = []
    analyzed_tab_b = []
    
    # Tab A
    with tab_a:
        st.subheader("🔥 熱門追蹤個股")
        
        # Action controls for Tab A
        control_col1, control_col2, control_col3 = st.columns([1, 1.5, 1])
        with control_col1:
            if st.button("🔄 重刷熱門股"):
                with st.spinner("正在爬取最新 Yahoo 熱門股..."):
                    try:
                        # Fetch trending stocks from yahoo
                        url = "https://tw.stock.yahoo.com/class-quote?category_id=100"
                        headers = {"User-Agent": "Mozilla/5.0"}
                        res = requests.get(url, headers=headers, timeout=10)
                        soup = BeautifulSoup(res.content, "lxml")
                        links = soup.find_all("a", href=re.compile(r'/quote/\d{4}'))
                        trending = []
                        seen = set()
                        for link in links:
                            href = link.get("href", "")
                            match = re.search(r'/quote/(\d{4})', href)
                            if match:
                                code = match.group(1)
                                if code not in seen:
                                    seen.add(code)
                                    # Fetch simple name from text
                                    name_text = link.get_text().strip()
                                    trending.append({"code": code, "symbol": f"{code}.TW", "name": name_text})
                        if trending:
                            existing = read_stock_list()
                            existing_codes = {s["code"] for s in existing}
                            manual_and_text = [s for s in existing if s.get("added_by") in ["manual", "text"]]
                            
                            new_populars = []
                            for t in trending[:15]:
                                added_type = "new_popular" if t["code"] not in existing_codes else "popular"
                                new_populars.append({
                                    "code": t["code"],
                                    "symbol": t["symbol"],
                                    "name": t["name"],
                                    "added_by": added_type
                                })
                            
                            final_stocks = []
                            final_codes = set()
                            for s in new_populars + manual_and_text:
                                if s["code"] not in final_codes:
                                    final_codes.add(s["code"])
                                    final_stocks.append(s)
                            write_stock_list(final_stocks)
                            st.success("成功更新熱門股清單！")
                            st.rerun()
                    except Exception as err:
                        st.error(f"重刷失敗: {err}")
                        
        with control_col2:
            txt_file = st.file_uploader("📥 批量文字檔匯入 (代碼以逗號/換行區隔)", type=["txt"])
            if txt_file is not None:
                content = txt_file.read().decode("utf-8")
                matches = re.findall(r'\b\d{4,6}\b', content)
                unique_codes = list(set(matches))
                if unique_codes:
                    existing = read_stock_list()
                    existing_codes = {s["code"] for s in existing}
                    added_count = 0
                    for code in unique_codes:
                        if code not in existing_codes:
                            existing.append({
                                "code": code,
                                "symbol": f"{code}.TW",
                                "name": "自訂個股",
                                "added_by": "text"
                            })
                            added_count += 1
                    if added_count > 0:
                        write_stock_list(existing)
                        st.success(f"成功匯入 {added_count} 檔個股！")
                        st.rerun()
                        
        with control_col3:
            add_code = st.text_input("➕ 新增單檔股票代號", max_chars=6)
            if add_code:
                add_code = add_code.strip()
                if add_code.isdigit() and len(add_code) >= 4:
                    existing = read_stock_list()
                    if not any(s["code"] == add_code for s in existing):
                        existing.append({
                            "code": add_code,
                            "symbol": f"{add_code}.TW",
                            "name": "自訂個股",
                            "added_by": "manual"
                        })
                        write_stock_list(existing)
                        st.success(f"已新增 {add_code} 至追蹤名單！")
                        st.rerun()
        
        # Batch analyze Tab A stocks
        analyzed_tab_a = analyze_stocks_batch(stocks_list)
        
        # Selector for active stock
        options_a = ["請選擇..."] + [f"{item['code']} - {item['name']}" for item in analyzed_tab_a]
        selected_a = st.selectbox("🎯 選擇欲分析的熱門股進行試算及看圖", options_a, index=0, key="select_tab_a")
        if selected_a != "請選擇...":
            st.session_state.selected_stock_code = selected_a.split(" - ")[0]
            
        # Draw table
        html_tab_a = render_stocks_table_html(analyzed_tab_a, st.session_state.selected_stock_code)
        st.markdown(html_tab_a, unsafe_allow_html=True)
        
        # Delete stock manual support
        st.write("")
        delete_col1, delete_col2 = st.columns([2, 1])
        with delete_col2:
            manual_stocks = [s for s in stocks_list if s.get("added_by") in ["manual", "text"]]
            if manual_stocks:
                del_target = st.selectbox("🗑️ 取消追蹤自訂股", [f"{s['code']} - {s['name']}" for s in manual_stocks], index=0)
                if st.button("確認刪除"):
                    del_code = del_target.split(" - ")[0]
                    updated_stocks = [s for s in stocks_list if s["code"] != del_code]
                    write_stock_list(updated_stocks)
                    if st.session_state.selected_stock_code == del_code:
                        st.session_state.selected_stock_code = None
                    st.success("已取消追蹤該自訂個股！")
                    st.rerun()

    # Tab B
    with tab_b:
        st.subheader("🔍 全市場底部潛力股")
        
        scan_state = get_scan_state()
        
        col_scan1, col_scan2 = st.columns([3, 1])
        with col_scan1:
            if scan_state.active:
                st.warning("⚠️ 全市場掃描正在進行中，請稍候...")
                pct = int((scan_state.progress / scan_state.total) * 100) if scan_state.total > 0 else 0
                st.progress(pct / 100.0)
                st.write(f"進度: {scan_state.progress} / {scan_state.total} 檔 ({pct}%) - {scan_state.message}")
            else:
                st.info("點擊右方按鈕即可啟動全市場 1,900+ 檔股票掃描 (約需 30~40 秒)。")
        with col_scan2:
            if st.button("⚡ 重新掃描全市場", disabled=scan_state.active):
                run_all_market_scan_async()
                st.rerun()
                
        # Load scanned potential stocks
        potentials_path = get_file_path("potential_stocks.json")
        if os.path.exists(potentials_path):
            with open(potentials_path, "r", encoding="utf-8") as f:
                analyzed_tab_b = json.load(f)
        else:
            analyzed_tab_b = []
            
        options_b = ["請選擇..."] + [f"{item['code']} - {item['name']}" for item in analyzed_tab_b]
        selected_b = st.selectbox("🎯 選擇欲分析的潛力股進行試算及看圖", options_b, index=0, key="select_tab_b")
        if selected_b != "請選擇...":
            st.session_state.selected_stock_code = selected_b.split(" - ")[0]
            
        html_tab_b = render_stocks_table_html(analyzed_tab_b, st.session_state.selected_stock_code)
        st.markdown(html_tab_b, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# Find the active stock object across both lists
selected_stock_obj = None
if st.session_state.selected_stock_code:
    selected_stock_obj = next((s for s in analyzed_tab_a if s["code"] == st.session_state.selected_stock_code), None)
    if not selected_stock_obj:
        selected_stock_obj = next((s for s in analyzed_tab_b if s["code"] == st.session_state.selected_stock_code), None)

# ----------------- RIGHT COLUMN (CALCULATOR, DETAILS & CHARTS) -----------------
with col_right:
    if not selected_stock_obj:
        st.markdown("""
        <div class="glass-panel" style="text-align: center; padding: 5rem 2rem; color: #94a3b8;">
            <i class="fa-solid fa-calculator" style="font-size: 3rem; margin-bottom: 1.5rem; display: block; color: rgba(255,255,255,0.1);"></i>
            <h3>請先在左方列表選擇一檔股票，載入風控計算機與技術指標圖表。</h3>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Stock Details & Signal Card
        st.markdown(f'<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader(f"📈 {selected_stock_obj['name']} ({selected_stock_obj['code']}) 技術面分析")
        
        det_col1, det_col2 = st.columns(2)
        with det_col1:
            st.write(f"當前收盤價: **${selected_stock_obj['current_price']}**")
            st.write(f"今日成交量: **{selected_stock_obj['volume_lots']:,} 張**")
            
            trend_dot = "green" if selected_stock_obj["daily_trend_ok"] else "red"
            trend_text = "符合多頭" if selected_stock_obj["daily_trend_ok"] else "未符合多頭"
            st.markdown(f"日線趨勢: <span class='light-dot {trend_dot}'></span> **{trend_text}**", unsafe_allow_html=True)
            
            kd_dot = "green" if selected_stock_obj["hourly_kd_ok"] else "red"
            st.markdown(f"60分K KD: <span class='light-dot {kd_dot}'></span> **金叉 {selected_stock_obj['golden_cross_count']} 次**", unsafe_allow_html=True)
            
        with det_col2:
            st.write("五大策略符合狀態:")
            st.markdown(render_strategy_lights_html(selected_stock_obj["signals"]), unsafe_allow_html=True)
            st.write("")
            
            sig_class = "active" if selected_stock_obj["system_a_signal"] else "inactive"
            sig_text = "符合進場" if selected_stock_obj["system_a_signal"] else "未符合進場"
            st.markdown(f"系統進場訊號: <span class='signal-badge {sig_class}'>{sig_text}</span>", unsafe_allow_html=True)
            
        st.markdown('</div>', unsafe_allow_html=True)

        # Active Simulated Portfolio Monitors (Moved up here)
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("🛡️ 當前模擬風控監控清單")
        
        orders_path = get_file_path("orders_store.json")
        orders_list = []
        if os.path.exists(orders_path):
            try:
                with open(orders_path, "r", encoding="utf-8") as f:
                    orders_list = json.load(f)
            except Exception:
                pass
                
        if not orders_list:
            st.info("目前無進行中的模擬風控監控項目。")
        else:
            # Render a custom HTML table for active portfolios
            html_monitors = """
            <table class="stock-table" style="font-size:0.8rem;">
                <thead>
                    <tr>
                        <th>個股</th>
                        <th>買入價/數量</th>
                        <th>最新報價</th>
                        <th>停損條件</th>
                        <th>停利條件</th>
                        <th>狀態</th>
                        <th>操作</th>
                    </tr>
                </thead>
                <tbody>
            """
            for idx, o in enumerate(orders_list):
                status_class = o["status"].lower()
                status_text = o["status"]
                if o["status"] == "MONITORING":
                    status_text = "監控中"
                elif o["status"] == "CANCELLED":
                    status_text = "已取消"
                elif o["status"] == "STOP_LOSS_TRIGGERED":
                    status_text = "已停損觸發"
                elif o["status"] == "TAKE_PROFIT_TRIGGERED":
                    status_text = "已停利觸發"
                    
                qty_text = f"{o['quantity'] / 1000} 張" if o.get("lot_type") == "ROUND" else f"{o['quantity']} 股"
                
                # Check status color
                status_color = "#34d399" if "PROFIT" in o["status"] else ("#f87171" if "LOSS" in o["status"] else "#f59e0b")
                
                # Buttons will be handled natively below the table for safety, but we display the HTML rows first
                html_monitors += f"""
                <tr>
                    <td><b>{o['name']}</b><br/><span style="font-size:0.7rem; color:#94a3b8;">{o['code']}</span></td>
                    <td>${o['buy_price']:.2f}<br/><span style="font-size:0.7rem; color:#94a3b8;">{qty_text}</span></td>
                    <td style="color:#f59e0b; font-weight:700;">${o.get('last_price', o['buy_price']):.2f}</td>
                    <td style="color:#f87171;">&le; ${o['stop_loss_price']:.2f}</td>
                    <td style="color:#34d399;">&ge; ${o['stop_profit_price']:.2f}</td>
                    <td><span style="color:{status_color}; font-weight:700;">{status_text}</span></td>
                    <td><code>{o['order_id'][:8]}</code></td>
                </tr>
                """
            html_monitors += "</tbody></table>"
            st.markdown(html_monitors, unsafe_allow_html=True)
            
            # Action button triggers below the table
            st.write("監控項目管理操作:")
            act_col1, act_col2 = st.columns(2)
            with act_col1:
                monitoring_items = [o for o in orders_list if o["status"] == "MONITORING"]
                if monitoring_items:
                    cancel_target = st.selectbox("🛑 選擇欲取消監控的個股", [f"{o['name']} ({o['code']})" for o in monitoring_items], key="cancel_select")
                    if st.button("取消風控監控"):
                        target_code = cancel_target.split(" (")[-1].replace(")", "")
                        for o in orders_list:
                            if o["code"] == target_code and o["status"] == "MONITORING":
                                o["status"] = "CANCELLED"
                                o["message"] = "使用者手動取消監控"
                        with open(orders_path, "w", encoding="utf-8") as f:
                            json.dump(orders_list, f, ensure_ascii=False, indent=2)
                        st.success(f"已取消對 {target_code} 的模擬監控。")
                        st.rerun()
            with act_col2:
                ended_items = [o for o in orders_list if o["status"] != "MONITORING"]
                if ended_items:
                    delete_target = st.selectbox("🗑️ 選擇欲刪除歷史紀錄的個股", [f"{o['name']} ({o['code']}) - {o['order_id'][:8]}" for o in ended_items], key="delete_select")
                    if st.button("刪除歷史紀錄"):
                        target_id = delete_target.split(" - ")[-1]
                        orders_list = [o for o in orders_list if not o["order_id"].startswith(target_id)]
                        with open(orders_path, "w", encoding="utf-8") as f:
                            json.dump(orders_list, f, ensure_ascii=False, indent=2)
                        st.success("模擬交易歷史紀錄刪除成功！")
                        st.rerun()
                        
        st.markdown('</div>', unsafe_allow_html=True)

        # Calculator Parameters and Prefill Cards
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("🧮 倉位與風控計算器")
        
        calc_mode = st.selectbox("交易模式", ["零股 (按股數計算)", "整股 (按張數計算，1張=1000股)"], index=0)
        
        # Dynamic inputs
        price_val = st.number_input("設定買入價格 (台幣)", min_value=0.1, max_value=10000.0, value=float(selected_stock_obj["current_price"]), step=0.1, key="target_buy_price")
        
        if calc_mode.startswith("整股"):
            # Round Lot mode: input sheets/lots
            lots_val = st.number_input("預計買入張數 (張)", min_value=1, max_value=10000, value=1, step=1)
            shares = lots_val * 1000
            actual_cost = shares * price_val
        else:
            # Odd Lot mode: input investment amount
            invest_val = st.number_input("預計投入金額 (台幣)", min_value=100, max_value=10000000, value=100000, step=1000)
            shares = int(invest_val // price_val)
            actual_cost = shares * price_val
            
        stop_loss_pct = st.number_input("停損比例 (%)", min_value=1, max_value=50, value=5, step=1)
        
        # Calculations
        stop_loss_price = round(price_val * (1 - stop_loss_pct / 100), 2)
        stop_profit_price = selected_stock_obj.get("prev_high") or round(price_val * 1.1, 2)
        if stop_profit_price <= price_val:
            stop_profit_price = round(price_val * 1.1, 2)
            
        max_loss = (price_val - stop_loss_price) * shares
        max_profit = (stop_profit_price - price_val) * shares
        
        r_value = 0.0
        risk_diff = price_val - stop_loss_price
        if risk_diff > 0:
            r_value = (stop_profit_price - price_val) / risk_diff
            
        # Display calculator results
        res_col1, res_col2 = st.columns(2)
        with res_col1:
            st.markdown(f"""
            <div style="background:rgba(0,0,0,0.15); padding:10px; border-radius:8px; border:1px solid rgba(255,255,255,0.03); margin-bottom:10px;">
                <span style="font-size:0.75rem; color:#94a3b8; display:block;">預估買入數量</span>
                <span style="font-size:1.3rem; font-weight:700; color:#fff;">{shares:,} 股</span>
                <span style="font-size:0.75rem; color:#94a3b8; display:block;">實質花費: NT$ {int(actual_cost):,}</span>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"""
            <div style="background:rgba(239,68,68,0.05); padding:10px; border-radius:8px; border:1px solid rgba(239,68,68,0.15); margin-bottom:10px;">
                <span style="font-size:0.75rem; color:#94a3b8; display:block;">嚴格 {stop_loss_pct}% 停損價格</span>
                <span style="font-size:1.3rem; font-weight:700; color:#f87171;">${stop_loss_price:.2f}</span>
                <span style="font-size:0.75rem; color:#f87171; display:block;">預期最大虧損: NT$ -{int(max_loss):,}</span>
            </div>
            """, unsafe_allow_html=True)
            
        with res_col2:
            st.markdown(f"""
            <div style="background:rgba(16,185,129,0.05); padding:10px; border-radius:8px; border:1px solid rgba(16,185,129,0.15); margin-bottom:10px;">
                <span style="font-size:0.75rem; color:#94a3b8; display:block;">預估前高停利價格</span>
                <span style="font-size:1.3rem; font-weight:700; color:#34d399;">${stop_profit_price:.2f}</span>
                <span style="font-size:0.75rem; color:#34d399; display:block;">預估潛在獲利: NT$ +{int(max_profit):,}</span>
            </div>
            """, unsafe_allow_html=True)
            
            r_bg = "rgba(16,185,129,0.1)" if r_value >= 2.0 else ("rgba(245,158,11,0.1)" if r_value >= 1.0 else "rgba(239,68,68,0.1)")
            r_color = "#34d399" if r_value >= 2.0 else ("#f59e0b" if r_value >= 1.0 else "#f87171")
            r_comment = "高風暴比 (≥ 2.0，值得進場)" if r_value >= 2.0 else ("中風暴比 (1.0 ~ 2.0，審慎評估)" if r_value >= 1.0 else "低風暴比 (< 1.0，不符賺賠比)")
            
            st.markdown(f"""
            <div style="background:{r_bg}; padding:10px; border-radius:8px; border:1px solid {r_color}40; margin-bottom:10px;">
                <span style="font-size:0.75rem; color:#94a3b8; display:block;">預期風暴比 (R值)</span>
                <span style="font-size:1.3rem; font-weight:700; color:{r_color};">{r_value:.2f}</span>
                <span style="font-size:0.75rem; color:{r_color}; display:block;">{r_comment}</span>
            </div>
            """, unsafe_allow_html=True)
            
        # Submit simulated order action
        if st.button("🚀 送出模擬限價委託並啟動背景風控監控", use_container_width=True):
            if shares <= 0:
                st.error("委託股數必須大於 0！")
            else:
                new_order = {
                    "code": selected_stock_obj["code"],
                    "symbol": selected_stock_obj["symbol"],
                    "name": selected_stock_obj["name"].split(" (")[0],
                    "action": "BUY",
                    "buy_price": price_val,
                    "quantity": shares,
                    "stop_loss_price": stop_loss_price,
                    "stop_profit_price": stop_profit_price,
                    "lot_type": "ROUND" if calc_mode.startswith("整股") else "ODD",
                    "status": "MONITORING",
                    "order_id": f"mock-{'round' if calc_mode.startswith('整股') else 'odd'}-buy-{selected_stock_obj['code']}-{int(time.time())}",
                    "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "last_price": price_val,
                    "dry_run": True,
                    "trigger_order_id": None,
                    "message": "已建立模擬委託並啟動風控監控"
                }
                
                # Load existing and save
                try:
                    orders_curr = []
                    if os.path.exists(orders_path):
                        with open(orders_path, "r", encoding="utf-8") as f:
                            orders_curr = json.load(f)
                    orders_curr.append(new_order)
                    with open(orders_path, "w", encoding="utf-8") as f:
                        json.dump(orders_curr, f, ensure_ascii=False, indent=2)
                    st.success("模擬委託送出成功！已啟動背景觸價風控監控。")
                    st.rerun()
                except Exception as err:
                    st.error(f"下單失敗: {err}")
                    
        st.markdown('</div>', unsafe_allow_html=True)

        # ----------------- ECHARTS SECTION (INTRADAYS, DAILY K, HOURLY KD, INSTITUTIONAL) -----------------
        
        # Load charts data from yfinance
        try:
            ticker = yf.Ticker(selected_stock_obj["symbol"])
            
            # 1. Fetch Intraday Data (latest 5 days to isolate today and yesterday)
            df_intra = ticker.history(period="5d", interval="2m")
            intraday_list = []
            prev_intraday_list = []
            
            if not df_intra.empty:
                df_intra['date_str'] = df_intra.index.map(lambda x: x.strftime("%Y-%m-%d"))
                unique_dates = sorted(df_intra['date_str'].unique())
                
                if len(unique_dates) >= 1:
                    latest_date = unique_dates[-1]
                    df_latest = df_intra[df_intra['date_str'] == latest_date]
                    for idx, row in df_latest.iterrows():
                        intraday_list.append({
                            "time": idx.strftime("%H:%M"),
                            "price": float(row["Close"]),
                            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                        })
                        
                if len(unique_dates) >= 2:
                    prev_date = unique_dates[-2]
                    df_prev = df_intra[df_intra['date_str'] == prev_date]
                    for idx, row in df_prev.iterrows():
                        prev_intraday_list.append({
                            "time": idx.strftime("%H:%M"),
                            "price": float(row["Close"]),
                            "volume": int(row["Volume"]) if not pd.isna(row["Volume"]) else 0
                        })
                        
            # 2. Daily K-line Data
            df_daily_k = ticker.history(period="3mo", interval="1d")
            kline_list = []
            if not df_daily_k.empty:
                df_daily_k['SMA5'] = df_daily_k['Close'].rolling(window=5).mean()
                df_daily_k['SMA20'] = df_daily_k['Close'].rolling(window=20).mean()
                
                df_recent = df_daily_k.tail(40)
                for idx, row in df_recent.iterrows():
                    kline_list.append({
                        "date": idx.strftime("%Y/%m/%d"),
                        "open": float(row["Open"]),
                        "close": float(row["Close"]),
                        "low": float(row["Low"]),
                        "high": float(row["High"]),
                        "sma5": float(row["SMA5"]) if not pd.isna(row["SMA5"]) else None,
                        "sma20": float(row["SMA20"]) if not pd.isna(row["SMA20"]) else None
                    })
                    
            # 3. Hourly KD Data
            df_hourly_k = ticker.history(period="2mo", interval="60m")
            kd_list = []
            if not df_hourly_k.empty:
                df_hourly_kd = calculate_kd(df_hourly_k)
                df_h_recent = df_hourly_kd.tail(40)
                for idx, row in df_h_recent.iterrows():
                    kd_list.append({
                        "time": idx.strftime("%m/%d %H:%M"),
                        "k": float(row["K"]),
                        "d": float(row["D"])
                    })
                    
            # 4. Institutional Net buy/sell
            inst_list = fetch_institutional_data(selected_stock_obj["symbol"])
            
        except Exception as chart_fetch_err:
            st.error(f"載入圖表數據時發生錯誤: {chart_fetch_err}")
            intraday_list, prev_intraday_list, kline_list, kd_list, inst_list = [], [], [], [], []

        # Today Intraday Chart Card
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("🕒 建議掛單與今日走勢")
        if not intraday_list:
            st.info("今日無即時交易數據")
        else:
            # Prefill buttons for Today
            t_open = intraday_list[0]["price"] if intraday_list else 0.0
            t_close = intraday_list[-1]["price"] if intraday_list else 0.0
            t_high = max(x["price"] for x in intraday_list) if intraday_list else 0.0
            t_low = min(x["price"] for x in intraday_list) if intraday_list else 0.0
            
            st.markdown(f"今日報價參考: 開盤 **${t_open:.2f}** | 最高 **${t_high:.2f}** | 最低 **${t_low:.2f}** | 收盤 **${t_close:.2f}**")
            
            avg_a = (t_open + t_close) / 2
            avg_m = (t_low + t_close) / 2
            avg_c = t_low
            
            p_col1, p_col2, p_col3 = st.columns(3)
            with p_col1:
                if st.button(f"積極 ${avg_a:.2f}", key="btn_today_a", use_container_width=True):
                    st.session_state.target_buy_price_value = avg_a
            with p_col2:
                if st.button(f"穩健 ${avg_m:.2f}", key="btn_today_m", use_container_width=True):
                    st.session_state.target_buy_price_value = avg_m
            with p_col3:
                if st.button(f"保守 ${avg_c:.2f}", key="btn_today_c", use_container_width=True):
                    st.session_state.target_buy_price_value = avg_c
                    
            # Render Today Intraday fold chart
            times_t = [x["time"] for x in intraday_list]
            prices_t = [x["price"] for x in intraday_list]
            vols_t = [x["volume"] for x in intraday_list]
            render_echarts_js("today-chart", "intraday", times_t, prices_t, vols_t)
        st.markdown('</div>', unsafe_allow_html=True)

        # Yesterday Intraday Chart Card
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("🕒 建議掛單與前一交易日走勢")
        if not prev_intraday_list:
            st.info("前一交易日無即時交易數據")
        else:
            p_open = prev_intraday_list[0]["price"] if prev_intraday_list else 0.0
            p_close = prev_intraday_list[-1]["price"] if prev_intraday_list else 0.0
            p_high = max(x["price"] for x in prev_intraday_list) if prev_intraday_list else 0.0
            p_low = min(x["price"] for x in prev_intraday_list) if prev_intraday_list else 0.0
            
            st.markdown(f"昨日報價參考: 開盤 **${p_open:.2f}** | 最高 **${p_high:.2f}** | 最低 **${p_low:.2f}** | 收盤 **${p_close:.2f}**")
            
            p_avg_a = (p_open + p_close) / 2
            p_avg_m = (p_low + p_close) / 2
            p_avg_c = p_low
            
            p_y_col1, p_y_col2, p_y_col3 = st.columns(3)
            with p_y_col1:
                if st.button(f"積極 ${p_avg_a:.2f}", key="btn_prev_a", use_container_width=True):
                    st.session_state.target_buy_price_value = p_avg_a
            with p_y_col2:
                if st.button(f"穩健 ${p_avg_m:.2f}", key="btn_prev_m", use_container_width=True):
                    st.session_state.target_buy_price_value = p_avg_m
            with p_y_col3:
                if st.button(f"保守 ${p_avg_c:.2f}", key="btn_prev_c", use_container_width=True):
                    st.session_state.target_buy_price_value = p_avg_c
                    
            # Render Yesterday Intraday fold chart (Greenish style)
            times_p = [x["time"] for x in prev_intraday_list]
            prices_p = [x["price"] for x in prev_intraday_list]
            vols_p = [x["volume"] for x in prev_intraday_list]
            render_echarts_js("prev-chart", "prev_intraday", times_p, prices_p, vols_p)
        st.markdown('</div>', unsafe_allow_html=True)

        # Daily K-Line Chart Card
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("📅 日K線技術指標圖 (近40日)")
        if not kline_list:
            st.info("無日K線數據")
        else:
            dates_k = [x["date"] for x in kline_list]
            candles_k = [[x["open"], x["close"], x["low"], x["high"]] for x in kline_list]
            sma5_k = [x["sma5"] for x in kline_list]
            sma20_k = [x["sma20"] for x in kline_list]
            render_echarts_js("kline-chart-st", "daily_kline", dates_k, candles_k, sma5_k, sma20_k)
        st.markdown('</div>', unsafe_allow_html=True)

        # Hourly KD Chart Card
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("📉 60分K KD 指標走勢 (近40根)")
        if not kd_list:
            st.info("無60分K KD數據")
        else:
            times_kd = [x["time"] for x in kd_list]
            k_val = [x["k"] for x in kd_list]
            d_val = [x["d"] for x in kd_list]
            render_echarts_js("kd-chart-st", "hourly_kd", times_kd, k_val, d_val)
        st.markdown('</div>', unsafe_allow_html=True)

        # Institutional Net Buy/Sell Card
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("🏛️ 三大法人買賣超統計 (近20日, 單位:張)")
        if not inst_list:
            st.info("無法人買賣超數據")
        else:
            dates_inst = [x["date"] for x in inst_list]
            foreign = [x["foreign"] for x in inst_list]
            trust = [x["trust"] for x in inst_list]
            dealer = [x["dealer"] for x in inst_list]
            render_echarts_js("inst-chart-st", "institutional", dates_inst, foreign, trust, dealer)
        st.markdown('</div>', unsafe_allow_html=True)

# Trigger auto-update of buy price from card select callbacks
if st.session_state.target_buy_price_value > 0.0:
    st.session_state.target_buy_price = st.session_state.target_buy_price_value
    st.session_state.target_buy_price_value = 0.0
    st.rerun()

# Poller sleep loop while scanner is running to automatically redraw progress bar
if scan_state.active:
    time.sleep(2.0)
    st.rerun()
