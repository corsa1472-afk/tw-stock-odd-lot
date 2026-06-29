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
        
        # Sanitize loop
        for attempt in range(10):
            # Replace undefined with null
            json_str = re.sub(r':\s*undefined', ': null', json_str)
            json_str = re.sub(r':\s*NaN', ': null', json_str)
            
            try:
                data = json.loads(json_str)
                print(f"SUCCESS! Parsed JSON on attempt {attempt+1}")
                # Print key stores
                stores = data.get("context", {}).get("dispatcher", {}).get("stores", {})
                print("Stores:", list(stores.keys()))
                break
            except json.JSONDecodeError as err:
                pos = err.pos
                print(f"Attempt {attempt+1} failed at pos {pos}: {err.msg}")
                start = max(0, pos - 100)
                end = min(len(json_str), pos + 100)
                print(f"Snippet: {json_str[start:end]}")
                # To prevent infinite loop if we can't solve it
                # We can replace the problematic token. Let's see what it is
                # If it's a word like undefined, we handled it, but let's check
                if json_str[pos:pos+9] == 'undefined':
                    json_str = json_str[:pos] + 'null' + json_str[pos+9:]
                elif json_str[pos:pos+3] == 'NaN':
                    json_str = json_str[:pos] + 'null' + json_str[pos+3:]
                else:
                    break
except Exception as e:
    print(f"Error: {e}")
