import yfinance as yf
import pandas as pd

symbol = "2330.TW"
print(f"Fetching data for {symbol}...")

try:
    ticker = yf.Ticker(symbol)
    
    # Fetch Daily
    print("Fetching daily data (1y, 1d)...")
    df_daily = ticker.history(period="1y", interval="1d")
    print(f"Daily shape: {df_daily.shape}")
    if not df_daily.empty:
        print("Latest daily row:")
        print(df_daily.tail(1))
    else:
        print("Daily df is empty!")
        
    # Fetch Hourly
    print("\nFetching hourly data (1mo, 60m)...")
    df_hourly = ticker.history(period="1mo", interval="60m")
    print(f"Hourly shape: {df_hourly.shape}")
    if not df_hourly.empty:
        print("Latest hourly row:")
        print(df_hourly.tail(1))
    else:
        print("Hourly df is empty!")

except Exception as e:
    print(f"Error fetching data: {e}")
