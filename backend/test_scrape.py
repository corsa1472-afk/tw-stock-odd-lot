import requests
import re
from bs4 import BeautifulSoup

url = "https://tw.stock.yahoo.com/ranking/trending"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Response status code: {response.status_code}")
    html = response.text
    print(f"HTML Length: {len(html)}")
    
    # Let's find links containing /quote/
    soup = BeautifulSoup(html, "lxml")
    links = soup.find_all("a", href=True)
    
    symbols = []
    # Match pattern like /quote/2330.TW or /quote/2330
    for link in links:
        href = link['href']
        match = re.search(r'/quote/([0-9]{4,6}(?:\.[TToO]+)?)', href)
        if match:
            symbol = match.group(1)
            symbols.append((symbol, link.text.strip()))
            
    # Also find regular pattern of Taiwan stock code in text
    # e.g., "2330 台積電" or similar
    print("Found links with stock codes:")
    unique_symbols = {}
    for sym, text in symbols:
        if sym not in unique_symbols:
            unique_symbols[sym] = text
            
    for k, v in list(unique_symbols.items())[:20]:
        print(f"Symbol: {k}, Text: {v}")
        
except Exception as e:
    print(f"Error occurred: {e}")
