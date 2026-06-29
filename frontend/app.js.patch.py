js_path = r"c:\Users\hopes\OneDrive\文件\tw_stock_odd_lot-anti\frontend\app.js"

with open(js_path, "r", encoding="utf-8") as f:
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

# 1. Update version number constants
content, ok = robust_replace(content,
    'const APP_VERSION = "v1.6.10";\nconst APP_REVISION_DATE = "260622";\nconst APP_REVISION_TIME = "152137";',
    'const APP_VERSION = "v1.6.11";\nconst APP_REVISION_DATE = "260624";\nconst APP_REVISION_TIME = "153316";'
)
print("1. Version update:", ok)

# 2. Add allUsStocks global variable
content, ok = robust_replace(content,
    'let usStocksData = [];',
    'let usStocksData = [];\nlet allUsStocks = [];'
)
print("2. Global allUsStocks added:", ok)

# 3. Add formatChangeCell utility function
# We will insert it right before "function renderStockTable"
format_change_cell_code = """function formatChangeCell(change, percent) {
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
}

function retriggerCardAnimations() {
    const cards = document.querySelectorAll('#calc-active .animate-fade-in');
    cards.forEach(card => {
        card.classList.remove('animate-fade-in');
        void card.offsetWidth; // Force reflow
        card.classList.add('animate-fade-in');
    });
}

"""
content, ok = robust_replace(content,
    'function renderStockTable(stocks) {',
    format_change_cell_code + 'function renderStockTable(stocks) {'
)
print("3. formatChangeCell added:", ok)

# 4. Add fetchAndPopulateUsDatalist function
# We will insert it right after "function fetchAndPopulateDatalist"
us_datalist_code = """
async function fetchAndPopulateUsDatalist() {
    try {
        const r = await fetch(`${API_BASE}/all_us_stocks`);
        if (r.ok) {
            allUsStocks = await r.json();
            const datalist = document.getElementById("all-us-stocks-list");
            if (datalist) {
                datalist.innerHTML = "";
                allUsStocks.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.code;
                    opt.textContent = `${s.code} ${s.name}`;
                    datalist.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.error("Error fetching all US stocks list:", e);
    }
}
"""
content, ok = robust_replace(content,
    '// Setup event listeners',
    us_datalist_code + '\n// Setup event listeners'
)
print("4. fetchAndPopulateUsDatalist added:", ok)

# 5. Add US scanner trigger and polling logic
# We will insert it right after "async function pollScanStatus()"
us_scanner_code = """
async function handleTriggerUSScan() {
    try {
        const response = await fetch(`${API_BASE}/us-stocks/scan`, { method: "POST" });
        const data = await response.json();
        if (response.ok) {
            showToast(data.message, "success");
            pollUSScanStatus();
        } else {
            showToast(data.message, "danger");
        }
    } catch (e) {
        showToast("啟動美股全市場掃描失敗", "danger");
    }
}

async function pollUSScanStatus() {
    const scanUsBtn = document.getElementById("scan-us-btn");
    const scanUsStatusLabel = document.getElementById("scan-us-status-label");
    const scanUsProgressBox = document.getElementById("scan-us-progress-box");
    const scanUsProgressText = document.getElementById("scan-us-progress-text");
    const scanUsProgressBar = document.getElementById("scan-us-progress-bar");
    
    if (!scanUsBtn || !scanUsStatusLabel || !scanUsProgressBox) return;
    
    try {
        const res = await fetch(`${API_BASE}/us-stocks/scan/status`);
        if (!res.ok) return;
        const status = await res.json();
        
        if (status.active) {
            scanUsBtn.disabled = true;
            scanUsBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 掃描中...`;
            scanUsStatusLabel.textContent = `掃描進度: ${status.progress} / ${status.total} 檔`;
            
            scanUsProgressBox.classList.remove("hidden");
            const pct = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
            scanUsProgressText.textContent = `${status.progress} / ${status.total} 檔 (${pct}%)`;
            scanUsProgressBar.style.width = `${pct}%`;
        } else {
            const wasActive = !scanUsProgressBox.classList.contains("hidden");
            scanUsBtn.disabled = false;
            scanUsBtn.innerHTML = `<i class="fa-solid fa-radar"></i> 重新掃描美股全市場`;
            const lastUpdatedStr = status.last_updated ? ` ｜ 最後更新: ${status.last_updated}` : '';
            scanUsStatusLabel.innerHTML = `已載入最新緩存${lastUpdatedStr} <span style="opacity:0.6; margin-left:6px;">(盤後掃描一次即可，掃描需時二分鐘)</span>`;
            scanUsProgressBox.classList.add("hidden");
            
            if (wasActive) {
                showToast("美股全市場掃描已完成！已刷新美股自選清單。", "success");
                await fetchAndAnalyzeUSStocks(false);
            }
        }
    } catch (e) {
        console.error(e);
    }
}
"""
content, ok = robust_replace(content,
    '// Refresh popular stocks\nasync function handleRefreshPopular() {',
    us_scanner_code + '\n// Refresh popular stocks\nasync function handleRefreshPopular() {'
)
print("5. US scanner trigger and poll functions added:", ok)

