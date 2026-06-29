import requests
from bs4 import BeautifulSoup
import re

url = "https://tw.stock.yahoo.com/quote/2330.TW/institutional-trading"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "lxml")
        scripts = soup.find_all("script")
        print(f"Found {len(scripts)} script tags.")
        
        for idx, script in enumerate(scripts):
            text = script.string
            if not text:
                continue
            
            # Let's search for keywords
            keywords = ["App.main", "context", "preloadedState", "state", "institutionalTrading", "buy", "sell"]
            found = [k for k in keywords if k in text]
            if found:
                print(f"\n--- Script {idx+1} (Length: {len(text)}) | Matches: {found} ---")
                # print first 500 chars
                print(text[:1000])
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
