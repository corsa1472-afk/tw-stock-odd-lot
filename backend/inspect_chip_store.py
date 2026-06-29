import requests
import re
import json

url = "https://tw.stock.yahoo.com/quote/2330.TW/institutional-trading"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    response = requests.get(url, headers=headers, timeout=10)
    html = response.text
    match = re.search(r'root\.App\.main\s*=\s*(.*?);\s*\(function', html, re.DOTALL)
    if not match:
        match = re.search(r'root\.App\.main\s*=\s*(.*?);\n', html, re.DOTALL)
        
    if match:
        json_str = match.group(1)
        json_str = re.sub(r':\s*undefined', ': null', json_str)
        json_str = re.sub(r':\s*NaN', ': null', json_str)
        
        data = json.loads(json_str)
        chip_store = data.get("context", {}).get("dispatcher", {}).get("stores", {}).get("QuoteChipStore", {})
        
        print("QuoteChipStore type:", type(chip_store))
        # Write to a JSON file to inspect
        out_file = "C:/Users/hopes/.gemini/antigravity/scratch/tw_stock_odd_lot/backend/chip_store.json"
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(chip_store, f, ensure_ascii=False, indent=2)
        print(f"Wrote QuoteChipStore to {out_file}")
        
except Exception as e:
    print(f"Error: {e}")