# 6. Bind US scanner buttons & autocomplete input in setupEventListeners()
content, ok = robust_replace(content,
    '    refreshUSPopularBtn.addEventListener("click", () => handleRefreshUSPopular(false));',
    '    const scanUsBtn = document.getElementById("scan-us-btn");\n    if (scanUsBtn) {\n        scanUsBtn.addEventListener("click", handleTriggerUSScan);\n    }'
)
print("6a. Bound US scan button:", ok)

us_input_event_listener = """    const usStockCodeInput = document.getElementById("us-stock-code-input");
    if (usStockCodeInput) {
        usStockCodeInput.addEventListener("input", () => {
            let val = usStockCodeInput.value.trim();
            if (!val) return;
            
            const isTicker = /^[A-Za-z0-9.\\-]{1,15}$/.test(val) && isNaN(val);
            if (!isTicker && isNaN(val)) {
                const foundStock = allUsStocks.find(s => s.name === val || s.name.toLowerCase().includes(val.toLowerCase()) || val.toLowerCase().includes(s.name.toLowerCase()));
                if (foundStock) {
                    val = foundStock.code;
                }
            }
            
            if (isTicker) {
                val = val.toUpperCase();
                const found = usStocksData.find(s => s.code === val);
                if (found && validPrice(found.current_price) !== null) {
                    selectStockRow(found, false);
                }
            }
        });
    }"""
content, ok = robust_replace(content,
    '    stockCodeInput.addEventListener("input", () => {',
    us_input_event_listener + '\n    stockCodeInput.addEventListener("input", () => {'
)
print("6b. Bound US input listener:", ok)

# 7. Update DOMContentLoaded logic to call autocomplete fetch and poll scanner
content, ok = robust_replace(content,
    '    updateVisitStats();\n    fetchAndPopulateDatalist();',
    '    updateVisitStats();\n    fetchAndPopulateDatalist();\n    fetchAndPopulateUsDatalist();\n    setTimeout(pollUSScanStatus, 500);'
)
print("7a. Added startup autocomplete & poll:", ok)

content, ok = robust_replace(content,
    '        fetchAndRenderMonitors();\n        pollScanStatus();',
    '        fetchAndRenderMonitors();\n        pollScanStatus();\n        pollUSScanStatus();'
)
print("7b. Added 5s polling:", ok)

# 8. Resolve name to ticker in handleAddUSStock()
content, ok = robust_replace(content,
    'async function handleAddUSStock() {\n    const code = usStockCodeInput.value.trim().toUpperCase();',
    'async function handleAddUSStock() {\n    let code = usStockCodeInput.value.trim();\n    if (!code) return;\n    const foundStock = allUsStocks.find(s => s.name.toLowerCase() === code.toLowerCase() || s.code.toLowerCase() === code.toLowerCase() || s.name.toLowerCase().includes(code.toLowerCase()));\n    if (foundStock) {\n        code = foundStock.code;\n    }\n    code = code.toUpperCase();'
)
print("8. Name resolution in handleAddUSStock:", ok)

# 9. Update TW stock table renderer (renderStockTable)
# Increase error colspan
content, ok = robust_replace(content,
    '<td colspan="11" style="text-align: center; padding: 3rem; color: var(--text-muted);">',
    '<td colspan="12" style="text-align: center; padding: 3rem; color: var(--text-muted);">'
)
print("9a. TW empty table colspan updated:", ok)

content, ok = robust_replace(content,
    '<td colspan="8" style="color: var(--color-danger); font-size: 0.85rem;">',
    '<td colspan="9" style="color: var(--color-danger); font-size: 0.85rem;">'
)
print("9b. TW error row colspan updated:", ok)

