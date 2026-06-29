main_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\backend\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Fix the function definition header for run_all_market_scan
bad_def = """def run_all_market_scan()
    threading.Thread(target=load_all_us_stocks_cache, daemon=True).start():"""

good_def = """def run_all_market_scan():"""

if bad_def in content:
    content = content.replace(bad_def, good_def)
    print("Restored def run_all_market_scan():")
else:
    bad_def_lf = bad_def.replace("\r\n", "\n")
    good_def_lf = good_def.replace("\r\n", "\n")
    if bad_def_lf in content:
        content = content.replace(bad_def_lf, good_def_lf)
        print("Restored def run_all_market_scan(): (LF)")
    else:
        print("Warning: Could not find the bad run_all_market_scan function header!")

# 2. Correctly update the startup_event at the end of the file
bad_startup = """@app.on_event("startup")
def startup_event():
    load_potential_stocks()
    sync_connector_lists()
    run_all_market_scan()"""

good_startup = """@app.on_event("startup")
def startup_event():
    load_potential_stocks()
    sync_connector_lists()
    run_all_market_scan()
    import threading
    threading.Thread(target=load_all_us_stocks_cache, daemon=True).start()"""

if bad_startup in content:
    content = content.replace(bad_startup, good_startup)
    print("Updated startup_event with background US cache loader.")
else:
    bad_startup_lf = bad_startup.replace("\r\n", "\n")
    good_startup_lf = good_startup.replace("\r\n", "\n")
    if bad_startup_lf in content:
        content = content.replace(bad_startup_lf, good_startup_lf)
        print("Updated startup_event with background US cache loader (LF)")
    else:
        print("Warning: Could not find bad startup_event!")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Startup and function definition fix complete!")
