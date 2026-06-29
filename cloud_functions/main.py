import functions_framework
import json
import pandas as pd
import numpy as np
import requests
import datetime
from bs4 import BeautifulSoup
import re
from flask import jsonify, make_response

# ---------------------------------------------------------
# CORS & Helper Methods
# ---------------------------------------------------------
def cors_response(data, status=200):
    response = make_response(jsonify(data), status)
    # 設定 CORS 允許任何前端 Domain 跨域呼叫
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

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

# ---------------------------------------------------------
# Strategy Calculation Logic
# ---------------------------------------------------------
def calculate_kd(df, n=9, m1=3, m2=3):
    df = df.copy()
    low_n = df['Low'].rolling(window=n).min()
    high_n = df['High'].rolling(window=n).max()
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50.0)
    k_list, d_list = [], []
    k_val, d_val = 50.0, 50.0
    factor_k, factor_d = 1.0 / m1, 1.0 / m2
    for r in rsv:
        k_val = (1.0 - factor_k) * k_val + factor_k * r
        d_val = (1.0 - factor_d) * d_val + factor_d * k_val
        k_list.append(k_val)
        d_list.append(d_val)
    df['K'] = k_list
    df['D'] = d_list
    return df

def calculate_strategy_signals(df_daily):
    if df_daily.empty or len(df_daily) < 20:
        return {
            "vol_breakout": False, "undervalued": False,
            "breakout_5ma": False, "momentum": False, "mean_reversion": False
        }
    df = df_daily.copy()
    df['MA5'] = df['Close'].rolling(window=5).mean()
    df['MA10'] = df['Close'].rolling(window=10).mean()
    df['MA20'] = df['Close'].rolling(window=20).mean()
    df['Vol_MA20'] = df['Volume'].rolling(window=20).mean()
    
    close = float(df['Close'].iloc[-1])
    prev_close = float(df['Close'].iloc[-2]) if len(df) >= 2 else close
    volume = float(df['Volume'].iloc[-1])
    vol_ma20 = float(df['Vol_MA20'].iloc[-1]) if not pd.isna(df['Vol_MA20'].iloc[-1]) else 1.0
    
    vol_breakout = (close > prev_close) and (volume > 1.5 * vol_ma20)
    
    n_days = min(len(df), 120)
    recent_low = float(df['Low'].tail(n_days).min())
    recent_high = float(df['High'].tail(n_days).max())
    range_span = recent_high - recent_low
    undervalued = close < (recent_low + 0.3 * range_span) if range_span > 0 else False
        
    ma5 = float(df['MA5'].iloc[-1]) if not pd.isna(df['MA5'].iloc[-1]) else close
    prev_high_20 = float(df['High'].iloc[-21:-1].max()) if len(df) >= 21 else close
    breakout_5ma = (close > prev_high_20) and (close > ma5)
    
    ma10 = float(df['MA10'].iloc[-1]) if not pd.isna(df['MA10'].iloc[-1]) else close
    ma20 = float(df['MA20'].iloc[-1]) if not pd.isna(df['MA20'].iloc[-1]) else close
    momentum = (close > ma5) and (ma5 > ma10) and (ma10 > ma20)
    
    mean_reversion = (close < ma20 * 0.95) and (close > prev_close)
    
    return {
        "vol_breakout": bool(vol_breakout),
        "undervalued": bool(undervalued),
        "breakout_5ma": bool(breakout_5ma),
        "momentum": bool(momentum),
        "mean_reversion": bool(mean_reversion)
    }

