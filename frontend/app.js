let API_BASE = window.location.origin + "/api";
if (window.location.hostname.includes("firebaseapp.com") || window.location.hostname.includes("web.app") || window.location.hostname.includes("github.io")) {
    // Dynamically resolved from config.json in initApiBase
} else if (window.location.protocol.startsWith("file")) {
    API_BASE = "http://127.0.0.1:8000/api";
}

async function initApiBase() {
    if (window.location.hostname.includes("firebaseapp.com") || window.location.hostname.includes("web.app") || window.location.hostname.includes("github.io")) {
        try {
            const res = await fetch("/config.json?t=" + Date.now());
            if (res.ok) {
                const config = await res.json();
                if (config.api_url) {
                    API_BASE = config.api_url;
                    console.log("Context Firebase: Loaded dynamic API_BASE from config.json: " + API_BASE);
                    return;
                }
            }
        } catch (e) {
            console.error("Failed to load config.json:", e);
        }
        // Fallback to currently running tunnel
        API_BASE = "https://voted-conditional-shut-solving.trycloudflare.com/api";
    }
}

let allStocks = [];

// Global JS Tooltip logic
let tooltipHoveredElement = null;

document.addEventListener('mouseover', function(e) {
    const target = e.target.closest('[data-tooltip]');
    if (target) {
        tooltipHoveredElement = target;
        showGlobalTooltip(target, target.getAttribute('data-tooltip'), e);
    }
});

document.addEventListener('mousemove', function(e) {
    if (tooltipHoveredElement) {
        updateGlobalTooltipPosition(e);
    }
});

document.addEventListener('mouseout', function(e) {
    const target = e.target.closest('[data-tooltip]');
    if (target && target === tooltipHoveredElement) {
        tooltipHoveredElement = null;
        hideGlobalTooltip();
    }
});

document.addEventListener('touchstart', function(e) {
    const target = e.target.closest('[data-tooltip]');
    if (!target) {
        tooltipHoveredElement = null;
        hideGlobalTooltip();
        return;
    }
    
    const tooltip = document.getElementById('global-tooltip');
    if (tooltip && tooltip.style.display === 'block' && tooltip.dataset.owner === target.outerHTML) {
        tooltipHoveredElement = null;
        hideGlobalTooltip();
    } else {
        tooltipHoveredElement = target;
        showGlobalTooltip(target, target.getAttribute('data-tooltip'), e.touches[0]);
        if (tooltip) {
            tooltip.dataset.owner = target.outerHTML;
        }
    }
}, { passive: true });

document.addEventListener('touchmove', function(e) {
    if (tooltipHoveredElement && e.touches.length > 0) {
        updateGlobalTooltipPosition(e.touches[0]);
    }
}, { passive: true });

function escapeHtmlText(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

function escapeHtmlAttribute(value) {
    return escapeHtmlText(value)
        .replaceAll("\r", "&#13;")
        .replaceAll("\n", "&#10;");
}

function showGlobalTooltip(element, text, eventObj) {
    if (!text) return;
    let tooltip = document.getElementById('global-tooltip');
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'global-tooltip';
        document.body.appendChild(tooltip);
    }
    
    tooltip.textContent = text;
    tooltip.style.display = 'block';
    
    if (eventObj) {
        updateGlobalTooltipPosition(eventObj);
    } else {
        const rect = element.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;
        
        let top = rect.top + scrollTop - tooltip.offsetHeight - 8;
        let left = rect.left + scrollLeft + (rect.width - tooltip.offsetWidth) / 2;
        
        if (left < 10) left = 10;
        if (left + tooltip.offsetWidth > window.innerWidth - 10) {
            left = window.innerWidth - tooltip.offsetWidth - 10;
        }
        if (rect.top - tooltip.offsetHeight - 8 < 10) {
            top = rect.bottom + scrollTop + 8;
        }
        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
    }
}

function getBodyScale() {
    const transform = window.getComputedStyle(document.body).transform;
    if (!transform || transform === 'none') return 1;
    const matrix = transform.match(/^matrix\(([^,]*),\s*([^,]*),\s*([^,]*),\s*([^,]*),\s*([^,]*),\s*([^,]*)\)$/);
    if (matrix) {
        return parseFloat(matrix[1]);
    }
    return 1;
}

function updateGlobalTooltipPosition(e) {
    const tooltip = document.getElementById('global-tooltip');
    if (!tooltip || tooltip.style.display !== 'block') return;
    
    const scale = getBodyScale();
    const tooltipWidth = tooltip.offsetWidth;
    const tooltipHeight = tooltip.offsetHeight;
    
    let left = (e.pageX / scale) - (tooltipWidth / 2);
    let top = (e.pageY / scale) - tooltipHeight - (15 / scale);
    
    const scaledWidth = window.innerWidth / scale;
    const scrollLeft = (window.pageXOffset || document.documentElement.scrollLeft) / scale;
    const scrollTop = (window.pageYOffset || document.documentElement.scrollTop) / scale;
    
    if (left < 10) {
        left = 10;
    }
    const maxLeft = scaledWidth - tooltipWidth - 10 + scrollLeft;
    if (left > maxLeft) {
        left = maxLeft;
    }
    if (top < 10 + scrollTop) {
        top = (e.pageY / scale) + (20 / scale); 
    }
    
    tooltip.style.left = left + 'px';
    tooltip.style.top = top + 'px';
}

function hideGlobalTooltip() {
    const tooltip = document.getElementById('global-tooltip');
    if (tooltip) {
        tooltip.style.display = 'none';
        delete tooltip.dataset.owner;
    }
}

let currentStocksData = [];
let totalPopularCount = 0;
let usStocksData = [];
let enableUSFilter = false;
let usScanTotal = 0;
let usScanLastUpdated = "";
let usScanPotentialsCount = 0;
let allUsStocks = [];
let potentialStocksData = [];
let currentMonitorsData = [];
let currentTrailingData = [];
let monitorSignalsData = {};
let monitorSignalsLoading = false;
let selectedStock = null;
let activeTab = "tab-a"; // tab-a, tab-b, or tab-c
let currentPricePerShare = 0;
let oddLotInputSource = "amount";

const APP_VERSION = "v1.6.48";
const APP_REVISION_DATE = "260629";
const APP_REVISION_TIME = "072259";

// Load lists from cloud storage
async function loadStocksFromStorage() {
    try {
        const response = await fetch(`${API_BASE}/lists`);
        if (response.ok) {
            const data = await response.json();
            console.log("成功從雲端載入清單資料", data);
            if (data.monitorList) {
                currentMonitorsData = data.monitorList;
            }
            if (data.trailingList) {
                currentTrailingData = data.trailingList;
            }
        }
    } catch (e) {
        console.error("載入雲端清單失敗:", e);
    }
}

// Save lists to cloud storage
async function saveStocksToStorage(customStockList = null, customMonitorList = null) {
    try {
        const stockList = customStockList || currentStocksData.map(s => {
            let addedBy = s.added_by;
            if (!addedBy) {
                if (s.name.includes(" (手動)") || s.name.includes(" (手動加入)")) addedBy = "manual";
                else if (s.name.includes(" (文字)") || s.name.includes(" (文字加入)")) addedBy = "text";
                else if (s.name.includes(" (掃描)") || s.name.includes(" (新增)")) addedBy = "new_popular";
                else addedBy = "popular";
            }
            return {
                code: s.code,
                symbol: s.symbol,
                name: s.name.replace(" (手動)", "").replace(" (文字)", "").replace(" (掃描)", "").replace(" (手動加入)", "").replace(" (文字加入)", "").replace(" (新增)", ""),
                added_by: addedBy
            };
        });
        
        const monitorList = customMonitorList || currentMonitorsData;
        
        const response = await fetch(`${API_BASE}/lists`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                stockList: stockList,
                monitorList: monitorList,
                trailingList: currentTrailingData
            })
        });
        if (response.ok) {
            console.log("雲端清單已同步保存");
        }
    } catch (e) {
        console.error("同步至雲端失敗:", e);
    }
}

function formatStockNameHTML(stock, fallbackCode="", industry="", showBadge = true) {
    const rawName = repairMojibake(stock.name || "自訂股票");
    let clean = rawName
        .replace(" (手動)", "")
        .replace(" (文字)", "")
        .replace(" (掃描)", "")
        .replace(" (手動加入)", "")
        .replace(" (文字加入)", "")
        .replace(" (新增)", "")
        .replace(" (全市場掃描新增)", "")
        .trim();
    if (!clean || clean.includes("?")) {
        const prefix = clean.split(/[（(]/)[0].trim();
        clean = prefix && !prefix.includes("?") ? prefix : "自訂股票";
    }
    let badge = "";
    if (showBadge) {
        if (stock.added_by === "manual" || rawName.includes(" (手動)") || rawName.includes(" (手動加入)")) {
            badge = `<span class="added-by-badge manual" data-tooltip="手動加入"><i class="fa-solid fa-hand-pointer"></i></span>`;
        } else if (stock.added_by === "text" || rawName.includes(" (文字)") || rawName.includes(" (文字加入)")) {
            badge = `<span class="added-by-badge text" data-tooltip="文字檔加入"><i class="fa-solid fa-file-import"></i></span>`;
        } else if (stock.added_by === "scan" || stock.added_by === "new_popular" || rawName.includes(" (掃描)") || rawName.includes(" (新增)") || rawName.includes(" (全市場掃描新增)")) {
            badge = `<span class="added-by-badge new-popular" data-tooltip="全市場掃描新增"><i class="fa-solid fa-radar" style="margin-right:2px;"></i>掃</span>`;
        }
    }
    
    let dispPrefix = "";
    if (stock.disposition) {
        const period = stock.disposition.period || "";
        const measures = stock.disposition.measures || "";
        const reason = stock.disposition.reason || "";
        const tooltip = `【處置】\n原因：${reason}\n期間：${period}\n措施：${measures}`;
        dispPrefix = `<span class="disposition-badge" data-tooltip="${tooltip}" style="margin-right: 4px; padding: 1px 4px; font-size: 0.65rem;">處</span>`;
    }
    
    const tooltipText = escapeHtmlAttribute(industry ? `主要業務: ${industry}` : `股票代號: ${stock.code || fallbackCode}`);
    return `${dispPrefix}<span data-tooltip="${tooltipText}" style="text-decoration: underline dotted rgba(255,255,255,0.3); text-underline-offset: 4px; cursor:help;">${escapeHtmlText(clean)}</span>${badge}${formatGroupTagsHTML(stock)}`;
}

function formatGroupTagsHTML(stock) {
    const category = String(stock.group_category || "").trim();
    const concepts = Array.isArray(stock.concepts)
        ? stock.concepts.filter(Boolean).map(String).slice(0, 3)
        : [];
    if (!category && concepts.length === 0) return "";
    const isUS = stock.market === "US";
    const tooltip = escapeHtmlAttribute(
        `${isUS ? "產業板塊" : "類股"}：${category || "未分類"}\n所屬概念：${concepts.length ? concepts.join("、") : "未分類"}`
    );
    const abbreviate = value => {
        const map = {
            "半導體業": "半", "電腦及週邊": "電", "通信網路業": "網", "光電業": "光",
            "電子零組件": "零", "電子通路業": "通", "金融保險業": "金", "航運業": "航",
            "生技醫療業": "生", "汽車工業": "車", "電機機械": "機", "建材營造": "建",
            "鋼鐵工業": "鋼", "塑膠工業": "塑", "化學工業": "化", "食品工業": "食",
            "觀光餐旅": "觀", "其他類股": "他", "科技": "科", "通訊服務": "訊",
            "金融服務": "金", "非必需消費": "非", "民生消費": "民", "能源": "能",
            "醫療保健": "醫", "工業": "工", "原物料": "原", "不動產": "房",
            "公用事業": "公", "消費電子": "消", "電子代工": "代", "電網建設": "電網",
            "半導體": "半", "雲端運算": "雲", "網路通訊": "網", "電動車": "EV",
            "電子商務": "商", "金融科技": "Fin", "影音串流": "流", "生技醫療": "生",
            "綠能": "綠", "航太國防": "航太", "機器人": "機器", "散熱": "散",
            "面板": "板", "航運": "航", "指數投資": "指", "個股題材": "題",
            "資料中心": "DC", "企業軟體": "軟", "數位廣告": "廣", "社群平台": "社",
            "數位娛樂": "娛", "儲能": "儲", "銀行": "銀", "支付": "付",
            "大型股": "大", "科技股": "科股", "小型股": "小"
        };
        return map[value] || (value.length <= 3 ? value : value.slice(0, 1));
    };
    const categoryShort = category ? abbreviate(category) : "";
    const conceptShorts = concepts
        .map(concept => abbreviate(concept))
        .filter((value, index, values) => value && value !== categoryShort && values.indexOf(value) === index);
    const categoryTag = category
        ? `<span class="stock-group-tag category ${isUS ? "us" : "tw"}">${escapeHtmlText(categoryShort)}</span>`
        : "";
    const conceptTags = conceptShorts
        .map(concept => `<span class="stock-group-tag concept">${escapeHtmlText(concept)}</span>`)
        .join("");
    return `<span class="stock-group-tags" data-tooltip="${tooltip}">${categoryTag}${conceptTags}</span>`;
}

function repairMojibake(value) {
    if (!value) return "";
    const text = String(value);
    if (!/[åæçèéïã¤¥ª]/.test(text)) return text;
    try {
        const bytes = Uint8Array.from(text, ch => ch.charCodeAt(0) & 0xff);
        return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    } catch (e) {
        return text;
    }
}

function cleanDisplayStockName(value) {
    let text = repairMojibake(value || "").trim();
    if (!text) return "自訂股票";
    if (text.includes("?")) {
        const prefix = text.split(/[（(]/)[0].trim();
        text = prefix && !prefix.includes("?") ? prefix : "自訂股票";
    }
    return text;
}

function validPrice(value) {
    const number = Number(value);
    return Number.isFinite(number) && number > 0 ? number : null;
}

function formatPrice(value, fallback = "--") {
    const number = validPrice(value);
    return number === null ? fallback : `$${number.toFixed(2)}`;
}

function getRiskTriggerState(order) {
    const currentPrice = validPrice(order.last_price) || validPrice(order.buy_price);
    const stopLoss = validPrice(order.stop_loss_price);
    const stopProfit = validPrice(order.stop_profit_price);

    if (currentPrice !== null && stopLoss !== null && currentPrice <= stopLoss) {
        return "stop-loss";
    }
    if (currentPrice !== null && stopProfit !== null && currentPrice >= stopProfit) {
        return "take-profit";
    }
    return "";
}

function applyRiskTriggerHighlight(row, order) {
    const triggerState = getRiskTriggerState(order);
    if (!triggerState) return;

    row.classList.add(`risk-trigger-${triggerState}`);
    row.dataset.riskTrigger = triggerState;
}

function getActiveSignalsCount(stock) {
    if (!stock || !stock.signals) return 0;
    let count = 0;
    const keys = ["vol_breakout", "undervalued", "breakout_5ma", "momentum", "mean_reversion"];
    keys.forEach(k => {
        if (stock.signals[k] === true) {
            count++;
        }
    });
    return count;
}

function signalLight(ok, shape = "dot") {
    const cls = ok ? "red" : "off";
    return `<div class="status-indicator"><span class="light-${shape} ${cls}"></span></div>`;
}

function getLatestIntradayPrice(intradayList) {
    if (!intradayList || intradayList.length === 0) return null;
    for (let i = intradayList.length - 1; i >= 0; i--) {
        const price = Number(intradayList[i].price);
        if (!Number.isNaN(price)) return price;
    }
    return null;
}

function isTodayString(dateStr) {
    if (!dateStr) return false;
    const now = new Date();
    const yyyy = now.getFullYear();
    const mm = String(now.getMonth() + 1).padStart(2, "0");
    const dd = String(now.getDate()).padStart(2, "0");
    return dateStr === `${yyyy}-${mm}-${dd}`;
}

function inTwIntradaySession(dateStr) {
    if (!isTodayString(dateStr)) return false;
    const now = new Date();
    const minutes = now.getHours() * 60 + now.getMinutes();
    return now.getDay() >= 1 && now.getDay() <= 5 && minutes >= 9 * 60 && minutes < 13 * 60 + 30;
}

// Render 5 Strategy lights: 帶量突破 (vol_breakout), 價質低估 (undervalued), 破前高站穩5日均線 (breakout_5ma), 動能順勢 (momentum), 均值回歸 (mean_reversion)
function renderStrategyLights(signals) {
    const strategies = [
        { key: "vol_breakout", label: "帶量突破", char: "帶", desc: "今日收盤上漲且成交量大於20日均量1.5倍，顯示主力資金介入" },
        { key: "undervalued", label: "價值低估", char: "估", desc: "股價落在近一個月波動區間的底部30%以內，下檔風險較低" },
        { key: "breakout_5ma", label: "破前高站穩5日均線", char: "破", desc: "股價突破近一個月新高，且收盤站穩5日均線，為強勢突破" },
        { key: "momentum", label: "動能順勢", char: "勢", desc: "短中長天期均線(5/10/20日)多頭排列，上升動能極強" },
        { key: "mean_reversion", label: "均值回歸", char: "歸", desc: "股價跌破月線至少5%出現超跌，但今日收紅止跌，有望迎來反彈" }
    ];
    
    if (!signals) {
        return `<div class="strategy-lights-container">` +
            strategies.map(s => `<span class="strategy-light inactive" data-tooltip="${s.label} (未符合)">${s.char}</span>`).join("") +
            `</div>`;
    }
    
    return `<div class="strategy-lights-container">` +
        strategies.map(s => {
            const active = signals[s.key] === true;
            const colorClass = active ? "active" : "inactive";
            const title = active ? `${s.label} (符合)\n${s.desc}` : `${s.label} (未符合)`;
            const displayChar = s.char;
            return `<span class="strategy-light ${colorClass}" data-tooltip="${title}">${displayChar}</span>`;
        }).join("") +
        `</div>`;
}

// ECharts Instances
let intradayChart = null;
let prevIntradayChart = null;
let klineChart = null;
let kdChart = null;
let hourlyKlineChart = null;
let institutionalChart = null;
let chipConcentrationChart = null;
let majorHolderChart = null;
const chartDataCache = new Map();

// DOM Elements
const apiStatusBadge = document.getElementById("api-status");
const stockTableBody = document.getElementById("stock-table-body");
const addStockForm = document.getElementById("add-stock-form");
const stockCodeInput = document.getElementById("stock-code-input");
const refreshBtn = document.getElementById("refresh-btn");
const addBtn = document.getElementById("add-btn");

// Tab Elements
const tabABtn = document.getElementById("tab-a-btn");
const tabCBtn = document.getElementById("tab-c-btn");
const tabBBtn = document.getElementById("tab-b-btn");
const scannerSection = document.getElementById("scanner-section");
const usSection = document.getElementById("us-section");
const potentialSection = document.getElementById("potential-section");
const usStockTableBody = document.getElementById("us-stock-table-body");
const refreshUSBtn = document.getElementById("refresh-us-btn");
const refreshUSPopularBtn = document.getElementById("refresh-us-popular-btn");
const addUSStockForm = document.getElementById("add-us-stock-form");
const usStockCodeInput = document.getElementById("us-stock-code-input");
const addUSBtn = document.getElementById("add-us-btn");

// Tab B Potential Scanner Elements
const potentialTableBody = document.getElementById("potential-table-body");
const scanBtn = document.getElementById("scan-btn");
const scanStatusLabel = document.getElementById("scan-status-label");
const scanProgressBox = document.getElementById("scan-progress-box");
const scanProgressText = document.getElementById("scan-progress-text");
const scanProgressBar = document.getElementById("scan-progress-bar");

// Actions Bar Elements
const refreshPopularBtn = document.getElementById("refresh-popular-btn");
const textFileInput = document.getElementById("text-file-input");

// Calculator Elements
const calcEmptyState = document.getElementById("calc-empty");
const calcActiveState = document.getElementById("calc-active");
const calcStockCode = document.getElementById("calc-stock-code");
const calcStockName = document.getElementById("calc-stock-name");
const calcStockSymbol = document.getElementById("calc-stock-symbol");
const calcStockPrice = document.getElementById("calc-stock-price");
const calcSystemStatus = document.getElementById("calc-system-status");
const calcSignalBadge = document.getElementById("calc-signal-badge");
const calcSignalReason = document.getElementById("calc-signal-reason");

const investmentAmountInput = document.getElementById("investment-amount");
const oddShareCountInput = document.getElementById("odd-share-count");
const oddShareCountGroup = document.getElementById("odd-share-count-group");
const targetBuyPriceInput = document.getElementById("target-buy-price");
const tradeTypeSelect = document.getElementById("trade-type");
const stopLossPctInput = document.getElementById("stop-loss-pct");
const quickAmountButtons = document.querySelectorAll(".btn-quick");

// Suggested Prices variables
const suggestPriceAggressive = document.getElementById("suggest-price-aggressive");
const suggestPriceModerate = document.getElementById("suggest-price-moderate");
const suggestPriceConservative = document.getElementById("suggest-price-conservative");
const refOpen = document.getElementById("ref-open");
const refHigh = document.getElementById("ref-high");
const refLow = document.getElementById("ref-low");
const refClose = document.getElementById("ref-close");

// Previous Day Suggested Prices variables
const suggestPrevPriceAggressive = document.getElementById("suggest-prev-price-aggressive");
const suggestPrevPriceModerate = document.getElementById("suggest-prev-price-moderate");
const suggestPrevPriceConservative = document.getElementById("suggest-prev-price-conservative");
const refPrevOpen = document.getElementById("ref-prev-open");
const refPrevHigh = document.getElementById("ref-prev-high");
const refPrevLow = document.getElementById("ref-prev-low");
const refPrevClose = document.getElementById("ref-prev-close");

const resShares = document.getElementById("res-shares");
const resActualCost = document.getElementById("res-actual-cost");
const resStopLoss = document.getElementById("res-stop-loss");
const stopLossLabel = document.getElementById("stop-loss-label");
const resRiskLoss = document.getElementById("res-risk-loss");
const resStopProfit = document.getElementById("res-stop-profit");
const resProfitGain = document.getElementById("res-profit-gain");
const resRRatio = document.getElementById("res-r-ratio");
const resRComment = document.getElementById("res-r-comment");
const rRatioCard = document.getElementById("r-ratio-card");

const toastContainer = document.getElementById("toast-container");

function setCalculatorMode(hasSelectedStock) {
    if (!calcActiveState) return;
    const alwaysVisibleIds = new Set(["holdings-zone", "calc-monitors-card", "us-monitors-card"]);
    calcActiveState.classList.remove("hidden");
    if (calcEmptyState) {
        calcEmptyState.classList.toggle("hidden", hasSelectedStock);
    }
    Array.from(calcActiveState.children).forEach(child => {
        if (alwaysVisibleIds.has(child.id)) {
            child.classList.remove("hidden");
        } else {
            child.classList.toggle("hidden", !hasSelectedStock);
        }
    });
}

function syncTradeModeUI() {
    if (!tradeTypeSelect) return;
    const mode = tradeTypeSelect.value;
    if (oddShareCountGroup) {
        oddShareCountGroup.classList.toggle("hidden", mode !== "ODD");
    }
    const tradeRow = document.querySelector(".form-row-trade-invest");
    if (tradeRow) {
        tradeRow.classList.toggle("round-mode", mode === "ROUND");
    }
}

function renderMorphSignal(stock) {
    const color = stock.morph_breakout ? "morph-breakout" : (stock.morph_ok ? "morph-higher-low" : "morph-none");
    const label = stock.morph_breakout ? "底底高且破前高" : (stock.morph_ok ? "底底高" : "無");
    return `<div class="status-indicator" data-tooltip="${label}${stock.neckline ? `；頸線 ${stock.neckline}` : ""}"><span class="light-dot ${color}"></span></div>`;
}

function renderRValue(value) {
    if (value === null || value === undefined || value === "") return "";
    const number = Number(value);
    const color = number > 2 ? "#f43f5e" : (number >= 1 ? "#34d399" : "#94a3b8");
    return `<span style="color:${color};font-weight:700;">${number.toFixed(2)}R</span>`;
}

function renderBooleanSignal(value, shape = "dot") {
    if (value === null || value === undefined) return "";
    return `<div class="status-indicator"><span class="light-${shape} ${value ? "green" : "red"}"></span></div>`;
}

function renderKdSignal(stock) {
    if (stock.hourly_kd_ok === null || stock.hourly_kd_ok === undefined) return "";
    return `<div class="status-indicator"><span class="light-dot ${stock.hourly_kd_ok ? "green" : "red"}"></span>${stock.golden_cross_count ?? 0}次</div>`;
}

function setupRiskControlLocks() {
    const zone = document.getElementById("holdings-zone");
    const heading = zone?.querySelector(":scope > .holdings-zone-header h2");
    if (!zone || !heading) return;
    const unlocked = sessionStorage.getItem("holdingsZoneUnlocked") === "true";
    zone.classList.toggle("risk-locked", !unlocked);
    heading.setAttribute("data-tooltip", "點擊輸入密碼展開持股專區");
    heading.style.cursor = "pointer";
    heading.addEventListener("click", () => {
        if (!zone.classList.contains("risk-locked")) {
            zone.classList.add("risk-locked");
            sessionStorage.removeItem("holdingsZoneUnlocked");
            return;
        }
        const password = prompt("請輸入持股專區密碼：");
        if (password === null) return;
        if (password !== "193225") {
            showToast("密碼錯誤", "danger");
            return;
        }
        zone.classList.remove("risk-locked");
        sessionStorage.setItem("holdingsZoneUnlocked", "true");
        showToast("持股專區已展開；三張卡片已同步開啟", "success");
    });
}

function syncOddLotInputs(source = oddLotInputSource) {
    if (!selectedStock || tradeTypeSelect.value !== "ODD") return;

    const price = validPrice(currentPricePerShare || targetBuyPriceInput.value || selectedStock.current_price);
    if (price === null) return;

    oddLotInputSource = source;
    if (source === "shares") {
        const shares = Math.max(0, Math.floor(Number(oddShareCountInput.value) || 0));
        oddShareCountInput.value = shares;
        investmentAmountInput.value = shares > 0 ? Math.round(shares * price) : 0;
    } else {
        const amount = Math.max(0, Math.floor(Number(investmentAmountInput.value) || 0));
        investmentAmountInput.value = amount;
        oddShareCountInput.value = amount > 0 ? Math.floor(amount / price) : 0;
    }
}

function ensureMonitorToolbar() {
    [
        {cardId: "calc-monitors-card", buttonId: "btn-add-inventory", market: "TW"},
        {cardId: "us-monitors-card", buttonId: "btn-add-us-inventory", market: "US"}
    ].forEach(({cardId, buttonId, market}) => {
        const header = document.querySelector(`#${cardId} .panel-header`);
        if (!header || document.getElementById(buttonId)) return;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.id = buttonId;
        btn.className = "icon-btn btn-secondary";
        btn.innerHTML = `<i class="fa-solid fa-plus"></i> 手動庫存`;
        btn.addEventListener("click", () => handleAddManualInventory(market));
        header.appendChild(btn);
    });
}

async function saveMonitorOrder(sortedOrders) {
    const listsRes = await fetch(`${API_BASE}/lists`);
    const listsData = await listsRes.json();
    await fetch(`${API_BASE}/lists`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            stockList: listsData.stockList || [],
            monitorList: sortedOrders,
            trailingList: listsData.trailingList || []
        })
    });
}

