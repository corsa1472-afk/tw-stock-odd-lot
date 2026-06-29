import requests

urls = [
    "https://tw.stock.yahoo.com/rank/volume-rank",
    "https://tw.stock.yahoo.com/rank/browsing-rank",
    "https://tw.stock.yahoo.com/rank/trending-rank",
    "https://tw.stock.yahoo.com/rank/popular-rank",
    "https://tw.stock.yahoo.com/rank/hot-rank",
    "https://tw.stock.yahoo.com/rank/value-rank",
    "https://tw.stock.yahoo.com/rank/price-gain-rank",
    "https://tw.stock.yahoo.com/rank"
]

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

for url in urls:
    try:
        response = requests.head(url, headers=headers, timeout=5)
        print(f"URL: {url} -> Status: {response.status_code}")
        # If it returned 405 (Method Not Allowed for HEAD), try GET
        if response.status_code == 405 or response.status_code == 404:
            response = requests.get(url, headers=headers, timeout=5)
            print(f"URL: {url} -> GET Status: {response.status_code}")
    except Exception as e:
        print(f"URL: {url} -> Error: {e}")
