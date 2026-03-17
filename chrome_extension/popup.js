/**
 * Amazon Visionary Sourcing Tool - Popup Script
 */

document.addEventListener("DOMContentLoaded", async () => {
    const statusDot = document.getElementById("statusDot");
    const statusText = document.getElementById("statusText");
    const apiBaseInput = document.getElementById("apiBase");
    const usernameInput = document.getElementById("username");
    const passwordInput = document.getElementById("password");
    const loginBtn = document.getElementById("loginBtn");
    const saveConfigBtn = document.getElementById("saveConfigBtn");
    const messageEl = document.getElementById("message");

    // 加载已保存的配置
    const stored = await chrome.storage.local.get(["apiBase", "authToken"]);
    if (stored.apiBase) {
        apiBaseInput.value = stored.apiBase;
    }

    // 检查连接状态
    chrome.runtime.sendMessage({ type: "GET_STATUS" }, (response) => {
        if (response?.connected) {
            statusDot.classList.add("connected");
            statusText.textContent = "已连接到 " + (response.apiBase || "服务器");
        } else {
            statusText.textContent = "未连接";
        }
    });

    // 保存配置
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

    // 登录
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
            } else {
                showMessage(response?.error || "登录失败", "error");
            }
        });
    });

    function showMessage(text, type) {
        messageEl.textContent = text;
        messageEl.className = "message " + type;
        setTimeout(() => {
            messageEl.className = "message";
        }, 3000);
    }
});