function moveOrderById(orderId, direction) {
    const index = currentMonitorsData.findIndex(o => o.order_id === orderId);
    const target = index + direction;
    if (index < 0 || target < 0 || target >= currentMonitorsData.length) return;
    const next = [...currentMonitorsData];
    [next[index], next[target]] = [next[target], next[index]];
    currentMonitorsData = next;
    saveMonitorOrder(next).then(fetchAndRenderMonitors).catch(() => showToast("排序儲存失敗", "danger"));
}

async function handleAddManualInventory(market = "TW") {
    const isUS = market === "US";
    const codeInput = prompt(isUS ? "輸入美股庫存代號（例如 AAPL）" : "輸入庫存股代號");
    if (!codeInput) return;
    const code = isUS ? codeInput.trim().toUpperCase() : codeInput.trim();
    if (isUS && !/^[A-Z0-9][A-Z0-9.\-]{0,14}$/.test(code)) {
        showToast("美股代號格式不正確", "danger");
        return;
    }
    const price = parseFloat(prompt(isUS ? "輸入買入價（美元）" : "輸入買入價", "0") || "0");
    const quantity = parseInt(prompt("輸入股數", isUS ? "1" : "1000") || "0", 10);
    if (!code || !price || !quantity) {
        showToast("庫存資料不完整", "danger");
        return;
    }
    const stopLoss = parseFloat(prompt("輸入停損價", (price * 0.95).toFixed(2)) || "0");
    const stopProfit = parseFloat(prompt("輸入停利價", (price * 1.1).toFixed(2)) || "0");
    const lotType = isUS ? "ODD" : (quantity >= 1000 && quantity % 1000 === 0 ? "ROUND" : "ODD");
    const response = await fetch(`${API_BASE}/sinopac/order`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            code,
            action: "BUY",
            price,
            quantity,
            stop_loss_price: stopLoss || null,
            stop_profit_price: stopProfit || null,
            lot_type: lotType,
            dry_run: true,
            market
        })
    });
    if (response.ok) {
        showToast(isUS ? "已新增美股手動庫存" : "已新增手動庫存股", "success");
        fetchAndRenderMonitors();
    } else {
        const result = await response.json().catch(() => ({}));
        showToast(result.detail || "新增庫存失敗", "danger");
    }
}

// Mock Ordering DOM Elements
const sinopacOrderSection = document.getElementById("sinopac-order-section");
const orderPreviewPrice = document.getElementById("order-preview-price");
const orderPreviewShares = document.getElementById("order-preview-shares");
const orderPreviewStoploss = document.getElementById("order-preview-stoploss");
const orderPreviewStopprofit = document.getElementById("order-preview-stopprofit");
const btnSubmitOrder = document.getElementById("btn-submit-order");
const monitorsTableBody = document.getElementById("monitors-table-body");
const monitorCountLabel = document.getElementById("monitor-count-label");
const usMonitorsTableBody = document.getElementById("us-monitors-table-body");
const usMonitorCountLabel = document.getElementById("us-monitor-count-label");

// Initialize application
document.addEventListener("DOMContentLoaded", async () => {
    await initApiBase();
    const versionLabel = document.getElementById("version-label");
    if (versionLabel) {
        versionLabel.textContent = `版次：${APP_VERSION} (${APP_REVISION_DATE}|${APP_REVISION_TIME})`;
    }
    setCalculatorMode(false);
    setupRiskControlLocks();
    ensureMonitorToolbar();
    syncTradeModeUI();
    setupEventListeners();
    initUSFilterState();
    document.querySelectorAll(".entry-signal-info").forEach(icon => {
        icon.setAttribute("data-tooltip", "須同時符合三項：\n① 日線收盤價高於 MA20、MA60，且 MA20 高於 MA60。\n② 60 分 K 的 K、D 值皆低於 50。\n③ 近 12 個交易日的 60 分 K 低檔黃金交叉共 2～3 次。\n\n未買入：符合時顯示「可買入」；買入：符合時顯示「可加碼」。");
    });
    document.querySelectorAll(".morph-rule-info").forEach(icon => {
        icon.setAttribute("data-tooltip", "顏色：紅＝底底高且破前高；綠＝底底高；灰＝無。\n\n底底高：最近低點 > 前次低點。\n底底高且破前高：頸線取兩個低點之間的最高收盤價；最近兩個交易日內須由頸線下方向上突破，突破日成交量 ≥ 突破前 20 日均量的 1.2 倍，突破後收盤持續站穩頸線。");
    });
    await loadStocksFromStorage();
    
    // Read the saved tab and restore it
    const savedTab = localStorage.getItem("activeTab") || "tab-a";
    switchTab(savedTab, true);
    
    // Load the active tab's data first to ensure instant rendering
    if (savedTab === "tab-a") {
        await fetchAndAnalyzeStocks(false);
        // Load others in background
        fetchPotentialStocks();
    } else if (savedTab === "tab-b") {
        await fetchPotentialStocks();
        // Load others in background
        fetchAndAnalyzeStocks(false);
    } else if (savedTab === "tab-c") {
        await fetchAndAnalyzeUSStocks(false);
        // Load others in background
        fetchAndAnalyzeStocks(false);
        fetchPotentialStocks();
    }
    
    fetchAndRenderMonitors();
    restoreLastSelectedStock();
    updateTradingLightsAndLabels();
    startMarketHoursTimer();
    
    // Restore window scroll position after rendering completes
    setTimeout(() => {
        const savedScrollY = localStorage.getItem("windowScrollY");
        if (savedScrollY !== null) {
            window.scrollTo(0, parseFloat(savedScrollY));
        }
    }, 600);
    
    // Listen to window scroll events to persist position
    window.addEventListener("scroll", () => {
        localStorage.setItem("windowScrollY", window.scrollY);
    });
    
    // Initialize visitor stats and stock datalist
    updateVisitStats();
    fetchAndPopulateDatalist();
    fetchAndPopulateUsDatalist();
    setTimeout(pollUSScanStatus, 500);
    
    const visitorCounter = document.getElementById("visitor-counter");
    if (visitorCounter) {
        visitorCounter.addEventListener("click", async () => {
            const choice = prompt("請設定此裝置代表的位置：\n輸入 1：設定此裝置與IP為「家」\n輸入 2：設定此裝置與IP為「公司」\n輸入 3：設定此裝置與IP為「手機」");
            let locTag = "";
            if (choice === "1") locTag = "home";
            else if (choice === "2") locTag = "company";
            else if (choice === "3") locTag = "phone";
            else return;
            
            localStorage.setItem("visitor_loc", locTag);
            await updateVisitStats(locTag);
        });
    }
    
    // Poll monitor statuses & background scan status every 5 seconds
    setInterval(() => {
        fetchAndRenderMonitors();
        pollScanStatus();
        pollUSScanStatus();
    }, 5000);
});

async function updateVisitStats(locTag = null) {
    try {
        const tag = locTag || localStorage.getItem("visitor_loc") || "";
        const url = tag ? `${API_BASE.replace("/api", "")}/api/visit?loc=${tag}` : `${API_BASE.replace("/api", "")}/api/visit`;
        const r = await fetch(url);
        if (r.ok) {
            const res = await r.json();
            document.querySelector("#visit-home .count").textContent = res.stats.home;
            document.querySelector("#visit-company .count").textContent = res.stats.company;
            document.querySelector("#visit-phone .count").textContent = res.stats.phone;
            document.querySelector("#visit-other .count").textContent = res.stats.other;
            
            const elements = {
                home: document.getElementById("visit-home"),
                company: document.getElementById("visit-company"),
                phone: document.getElementById("visit-phone"),
                other: document.getElementById("visit-other")
            };
            Object.keys(elements).forEach(key => {
                if (elements[key]) {
                    if (key === res.determined_loc) {
                        elements[key].style.textDecoration = "underline";
                        elements[key].style.fontWeight = "bold";
                        elements[key].style.opacity = "1";
                    } else {
                        elements[key].style.textDecoration = "none";
                        elements[key].style.fontWeight = "normal";
                        elements[key].style.opacity = "0.75";
                    }
                }
            });
        }
    } catch (e) {
        console.error("Error updating visit stats:", e);
    }
}

async function fetchAndPopulateDatalist() {
    try {
        const r = await fetch(`${API_BASE.replace("/api", "")}/api/all_stocks`);
        if (r.ok) {
            allStocks = await r.json();
            const datalist = document.getElementById("all-stocks-list");
            if (datalist) {
                datalist.innerHTML = "";
                allStocks.forEach(s => {
                    const opt = document.createElement("option");
                    opt.value = s.code;
                    opt.textContent = `${s.code} ${s.name}`;
                    datalist.appendChild(opt);
                });
            }
        }
    } catch (e) {
        console.error("Error fetching all stocks list:", e);
    }
}


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

// Setup event listeners
function setupEventListeners() {
    // Tab switching
    tabABtn.addEventListener("click", () => switchTab("tab-a"));
    tabBBtn.addEventListener("click", () => switchTab("tab-b"));
    tabCBtn.addEventListener("click", () => switchTab("tab-c"));

    // Table A Actions
    if (refreshBtn) {
        refreshBtn.addEventListener("click", async () => {
            await fetchAndAnalyzeStocks(true);
            await Promise.all([
                fetchPotentialStocks(),
                fetchAndRenderMonitors()
            ]);
        });
    }
    addStockForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleAddStock();
    });
    const addWebBtn = document.getElementById("add-web-btn");
    if (addWebBtn) {
        addWebBtn.addEventListener("click", () => textFileInput.click());
    }
    if (textFileInput) {
        textFileInput.addEventListener("change", handleTextFileSelect);
    }
    addUSStockForm.addEventListener("submit", (e) => {
        e.preventDefault();
        handleAddUSStock();
    });
    const addUsWebBtn = document.getElementById("add-us-web-btn");
    if (addUsWebBtn) {
        addUsWebBtn.addEventListener("click", () => {
            const usFileInput = document.getElementById("us-text-file-input");
            if (usFileInput) usFileInput.click();
        });
    }
    const usFileInput = document.getElementById("us-text-file-input");
    if (usFileInput) {
        usFileInput.addEventListener("change", handleUSTextFileSelect);
    }

    const usStockCodeInput = document.getElementById("us-stock-code-input");
    if (usStockCodeInput) {
        usStockCodeInput.addEventListener("input", () => {
            let val = usStockCodeInput.value.trim();
            if (!val) return;
            
            const isTicker = /^[A-Za-z0-9.\-]{1,15}$/.test(val) && isNaN(val);
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
    }
    stockCodeInput.addEventListener("input", () => {
        let val = stockCodeInput.value.trim();
        if (!val) return;
        
        const isTaiwanCode = /^\d{4,6}[A-Za-z]?$/.test(val);
        if (!isTaiwanCode && isNaN(val)) {
            const foundStock = allStocks.find(s => s.name === val || s.name.includes(val) || val.includes(s.name));
            if (foundStock) {
                val = foundStock.code;
            }
        }
        
        if (isTaiwanCode) {
            val = val.toUpperCase();
            stockCodeInput.value = val;
            const found = currentStocksData.find(s => s.code === val)
                || potentialStocksData.find(s => s.code === val);
            if (found && validPrice(found.current_price) !== null) {
                selectStockRow(found, false);
            }
        }
    });

    // Refresh Popular stocks
    refreshPopularBtn.addEventListener("click", () => handleRefreshPopular());
    if (refreshUSBtn) {
        refreshUSBtn.addEventListener("click", () => fetchAndAnalyzeUSStocks(true));
    }
    const scanUsBtn = document.getElementById("scan-us-btn");
    if (scanUsBtn) {
        scanUsBtn.addEventListener("click", handleTriggerUSScan);
    }
    const usFilterBtn = document.getElementById("us-filter-btn");
    if (usFilterBtn) {
        usFilterBtn.addEventListener("click", toggleUSFilter);
    }
    // Tab B Actions
    scanBtn.addEventListener("click", handleTriggerScan);

    investmentAmountInput.addEventListener("input", () => {
        if (tradeTypeSelect.value === "ODD") {
            syncOddLotInputs("amount");
        }
        if (selectedStock) updateCalculations();
    });
    if (oddShareCountInput) {
        oddShareCountInput.addEventListener("input", () => {
            syncOddLotInputs("shares");
            if (selectedStock) updateCalculations();
        });
    }
    targetBuyPriceInput.addEventListener("input", () => {
        currentPricePerShare = parseFloat(targetBuyPriceInput.value) || (selectedStock ? selectedStock.current_price : 0);
        syncOddLotInputs();
        if (selectedStock) updateCalculations();
    });
    tradeTypeSelect.addEventListener("change", () => {
        const mode = tradeTypeSelect.value;
        const label = document.querySelector('label[for="investment-amount"]');
        const buyPricePrefix = document.getElementById("buy-price-prefix");
        const investmentPrefix = document.getElementById("investment-prefix");
        const quickButtons = document.querySelectorAll(".quick-amounts .btn-quick");
        const buyLabel = document.getElementById("buy-price-label");
        
        if (selectedStock && !currentPricePerShare) {
            currentPricePerShare = selectedStock.current_price;
        }
        
        if (mode === "ROUND") {
            label.textContent = "預計買入張數 (張)";
            if (buyPricePrefix) buyPricePrefix.textContent = "NT$";
            if (investmentPrefix) investmentPrefix.textContent = "張數";
            if (buyLabel) buyLabel.innerHTML = `設定買入價格 (台幣/股)<br><span style="font-size: 0.78em; color: var(--text-secondary); font-weight: normal;">(下方走勢可點擊套用單價)</span>`;
            targetBuyPriceInput.readOnly = false;
            
            investmentAmountInput.step = "1";
            investmentAmountInput.min = "1";
            if (parseFloat(investmentAmountInput.value) >= 100) {
                investmentAmountInput.value = "1";
            }
            targetBuyPriceInput.value = currentPricePerShare.toFixed(2);
            
            const values = [1, 3, 5, 10, 30];
            quickButtons.forEach((btn, idx) => {
                btn.textContent = `${values[idx]}張`;
                btn.dataset.val = values[idx].toString();
            });
        } else {
            label.textContent = "投入金額（台幣）";
            if (buyPricePrefix) buyPricePrefix.textContent = "NT$";
            if (investmentPrefix) investmentPrefix.textContent = "NT$";
            if (buyLabel) buyLabel.innerHTML = `設定買入價格 (台幣/股)<br><span style="font-size: 0.78em; color: var(--text-secondary); font-weight: normal;">(下方走勢可點擊套用單價)</span>`;
            targetBuyPriceInput.readOnly = false;
            
            investmentAmountInput.step = "1000";
            investmentAmountInput.min = "100";
            if (parseFloat(investmentAmountInput.value) < 100) {
                investmentAmountInput.value = "20000";
            }
            targetBuyPriceInput.value = currentPricePerShare.toFixed(2);
            oddLotInputSource = "amount";
            syncOddLotInputs("amount");
            
            const values = [10000, 30000, 50000, 100000, 300000];
            const labels = ["1萬", "3萬", "5萬", "10萬", "30萬"];
            quickButtons.forEach((btn, idx) => {
                btn.textContent = labels[idx];
                btn.dataset.val = values[idx].toString();
            });
        }
        syncTradeModeUI();
        if (selectedStock) updateCalculations();
    });
    stopLossPctInput.addEventListener("input", () => {
        if (selectedStock) updateCalculations();
    });

    quickAmountButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            const currentVal = parseFloat(investmentAmountInput.value) || 0;
            const btnVal = parseFloat(btn.dataset.val) || 0;
            investmentAmountInput.value = currentVal + btnVal;
            if (tradeTypeSelect.value === "ODD") {
                syncOddLotInputs("amount");
            }
            if (selectedStock) updateCalculations();
        });
    });

    const btnQuickReset = document.getElementById("btn-quick-reset");
    if (btnQuickReset) {
        btnQuickReset.addEventListener("click", () => {
            investmentAmountInput.value = "0";
            if (oddShareCountInput) oddShareCountInput.value = "0";
            oddLotInputSource = "amount";
            if (selectedStock) updateCalculations();
        });
    }

    // Suggested price cards click event listeners
    const suggestCards = document.querySelectorAll(".price-suggest-card");
    suggestCards.forEach(card => {
        card.addEventListener("click", () => {
            if (selectedStock && card.dataset.val) {
                currentPricePerShare = parseFloat(card.dataset.val);
                targetBuyPriceInput.value = currentPricePerShare.toFixed(2);
                syncOddLotInputs();
                updateCalculations();
                showToast(`已套用建議買入價: $${currentPricePerShare.toFixed(2)}`, "success");
            }
        });
    });

    // Submit Simulated Order
    if (btnSubmitOrder) {
        btnSubmitOrder.addEventListener("click", () => {
            handlePlaceOrder();
        });
    }

    // Responsive window resizing
    window.addEventListener("resize", () => {
        resizeAllCharts();
    });

    // Global mouseup handler to stop infinite loop on number inputs' spin buttons in Chrome/Edge
    window.addEventListener("mouseup", () => {
        const activeEl = document.activeElement;
        if (activeEl && activeEl.type === "number") {
            activeEl.disabled = true;
            setTimeout(() => {
                activeEl.disabled = false;
                activeEl.focus();
            }, 0);
        }
    });
}

function switchTab(tabId, forceRefresh = false) {
    if (activeTab === tabId && !forceRefresh) return;
    activeTab = tabId;
    localStorage.setItem("activeTab", tabId);
    
    tabABtn.classList.toggle("active", tabId === "tab-a");
    tabBBtn.classList.toggle("active", tabId === "tab-b");
    tabCBtn.classList.toggle("active", tabId === "tab-c");
    scannerSection.classList.toggle("hidden", tabId !== "tab-a");
    usSection.classList.toggle("hidden", tabId !== "tab-c");
    potentialSection.classList.toggle("hidden", tabId !== "tab-b");

    if (tabId === "tab-c") {
        if (usStocksData.length === 0) {
            fetchAndAnalyzeUSStocks(false);
        }
    } else if (tabId === "tab-b") {
        fetchPotentialStocks();
    }
    
    // Highlight selected stock in the new tab if it exists there
    if (selectedStock) {
        const activeTable = tabId === "tab-a"
            ? stockTableBody
            : (tabId === "tab-c" ? usStockTableBody : potentialTableBody);
        const rows = activeTable.querySelectorAll("tr");
        rows.forEach(r => r.classList.remove("selected"));
        const selectedRow = activeTable.querySelector(`tr[data-code="${selectedStock.code}"]`);
        if (selectedRow) selectedRow.classList.add("selected");
    }
}

function resizeAllCharts() {
    if (intradayChart) intradayChart.resize();
    if (prevIntradayChart) prevIntradayChart.resize();
    if (klineChart) klineChart.resize();
    if (kdChart) kdChart.resize();
    if (hourlyKlineChart) hourlyKlineChart.resize();
    if (institutionalChart) institutionalChart.resize();
    if (chipConcentrationChart) chipConcentrationChart.resize();
    if (majorHolderChart) majorHolderChart.resize();
}

// Toast Notifications System
function showToast(message, type = "info") {
    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;
    
    let iconClass = "fa-circle-info";
    if (type === "success") iconClass = "fa-circle-check";
    if (type === "danger") iconClass = "fa-circle-xmark";
    
    toast.innerHTML = `
        <i class="fa-solid ${iconClass} toast-icon"></i>
        <span>${message}</span>
    `;
    
    toastContainer.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 4000);
}

