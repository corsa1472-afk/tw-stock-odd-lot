import os
import re
import datetime

# Use relative paths so the script works anywhere within the project structure
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
html_path = os.path.join(SCRIPT_DIR, "index.html")
js_path = os.path.join(SCRIPT_DIR, "app.js")

print(f"Target HTML: {html_path}")
print(f"Target JS: {js_path}")

# 1. Update index.html
if not os.path.exists(html_path):
    print(f"Error: {html_path} not found.")
    exit(1)

with open(html_path, "r", encoding="utf-8") as f:
    html = f.read()

# Match pattern: 版次：v1.6.12 (260624|161000)
html_pattern = r"版次：(v\d+\.\d+\.(\d+))\s*\((\d{6})\|(\d{6})\)"
match = re.search(html_pattern, html)
if not match:
    print("Error: Could not find version pattern in index.html")
    exit(1)

full_version = match.group(1)
patch_version = int(match.group(2))
old_date = match.group(3)
old_time = match.group(4)

# Increment version
new_patch = patch_version + 1
version_parts = full_version.split('.')
version_parts[-1] = str(new_patch)
new_version = ".".join(version_parts)

# Get current local time
now = datetime.datetime.now()
new_date = now.strftime("%y%m%d")
new_time = now.strftime("%H%M%S")

old_html_ver = f"版次：{full_version} ({old_date}|{old_time})"
new_html_ver = f"版次：{new_version} ({new_date}|{new_time})"

html = html.replace(old_html_ver, new_html_ver)

# Match and update css / js query parameters to prevent browser caching
html = re.sub(r'href="index\.css\?v=[^"]+"', f'href="index.css?v={new_version}"', html)
html = re.sub(r'src="app\.js\?v=[^"]+"', f'src="app.js?v={new_version}"', html)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Successfully updated index.html: {old_html_ver} -> {new_html_ver}")

# 2. Update app.js
if not os.path.exists(js_path):
    print(f"Error: {js_path} not found.")
    exit(1)

with open(js_path, "r", encoding="utf-8") as f:
    js = f.read()

# Regex patterns to find variable declarations in JS
js_version_pattern = r'const APP_VERSION = "[^"]+";'
js_date_pattern = r'const APP_REVISION_DATE = "\d{6}";'
js_time_pattern = r'const APP_REVISION_TIME = "\d{6}";'

if not re.search(js_version_pattern, js):
    print("Warning: const APP_VERSION not found in app.js")
if not re.search(js_date_pattern, js):
    print("Warning: const APP_REVISION_DATE not found in app.js")
if not re.search(js_time_pattern, js):
    print("Warning: const APP_REVISION_TIME not found in app.js")

js = re.sub(js_version_pattern, f'const APP_VERSION = "{new_version}";', js)
js = re.sub(js_date_pattern, f'const APP_REVISION_DATE = "{new_date}";', js)
js = re.sub(js_time_pattern, f'const APP_REVISION_TIME = "{new_time}";', js)

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js)
print(f"Successfully updated app.js to version {new_version} ({new_date}|{new_time})")

print("Version bump completed successfully!")
