import requests
from bs4 import BeautifulSoup

url = "https://tw.stock.yahoo.com/rank"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", href=True)
        print(f"Found {len(links)} links in total.")
        
        # Let's look for any link containing /rank or /ranking or similar
        ranking_links = []
        for link in links:
            href = link['href']
            text = link.text.strip()
            # If the href contains '/rank' (like /rank/volume or /class/ or similar)
            if '/rank' in href or 'volume' in href or 'trending' in href:
                ranking_links.append((href, text))
                
        print("\nFiltered ranking-related links:")
        for href, text in sorted(list(set(ranking_links))):
            print(f"Href: {href} | Text: {text}")
            
    else:
        print("Failed to get 200 status.")
except Exception as e:
    print(f"Error: {e}")
