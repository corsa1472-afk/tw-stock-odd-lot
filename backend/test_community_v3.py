import requests
from bs4 import BeautifulSoup
import re
import json
import sys

# Try to set stdout to UTF-8 in case the terminal supports it
try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

url = "https://tw.stock.yahoo.com/community/rank/active"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        # Use response.content so BeautifulSoup handles encoding automatically
        soup = BeautifulSoup(response.content, "lxml")
        
        links = soup.find_all("a", href=True)
        trending_list = []
        seen = set()
        
        for link in links:
            href = link['href']
            # Match quote/XXXX.TW or quote/XXXX.TWO
            match = re.search(r'/quote/([0-9]{4,6})\.(TW|TWO)', href)
            if match:
                symbol = match.group(0).split('/')[-1] # e.g. 2330.TW
                code = match.group(1)
                
                # Let's inspect the parent container to get the stock name
                parent = link.parent
                strings = list(parent.stripped_strings)
                
                name = "未知股名"
                if strings:
                    # Filter out strings that are just symbol or code
                    clean_strings = [s for s in strings if s != symbol and s != code and not s.startswith('/')]
                    if clean_strings:
                        name = clean_strings[0]
                
                if symbol not in seen:
                    seen.add(symbol)
                    trending_list.append({
                        "symbol": symbol,
                        "code": code,
                        "name": name
                    })
                    
        # Write results to a JSON file with UTF-8 encoding
        out_file = "C:/Users/hopes/.gemini/antigravity/scratch/tw_stock_odd_lot/backend/test_result.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(trending_list, f, ensure_ascii=False, indent=2)
        print(f"Successfully wrote {len(trending_list)} stocks to {out_file}")
            
    else:
        print("Page load failed.")
except Exception as e:
    print(f"Error: {e}")
