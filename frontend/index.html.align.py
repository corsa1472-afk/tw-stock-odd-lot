html_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.html"
css_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.css"

with open(html_path, "r", encoding="utf-8") as f:
    html_content = f.read()

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

# 1. Restructure Tab C panel header to align with Tab B
old_us_header = """                <section class="panel-card glass-panel hidden animate-fade-in" id="us-section">
                    <div class="panel-header us-panel-header">
                        <h2><i class="fa-solid fa-earth-americas"></i> 美股追蹤 <span id="us-count-label" class="panel-count-label"></span><span id="us-update-time" class="panel-update-label"></span></h2>
                        <div class="actions us-panel-actions" style="display: flex; align-items: center; gap: 10px;">
                            <span id="scan-us-status-label" style="font-size: 0.75rem; color: var(--text-muted);">已載入緩存</span>
                            <button id="refresh-us-btn" class="icon-btn btn-primary" title="重新整理美股技術指標">
                                <i class="fa-solid fa-rotate"></i> 重新整理
                            </button>
                            <button id="scan-us-btn" class="icon-btn btn-secondary" title="重新掃描美股全市場 (S&P 500 & Nasdaq 100)">
                                <i class="fa-solid fa-radar"></i> 重新掃描美股全市場
                            </button>
                        </div>
                    </div>"""

new_us_header = """                <section class="panel-card glass-panel hidden animate-fade-in" id="us-section">
                    <div class="panel-header us-panel-header">
                        <h2><i class="fa-solid fa-earth-americas"></i> 美股熱門與自選追蹤</h2>
                        <div class="actions us-panel-actions" style="display: flex; align-items: center; gap: 10px;">
                            <span id="scan-us-status-label" style="font-size: 0.75rem; color: var(--text-muted);">已載入最新緩存 <span id="us-count-label" class="panel-count-label"></span> <span id="us-update-time" class="panel-update-label"></span> <span style="opacity:0.6; margin-left:6px;">(每天盤後掃描一次即可，掃描需時二分鐘)</span></span>
                            <button id="refresh-us-btn" class="icon-btn btn-secondary" title="重新整理美股技術指標">
                                <i class="fa-solid fa-rotate"></i> 重新整理
                            </button>
                            <button id="scan-us-btn" class="icon-btn btn-primary" title="重新掃描美股全市場 (S&P 500 & Nasdaq 100)">
                                <i class="fa-solid fa-radar"></i> 重新掃描美股全市場
                            </button>
                        </div>
                    </div>"""

html_content, ok = robust_replace(html_content, old_us_header, new_us_header)
print("1. Restructured US Panel Header:", ok)

# 2. Replace old criteria-bar in Tab C with the modern Criteria Summary Bar
old_us_criteria = """                    <div class="criteria-bar">
                        <span class="criteria-title"><i class="fa-solid fa-filter"></i> 追蹤內容：</span>
                        <span class="criteria-pill">SPY / QQQ / DIA / IWM 指標 ETF</span>
                        <span class="criteria-pill">Yahoo 美股頁完整指標股</span>
                        <span class="criteria-pill">Yahoo Most Active 熱門股</span>
                        <span class="criteria-sort"><i class="fa-solid fa-arrow-down-wide-short"></i> 排序：進場訊號 <i class="fa-solid fa-circle-info entry-signal-info"></i> &gt; 符合燈號數 &gt; 風報比 &gt; 成交量</span>
                    </div>"""

new_us_criteria = """                    <!-- US Criteria Summary Bar -->
                    <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom: 0.75rem; padding: 10px 14px; background: rgba(99,102,241,0.07); border-radius: 10px; border: 1px solid rgba(99,102,241,0.15); font-size: 0.78rem; color: var(--text-secondary); align-items: center;">
                        <span style="color: var(--color-primary); font-weight: 700; margin-right: 4px;"><i class="fa-solid fa-filter"></i> 篩選條件：</span>
                        <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px;">① 成交量 > 500k 股</span>
                        <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px;">② 日線收盤價 > MA20 & MA60 (趨勢向上)</span>
                        <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px;">③ 收盤 > MA20 & MA60</span>
                        <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px;">④ 底底高型態</span>
                        <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px;">⑤ 預期風報比 R值 >= 1.0</span>
                        <span style="color: var(--text-muted); margin: 0 4px;">｜</span>
                        <span style="color: #f59e0b; font-weight: 700;"><i class="fa-solid fa-arrow-down-wide-short"></i> 排序：進場訊號 <i class="fa-solid fa-circle-info entry-signal-info"></i> > 符合燈號數 > 風報比 > 成交量</span>
                        <span style="color: var(--text-muted); margin: 0 4px;">｜</span>
                        <span style="color: var(--text-muted);" data-tooltip="美股股價來自 Yahoo Finance 盤中延遲約 15 分鐘。請點擊「重新整理」或「重新掃描美股全市場」即可更新價格。"><i class="fa-solid fa-clock"></i> 股價：延遲15分</span>
                    </div>"""

