html_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\index.html"

with open(html_path, "r", encoding="utf-8") as f:
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

# 1. Update version number
content, ok = robust_replace(content, 
    '<span id="version-label">版次：v1.6.8 (260620|140124)</span>',
    '<span id="version-label">版次：v1.6.11 (260624|153316)</span>'
)
print("1. Update version:", ok)

# 2. TW stock list table header (stock-table)
tw_header_old = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價</th>
                                    <th>成交量</th>"""

tw_header_new = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價</th>
                                    <th>漲跌 / 漲幅</th>
                                    <th>成交量</th>"""

content, ok = robust_replace(content, tw_header_old, tw_header_new)
print("2. TW stock-table header:", ok)

# 3. US stock watchlist table header (us-stock-table)
us_header_old = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價<br><span class="desc-tip">美元</span></th>
                                    <th>成交量<br><span class="desc-tip">千股</span></th>"""

us_header_new = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價<br><span class="desc-tip">美元</span></th>
                                    <th>漲跌 / 漲幅</th>
                                    <th>成交量<br><span class="desc-tip">千股</span></th>"""

content, ok = robust_replace(content, us_header_old, us_header_new)
print("3. US us-stock-table header:", ok)

# 4. Potential bottoms scanner table header (potential-table)
pot_header_old = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價</th>
                                    <th>成交量</th>"""

pot_header_new = """                                    <th>代號</th>
                                    <th>股名</th>
                                    <th>股價</th>
                                    <th>漲跌 / 漲幅</th>
                                    <th>成交量</th>"""

content, ok = robust_replace(content, pot_header_old, pot_header_new)
print("4. TW potential-table header:", ok)

# 5. TW monitors table header (monitors-table)
tw_mon_old = """                                        <th>個股</th>
                                        <th>買入價 / 數量</th>
                                        <th>小計</th>
                                        <th>即時價</th>
                                        <th>停損 / 停利</th>"""

tw_mon_new = """                                        <th>個股</th>
                                        <th>買入價 / 數量</th>
                                        <th>小計</th>
                                        <th>即時價</th>
                                        <th>漲跌 / 漲幅</th>
                                        <th>停損 / 停利</th>"""

content, ok = robust_replace(content, tw_mon_old, tw_mon_new)
print("5. TW monitors-table header:", ok)

# 6. US monitors table header (us-monitors-table)
us_mon_old = """                                        <th>個股</th>
                                        <th>買入價 / 數量</th>
                                        <th>小計</th>
                                        <th>即時價</th>
                                        <th>停損 / 停利</th>"""

us_mon_new = """                                        <th>個股</th>
                                        <th>買入價 / 數量</th>
                                        <th>小計</th>
                                        <th>即時價</th>
                                        <th>漲跌 / 漲幅</th>
                                        <th>停損 / 停利</th>"""

content, ok = robust_replace(content, us_mon_old, us_mon_new)
print("6. US us-monitors-table header:", ok)

# 7. US input autocomplete and datalist
us_input_old = '<input id="us-stock-code-input" type="text" maxlength="15" autocomplete="off" placeholder="輸入美股代號（如 COST、TSM）">'
us_input_new = """<input id="us-stock-code-input" type="text" list="all-us-stocks-list" maxlength="15" autocomplete="off" placeholder="輸入美股代號（如 COST、TSM）">
                            <datalist id="all-us-stocks-list"></datalist>"""

content, ok = robust_replace(content, us_input_old, us_input_new)
print("7. US input autocomplete:", ok)

# 8. US Scanner button & progress box
us_actions_old = """                        <div class="actions us-panel-actions">
                            <button id="refresh-us-btn" class="icon-btn btn-primary" title="重新整理美股技術指標">
                                <i class="fa-solid fa-rotate"></i> 重新整理
                            </button>
                            <button id="refresh-us-popular-btn" class="icon-btn btn-secondary" title="重刷 Yahoo 美國市場熱門排行">
                                <i class="fa-solid fa-fire"></i> 重刷 Yahoo 熱門
                            </button>
                        </div>
                    </div>"""

us_actions_new = """                        <div class="actions us-panel-actions" style="display: flex; align-items: center; gap: 10px;">
                            <span id="scan-us-status-label" style="font-size: 0.75rem; color: var(--text-muted);">已載入緩存</span>
                            <button id="refresh-us-btn" class="icon-btn btn-primary" title="重新整理美股技術指標">
                                <i class="fa-solid fa-rotate"></i> 重新整理
                            </button>
                            <button id="scan-us-btn" class="icon-btn btn-secondary" title="重新掃描美股全市場 (S&P 500 & Nasdaq 100)">
                                <i class="fa-solid fa-radar"></i> 重新掃描美股全市場
                            </button>
                        </div>
                    </div>
                    
                    <!-- US Scan Progress Bar -->
                    <div id="scan-us-progress-box" class="hidden" style="background: rgba(0,0,0,0.15); padding: 10px 14px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.03); margin-top: -0.5rem; margin-bottom: 0.75rem;">
                        <div style="display:flex; justify-content:space-between; font-size:0.75rem; margin-bottom:4px;">
                            <span style="color:var(--color-primary); font-weight:600;"><i class="fa-solid fa-arrows-spin fa-spin"></i> 背景掃描中...</span>
                            <span id="scan-us-progress-text" style="color:var(--text-muted);">0 / 0 檔 (0%)</span>
                        </div>
                        <div class="scan-progress-container">
                            <div id="scan-us-progress-bar" class="scan-progress-bar"></div>
                        </div>
                    </div>"""

content, ok = robust_replace(content, us_actions_old, us_actions_new)
print("8. US Scanner button & progress box:", ok)

# 9. Animation classes for left panel cards
content, ok = robust_replace(content, 
    '<section class="panel-card glass-panel" id="stock-section">',
    '<section class="panel-card glass-panel animate-fade-in" id="stock-section">'
)
print("9a. Animation TW Watchlist:", ok)

content, ok = robust_replace(content, 
    '<section class="panel-card glass-panel hidden" id="us-section">',
    '<section class="panel-card glass-panel hidden animate-fade-in" id="us-section">'
)
print("9b. Animation US Watchlist:", ok)

content, ok = robust_replace(content, 
    '<section class="panel-card glass-panel hidden" id="potential-section">',
    '<section class="panel-card glass-panel hidden animate-fade-in" id="potential-section">'
)
print("9c. Animation Scanner:", ok)

content, ok = robust_replace(content, 
    '<section class="panel-card glass-panel" id="calc-monitors-card">',
    '<section class="panel-card glass-panel animate-fade-in delay-1" id="calc-monitors-card">'
)
print("9d. Animation TW Risk:", ok)

content, ok = robust_replace(content, 
    '<section class="panel-card glass-panel" id="us-monitors-card" style="margin-top: 1rem;">',
    '<section class="panel-card glass-panel animate-fade-in delay-2" id="us-monitors-card" style="margin-top: 1rem;">'
)
print("9e. Animation US Risk:", ok)

# 10. Animation classes for right detail panel cards
content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-signal-card" style="display: flex; flex-direction: column; gap: 1.5rem;">',
    '<section class="panel-card glass-panel animate-fade-in delay-1" id="calc-signal-card" style="display: flex; flex-direction: column; gap: 1.5rem;">'
)
print("10a. Animation signal-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-suggested-card" style="display: flex; flex-direction: column; gap: 1.5rem;">',
    '<section class="panel-card glass-panel animate-fade-in delay-2" id="calc-suggested-card" style="display: flex; flex-direction: column; gap: 1.5rem;">'
)
print("10b. Animation suggested-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-prev-suggested-card" style="display: flex; flex-direction: column; gap: 1.5rem;">',
    '<section class="panel-card glass-panel animate-fade-in delay-3" id="calc-prev-suggested-card" style="display: flex; flex-direction: column; gap: 1.5rem;">'
)
print("10c. Animation prev-suggested-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-kline-card">',
    '<section class="panel-card glass-panel animate-fade-in delay-4" id="calc-kline-card">'
)
print("10d. Animation kline-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-institutional-card">',
    '<section class="panel-card glass-panel animate-fade-in delay-5" id="calc-institutional-card">'
)
print("10e. Animation institutional-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-chip-concentration-card">',
    '<section class="panel-card glass-panel animate-fade-in delay-6" id="calc-chip-concentration-card">'
)
print("10f. Animation chip-card:", ok)

content, ok = robust_replace(content,
    '<section class="panel-card glass-panel" id="calc-params-card" style="display: flex; flex-direction: column; gap: 1.5rem;">',
    '<section class="panel-card glass-panel animate-fade-in delay-7" id="calc-params-card" style="display: flex; flex-direction: column; gap: 1.5rem;">'
)
print("10g. Animation params-card:", ok)

with open(html_path, "w", encoding="utf-8") as f:
    f.write(content)

print("HTML patching completed successfully!")
