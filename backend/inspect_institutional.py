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
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "lxml")
        
        # Find all tables
        tables = soup.find_all("table")
        print(f"Found {len(tables)} tables.")
        
        # Let's inspect the tables
        for idx, table in enumerate(tables):
            print(f"\n--- Table {idx+1} ---")
            rows = table.find_all("tr")
            print(f"Total rows: {len(rows)}")
            for r_idx, r in enumerate(rows[:15]):
                # print first 15 rows
                cells = [c.text.strip() for c in r.find_all(["td", "th"])]
                print(f"Row {r_idx}: {cells}")
                
    else:
        print("Failed to load page.")
except Exception as e:
    print(f"Error: {e}")
