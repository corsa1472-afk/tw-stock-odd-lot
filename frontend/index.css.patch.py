css_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.css"

with open(css_path, "r", encoding="utf-8") as f:
    content = f.read()

# Helper function to replace content robustly (both CRLF and LF)
def robust_replace(text, target, replacement):
    if target in text:
        text = text.replace(target, replacement)
        return text, True
    target_lf = target.replace("\r\n", "\n")
    replacement_lf = replacement.replace("\r\n", "\n")
    if target_lf in text:
        text = text.replace(target_lf, replacement_lf)
        return text, True
    return text, False

# 1. Replace TW Stock Tracker and Scanner column widths (lines 1664 to 1685)
tw_cols_old = """#stock-table th:nth-child(1), #stock-table td:nth-child(1),
#potential-table th:nth-child(1), #potential-table td:nth-child(1) { width: 7.5%; min-width: 60px; white-space: nowrap !important; }   /* 代號 */
#stock-table th:nth-child(2), #stock-table td:nth-child(2),
#potential-table th:nth-child(2), #potential-table td:nth-child(2) { width: 16.5%; min-width: 95px; white-space: nowrap !important; }  /* 股名 */
#stock-table th:nth-child(3), #stock-table td:nth-child(3),
#potential-table th:nth-child(3), #potential-table td:nth-child(3) { width: 8.0%; min-width: 65px; white-space: nowrap !important; }   /* 股價 */
#stock-table th:nth-child(4), #stock-table td:nth-child(4),
#potential-table th:nth-child(4), #potential-table td:nth-child(4) { width: 9.5%; min-width: 70px; white-space: nowrap !important; }   /* 成交量 */
#stock-table th:nth-child(5), #stock-table td:nth-child(5),
#potential-table th:nth-child(5), #potential-table td:nth-child(5) { width: 7.5%; min-width: 50px; }   /* 日線趨勢 */
#stock-table th:nth-child(6), #stock-table td:nth-child(6),
#potential-table th:nth-child(6), #potential-table td:nth-child(6) { width: 7.5%; min-width: 50px; }  /* 60分K打底 */
#stock-table th:nth-child(7), #stock-table td:nth-child(7),
#potential-table th:nth-child(7), #potential-table td:nth-child(7) { width: 7.5%; min-width: 50px; }   /* 進場訊號 */
#stock-table th:nth-child(8), #stock-table td:nth-child(8),
#potential-table th:nth-child(8), #potential-table td:nth-child(8) { width: 7.5%; min-width: 50px; }   /* 底底高 */
#stock-table th:nth-child(9), #stock-table td:nth-child(9),
#potential-table th:nth-child(9), #potential-table td:nth-child(9) { width: 13%; min-width: 50px; }  /* 策略燈號 */
#stock-table th:nth-child(10), #stock-table td:nth-child(10),
#potential-table th:nth-child(10), #potential-table td:nth-child(10) { width: 10%; min-width: 48px; white-space: nowrap !important; } /* 預期R値 */
#stock-table th:nth-child(11), #stock-table td:nth-child(11),
#potential-table th:nth-child(11), #potential-table td:nth-child(11) { width: 5.5%; min-width: 35px; } /* 操作 */"""

tw_cols_new = """#stock-table th:nth-child(1), #stock-table td:nth-child(1),
#potential-table th:nth-child(1), #potential-table td:nth-child(1) { width: 7.0%; min-width: 60px; white-space: nowrap !important; }   /* 代號 */
#stock-table th:nth-child(2), #stock-table td:nth-child(2),
#potential-table th:nth-child(2), #potential-table td:nth-child(2) { width: 13.0%; min-width: 95px; white-space: nowrap !important; }  /* 股名 */
#stock-table th:nth-child(3), #stock-table td:nth-child(3),
#potential-table th:nth-child(3), #potential-table td:nth-child(3) { width: 7.0%; min-width: 65px; white-space: nowrap !important; }   /* 股價 */
#stock-table th:nth-child(4), #stock-table td:nth-child(4),
#potential-table th:nth-child(4), #potential-table td:nth-child(4) { width: 9.0%; min-width: 75px; white-space: nowrap !important; }   /* 漲跌 / 漲幅 */
#stock-table th:nth-child(5), #stock-table td:nth-child(5),
#potential-table th:nth-child(5), #potential-table td:nth-child(5) { width: 7.5%; min-width: 70px; white-space: nowrap !important; }   /* 成交量 */
#stock-table th:nth-child(6), #stock-table td:nth-child(6),
#potential-table th:nth-child(6), #potential-table td:nth-child(6) { width: 7.0%; min-width: 50px; }   /* 日線趨勢 */
#stock-table th:nth-child(7), #stock-table td:nth-child(7),
#potential-table th:nth-child(7), #potential-table td:nth-child(7) { width: 7.0%; min-width: 50px; }  /* 60分K打底 */
#stock-table th:nth-child(8), #stock-table td:nth-child(8),
#potential-table th:nth-child(8), #potential-table td:nth-child(8) { width: 7.0%; min-width: 50px; }   /* 進場訊號 */
#stock-table th:nth-child(9), #stock-table td:nth-child(9),
#potential-table th:nth-child(9), #potential-table td:nth-child(9) { width: 7.0%; min-width: 50px; }   /* 底底高 */
#stock-table th:nth-child(10), #stock-table td:nth-child(10),
#potential-table th:nth-child(10), #potential-table td:nth-child(10) { width: 11.0%; min-width: 50px; }  /* 策略燈號 */
#stock-table th:nth-child(11), #stock-table td:nth-child(11),
#potential-table th:nth-child(11), #potential-table td:nth-child(11) { width: 8.5%; min-width: 48px; white-space: nowrap !important; } /* 預期R値 */
#stock-table th:nth-child(12), #stock-table td:nth-child(12),
#potential-table th:nth-child(12), #potential-table td:nth-child(12) { width: 5.0%; min-width: 35px; } /* 操作 */"""

