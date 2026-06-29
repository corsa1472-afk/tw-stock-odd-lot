import requests

url = "https://tw.stock.yahoo.com/rank/volume-rank"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://tw.stock.yahoo.com/"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Redirect History: {response.history}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response Body (first 500 chars):")
    print(response.text[:500])
except Exception as e:
    print(f"Error: {e}")