# Add changeCell in normal row
tw_row_old = """            tr.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
                <td><span class="stock-code">${formatPrice(stock.current_price)}</span></td>
                <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>"""

tw_row_new = """            const changeCell = formatChangeCell(stock.price_change, stock.price_change_percent);
            tr.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
                <td><span class="stock-code">${formatPrice(stock.current_price)}</span></td>
                ${changeCell}
                <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>"""

content, ok = robust_replace(content, tw_row_old, tw_row_new)
print("9c. TW table row change cell inserted:", ok)

# 10. Update US stock table renderer (renderUSStockTable)
content, ok = robust_replace(content,
    'usStockTableBody.innerHTML = `<tr><td colspan="11" class="table-error-cell">目前沒有可顯示的美股資料。</td></tr>`;',
    'usStockTableBody.innerHTML = `<tr><td colspan="12" class="table-error-cell">目前沒有可顯示的美股資料。</td></tr>`;'
)
print("10a. US empty table colspan updated:", ok)

content, ok = robust_replace(content,
    '<td colspan="8" class="table-error-cell">${stock.error}</td>',
    '<td colspan="9" class="table-error-cell">${stock.error}</td>'
)
print("10b. US error row colspan updated:", ok)

us_row_old = """            row.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name" data-tooltip="${tooltip}">${escapeHtmlText(stock.name || stock.code)}</span>${manualBadge}${formatGroupTagsHTML(stock)}</td>
                <td><span class="stock-code">${formatPrice(stock.current_price)}</span></td>
                <td><span class="stock-code">${Number(stock.volume_lots || 0).toLocaleString()}</span></td>"""

us_row_new = """            const changeCell = formatChangeCell(stock.price_change, stock.price_change_percent);
            row.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name" data-tooltip="${tooltip}">${escapeHtmlText(stock.name || stock.code)}</span>${manualBadge}${formatGroupTagsHTML(stock)}</td>
                <td><span class="stock-code">${formatPrice(stock.current_price)}</span></td>
                ${changeCell}
                <td><span class="stock-code">${Number(stock.volume_lots || 0).toLocaleString()}</span></td>"""

content, ok = robust_replace(content, us_row_old, us_row_new)
print("10c. US table row change cell inserted:", ok)

# 11. Update Scanner table renderer (renderPotentialTable)
content, ok = robust_replace(content,
    '<td colspan="11" style="text-align: center; padding: 3rem; color: var(--text-muted);">',
    '<td colspan="12" style="text-align: center; padding: 3rem; color: var(--text-muted);">'
)
print("11a. Scanner empty table colspan updated:", ok)

pot_row_old = """        tr.innerHTML = `
            <td><span class="stock-code">${stock.code}</span></td>
            <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
            <td><span class="stock-code">$${stock.current_price}</span></td>
            <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>"""

pot_row_new = """        const changeCellB = formatChangeCell(stock.price_change, stock.price_change_percent);
        tr.innerHTML = `
            <td><span class="stock-code">${stock.code}</span></td>
            <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
            <td><span class="stock-code">$${stock.current_price}</span></td>
            ${changeCellB}
            <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>"""

content, ok = robust_replace(content, pot_row_old, pot_row_new)
print("11b. Scanner table row change cell inserted:", ok)

# 12. Update TW monitors table renderer (fetchAndRenderMonitors)
content, ok = robust_replace(content,
    '<td colspan="9" style="text-align: center; padding: 2rem; color: var(--text-muted);">',
    '<td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">'
)
print("12a. TW monitor empty table colspan updated:", ok)

