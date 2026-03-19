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

    let currentTimeRange = 'today';
    let miniCharts = {};

    function loadDailyStats(stats) {
        if (!stats || stats.date !== getTodayStr()) {
            stats = { date: getTodayStr(), captured: 0, analyzed: 0, tracked: 0 };
            chrome.storage.local.set({ dailyStats: stats });
        }
        // 保存到历史记录
        saveDailyToHistory(stats);
        // 显示当前范围的统计
        displayStatsForRange(currentTimeRange);
    }

    function saveDailyToHistory(todayStats) {
        chrome.storage.local.get(["statsHistory"], (result) => {
            let history = result.statsHistory || {};
            const today = getTodayStr();
            history[today] = {
                captured: todayStats.captured || 0,
                analyzed: todayStats.analyzed || 0,
                tracked: todayStats.tracked || 0
            };
            // 只保留最近 90 天
            const keys = Object.keys(history).sort();
            if (keys.length > 90) {
                keys.slice(0, keys.length - 90).forEach(k => delete history[k]);
            }
            chrome.storage.local.set({ statsHistory: history });
        });
    }

    function switchTimeRange(range) {
        currentTimeRange = range;
        // 更新按钮状态
        document.querySelectorAll('.time-toggle-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.range === range);
        });
        // 更新标签文字
        const labels = {
            today: { captured: '今日采集', analyzed: '今日分析', tracked: '今日追踪' },
            week: { captured: '本周采集', analyzed: '本周分析', tracked: '本周追踪' },
            month: { captured: '本月采集', analyzed: '本月分析', tracked: '本月追踪' }
        };
        const l = labels[range];
        const labelCaptured = document.getElementById('label-captured');
        const labelAnalyzed = document.getElementById('label-analyzed');
        const labelTracked = document.getElementById('label-tracked');
        if (labelCaptured) labelCaptured.textContent = l.captured;
        if (labelAnalyzed) labelAnalyzed.textContent = l.analyzed;
        if (labelTracked) labelTracked.textContent = l.tracked;

        displayStatsForRange(range);
    }
    // 暴露到全局作用域
    window.switchTimeRange = switchTimeRange;

    function displayStatsForRange(range) {
        chrome.storage.local.get(["statsHistory", "dailyStats"], (result) => {
            const history = result.statsHistory || {};
            const todayStats = result.dailyStats || { date: getTodayStr(), captured: 0, analyzed: 0, tracked: 0 };
            const today = getTodayStr();

            // 确保今天的数据在 history 中
            history[today] = {
                captured: todayStats.captured || 0,
                analyzed: todayStats.analyzed || 0,
                tracked: todayStats.tracked || 0
            };

            let dates = [];
            const now = new Date();

            if (range === 'today') {
                dates = [today];
            } else if (range === 'week') {
                for (let i = 6; i >= 0; i--) {
                    const d = new Date(now);
                    d.setDate(d.getDate() - i);
                    dates.push(d.toISOString().slice(0, 10));
                }
            } else if (range === 'month') {
                for (let i = 29; i >= 0; i--) {
                    const d = new Date(now);
                    d.setDate(d.getDate() - i);
                    dates.push(d.toISOString().slice(0, 10));
                }
            }

            // 聚合数据
            let totalCaptured = 0, totalAnalyzed = 0, totalTracked = 0;
            const chartData = { captured: [], analyzed: [], tracked: [] };

            dates.forEach(date => {
                const dayData = history[date] || { captured: 0, analyzed: 0, tracked: 0 };
                totalCaptured += dayData.captured;
                totalAnalyzed += dayData.analyzed;
                totalTracked += dayData.tracked;
                chartData.captured.push(dayData.captured);
                chartData.analyzed.push(dayData.analyzed);
                chartData.tracked.push(dayData.tracked);
            });

            // 动画更新数值
            animateValue('stat-captured', totalCaptured);
            animateValue('stat-analyzed', totalAnalyzed);
            animateValue('stat-tracked', totalTracked);

            // 更新总计
            const summaryTotal = document.getElementById('summary-total');
            if (summaryTotal) {
                summaryTotal.textContent = totalCaptured + totalAnalyzed + totalTracked;
            }

            // 计算趋势（与前一个周期对比）
            if (range !== 'today') {
                updateTrend('trend-captured', chartData.captured);
                updateTrend('trend-analyzed', chartData.analyzed);
                updateTrend('trend-tracked', chartData.tracked);
            } else {
                ['trend-captured', 'trend-analyzed', 'trend-tracked'].forEach(id => {
                    const el = document.getElementById(id);
                    if (el) { el.textContent = '-'; el.className = 'stat-trend flat'; }
                });
            }

            // 绘制迷你图表（仅周/月视图）
            if (range !== 'today' && dates.length > 1) {
                drawMiniChart('chart-captured', chartData.captured, '#667eea');
                drawMiniChart('chart-analyzed', chartData.analyzed, '#f59e0b');
                drawMiniChart('chart-tracked', chartData.tracked, '#3b82f6');
            } else {
                // 隐藏图表
                ['chart-captured', 'chart-analyzed', 'chart-tracked'].forEach(id => {
                    const canvas = document.getElementById(id);
                    if (canvas) {
                        const ctx = canvas.getContext('2d');
                        ctx.clearRect(0, 0, canvas.width, canvas.height);
                    }
                });
            }
        });
    }

    function animateValue(elementId, targetValue) {
        const el = document.getElementById(elementId);
        if (!el) return;
        const currentValue = parseInt(el.textContent) || 0;
        if (currentValue === targetValue) return;

        el.classList.add('animating');
        const duration = 300;
        const startTime = Date.now();

        function update() {
            const elapsed = Date.now() - startTime;
            const progress = Math.min(elapsed / duration, 1);
            // Ease out cubic
            const eased = 1 - Math.pow(1 - progress, 3);
            const current = Math.round(currentValue + (targetValue - currentValue) * eased);
            el.textContent = current;

            if (progress < 1) {
                requestAnimationFrame(update);
            } else {
                el.classList.remove('animating');
            }
        }
        requestAnimationFrame(update);
    }

    function updateTrend(elementId, dataPoints) {
        const el = document.getElementById(elementId);
        if (!el || dataPoints.length < 2) return;

        const mid = Math.floor(dataPoints.length / 2);
        const firstHalf = dataPoints.slice(0, mid).reduce((a, b) => a + b, 0);
        const secondHalf = dataPoints.slice(mid).reduce((a, b) => a + b, 0);

        if (secondHalf > firstHalf) {
            const pct = firstHalf > 0 ? Math.round(((secondHalf - firstHalf) / firstHalf) * 100) : 100;
            el.textContent = '+' + pct + '%';
            el.className = 'stat-trend up';
        } else if (secondHalf < firstHalf) {
            const pct = firstHalf > 0 ? Math.round(((firstHalf - secondHalf) / firstHalf) * 100) : 0;
            el.textContent = '-' + pct + '%';
            el.className = 'stat-trend down';
        } else {
            el.textContent = '0%';
            el.className = 'stat-trend flat';
        }
    }

    function drawMiniChart(canvasId, data, color) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const w = canvas.parentElement.clientWidth || 140;
        const h = 30;
        canvas.width = w * 2; // Retina
        canvas.height = h * 2;
        canvas.style.width = w + 'px';
        canvas.style.height = h + 'px';
        ctx.scale(2, 2);

        ctx.clearRect(0, 0, w, h);

        if (data.length < 2) return;

        const max = Math.max(...data, 1);
        const padding = 2;
        const stepX = (w - padding * 2) / (data.length - 1);

        // 绘制渐变填充
        const gradient = ctx.createLinearGradient(0, 0, 0, h);
        gradient.addColorStop(0, color + '40');
        gradient.addColorStop(1, color + '05');

        ctx.beginPath();
        ctx.moveTo(padding, h);
        data.forEach((val, i) => {
            const x = padding + i * stepX;
            const y = h - padding - ((val / max) * (h - padding * 2));
            if (i === 0) ctx.lineTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.lineTo(padding + (data.length - 1) * stepX, h);
        ctx.closePath();
        ctx.fillStyle = gradient;
        ctx.fill();

        // 绘制线条
        ctx.beginPath();
        data.forEach((val, i) => {
            const x = padding + i * stepX;
            const y = h - padding - ((val / max) * (h - padding * 2));
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        });
        ctx.strokeStyle = color;
        ctx.lineWidth = 1.5;
        ctx.lineJoin = 'round';
        ctx.stroke();

        // 绘制最后一个点
        const lastX = padding + (data.length - 1) * stepX;
        const lastY = h - padding - ((data[data.length - 1] / max) * (h - padding * 2));
        ctx.beginPath();
        ctx.arc(lastX, lastY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.lineWidth = 1;
        ctx.stroke();
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
