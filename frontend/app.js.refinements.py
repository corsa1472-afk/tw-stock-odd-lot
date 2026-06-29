import os

main_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\backend\main.py"
js_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\app.js"
css_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.css"

# 1. Update TW process_scanned_stock_data in backend/main.py to calculate and return change/percent
with open(main_path, "r", encoding="utf-8") as f:
    main_content = f.read()

# Locate process_scanned_stock_data return statement block and insert change calculations
target_marker = "signals = calculate_strategy_signals(df_daily)"
marker_idx = main_content.find(target_marker)
if marker_idx != -1:
    # Find next disposition_info or group_info
    insert_pos = main_content.find("\n", marker_idx) + 1
    calculation_code = """        if is_intraday:
            reference_price = float(df_daily['Close'].iloc[-1])
        else:
            reference_price = float(df_daily['Close'].iloc[-2]) if len(df_daily) >= 2 else close_price
            
        reference_price = round(reference_price, 2) if reference_price is not None else close_price
        price_change = round(close_price - reference_price, 2)
        price_change_percent = round((price_change / reference_price) * 100, 2) if reference_price else 0.0
        
"""
    main_content = main_content[:insert_pos] + calculation_code + main_content[insert_pos:]
    print("Added change calculations to process_scanned_stock_data.")

# Now add these fields to the return dictionary of process_scanned_stock_data
old_dict_return = """"current_price": round(close_price, 2),
            "daily_ma20": round(ma20, 2),"""

new_dict_return = """"current_price": round(close_price, 2),
            "reference_price": reference_price,
            "price_change": price_change,
            "price_change_percent": price_change_percent,
            "daily_ma20": round(ma20, 2),"""

if old_dict_return in main_content:
    main_content = main_content.replace(old_dict_return, new_dict_return)
    print("Added change fields to process_scanned_stock_data return dictionary.")
else:
    old_dict_return_lf = old_dict_return.replace("\r\n", "\n")
    new_dict_return_lf = new_dict_return.replace("\r\n", "\n")
    if old_dict_return_lf in main_content:
        main_content = main_content.replace(old_dict_return_lf, new_dict_return_lf)
        print("Added change fields to process_scanned_stock_data return dictionary (LF).")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(main_content)

# 2. Delete old cache files to force regeneration
cache_dir = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\backend\data"
tw_cache = os.path.join(cache_dir, "tw_analysis_cache.json")
us_cache = os.path.join(cache_dir, "us_analysis_cache.json")

for cache_file in [tw_cache, us_cache]:
    if os.path.exists(cache_file):
        try:
            os.remove(cache_file)
            print(f"Deleted old cache file: {os.path.basename(cache_file)} to force regeneration.")
        except Exception as e:
            print(f"Error deleting {os.path.basename(cache_file)}: {e}")

# 3. Update formatChangeCell in frontend/app.js to force 2 lines
with open(js_path, "r", encoding="utf-8") as f:
    js_content = f.read()

old_format_fn = """function formatChangeCell(change, percent) {
    if (change === undefined || change === null || percent === undefined || percent === null) {
        return `<td><span class="stock-code flat-gray">-</span></td>`;
    }
    const valChange = parseFloat(change);
    const valPercent = parseFloat(percent);
    if (valChange > 0) {
        return `<td class="up-red" style="font-weight: 700; font-family: var(--font-outfit);">+${valChange.toFixed(2)} (+${valPercent.toFixed(2)}%)</td>`;
    } else if (valChange < 0) {
        return `<td class="down-green" style="font-weight: 700; font-family: var(--font-outfit);">${valChange.toFixed(2)} (${valPercent.toFixed(2)}%)</td>`;
    } else {
        return `<td class="flat-gray" style="font-family: var(--font-outfit);">0.00 (0.00%)</td>`;
    }
}"""

new_format_fn = """function formatChangeCell(change, percent) {
    if (change === undefined || change === null || percent === undefined || percent === null) {
        return `<td><span class="stock-code flat-gray">-</span></td>`;
    }
    const valChange = parseFloat(change);
    const valPercent = parseFloat(percent);
    if (valChange > 0) {
        return `<td class="up-red">+${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; opacity: 0.85; display: inline-block; margin-top: 2px;">(+${valPercent.toFixed(2)}%)</span></td>`;
    } else if (valChange < 0) {
        return `<td class="down-green">${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; opacity: 0.85; display: inline-block; margin-top: 2px;">(${valPercent.toFixed(2)}%)</span></td>`;
    } else {
        return `<td class="flat-gray">0.00<br><span style="font-size: 0.68rem; opacity: 0.85; display: inline-block; margin-top: 2px;">(0.00%)</span></td>`;
    }
}"""

if old_format_fn in js_content:
    js_content = js_content.replace(old_format_fn, new_format_fn)
    print("Updated formatChangeCell in app.js.")
else:
    old_format_fn_lf = old_format_fn.replace("\r\n", "\n")
    new_format_fn_lf = new_format_fn.replace("\r\n", "\n")
    if old_format_fn_lf in js_content:
        js_content = js_content.replace(old_format_fn_lf, new_format_fn_lf)
        print("Updated formatChangeCell in app.js (LF).")

with open(js_path, "w", encoding="utf-8") as f:
    f.write(js_content)

# 4. Refine index.css to force thin font, smaller size, and centered alignments for change cells
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

old_css_styling = """/* Price change / change percent styled classes */
td.up-red {
    color: var(--color-danger) !important;
}
td.down-green {
    color: var(--color-success) !important;
}
td.flat-gray {
    color: var(--text-muted) !important;
}"""

new_css_styling = """/* Price change / change percent styled classes */
td.up-red, td.down-green, td.flat-gray {
    font-size: 0.75rem !important;
    font-weight: 300 !important; /* Force light font weight */
    line-height: 1.25 !important;
    text-align: center !important;
    white-space: nowrap !important;
}
td.up-red {
    color: var(--color-danger) !important;
}
td.down-green {
    color: var(--color-success) !important;
}
td.flat-gray {
    color: var(--text-muted) !important;
}"""

if old_css_styling in css_content:
    css_content = css_content.replace(old_css_styling, new_css_styling)
    print("Updated CSS styling classes in index.css.")
else:
    old_css_styling_lf = old_css_styling.replace("\r\n", "\n")
    new_css_styling_lf = new_css_styling.replace("\r\n", "\n")
    if old_css_styling_lf in css_content:
        css_content = css_content.replace(old_css_styling_lf, new_css_styling_lf)
        print("Updated CSS styling classes in index.css (LF).")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css_content)

print("Refinements applied successfully!")