// Fetch and Analyze Tab A (Scanner) Stocks
async function fetchAndAnalyzeStocks(isManualRefresh = false, isSilent = false) {
    if (isManualRefresh) {
        showToast("開始更新股票數據並重新計算指標...", "info");
    }
    
    if (!isSilent) {
        stockTableBody.innerHTML = `
            <tr class="table-placeholder">
                <td colspan="7">
                    <div class="skeleton-loader">
                        <div class="spinner"></div>
                        <p>正在分析股票技術指標（MA、KD 交叉），請稍候...</p>
                    </div>
                </td>
            </tr>
        `;
    }

    try {
        const res = await fetch(`${API_BASE}/stocks/analyze${isManualRefresh ? "?force=true" : ""}`);
        if (!res.ok) throw new Error("Analysis failed");
        
        const data = await res.json();
        
        const popularStocks = data.filter(s => s.added_by === "popular" || !s.added_by);
        const userStocks = data.filter(s => s.added_by && s.added_by !== "popular");
        totalPopularCount = popularStocks.length;
        
        const filteredPopular = popularStocks.filter(s => s.error ? false : (s.r_value !== null && s.r_value !== undefined && Number(s.r_value) >= 1.0));
        const filtered = [...filteredPopular, ...userStocks];
        
        // Sort: system_a_signal -> active signals count -> r_value -> volume_lots
        filtered.sort((a, b) => {
            const sigA = a.system_a_signal ? 1 : 0;
            const sigB = b.system_a_signal ? 1 : 0;
            if (sigA !== sigB) return sigB - sigA;
            
            const countA = getActiveSignalsCount(a);
            const countB = getActiveSignalsCount(b);
            if (countA !== countB) return countB - countA;
            
            const rA = a.r_value || 0;
            const rB = b.r_value || 0;
            if (rA !== rB) return rB - rA;
            
            const volA = a.volume_lots || 0;
            const volB = b.volume_lots || 0;
            if (volB !== volA) return volB - volA;
            
            return a.code.localeCompare(b.code);
        });
        
        currentStocksData = filtered;
        renderStockTable(filtered);
        
        // Update popular stocks update time
        const popularUpdateTimeEl = document.getElementById("popular-update-time");
        if (popularUpdateTimeEl) {
            popularUpdateTimeEl.innerText = `更新時間: ${new Date().toLocaleString()}`;
        }
        
        if (isManualRefresh) {
            showToast("熱門股追蹤指標更新完畢！", "success");
        }
        
        // Refresh calculations for the currently selected stock
        if (selectedStock) {
            const updated = data.find(s => s.code === selectedStock.code);
            if (updated) {
                if (isSilent) {
                    selectedStock.current_price = updated.current_price;
                    selectedStock.price_change = updated.price_change;
                    selectedStock.price_change_percent = updated.price_change_percent;
                    currentPricePerShare = updated.current_price;
                    updateCalcStockPrice(updated.current_price, selectedStock.reference_price, selectedStock.code, selectedStock.limit_up);
                    updateCalculations();
                } else {
                    selectStockRow(updated, false);
                }
            }
        } else {
            // Restore from localStorage on initial load
            const savedCode = localStorage.getItem("selectedStockCode");
            if (savedCode) {
                const savedStock = data.find(s => s.code === savedCode);
                if (savedStock) {
                    selectStockRow(savedStock, false);
                }
            }
        }
        
    } catch (e) {
        console.error(e);
        showToast("分析股票指標時發生錯誤。", "danger");
        renderTableError("獲取分析結果失敗，請稍後再試。");
    }
}

function updateUSStatusLabel() {
    const scanUsStatusLabel = document.getElementById("scan-us-status-label");
    if (!scanUsStatusLabel) return;
    
    let displayedCount = 0;
    const lastUpdatedStr = usScanLastUpdated ? `<br>最後更新: ${usScanLastUpdated}` : '';
    
    if (usStocksData && usStocksData.length > 0) {
        const usManualCount = usStocksData.filter(s => s.added_by === "manual" || s.added_by === "web" || s.added_by === "text").length;
        if (enableUSFilter) {
            const filtered = usStocksData.filter(stock => {
                if (stock.error) return false;
                const cond1 = stock.volume_lots !== null && stock.volume_lots !== undefined && Number(stock.volume_lots) >= 500;
                const cond3 = stock.daily_trend_ok === true;
                const cond4 = stock.morph_ok === true || stock.morph_breakout === true;
                const cond5 = stock.r_value !== null && stock.r_value !== undefined && Number(stock.r_value) >= 1.0;
                return cond1 && cond3 && cond4 && cond5;
            });
            displayedCount = filtered.length;
            scanUsStatusLabel.innerHTML = `已載入最新緩存 (篩選出 ${displayedCount} 檔 / 掃描 ${usScanTotal} 檔 + 自選 ${usManualCount} 檔)${lastUpdatedStr}`;
        } else {
            displayedCount = usStocksData.length;
            scanUsStatusLabel.innerHTML = `已載入最新緩存 (追蹤 ${displayedCount} 檔 / 掃描 ${usScanTotal} 檔 + 自選 ${usManualCount} 檔)${lastUpdatedStr}`;
        }
    } else {
        scanUsStatusLabel.innerHTML = `已載入最新緩存 (美股資料載入中... / 掃描 ${usScanTotal} 檔)${lastUpdatedStr}`;
    }
    
    const usCriteriaSpans = document.getElementById("us-criteria-spans");
    if (usCriteriaSpans) {
        if (enableUSFilter) {
            usCriteriaSpans.innerHTML = `
                <span style="background:rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); padding:2px 8px; border-radius:99px; color: #a5b4fc;">① 成交量 &ge; 500,000 股 (500k)</span>
                <span style="background:rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); padding:2px 8px; border-radius:99px; color: #a5b4fc;">② 日線收盤價 &gt; MA20 &amp; MA60 (趨勢向上)</span>
                <span style="background:rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); padding:2px 8px; border-radius:99px; color: #a5b4fc;">③ 底底高型態</span>
                <span style="background:rgba(99,102,241,0.15); border: 1px solid rgba(99,102,241,0.3); padding:2px 8px; border-radius:99px; color: #a5b4fc;">④ 預期風報比 R值 &ge; 1.0</span>
            `;
        } else {
            usCriteriaSpans.innerHTML = `
                <span style="background:rgba(255,255,255,0.06); padding:2px 8px; border-radius:99px; color: var(--text-secondary);">無 (顯示全部追蹤個股)</span>
            `;
        }
    }
}

function toggleUSFilter() {
    enableUSFilter = !enableUSFilter;
    sessionStorage.setItem("enableUSFilter", enableUSFilter ? "true" : "false");
    
    const filterBtn = document.getElementById("us-filter-btn");
    if (filterBtn) {
        if (enableUSFilter) {
            filterBtn.classList.remove("btn-secondary");
            filterBtn.classList.add("btn-primary");
            filterBtn.innerHTML = `<i class="fa-solid fa-filter"></i> 已加強篩選`;
        } else {
            filterBtn.classList.remove("btn-primary");
            filterBtn.classList.add("btn-secondary");
            filterBtn.innerHTML = `<i class="fa-solid fa-filter"></i> 加強篩選`;
        }
    }
    
    updateUSStatusLabel();
    if (usStocksData && usStocksData.length > 0) {
        renderUSStockTable(usStocksData);
    }
}

function initUSFilterState() {
    const savedState = sessionStorage.getItem("enableUSFilter");
    enableUSFilter = savedState === "true";
    
    const filterBtn = document.getElementById("us-filter-btn");
    if (filterBtn) {
        if (enableUSFilter) {
            filterBtn.classList.remove("btn-secondary");
            filterBtn.classList.add("btn-primary");
            filterBtn.innerHTML = `<i class="fa-solid fa-filter"></i> 已加強篩選`;
        } else {
            filterBtn.classList.remove("btn-primary");
            filterBtn.classList.add("btn-secondary");
            filterBtn.innerHTML = `<i class="fa-solid fa-filter"></i> 加強篩選`;
        }
    }
    
    updateUSStatusLabel();
}

async function fetchAndAnalyzeUSStocks(isManualRefresh = false, isSilent = false) {
    if (!usStockTableBody) return;
    if (isManualRefresh) showToast("開始更新美股技術指標...", "info");
    if (!isSilent) {
        usStockTableBody.innerHTML = `
            <tr class="table-placeholder"><td colspan="12">
                <div class="skeleton-loader"><div class="spinner"></div><p>正在分析美股技術指標，請稍候...</p></div>
            </td></tr>`;
    }
    try {
        const response = await fetch(`${API_BASE}/us-stocks/analyze${isManualRefresh ? "?force=true" : ""}`);
        if (!response.ok) throw new Error("US analysis failed");
        const data = await response.json();
        data.sort((a, b) => {
            if (Boolean(a.system_a_signal) !== Boolean(b.system_a_signal)) return b.system_a_signal ? 1 : -1;
            const signalDiff = getActiveSignalsCount(b) - getActiveSignalsCount(a);
            if (signalDiff !== 0) return signalDiff;
            const rDiff = Number(b.r_value || 0) - Number(a.r_value || 0);
            if (rDiff !== 0) return rDiff;
            const volumeDiff = Number(b.volume_lots || 0) - Number(a.volume_lots || 0);
            if (volumeDiff !== 0) return volumeDiff;
            return String(a.code).localeCompare(String(b.code));
        });
        usStocksData = data;
        renderUSStockTable(data);
        // Removed redundant local labels
        updateUSStatusLabel();
        if (selectedStock) {
            const updated = data.find(s => s.code === selectedStock.code);
            if (updated) {
                if (isSilent) {
                    selectedStock.current_price = updated.current_price;
                    selectedStock.price_change = updated.price_change;
                    selectedStock.price_change_percent = updated.price_change_percent;
                    currentPricePerShare = updated.current_price;
                    updateCalcStockPrice(updated.current_price, selectedStock.reference_price, selectedStock.code, selectedStock.limit_up);
                    updateCalculations();
                } else {
                    selectStockRow(updated, false);
                }
            }
        }
        if (isManualRefresh) showToast("美股技術指標更新完成", "success");
    } catch (error) {
        console.error(error);
        usStockTableBody.innerHTML = `<tr><td colspan="12" class="table-error-cell">美股資料載入失敗，請稍後重試。</td></tr>`;
        if (isManualRefresh) showToast("美股資料更新失敗", "danger");
    }
}

function renderUSStockTable(stocks) {
    let displayStocks = stocks;
    if (enableUSFilter) {
        displayStocks = stocks.filter(stock => {
            if (stock.error) return false;
            const cond1 = stock.volume_lots !== null && stock.volume_lots !== undefined && Number(stock.volume_lots) >= 500;
            const cond3 = stock.daily_trend_ok === true;
            const cond4 = stock.morph_ok === true || stock.morph_breakout === true;
            const cond5 = stock.r_value !== null && stock.r_value !== undefined && Number(stock.r_value) >= 1.0;
            return cond1 && cond3 && cond4 && cond5;
        });
    }

    // Removed redundant local labels

    if (!displayStocks.length) {
        usStockTableBody.innerHTML = enableUSFilter
            ? `<tr><td colspan="12" class="table-error-cell" style="text-align: center; padding: 3rem; color: var(--text-muted);"><i class="fa-solid fa-filter" style="font-size: 2rem; margin-bottom: 0.5rem; display: block; opacity: 0.5;"></i>目前沒有符合加強篩選條件（收盤>MA20/60、底底高、R>=1.0）的美股個股。</td></tr>`
            : `<tr><td colspan="12" class="table-error-cell">目前沒有可顯示的美股資料。</td></tr>`;
        return;
    }
    usStockTableBody.innerHTML = "";
    displayStocks.forEach(stock => {
        const row = document.createElement("tr");
        row.dataset.code = stock.code;
        if (selectedStock && selectedStock.code === stock.code) row.classList.add("selected");
        row.addEventListener("click", () => selectStockRow(stock, true));
        if (stock.error) {
            row.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td>${escapeHtmlText(stock.name || stock.code)}${formatGroupTagsHTML(stock)}</td>
                <td colspan="9" class="table-error-cell">${stock.error}</td>
                <td class="actions-col"><button class="delete-btn delete-us-stock-btn" data-code="${stock.code}" title="刪除美股"><i class="fa-regular fa-trash-can"></i></button></td>`;
        } else {
            const trend = renderBooleanSignal(stock.daily_trend_ok);
            const kd = renderKdSignal(stock);
            const signal = stock.insufficient_history ? "" : renderBooleanSignal(stock.system_a_signal, "rect");
            const morph = renderMorphSignal(stock);
            const lights = renderStrategyLights(stock.signals);
            const rValue = stock.r_value;
            const tooltip = escapeHtmlAttribute(`中文名稱: ${stock.name_zh || stock.name || stock.code}\n英文名稱: ${stock.name || stock.code}\n主要業務: ${stock.business_zh || stock.industry || "尚未取得"}`);
            const manualBadge = stock.added_by === "manual"
                ? `<span class="added-by-badge manual" data-tooltip="手動加入"><i class="fa-solid fa-hand-pointer"></i></span>`
                : (stock.added_by === "web" ? `<span class="added-by-badge web" data-tooltip="網頁新增"><i class="fa-solid fa-globe"></i></span>` : "");
            const priceCell = formatPriceCell(stock.current_price, stock.reference_price, stock.code, stock.limit_up);
            const changeCell = formatChangeCellWithLimit(stock.price_change, stock.price_change_percent, stock.current_price, stock.reference_price, stock.code, stock.limit_up);
            row.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name" data-tooltip="${tooltip}">${escapeHtmlText(stock.name || stock.code)}</span>${manualBadge}${formatGroupTagsHTML(stock)}</td>
                ${priceCell}
                ${changeCell}
                <td><span class="stock-code">${Number((stock.volume_lots || 0) * 1000).toLocaleString()}</span></td>
                <td>${trend}</td><td>${kd}</td><td>${signal}</td><td>${morph}</td><td>${lights}</td>
                <td>${renderRValue(rValue)}</td>
                <td class="actions-col"><button class="delete-btn delete-us-stock-btn" data-code="${stock.code}" title="刪除美股"><i class="fa-regular fa-trash-can"></i></button></td>`;
        }
        row.querySelector(".delete-us-stock-btn")?.addEventListener("click", event => {
            event.stopPropagation();
            handleDeleteUSStock(stock.code, stock.name || stock.code);
        });
        usStockTableBody.appendChild(row);
    });
}

async function handleDeleteUSStock(code, name) {
    if (!confirm(`確認要取消追蹤 ${name} (${code}) 嗎？`)) return;
    try {
        const response = await fetch(`${API_BASE}/us-stocks/${encodeURIComponent(code)}`, {method: "DELETE"});
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "刪除失敗");
        if (selectedStock?.code === code) {
            selectedStock = null;
            localStorage.removeItem("lastSelectedStock");
            setCalculatorMode(false);
        }
        showToast(`已取消追蹤 ${name} (${code})`, "success");
        await fetchAndAnalyzeUSStocks(false);
    } catch (error) {
        showToast(error.message || "刪除美股失敗", "danger");
    }
}

async function handleAddUSStock() {
    let code = usStockCodeInput.value.trim();
    if (!code) return;
    const foundStock = allUsStocks.find(s => s.name.toLowerCase() === code.toLowerCase() || s.code.toLowerCase() === code.toLowerCase() || s.name.toLowerCase().includes(code.toLowerCase()));
    if (foundStock) {
        code = foundStock.code;
    }
    code = code.toUpperCase();
    if (!code) return;
    addUSBtn.disabled = true;
    addUSBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 新增中...`;
    try {
        const response = await fetch(`${API_BASE}/us-stocks`, {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({code, added_by: "manual"})
        });
        const result = await response.json();
        if (!response.ok) throw new Error(result.detail || "新增失敗");
        usStockCodeInput.value = "";
        showToast(`已手動新增 ${result.name} (${result.code})`, "success");
        await fetchAndAnalyzeUSStocks(false);
        const added = usStocksData.find(stock => stock.code === result.code);
        if (added) selectStockRow(added, true);
    } catch (error) {
        showToast(error.message || "無法新增此美股", "danger");
    } finally {
        addUSBtn.disabled = false;
        addUSBtn.innerHTML = `<i class="fa-solid fa-plus"></i> 手動新增`;
    }
}

async function handleTextFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(evt) {
        const text = evt.target.result;
        e.target.value = "";
        
        const addWebBtn = document.getElementById("add-web-btn");
        const originalHtml = addWebBtn ? addWebBtn.innerHTML : "";
        if (addWebBtn) {
            addWebBtn.disabled = true;
            addWebBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 匯入中...`;
        }
        
        try {
            const response = await fetch(`${API_BASE}/stocks/import-text`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
            const resData = await response.json();
            
            if (response.ok) {
                alert(`檔案共找到 ${resData.total_found} 個個股\n重複 ${resData.duplicates} 個\n成功加入 ${resData.added} 個！`);
                showToast(`成功從文字檔匯入 ${resData.added} 個新股！`, "success");
                await fetchAndAnalyzeStocks(false);
                await saveStocksToStorage();
            } else {
                showToast(resData.detail || "檔案加入失敗", "danger");
            }
        } catch (err) {
            showToast("伺服器連線失敗，請稍後再試。", "danger");
        } finally {
            if (addWebBtn) {
                addWebBtn.disabled = false;
                addWebBtn.innerHTML = originalHtml;
            }
        }
    };
    reader.readAsText(file);
}

