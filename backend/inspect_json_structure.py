import requests
from bs4 import BeautifulSoup
import re
import json

url = "https://tw.stock.yahoo.com/quote/2330.TW/institutional-trading"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        html = response.text
        # Find root.App.main = ...
        match = re.search(r'root\.App\.main\s*=\s*(.*?);\s*\(function', html, re.DOTALL)
        if not match:
            # Try another pattern
            match = re.search(r'root\.App\.main\s*=\s*(.*?);\n', html, re.DOTALL)
            
        if match:
            json_str = match.group(1)
            print("Extracted JSON string length:", len(json_str))
            
            # Load into dict
            data = json.loads(json_str)
            print("Successfully loaded JSON.")
            
            # Let's search inside the dictionary for anything related to institutional trading.
            # We can write a recursive finder.
            results = []
            
            def find_key(obj, path=""):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        new_path = f"{path}.{k}" if path else k
                        if "institutional" in k.lower() or "major" in k.lower() or "chip" in k.lower():
                            results.append((new_path, type(v)))
                        find_key(v, new_path)
                elif isinstance(obj, list):
                    for idx, item in enumerate(obj[:2]): # only check first few
                        find_key(item, f"{path}[{idx}]")
                        
            find_key(data)
            print("\nFound keys related to institutional/major/chip:")
            for path, t in results[:20]:
                print(f"Path: {path} | Type: {t}")
                
            # Let's search specifically for the institutional trading data block.
            # Let's search for keys inside dispatcher -> stores
            stores = data.get("context", {}).get("dispatcher", {}).get("stores", {})
            print("\nAvailable stores in dispatcher:")
            for store_name in stores.keys():
                if "chip" in store_name.lower() or "inst" in store_name.lower() or "trade" in store_name.lower():
                    print(f"  * {store_name}")
                    
        else:
            print("Could not find root.App.main in HTML.")
    else:
        print(f"Status: {response.status_code}")
except Exception as e:
    print(f"Error: {e}")
