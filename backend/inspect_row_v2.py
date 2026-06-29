import requests
from bs4 import BeautifulSoup

url = "https://tw.stock.yahoo.com/community/rank/active"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        
        # Find the specific link to 2330.TW
        # Note: Yahoo links can be relative like /quote/2330.TW or absolute
        links = soup.find_all("a", href=True)
        for link in links:
            href = link['href']
            if href.endswith('/quote/2330.TW') or href.endswith('2330.TW'):
                print("--- LINK FOUND ---")
                print(str(link))
                print("--- PARENT ---")
                parent = link.parent
                print(str(parent)[:2000])
                print("--- GRANDPARENT ---")
                grandparent = parent.parent
                print(str(grandparent)[:2000])
                print("--- GRANDPARENT TEXT ---")
                print(grandparent.get_text(separator=" | ", strip=True))
                break
except Exception as e:
    print(f"Error: {e}")
