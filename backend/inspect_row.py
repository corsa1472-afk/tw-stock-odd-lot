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
        
        # Let's find all divs containing the quote links
        links = soup.find_all("a", href=True)
        for link in links:
            href = link['href']
            if 'quote/2330.TW' in href:
                # Print parent container and its text
                parent = link.parent
                print("--- PARENT ---")
                print(str(parent)[:1000])
                print("--- PARENT TEXT ---")
                print(parent.get_text(strip=True))
                
                # Print grandparent container
                grandparent = parent.parent
                print("--- GRANDPARENT ---")
                print(str(grandparent)[:2000])
                print("--- GRANDPARENT TEXT ---")
                print(grandparent.get_text(separator=" | ", strip=True))
                break
except Exception as e:
    print(f"Error: {e}")