tw_mon_row_old = """            tr.innerHTML = `
                <td>
                    <div style="display:flex; flex-direction:column; align-items:center; text-align:center; gap:2px; justify-content:center;">
                        <div style="font-weight:700; display:flex; align-items:center; justify-content:center; gap:4px; max-width:180px; flex-wrap:nowrap;">${formattedName}</div>
                        <span style="font-size:0.7rem; color:var(--text-muted); font-family:var(--font-outfit);">${o.code}</span>
                        <button type="button" class="toggle-buy-btn" data-order-id="${o.order_id}" data-current-action="${o.action}" style="font-size:0.68rem; color:${buyStateColor}; font-weight:700; background:transparent; border:none; padding:0; cursor:pointer;">${buyStateText}</button>
                    </div>
                </td>
                <td><div class="monitor-buy-cell"><span class="editable-price" data-id="${o.order_id}" data-price="${o.buy_price}" title="點擊修改買入價">$${o.buy_price.toFixed(2)}</span><span class="editable-qty" data-id="${o.order_id}" data-price="${o.buy_price}" data-qty="${o.quantity}" data-type="${o.lot_type}" title="點擊修改數量">${qtyText}</span></div></td>
                <td class="monitor-cost-cell">NT$ ${Math.round(Number(o.buy_price) * Number(o.quantity)).toLocaleString()}</td>
                <td style="font-family:var(--font-outfit); font-weight:700; color:var(--color-warning);">
                    $${(o.last_price || o.buy_price).toFixed(2)}
                    ${triggerBadge}
                </td>"""

tw_mon_row_new = """            const lastPrice = o.last_price || o.buy_price;
            const refPrice = o.reference_price || lastPrice;
            const change = lastPrice - refPrice;
            const percent = refPrice > 0 ? (change / refPrice) * 100 : 0.0;
            const changeCellHtml = formatChangeCell(change, percent);

            tr.innerHTML = `
                <td>
                    <div style="display:flex; flex-direction:column; align-items:center; text-align:center; gap:2px; justify-content:center;">
                        <div style="font-weight:700; display:flex; align-items:center; justify-content:center; gap:4px; max-width:180px; flex-wrap:nowrap;">${formattedName}</div>
                        <span style="font-size:0.7rem; color:var(--text-muted); font-family:var(--font-outfit);">${o.code}</span>
                        <button type="button" class="toggle-buy-btn" data-order-id="${o.order_id}" data-current-action="${o.action}" style="font-size:0.68rem; color:${buyStateColor}; font-weight:700; background:transparent; border:none; padding:0; cursor:pointer;">${buyStateText}</button>
                    </div>
                </td>
                <td><div class="monitor-buy-cell"><span class="editable-price" data-id="${o.order_id}" data-price="${o.buy_price}" title="點擊修改買入價">$${o.buy_price.toFixed(2)}</span><span class="editable-qty" data-id="${o.order_id}" data-price="${o.buy_price}" data-qty="${o.quantity}" data-type="${o.lot_type}" title="點擊修改數量">${qtyText}</span></div></td>
                <td class="monitor-cost-cell">NT$ ${Math.round(Number(o.buy_price) * Number(o.quantity)).toLocaleString()}</td>
                <td style="font-family:var(--font-outfit); font-weight:700; color:var(--color-warning);">
                    $${(o.last_price || o.buy_price).toFixed(2)}
                    ${triggerBadge}
                </td>
                ${changeCellHtml}"""

content, ok = robust_replace(content, tw_mon_row_old, tw_mon_row_new)
print("12b. TW monitor table row change cell inserted:", ok)

