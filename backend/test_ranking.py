import requests
from bs4 import BeautifulSoup
import re

url = "https://tw.stock.yahoo.com/ranking"
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
        print("Found sub-links inside ranking page:")
        ranking_links = []
        for link in links:
            href = link['href']
            if '/ranking/' in href:
                ranking_links.append((href, link.text.strip()))
        for href, text in list(set(ranking_links)):
            print(f"Link: {href}, Text: {text}")
    else:
        print("Page load failed.")
except Exception as e:
    print(f"Error: {e}")
