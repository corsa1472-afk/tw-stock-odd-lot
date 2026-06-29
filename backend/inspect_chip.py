import requests
from bs4 import BeautifulSoup
import re

url = "https://tw.stock.yahoo.com/quote/2330.TW/chip"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "lxml")
        print("Title:", soup.title.text if soup.title else "No Title")
        
        # Let's see if there are tables
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables.")
        for idx, table in enumerate(tables):
            print(f"\n--- Table {idx+1} ---")
            # Print first 3 rows text
            rows = table.find_all("tr")
            for r_idx, r in enumerate(rows[:5]):
                print(f"Row {r_idx}: {r.get_text(separator=' | ', strip=True)}")
                
        # Also print all text containing "外資"
        print("\nSearching for '外資' in text...")
        elements = soup.find_all(text=re.compile("外資"))
        print(f"Found {len(elements)} instances of '外資'.")
        for el in elements[:10]:
            parent = el.parent
            print(f"Parent tag: {parent.name} | Text: {parent.get_text(strip=True)}")
            
    else:
        print("Failed to get 200 status.")
except Exception as e:
    print(f"Error: {e}")
