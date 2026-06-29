html_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.html"

with open(html_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace scanner-section animation class
if '<section class="panel-card glass-panel" id="scanner-section">' in content:
    content = content.replace(
        '<section class="panel-card glass-panel" id="scanner-section">',
        '<section class="panel-card glass-panel animate-fade-in" id="scanner-section">'
    )
    print("Fixed scanner-section animation.")
else:
    # Try with LF
    lf_old = '<section class="panel-card glass-panel" id="scanner-section">'
    lf_new = '<section class="panel-card glass-panel animate-fade-in" id="scanner-section">'
    if lf_old in content:
        content = content.replace(lf_old, lf_new)
        print("Fixed scanner-section animation (LF).")
    else:
        print("Warning: Could not find scanner-section in HTML!")

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("HTML cleanup complete.")
