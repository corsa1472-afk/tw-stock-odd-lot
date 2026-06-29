import yfinance as yf
import pandas as pd
import numpy as np
import requests
import re
import json
from urllib.parse import urlparse

def calculate_kd(df, n=9, m1=3, m2=3):
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
                
            # Grab latest 20 days
            recent_trades = trades[-20:]
            result = []
            for t in recent_trades:
                result.append({
                    "date": t.get("formattedDate", t.get("date", "")[:10]),
                    "foreign": t.get("foreignDiffVolK", 0),
                    "trust": t.get("investmentTrustDiffVolK", 0),
                    "dealer": t.get("dealerDiffVolK", 0)
                })
            return result
    except Exception as e:
        print(f"Error fetching institutional data: {e}")
    return []

def get_chart_data(symbol):
    print(f"--- Fetching chart data for {symbol} ---")
    ticker = yf.Ticker(symbol)
    
    # 1. Intraday (1d, 2m)
    print("Fetching intraday...")
    df_intra = ticker.history(period="1d", interval="2m")
    intraday_data = []
    if not df_intra.empty:
        for idx, row in df_intra.iterrows():
            # Format time as HH:MM
            time_str = idx.strftime("%H:%M")
            intraday_data.append({
                "time": time_str,
                "price": round(row["Close"], 2)
            })
            
    # 2. Daily K-line & Volume (last 40 days)
    print("Fetching daily K-line...")
    df_daily = ticker.history(period="3mo", interval="1d")
    kline_data = []
    if not df_daily.empty:
        df_daily_recent = df_daily.tail(40)
        for idx, row in df_daily_recent.iterrows():
            date_str = idx.strftime("%Y/%m/%d")
            kline_data.append({
                "date": date_str,
                "open": round(row["Open"], 2),
                "high": round(row["High"], 2),
                "low": round(row["Low"], 2),
                "close": round(row["Close"], 2),
                "volume": int(row["Volume"])
            })
            
    # 3. KD lines (60m, last 40 bars)
    print("Fetching hourly KD...")
    df_hourly = ticker.history(period="1mo", interval="60m")
    kd_data = []
    if not df_hourly.empty:
        df_hourly_kd = calculate_kd(df_hourly)
        df_hourly_recent = df_hourly_kd.tail(40)
        for idx, row in df_hourly_recent.iterrows():
            # Format datetime as MM/DD HH:MM
            datetime_str = idx.strftime("%m/%d %H:%M")
            kd_data.append({
                "time": datetime_str,
                "k": round(row["K"], 2),
                "d": round(row["D"], 2)
            })
            
    # 4. Institutional
    print("Fetching institutional...")
    inst_data = fetch_institutional_data(symbol)
    
    chart_payload = {
        "symbol": symbol,
        "intraday": intraday_data,
        "kline": kline_data,
        "kd": kd_data,
        "institutional": inst_data
    }
    
    return chart_payload

if __name__ == "__main__":
    payload = get_chart_data("2330.TW")
    print(f"\nIntraday bars: {len(payload['intraday'])}")
    if payload['intraday']:
        print("  Sample:", payload['intraday'][0], "to", payload['intraday'][-1])
        
    print(f"K-line bars: {len(payload['kline'])}")
    if payload['kline']:
        print("  Sample:", payload['kline'][0], "to", payload['kline'][-1])
        
    print(f"KD bars: {len(payload['kd'])}")
    if payload['kd']:
        print("  Sample:", payload['kd'][0], "to", payload['kd'][-1])
        
    print(f"Institutional records: {len(payload['institutional'])}")
    if payload['institutional']:
        print("  Sample:", payload['institutional'][0], "to", payload['institutional'][-1])
