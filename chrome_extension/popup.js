/**
 * Amazon Visionary Sourcing Tool - Enhanced Popup Script v1.3.0
 * Features: Dashboard stats, capture history, quota display, quick actions
 */

document.addEventListener("DOMContentLoaded", async () => {
    // === DOM Elements ===
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const statusUser = document.getElementById("statusUser");
    const apiBaseInput = document.getElementById("apiBase");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginBtn = document.getElementById("loginBtn");
    const logoutBtn = document.getElementById("logoutBtn");
    const saveConfigBtn = document.getElementById("saveConfigBtn");
    const messageEl = document.getElementById("message");

    // Quick action buttons
    const btnCapture = document.getElementById("btn-capture");
    const btnAnalyze = document.getElementById("btn-analyze");
    const btnCompare = document.getElementById("btn-compare");
    const btnTrack = document.getElementById("btn-track");

    // === Tab Navigation ===
    document.querySelectorAll(".tab").forEach(tab => {
        tab.addEventListener("click", () => {
            document.querySelectorAll(".tab").forEach(t => t.classList.remove("active"));
            document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
            tab.classList.add("active");
            document.getElementById("panel-" + tab.dataset.tab).classList.add("active");
        });
    });

    // === Load Saved Config ===
    const stored = await chrome.storage.local.get([
        "apiBase", "authToken", "username", "captureHistory", "dailyStats"
    ]);

    if (stored.apiBase) {
        apiBaseInput.value = stored.apiBase;
    }

    // === Check Connection Status ===
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
        if (response?.connected) {
            statusDot.classList.add("connected");
            statusText.textContent = "已连接";
            if (response.username) {
                statusUser.textContent = response.username;
            }
            enableQuickActions(true);
            loadDashboardStats();
        } else {
            statusText.textContent = "未连接";
            enableQuickActions(false);
        }
    });

    // === Show Login/Logout State ===
    if (stored.authToken) {
        loginBtn.style.display = "none";
        logoutBtn.style.display = "block";
        if (stored.username) {
            statusUser.textContent = stored.username;
        }
    }

    // === Load Capture History ===
    loadCaptureHistory(stored.captureHistory || []);

    // === Load Daily Stats ===
    loadDailyStats(stored.dailyStats);

    // === Save Config ===
    saveConfigBtn.addEventListener("click", () => {
        const apiBase = apiBaseInput.value.trim();
        if (!apiBase) {
            showMessage("请输入 API 地址", "error");
            return;
        }
        chrome.runtime.sendMessage({
            type: "SET_CONFIG",
            data: { apiBase },
        }, () => {
            showMessage("配置已保存", "success");
        });
    });

    // === Login ===
    loginBtn.addEventListener("click", async () => {
        const username = usernameInput.value.trim();
        const password = passwordInput.value.trim();

        if (!username || !password) {
            showMessage("请输入用户名和密码", "error");
            return;
        }

        loginBtn.textContent = "登录中...";
        loginBtn.disabled = true;

        chrome.runtime.sendMessage({
            type: "LOGIN",
            data: { login_id: username, password },
        }, (response) => {
            loginBtn.textContent = "登录";
            loginBtn.disabled = false;

            if (response?.success) {
                showMessage("登录成功", "success");
                statusDot.classList.add("connected");
                statusText.textContent = "已连接";
                statusUser.textContent = username;
                loginBtn.style.display = "none";
                logoutBtn.style.display = "block";
                enableQuickActions(true);
                // Save username
                chrome.storage.local.set({ username });
                // Load stats after login
                loadDashboardStats();
            } else {
                showMessage(response?.error || "登录失败", "error");
            }
        });
    });

    // === Logout ===
    logoutBtn.addEventListener("click", () => {
        chrome.storage.local.remove(["authToken", "username"]);
        statusDot.classList.remove("connected");
        statusText.textContent = "未连接";
        statusUser.textContent = "";
        loginBtn.style.display = "block";
        logoutBtn.style.display = "none";
        enableQuickActions(false);
        showMessage("已退出登录", "success");
    });

    // === Quick Actions ===
    btnCapture.addEventListener("click", () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "CAPTURE_PAGE" }, (response) => {
                    if (response?.success) {
                        showMessage(`已采集: ${response.asin || "商品"}`, "success");
                        addToCaptureHistory(response.data);
                        incrementDailyStat("captured");
                    } else {
                        showMessage("采集失败: 请确认在商品详情页", "error");
                    }
                });
            }
        });
    });

    btnAnalyze.addEventListener("click", () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "AI_ANALYZE" }, (response) => {
                    if (response?.success) {
                        showMessage("AI 分析已提交", "success");
                        incrementDailyStat("analyzed");
                    } else {
                        showMessage(response?.error || "分析失败", "error");
                    }
                });
            }
        });
    });

    btnCompare.addEventListener("click", () => {
        chrome.runtime.sendMessage({ type: "OPEN_COMPARE" });
    });

    btnTrack.addEventListener("click", () => {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]) {
                chrome.tabs.sendMessage(tabs[0].id, { type: "TRACK_PRICE" }, (response) => {
                    if (response?.success) {
                        showMessage("已添加价格追踪", "success");
                        incrementDailyStat("tracked");
                    } else {
                        showMessage(response?.error || "追踪失败", "error");
                    }
                });
            }
        });
    });

    // === Helper Functions ===

    function showMessage(text, type) {
        messageEl.textContent = text;
        messageEl.className = "message " + type;
        setTimeout(() => {
            messageEl.className = "message";
        }, 3000);
    }

    function enableQuickActions(enabled) {
        [btnCapture, btnAnalyze, btnCompare, btnTrack].forEach(btn => {
            if (btn) btn.disabled = !enabled;
        });
    }

    function loadDashboardStats() {
        chrome.runtime.sendMessage({ type: "GET_STATS" }, (response) => {
            if (response) {
                document.getElementById("stat-projects").textContent = response.projects || 0;

                // Update quota
                const used = response.quotaUsed || 0;
                const total = response.quotaTotal || 1000;
                document.getElementById("quota-text").textContent = `${used} / ${total}`;
                document.getElementById("quota-fill").style.width =
                    Math.min((used / total) * 100, 100) + "%";
            }
        });
    }

    function loadDailyStats(stats) {
        if (!stats || stats.date !== getTodayStr()) {
            stats = { date: getTodayStr(), captured: 0, analyzed: 0, tracked: 0 };
            chrome.storage.local.set({ dailyStats: stats });
        }
        document.getElementById("stat-captured").textContent = stats.captured || 0;
        document.getElementById("stat-analyzed").textContent = stats.analyzed || 0;
        document.getElementById("stat-tracked").textContent = stats.tracked || 0;
    }

    function incrementDailyStat(key) {
        chrome.storage.local.get(["dailyStats"], (result) => {
            let stats = result.dailyStats || { date: getTodayStr(), captured: 0, analyzed: 0, tracked: 0 };
            if (stats.date !== getTodayStr()) {
                stats = { date: getTodayStr(), captured: 0, analyzed: 0, tracked: 0 };
            }
            stats[key] = (stats[key] || 0) + 1;
            chrome.storage.local.set({ dailyStats: stats });
            document.getElementById("stat-" + key).textContent = stats[key];
        });
    }

    function getTodayStr() {
        return new Date().toISOString().slice(0, 10);
    }

    function loadCaptureHistory(history) {
        const container = document.getElementById("history-list");
        if (!history || history.length === 0) {
            return; // Keep empty state
        }

        container.innerHTML = "";
        history.slice(0, 20).forEach(item => {
            const el = document.createElement("div");
            el.className = "history-item";
            el.innerHTML = `
                <img class="history-img" src="${item.image || ''}" alt="" onerror="this.style.display='none'">
                <div class="history-info">
                    <div class="history-title">${item.title || item.asin || 'Unknown'}</div>
                    <div class="history-meta">${item.asin || ''} &middot; ${item.time || ''}</div>
                </div>
                <div class="history-price">${item.price || ''}</div>
            `;
            el.addEventListener("click", () => {
                if (item.url) {
                    chrome.tabs.create({ url: item.url });
                }
            });
            container.appendChild(el);
        });
    }

    function addToCaptureHistory(data) {
        if (!data) return;
        chrome.storage.local.get(["captureHistory"], (result) => {
            const history = result.captureHistory || [];
            history.unshift({
                asin: data.asin,
                title: data.title,
                price: data.price,
                image: data.image,
                url: data.url,
                time: new Date().toLocaleTimeString(),
            });
            // Keep only last 50 items
            const trimmed = history.slice(0, 50);
            chrome.storage.local.set({ captureHistory: trimmed });
            loadCaptureHistory(trimmed);
        });
    }
});
