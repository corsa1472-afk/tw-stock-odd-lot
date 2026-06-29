import requests

subpaths = [
    "institutional-trading",
    "institutional",
    "chip",
    "major-investors",
    "insiders",
    "profile",
    "financials",
    "holders",
    "options"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

for sub in subpaths:
    url = f"https://tw.stock.yahoo.com/quote/2330.TW/{sub}"
    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"Subpath: {sub} -> GET Status: {response.status_code}")
    except Exception as e:
        print(f"Subpath: {sub} -> Error: {e}")
