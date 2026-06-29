import requests
import json

base_url = "http://127.0.0.1:8000"

try:
    print("1. Querying /api/stocks ...")
    r = requests.get(f"{base_url}/api/stocks", timeout=5)
    print(f"Status: {r.status_code}")
    print(json.dumps(r.json()[:3], ensure_ascii=False, indent=2))
    
    print("\n2. Querying /api/stocks/analyze (takes a few seconds) ...")
    r_analyze = requests.get(f"{base_url}/api/stocks/analyze", timeout=30)
    print(f"Status: {r_analyze.status_code}")
    data = r_analyze.json()
    print(f"Analyzed {len(data)} stocks.")
    # Show the first analysis result
    if data:
        print("First analysis result:")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))
        
except Exception as e:
    print(f"API Request failed: {e}")