async function handleUSTextFileSelect(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async function(evt) {
        const text = evt.target.result;
        e.target.value = "";
        
        const addUsWebBtn = document.getElementById("add-us-web-btn");
        const originalHtml = addUsWebBtn ? addUsWebBtn.innerHTML : "";
        if (addUsWebBtn) {
            addUsWebBtn.disabled = true;
            addUsWebBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 匯入中...`;
        }
        
        try {
            const response = await fetch(`${API_BASE}/us-stocks/import-text`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ text: text })
            });
            const resData = await response.json();
            
            if (response.ok) {
                alert(`檔案共找到 ${resData.total_found} 個個股\n重複 ${resData.duplicates} 個\n成功加入 ${resData.added} 個！`);
                showToast(`成功從文字檔匯入 ${resData.added} 個美股！`, "success");
                await fetchAndAnalyzeUSStocks(false);
            } else {
                showToast(resData.detail || "檔案加入失敗", "danger");
            }
        } catch (err) {
            showToast("伺服器連線失敗，請稍後再試。", "danger");
        } finally {
            if (addUsWebBtn) {
                addUsWebBtn.disabled = false;
                addUsWebBtn.innerHTML = originalHtml;
            }
        }
    };
    reader.readAsText(file);
}

let usRefreshInProgress = false;

async function handleRefreshUSPopular(silent = false) {
    if (usRefreshInProgress) return;
    usRefreshInProgress = true;
    refreshUSPopularBtn.disabled = true;
    if (refreshUSBtn) refreshUSBtn.disabled = true;
    refreshUSPopularBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 正在重刷...`;
    if (!silent) showToast("正在重刷 Yahoo 熱門與指標美股...", "info");
    try {
        const response = await fetch(`${API_BASE}/us-stocks/refresh-popular`, {method: "POST"});
        const result = await response.json();
        if (!response.ok || result.success === false) throw new Error(result.message || "refresh failed");
        if (!silent) {
            showToast(`已更新 ${result.indicator_count || 0} 檔指標與 ${result.popular_count || 0} 檔熱門美股`, "success");
        }
        await fetchAndAnalyzeUSStocks(false);
    } catch (error) {
        console.error(error);
        if (!silent) showToast("Yahoo 美股重刷失敗，保留原清單", "danger");
    } finally {
        usRefreshInProgress = false;
        refreshUSPopularBtn.disabled = false;
        if (refreshUSBtn) refreshUSBtn.disabled = false;
        refreshUSPopularBtn.innerHTML = `<i class="fa-solid fa-fire"></i> 重刷 Yahoo 熱門`;
    }
}

// Render Tab A Table
function isTaiwanETF(code) {
    if (!code) return false;
    const c = String(code).trim();
    return c.startsWith("00");
}

function calculateTaiwanLimitUp(referencePrice, isEtf) {
    if (!referencePrice || referencePrice <= 0) return null;
    const rawLimitUp = referencePrice * 1.10;
    
    let tickSize = 0.01;
    if (isEtf) {
        if (rawLimitUp < 50) {
            tickSize = 0.01;
        } else if (rawLimitUp < 100) {
            tickSize = 0.05;
        } else if (rawLimitUp < 500) {
            tickSize = 0.1;
        } else if (rawLimitUp < 1000) {
            tickSize = 0.5;
        } else {
            tickSize = 1.0;
        }
    } else {
        if (rawLimitUp < 10) {
            tickSize = 0.01;
        } else if (rawLimitUp < 50) {
            tickSize = 0.05;
        } else if (rawLimitUp < 100) {
            tickSize = 0.1;
        } else if (rawLimitUp < 500) {
            tickSize = 0.5;
        } else if (rawLimitUp < 1000) {
            tickSize = 1.0;
        } else {
            tickSize = 5.0;
        }
    }
    
    const epsilon = 1e-9;
    const ticks = Math.floor((rawLimitUp + epsilon) / tickSize);
    const limitUp = parseFloat((ticks * tickSize).toFixed(2));
    return limitUp;
}

function getPriceStyleAndClass(price, referencePrice, code, officialLimitUp = null) {
    if (price === undefined || price === null || price <= 0) {
        return { className: "", style: "" };
    }
    const p = parseFloat(price);
    const r = referencePrice ? parseFloat(referencePrice) : null;
    
    if (!r || p === r) {
        return { className: "", style: "" };
    }
    
    const isUS = code && !/^\d/.test(String(code).trim());
    
    if (!isUS) {
        let limitUp = officialLimitUp ? parseFloat(officialLimitUp) : null;
        if (!limitUp) {
            const isEtf = isTaiwanETF(code);
            limitUp = calculateTaiwanLimitUp(r, isEtf);
        }
        if (limitUp && p >= limitUp) {
            return {
                className: "limit-up-badge",
                style: "background-color: var(--color-danger) !important; color: #ffffff !important; font-weight: bold !important; padding: 2px 6px; border-radius: 4px; display: inline-block; text-shadow: none;"
            };
        }
    }
    
    if (p > r) {
        return {
            className: "up-red-text",
            style: "color: var(--color-danger) !important; font-weight: bold !important;"
        };
    } else {
        return {
            className: "down-green-text",
            style: "color: var(--color-success) !important; font-weight: bold !important;"
        };
    }
}

function formatPriceCell(price, referencePrice, code, officialLimitUp = null) {
    const p = parseFloat(price);
    const formatted = formatPrice(p);
    const { className, style } = getPriceStyleAndClass(price, referencePrice, code, officialLimitUp);
    if (style) {
        return `<td><span class="${className}" style="${style}">${formatted}</span></td>`;
    }
    return `<td><span class="stock-code">${formatted}</span></td>`;
}

function formatChangeCellWithLimit(change, percent, price, referencePrice, code, officialLimitUp = null) {
    if (change === undefined || change === null || percent === undefined || percent === null) {
        return `<td><span class="stock-code flat-gray">-</span></td>`;
    }
    const valChange = parseFloat(change);
    const valPercent = parseFloat(percent);
    
    if (valChange > 0) {
        return `<td class="up-red">+${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(+${valPercent.toFixed(2)}%)</span></td>`;
    } else if (valChange < 0) {
        return `<td class="down-green">${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(${valPercent.toFixed(2)}%)</span></td>`;
    } else {
        return `<td class="flat-gray">0.00<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(0.00%)</span></td>`;
    }
}

function applyPriceStyling(element, price, referencePrice, code, officialLimitUp = null) {
    if (!element) return;
    
    element.className = "price-val"; 
    element.style.backgroundColor = "";
    element.style.color = "";
    element.style.padding = "";
    element.style.borderRadius = "";
    element.style.fontWeight = "";
    element.style.display = "";
    
    const { className, style } = getPriceStyleAndClass(price, referencePrice, code, officialLimitUp);
    if (className === "limit-up-badge") {
        element.style.backgroundColor = "var(--color-danger)";
        element.style.color = "#ffffff";
        element.style.fontWeight = "bold";
        element.style.padding = "2px 8px";
        element.style.borderRadius = "4px";
        element.style.display = "inline-block";
    } else if (className === "up-red-text") {
        element.style.color = "var(--color-danger)";
        element.style.fontWeight = "bold";
    } else if (className === "down-green-text") {
        element.style.color = "var(--color-success)";
        element.style.fontWeight = "bold";
    }
}

function updateCalcStockPrice(price, referencePrice, code, officialLimitUp = null) {
    calcStockPrice.textContent = formatPrice(price);
    applyPriceStyling(calcStockPrice, price, referencePrice, code, officialLimitUp);
}

function formatChangeCell(change, percent) {
    if (change === undefined || change === null || percent === undefined || percent === null) {
        return `<td><span class="stock-code flat-gray">-</span></td>`;
    }
    const valChange = parseFloat(change);
    const valPercent = parseFloat(percent);
    if (valChange > 0) {
        return `<td class="up-red">+${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(+${valPercent.toFixed(2)}%)</span></td>`;
    } else if (valChange < 0) {
        return `<td class="down-green">${valChange.toFixed(2)}<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(${valPercent.toFixed(2)}%)</span></td>`;
    } else {
        return `<td class="flat-gray">0.00<br><span style="font-size: 0.68rem; font-weight: bold !important; opacity: 0.95; display: inline-block; margin-top: 2px;">(0.00%)</span></td>`;
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

function renderStockTable(stocks) {
    // Update the count label in the header
    const popularCountLabel = document.getElementById("popular-count-label");
    if (popularCountLabel) {
        if (stocks.length > 0) {
            const manualCount = stocks.filter(s => s.added_by && s.added_by !== "popular").length;
            const filterCount = stocks.filter(s => s.added_by === "popular" || !s.added_by).length;
            const displayPopularTotal = Math.max(totalPopularCount, filterCount);
            popularCountLabel.textContent = `篩選 ${filterCount} 檔 + 自選 ${manualCount} 檔 / 掃描熱門股 ${displayPopularTotal} 檔`;
        } else {
            popularCountLabel.textContent = "";
        }
    }

    if (stocks.length === 0) {
        stockTableBody.innerHTML = `
            <tr>
                <td colspan="12" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                    <i class="fa-solid fa-list-check" style="font-size: 2rem; margin-bottom: 1rem; display: block;"></i>
                    <p>追蹤清單中目前沒有股票。請在上方輸入股票代號或上傳文字檔新增。</p>
                </td>
            </tr>
        `;
        return;
    }

    stockTableBody.innerHTML = "";
    
    stocks.forEach(stock => {
        const tr = document.createElement("tr");
        tr.dataset.code = stock.code;
        
        if (selectedStock && selectedStock.code === stock.code) {
            tr.className = "selected";
        }
        
        tr.addEventListener("click", () => selectStockRow(stock, true));
        
        if (stock.error) {
            tr.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name">${escapeHtmlText(stock.name)}${formatGroupTagsHTML(stock)}</span></td>
                <td colspan="9" style="color: var(--color-danger); font-size: 0.85rem;">
                    <i class="fa-solid fa-triangle-exclamation"></i> ${stock.error}
                </td>
                <td class="actions-col">
                    <button class="delete-btn" data-code="${stock.code}" title="刪除股票">
                        <i class="fa-regular fa-trash-can"></i>
                    </button>
                </td>
            `;
        } else {
            const trendHtml = renderBooleanSignal(stock.daily_trend_ok);
            
        const crossesCount = stock.golden_cross_count !== undefined && stock.golden_cross_count !== null ? stock.golden_cross_count : 0;
        const kdHtml = renderKdSignal(stock);
            
        const morphHtml = renderMorphSignal(stock);
            
        const signalHtml = stock.insufficient_history ? "" : renderBooleanSignal(stock.system_a_signal, "rect");
                
            const lightsHtml = renderStrategyLights(stock.signals);
            const rHtml = renderRValue(stock.r_value);
                
            const priceCell = formatPriceCell(stock.current_price, stock.reference_price, stock.code, stock.limit_up);
            const changeCell = formatChangeCellWithLimit(stock.price_change, stock.price_change_percent, stock.current_price, stock.reference_price, stock.code, stock.limit_up);
            tr.innerHTML = `
                <td><span class="stock-code">${stock.code}</span></td>
                <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
                ${priceCell}
                ${changeCell}
                <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>
                <td>${trendHtml}</td>
                <td>${kdHtml}</td>
                <td>${signalHtml}</td>
                <td>${morphHtml}</td>
                <td>${lightsHtml}</td>
                <td>${rHtml}</td>
                <td class="actions-col">
                    <button class="delete-btn" data-code="${stock.code}" title="刪除股票">
                        <i class="fa-regular fa-trash-can"></i>
                    </button>
                </td>
            `;
        }
        
        const delBtn = tr.querySelector(".delete-btn");
        delBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            handleDeleteStock(stock.code, stock.name);
        });
        
        stockTableBody.appendChild(tr);
    });
}

function renderTableError(msg) {
    stockTableBody.innerHTML = `
        <tr>
            <td colspan="7" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                <i class="fa-solid fa-triangle-exclamation" style="font-size: 2rem; color: var(--color-danger); margin-bottom: 1rem; display: block;"></i>
                <p>${msg}</p>
                <button onclick="location.reload()" class="icon-btn btn-primary" style="margin: 1rem auto 0 auto;">
                    <i class="fa-solid fa-arrows-rotate"></i> 重新嘗試
                </button>
            </td>
        </tr>
    `;
}

// Fetch Tab B (Potential) Stocks
async function fetchPotentialStocks() {
    try {
        const res = await fetch(`${API_BASE}/stocks/potential`);
        if (!res.ok) throw new Error();
        const data = await res.json();
        
        // Filter out stocks with r_value < 1.0 (低風報比)
        const filteredB = data.filter(s => (s.r_value || 0) >= 1.0);
        
        // Sort: system_a_signal -> active signals count -> r_value -> volume_lots
        filteredB.sort((a, b) => {
            const sigA = a.system_a_signal ? 1 : 0;
            const sigB = b.system_a_signal ? 1 : 0;
            if (sigA !== sigB) return sigB - sigA;
            
            const countA = getActiveSignalsCount(a);
            const countB = getActiveSignalsCount(b);
            if (countA !== countB) return countB - countA;
            
            const rA = a.r_value || 0;
            const rB = b.r_value || 0;
            if (rA !== rB) return rB - rA;
            
            const volA = a.volume_lots || 0;
            const volB = b.volume_lots || 0;
            if (volB !== volA) return volB - volA;
            
            return a.code.localeCompare(b.code);
        });
        
        potentialStocksData = filteredB;
        renderPotentialTable(filteredB);
        
        // Restore from localStorage if not already selected by Tab A
        if (!selectedStock) {
            const savedCode = localStorage.getItem("selectedStockCode");
            if (savedCode) {
                const savedStock = filteredB.find(s => s.code === savedCode);
                if (savedStock) {
                    selectStockRow(savedStock, false);
                }
            }
        }
    } catch (e) {
        potentialTableBody.innerHTML = `
            <tr>
                <td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                    載入潛力股清單失敗，請點選重新掃描。
                </td>
            </tr>
        `;
    }
}

// Render Tab B Table
function renderPotentialTable(stocks) {
    if (stocks.length === 0) {
        potentialTableBody.innerHTML = `
            <tr>
                <td colspan="12" style="text-align: center; padding: 3rem; color: var(--text-muted);">
                    <i class="fa-solid fa-folder-open" style="font-size: 2rem; margin-bottom: 1rem; display: block; color: rgba(255,255,255,0.15);"></i>
                    <p>目前沒有符合三道濾網（流動性、均線、底底高）的底部潛力股。<br>可以點選右上角重新掃描全市場。</p>
                </td>
            </tr>
        `;
        return;
    }

    potentialTableBody.innerHTML = "";
    
    stocks.forEach(stock => {
        const tr = document.createElement("tr");
        tr.dataset.code = stock.code;
        
        if (selectedStock && selectedStock.code === stock.code) {
            tr.className = "selected";
        }
        
        tr.addEventListener("click", () => selectStockRow(stock, true));
        
        const trendHtml = renderBooleanSignal(stock.daily_trend_ok);
        const kdHtml = renderKdSignal(stock);
        const morphHtml = renderMorphSignal(stock);
        const signalHtml = renderBooleanSignal(stock.system_a_signal, "rect");
            
        const lightsHtml = renderStrategyLights(stock.signals);
        const rHtmlB = renderRValue(stock.r_value);
        
        const isTracked = currentStocksData.some(s => s.code === stock.code);
        let actionBtnHtml = "";
        if (isTracked) {
            actionBtnHtml = `<span class="added-badge" data-tooltip="已加入追蹤" style="cursor:help; color:var(--color-success); font-size:1.05rem; display:inline-block; padding:4px;"><i class="fa-solid fa-circle-check"></i></span>`;
        } else {
            actionBtnHtml = `<button class="add-to-track-btn" data-code="${stock.code}" title="加入追蹤"><i class="fa-solid fa-plus"></i></button>`;
        }
        
        const priceCellB = formatPriceCell(stock.current_price, stock.reference_price, stock.code, stock.limit_up);
        const changeCellB = formatChangeCellWithLimit(stock.price_change, stock.price_change_percent, stock.current_price, stock.reference_price, stock.code, stock.limit_up);
        tr.innerHTML = `
            <td><span class="stock-code">${stock.code}</span></td>
            <td><span class="stock-name">${formatStockNameHTML(stock, stock.code, stock.industry || "")}</span></td>
            ${priceCellB}
            ${changeCellB}
            <td><span class="stock-code">${(stock.volume_lots || 0).toLocaleString()} 張</span></td>
            <td>${trendHtml}</td>
            <td>${kdHtml}</td>
            <td>${signalHtml}</td>
            <td>${morphHtml}</td>
            <td>${lightsHtml}</td>
            <td>${rHtmlB}</td>
            <td class="actions-col">${actionBtnHtml}</td>
        `;
        
        const addTrackBtn = tr.querySelector(".add-to-track-btn");
        if (addTrackBtn) {
            addTrackBtn.addEventListener("click", (e) => {
                e.stopPropagation();
                handleAddTrackFromTable(stock.code);
            });
        }
        
        potentialTableBody.appendChild(tr);
    });
}

// Handle Add Track From Table click
async function handleAddTrackFromTable(code) {
    try {
        const response = await fetch(`${API_BASE}/stocks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code, added_by: "scan" })
        });
        const resData = await response.json();
        
        if (response.ok) {
            showToast(`成功將 ${resData.name} (${resData.code}) 新增至追蹤清單！`, "success");
            await fetchAndAnalyzeStocks(false);
            renderPotentialTable(potentialStocksData);
            await saveStocksToStorage();
        } else {
            showToast(resData.detail || "無法新增此股票", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗，請稍後再試。", "danger");
    }
}

// Trigger All-Market Scan
async function handleTriggerScan() {
    try {
        const response = await fetch(`${API_BASE}/stocks/scan`, { method: "POST" });
        const data = await response.json();
        if (response.ok) {
            showToast(data.message, "success");
            pollScanStatus();
        } else {
            showToast(data.message, "danger");
        }
    } catch (e) {
        showToast("啟動全市場掃描失敗", "danger");
    }
}

// Poll background scanner status
async function pollScanStatus() {
    try {
        const res = await fetch(`${API_BASE}/stocks/scan/status`);
        if (!res.ok) return;
        const status = await res.json();
        
        if (status.active) {
            scanBtn.disabled = true;
            scanBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 掃描中...`;
            scanStatusLabel.textContent = `掃描進度: ${status.progress} / ${status.total} 檔 (篩選出 ${potentialStocksData.length} 檔)`;
            
            scanProgressBox.classList.remove("hidden");
            const pct = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
            scanProgressText.textContent = `${status.progress} / ${status.total} 檔 (${pct}%)`;
            scanProgressBar.style.width = `${pct}%`;
        } else {
            const wasActive = !scanProgressBox.classList.contains("hidden");
            scanBtn.disabled = false;
            scanBtn.innerHTML = `<i class="fa-solid fa-radar"></i> 重新掃描全市場`;
            const lastUpdatedStr = status.last_updated ? `<br>最後更新: ${status.last_updated}` : '';
            const totalScanned = status.total || 0;
            scanStatusLabel.innerHTML = `已載入最新緩存 (篩選出 ${potentialStocksData.length} 檔 / 掃描 ${totalScanned} 檔)${lastUpdatedStr}`;
            scanProgressBox.classList.add("hidden");
            
            if (wasActive) {
                showToast("全市場掃描已完成！已刷新潛力股清單。", "success");
                fetchPotentialStocks();
            }
        }
    } catch (e) {
        console.error(e);
    }
}


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
            scanUsStatusLabel.textContent = `掃描進度: ${status.progress} / ${status.total} 檔 (篩選出 ${status.potentials_count || 0} 檔)`;
            
            scanUsProgressBox.classList.remove("hidden");
            const pct = status.total > 0 ? Math.round((status.progress / status.total) * 100) : 0;
            scanUsProgressText.textContent = `${status.progress} / ${status.total} 檔 (${pct}%)`;
            scanUsProgressBar.style.width = `${pct}%`;
        } else {
            const wasActive = !scanUsProgressBox.classList.contains("hidden");
            scanUsBtn.disabled = false;
            scanUsBtn.innerHTML = `<i class="fa-solid fa-radar"></i> 掃描S&P 500/Nasdaq 100`;
            usScanTotal = status.total || 0;
            usScanLastUpdated = status.last_updated || "";
            usScanPotentialsCount = status.potentials_count || 0;
            updateUSStatusLabel();
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

// Refresh popular stocks
async function handleRefreshPopular() {
    refreshPopularBtn.disabled = true;
    refreshPopularBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 正在重刷...`;
    showToast("正在重新爬取 Yahoo 熱門股排行榜...", "info");
    
    try {
        const response = await fetch(`${API_BASE}/stocks/refresh_popular`, { method: "POST" });
        if (response.ok) {
            showToast("成功更新熱門排行！已重新加載列表。", "success");
            fetchAndAnalyzeStocks(false);
        } else {
            showToast("重刷熱門股失敗", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗", "danger");
    } finally {
        refreshPopularBtn.disabled = false;
        refreshPopularBtn.innerHTML = `<i class="fa-solid fa-fire"></i> 重刷熱門`;
    }
}

// Import stock codes from text file
function handleImportTextFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
        const text = event.target.result;
        const matches = text.match(/\b\d{4,6}\b/g) || [];
        const uniqueCodes = [...new Set(matches)];
        
        if (uniqueCodes.length === 0) {
            showToast("文字檔內未找到有效的台股代號（必須為4至6位數字）。", "danger");
            return;
        }
        
        showToast(`讀取到 ${uniqueCodes.length} 檔股票代碼，開始驗證並匯入...`, "info");
        
        try {
            const response = await fetch(`${API_BASE}/stocks/bulk_add`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ codes: uniqueCodes })
            });
            const data = await response.json();
            
            if (response.ok) {
                showToast(`成功匯入 ${data.total_added} 檔新股至追蹤列表！`, "success");
                await fetchAndAnalyzeStocks(false);
                await saveStocksToStorage();
            } else {
                showToast("批量匯入失敗", "danger");
            }
        } catch (err) {
            showToast("與伺服器通訊錯誤，無法批次匯入", "danger");
        }
    };
    reader.readAsText(file);
    textFileInput.value = "";
}

// Select a Stock to Calculate & Draw Charts
function selectStockRow(stock, shouldResetTab = true) {
    if (stock.error) {
        showToast(`無法計算 ${stock.name}，因為數據載入失敗。`, "danger");
        return;
    }
    
    let selectedPrice = validPrice(stock.current_price);
    if (selectedPrice === null) {
        selectedPrice = validPrice(stock.reference_price);
    }

    selectedStock = { ...stock, current_price: selectedPrice };
    localStorage.setItem("selectedStockCode", stock.code);
    localStorage.setItem("lastSelectedStock", JSON.stringify(selectedStock));
    
    const aRows = stockTableBody.querySelectorAll("tr");
    aRows.forEach(r => r.classList.remove("selected"));
    const usRows = usStockTableBody.querySelectorAll("tr");
    usRows.forEach(r => r.classList.remove("selected"));
    const bRows = potentialTableBody.querySelectorAll("tr");
    bRows.forEach(r => r.classList.remove("selected"));
    
    const activeTable = activeTab === "tab-a"
        ? stockTableBody
        : (activeTab === "tab-c" ? usStockTableBody : potentialTableBody);
    const selectedRow = activeTable.querySelector(`tr[data-code="${stock.code}"]`);
    if (selectedRow) selectedRow.classList.add("selected");
    [monitorsTableBody, usMonitorsTableBody].forEach(tableBody => {
        if (!tableBody) return;
        tableBody.querySelectorAll("tr").forEach(row => {
            row.classList.toggle("selected", row.dataset.code === stock.code);
        });
    });
    
    setCalculatorMode(true);
    
    setTimeout(resizeAllCharts, 100);
    
    calcStockCode.textContent = stock.code;
    // Show stock name with industry tooltip in header
    calcStockName.innerHTML = formatStockNameHTML(stock, stock.code, stock.industry || "");
    calcStockSymbol.textContent = stock.symbol;
    updateCalcStockPrice(selectedPrice, stock.reference_price, stock.code, stock.limit_up);
    updateTradingLightsAndLabels();
    
    const dispBadge = document.getElementById("disposition-badge");
    if (dispBadge) {
        dispBadge.classList.add("hidden");
        dispBadge.removeAttribute("data-tooltip");
        dispBadge.textContent = "處置股";
    }
    
    currentPricePerShare = selectedPrice || 0.0;
    targetBuyPriceInput.value = currentPricePerShare > 0 ? currentPricePerShare.toFixed(2) : "";
    syncOddLotInputs();
    targetBuyPriceInput.readOnly = false;
    const buyLabel = document.getElementById("buy-price-label");
    const isUSStock = stock.market === "US";
    if (buyLabel) buyLabel.innerHTML = `設定買入價格 (${isUSStock ? "美元" : "台幣"})<br><span style="font-size: 0.78em; color: var(--text-secondary); font-weight: normal;">(下方走勢可點擊套用單價)</span>`;
    const buyPrefix = document.getElementById("buy-price-prefix");
    if (buyPrefix) buyPrefix.textContent = isUSStock ? "US$" : "NT$";
    const investmentLabel = document.querySelector('label[for="investment-amount"]');
    const investmentPrefix = document.getElementById("investment-prefix");
    if (investmentLabel) investmentLabel.textContent = isUSStock ? "投入金額（美元）" : "投入金額（台幣）";
    if (investmentPrefix) investmentPrefix.textContent = isUSStock ? "US$" : "NT$";
    const tradeTypeGroup = tradeTypeSelect?.closest(".calc-input-group");
    const quickAmounts = document.getElementById("quick-amounts");
    if (tradeTypeGroup) tradeTypeGroup.classList.toggle("hidden", isUSStock);
    if (quickAmounts) quickAmounts.classList.toggle("hidden", isUSStock);
    if (sinopacOrderSection) sinopacOrderSection.classList.remove("hidden");
    if (isUSStock && tradeTypeSelect) {
        tradeTypeSelect.value = "ODD";
        investmentAmountInput.value = "100";
        oddLotInputSource = "amount";
        syncTradeModeUI();
        syncOddLotInputs("amount");
    } else if (tradeTypeSelect) {
        if (Number(investmentAmountInput.value) === 100) investmentAmountInput.value = "20000";
        syncTradeModeUI();
    }
    
    if (stock.system_a_signal) {
        calcSystemStatus.className = "system-status-indicator signal-true";
        calcSignalBadge.textContent = "符合進場";
        calcSignalReason.innerHTML = `<i class="fa-solid fa-circle-check"></i> 日線多頭排列且 60分K 低檔黃金交叉 ${stock.golden_cross_count} 次，符合進場標準！${stock.is_intraday ? "（盤中採前一交易日完成資料）" : ""}`;
    } else {
        calcSystemStatus.className = "system-status-indicator signal-false";
        calcSignalBadge.textContent = "未符合";
        
        let reasons = [];
        if (!stock.daily_trend_ok) reasons.push("日線趨勢非多頭排列");
        if (!stock.kd_under_50) reasons.push("60分K之 KD 指標未在 50 以下");
        if (!stock.hourly_kd_ok) reasons.push(`60分K低階黃金交叉為 ${stock.golden_cross_count} 次`);
        
        calcSignalReason.innerHTML = `<i class="fa-solid fa-circle-xmark"></i> ${reasons.join("；")} (計算以12個交易日為基準)`;
    }
    
    updateCalculations();
    fetchAndDrawCharts(stock.code);
    retriggerCardAnimations();
}

let marketHoursTimer = null;
let lastChartRefreshTime = 0;

function updateTradingLightsAndLabels() {
    const twOpen = isMarketOpen("TW");
    const usOpen = isMarketOpen("US");
    
    // 1. Update lights
    const twLights = document.querySelectorAll(".tw-market-light");
    twLights.forEach(light => {
        if (twOpen) {
            light.classList.add("open");
        } else {
            light.classList.remove("open");
        }
    });
    
    const usLights = document.querySelectorAll(".us-market-light");
    usLights.forEach(light => {
        if (usOpen) {
            light.classList.add("open");
        } else {
            light.classList.remove("open");
        }
    });
    
    // 2. Update price column headers & card labels
    const tabAPriceHeader = document.getElementById("tab-a-price-header");
    if (tabAPriceHeader) {
        tabAPriceHeader.textContent = twOpen ? "即時價" : "收盤價";
    }
    
    const tabBPriceHeader = document.getElementById("tab-b-price-header");
    if (tabBPriceHeader) {
        tabBPriceHeader.textContent = twOpen ? "即時價" : "收盤價";
    }
    
    const tabCPriceHeader = document.getElementById("tab-c-price-header");
    if (tabCPriceHeader) {
        tabCPriceHeader.textContent = usOpen ? "即時價" : "收盤價";
    }
    
    const monitorPriceHeader = document.getElementById("monitor-price-header");
    if (monitorPriceHeader) {
        monitorPriceHeader.textContent = twOpen ? "即時價" : "收盤價";
    }
    
    const usMonitorPriceHeader = document.getElementById("us-monitor-price-header");
    if (usMonitorPriceHeader) {
        usMonitorPriceHeader.textContent = usOpen ? "即時價" : "收盤價";
    }
    
    // Detail Card "當前股價" / "即時價" / "收盤價"
    const calcPriceLabel = document.getElementById("calc-price-label");
    if (calcPriceLabel && selectedStock) {
        const isSelectedUS = !/^\d/.test(selectedStock.code);
        const isOpen = isSelectedUS ? usOpen : twOpen;
        calcPriceLabel.textContent = isOpen ? "即時價" : "收盤價";
    }
    
    // Daily close label in the intraday chart overlay
    const refCloseLabel = document.getElementById("ref-close-label");
    if (refCloseLabel && selectedStock) {
        const isSelectedUS = !/^\d/.test(selectedStock.code);
        const isOpen = isSelectedUS ? usOpen : twOpen;
        refCloseLabel.textContent = isOpen ? "即時" : "收盤";
    }
}

function startMarketHoursTimer() {
    if (marketHoursTimer) clearInterval(marketHoursTimer);
    marketHoursTimer = setInterval(async () => {
        const twOpen = isMarketOpen("TW");
        const usOpen = isMarketOpen("US");
        const now = Date.now();
        
        // 1. Update TW stock lists if TW market is open
        if (twOpen) {
            try {
                await fetchAndAnalyzeStocks(false, true);
                await fetchPotentialStocks();
            } catch (e) {
                console.error("Auto refresh TW lists failed:", e);
            }
        }
        
        // 2. Update US stock list if US market is open
        if (usOpen) {
            try {
                await fetchAndAnalyzeUSStocks(false, true);
            } catch (e) {
                console.error("Auto refresh US lists failed:", e);
            }
        }
        
        // 3. Update the currently selected stock's charts/data
        if (selectedStock) {
            const isSelUS = !/^\d/.test(selectedStock.code);
            const isSelOpen = isSelUS ? usOpen : twOpen;
            if (isSelOpen) {
                // Throttle chart reloading to once every 60 seconds to prevent rate limits and performance issues
                if (now - lastChartRefreshTime >= 60000) {
                    try {
                        await fetchAndDrawCharts(selectedStock.code, true);
                    } catch (e) {
                        console.error("Auto refresh charts failed:", e);
                    }
                    lastChartRefreshTime = now;
                } else {
                    // Update just the calculations and details price if list data has changed
                    const found = isSelUS 
                        ? usStocksData.find(s => String(s.code).trim() === String(selectedStock.code).trim())
                        : (currentStocksData.find(s => String(s.code).trim() === String(selectedStock.code).trim()) || 
                           potentialStocksData.find(s => String(s.code).trim() === String(selectedStock.code).trim()));
                    if (found && found.current_price !== undefined && found.current_price !== null) {
                        selectedStock.current_price = found.current_price;
                        currentPricePerShare = found.current_price;
                        updateCalcStockPrice(found.current_price, selectedStock.reference_price, selectedStock.code, selectedStock.limit_up);
                        updateCalculations();
                    }
                }
            }
        }
        
        // 4. Update the tab indicator lights and text labels
        updateTradingLightsAndLabels();
    }, 15000);
}

function isMarketOpen(market = "TW") {
    const zone = market === "US" ? "America/New_York" : "Asia/Taipei";
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: zone, weekday: "short", hour: "2-digit", minute: "2-digit",
        hourCycle: "h23"
    }).formatToParts(new Date()).reduce((result, part) => {
        result[part.type] = part.value;
        return result;
    }, {});
    if (["Sat", "Sun"].includes(parts.weekday)) return false;
    const minutes = Number(parts.hour) * 60 + Number(parts.minute);
    return market === "US"
        ? minutes >= 570 && minutes < 960
        : minutes >= 540 && minutes < 810;
}

function isChartRefreshWindow(market = "TW") {
    const zone = market === "US" ? "America/New_York" : "Asia/Taipei";
    const parts = new Intl.DateTimeFormat("en-US", {
        timeZone: zone, weekday: "short", hour: "2-digit", minute: "2-digit",
        hourCycle: "h23"
    }).formatToParts(new Date()).reduce((result, part) => {
        result[part.type] = part.value;
        return result;
    }, {});
    if (["Sat", "Sun"].includes(parts.weekday)) return false;
    const minutes = Number(parts.hour) * 60 + Number(parts.minute);
    return market === "US"
        ? minutes >= 570 && minutes < 1020
        : minutes >= 540 && minutes < 870;
}

function restoreLastSelectedStock() {
    try {
        const saved = JSON.parse(localStorage.getItem("lastSelectedStock") || "null");
        if (!saved?.code) return;
        selectStockRow(saved, false);
    } catch (error) {
        console.warn("Unable to restore the last selected stock", error);
    }
}

// Run Calculations on Input
function updateCalculations() {
    if (!selectedStock) return;
    
    const price = currentPricePerShare || selectedStock.current_price || 0.0;
    if (price <= 0) return;
    
    const investment = parseFloat(investmentAmountInput.value) || 0;
    const oddShareCount = parseInt(oddShareCountInput ? oddShareCountInput.value : "0", 10) || 0;
    const tradeType = tradeTypeSelect.value;
    const stopLossPct = parseFloat(stopLossPctInput.value) || 5;
    
    const isCustomPrice = (price !== selectedStock.current_price);
    const rLabelText = document.getElementById("r-ratio-label-text");
    if (rLabelText) {
        rLabelText.textContent = isCustomPrice ? "掛單價風報比 (R值)" : "預期風報比 (R值)";
    }
    
    const stopLoss = Math.round(price * (1 - stopLossPct / 100) * 100) / 100;
    const stopProfit = selectedStock.prev_high || (price * 1.1);
    
    let shares = 0;
    let sharesText = "";
    if (tradeType === "ROUND") {
        const lots = Math.floor(investment);
        shares = lots * 1000;
        sharesText = `${lots.toLocaleString()} 張 <span style="font-size:0.75rem; color:var(--text-muted);">(${shares.toLocaleString()} 股)</span>`;
    } else {
        shares = oddShareCount > 0 ? oddShareCount : Math.floor(investment / price);
        sharesText = `${shares.toLocaleString()} <span>股</span>`;
    }
    
    const actualCost = shares * price;
    const maxLoss = (price - stopLoss) * shares;
    const maxProfit = (stopProfit - price) * shares;
    
    let rValue = 0;
    const roundedLoss = Math.round(maxLoss);
    const roundedProfit = Math.round(maxProfit);
    if (shares > 0 && roundedLoss > 0) {
        rValue = roundedProfit / roundedLoss;
    }
    
    resShares.innerHTML = sharesText;
    const currency = selectedStock?.market === "US" ? "US$" : "NT$";
    resActualCost.textContent = `實質花費: ${currency} ${Math.round(actualCost).toLocaleString()}`;
    
    stopLossLabel.textContent = `嚴格 ${stopLossPct}% 停損價格`;
    const pricePrefix = selectedStock?.market === "US" ? "US$" : "$";
    resStopLoss.textContent = `${pricePrefix}${stopLoss.toFixed(2)}`;
    resRiskLoss.textContent = `預期最大虧損: ${currency} -${Math.round(maxLoss).toLocaleString()}`;
    
    resStopProfit.textContent = `${pricePrefix}${stopProfit.toFixed(2)}`;
    resProfitGain.textContent = `預估潛在獲利: ${currency} +${Math.round(maxProfit).toLocaleString()}`;
    
    resRRatio.textContent = rValue.toFixed(2);
    rRatioCard.classList.remove("r-badge-green", "r-badge-yellow", "r-badge-red");
    
    if (rValue >= 2.0) {
        resRComment.textContent = "高風報比 (≥ 2.0，值得進場)";
        resRComment.className = "card-sub text-success";
        rRatioCard.classList.add("r-badge-green");
    } else if (rValue >= 1.0) {
        resRComment.textContent = "中風報比 (1.0 ~ 2.0，審慎評估)";
        resRComment.className = "card-sub text-success";
        rRatioCard.classList.add("r-badge-yellow");
    } else {
        resRComment.textContent = "低風報比 (< 1.0，不符賺賠比)";
        resRComment.className = "card-sub text-danger";
        rRatioCard.classList.add("r-badge-red");
    }

    if (orderPreviewPrice) orderPreviewPrice.textContent = `${pricePrefix}${price.toFixed(2)}`;
    if (orderPreviewShares) {
        if (tradeType === "ROUND") {
            const lots = shares / 1000;
            orderPreviewShares.textContent = `${lots} 張 (${shares.toLocaleString()} 股)`;
        } else {
            orderPreviewShares.textContent = `${shares.toLocaleString()} 股`;
        }
    }
    if (orderPreviewStoploss) orderPreviewStoploss.textContent = `${pricePrefix}${stopLoss.toFixed(2)}`;
    if (orderPreviewStopprofit) orderPreviewStopprofit.textContent = `${pricePrefix}${stopProfit.toFixed(2)}`;
}

// Fetch Chart Data and Initialize ECharts
async function fetchAndDrawCharts(code, isSilent = false) {
    if (!isSilent) {
        if (intradayChart) { intradayChart.dispose(); intradayChart = null; }
        if (prevIntradayChart) { prevIntradayChart.dispose(); prevIntradayChart = null; }
        if (klineChart) { klineChart.dispose(); klineChart = null; }
        if (kdChart) { kdChart.dispose(); kdChart = null; }
        if (hourlyKlineChart) { hourlyKlineChart.dispose(); hourlyKlineChart = null; }
        if (institutionalChart) { institutionalChart.dispose(); institutionalChart = null; }
        if (chipConcentrationChart) { chipConcentrationChart.dispose(); chipConcentrationChart = null; }
        if (majorHolderChart) { majorHolderChart.dispose(); majorHolderChart = null; }

        updateChartCardVisibility(null, selectedStock?.market === "US", true);
        document.getElementById("intraday-chart").innerHTML = `<div class="spinner" style="margin: 6rem auto;"></div>`;
        document.getElementById("prev-intraday-chart").innerHTML = `<div class="spinner" style="margin: 6rem auto;"></div>`;
        document.getElementById("kline-chart").innerHTML = `<div class="spinner" style="margin: 8rem auto;"></div>`;
        document.getElementById("kd-chart").innerHTML = `<div class="spinner" style="margin: 3rem auto;"></div>`;
        document.getElementById("hourly-kline-chart").innerHTML = `<div class="spinner" style="margin: 3rem auto;"></div>`;
        document.getElementById("institutional-chart").innerHTML = `<div class="spinner" style="margin: 7rem auto;"></div>`;
        document.getElementById("chip-concentration-chart").innerHTML = `<div class="spinner" style="margin: 7rem auto;"></div>`;
        document.getElementById("major-holder-chart").innerHTML = `<div class="spinner" style="margin: 7rem auto;"></div>`;
    } else {
        if (intradayChart) { intradayChart.dispose(); intradayChart = null; }
        if (prevIntradayChart) { prevIntradayChart.dispose(); prevIntradayChart = null; }
    }

    try {
        const market = selectedStock?.market === "US" ? "US" : "TW";
        const cacheKey = `${market}:${String(code).toUpperCase()}`;
        let response;
        let data;
        response = await fetch(`${API_BASE}/stocks/${code}/chart-data${isMarketOpen(market) ? "?force=true" : ""}`);
        if (!response.ok) throw new Error("Chart data fetch failed");
        data = await response.json();
        chartDataCache.set(cacheKey, {data, updatedAt: Date.now()});
        const isUSChart = data.market === "US" || selectedStock?.market === "US";
        const latestKline = data.kline?.[data.kline.length - 1];
        const chartPrice = validPrice(getLatestIntradayPrice(data.intraday))
            || validPrice(latestKline?.close);
        const currentVal = validPrice(selectedStock?.current_price);
        if ((currentVal === null || currentVal <= 0) && chartPrice !== null && selectedStock?.code === code) {
            selectedStock.current_price = chartPrice;
            currentPricePerShare = chartPrice;
            updateCalcStockPrice(chartPrice, selectedStock?.reference_price, selectedStock?.code, selectedStock?.limit_up);
            if (targetBuyPriceInput) {
                targetBuyPriceInput.value = chartPrice.toFixed(2);
            }
            localStorage.setItem("lastSelectedStock", JSON.stringify(selectedStock));
            updateCalculations();
        }
        updateChartCardVisibility(data, isUSChart, false);
        
        const suggestCardHeader = document.querySelector("#calc-suggested-card .panel-header h2");
        if (suggestCardHeader) {
            const titleText = data.is_intraday ? "今日走勢與掛單價設定" : "最近交易日走勢與掛單價設定";
            suggestCardHeader.innerHTML = `<i class="fa-solid fa-tags"></i> ${titleText} <span id="intraday-date-label" style="font-size: 0.8rem; color: var(--text-muted); font-weight: normal; margin-left: 8px;"></span>`;
        }
        const consLabel = document.getElementById("suggest-conservative-label");
        if (consLabel) {
            consLabel.textContent = data.is_intraday ? "保守 (今日低點)" : "保守 (最近交易日低點)";
        }
        
        const intradayDateLabel = document.getElementById("intraday-date-label");
        const prevIntradayDateLabel = document.getElementById("prev-intraday-date-label");
        if (intradayDateLabel) {
            intradayDateLabel.textContent = formatIntradayDateLabel(data.intraday_date, data.intraday_session, isUSChart);
        }
        if (prevIntradayDateLabel) {
            prevIntradayDateLabel.textContent = formatIntradayDateLabel(data.prev_intraday_date, data.prev_intraday_session, isUSChart);
        }
        
        const dispBadge = document.getElementById("disposition-badge");
        if (dispBadge) {
            if (data.disposition) {
                dispBadge.classList.remove("hidden");
                const period = data.disposition.period || "";
                const measures = data.disposition.measures || "";
                const reason = data.disposition.reason || "";
                dispBadge.setAttribute("data-tooltip", `【處置】\n原因：${reason}\n期間：${period}\n措施：${measures}`);
                dispBadge.textContent = "處置股";
            } else {
                dispBadge.classList.add("hidden");
            }
        }
        
        // Dynamically add stock name, badge, and tooltips to card headers on the right
        const formattedNameHTML = formatStockNameHTML(selectedStock, selectedStock.code, selectedStock.industry || "");
        
        const klineCardHeader = document.querySelector("#calc-kline-card .panel-header h2");
        if (klineCardHeader) {
            klineCardHeader.innerHTML = `<i class="fa-solid fa-chart-candlestick"></i> ${formattedNameHTML} ‧ 日K線與成交量 (近60日, 疊加 SMA5、SMA20、SMA60)`;
        }
        
        const instCardHeader = document.querySelector("#calc-institutional-card .panel-header h2");
        if (instCardHeader) {
            instCardHeader.innerHTML = `<i class="fa-solid fa-users-viewfinder"></i> ${formattedNameHTML} ‧ 三大法人淨買賣超統計 (近60日, 單位:張)`;
        }
        
        const chipCardHeader = document.querySelector("#calc-chip-concentration-card .panel-header h2");
        if (chipCardHeader) {
            chipCardHeader.innerHTML = `<i class="fa-solid fa-chart-area"></i> ${formattedNameHTML} ‧ 籌碼集中度(近60日,%)`;
        }
        
        const paramsCardHeader = document.querySelector("#calc-params-card .panel-header h2");
        if (paramsCardHeader) {
            paramsCardHeader.innerHTML = `<i class="fa-solid fa-calculator"></i> ${formattedNameHTML} ‧ 倉位與風控計算`;
        }
        
        if (data.kline && data.kline.length > 0) {
            // Today's Bar
            const latestBar = data.kline[data.kline.length - 1];
            
            const open = validPrice(latestBar.open);
            const high = validPrice(latestBar.high);
            const low = validPrice(latestBar.low);
            const livePrice = data.is_intraday ? validPrice(getLatestIntradayPrice(data.intraday)) : null;
            const close = livePrice || validPrice(latestBar.close);

            if ([open, high, low, close].some(value => value === null)) {
                throw new Error("最新 K 線價格資料不完整");
            }
            
            refOpen.textContent = `$${open.toFixed(2)}`;
            refHigh.textContent = `$${high.toFixed(2)}`;
            refLow.textContent = `$${low.toFixed(2)}`;
            refClose.textContent = data.is_intraday ? `$${close.toFixed(2)} (當前)` : `$${close.toFixed(2)}`;
            
            const aggressive = (open + close) / 2;
            const moderate = (low + close) / 2;
            const conservative = low;
            
            suggestPriceAggressive.textContent = `$${aggressive.toFixed(2)}`;
            suggestPriceModerate.textContent = `$${moderate.toFixed(2)}`;
            suggestPriceConservative.textContent = `$${conservative.toFixed(2)}`;
            
            document.getElementById("suggest-card-aggressive").dataset.val = aggressive.toFixed(2);
            document.getElementById("suggest-card-moderate").dataset.val = moderate.toFixed(2);
            document.getElementById("suggest-card-conservative").dataset.val = conservative.toFixed(2);
            
            // Previous Trading Day's Bar (if available)
            if (data.kline.length >= 2) {
                const prevBar = data.kline[data.kline.length - 2];
                const pOpen = validPrice(prevBar.open);
                const pHigh = validPrice(prevBar.high);
                const pLow = validPrice(prevBar.low);
                const pClose = validPrice(prevBar.close);
                
                refPrevOpen.textContent = formatPrice(pOpen);
                refPrevHigh.textContent = formatPrice(pHigh);
                refPrevLow.textContent = formatPrice(pLow);
                refPrevClose.textContent = formatPrice(pClose);
                
                const previousPricesValid = [pOpen, pHigh, pLow, pClose].every(value => value !== null);
                if (!previousPricesValid) {
                    return;
                }

                const pAggressive = (pOpen + pClose) / 2;
                const pModerate = (pLow + pClose) / 2;
                const pConservative = pLow;
                
                suggestPrevPriceAggressive.textContent = `$${pAggressive.toFixed(2)}`;
                suggestPrevPriceModerate.textContent = `$${pModerate.toFixed(2)}`;
                suggestPrevPriceConservative.textContent = `$${pConservative.toFixed(2)}`;
                
                document.getElementById("suggest-prev-card-aggressive").dataset.val = pAggressive.toFixed(2);
                document.getElementById("suggest-prev-card-moderate").dataset.val = pModerate.toFixed(2);
                document.getElementById("suggest-prev-card-conservative").dataset.val = pConservative.toFixed(2);
            }
        }
        
        let yesterdayClose = null;
        let prevYesterdayClose = null;
        if (data.kline && data.kline.length >= 2) {
            yesterdayClose = data.kline[data.kline.length - 2].close;
            if (data.kline.length >= 3) {
                prevYesterdayClose = data.kline[data.kline.length - 3].close;
            } else {
                prevYesterdayClose = data.kline[data.kline.length - 2].open;
            }
        }
        
        renderIntradayChart(data.intraday, yesterdayClose, data.intraday_session);
        renderPrevIntradayChart(data.prev_intraday, prevYesterdayClose, data.prev_intraday_session);
        if (!isSilent) {
            renderKlineChart(data.kline);
            renderKdChart(data.kd);
            renderHourlyKlineChart(data.kd);
            renderInstitutionalChart(data.institutional, data.is_intraday, data.intraday_date);
            renderChipConcentrationChart(data.institutional, data.is_intraday, data.intraday_date);
            renderMajorHolderChart(data.major_holders);
        }
        
    } catch (e) {
        console.error(e);
        showToast("載入個股圖表數據失敗", "danger");
        const errorMsg = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;"><i class="fa-solid fa-circle-exclamation" style="font-size: 1.5rem; color: var(--color-danger); margin-bottom: 0.5rem; display:block;"></i>載入圖表失敗</div>`;
        document.getElementById("intraday-chart").innerHTML = errorMsg;
        document.getElementById("prev-intraday-chart").innerHTML = errorMsg;
        document.getElementById("kline-chart").innerHTML = errorMsg;
        document.getElementById("kd-chart").innerHTML = errorMsg;
        document.getElementById("hourly-kline-chart").innerHTML = errorMsg;
        document.getElementById("institutional-chart").innerHTML = errorMsg;
        document.getElementById("chip-concentration-chart").innerHTML = errorMsg;
        document.getElementById("major-holder-chart").innerHTML = "";
    }
}

function formatIntradayDateLabel(date, session, isUS) {
    if (!date) return "";
    if (!isUS || !session) return `(${date})`;
    const season = session.is_dst ? "美東夏令" : "美東冬令";
    return `(${date}｜台灣時間 ${session.start}～${session.end}｜${season})`;
}

function updateChartCardVisibility(data, isUS, isLoading = false) {
    const toggle = (id, visible) => {
        const card = document.getElementById(id);
        if (card) card.classList.toggle("hidden", !visible);
    };
    const kdContainer = document.getElementById("kd-chart-container");

    if (!isUS) {
        ["calc-suggested-card", "calc-prev-suggested-card", "calc-kline-card",
            "calc-institutional-card", "calc-chip-concentration-card"].forEach(id => toggle(id, true));
        if (kdContainer) kdContainer.classList.remove("hidden");
        return;
    }

    if (isLoading || !data) {
        toggle("calc-suggested-card", true);
        toggle("calc-prev-suggested-card", true);
        toggle("calc-kline-card", true);
        toggle("calc-institutional-card", false);
        toggle("calc-chip-concentration-card", false);
        return;
    }

    toggle("calc-suggested-card", Boolean(data.intraday?.length && data.kline?.length));
    toggle("calc-prev-suggested-card", Boolean(data.prev_intraday?.length && data.kline?.length >= 2));
    toggle("calc-kline-card", Boolean(data.kline?.length));
    toggle("calc-institutional-card", Boolean(data.institutional?.length));
    toggle("calc-chip-concentration-card", Boolean(data.institutional?.length || data.major_holders?.length));
    if (kdContainer) kdContainer.classList.toggle("hidden", !data.kd?.length);
}

function generateIntradayTimeline(session = null) {
    if (session?.start && session?.end) {
        const toMinutes = value => {
            const [hour, minute] = value.split(":").map(Number);
            return hour * 60 + minute;
        };
        const start = toMinutes(session.start);
        let end = toMinutes(session.end);
        if (end <= start) end += 24 * 60;
        const timeline = [];
        for (let minute = start; minute <= end; minute++) {
            const normalized = minute % (24 * 60);
            timeline.push(
                `${Math.floor(normalized / 60).toString().padStart(2, "0")}:${(normalized % 60).toString().padStart(2, "0")}`
            );
        }
        return timeline;
    }
    const timeline = [];
    for (let h = 9; h <= 12; h++) {
        const hStr = h.toString().padStart(2, '0');
        for (let m = 0; m <= 59; m++) {
            const mStr = m.toString().padStart(2, '0');
            timeline.push(`${hStr}:${mStr}`);
        }
    }
    for (let m = 0; m <= 30; m++) {
        const mStr = m.toString().padStart(2, '0');
        timeline.push(`13:${mStr}`);
    }
    return timeline;
}

// Chart 1: Intraday Line Chart (今日走勢)
function renderIntradayChart(intradayList, yesterdayClose, session = null) {
    const chartDom = document.getElementById("intraday-chart");
    if (intradayChart) {
        intradayChart.dispose();
    }
    
    if (!intradayList || intradayList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">最近交易日無即時交易數據</div>`;
        return;
    }
    
    intradayChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    
    const timeline = generateIntradayTimeline(session);
    const usesMinuteIndex = intradayList.some(item => Number.isInteger(item.minute_index));
    const dataMap = {};
    intradayList.forEach(item => {
        dataMap[usesMinuteIndex ? item.minute_index : item.time] = item;
    });
    
    let lastPrice = null;
    let sum = 0;
    let count = 0;
    const times = timeline;
    const prices = [];
    const avgPrices = [];
    const volumes = [];
    
    // Find the actual last time with data in the received intraday list
    let lastDataIndex = -1;
    intradayList.forEach(item => {
        const index = usesMinuteIndex ? item.minute_index : timeline.indexOf(item.time);
        if (index > lastDataIndex && item.price !== null && item.price !== undefined) {
            lastDataIndex = index;
        }
    });

    let lastAvgPrice = null;
    for (let i = 0; i < timeline.length; i++) {
        const t = timeline[i];
        const item = dataMap[usesMinuteIndex ? i : t];
        
        if (item) {
            lastPrice = item.price;
            prices.push(item.price);
            volumes.push(item.volume || 0);
        } else {
            if (i > lastDataIndex) {
                prices.push(null);
                volumes.push(null);
            } else {
                // If it is an internal missing minute, forward-fill the price and set volume to 0
                prices.push(lastPrice);
                volumes.push(0);
            }
        }
        
        if (lastPrice !== null && i <= lastDataIndex) {
            sum += lastPrice;
            count++;
            lastAvgPrice = Number((sum / count).toFixed(2));
            avgPrices.push(lastAvgPrice);
        } else {
            avgPrices.push(null);
        }
    }
    
    const validPrices = prices.filter(p => p !== null && p !== undefined && !isNaN(p));
    const maxPrice = Math.max(...validPrices);
    const minPrice = Math.min(...validPrices);
    
    let yMin = minPrice;
    let yMax = maxPrice;
    if (yesterdayClose !== null && yesterdayClose !== undefined && !isNaN(yesterdayClose)) {
        const maxDiff = Math.max(Math.abs(maxPrice - yesterdayClose), Math.abs(yesterdayClose - minPrice));
        const padding = maxDiff > 0 ? maxDiff * 0.08 : yesterdayClose * 0.01;
        yMin = Number((yesterdayClose - maxDiff - padding).toFixed(2));
        yMax = Number((yesterdayClose + maxDiff + padding).toFixed(2));
    } else {
        const diff = maxPrice - minPrice;
        if (diff > 0) {
            yMin = Number((minPrice - 0.1 * diff).toFixed(2));
            yMax = Number((maxPrice + 0.1 * diff).toFixed(2));
        } else {
            yMin = Number((minPrice * 0.9).toFixed(2));
            yMax = Number((maxPrice * 1.1).toFixed(2));
        }
    }
    
    let maxIdx = 0, minIdx = 0, maxVal = -Infinity, minVal = Infinity;
    for (let i = 0; i < prices.length; i++) {
        const p = prices[i];
        if (p !== null && p !== undefined && !isNaN(p)) {
            if (p > maxVal) { maxVal = p; maxIdx = i; }
            if (p < minVal) { minVal = p; minIdx = i; }
        }
    }
    const yRange = yMax - yMin;
    // Cap the label Y position within chart boundary
    const maxLabelY = Math.min(yMax - yRange * 0.05, maxVal + yRange * 0.08);
    const minLabelY = Math.max(yMin + yRange * 0.05, minVal - yRange * 0.08);
    
    let maxLabelIdx = maxIdx < prices.length / 2 ? maxIdx + 12 : maxIdx - 12;
    maxLabelIdx = Math.max(0, Math.min(times.length - 1, maxLabelIdx));
    let minLabelIdx = minIdx < prices.length / 2 ? minIdx + 12 : minIdx - 12;
    minLabelIdx = Math.max(0, Math.min(times.length - 1, minLabelIdx));
    
    const option = {
        grid: [
            { left: 45, right: 15, height: "55%", top: 20 },
            { left: 45, right: 15, top: "72%", height: "20%" }
        ],
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "cross" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function (params) {
                const priceParam = params.find(p => p.seriesName === "即時股價");
                const avgParam = params.find(p => p.seriesName === "均價線");
                const volParam = params.find(p => p.seriesName === "分時成交量");
                
                let res = `<b>時間: ${params[0].name}</b><br/>`;
                if (priceParam && priceParam.value !== undefined && priceParam.value !== null && !isNaN(priceParam.value)) {
                    res += `<span style="color:#f59e0b;">●</span> 價格: $${Number(priceParam.value).toFixed(2)}<br/>`;
                }
                if (avgParam && avgParam.value !== undefined && avgParam.value !== null && !isNaN(avgParam.value)) {
                    res += `<span style="color:#c084fc;">●</span> 均價: $${Number(avgParam.value).toFixed(2)}<br/>`;
                }
                if (volParam && volParam.value !== undefined && volParam.value !== null && !isNaN(volParam.value)) {
                    res += `<span style="color:#f97316;">●</span> 成交量: ${Number(volParam.value).toLocaleString()} 股<br/>`;
                }
                return res;
            }
        },
        xAxis: [
            {
                type: "category",
                data: times,
                gridIndex: 0,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { show: false }
            },
            {
                type: "category",
                data: times,
                gridIndex: 1,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            }
        ],
        yAxis: [
            {
                type: "value",
                scale: true,
                min: yMin,
                max: yMax,
                gridIndex: 0,
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            },
            {
                type: "value",
                gridIndex: 1,
                axisLine: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false }
            }
        ],
        series: [
            {
                name: "即時股價",
                type: "line",
                data: prices,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                symbol: "none",
                lineStyle: { color: "#f59e0b", width: 2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: "rgba(245, 158, 11, 0.15)" },
                        { offset: 1, color: "rgba(245, 158, 11, 0.0)" }
                    ])
                },
                markPoint: {
                    symbol: "circle",
                    symbolSize: 6,
                    data: [
                        { coord: [times[maxIdx], maxVal], name: "最高點", itemStyle: { color: "#ef4444" }, label: { show: false } },
                        { coord: [times[minIdx], minVal], name: "最低點", itemStyle: { color: "#10b981" }, label: { show: false } }
                    ]
                },
                markLine: {
                    symbol: ["none", "none"],
                    data: [
                        ...(yesterdayClose ? [{
                            yAxis: yesterdayClose,
                            lineStyle: { color: "rgba(255, 255, 255, 0.25)", type: "dashed", width: 1 },
                            label: {
                                show: true,
                                position: "insideEnd",
                                formatter: "昨收: $" + yesterdayClose.toFixed(2),
                                color: "#94a3b8",
                                fontSize: 9,
                                backgroundColor: "rgba(13, 8, 24, 0.8)",
                                padding: [2, 4],
                                borderRadius: 3
                            }
                        }] : []),
                        [
                            { coord: [times[maxIdx], maxVal], lineStyle: { color: "rgba(239, 68, 68, 0.4)", type: "dashed", width: 1 } },
                            { 
                                coord: [times[maxLabelIdx], maxLabelY], 
                                label: {
                                    show: true,
                                    position: "end",
                                    formatter: "最高: $" + maxVal.toFixed(2),
                                    color: "#ef4444",
                                    fontFamily: "Outfit",
                                    fontSize: 11,
                                    backgroundColor: "rgba(13, 8, 24, 0.75)",
                                    padding: [2, 4],
                                    borderRadius: 3
                                }
                            }
                        ],
                        [
                            { coord: [times[minIdx], minVal], lineStyle: { color: "rgba(16, 185, 129, 0.4)", type: "dashed", width: 1 } },
                            { 
                                coord: [times[minLabelIdx], minLabelY], 
                                label: {
                                    show: true,
                                    position: "end",
                                    formatter: "最低: $" + minVal.toFixed(2),
                                    color: "#10b981",
                                    fontFamily: "Outfit",
                                    fontSize: 11,
                                    backgroundColor: "rgba(13, 8, 24, 0.75)",
                                    padding: [2, 4],
                                    borderRadius: 3
                                }
                            }
                        ]
                    ]
                }
            },
            {
                name: "均價線",
                type: "line",
                data: avgPrices,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                symbol: "none",
                lineStyle: { color: "#c084fc", width: 1.5 }
            },
            {
                name: "分時成交量",
                type: "bar",
                data: volumes,
                xAxisIndex: 1,
                yAxisIndex: 1,
                itemStyle: { color: "#f97316" }
            }
        ]
    };
    
    intradayChart.setOption(option);
}

