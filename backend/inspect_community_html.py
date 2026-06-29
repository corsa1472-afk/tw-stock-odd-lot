import requests
from bs4 import BeautifulSoup
import re

url = "https://tw.stock.yahoo.com/community/rank/active"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "lxml")
        links = soup.find_all("a", href=True)
        count = 0
        for link in links:
            href = link['href']
            if '/quote/' in href:
                print(f"Href: {href} | Text: {link.text.strip()} | HTML: {str(link)}")
                count += 1
                if count >= 15:
                    break
except Exception as e:
    print(f"Error: {e}")
