/**
 * Coupang 选品系统 - AI 模型配置页面交互逻辑
 *
 * 功能:
 *   1. 加载服务商列表 → 填充下拉菜单
 *   2. 加载用户已保存的配置 → 回填表单
 *   3. 切换服务商 → 自动填充 Base URL 和模型列表
 *   4. 保存配置 → POST /api/ai/settings
 *   5. 测试连接 → POST /api/ai/test-direct
 *   6. 粘贴/复制 API Key 按钮交互
 */

// ============================================================
// 全局变量
// ============================================================
const API_BASE = "";  // 同域，留空即可
let providersData = [];
let currentSettings = null;

// ============================================================
// 工具函数
// ============================================================

/**
 * 获取 JWT Token（从 localStorage）
 */
function getToken() {
    return localStorage.getItem("access_token") || "";
}

/**
 * 带认证的 fetch 请求
 */
async function authFetch(url, options = {}) {
    const token = getToken();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {}),
    };
    if (token) {
        headers["Authorization"] = `Bearer ${token}`;
    }
    return fetch(API_BASE + url, { ...options, headers });
}

/**
 * 设置按钮加载状态
 */
function setButtonLoading(btn, loading) {
    if (loading) {
        btn.classList.add("loading");
        btn.disabled = true;
    } else {
        btn.classList.remove("loading");
        btn.disabled = false;
    }
}

// ============================================================
// 1. 加载服务商列表
// ============================================================
async function loadProviders() {
    try {
        const resp = await fetch(API_BASE + "/api/ai/providers");
        const data = await resp.json();

        if (data.success) {
            providersData = data.data;
            const select = document.getElementById("provider");
            select.innerHTML = "";

            providersData.forEach(p => {
                const opt = document.createElement("option");
                opt.value = p.id;
                opt.textContent = p.name;
                select.appendChild(opt);
            });

            // 默认选中第一个
            if (providersData.length > 0) {
                onProviderChange(providersData[0].id);
            }
        }
    } catch (e) {
        console.error("加载服务商列表失败:", e);
        showToast("加载服务商列表失败", "error");
    }
}

// ============================================================
// 2. 加载用户已保存的配置
// ============================================================
async function loadCurrentSettings() {
    try {
        const resp = await authFetch("/api/ai/settings");
        const data = await resp.json();

        if (data.success && data.data) {
            currentSettings = data.data;
            fillFormWithSettings(currentSettings);
            updateStatusCard(currentSettings);
        }
    } catch (e) {
        console.error("加载配置失败:", e);
    }
}

/**
 * 将已保存的配置回填到表单
 */
function fillFormWithSettings(settings) {
    if (settings.provider) {
        document.getElementById("provider").value = settings.provider;
        onProviderChange(settings.provider);
    }

    // API Key 显示脱敏版本
    if (settings.api_key_masked) {
        document.getElementById("apiKey").value = "";
        document.getElementById("apiKey").placeholder = `已配置: ${settings.api_key_masked}（重新输入可覆盖）`;
    }

    if (settings.base_url) {
        document.getElementById("baseUrl").value = settings.base_url;
    }

    if (settings.model) {
        document.getElementById("model").value = settings.model;
    }

    if (settings.temperature !== undefined) {
        document.getElementById("temperature").value = settings.temperature;
        document.getElementById("temperatureRange").value = settings.temperature;
    }

    if (settings.max_tokens !== undefined) {
        document.getElementById("maxTokens").value = settings.max_tokens;
    }
}

/**
 * 更新状态卡片
 */
function updateStatusCard(settings) {
    const dot = document.querySelector("#statusIndicator .status-dot");
    const text = document.querySelector("#statusIndicator .status-text");
    const details = document.getElementById("statusDetails");

    if (!settings.configured) {
        dot.className = "status-dot unconfigured";
        text.textContent = "未配置";
        details.innerHTML = "<p>尚未配置 AI 模型，请在下方填写您的 API Key 并保存。</p>";
        return;
    }

    if (settings.test_status === "success") {
        dot.className = "status-dot success";
        text.textContent = "已连接";
        const provider = providersData.find(p => p.id === settings.provider);
        const providerName = provider ? provider.name : settings.provider;
        details.innerHTML = `<p>当前使用 <strong>${providerName}</strong> 的 <strong>${settings.model}</strong> 模型。API Key: ${settings.api_key_masked || "已配置"}</p>`;
    } else if (settings.test_status === "failed") {
        dot.className = "status-dot failed";
        text.textContent = "连接失败";
        details.innerHTML = `<p>上次测试失败，请检查 API Key 和网络连接。</p>`;
    } else {
        dot.className = "status-dot unconfigured";
        text.textContent = "待测试";
        details.innerHTML = `<p>配置已保存但尚未测试，建议点击"测试连接"验证。</p>`;
    }
}

// ============================================================
// 3. 切换服务商
// ============================================================
function onProviderChange(providerId) {
    const provider = providersData.find(p => p.id === providerId);
    if (!provider) return;

    // 更新 Base URL 提示
    const baseUrlInput = document.getElementById("baseUrl");
    const baseUrlHint = document.getElementById("baseUrlHint");

    if (provider.default_base_url) {
        baseUrlInput.placeholder = provider.default_base_url;
        baseUrlHint.textContent = `默认地址: ${provider.default_base_url}。如需使用代理，请填写自定义地址。`;
    } else {
        baseUrlInput.placeholder = "请输入 API 地址";
        baseUrlHint.textContent = "自定义服务商需要手动填写完整的 API 地址。";
    }

    // 更新模型下拉列表
    const modelList = document.getElementById("modelList");
    modelList.innerHTML = "";
    provider.models.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        modelList.appendChild(opt);
    });

    // 如果当前模型输入框为空或不在新列表中，自动填充第一个
    const modelInput = document.getElementById("model");
    if (!modelInput.value || !provider.models.includes(modelInput.value)) {
        modelInput.value = provider.models[0] || "";
    }
}