// Chart 1.5: Previous Intraday Line Chart (前一交易日走勢)
function renderPrevIntradayChart(prevIntradayList, yesterdayClose, session = null) {
    const chartDom = document.getElementById("prev-intraday-chart");
    if (prevIntradayChart) {
        prevIntradayChart.dispose();
    }
    
    if (!prevIntradayList || prevIntradayList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">前一交易日無即時交易數據</div>`;
        return;
    }
    
    prevIntradayChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    
    const timeline = generateIntradayTimeline(session);
    const usesMinuteIndex = prevIntradayList.some(item => Number.isInteger(item.minute_index));
    const dataMap = {};
    prevIntradayList.forEach(item => {
        dataMap[usesMinuteIndex ? item.minute_index : item.time] = item;
    });
    
    let lastPrice = null;
    let sum = 0;
    let count = 0;
    const times = timeline;
    const prices = [];
    const avgPrices = [];
    const volumes = [];
    
    // Find the actual last time with data in the received previous intraday list
    let lastDataIndex = -1;
    prevIntradayList.forEach(item => {
        const index = usesMinuteIndex ? item.minute_index : timeline.indexOf(item.time);
        if (index > lastDataIndex && item.price !== null && item.price !== undefined) {
            lastDataIndex = index;
        }
    });

    let lastAvgPrice = null;
    for (let i = 0; i < timeline.length; i++) {
        const t = timeline[i];
        const item = dataMap[usesMinuteIndex ? i : t];
        
        if (item) {
            lastPrice = item.price;
            prices.push(item.price);
            volumes.push(item.volume || 0);
        } else {
            if (i > lastDataIndex) {
                prices.push(null);
                volumes.push(null);
            } else {
                // If it is an internal missing minute, forward-fill the price and set volume to 0
                prices.push(lastPrice);
                volumes.push(0);
            }
        }
        
        if (lastPrice !== null && i <= lastDataIndex) {
            sum += lastPrice;
            count++;
            lastAvgPrice = Number((sum / count).toFixed(2));
            avgPrices.push(lastAvgPrice);
        } else {
            avgPrices.push(null);
        }
    }
    
    const validPrices = prices.filter(p => p !== null && p !== undefined && !isNaN(p));
    const maxPrice = Math.max(...validPrices);
    const minPrice = Math.min(...validPrices);
    
    let yMin = minPrice;
    let yMax = maxPrice;
    if (yesterdayClose !== null && yesterdayClose !== undefined && !isNaN(yesterdayClose)) {
        const maxDiff = Math.max(Math.abs(maxPrice - yesterdayClose), Math.abs(yesterdayClose - minPrice));
        const padding = maxDiff > 0 ? maxDiff * 0.08 : yesterdayClose * 0.01;
        yMin = Number((yesterdayClose - maxDiff - padding).toFixed(2));
        yMax = Number((yesterdayClose + maxDiff + padding).toFixed(2));
    } else {
        const diff = maxPrice - minPrice;
        if (diff > 0) {
            yMin = Number((minPrice - 0.1 * diff).toFixed(2));
            yMax = Number((maxPrice + 0.1 * diff).toFixed(2));
        } else {
            yMin = Number((minPrice * 0.9).toFixed(2));
            yMax = Number((maxPrice * 1.1).toFixed(2));
        }
    }
    
    let maxIdx = 0, minIdx = 0, maxVal = -Infinity, minVal = Infinity;
    for (let i = 0; i < prices.length; i++) {
        const p = prices[i];
        if (p !== null && p !== undefined && !isNaN(p)) {
            if (p > maxVal) { maxVal = p; maxIdx = i; }
            if (p < minVal) { minVal = p; minIdx = i; }
        }
    }
    const yRange = yMax - yMin;
    // Cap the label Y position within chart boundary
    const maxLabelY = Math.min(yMax - yRange * 0.05, maxVal + yRange * 0.08);
    const minLabelY = Math.max(yMin + yRange * 0.05, minVal - yRange * 0.08);
    
    let maxLabelIdx = maxIdx < prices.length / 2 ? maxIdx + 12 : maxIdx - 12;
    maxLabelIdx = Math.max(0, Math.min(times.length - 1, maxLabelIdx));
    let minLabelIdx = minIdx < prices.length / 2 ? minIdx + 12 : minIdx - 12;
    minLabelIdx = Math.max(0, Math.min(times.length - 1, minLabelIdx));
    
    const option = {
        grid: [
            { left: 45, right: 15, height: "55%", top: 20 },
            { left: 45, right: 15, top: "72%", height: "20%" }
        ],
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "cross" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function (params) {
                const priceParam = params.find(p => p.seriesName === "即時股價");
                const avgParam = params.find(p => p.seriesName === "均價線");
                const volParam = params.find(p => p.seriesName === "分時成交量");
                
                let res = `<b>時間: ${params[0].name}</b><br/>`;
                if (priceParam && priceParam.value !== undefined && priceParam.value !== null && !isNaN(priceParam.value)) {
                    res += `<span style="color:#34d399;">●</span> 價格: $${Number(priceParam.value).toFixed(2)}<br/>`;
                }
                if (avgParam && avgParam.value !== undefined && avgParam.value !== null && !isNaN(avgParam.value)) {
                    res += `<span style="color:#f59e0b;">●</span> 均價: $${Number(avgParam.value).toFixed(2)}<br/>`;
                }
                if (volParam && volParam.value !== undefined && volParam.value !== null && !isNaN(volParam.value)) {
                    res += `<span style="color:#34d399;">●</span> 成交量: ${Number(volParam.value).toLocaleString()} 股<br/>`;
                }
                return res;
            }
        },
        xAxis: [
            {
                type: "category",
                data: times,
                gridIndex: 0,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { show: false }
            },
            {
                type: "category",
                data: times,
                gridIndex: 1,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            }
        ],
        yAxis: [
            {
                type: "value",
                scale: true,
                min: yMin,
                max: yMax,
                gridIndex: 0,
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            },
            {
                type: "value",
                gridIndex: 1,
                axisLine: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false }
            }
        ],
        series: [
            {
                name: "即時股價",
                type: "line",
                data: prices,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                symbol: "none",
                lineStyle: { color: "#8b5cf6", width: 2 },
                areaStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                        { offset: 0, color: "rgba(139, 92, 246, 0.15)" },
                        { offset: 1, color: "rgba(139, 92, 246, 0.0)" }
                    ])
                },
                markPoint: {
                    symbol: "circle",
                    symbolSize: 6,
                    data: [
                        { coord: [times[maxIdx], maxVal], name: "最高點", itemStyle: { color: "#ef4444" }, label: { show: false } },
                        { coord: [times[minIdx], minVal], name: "最低點", itemStyle: { color: "#10b981" }, label: { show: false } }
                    ]
                },
                markLine: {
                    symbol: ["none", "none"],
                    data: [
                        ...(yesterdayClose ? [{
                            yAxis: yesterdayClose,
                            lineStyle: { color: "rgba(255, 255, 255, 0.25)", type: "dashed", width: 1 },
                            label: {
                                show: true,
                                position: "insideEnd",
                                formatter: "昨收: $" + yesterdayClose.toFixed(2),
                                color: "#94a3b8",
                                fontSize: 9,
                                backgroundColor: "rgba(13, 8, 24, 0.8)",
                                padding: [2, 4],
                                borderRadius: 3
                            }
                        }] : []),
                        [
                            { coord: [times[maxIdx], maxVal], lineStyle: { color: "rgba(239, 68, 68, 0.4)", type: "dashed", width: 1 } },
                            { 
                                coord: [times[maxLabelIdx], maxLabelY], 
                                label: {
                                    show: true,
                                    position: "end",
                                    formatter: "最高: $" + maxVal.toFixed(2),
                                    color: "#ef4444",
                                    fontFamily: "Outfit",
                                    fontSize: 11,
                                    backgroundColor: "rgba(13, 8, 24, 0.75)",
                                    padding: [2, 4],
                                    borderRadius: 3
                                }
                            }
                        ],
                        [
                            { coord: [times[minIdx], minVal], lineStyle: { color: "rgba(16, 185, 129, 0.4)", type: "dashed", width: 1 } },
                            { 
                                coord: [times[minLabelIdx], minLabelY], 
                                label: {
                                    show: true,
                                    position: "end",
                                    formatter: "最低: $" + minVal.toFixed(2),
                                    color: "#10b981",
                                    fontFamily: "Outfit",
                                    fontSize: 11,
                                    backgroundColor: "rgba(13, 8, 24, 0.75)",
                                    padding: [2, 4],
                                    borderRadius: 3
                                }
                            }
                        ]
                    ]
                }
            },
            {
                name: "均價線",
                type: "line",
                data: avgPrices,
                xAxisIndex: 0,
                yAxisIndex: 0,
                smooth: true,
                symbol: "none",
                lineStyle: { color: "#f59e0b", width: 1.5 }
            },
            {
                name: "分時成交量",
                type: "bar",
                data: volumes,
                xAxisIndex: 1,
                yAxisIndex: 1,
                itemStyle: { color: "#a855f7" }
            }
        ]
    };
    
    prevIntradayChart.setOption(option);
}

