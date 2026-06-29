import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urlparse
import yfinance as yf
import pandas as pd
import os

def fetch_trending_stocks():
    """
    Scrape Yahoo Finance Taiwan's community trending and other market rank pages.
    Returns a list of dicts: [{'symbol': '2330.TW', 'code': '2330', 'name': '台積電'}]
    """
    urls = [
        "https://tw.stock.yahoo.com/community/rank/active",
        "https://tw.stock.yahoo.com/rank/volume?exchange=TAI",
        "https://tw.stock.yahoo.com/rank/turnover?exchange=TAI",
        "https://tw.stock.yahoo.com/rank/change-up?exchange=TAI",
        "https://tw.stock.yahoo.com/rank/foreign-investor-buy?exchange=TAI&period=day"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
    }
    
    trending_list = []
    seen = set()
    
    # Extract up to 35 stocks from each page to ensure list coverage
    for i, url in enumerate(urls):
        print(f"Fetching popular stocks from {url}...")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                print(f"Failed to fetch rank page {url}: HTTP {response.status_code}")
                continue
                
            soup = BeautifulSoup(response.content, "lxml")
            links = soup.find_all("a", href=True)
            
            page_stocks = []
            page_seen = set()
            
            for link in links:
                href = link['href']
                parsed_url = urlparse(href)
                path = parsed_url.path.strip('/')
                parts = path.split('/')
                
                # Match standard pattern quote/2330.TW, only support listed (.TW)
                if len(parts) == 2 and parts[0] == 'quote' and re.match(r'^[0-9A-Z]{4,6}\.TW$', parts[1]):
                    symbol = parts[1] # e.g. 2330.TW
                    code = symbol.split('.')[0]
                    
                    parent = link.parent
                    strings = list(parent.stripped_strings)
                    
                    name = "未知股名"
                    if strings:
                        clean_strings = [s for s in strings if s != symbol and s != code and not s.startswith('/')]
                        if clean_strings:
                            name = clean_strings[0]
                    
                    if symbol not in page_seen:
                        page_seen.add(symbol)
                        page_stocks.append({
                            "symbol": symbol,
                            "code": code,
                            "name": name
                        })
            
            limit = 35
            for item in page_stocks[:limit]:
                if item["symbol"] not in seen:
                    seen.add(item["symbol"])
                    trending_list.append(item)
        except Exception as e:
            print(f"Error scraping rank page {url}: {e}")
            
    # If we didn't scrape enough, merge with defaults
    if not trending_list:
        defaults = get_default_popular_stocks()
        for d in defaults:
            if d["symbol"] not in seen:
                seen.add(d["symbol"])
                trending_list.append(d)
                
    # Remove any items with name "新版個股健診" or similar error values
    cleaned_list = []
    for item in trending_list:
        if "健診" in item["name"] or "價格" in item["name"] or "未知" in item["name"]:
            # Try to map correct name
            item["name"] = get_stock_name_map().get(item["code"], item["name"])
        cleaned_list.append(item)
        
    return cleaned_list

def get_default_popular_stocks():
    return [
        {"symbol": "2330.TW", "code": "2330", "name": "台積電"},
        {"symbol": "2317.TW", "code": "2317", "name": "鴻海"},
        {"symbol": "2454.TW", "code": "2454", "name": "聯發科"},
        {"symbol": "2382.TW", "code": "2382", "name": "廣達"},
        {"symbol": "3231.TW", "code": "3231", "name": "緯創"},
        {"symbol": "2308.TW", "code": "2308", "name": "台達電"},
        {"symbol": "2603.TW", "code": "2603", "name": "長榮"},
        {"symbol": "2881.TW", "code": "2881", "name": "富邦金"},
        {"symbol": "2882.TW", "code": "2882", "name": "國泰金"},
        {"symbol": "2303.TW", "code": "2303", "name": "聯電"}
    ]

def get_stock_name_map():
    return {
        "2330": "台積電",
        "2317": "鴻海",
        "2454": "聯發科",
        "2382": "廣達",
        "3231": "緯創",
        "2308": "台達電",
        "2603": "長榮",
        "2881": "富邦金",
        "2882": "國泰金",
        "2303": "聯電",
        "3481": "群創",
        "2409": "友達",
        "2344": "華邦電",
        "6770": "力積電",
        "2408": "南亞科",
        "2324": "仁寶",
        "2327": "國巨",
        "0050": "元大台灣50",
        "6116": "彩晶",
        "2337": "旺宏",
        "2356": "英業達",
        "2353": "宏碁",
        "2313": "華通"
    }

def fetch_stock_history(symbol, period="1y", interval="1d"):
    """
    Fetch historical stock data using yfinance.
    """
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return pd.DataFrame()

def main():
    print("=== STARTING STEP 2 DATA CRAWLER ===")
    
    # 1. Scrape community trending stocks
    trending = fetch_trending_stocks()
    print(f"\nScraped/Resolved {len(trending)} stocks:")
    for i, stock in enumerate(trending):
        print(f"[{i+1}] Code: {stock['code']} | Name: {stock['name']} | Symbol: {stock['symbol']}")
        
    # 2. Save the trending stock list to json file for the frontend
    output_dir = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(output_dir, "trending_stocks.json")
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(trending, f, ensure_ascii=False, indent=2)
    print(f"\nSaved stock list to {output_file}")
    
    # 3. Test yfinance on the top 3 stocks
    print("\n--- Verifying yfinance on top 3 stocks ---")
    for stock in trending[:3]:
        df_daily = fetch_stock_history(stock["symbol"], period="1mo", interval="1d")
        df_hourly = fetch_stock_history(stock["symbol"], period="1mo", interval="60m")
        print(f"Stock: {stock['name']} ({stock['symbol']})")
        print(f"  Daily rows: {len(df_daily)}")
        print(f"  Hourly rows: {len(df_hourly)}")
        if not df_daily.empty:
            print(f"  Latest Close: {df_daily['Close'].iloc[-1]:.2f}")
            
    print("\n=== DATA CRAWLER VERIFICATION COMPLETED ===")

if __name__ == "__main__":
    main()
