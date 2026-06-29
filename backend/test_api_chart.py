import requests
import json

url = "http://127.0.0.1:8000/api/stocks/2330/chart-data"
try:
    print(f"Requesting {url}...")
    r = requests.get(url, timeout=30)
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print("Success!")
        print("Keys returned:", list(data.keys()))
        print(f"Intraday records: {len(data['intraday'])}")
        print(f"K-line records: {len(data['kline'])}")
        print(f"KD records: {len(data['kd'])}")
        print(f"Institutional records: {len(data['institutional'])}")
    else:
        print("Failed to get 200:", r.text)
except Exception as e:
    print(f"Error: {e}")