// Chart 2: Candlestick + Volume (日K線與成交量，疊加 SMA5、SMA20 及 BBAND)
function renderKlineChart(klineList) {
    const chartDom = document.getElementById("kline-chart");
    if (klineChart) {
        klineChart.dispose();
    }
    
    if (!klineList || klineList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">無日K線數據</div>`;
        return;
    }
    
    klineChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    
    const dates = klineList.map(item => item.date);
    const values = klineList.map(item => [item.open, item.close, item.low, item.high]);
    const sma5Values = klineList.map(item => item.sma5);
    const sma20Values = klineList.map(item => item.sma20);
    const sma60Values = klineList.map(item => item.sma60);
    const bbUpperValues = klineList.map(item => item.bb_upper);
    const bbLowerValues = klineList.map(item => item.bb_lower);
    const volumes = klineList.map((item, idx) => {
        return {
            value: item.volume,
            itemStyle: {
                color: item.close >= item.open ? "#ef4444" : "#10b981"
            }
        };
    });
    
    const option = {
        grid: [
            { left: 45, right: 15, height: "60%", top: 20 },
            { left: 45, right: 15, top: "72%", height: "20%" }
        ],
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "cross" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function (params) {
                const kData = params.find(p => p.seriesName === "K-Line");
                const vData = params.find(p => p.seriesName === "Volume");
                const sma5Data = params.find(p => p.seriesName === "SMA5");
                const sma20Data = params.find(p => p.seriesName === "SMA20");
                const sma60Data = params.find(p => p.seriesName === "SMA60");
                const bbUpperData = params.find(p => p.seriesName === "布林上軌");
                const bbLowerData = params.find(p => p.seriesName === "布林下軌");
                
                let res = `<b>${params[0].name}</b><br/>`;
                if (kData) {
                    res += `<span style="color:#ef4444;">●</span> 開盤: $${Number(kData.value[1]).toFixed(2)} ‧ 收盤: $${Number(kData.value[2]).toFixed(2)}<br/>`;
                    res += `<span style="color:#10b981;">●</span> 最低: $${Number(kData.value[3]).toFixed(2)} ‧ 最高: $${Number(kData.value[4]).toFixed(2)}<br/>`;
                }
                
                let smaText = [];
                if (sma5Data && sma5Data.value !== undefined && sma5Data.value !== null) {
                    smaText.push(`<span style="color:#f59e0b;">●</span> SMA5: $${Number(sma5Data.value).toFixed(2)}`);
                }
                if (sma20Data && sma20Data.value !== undefined && sma20Data.value !== null) {
                    smaText.push(`<span style="color:#a855f7;">●</span> SMA20: $${Number(sma20Data.value).toFixed(2)}`);
                }
                if (sma60Data && sma60Data.value !== undefined && sma60Data.value !== null) {
                    smaText.push(`<span style="color:#06b6d4;">●</span> SMA60: $${Number(sma60Data.value).toFixed(2)}`);
                }
                if (smaText.length > 0) {
                    res += smaText.join(" ‧ ") + "<br/>";
                }
                
                let bbText = [];
                if (bbUpperData && bbUpperData.value !== undefined && bbUpperData.value !== null) {
                    bbText.push(`<span style="color:rgba(244, 63, 94, 0.85);">●</span> 上軌: $${Number(bbUpperData.value).toFixed(2)}`);
                }
                if (bbLowerData && bbLowerData.value !== undefined && bbLowerData.value !== null) {
                    bbText.push(`<span style="color:rgba(16, 185, 129, 0.85);">●</span> 下軌: $${Number(bbLowerData.value).toFixed(2)}`);
                }
                if (bbText.length > 0) {
                    res += bbText.join(" ‧ ") + "<br/>";
                }
                
                if (vData) {
                    res += `成交量: ${vData.value.toLocaleString()} 股`;
                }
                return res;
            }
        },
        legend: {
            data: ["SMA5", "SMA20", "SMA60", "布林上軌", "布林下軌"],
            textStyle: { color: "#94a3b8", fontFamily: "Outfit", fontSize: 11 },
            right: 15,
            top: 0
        },
        xAxis: [
            {
                type: "category",
                data: dates,
                gridIndex: 0,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { color: "#94a3b8", show: false }
            },
            {
                type: "category",
                data: dates,
                gridIndex: 1,
                axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            }
        ],
        yAxis: [
            {
                type: "value",
                scale: true,
                gridIndex: 0,
                axisLine: { show: false },
                splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
                axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
            },
            {
                type: "value",
                gridIndex: 1,
                axisLine: { show: false },
                splitLine: { show: false },
                axisLabel: { show: false }
            }
        ],
        series: [
            {
                name: "K-Line",
                type: "candlestick",
                data: values,
                xAxisIndex: 0,
                yAxisIndex: 0,
                itemStyle: {
                    color: "#ef4444",
                    color0: "#10b981",
                    borderColor: "#ef4444",
                    borderColor0: "#10b981"
                }
            },
            {
                name: "SMA5",
                type: "line",
                data: sma5Values,
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: "none",
                color: "#f59e0b",
                lineStyle: { width: 1.5 },
                smooth: true
            },
            {
                name: "SMA20",
                type: "line",
                data: sma20Values,
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: "none",
                color: "#a855f7",
                lineStyle: { width: 1.5 },
                smooth: true
            },
            {
                name: "SMA60",
                type: "line",
                data: sma60Values,
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: "none",
                color: "#06b6d4",
                lineStyle: { width: 1.5 },
                smooth: true
            },
            {
                name: "布林上軌",
                type: "line",
                data: bbUpperValues,
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: "none",
                color: "rgba(244, 63, 94, 0.45)",
                lineStyle: { width: 1, type: "dashed" },
                smooth: true
            },
            {
                name: "布林下軌",
                type: "line",
                data: bbLowerValues,
                xAxisIndex: 0,
                yAxisIndex: 0,
                symbol: "none",
                color: "rgba(16, 185, 129, 0.45)",
                lineStyle: { width: 1, type: "dashed" },
                smooth: true
            },
            {
                name: "Volume",
                type: "bar",
                data: volumes,
                xAxisIndex: 1,
                yAxisIndex: 1
            }
        ]
    };
    
    klineChart.setOption(option);
}