content, ok = robust_replace(content, tw_cols_old, tw_cols_new)
print("1. TW columns updated:", ok)

# 2. Replace US Stock Tracker column widths (lines 1770 to 1780)
us_cols_old = """#us-stock-table th:nth-child(1), #us-stock-table td:nth-child(1) { width: 9%; }
#us-stock-table th:nth-child(2), #us-stock-table td:nth-child(2) { width: 18%; }
#us-stock-table th:nth-child(3), #us-stock-table td:nth-child(3) { width: 9%; }
#us-stock-table th:nth-child(4), #us-stock-table td:nth-child(4) { width: 10%; }
#us-stock-table th:nth-child(5), #us-stock-table td:nth-child(5) { width: 10%; }
#us-stock-table th:nth-child(6), #us-stock-table td:nth-child(6) { width: 10%; }
#us-stock-table th:nth-child(7), #us-stock-table td:nth-child(7) { width: 8%; }
#us-stock-table th:nth-child(8), #us-stock-table td:nth-child(8) { width: 8%; }
#us-stock-table th:nth-child(9), #us-stock-table td:nth-child(9) { width: 9%; }
#us-stock-table th:nth-child(10), #us-stock-table td:nth-child(10) { width: 6%; }
#us-stock-table th:nth-child(11), #us-stock-table td:nth-child(11) { width: 3%; }"""

us_cols_new = """#us-stock-table th:nth-child(1), #us-stock-table td:nth-child(1) { width: 8%; }
#us-stock-table th:nth-child(2), #us-stock-table td:nth-child(2) { width: 15%; }
#us-stock-table th:nth-child(3), #us-stock-table td:nth-child(3) { width: 8%; }
#us-stock-table th:nth-child(4), #us-stock-table td:nth-child(4) { width: 9%; } /* 漲跌 / 漲幅 */
#us-stock-table th:nth-child(5), #us-stock-table td:nth-child(5) { width: 8%; } /* 成交量 */
#us-stock-table th:nth-child(6), #us-stock-table td:nth-child(6) { width: 9%; } /* 日線趨勢 */
#us-stock-table th:nth-child(7), #us-stock-table td:nth-child(7) { width: 9%; } /* 60分K打底 */
#us-stock-table th:nth-child(8), #us-stock-table td:nth-child(8) { width: 7%; } /* 進場訊號 */
#us-stock-table th:nth-child(9), #us-stock-table td:nth-child(9) { width: 7%; } /* 底底高 */
#us-stock-table th:nth-child(10), #us-stock-table td:nth-child(10) { width: 8%; } /* 策略燈號 */
#us-stock-table th:nth-child(11), #us-stock-table td:nth-child(11) { width: 7%; } /* R-Value */
#us-stock-table th:nth-child(12), #us-stock-table td:nth-child(12) { width: 5%; } /* 操作 */"""

content, ok = robust_replace(content, us_cols_old, us_cols_new)
print("2. US columns updated:", ok)

