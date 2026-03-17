/**
 * Coupang 选品系统 - 全局剪贴板工具
 *
 * 为所有输入框和文本展示区提供一键复制/粘贴功能。
 * 使用 navigator.clipboard API，兼容降级到 execCommand。
 */

const ClipboardUtil = {
    /**
     * 复制文本到剪贴板
     * @param {string} text - 要复制的文本
     * @returns {Promise<boolean>}
     */
    async copy(text) {
        if (!text) return false;

        try {
            if (navigator.clipboard && navigator.clipboard.writeText) {
                await navigator.clipboard.writeText(text);
                return true;
            }
        } catch (e) {
            // 降级方案
        }

        // 降级: 使用 execCommand
        try {
            const textarea = document.createElement("textarea");
            textarea.value = text;
            textarea.style.cssText = "position:fixed;left:-9999px;top:-9999px;opacity:0";
            document.body.appendChild(textarea);
            textarea.select();
            const ok = document.execCommand("copy");
            document.body.removeChild(textarea);
            return ok;
        } catch (e) {
            console.error("复制失败:", e);
            return false;
        }
    },

    /**
     * 从剪贴板读取文本
     * @returns {Promise<string>}
     */
    async paste() {
        try {
            if (navigator.clipboard && navigator.clipboard.readText) {
                return await navigator.clipboard.readText();
            }
        } catch (e) {
            console.warn("剪贴板读取失败，可能需要用户授权:", e);
        }
        return "";
    },

    /**
     * 将剪贴板内容粘贴到指定输入框
     * @param {HTMLInputElement} input - 目标输入框
     */
    async pasteToInput(input) {
        const text = await this.paste();
        if (text) {
            input.value = text;
            input.dispatchEvent(new Event("input", { bubbles: true }));
            showToast("已粘贴", "success");
        } else {
            showToast("剪贴板为空或无权限读取", "error");
        }
    },

    /**
     * 复制输入框内容到剪贴板
     * @param {HTMLInputElement} input - 源输入框
     */
    async copyFromInput(input) {
        const text = input.value || input.textContent;
        if (!text) {
            showToast("内容为空", "error");
            return;
        }
        const ok = await this.copy(text);
        if (ok) {
            showToast("复制成功", "success");
        } else {
            showToast("复制失败", "error");
        }
    },
};

/**
 * 显示 Toast 通知
 * @param {string} message - 提示信息
 * @param {string} type - 类型: success, error, info
 * @param {number} duration - 持续时间(ms)
 */
function showToast(message, type = "info", duration = 3000) {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.remove();
    }, duration);
}

/**
 * 自动绑定所有带 data-target 属性的粘贴/复制按钮
 */
function initClipboardButtons() {
    // 通用粘贴按钮
    document.querySelectorAll(".paste-btn[data-target]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (input) {
                await ClipboardUtil.pasteToInput(input);
            }
        });
    });

    // 通用复制按钮
    document.querySelectorAll(".copy-btn[data-target]").forEach(btn => {
        btn.addEventListener("click", async () => {
            const targetId = btn.getAttribute("data-target");
            const input = document.getElementById(targetId);
            if (input) {
                await ClipboardUtil.copyFromInput(input);
            }
        });
    });
}

// DOM 加载完成后自动初始化
document.addEventListener("DOMContentLoaded", initClipboardButtons);