// Chart 3: KD Double Lines (60分K KD值曲線)
function renderKdChart(kdList) {
    const chartDom = document.getElementById("kd-chart");
    if (kdChart) {
        kdChart.dispose();
    }
    
    if (!kdList || kdList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">無 KD 技術指標數據</div>`;
        return;
    }
    
    kdChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    
    const times = kdList.map(item => item.time);
    const kValues = kdList.map(item => item.k);
    const dValues = kdList.map(item => item.d);
    
    // Find best x-axis index where K and D lines are furthest from target Y
    const findBestIdx = (targetY) => {
        let best = 0;
        let maxDist = -1;
        for (let i = 0; i < times.length; i++) {
            const dist = Math.min(Math.abs(kValues[i] - targetY), Math.abs(dValues[i] - targetY));
            if (dist > maxDist) {
                maxDist = dist;
                best = i;
            }
        }
        return best;
    };
    
    const bestIdx50 = findBestIdx(50);
    const bestIdx40 = findBestIdx(40);
    
    const option = {
        grid: { top: 15, bottom: 20, left: 35, right: 15 },
        tooltip: {
            trigger: "axis",
            confine: true,
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function(params) {
                let res = `<b>時間: ${params[0].name}</b><br/>`;
                params.forEach(p => {
                    res += `${p.seriesName}: <span style="font-weight:700; color:${p.color}">${Number(p.value).toFixed(3)}</span><br/>`;
                });
                return res;
            }
        },
        legend: {
            data: ["K 值 (60,3)", "D 值 (60,3)"],
            textStyle: { color: "#94a3b8", fontFamily: "Outfit" },
            top: 0
        },
        xAxis: {
            type: "category",
            data: times,
            axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
        },
        yAxis: {
            type: "value",
            min: 0,
            max: 100,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
        },
        series: [
            {
                name: "K 值 (60,3)",
                type: "line",
                data: kValues,
                symbol: "none",
                color: "#f59e0b",
                lineStyle: { width: 2 },
                markLine: {
                    symbol: "none",
                    data: [
                        { 
                            yAxis: 50, 
                            lineStyle: { color: "rgba(16, 185, 129, 0.45)", type: "dashed", width: 1.5 }, 
                            label: { show: false }
                        },
                        { 
                            yAxis: 40, 
                            lineStyle: { color: "rgba(255,255,255,0.15)", type: "dashed" }, 
                            label: { show: false }
                        }
                    ]
                },
                markPoint: {
                    symbol: "circle",
                    symbolSize: 0,
                    data: [
                        {
                            coord: [times[bestIdx50], 50],
                            label: {
                                show: true,
                                formatter: "50 基準",
                                color: "#34d399",
                                fontFamily: "Outfit",
                                fontWeight: "bold",
                                backgroundColor: "#0c0718",
                                padding: [2, 4],
                                borderRadius: 3,
                                distance: 0
                            }
                        },
                        {
                            coord: [times[bestIdx40], 40],
                            label: {
                                show: true,
                                formatter: "40 低檔",
                                color: "#94a3b8",
                                fontFamily: "Outfit",
                                backgroundColor: "#0c0718",
                                padding: [2, 4],
                                borderRadius: 3,
                                distance: 0
                            }
                        }
                    ]
                },
                markArea: {
                    silent: true,
                    itemStyle: {
                        color: "rgba(244, 63, 94, 0.06)"
                    },
                    data: [
                        [
                            {
                                yAxis: 0
                            },
                            {
                                yAxis: 40
                            }
                        ]
                    ]
                }
            },
            {
                name: "D 值 (60,3)",
                type: "line",
                data: dValues,
                symbol: "none",
                color: "#6366f1",
                lineStyle: { width: 2 }
            }
        ]
    };
    
    kdChart.setOption(option);
}

// Chart 3.5: Hourly K-Line Chart (60分K線圖，併入 SMA60)
function renderHourlyKlineChart(kdList) {
    const chartDom = document.getElementById("hourly-kline-chart");
    if (hourlyKlineChart) {
        hourlyKlineChart.dispose();
    }
    
    const validKlineList = kdList.filter(item => item.open !== undefined && item.close !== undefined);
    
    if (!validKlineList || validKlineList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 3rem 0; font-size:0.8rem;">無60分K線數據</div>`;
        return;
    }
    
    hourlyKlineChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    
    const dates = validKlineList.map(item => item.time);
    const values = validKlineList.map(item => [item.open, item.close, item.low, item.high]);
    const sma60Values = validKlineList.map(item => item.sma60);
    
    const option = {
        grid: { left: 35, right: 15, top: 15, bottom: 20 },
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "cross" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function (params) {
                const kData = params.find(p => p.seriesName === "K-Line");
                const sma60Data = params.find(p => p.seriesName === "SMA60");
                
                let res = `<b>60分K: ${params[0].name}</b><br/>`;
                if (kData) {
                    const oVal = Number(kData.value[1]).toFixed(2);
                    const cVal = Number(kData.value[2]).toFixed(2);
                    const lVal = Number(kData.value[3]).toFixed(2);
                    const hVal = Number(kData.value[4]).toFixed(2);
                    res += `<span style="color:#ef4444;">●</span> 開: $${oVal} ‧ 收: $${cVal}<br/>`;
                    res += `<span style="color:#10b981;">●</span> 低: $${lVal} ‧ 高: $${hVal}<br/>`;
                }
                if (sma60Data && sma60Data.value !== undefined && sma60Data.value !== null) {
                    res += `<span style="color:#06b6d4;">●</span> SMA60: $${Number(sma60Data.value).toFixed(3)}<br/>`;
                }
                return res;
            }
        },
        legend: {
            data: ["SMA60"],
            textStyle: { color: "#94a3b8", fontFamily: "Outfit", fontSize: 10 },
            right: 15,
            top: 0
        },
        xAxis: {
            type: "category",
            data: dates,
            axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit", fontSize: 9 }
        },
        yAxis: {
            type: "value",
            scale: true,
            axisLine: { show: false },
            splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit", fontSize: 9 }
        },
        series: [
            {
                name: "K-Line",
                type: "candlestick",
                data: values,
                itemStyle: {
                    color: "#ef4444",
                    color0: "#10b981",
                    borderColor: "#ef4444",
                    borderColor0: "#10b981"
                }
            },
            {
                name: "SMA60",
                type: "line",
                data: sma60Values,
                symbol: "none",
                lineStyle: { color: "#06b6d4", width: 1.5 },
                smooth: true
            }
        ]
    };
    
    hourlyKlineChart.setOption(option);
}

// Chart 4: Institutional Net Buy/Sell Multi-Bar Chart (法人買賣超)
function renderInstitutionalChart(instList, isIntraday = false, intradayDate = "") {
    const chartDom = document.getElementById("institutional-chart");
    if (institutionalChart) {
        institutionalChart.dispose();
    }
    
    if (!instList || instList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">無法人買賣超數據</div>`;
        return;
    }
    
    institutionalChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    const chartList = [...instList];
    if (isIntraday && intradayDate && !chartList.some(item => item.date === intradayDate)) {
        chartList.push({
            date: intradayDate,
            foreign: null,
            trust: null,
            dealer: null,
            foreign_buy: 0,
            foreign_sell: 0,
            trust_buy: 0,
            trust_sell: 0,
            dealer_buy: 0,
            dealer_sell: 0,
            close: selectedStock ? selectedStock.current_price : 0,
            pending: true
        });
    }
    
    const dates = chartList.map(item => item.date);
    const foreign = chartList.map(item => item.foreign);
    const trust = chartList.map(item => item.trust);
    const dealer = chartList.map(item => item.dealer);
    
    const option = {
        color: ["#6366f1", "#ec4899", "#f59e0b"],
        grid: { top: 35, bottom: 25, left: 45, right: 15 },
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "shadow" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function(params) {
                const itemData = chartList.find(d => d.date === params[0].name);
                if (itemData && itemData.pending) {
                    return `<b>${params[0].name}</b><br/><span style="color:#94a3b8;">盤中資料待收盤</span>`;
                }
                const closePrice = itemData ? itemData.close : (selectedStock ? selectedStock.current_price : 0);
                let res = `<b>${params[0].name} 法人買賣詳情</b><br/>`;
                params.forEach(p => {
                    const sign = p.value >= 0 ? "+" : "";
                    const shares = p.value * 1000;
                    const valueNtd = closePrice ? shares * closePrice : 0;
                    let valueText = "";
                    if (valueNtd !== 0) {
                        if (Math.abs(valueNtd) >= 100000000) {
                            valueText = ` (${(valueNtd / 100000000).toFixed(2)} 億)`;
                        } else {
                            valueText = ` (${(valueNtd / 10000).toFixed(0)} 萬)`;
                        }
                    }
                    
                    let buySellText = "";
                    if (itemData) {
                        let buyVal = 0;
                        let sellVal = 0;
                        if (p.seriesName === "外資") {
                            buyVal = itemData.foreign_buy || 0;
                            sellVal = itemData.foreign_sell || 0;
                        } else if (p.seriesName === "投信") {
                            buyVal = itemData.trust_buy || 0;
                            sellVal = itemData.trust_sell || 0;
                        } else if (p.seriesName === "自營商") {
                            buyVal = itemData.dealer_buy || 0;
                            sellVal = itemData.dealer_sell || 0;
                        }
                        buySellText = `<span style="font-size: 0.82em; color: #94a3b8; font-weight: normal; margin-left: 6px;">(買:${buyVal.toLocaleString()} / 賣:${sellVal.toLocaleString()})</span>`;
                    }
                    
                    res += `${p.seriesName}淨值: <span style="font-weight:700; color:${p.value >= 0 ? '#ef4444' : '#10b981'}">${sign}${p.value.toLocaleString()} 張${valueText}</span>${buySellText}<br/>`;
                });
                return res;
            }
        },
        legend: {
            data: ["外資", "投信", "自營商"],
            textStyle: { color: "#94a3b8", fontFamily: "Outfit" },
            top: 0
        },
        xAxis: {
            type: "category",
            data: dates,
            axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
        },
        yAxis: {
            type: "value",
            axisLine: { show: false },
            splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
        },
        series: [
            {
                name: "外資",
                type: "bar",
                data: foreign,
                color: "#6366f1",
                itemStyle: {
                    color: function(params) {
                        return params.value >= 0 ? "#6366f1" : "rgba(99, 102, 241, 0.45)";
                    }
                }
            },
            {
                name: "投信",
                type: "bar",
                data: trust,
                color: "#ec4899",
                itemStyle: {
                    color: function(params) {
                        return params.value >= 0 ? "#ec4899" : "rgba(236, 72, 153, 0.45)";
                    }
                }
            },
            {
                name: "自營商",
                type: "bar",
                data: dealer,
                color: "#f59e0b",
                itemStyle: {
                    color: function(params) {
                        return params.value >= 0 ? "#f59e0b" : "rgba(245, 158, 11, 0.45)";
                    }
                }
            }
        ]
    };
    
    institutionalChart.setOption(option);
}

// Chart 5: Chip Concentration Chart (近20日籌碼集中度)
function renderChipConcentrationChart(instList, isIntraday = false, intradayDate = "") {
    const chartDom = document.getElementById("chip-concentration-chart");
    if (chipConcentrationChart) {
        chipConcentrationChart.dispose();
    }
    
    if (!instList || instList.length === 0) {
        chartDom.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 5rem 0;">無籌碼集中度數據</div>`;
        return;
    }
    
    chipConcentrationChart = echarts.init(chartDom, "dark", { backgroundColor: "transparent" });
    const chartList = [...instList];
    if (isIntraday && intradayDate && !chartList.some(item => item.date === intradayDate)) {
        chartList.push({
            date: intradayDate,
            concentration: null,
            total_diff: 0,
            volume: 0,
            pending: true
        });
    }
    
    const dates = chartList.map(item => item.date);
    const concentration = chartList.map(item => item.concentration);
    
    const option = {
        grid: { top: 35, bottom: 25, left: 45, right: 15 },
        tooltip: {
            trigger: "axis",
            confine: true,
            axisPointer: { type: "shadow" },
            backgroundColor: "#000",
            borderColor: "rgba(255, 255, 255, 0.1)",
            textStyle: { color: "#fff", fontFamily: "Outfit", fontSize: 15 },
            formatter: function(params) {
                const p = params[0];
                const itemData = chartList.find(d => d.date === p.name);
                if (itemData && itemData.pending) {
                    return `<b>${p.name}</b><br/><span style="color:#94a3b8;">盤中資料待收盤</span>`;
                }
                const totalDiff = itemData ? itemData.total_diff : 0;
                const dailyVol = itemData ? itemData.volume : 0;
                
                const sign = p.value >= 0 ? "+" : "";
                const netSign = totalDiff >= 0 ? "+" : "";
                return `<div style="font-size:15px; line-height:1.45; font-family:Outfit, Noto Sans TC;">` +
                       `<b>${p.name} 籌碼集中度</b><br/>` +
                       `集中度: <span style="font-weight:700; color:${p.value >= 0 ? '#ef4444' : '#10b981'}">${sign}${p.value.toFixed(2)} %</span><br/>` +
                       `三大法人淨買賣超: <span style="font-weight:700; color:${totalDiff >= 0 ? '#ef4444' : '#10b981'}">${netSign}${totalDiff.toLocaleString()} 張</span><br/>` +
                       `當日總成交量: <span style="font-weight:600; color:#fff;">${dailyVol.toLocaleString()} 張</span><br/>` +
                       `<div style="font-size:12px; color:#94a3b8; font-weight:normal; margin-top:4px; line-height:1.4;">` +
                       `● 公式: 三大法人淨買賣超 / 當日成交量 * 100%<br>` +
                       `● 分析: ＞ 0 籌碼趨向集中；＜ 0 籌碼趨向分散</div>` +
                       `</div>`;
            }
        },
        xAxis: {
            type: "category",
            data: dates,
            axisLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
            axisLabel: { color: "#94a3b8", fontFamily: "Outfit" }
        },
        yAxis: {
            type: "value",
            axisLine: { show: false },
            splitLine: { lineStyle: { color: "rgba(255,255,255,0.04)" } },
            axisLabel: { 
                color: "#94a3b8", 
                fontFamily: "Outfit",
                formatter: "{value} %"
            }
        },
        series: [
            {
                name: "籌碼集中度",
                type: "bar",
                data: concentration,
                itemStyle: {
                    color: function(params) {
                        return params.value >= 0 ? "#ef4444" : "#10b981";
                    }
                }
            }
        ]
    };
    
    chipConcentrationChart.setOption(option);
}

function renderMajorHolderChart(holderList) {
    const chartDom = document.getElementById("major-holder-chart");
    if (majorHolderChart) majorHolderChart.dispose();
    const holderRows = (holderList || [])
        .filter(item => item?.date && (item.ratio !== null || item.retail_ratio !== null))
        .sort((a, b) => String(a.date).localeCompare(String(b.date)));
    if (holderRows.length === 0) {
        chartDom.innerHTML = "";
        return;
    }
    const axisDates = holderRows.map(item => item.date);
    const majorRatios = holderRows.map(item => item.ratio);
    const retailRatios = holderRows.map(item => item.retail_ratio);
    majorHolderChart = echarts.init(chartDom, "dark", {backgroundColor: "transparent"});
    majorHolderChart.setOption({
        color: ["#f43f5e", "#22c55e"],
        legend: {
            top: 0,
            right: 12,
            textStyle: {color: "#cbd5e1"},
            itemWidth: 18,
            itemHeight: 8,
            data: ["千張以上大戶", "10張以下散戶"]
        },
        grid: {top: 38, bottom: 48, left: 48, right: 18},
        dataZoom: [
            {type: "inside", start: 0, end: 100},
            {type: "slider", height: 16, bottom: 4, borderColor: "transparent", fillerColor: "rgba(99,102,241,0.18)"}
        ],
        tooltip: {
            trigger: "axis",
            confine: true,
            formatter: params => {
                const rows = params
                    .filter(point => point.value !== null && point.value !== undefined)
                    .map(point => `${point.marker}${point.seriesName}：<b>${Number(point.value).toFixed(2)}%</b>`);
                return `<b>${params[0]?.name || ""}</b><br>${rows.join("<br>")}`;
            }
        },
        xAxis: {
            type: "category",
            data: axisDates,
            boundaryGap: false,
            axisLine: {lineStyle: {color: "rgba(255,255,255,0.1)"}},
            axisLabel: {color: "#94a3b8", hideOverlap: true}
        },
        yAxis: {
            type: "value",
            min: 0,
            max: 100,
            interval: 20,
            axisLabel: {color: "#94a3b8", formatter: "{value}%"},
            splitLine: {lineStyle: {color: "rgba(255,255,255,0.04)"}}
        },
        series: [
            {
                name: "千張以上大戶",
                type: "line",
                smooth: true,
                showSymbol: true,
                symbol: "circle",
                symbolSize: 7,
                data: majorRatios,
                connectNulls: true,
                lineStyle: {width: 3, color: "#f43f5e"},
                itemStyle: {
                    color: "#fbbf24",
                    borderColor: "#fff7ed",
                    borderWidth: 2,
                    shadowBlur: 8,
                    shadowColor: "rgba(251,191,36,0.85)"
                },
                markArea: {
                    silent: true,
                    itemStyle: {color: "rgba(245,158,11,0.12)"},
                    label: {show: true, color: "#f59e0b", formatter: "大戶適度集中 40%–70%"},
                    data: [[{yAxis: 40}, {yAxis: 70}]]
                }
            },
            {
                name: "10張以下散戶",
                type: "line",
                smooth: true,
                showSymbol: true,
                symbol: "circle",
                symbolSize: 7,
                data: retailRatios,
                connectNulls: true,
                lineStyle: {width: 3, color: "#22c55e"},
                itemStyle: {
                    color: "#67e8f9",
                    borderColor: "#ecfeff",
                    borderWidth: 2,
                    shadowBlur: 8,
                    shadowColor: "rgba(103,232,249,0.85)"
                }
            }
        ]
    });
}

// Handle Add Stock Action
async function handleAddStock() {
    let code = stockCodeInput.value.trim();
    if (!code) return;
    const isTaiwanCode = /^\d{4,6}[A-Za-z]?$/.test(code);
    
    // Check if code is non-numeric, meaning the user typed/selected a stock name
    if (!isTaiwanCode && isNaN(code)) {
        const found = allStocks.find(s => s.name === code || s.name.includes(code) || code.includes(s.name));
        if (found) {
            code = found.code;
        } else {
            showToast("找不到對應的股票名稱，請由下拉清單中點選或輸入代號", "danger");
            return;
        }
    }
    code = code.toUpperCase();
    
    addBtn.disabled = true;
    addBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 新增中...`;
    
    try {
        const response = await fetch(`${API_BASE}/stocks`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code: code, added_by: "manual" })
        });
        const resData = await response.json();
        
        if (response.ok) {
            showToast(`成功將 ${resData.name} (${resData.code}) 新增至追蹤清單！`, "success");
            stockCodeInput.value = "";
            await fetchAndAnalyzeStocks(false);
            await saveStocksToStorage();
            
            // Auto-select the newly added stock
            const newlyAdded = currentStocksData.find(s => s.code === resData.code);
            if (newlyAdded) {
                selectStockRow(newlyAdded, true);
            }
        } else {
            showToast(resData.detail || "無法新增此股票", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗，請稍後再試。", "danger");
    } finally {
        addBtn.disabled = false;
        addBtn.innerHTML = `<i class="fa-solid fa-plus"></i> 手動新增`;
    }
}

// Text file importing is handled by handleTextFileSelect above

// Handle Delete Stock Action
async function handleDeleteStock(code, name) {
    if (!confirm(`確認要取消追蹤 ${name} (${code}) 嗎？`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/stocks/${code}`, { method: "DELETE" });
        if (response.ok) {
            showToast(`已取消追蹤 ${name} (${code})`, "success");
            
            if (selectedStock && selectedStock.code === code) {
                selectedStock = null;
                localStorage.removeItem("selectedStockCode");
                localStorage.removeItem("lastSelectedStock");
                setCalculatorMode(false);
            }
            currentStocksData = currentStocksData.filter(stock => stock.code !== code);
            renderStockTable(currentStocksData);
            await saveStocksToStorage();
        } else {
            const resData = await response.json();
            showToast(resData.detail || "無法刪除股票", "danger");
        }
    } catch (e) {
        showToast("取消追蹤失敗，請檢查網路連線。", "danger");
    }
}

// Fetch and Render Active Wind-Control Monitors
function renderMonitorSignal(code, action = "BUY") {
    const signal = monitorSignalsData[String(code)] || {};
    const active = signal.system_a_signal === true;
    const label = active ? (action === "NOT_BUY" ? "可買入" : "可加碼") : "";
    return `
        <div class="status-indicator monitor-signal" data-code="${code}" data-action="${action}" data-tooltip="${active ? label : "目前未符合進場條件"}">
            <span class="light-rect ${active ? "green" : "red"}"></span>
            ${label ? `<span style="font-size:0.68rem;color:var(--color-danger);font-weight:700;">${label}</span>` : ""}
        </div>`;
}

