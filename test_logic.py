import yfinance as yf
import pandas as pd
import numpy as np

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
    if len(df_daily) < 40:
        return None
        
    df_daily = calculate_kd(df_daily)
    df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
    df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
    
    close_price = float(df_daily['Close'].iloc[-1])
    ma20 = float(df_daily['MA20'].iloc[-1])
    ma60 = float(df_daily['MA60'].iloc[-1])
    
    daily_trend_ok = ma20 > ma60 if not pd.isna(ma60) else True
    hourly_kd_ok = True
    golden_cross_count = 2
    morph_ok = True
    signals = calculate_strategy_signals(df_daily)
    system_a_signal = daily_trend_ok and hourly_kd_ok and morph_ok
    
    return {
        "code": stock_code,
        "name": stock_code,
        "current_price": close_price,
        "volume_lots": int(df_daily['Volume'].iloc[-1] / 1000),
        "daily_trend_ok": bool(daily_trend_ok),
        "system_a_signal": bool(system_a_signal)
    }

print("Running test...")
test_tickers = ["2330.TW", "2317.TW"]
results = []
for ticker in test_tickers:
    code = ticker.replace(".TW", "")
    try:
        df = yf.Ticker(ticker).history(period="60d", auto_adjust=False)
        df = df.dropna()
        res = analyze_stock_logic(code, df)
        if res:
            results.append(res)
    except Exception as e:
        print("Error:", e)
print("Results:", results)
