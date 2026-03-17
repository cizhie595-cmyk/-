/**
 * Amazon Visionary Sourcing Tool - Background Service Worker
 * 对应 PRD 3.1.2 - Chrome 插件 (Manifest V3)
 *
 * 功能:
 * 1. 管理与 Web 端的 WebSocket 连接
 * 2. 接收 content script 提取的数据
 * 3. 转发数据到 Web 端 API
 */

// ============================================================
// 配置
// ============================================================
const DEFAULT_API_BASE = "http://localhost:5000";
const WS_RECONNECT_INTERVAL = 5000;

let apiBase = DEFAULT_API_BASE;
let authToken = null;
let wsConnection = null;

// ============================================================
// 初始化
// ============================================================
chrome.runtime.onInstalled.addListener(async () => {
    console.log("[Background] Extension installed");

    // 从 storage 恢复配置
    const stored = await chrome.storage.local.get(["apiBase", "authToken"]);
    if (stored.apiBase) apiBase = stored.apiBase;
    if (stored.authToken) authToken = stored.authToken;
});

// ============================================================
// 消息处理 (来自 content script 和 popup)
// ============================================================
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    switch (message.type) {
        case "PRODUCT_DATA":
            handleProductData(message.data, sender.tab);
            sendResponse({ success: true });
            break;

        case "SEARCH_RESULTS":
            handleSearchResults(message.data, sender.tab);
            sendResponse({ success: true });
            break;

        case "SET_CONFIG":
            handleSetConfig(message.data);
            sendResponse({ success: true });
            break;

        case "GET_STATUS":
            sendResponse({
                connected: !!authToken,
                apiBase: apiBase,
            });
            break;

        case "LOGIN":
            handleLogin(message.data).then(sendResponse);
            return true; // 异步响应

        default:
            sendResponse({ success: false, error: "Unknown message type" });
    }
});

// ============================================================
// 数据处理
// ============================================================

/**
 * 处理从产品详情页提取的数据
 */
async function handleProductData(data, tab) {
    console.log("[Background] Received product data:", data.asin);

    // 发送到 Web 端 API
    try {
        const response = await fetch(`${apiBase}/api/v1/extension/product`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                asin: data.asin,
                title: data.title,
                price: data.price,
                rating: data.rating,
                review_count: data.reviewCount,
                bsr: data.bsr,
                brand: data.brand,
                images: data.images,
                variants: data.variants,
                hidden_data: data.hiddenData,
                page_url: tab?.url,
                extracted_at: new Date().toISOString(),
            }),
        });

        if (response.ok) {
            // 通知 content script 数据已同步
            chrome.tabs.sendMessage(tab.id, {
                type: "SYNC_SUCCESS",
                asin: data.asin,
            });
        }
    } catch (error) {
        console.error("[Background] Failed to sync product data:", error);
    }
}

/**
 * 处理从搜索结果页提取的数据
 */
async function handleSearchResults(data, tab) {
    console.log("[Background] Received search results:", data.keyword);

    try {
        await fetch(`${apiBase}/api/v1/extension/search-results`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`,
            },
            body: JSON.stringify({
                keyword: data.keyword,
                page: data.page,
                products: data.products,
                total_results: data.totalResults,
                page_url: tab?.url,
                extracted_at: new Date().toISOString(),
            }),
        });
    } catch (error) {
        console.error("[Background] Failed to sync search results:", error);
    }
}

// ============================================================
// 配置管理
// ============================================================

function handleSetConfig(config) {
    if (config.apiBase) {
        apiBase = config.apiBase;
        chrome.storage.local.set({ apiBase });
    }
    if (config.authToken) {
        authToken = config.authToken;
        chrome.storage.local.set({ authToken });
    }
}

async function handleLogin(credentials) {
    try {
        const response = await fetch(`${apiBase}/api/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(credentials),
        });

        const result = await response.json();

        if (result.success && result.data?.access_token) {
            authToken = result.data.access_token;
            chrome.storage.local.set({ authToken });
            return { success: true };
        } else {
            return { success: false, error: result.message || "登录失败" };
        }
    } catch (error) {
        return { success: false, error: error.message };
    }
}