async function fetchAndRenderMonitors() {
    try {
        const [ordersRes, usOrdersRes] = await Promise.all([
            fetch(`${API_BASE}/sinopac/orders?market=TW`),
            fetch(`${API_BASE}/sinopac/orders?market=US`)
        ]);
        
        if (!ordersRes.ok) return;
        const orders = await ordersRes.json();
        const usOrders = usOrdersRes.ok ? await usOrdersRes.json() : [];
        if (!monitorSignalsLoading) {
            monitorSignalsLoading = true;
            fetch(`${API_BASE}/stocks/monitor-signals`)
                .then(response => response.ok ? response.json() : null)
                .then(data => {
                    if (!data) return;
                    monitorSignalsData = data;
                    document.querySelectorAll(".monitor-signal").forEach(element => {
                        const code = element.dataset.code;
                        const action = element.dataset.action || "BUY";
                        const wrapper = document.createElement("div");
                        wrapper.innerHTML = renderMonitorSignal(code, action);
                        element.replaceWith(wrapper.firstElementChild);
                    });
                })
                .catch(error => console.error("Failed to fetch monitor signals:", error))
                .finally(() => {
                    monitorSignalsLoading = false;
                });
        }
        
        currentMonitorsData = orders;
        const monitoringCount = orders.filter(o => o.status === "MONITORING").length;
        if (monitorCountLabel) {
            monitorCountLabel.textContent = `共 ${monitoringCount} 檔監控中`;
        }
        
        renderUSMonitors(usOrders);
        
        if (!monitorsTableBody) return;
        
        if (orders.length === 0) {
            monitorsTableBody.innerHTML = `
                <tr class="table-placeholder">
                    <td colspan="10" style="text-align: center; padding: 2rem; color: var(--text-muted);">
                        <i class="fa-solid fa-folder-open" style="font-size: 1.5rem; margin-bottom: 0.5rem; display: block; color: rgba(255,255,255,0.15);"></i>
                        無進行中的風控監控項目
                    </td>
                </tr>
            `;
            return;
        }
        
        const sortedOrders = orders
            .sort((a, b) => {
                const aIsBuy = a.action === "BUY";
                const bIsBuy = b.action === "BUY";
                if (aIsBuy !== bIsBuy) return aIsBuy ? -1 : 1;
                return String(a.code).localeCompare(
                    String(b.code),
                    "zh-Hant",
                    { numeric: true, sensitivity: "base" }
                );
            });
        currentMonitorsData = sortedOrders;
        monitorsTableBody.innerHTML = "";
        
        sortedOrders.forEach((o, orderIndex) => {
            const tr = document.createElement("tr");
            tr.dataset.code = o.code;
            if (selectedStock?.code === o.code) tr.classList.add("selected");
            tr.style.cursor = "pointer";
            tr.addEventListener("click", (e) => {
                if (e.target.closest("button") || e.target.closest("i") || e.target.closest(".editable-price") || e.target.closest(".editable-qty") || e.target.closest(".editable-risk-price")) {
                    return;
                }
                let foundStock = currentStocksData.find(s => s.code === o.code) || potentialStocksData.find(s => s.code === o.code);
                if (!foundStock) {
                    foundStock = {
                        code: o.code,
                        symbol: o.symbol || (o.code.length === 4 ? o.code + ".TW" : o.code + ".TWO"),
                        name: o.name,
                        current_price: o.last_price || o.buy_price,
                        prev_high: o.stop_profit_price,
                        system_a_signal: false,
                        daily_trend_ok: false,
                        kd_under_50: false,
                        hourly_kd_ok: false,
                        golden_cross_count: 0
                    };
                }
                selectStockRow(foundStock, false);
            });
            
            const isActualBuy = o.action === "BUY";
            const safeName = cleanDisplayStockName(o.name);
            const actionHtml = `<button class="delete-monitor-btn" data-id="${o.order_id}" data-name="${safeName}" data-code="${o.code}" data-tooltip="刪除紀錄"><i class="fa-regular fa-trash-can"></i></button>`;
                
            const qtyText = o.lot_type === "ROUND" ? `${o.quantity / 1000} 張 (${o.quantity} 股)` : `${o.quantity} 股`;
            
            const displayOrder = { ...o, name: safeName };
            const formattedName = formatStockNameHTML(displayOrder, o.code, o.industry || "", false);
            const isBuyAction = o.action === "BUY";
            const buyStateText = isBuyAction ? "已買入" : "未買入";
            const buyStateColor = isBuyAction ? "var(--color-danger)" : "var(--text-muted)";
            const triggerState = getRiskTriggerState(o);
            const triggerBadge = triggerState === "stop-loss"
                ? `<span class="risk-trigger-label stop-loss">停損觸發</span>`
                : (triggerState === "take-profit"
                    ? `<span class="risk-trigger-label take-profit">停利觸發</span>`
                    : "");
            let rValue = "-";
            const risk = o.buy_price - o.stop_loss_price;
            if (risk > 0 && o.stop_profit_price !== null && o.stop_profit_price !== undefined) {
                const computedR = (o.stop_profit_price - o.buy_price) / risk;
                rValue = computedR.toFixed(2);
            }
            const foundInList = currentStocksData.find(s => String(s.code).trim() === String(o.code).trim()) || 
                                potentialStocksData.find(s => String(s.code).trim() === String(o.code).trim());
            let lastPrice = o.last_price || o.buy_price;
            let refPrice = o.reference_price || lastPrice;
            if (foundInList && foundInList.current_price !== undefined && foundInList.current_price !== null && foundInList.current_price > 0) {
                lastPrice = foundInList.current_price;
                if (foundInList.reference_price !== undefined && foundInList.reference_price !== null && foundInList.reference_price > 0) {
                    refPrice = foundInList.reference_price;
                }
            }
            const change = lastPrice - refPrice;
            const percent = refPrice > 0 ? (change / refPrice) * 100 : 0.0;
            
            const priceStyle = getPriceStyleAndClass(lastPrice, refPrice, o.code, o.limit_up);
            const priceHtml = priceStyle.style 
                ? `<span class="${priceStyle.className}" style="${priceStyle.style}">${Number(lastPrice).toFixed(2)}</span>`
                : `<span>$${Number(lastPrice).toFixed(2)}</span>`;
            
            const changeCellHtml = formatChangeCellWithLimit(change, percent, lastPrice, refPrice, o.code, o.limit_up);

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
                <td style="font-family:var(--font-outfit); font-weight:700;">
                    ${priceHtml}
                    ${triggerBadge}
                </td>
                ${changeCellHtml}
                <td>
                    <span class="editable-risk-price stop-loss-price" data-id="${o.order_id}" data-field="stop_loss_price" data-value="${o.stop_loss_price}" data-other-value="${o.stop_profit_price}" title="點擊修改停損價">&le; $${o.stop_loss_price.toFixed(2)}</span>
                    <span class="editable-risk-price take-profit-price" data-id="${o.order_id}" data-field="stop_profit_price" data-value="${o.stop_profit_price}" data-other-value="${o.stop_loss_price}" title="點擊修改停利價">&ge; $${o.stop_profit_price.toFixed(2)}</span>
                </td>
                <td>${renderRiskLights(o)}</td>
                <td>${renderMonitorSignal(o.code, o.action)}</td>
                <td style="font-family:var(--font-outfit); font-weight:600;">
                    ${rValue}
                </td>
                <td class="actions-col">
                    ${actionHtml}
                </td>
            `;
            const delBtn = tr.querySelector(".delete-monitor-btn");
            if (delBtn) {
                delBtn.addEventListener("click", () => handleDeleteMonitor(o.order_id, o.name, o.code));
            }

            const toggleBtn = tr.querySelector(".toggle-buy-btn");
            if (toggleBtn) {
                toggleBtn.addEventListener("click", async (e) => {
                    e.stopPropagation();
                    const nextAction = toggleBtn.dataset.currentAction === "BUY" ? "NOT_BUY" : "BUY";
                    toggleBtn.disabled = true;
                    try {
                        const response = await fetch(`${API_BASE}/sinopac/orders/${o.order_id}/toggle-action`, {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ action: nextAction })
                        });
                        const data = await response.json();
                        if (response.ok) {
                            showToast(nextAction === "BUY" ? "已切換為已買入" : "已切換為未買入", "success");
                            await fetchAndRenderMonitors();
                        } else {
                            showToast(data.detail || "切換失敗", "danger");
                        }
                    } catch (err) {
                        console.error(err);
                        showToast("切換狀態失敗", "danger");
                    } finally {
                        toggleBtn.disabled = false;
                    }
                });
            }

            monitorsTableBody.appendChild(tr);
            const nextOrder = sortedOrders[orderIndex + 1];
            if (!nextOrder || nextOrder.action !== o.action) {
                const groupOrders = sortedOrders.filter(item => item.action === o.action);
                const subtotal = groupOrders.reduce((sum, item) => sum + Number(item.buy_price || 0) * Number(item.quantity || 0), 0);
                const subtotalRow = document.createElement("tr");
                subtotalRow.className = `monitor-subtotal-row ${o.action === "BUY" ? "bought" : "pending"} tw`;
                subtotalRow.innerHTML = `<td colspan="2">${o.action === "BUY" ? "已買入" : "未買入"}合計</td><td class="monitor-cost-cell"><strong>NT$ ${Math.round(subtotal).toLocaleString()}</strong></td><td colspan="6"></td>`;
                monitorsTableBody.appendChild(subtotalRow);
            }
        });

        // Add listeners for editing buy price
        monitorsTableBody.querySelectorAll(".editable-price").forEach(el => {
            el.addEventListener("click", async (e) => {
                e.stopPropagation();
                const orderId = el.dataset.id;
                const oldPrice = parseFloat(el.dataset.price);
                const newPriceInput = prompt("請輸入新買入價 (台幣)：", oldPrice.toFixed(2));
                if (newPriceInput === null) return;
                const newPrice = parseFloat(newPriceInput);
                if (isNaN(newPrice) || newPrice <= 0) {
                    showToast("請輸入有效的價格", "error");
                    return;
                }
                
                const qtyEl = el.nextElementSibling;
                const currentQty = parseInt(qtyEl.dataset.qty) || 0;
                
                await updateOrderPriceQty(orderId, newPrice, currentQty);
            });
        });
        
        // Add listeners for editing quantity
        monitorsTableBody.querySelectorAll(".editable-qty").forEach(el => {
            el.addEventListener("click", async (e) => {
                e.stopPropagation();
                const orderId = el.dataset.id;
                const oldQty = parseInt(el.dataset.qty);
                const type = el.dataset.type;
                
                let promptMsg = type === "ROUND" ? "請輸入新買入張數 (張)：" : "請輸入新買入數量 (股)：";
                let defaultVal = type === "ROUND" ? (oldQty / 1000).toString() : oldQty.toString();
                
                const newQtyInput = prompt(promptMsg, defaultVal);
                if (newQtyInput === null) return;
                
                let newQty = parseFloat(newQtyInput);
                if (isNaN(newQty) || newQty <= 0) {
                    showToast("請輸入有效的數量", "error");
                    return;
                }
                
                if (type === "ROUND") {
                    newQty = Math.floor(newQty) * 1000;
                } else {
                    newQty = Math.floor(newQty);
                }
                
                const currentPrice = parseFloat(el.previousElementSibling.dataset.price) || 0;
                
                await updateOrderPriceQty(orderId, currentPrice, newQty);
            });
        });

        bindEditableRiskPrices(monitorsTableBody);
        
    } catch (e) {
        console.error("Failed to fetch monitors:", e);
    }
}

function renderRiskLights(order) {
    const price = validPrice(order.last_price) || validPrice(order.buy_price);
    const stopLossOn = price !== null && price <= Number(order.stop_loss_price);
    const takeProfitOn = price !== null && price >= Number(order.stop_profit_price);
    return `<div class="risk-lights">
        <span class="risk-light loss ${stopLossOn ? "on" : ""}" data-tooltip="停損${stopLossOn ? "已觸發" : "未觸發"}">損</span>
        <span class="risk-light profit ${takeProfitOn ? "on" : ""}" data-tooltip="停利${takeProfitOn ? "已觸發" : "未觸發"}">利</span>
    </div>`;
}

function renderUSMonitors(orders) {
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
        const nameTooltip = escapeHtmlAttribute(`中文名稱: ${o.name_zh || o.code}\n英文名稱: ${o.name || o.code}\n主要業務: ${o.industry || "尚未取得"}`);
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
        
        const priceStyle = getPriceStyleAndClass(lastPrice, refPrice, o.code, o.limit_up);
        const priceHtml = priceStyle.style 
            ? `<span class="${priceStyle.className}" style="${priceStyle.style}">US$${Number(lastPrice).toFixed(2)}</span>`
            : `<span>US$${Number(lastPrice).toFixed(2)}</span>`;
            
        const changeCellHtml = formatChangeCellWithLimit(change, percent, lastPrice, refPrice, o.code, o.limit_up);

        tr.innerHTML = `
            <td><strong data-tooltip="${nameTooltip}">${escapeHtmlText(o.name || o.code)}</strong><span class="monitor-code">${escapeHtmlText(o.code)}</span><button type="button" class="toggle-buy-btn" data-order-id="${o.order_id}" data-current-action="${o.action}" style="font-size:0.68rem;color:${buyStateColor};font-weight:700;background:transparent;border:none;padding:0;cursor:pointer;">${buyStateText}</button></td>
            <td><div class="monitor-buy-cell"><span class="editable-price us-buy-price" data-id="${o.order_id}" data-price="${o.buy_price}">US$${Number(o.buy_price).toFixed(2)}</span><small class="editable-qty" data-id="${o.order_id}" data-price="${o.buy_price}" data-qty="${o.quantity}" data-type="ODD">${qtyText}</small></div></td>
            <td class="monitor-cost-cell">US$ ${Number(Number(o.buy_price) * Number(o.quantity)).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
            <td style="font-family:var(--font-outfit); font-weight:700;">${priceHtml}</td>
            ${changeCellHtml}
            <td><span class="editable-risk-price stop-loss-price" data-id="${o.order_id}" data-field="stop_loss_price" data-value="${o.stop_loss_price}">&le; US$${Number(o.stop_loss_price).toFixed(2)}</span><span class="editable-risk-price take-profit-price" data-id="${o.order_id}" data-field="stop_profit_price" data-value="${o.stop_profit_price}">&ge; US$${Number(o.stop_profit_price).toFixed(2)}</span></td>
            <td>${renderRiskLights(o)}</td>
            <td>${renderMonitorSignal(o.code, o.action)}</td>
            <td>${rValue}</td>
            <td><button class="delete-monitor-btn" data-id="${o.order_id}" title="刪除"><i class="fa-regular fa-trash-can"></i></button></td>`;
        tr.querySelector(".delete-monitor-btn").addEventListener("click", () => handleDeleteMonitor(o.order_id, o.name, o.code));
        tr.querySelector(".toggle-buy-btn").addEventListener("click", async e => {
            e.stopPropagation();
            const nextAction = o.action === "BUY" ? "NOT_BUY" : "BUY";
            const response = await fetch(`${API_BASE}/sinopac/orders/${o.order_id}/toggle-action`, {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({action: nextAction})
            });
            if (response.ok) {
                showToast(nextAction === "BUY" ? "已切換為已買入" : "已切換為未買入", "success");
                fetchAndRenderMonitors();
            } else {
                showToast("切換狀態失敗", "danger");
            }
        });
        usMonitorsTableBody.appendChild(tr);
        const nextOrder = sortedOrders[orderIndex + 1];
        if (!nextOrder || nextOrder.action !== o.action) {
            const groupOrders = sortedOrders.filter(item => item.action === o.action);
            const subtotal = groupOrders.reduce((sum, item) => sum + Number(item.buy_price || 0) * Number(item.quantity || 0), 0);
            const subtotalRow = document.createElement("tr");
            subtotalRow.className = `monitor-subtotal-row ${o.action === "BUY" ? "bought" : "pending"} us`;
            subtotalRow.innerHTML = `<td colspan="2">${o.action === "BUY" ? "已買入" : "未買入"}合計</td><td class="monitor-cost-cell"><strong>US$ ${subtotal.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></td><td colspan="6"></td>`;
            usMonitorsTableBody.appendChild(subtotalRow);
        }
    });
    usMonitorsTableBody.querySelectorAll(".editable-price").forEach(el => {
        el.addEventListener("click", async e => {
            e.stopPropagation();
            const value = parseFloat(prompt("請輸入新買入價（美元）：", Number(el.dataset.price).toFixed(2)));
            if (value > 0) {
                const qty = Number(el.nextElementSibling.dataset.qty);
                await updateOrderPriceQty(el.dataset.id, value, qty);
            }
        });
    });
    usMonitorsTableBody.querySelectorAll(".editable-qty").forEach(el => {
        el.addEventListener("click", async e => {
            e.stopPropagation();
            const value = Math.floor(Number(prompt("請輸入新買入股數：", el.dataset.qty)));
            if (value > 0) {
                const price = Number(el.previousElementSibling.dataset.price);
                await updateOrderPriceQty(el.dataset.id, price, value);
            }
        });
    });
    bindEditableRiskPrices(usMonitorsTableBody);
}

// Handle Trailing Stop logic
async function handleTrailingStopTrigger(e) {
    if (e.currentTarget.classList.contains("disabled")) return;
    const oStr = e.currentTarget.getAttribute("data-order");
    if (!oStr) return;
    const o = JSON.parse(oStr);
    
    e.currentTarget.disabled = true;
    e.currentTarget.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i>`;
    
    try {
        const res = await fetch(`${API_BASE}/stocks/${o.code}/quote`);
        const quote = await res.json();
        
        if (!quote || quote.error) {
            showToast("無法獲取最新報價，請稍後再試", "error");
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
            return;
        }
        
        const openPrice = quote.open;
        const refPrice = quote.reference;
        const currentPrice = quote.close;
        
        const risePercent = refPrice ? (currentPrice - refPrice) / refPrice : 0;
        const buyRisePercent = o.buy_price ? (currentPrice - o.buy_price) / o.buy_price : 0;
        const qualifiesByReference = risePercent > 0.05;
        const qualifiesByBuyPrice = buyRisePercent >= 0.10;
        
        if (!qualifiesByReference && !qualifiesByBuyPrice) {
            showToast(`未達條件：參考價漲幅 ${(risePercent*100).toFixed(2)}%，買入價漲幅 ${(buyRisePercent*100).toFixed(2)}%`, "warning");
            e.currentTarget.disabled = true;
            e.currentTarget.title = `需參考價漲幅 > 5%，或買入價漲幅 ≥ 10%`;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up" style="opacity: 0.5;"></i> 未達條件`;
            return;
        }
        
        const movementBasePrice = qualifiesByBuyPrice ? o.buy_price : refPrice;
        const increaseAmount = currentPrice - movementBasePrice;
        const halfIncrease = increaseAmount / 2;
        
        const newStopLoss = o.stop_loss_price + halfIncrease;
        const newTakeProfit = o.stop_profit_price + halfIncrease;
        
        let stopLossInput = prompt(`請確認或修改移動停損價格：`, newStopLoss.toFixed(2));
        if (stopLossInput === null) {
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
            return;
        }
        const userStopLoss = parseFloat(stopLossInput);
        if (isNaN(userStopLoss) || userStopLoss <= 0) {
            showToast("請輸入有效的停損價格", "error");
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
            return;
        }

        let takeProfitInput = prompt(`請確認或修改移動停利價格：`, newTakeProfit.toFixed(2));
        if (takeProfitInput === null) {
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
            return;
        }
        const userTakeProfit = parseFloat(takeProfitInput);
        if (isNaN(userTakeProfit) || userTakeProfit <= 0) {
            showToast("請輸入有效的停利價格", "error");
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
            return;
        }
        
        const saveRes = await fetch(`${API_BASE}/sinopac/orders/${o.order_id}/move-to-trailing`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                stop_loss_price: userStopLoss,
                stop_profit_price: userTakeProfit,
                trailing_reference: currentPrice
            })
        });
        
        if (saveRes.ok) {
            showToast(`已移到移動停損停利 (停損/停利皆上移 $${halfIncrease.toFixed(2)})`, "success");
            fetchAndRenderMonitors();
        } else {
            showToast("加入移動停損停利失敗", "error");
            e.currentTarget.disabled = false;
            e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
        }
    } catch (err) {
        console.error(err);
        showToast("處理移動停損停利時發生錯誤", "error");
        e.currentTarget.disabled = false;
        e.currentTarget.innerHTML = `<i class="fa-solid fa-money-bill-trend-up"></i>`;
    }
}

// Cancel Monitor Action Handler
async function handleCancelMonitor(code, name) {
    if (!confirm(`確定要取消對 ${name} (${code}) 的模擬停損停利自動風控監控嗎？`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/sinopac/orders/${code}/cancel`, { method: "POST" });
        const data = await response.json();
        if (response.ok) {
            showToast(`已成功取消對 ${name} (${code}) 的風控監控`, "success");
            await fetchAndRenderMonitors();
            await saveStocksToStorage();
        } else {
            showToast(data.detail || "取消監控失敗", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗，請檢查後端狀態。", "danger");
    }
}

// Delete Monitor Record Action Handler
async function handleDeleteMonitor(orderId, name, code) {
    if (!confirm(`確定要刪除對 ${name} (${code}) 的模擬交易歷史紀錄嗎？`)) return;
    
    try {
        const response = await fetch(`${API_BASE}/sinopac/orders/${orderId}`, { method: "DELETE" });
        const data = await response.json();
        if (response.ok) {
            showToast(`已成功刪除 ${name} (${code}) 的模擬交易歷史紀錄`, "success");
            await fetchAndRenderMonitors();
            await saveStocksToStorage();
        } else {
            showToast(data.detail || "刪除紀錄失敗", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗，請檢查後端狀態。", "danger");
    }
}

// Place Simulated Order Action Handler
async function handlePlaceOrder() {
    if (!selectedStock) {
        showToast("請先選擇一檔股票", "danger");
        return;
    }
    
    const amount = parseFloat(investmentAmountInput.value) || 0;
    const oddShareCount = parseInt(oddShareCountInput ? oddShareCountInput.value : "0", 10) || 0;
    const tradeType = tradeTypeSelect.value;
    const price = parseFloat(targetBuyPriceInput.value) || selectedStock.current_price;
    const stopLossPct = parseFloat(stopLossPctInput.value) || 5;
    
    const stopLoss = Math.round(price * (1 - stopLossPct / 100) * 100) / 100;
    const stopProfit = selectedStock.prev_high || (price * 1.1);
    
    let shares = 0;
    let confirmSharesText = "";
    if (tradeType === "ROUND") {
        const lots = Math.floor(amount);
        shares = lots * 1000;
        confirmSharesText = `${lots} 張 (${shares.toLocaleString()} 股)`;
    } else {
        shares = oddShareCount > 0 ? oddShareCount : Math.floor(amount / price);
        confirmSharesText = `${shares.toLocaleString()} 股`;
    }
    
    if (shares <= 0) {
        showToast("委託股數必須大於 0，請調整投入金額", "danger");
        return;
    }
    
    const lot_text = tradeType === "ROUND" ? "整股" : "零股";
    const confirmMsg = `確定要新增模擬 ${lot_text} 風控單嗎？（預設：未買入）\n\n` +
                       `股票：${selectedStock.name} (${selectedStock.code})\n` +
                       `限價價格：$${price.toFixed(2)}\n` +
                       `數量：${confirmSharesText}\n` +
                       `停損比例：${stopLossPct}%\n` +
                       `停損觸發設定：$${stopLoss.toFixed(2)}\n` +
                       `停利觸發設定：$${stopProfit.toFixed(2)}`;
                       
    if (!confirm(confirmMsg)) return;
    
    btnSubmitOrder.disabled = true;
    btnSubmitOrder.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> 新增風控單中...`;
    
    try {
        const response = await fetch(`${API_BASE}/sinopac/order`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                code: selectedStock.code,
                action: "NOT_BUY",
                price: price,
                quantity: shares,
                stop_loss_price: stopLoss,
                stop_profit_price: stopProfit,
                lot_type: tradeType,
                dry_run: true,
                market: selectedStock.market === "US" ? "US" : "TW"
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showToast(data.message || "模擬委託成功！已啟動風控監控。", "success");
            await fetchAndRenderMonitors();
        } else {
            showToast(data.detail || "委託失敗", "danger");
        }
    } catch (e) {
        showToast("伺服器連線失敗，請檢查後端狀態。", "danger");
        console.error(e);
    } finally {
        btnSubmitOrder.disabled = false;
        btnSubmitOrder.innerHTML = `<i class="fa-solid fa-paper-plane" style="margin-right: 6px;"></i> 新增未買入風控單`;
    }
}

async function updateOrderPriceQty(orderId, price, quantity) {
    try {
        const response = await fetch(`${API_BASE}/sinopac/orders/${orderId}/update`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ buy_price: price, quantity: quantity })
        });
        const data = await response.json();
        if (response.ok) {
            showToast("成功更新監控價格與數量！", "success");
            await fetchAndRenderMonitors();
        } else {
            showToast(data.detail || "更新失敗", "danger");
        }
    } catch (e) {
        console.error(e);
        showToast("連線伺服器失敗", "danger");
    }
}

function bindEditableRiskPrices(container) {
    if (!container) return;
    container.querySelectorAll(".editable-risk-price").forEach(el => {
        el.addEventListener("click", async (event) => {
            event.stopPropagation();
            const field = el.dataset.field;
            const currentValue = Number(el.dataset.value);
            const label = field === "stop_loss_price" ? "停損價" : "停利價";
            const input = prompt(`請輸入新的${label}：`, currentValue.toFixed(2));
            if (input === null) return;

            const newValue = Number(input);
            if (!Number.isFinite(newValue) || newValue <= 0) {
                showToast(`請輸入有效的${label}`, "danger");
                return;
            }

            const payload = {};
            payload[field] = newValue;
            try {
                const response = await fetch(`${API_BASE}/sinopac/orders/${el.dataset.id}/update`, {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await response.json();
                if (!response.ok) {
                    showToast(data.detail || `${label}修改失敗`, "danger");
                    return;
                }
                showToast(`${label}已更新，風報比已重新計算`, "success");
                await fetchAndRenderMonitors();
            } catch (error) {
                console.error(error);
                showToast(`${label}修改失敗`, "danger");
            }
        });
    });
}