html_content, ok = robust_replace(html_content, old_us_criteria, new_us_criteria)
print("2. Replaced US Criteria Summary Bar:", ok)

# 3. Align US stock table headers in Tab C with Tab B exactly
old_us_table_headers = """                            <thead>
                                <tr>
                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價<br><span class="desc-tip">美元</span></th>
                                    <th>漲跌 / 漲幅</th>
                                    <th>成交量<br><span class="desc-tip">千股</span></th>
                                    <th>日線趨勢<br><span class="desc-tip">收盤價 &gt; MA20 &amp; MA60</span></th>
                                    <th>60分K打底<br><span class="desc-tip">低檔交叉2~3次</span></th>
                                    <th>進場訊號 <i class="fa-solid fa-circle-info entry-signal-info"></i></th>
                                    <th>底底高/破前高 <i class="fa-solid fa-circle-info morph-rule-info"></i></th>
                                    <th>加分項目<br><span class="desc-tip">帶/估/破/勢/歸</span></th>
                                    <th>風報比</th>
                                    <th class="actions-col">操作</th>
                                </tr>
                            </thead>"""

new_us_table_headers = """                            <thead>
                                <tr>
                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價</th>
                                    <th>漲跌 / 漲幅</th>
                                    <th>成交量</th>
                                    <th>日線<br>趨勢<br><span class="desc-tip">收盤價 > MA20 &amp; MA60</span></th>
                                    <th>60分K<br>打底<br><span class="desc-tip">低檔交叉2~3次</span></th>
                                    <th>進場訊號 <i class="fa-solid fa-circle-info entry-signal-info"></i></th>
                                    <th>底底高/破前高 <i class="fa-solid fa-circle-info morph-rule-info"></i></th>
                                    <th>加分項目<br><span class="desc-tip">帶/估/破/勢/歸</span></th>
                                    <th>
                                        <div style="display: inline-flex; align-items: center; justify-content: center; gap: 4px;">
                                            <span style="line-height: 1.2;">預期風報比<br><span class="desc-tip">R值</span></span>
                                            <i class="fa-solid fa-circle-info" data-tooltip="風報比(R值) = 預期潛在獲利 / 預期最大虧損。&#10;數值越大代表這筆交易越划算。&#10;例如 R=2 代表承擔 1 元的風險去賺取 2 元的利潤。&#10;此數值會隨您的「買入價格」、「停損比例」與「前高停利價格」變動。" style="color: var(--text-muted); cursor: help; font-size: 0.85em; margin-left: 2px;"></i>
                                        </div>
                                    </th>
                                    <th class="actions-col">操作</th>
                                </tr>
                            </thead>"""

html_content, ok = robust_replace(html_content, old_us_table_headers, new_us_table_headers)
print("3. Aligned US Table Column Headers:", ok)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(html_content)

# 4. Modify frontend/index.css to group #us-stock-table under the same column width rules
with open(css_path, "r", encoding="utf-8") as f:
    css_content = f.read()

