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

// ============================================================
// WebSocket 通信 (PRD 3.1.2)
// Web端通过 WebSocket 向插件发送指令
// ============================================================

let wsReconnectTimer = null;

function connectWebSocket() {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) return;
    if (!authToken) return;

    const wsUrl = apiBase.replace(/^http/, 'ws') + '/ws/extension';
    console.log('[Background] Connecting WebSocket:', wsUrl);

    try {
        wsConnection = new WebSocket(wsUrl);

        wsConnection.onopen = () => {
            console.log('[Background] WebSocket connected');
            // 认证
            wsConnection.send(JSON.stringify({
                type: 'AUTH',
                token: authToken,
            }));
            // 清除重连定时器
            if (wsReconnectTimer) {
                clearInterval(wsReconnectTimer);
                wsReconnectTimer = null;
            }
        };

        wsConnection.onmessage = (event) => {
            try {
                const msg = JSON.parse(event.data);
                handleWebSocketMessage(msg);
            } catch (e) {
                console.error('[Background] WS message parse error:', e);
            }
        };

        wsConnection.onclose = () => {
            console.log('[Background] WebSocket disconnected');
            wsConnection = null;
            // 自动重连
            if (!wsReconnectTimer) {
                wsReconnectTimer = setInterval(() => {
                    if (authToken) connectWebSocket();
                }, WS_RECONNECT_INTERVAL);
            }
        };

        wsConnection.onerror = (err) => {
            console.error('[Background] WebSocket error:', err);
            wsConnection.close();
        };
    } catch (e) {
        console.error('[Background] WebSocket connection failed:', e);
    }
}

/**
 * 处理来自 Web 端的 WebSocket 指令
 */
function handleWebSocketMessage(msg) {
    switch (msg.type) {
        case 'NAVIGATE':
            // Web端指示插件打开指定 URL
            chrome.tabs.create({ url: msg.url, active: msg.active !== false });
            break;

        case 'SCRAPE_PAGE':
            // Web端指示插件抽取当前页面数据
            chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
                if (tabs[0]) {
                    chrome.tabs.sendMessage(tabs[0].id, {
                        type: 'EXTRACT_DATA',
                        options: msg.options || {},
                    });
                }
            });
            break;

        case 'SCRAPE_ASIN':
            // Web端指示插件打开并抽取指定 ASIN
            const asinUrl = `https://www.amazon.com/dp/${msg.asin}`;
            chrome.tabs.create({ url: asinUrl, active: false }, (tab) => {
                // 等待页面加载完成后提取数据
                chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
                    if (tabId === tab.id && info.status === 'complete') {
                        chrome.tabs.onUpdated.removeListener(listener);
                        setTimeout(() => {
                            chrome.tabs.sendMessage(tab.id, {
                                type: 'EXTRACT_DATA',
                                options: { autoClose: true, taskId: msg.taskId },
                            });
                        }, 2000);
                    }
                });
            });
            break;

        case 'BATCH_SCRAPE':
            // 批量抽取多个 ASIN
            if (msg.asins && Array.isArray(msg.asins)) {
                msg.asins.forEach((asin, index) => {
                    setTimeout(() => {
                        handleWebSocketMessage({
                            type: 'SCRAPE_ASIN',
                            asin: asin,
                            taskId: msg.taskId,
                        });
                    }, index * 3000); // 每个间隔 3 秒
                });
            }
            break;

        case 'PING':
            if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
                wsConnection.send(JSON.stringify({ type: 'PONG' }));
            }
            break;

        default:
            console.log('[Background] Unknown WS message type:', msg.type);
    }
}

// 当认证成功后自动连接 WebSocket
chrome.storage.onChanged.addListener((changes) => {
    if (changes.authToken && changes.authToken.newValue) {
        authToken = changes.authToken.newValue;
        connectWebSocket();
    }
});

// 启动时尝试连接
chrome.runtime.onStartup.addListener(async () => {
    const stored = await chrome.storage.local.get(['apiBase', 'authToken']);
    if (stored.apiBase) apiBase = stored.apiBase;
    if (stored.authToken) {
        authToken = stored.authToken;
        connectWebSocket();
    }
});


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