// ============================================================
// 4. 保存配置
// ============================================================
async function saveSettings(e) {
    e.preventDefault();

    const btn = document.getElementById("btnSave");
    setButtonLoading(btn, true);

    const apiKey = document.getElementById("apiKey").value.trim();
    const provider = document.getElementById("provider").value;
    const baseUrl = document.getElementById("baseUrl").value.trim();
    const model = document.getElementById("model").value.trim();
    const temperature = parseFloat(document.getElementById("temperature").value) || 0.3;
    const maxTokens = parseInt(document.getElementById("maxTokens").value) || 4000;

    // 如果用户没有输入新的 API Key，且已有配置，则不传 api_key（保持旧值）
    const payload = { provider, base_url: baseUrl, model, temperature, max_tokens: maxTokens };
    if (apiKey) {
        payload.api_key = apiKey;
    } else if (!currentSettings || !currentSettings.configured) {
        showToast("请输入 API Key", "error");
        setButtonLoading(btn, false);
        return;
    }

    try {
        const resp = await authFetch("/api/ai/settings", {
            method: "POST",
            body: JSON.stringify(payload),
        });
        const data = await resp.json();

        if (data.success) {
            showToast("配置保存成功", "success");
            currentSettings = data.data;
            fillFormWithSettings(currentSettings);
            updateStatusCard(currentSettings);
        } else {
            showToast(data.message || "保存失败", "error");
        }
    } catch (e) {
        showToast("网络错误，请稍后重试", "error");
    } finally {
        setButtonLoading(btn, false);
    }
}

// ============================================================
// 5. 测试连接
// ============================================================
async function testConnection() {
    const btn = document.getElementById("btnTestDirect");
    setButtonLoading(btn, true);

    const resultCard = document.getElementById("testResultCard");
    const resultContent = document.getElementById("testResultContent");
    resultCard.style.display = "block";
    resultContent.className = "test-result-content";
    resultContent.textContent = "正在测试连接，请稍候...";

    const apiKey = document.getElementById("apiKey").value.trim();
    const provider = document.getElementById("provider").value;
    const baseUrl = document.getElementById("baseUrl").value.trim();
    const model = document.getElementById("model").value.trim();

    // 如果用户没有输入新的 key，使用已保存的配置测试
    let url, payload;
    if (apiKey) {
        url = "/api/ai/test-direct";
        payload = { provider, api_key: apiKey, base_url: baseUrl, model };
    } else if (currentSettings && currentSettings.configured) {
        url = "/api/ai/test";
        payload = {};
    } else {
        resultContent.className = "test-result-content failed";
        resultContent.textContent = "请先输入 API Key";
        setButtonLoading(btn, false);
        return;
    }

    try {
        const resp = await authFetch(url, {
            method: "POST",
            body: JSON.stringify(payload),
        });
        const data = await resp.json();

        if (data.success) {
            resultContent.className = "test-result-content success";
            resultContent.textContent = data.message;
            showToast("连接测试成功", "success");
        } else {
            resultContent.className = "test-result-content failed";
            resultContent.textContent = data.message;
            showToast("连接测试失败", "error");
        }
    } catch (e) {
        resultContent.className = "test-result-content failed";
        resultContent.textContent = "网络错误，无法连接到服务器";
        showToast("网络错误", "error");
    } finally {
        setButtonLoading(btn, false);
    }
}

// ============================================================
// 6. API Key 特殊按钮交互
// ============================================================
function initApiKeyButtons() {
    // 显示/隐藏 API Key
    const toggleBtn = document.getElementById("toggleKeyVisibility");
    const apiKeyInput = document.getElementById("apiKey");

    toggleBtn.addEventListener("click", () => {
        if (apiKeyInput.type === "password") {
            apiKeyInput.type = "text";
        } else {
            apiKeyInput.type = "password";
        }
    });

    // 粘贴 API Key
    document.getElementById("pasteKey").addEventListener("click", async () => {
        await ClipboardUtil.pasteToInput(apiKeyInput);
    });

    // 复制 API Key
    document.getElementById("copyKey").addEventListener("click", async () => {
        if (apiKeyInput.value) {
            await ClipboardUtil.copyFromInput(apiKeyInput);
        } else {
            showToast("API Key 为空，无法复制", "error");
        }
    });
}

// ============================================================
// 7. Temperature 滑块同步
// ============================================================
function initTemperatureSync() {
    const range = document.getElementById("temperatureRange");
    const number = document.getElementById("temperature");

    range.addEventListener("input", () => {
        number.value = range.value;
    });

    number.addEventListener("input", () => {
        range.value = number.value;
    });
}

// ============================================================
// 初始化
// ============================================================
document.addEventListener("DOMContentLoaded", async () => {
    // 初始化各交互
    initApiKeyButtons();
    initTemperatureSync();

    // 服务商切换事件
    document.getElementById("provider").addEventListener("change", (e) => {
        onProviderChange(e.target.value);
    });

    // 表单提交
    document.getElementById("aiConfigForm").addEventListener("submit", saveSettings);

    // 测试连接按钮
    document.getElementById("btnTestDirect").addEventListener("click", testConnection);

    // 加载数据
    await loadProviders();
    await loadCurrentSettings();
});
