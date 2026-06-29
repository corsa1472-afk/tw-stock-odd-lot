main_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\backend\main.py"

with open(main_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Remove the duplicate MA20/MA60 and stray }) block
bad_ma_block = """        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()
        df_daily['MA60'] = df_daily['Close'].rolling(window=60).mean()
        
            })
            
        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()"""

good_ma_block = """        df_daily['MA20'] = df_daily['Close'].rolling(window=20).mean()"""

if bad_ma_block in content:
    content = content.replace(bad_ma_block, good_ma_block)
    print("Fixed bad MA block and stray })")
else:
    # Try with different line endings
    bad_ma_block_lf = bad_ma_block.replace("\r\n", "\n")
    good_ma_block_lf = good_ma_block.replace("\r\n", "\n")
    if bad_ma_block_lf in content:
        content = content.replace(bad_ma_block_lf, good_ma_block_lf)
        print("Fixed bad MA block and stray }) (LF)")
    else:
        print("Warning: Could not find bad MA block!")

# 2. Remove the duplicated end of analyze_single_stock function
# The end of the function is followed by:
# # Read/Write helpers
#             "system_a_signal": system_a_signal,
# ...
#         })

duplicate_end_start = """# Read/Write helpers
            "system_a_signal": system_a_signal,"""

# Let's find this and replace everything from that point until the next "def " or read/write helper function starts,
# or simply replace the exact duplicate block.
# Let's see the exact duplicate block:
duplicate_block = """# Read/Write helpers
            "system_a_signal": system_a_signal,
            "prev_high": round(prev_high, 2),
            "stop_loss_price": stop_loss_price,
            "r_value": r_value,
            "signals": signals,
            "disposition": disposition_info,
            "is_intraday": is_intraday,
            "error": None
        })
    except Exception as e:
        return clean_nan({
            "code": code,
            "symbol": symbol,
            "name": name,
            "market": "US" if is_us else "TW",
            "category": stock.get("category", ""),
            "is_intraday": is_intraday,
            "error": f"???航炊: {str(e)}",
            "system_a_signal": False
        })"""

if duplicate_block in content:
    content = content.replace(duplicate_block, "# Read/Write helpers")
    print("Removed duplicate analyze_single_stock block")
else:
    duplicate_block_lf = duplicate_block.replace("\r\n", "\n")
    if duplicate_block_lf in content:
        content = content.replace(duplicate_block_lf, "# Read/Write helpers")
        print("Removed duplicate analyze_single_stock block (LF)")
    else:
        print("Warning: Could not find duplicate analyze_single_stock block!")

with open(main_path, "w", encoding="utf-8") as f:
    f.write(content)

print("Indentation and duplicate fix complete!")
