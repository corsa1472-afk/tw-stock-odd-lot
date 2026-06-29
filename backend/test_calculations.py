import yfinance as yf
import pandas as pd
import numpy as np

def calculate_kd(df, n=9, m1=3, m2=3):
    """
    Calculate KD(9,3,3) for hourly data.
    Formula:
    RSV = (Close - Low_n) / (High_n - Low_n) * 100
    K = 2/3 * K_prev + 1/3 * RSV
    D = 2/3 * D_prev + 1/3 * K
    """
    df = df.copy()
    low_n = df['Low'].rolling(window=n).min()
    high_n = df['High'].rolling(window=n).max()
    
    # Calculate RSV
    rsv = (df['Close'] - low_n) / (high_n - low_n) * 100
    rsv = rsv.fillna(50.0) # Fill NaNs
    
    k_list = []
    d_list = []
    k_val = 50.0
    d_val = 50.0
    
    # Calculate K and D recursively
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

def analyze_system_a(symbol):
    print(f"\n--- Analyzing {symbol} for System A ---")
    
    # 1. Fetch Daily Data (1 year)
    ticker = yf.Ticker(symbol)
    df_daily = ticker.history(period="1y", interval="1d")
    if df_daily.empty or len(df_daily) < 60:
        print("Not enough daily data.")
        return None
        
    # Calculate 20 MA and 60 MA
    df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
    df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
    
    latest_close = df_daily['Close'].iloc[-1]
    latest_ma20 = df_daily['MA20'].iloc[-1]
    latest_ma60 = df_daily['MA60'].iloc[-1]
    
    # Condition 1: Price above 20MA and 60MA, and 20MA > 60MA (long alignment)
    daily_trend_ok = latest_close > latest_ma20 and latest_close > latest_ma60 and latest_ma20 > latest_ma60
    
    # Daily peak (stop profit target) over last 60 days
    prev_high = df_daily['High'].tail(60).max()
    
    # 2. Fetch Hourly Data (1 month)
    df_hourly = ticker.history(period="1mo", interval="60m")
    if df_hourly.empty or len(df_hourly) < 20:
        print("Not enough hourly data.")
        return None
        
    # Calculate KD
    df_hourly = calculate_kd(df_hourly)
    
    latest_k = df_hourly['K'].iloc[-1]
    latest_d = df_hourly['D'].iloc[-1]
    
    # Condition 2a: KD under 50
    kd_under_50 = latest_k < 50 and latest_d < 50
    
    # Condition 2b: Count golden crosses at low level (< 40) in recent 60 hourly bars
    # A golden cross happens when K_t-1 <= D_t-1 and K_t > D_t
    # Low level means either K_t < 40 or cross value is < 40
    recent_hourly = df_hourly.tail(60).copy()
    
    crosses = []
    for i in range(1, len(recent_hourly)):
        k_prev, d_prev = recent_hourly['K'].iloc[i-1], recent_hourly['D'].iloc[i-1]
        k_curr, d_curr = recent_hourly['K'].iloc[i], recent_hourly['D'].iloc[i]
        
        # Check for golden cross
        if k_prev <= d_prev and k_curr > d_curr:
            # Check if it is at low level (< 40)
            if k_curr < 40:
                timestamp = recent_hourly.index[i]
                crosses.append((timestamp, k_curr))
                
    golden_cross_count = len(crosses)
    # Target: 2 or 3 times
    hourly_kd_ok = 2 <= golden_cross_count <= 3
    
    # Summary of System A Signal
    system_a_signal = daily_trend_ok and kd_under_50 and hourly_kd_ok
    
    result = {
        "symbol": symbol,
        "current_price": round(latest_close, 2),
        "daily_ma20": round(latest_ma20, 2),
        "daily_ma60": round(latest_ma60, 2),
        "daily_trend_ok": daily_trend_ok,
        "prev_high": round(prev_high, 2),
        "latest_k": round(latest_k, 2),
        "latest_d": round(latest_d, 2),
        "kd_under_50": kd_under_50,
        "golden_cross_count": golden_cross_count,
        "hourly_kd_ok": hourly_kd_ok,
        "system_a_signal": system_a_signal,
        "crosses": [(str(t), round(v, 2)) for t, v in crosses]
    }
    
    print(f"Current Price: {result['current_price']}")
    print(f"MA20: {result['daily_ma20']} | MA60: {result['daily_ma60']}")
    print(f"Daily Trend OK (Price > MA20 > MA60): {result['daily_trend_ok']}")
    print(f"Hourly K: {result['latest_k']} | D: {result['latest_d']}")
    print(f"KD Under 50: {result['kd_under_50']}")
    print(f"Golden Crosses (<40) Count (last 60h): {result['golden_cross_count']}")
    for t, v in result['crosses']:
        print(f"  Cross at {t} value {v}")
    print(f"Hourly KD OK (Cross count is 2 or 3): {result['hourly_kd_ok']}")
    print(f"System A Buy Signal: {result['system_a_signal']}")
    print(f"Daily 60-day High (Stop Profit Price): {result['prev_high']}")
    
    return result

if __name__ == "__main__":
    analyze_system_a("2330.TW")