# 3. Replace risk monitors column widths (lines 1687 to 1704)
mon_cols_old = """#monitors-table th:nth-child(1), #monitors-table td:nth-child(1),
#us-monitors-table th:nth-child(1), #us-monitors-table td:nth-child(1) { width: 15%; }
#monitors-table th:nth-child(2), #monitors-table td:nth-child(2),
#us-monitors-table th:nth-child(2), #us-monitors-table td:nth-child(2) { width: 15%; }
#monitors-table th:nth-child(3), #monitors-table td:nth-child(3),
#us-monitors-table th:nth-child(3), #us-monitors-table td:nth-child(3) { width: 12%; }
#monitors-table th:nth-child(4), #monitors-table td:nth-child(4),
#us-monitors-table th:nth-child(4), #us-monitors-table td:nth-child(4) { width: 9%; }
#monitors-table th:nth-child(5), #monitors-table td:nth-child(5),
#us-monitors-table th:nth-child(5), #us-monitors-table td:nth-child(5) { width: 11%; }
#monitors-table th:nth-child(6), #monitors-table td:nth-child(6),
#us-monitors-table th:nth-child(6), #us-monitors-table td:nth-child(6) { width: 10%; }
#monitors-table th:nth-child(7), #monitors-table td:nth-child(7),
#us-monitors-table th:nth-child(7), #us-monitors-table td:nth-child(7) { width: 11%; }
#monitors-table th:nth-child(8), #monitors-table td:nth-child(8),
#us-monitors-table th:nth-child(8), #us-monitors-table td:nth-child(8) { width: 10%; }
#monitors-table th:nth-child(9), #monitors-table td:nth-child(9),
#us-monitors-table th:nth-child(9), #us-monitors-table td:nth-child(9) { width: 7%; }"""

mon_cols_new = """#monitors-table th:nth-child(1), #monitors-table td:nth-child(1),
#us-monitors-table th:nth-child(1), #us-monitors-table td:nth-child(1) { width: 14%; }
#monitors-table th:nth-child(2), #monitors-table td:nth-child(2),
#us-monitors-table th:nth-child(2), #us-monitors-table td:nth-child(2) { width: 14%; }
#monitors-table th:nth-child(3), #monitors-table td:nth-child(3),
#us-monitors-table th:nth-child(3), #us-monitors-table td:nth-child(3) { width: 11%; }
#monitors-table th:nth-child(4), #monitors-table td:nth-child(4),
#us-monitors-table th:nth-child(4), #us-monitors-table td:nth-child(4) { width: 9%; }
#monitors-table th:nth-child(5), #monitors-table td:nth-child(5),
#us-monitors-table th:nth-child(5), #us-monitors-table td:nth-child(5) { width: 9%; } /* 漲跌 / 漲幅 */
#monitors-table th:nth-child(6), #monitors-table td:nth-child(6),
#us-monitors-table th:nth-child(6), #us-monitors-table td:nth-child(6) { width: 11%; } /* 停損 / 停利 */
#monitors-table th:nth-child(7), #monitors-table td:nth-child(7),
#us-monitors-table th:nth-child(7), #us-monitors-table td:nth-child(7) { width: 9%; }  /* 風控燈號 */
#monitors-table th:nth-child(8), #monitors-table td:nth-child(8),
#us-monitors-table th:nth-child(8), #us-monitors-table td:nth-child(8) { width: 9%; }  /* 進場訊號 */
#monitors-table th:nth-child(9), #monitors-table td:nth-child(9),
#us-monitors-table th:nth-child(9), #us-monitors-table td:nth-child(9) { width: 9%; }  /* 風報比 */
#monitors-table th:nth-child(10), #monitors-table td:nth-child(10),
#us-monitors-table th:nth-child(10), #us-monitors-table td:nth-child(10) { width: 5%; } /* 操作 */"""

content, ok = robust_replace(content, mon_cols_old, mon_cols_new)
print("3. Monitors columns updated:", ok)

# 4. Append animation and color styling classes to the end of index.css
styling_classes = """

/* --- Staggered Card Animation & Price Change Colors (Added by Antigravity) --- */
@keyframes cardFadeIn {
    0% {
        opacity: 0;
        transform: translateY(15px);
    }
    100% {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-fade-in {
    animation: cardFadeIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) forwards;
    opacity: 0;
}

.delay-1 { animation-delay: 0.04s; }
.delay-2 { animation-delay: 0.08s; }
.delay-3 { animation-delay: 0.12s; }
.delay-4 { animation-delay: 0.16s; }
.delay-5 { animation-delay: 0.20s; }
.delay-6 { animation-delay: 0.24s; }
.delay-7 { animation-delay: 0.28s; }
.delay-8 { animation-delay: 0.32s; }

/* Price change / change percent styled classes */
td.up-red {
    color: var(--color-danger) !important;
}
td.down-green {
    color: var(--color-success) !important;
}
td.flat-gray {
    color: var(--text-muted) !important;
}
"""

content += styling_classes
print("4. Appended animation and color classes to index.css")

with open(css_path, "w", encoding="utf-8") as f:
    f.write(content)

print("CSS patching completed successfully!")