# 13. Update US monitors table renderer (renderUSMonitors) & Hide card if empty
us_mon_hide_code = """function renderUSMonitors(orders) {
    if (!usMonitorsTableBody) return;
    const usMonitorsCard = document.getElementById("us-monitors-card");
    if (!orders || !orders.length) {
        if (usMonitorsCard) usMonitorsCard.classList.add("hidden");
        return;
    } else {
        if (usMonitorsCard) usMonitorsCard.classList.remove("hidden");
    }
    if (usMonitorCountLabel) usMonitorCountLabel.textContent = `共 ${orders.length} 檔`;
    usMonitorsTableBody.innerHTML = "";
    orders.sort((a, b) => {
        if ((a.action === "BUY") !== (b.action === "BUY")) return a.action === "BUY" ? -1 : 1;
        return String(a.code).localeCompare(String(b.code));
    }).forEach((o, orderIndex, sortedOrders) => {
        const tr = document.createElement("tr");
        tr.dataset.code = o.code;
        if (selectedStock?.code === o.code) tr.classList.add("selected");
        const qtyText = `${Number(o.quantity).toLocaleString()} 股`;
        const risk = Number(o.buy_price) - Number(o.stop_loss_price);
        const rValue = risk > 0 ? ((Number(o.stop_profit_price) - Number(o.buy_price)) / risk).toFixed(2) : "-";
        const nameTooltip = escapeHtmlAttribute(`中文名稱: ${o.name_zh || o.code}\\n英文名稱: ${o.name || o.code}\\n主要業務: ${o.industry || "尚未取得"}`);
        const isBuyAction = o.action === "BUY";
        const buyStateText = isBuyAction ? "已買入" : "未買入";
        tr.style.cursor = "pointer";
        tr.addEventListener("click", e => {
            if (e.target.closest("button") || e.target.closest(".editable-price") || e.target.closest(".editable-qty") || e.target.closest(".editable-risk-price")) return;
            const foundStock = usStocksData.find(stock => stock.code === o.code) || {
                code: o.code,
                symbol: o.symbol || o.code,
                name: o.name || o.code,
                name_zh: o.name_zh || "",
                industry: o.industry || "",
                market: "US",
                current_price: o.last_price || o.buy_price,
                prev_high: o.stop_profit_price,
                system_a_signal: false,
                daily_trend_ok: false,
                kd_under_50: false,
                hourly_kd_ok: false,
                golden_cross_count: 0
            };
            selectStockRow(foundStock, false);
        });
        const buyStateColor = isBuyAction ? "var(--color-danger)" : "var(--text-muted)";
        
        const lastPrice = o.last_price || o.buy_price;
        const refPrice = o.reference_price || lastPrice;
        const change = lastPrice - refPrice;
        const percent = refPrice > 0 ? (change / refPrice) * 100 : 0.0;
        const changeCellHtml = formatChangeCell(change, percent);

        tr.innerHTML = `
            <td><strong data-tooltip="${nameTooltip}">${escapeHtmlText(o.name || o.code)}</strong><span class="monitor-code">${escapeHtmlText(o.code)}</span><button type="button" class="toggle-buy-btn" data-order-id="${o.order_id}" data-current-action="${o.action}" style="font-size:0.68rem;color:${buyStateColor};font-weight:700;background:transparent;border:none;padding:0;cursor:pointer;">${buyStateText}</button></td>
            <td><div class="monitor-buy-cell"><span class="editable-price us-buy-price" data-id="${o.order_id}" data-price="${o.buy_price}">US$${Number(o.buy_price).toFixed(2)}</span><small class="editable-qty" data-id="${o.order_id}" data-price="${o.buy_price}" data-qty="${o.quantity}" data-type="ODD">${qtyText}</small></div></td>
            <td class="monitor-cost-cell">US$ ${Number(Number(o.buy_price) * Number(o.quantity)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td><strong>US$${Number(lastPrice).toFixed(2)}</strong></td>
            ${changeCellHtml}
            <td><span class="editable-risk-price stop-loss-price" data-id="${o.order_id}" data-field="stop_loss_price" data-value="${o.stop_loss_price}">&le; US$${Number(o.stop_loss_price).toFixed(2)}</span><span class="editable-risk-price take-profit-price" data-id="${o.order_id}" data-field="stop_profit_price" data-value="${o.stop_profit_price}">&ge; US$${Number(o.stop_profit_price).toFixed(2)}</span></td>
            <td>${renderRiskLights(o)}</td>
            <td>${renderMonitorSignal(o.code, o.action)}</td>
            <td>${rValue}</td>
            <td><button class="delete-monitor-btn" data-id="${o.order_id}" title="刪除"><i class="fa-regular fa-trash-can"></i></button></td>`;"""

# We replace from "function renderUSMonitors(orders) {" down to "tr.querySelector(".delete-monitor-btn").addEventListener("click"..."
# Let's find the start and end in content
start_idx = content.find("function renderUSMonitors(orders) {")
end_idx = content.find('tr.querySelector(".delete-monitor-btn").addEventListener("click"', start_idx)
if start_idx != -1 and end_idx != -1:
    content = content[:start_idx] + us_mon_hide_code + "\n        " + content[end_idx:]
    print("13. renderUSMonitors updated with card hiding and change cell.")
else:
    print("Warning: Could not find renderUSMonitors block!")

# 14. Trigger card animations in selectStockRow
content, ok = robust_replace(content,
    '    updateCalculations();\n    fetchAndDrawCharts(stock.code);\n}',
    '    updateCalculations();\n    fetchAndDrawCharts(stock.code);\n    retriggerCardAnimations();\n}'
)
print("14. Staggered card animation triggered in selectStockRow:", ok)

with open(js_path, "w", encoding="utf-8") as f:
    f.write(content)

print("JS patching completed successfully!")