def analyze_stock_logic(stock_code, df_daily):
    # This represents the core analysis logic per stock
    if len(df_daily) < 40:
        return None
        
    df_daily = calculate_kd(df_daily)
    df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
    df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
    
    close_price = float(df_daily['Close'].iloc[-1])
    ma20 = float(df_daily['MA20'].iloc[-1])
    ma60 = float(df_daily['MA60'].iloc[-1])
    
    # 日線多頭 (MA20 > MA60) - allow ma60 to be nan if < 60 days
    daily_trend_ok = ma20 > ma60 if not pd.isna(ma60) else True
    
    # 60分K打底 (模擬 KD 金叉)
    hourly_kd_ok = True
    golden_cross_count = 2 # 模擬值
    
    # 底底高 (Morph OK)
    morph_ok = True # 模擬值
    
    # 計算進階策略燈號
    signals = calculate_strategy_signals(df_daily)
    
    # 進場訊號
    system_a_signal = daily_trend_ok and hourly_kd_ok and morph_ok
    
    # 預期風暴比 (R-value)
    r_value = 2.5 # 模擬值
    
    return {
        "code": stock_code,
        "name": stock_code, # 名字需另行查詢，此處簡化
        "current_price": close_price,
        "volume_lots": int(df_daily['Volume'].iloc[-1] / 1000),
        "daily_trend_ok": bool(daily_trend_ok),
        "hourly_kd_ok": bool(hourly_kd_ok),
        "golden_cross_count": golden_cross_count,
        "morph_ok": bool(morph_ok),
        "system_a_signal": bool(system_a_signal),
        "signals": signals,
        "r_value": r_value
    }

def fetch_finmind_data(stock_code, days=120):
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=days)
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={stock_code}&start_date={start_date}&end_date={end_date}"
    try:
        res = requests.get(url, timeout=10)
        data = res.json().get('data', [])
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        # Rename columns to match what analyze_stock_logic expects
        df = df.rename(columns={
            'open': 'Open',
            'max': 'High',
            'min': 'Low',
            'close': 'Close',
            'Trading_Volume': 'Volume',
            'date': 'Date'
        })
        df['Date'] = pd.to_datetime(df['Date'])
        df.set_index('Date', inplace=True)
        return df
    except Exception as e:
        print(f"FinMind error for {stock_code}: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# Entry Point (Cloud Function)
# ---------------------------------------------------------
@functions_framework.http
def stock_api(request):
    """HTTP Cloud Function."""
    
    # 處理 CORS Preflight Request
    if request.method == 'OPTIONS':
        headers = {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
            'Access-Control-Max-Age': '3600'
        }
        return ('', 204, headers)
        
    path = request.path

    # Tab A: manual add stock
    if request.method == 'POST' and (path == '/api/stocks' or path == '/stocks'):
        try:
            req_json = request.get_json(silent=True)
            if req_json and 'code' in req_json:
                code = req_json['code']
                df = fetch_finmind_data(code)
                df = df.dropna()
                if not df.empty:
                    res = analyze_stock_logic(code, df)
                    if res:
                        return cors_response([clean_nan(res)])
            return cors_response([])
        except Exception as e:
            return cors_response({"error": str(e)}, 500)

    # General Scan
    if path in ['/api/stocks/scan', '/scan', '/stocks/analyze', '/stocks/potential', '/api/stocks/analyze', '/api/stocks/potential']:
        test_tickers = ["2330", "2317", "2454", "2308", "2881", "2382", "3231", "2603", "2609", "2615"]
        try:
            # Download individually to guarantee stable format
            results = []
            debug_info = []
            for code in test_tickers:
                try:
                    df = fetch_finmind_data(code)
                    if df.empty:
                        debug_info.append(f"{code}: empty df")
                        continue
                    df = df.dropna()
                    if df.empty:
                        debug_info.append(f"{code}: empty after dropna")
                        continue
                    res = analyze_stock_logic(code, df)
                    if res:
                        results.append(res)
                    else:
                        debug_info.append(f"{code}: analyze_stock_logic returned None. len(df)={len(df)}")
                except Exception as e:
                    debug_info.append(f"{code} exception: {str(e)}")
                    continue
            
            if not results:
                return cors_response({"error": "No results", "debug": debug_info})
            return cors_response(clean_nan(results))
        except Exception as e:
            return cors_response({"error": str(e)}, 500)
            return cors_response({"error": str(e)}, 500)

    # Health Check
    return cors_response({"status": "Cloud Function API is running!", "endpoints": ["/scan", "/stocks/analyze", "/stocks/potential"]})
