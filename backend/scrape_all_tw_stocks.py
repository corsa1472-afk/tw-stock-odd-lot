import requests
from bs4 import BeautifulSoup
import re
import json
import os

def scrape_all_tw_stocks():
    stocks = {}
    
    # 1. TWSE (上市)
    try:
        r = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=2", timeout=15)
        r.encoding = 'big5'
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 0:
                text = tds[0].text.strip()
                # Match code like '2330  台積電'
                m = re.match(r'^([0-9]{4,6})\s+(.+)$', text)
                if m:
                    code = m.group(1)
                    name = m.group(2).strip()
                    # Only keep stocks (typically 4-digit code, not warrants or options which are 5 or 6 digits unless they are ETFs)
                    if len(code) == 4 or (len(code) == 5 and code.startswith('00')):
                        stocks[code] = {
                            "code": code,
                            "symbol": f"{code}.TW",
                            "name": name
                        }
    except Exception as e:
        print(f"Error scraping TWSE: {e}")

    # 2. TPEx (上櫃)
    try:
        r = requests.get("https://isin.twse.com.tw/isin/C_public.jsp?strMode=4", timeout=15)
        r.encoding = 'big5'
        soup = BeautifulSoup(r.text, 'html.parser')
        rows = soup.find_all('tr')
        for row in rows:
            tds = row.find_all('td')
            if len(tds) > 0:
                text = tds[0].text.strip()
                m = re.match(r'^([0-9]{4,6})\s+(.+)$', text)
                if m:
                    code = m.group(1)
                    name = m.group(2).strip()
                    if len(code) == 4 or (len(code) == 5 and code.startswith('00')):
                        stocks[code] = {
                            "code": code,
                            "symbol": f"{code}.TWO",
                            "name": name
                        }
    except Exception as e:
        print(f"Error scraping TPEx: {e}")

    return list(stocks.values())

def main():
    print("Scraping all Taiwan stock listings...")
    stocks = scrape_all_tw_stocks()
    print(f"Found {len(stocks)} stocks.")
    with open('backend/data/all_tw_stocks.json', 'w', encoding='utf-8') as f:
        json.dump(stocks, f, ensure_ascii=False, indent=2)
    print("Saved to backend/data/all_tw_stocks.json")

if __name__ == '__main__':
    main()