# Replace the nth-child rules for stock-table & potential-table to include us-stock-table!
css_replacements = [
    (
        "#stock-table th:nth-child(1), #stock-table td:nth-child(1),\n#potential-table th:nth-child(1), #potential-table td:nth-child(1)",
        "#stock-table th:nth-child(1), #stock-table td:nth-child(1),\n#potential-table th:nth-child(1), #potential-table td:nth-child(1),\n#us-stock-table th:nth-child(1), #us-stock-table td:nth-child(1)"
    ),
    (
        "#stock-table th:nth-child(2), #stock-table td:nth-child(2),\n#potential-table th:nth-child(2), #potential-table td:nth-child(2)",
        "#stock-table th:nth-child(2), #stock-table td:nth-child(2),\n#potential-table th:nth-child(2), #potential-table td:nth-child(2),\n#us-stock-table th:nth-child(2), #us-stock-table td:nth-child(2)"
    ),
    (
        "#stock-table th:nth-child(3), #stock-table td:nth-child(3),\n#potential-table th:nth-child(3), #potential-table td:nth-child(3)",
        "#stock-table th:nth-child(3), #stock-table td:nth-child(3),\n#potential-table th:nth-child(3), #potential-table td:nth-child(3),\n#us-stock-table th:nth-child(3), #us-stock-table td:nth-child(3)"
    ),
    (
        "#stock-table th:nth-child(4), #stock-table td:nth-child(4),\n#potential-table th:nth-child(4), #potential-table td:nth-child(4)",
        "#stock-table th:nth-child(4), #stock-table td:nth-child(4),\n#potential-table th:nth-child(4), #potential-table td:nth-child(4),\n#us-stock-table th:nth-child(4), #us-stock-table td:nth-child(4)"
    ),
    (
        "#stock-table th:nth-child(5), #stock-table td:nth-child(5),\n#potential-table th:nth-child(5), #potential-table td:nth-child(5)",
        "#stock-table th:nth-child(5), #stock-table td:nth-child(5),\n#potential-table th:nth-child(5), #potential-table td:nth-child(5),\n#us-stock-table th:nth-child(5), #us-stock-table td:nth-child(5)"
    ),
    (
        "#stock-table th:nth-child(6), #stock-table td:nth-child(6),\n#potential-table th:nth-child(6), #potential-table td:nth-child(6)",
        "#stock-table th:nth-child(6), #stock-table td:nth-child(6),\n#potential-table th:nth-child(6), #potential-table td:nth-child(6),\n#us-stock-table th:nth-child(6), #us-stock-table td:nth-child(6)"
    ),
    (
        "#stock-table th:nth-child(7), #stock-table td:nth-child(7),\n#potential-table th:nth-child(7), #potential-table td:nth-child(7)",
        "#stock-table th:nth-child(7), #stock-table td:nth-child(7),\n#potential-table th:nth-child(7), #potential-table td:nth-child(7),\n#us-stock-table th:nth-child(7), #us-stock-table td:nth-child(7)"
    ),
    (
        "#stock-table th:nth-child(8), #stock-table td:nth-child(8),\n#potential-table th:nth-child(8), #potential-table td:nth-child(8)",
        "#stock-table th:nth-child(8), #stock-table td:nth-child(8),\n#potential-table th:nth-child(8), #potential-table td:nth-child(8),\n#us-stock-table th:nth-child(8), #us-stock-table td:nth-child(8)"
    ),
    (
        "#stock-table th:nth-child(9), #stock-table td:nth-child(9),\n#potential-table th:nth-child(9), #potential-table td:nth-child(9)",
        "#stock-table th:nth-child(9), #stock-table td:nth-child(9),\n#potential-table th:nth-child(9), #potential-table td:nth-child(9),\n#us-stock-table th:nth-child(9), #us-stock-table td:nth-child(9)"
    ),
    (
        "#stock-table th:nth-child(10), #stock-table td:nth-child(10),\n#potential-table th:nth-child(10), #potential-table td:nth-child(10)",
        "#stock-table th:nth-child(10), #stock-table td:nth-child(10),\n#potential-table th:nth-child(10), #potential-table td:nth-child(10),\n#us-stock-table th:nth-child(10), #us-stock-table td:nth-child(10)"
    ),
    (
        "#stock-table th:nth-child(11), #stock-table td:nth-child(11),\n#potential-table th:nth-child(11), #potential-table td:nth-child(11)",
        "#stock-table th:nth-child(11), #stock-table td:nth-child(11),\n#potential-table th:nth-child(11), #potential-table td:nth-child(11),\n#us-stock-table th:nth-child(11), #us-stock-table td:nth-child(11)"
    ),
    (
        "#stock-table th:nth-child(12), #stock-table td:nth-child(12),\n#potential-table th:nth-child(12), #potential-table td:nth-child(12)",
        "#stock-table th:nth-child(12), #stock-table td:nth-child(12),\n#potential-table th:nth-child(12), #potential-table td:nth-child(12),\n#us-stock-table th:nth-child(12), #us-stock-table td:nth-child(12)"
    )
]

for target, replacement in css_replacements:
    css_content, ok = robust_replace(css_content, target, replacement)
    print(f"CSS Grouping for {target.split(' ')[0]}:", ok)

# Now, remove the old independent #us-stock-table rules (lines 1770 to 1780 in original, or current equivalents)
old_us_independent_rules = """#us-stock-table th:nth-child(1), #us-stock-table td:nth-child(1) { width: 8%; }
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

css_content, ok = robust_replace(css_content, old_us_independent_rules, "")
print("Removed old independent US CSS rules:", ok)

with open(css_path, "w", encoding="utf-8") as f:
    f.write(css_content)

print("Alignment modifications completed successfully!")
