import requests
from bs4 import BeautifulSoup
import re

url = "https://tw.stock.yahoo.com/community/rank/active"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        
        # Print Title
        print(f"Title: {soup.title.text if soup.title else 'No Title'}")
        
        # Let's find links containing stock symbols
        links = soup.find_all("a", href=True)
        symbols = []
        seen = set()
        
        for link in links:
            href = link['href']
            # Match quote/XXXX.TW or quote/XXXX.TWO
            match = re.search(r'/quote/([0-9a-zA-Z]{4,6})(?:\.([TToO]+))?', href)
            if match:
                symbol_code = match.group(1)
                suffix = match.group(2)
                if symbol_code.isdigit():
                    full_symbol = symbol_code + ("." + suffix.upper() if suffix else ".TW")
                    
                    # Try to extract the stock name
                    name = link.text.strip()
                    # Clean up the name if it contains code or is just numbers
                    name = re.sub(r'^[0-9]{4,6}\s*', '', name)
                    
                    if full_symbol not in seen:
                        seen.add(full_symbol)
                        symbols.append((full_symbol, name))
                        
        print(f"\nFound {len(symbols)} unique stock symbols in community rank:")
        for sym, name in symbols[:20]:
            print(f"Symbol: {sym} | Name: {name}")
            
    else:
        print("Page load failed.")
except Exception as e:
    print(f"Error: {e}")
