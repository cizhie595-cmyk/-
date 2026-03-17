/**
 * Amazon Visionary Sourcing Tool - Content Script
 * 对应 PRD 3.1.2 - Chrome 插件内容脚本
 *
 * 功能:
 * 1. 在 Amazon 产品页面提取隐藏数据 (BSR, 变体, 库存等)
 * 2. 在搜索结果页提取产品列表数据
 * 3. 注入浮动面板显示分析结果
 */

(function () {
    "use strict";

    // 避免重复注入
    if (window.__AVST_INJECTED) return;
    window.__AVST_INJECTED = true;

    console.log("[AVST] Content script loaded");

    // ============================================================
    // 页面类型检测
    // ============================================================

    function detectPageType() {
        const url = window.location.href;
        if (url.includes("/dp/") || url.includes("/gp/product/")) {
            return "product";
        } else if (url.includes("/s?") || url.includes("/s/")) {
            return "search";
        }
        return "other";
    }

    // ============================================================
    // 产品详情页数据提取
    // ============================================================

    function extractProductData() {
        const data = {
            asin: extractASIN(),
            title: extractText("#productTitle"),
            price: extractPrice(),
            rating: extractRating(),
            reviewCount: extractReviewCount(),
            brand: extractBrand(),
            bsr: extractBSR(),
            categories: extractCategories(),
            images: extractImages(),
            variants: extractVariants(),
            bulletPoints: extractBulletPoints(),
            hiddenData: extractHiddenData(),
            fulfillment: extractFulfillment(),
            sellerInfo: extractSellerInfo(),
        };

        return data;
    }

    function extractASIN() {
        // 从 URL 提取
        const match = window.location.href.match(/\/dp\/([A-Z0-9]{10})/);
        if (match) return match[1];

        // 从页面元素提取
        const input = document.querySelector('input[name="ASIN"]');
        if (input) return input.value;

        return null;
    }

    function extractText(selector) {
        const el = document.querySelector(selector);
        return el ? el.textContent.trim() : null;
    }

    function extractPrice() {
        const selectors = [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            "#priceblock_dealprice",
            ".a-price-whole",
        ];

        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) {
                const text = el.textContent.trim();
                const num = parseFloat(text.replace(/[^0-9.]/g, ""));
                if (!isNaN(num)) return num;
            }
        }
        return null;
    }

    function extractRating() {
        const el = document.querySelector("#acrPopover .a-icon-alt");
        if (el) {
            const match = el.textContent.match(/([\d.]+)/);
            if (match) return parseFloat(match[1]);
        }
        return null;
    }

    function extractReviewCount() {
        const el = document.querySelector("#acrCustomerReviewText");
        if (el) {
            const match = el.textContent.replace(/,/g, "").match(/(\d+)/);
            if (match) return parseInt(match[1]);
        }
        return null;
    }

    function extractBrand() {
        const selectors = ["#bylineInfo", ".po-brand .a-span9 .a-size-base"];
        for (const sel of selectors) {
            const el = document.querySelector(sel);
            if (el) return el.textContent.trim().replace(/^(Brand:|Visit the |Store)/, "").trim();
        }
        return null;
    }

    function extractBSR() {
        const bsrList = [];
        const rows = document.querySelectorAll("#productDetails_detailBullets_sections1 tr, #detailBulletsWrapper_feature_div li");

        for (const row of rows) {
            const text = row.textContent;
            if (text.includes("Best Sellers Rank") || text.includes("Amazon")) {
                const matches = text.matchAll(/#([\d,]+)\s+in\s+(.+?)(?:\(|$)/g);
                for (const match of matches) {
                    bsrList.push({
                        rank: parseInt(match[1].replace(/,/g, "")),
                        category: match[2].trim(),
                    });
                }
            }
        }
        return bsrList;
    }

    function extractCategories() {
        const breadcrumbs = document.querySelectorAll("#wayfinding-breadcrumbs_feature_div a");
        return Array.from(breadcrumbs).map(a => a.textContent.trim());
    }

    function extractImages() {
        const images = [];

        // 主图
        const mainImg = document.querySelector("#landingImage, #imgBlkFront");
        if (mainImg) {
            const src = mainImg.getAttribute("data-old-hires") || mainImg.src;
            images.push({ type: "main", url: src });
        }

        // 缩略图列表
        const thumbs = document.querySelectorAll("#altImages .a-button-thumbnail img");
        thumbs.forEach((img, i) => {
            let url = img.src.replace(/\._[A-Z]+\d+_\./, ".");
            images.push({ type: "gallery", index: i, url });
        });

        return images;
    }

    function extractVariants() {
        const variants = [];

        // 从 twisterJS 提取变体数据
        const scripts = document.querySelectorAll("script");
        for (const script of scripts) {
            const text = script.textContent;
            if (text.includes("dimensionValuesDisplayData")) {
                try {
                    const match = text.match(/dimensionValuesDisplayData\s*:\s*(\{.*?\})/s);
                    if (match) {
                        const data = JSON.parse(match[1]);
                        for (const [asin, values] of Object.entries(data)) {
                            variants.push({ asin, values });
                        }
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }

        return variants;
    }

    function extractBulletPoints() {
        const points = document.querySelectorAll("#feature-bullets .a-list-item");
        return Array.from(points).map(li => li.textContent.trim()).filter(t => t.length > 0);
    }

    function extractHiddenData() {
        const hidden = {};

        // 提取 parentASIN
        const scripts = document.querySelectorAll("script");
        for (const script of scripts) {
            const text = script.textContent;

            // parentASIN
            const parentMatch = text.match(/"parentAsin"\s*:\s*"([A-Z0-9]+)"/);
            if (parentMatch) hidden.parentAsin = parentMatch[1];

            // 库存数据
            const stockMatch = text.match(/"stockStatus"\s*:\s*"([^"]+)"/);
            if (stockMatch) hidden.stockStatus = stockMatch[1];

            // merchantID
            const merchantMatch = text.match(/"merchantID"\s*:\s*"([^"]+)"/);
            if (merchantMatch) hidden.merchantId = merchantMatch[1];
        }

        // 提取 data-asin 属性
        const mainDiv = document.querySelector("#dp-container, #dp");
        if (mainDiv) {
            hidden.dataAsin = mainDiv.getAttribute("data-asin");
        }

        return hidden;
    }

    function extractFulfillment() {
        const text = document.querySelector("#tabular-buybox .tabular-buybox-text")?.textContent || "";
        if (text.includes("Amazon")) return "FBA";
        if (text.includes("Seller")) return "FBM";
        return "unknown";
    }

    function extractSellerInfo() {
        const sellerLink = document.querySelector("#sellerProfileTriggerId, #merchant-info a");
        return {
            name: sellerLink?.textContent?.trim() || null,
            url: sellerLink?.href || null,
        };
    }

    // ============================================================
    // 搜索结果页数据提取
    // ============================================================

    function extractSearchResults() {
        const keyword = new URLSearchParams(window.location.search).get("k") || "";
        const products = [];

        const items = document.querySelectorAll('[data-component-type="s-search-result"]');
        items.forEach((item, index) => {
            const asin = item.getAttribute("data-asin");
            if (!asin) return;

            const titleEl = item.querySelector("h2 a span");
            const priceEl = item.querySelector(".a-price .a-offscreen");
            const ratingEl = item.querySelector(".a-icon-alt");
            const reviewEl = item.querySelector(".a-size-base.s-underline-text");
            const imgEl = item.querySelector(".s-image");

            products.push({
                asin,
                position: index + 1,
                title: titleEl?.textContent?.trim() || "",
                price: priceEl ? parseFloat(priceEl.textContent.replace(/[^0-9.]/g, "")) : null,
                rating: ratingEl ? parseFloat(ratingEl.textContent.match(/([\d.]+)/)?.[1] || 0) : null,
                reviewCount: reviewEl ? parseInt(reviewEl.textContent.replace(/[^0-9]/g, "") || 0) : null,
                imageUrl: imgEl?.src || null,
                sponsored: !!item.querySelector(".s-label-popover-default"),
            });
        });

        return {
            keyword,
            page: parseInt(new URLSearchParams(window.location.search).get("page") || "1"),
            products,
            totalResults: products.length,
        };
    }

    // ============================================================
    // 浮动面板
    // ============================================================

    function injectFloatingPanel(data) {
        // 移除已有面板
        const existing = document.getElementById("avst-panel");
        if (existing) existing.remove();

        const panel = document.createElement("div");
        panel.id = "avst-panel";
        panel.innerHTML = `
            <div class="avst-panel-header">
                <span class="avst-panel-title">AVST 选品助手</span>
                <button class="avst-panel-close" id="avst-close">&times;</button>
            </div>
            <div class="avst-panel-body">
                <div class="avst-row"><span class="avst-label">ASIN:</span><span class="avst-value">${data.asin || "N/A"}</span></div>
                <div class="avst-row"><span class="avst-label">价格:</span><span class="avst-value">$${data.price || "N/A"}</span></div>
                <div class="avst-row"><span class="avst-label">评分:</span><span class="avst-value">${data.rating || "N/A"} (${data.reviewCount || 0} reviews)</span></div>
                <div class="avst-row"><span class="avst-label">BSR:</span><span class="avst-value">${data.bsr?.length ? data.bsr.map(b => `#${b.rank} in ${b.category}`).join("<br>") : "N/A"}</span></div>
                <div class="avst-row"><span class="avst-label">发货:</span><span class="avst-value">${data.fulfillment || "N/A"}</span></div>
                <div class="avst-row"><span class="avst-label">变体:</span><span class="avst-value">${data.variants?.length || 0} 个</span></div>
                <div class="avst-actions">
                    <button class="avst-btn avst-btn-primary" id="avst-sync">同步到 Web 端</button>
                    <button class="avst-btn" id="avst-analyze">深度分析</button>
                </div>
                <div class="avst-status" id="avst-status"></div>
            </div>
        `;

        document.body.appendChild(panel);

        // 事件绑定
        document.getElementById("avst-close").addEventListener("click", () => panel.remove());

        document.getElementById("avst-sync").addEventListener("click", () => {
            chrome.runtime.sendMessage({ type: "PRODUCT_DATA", data }, (response) => {
                const status = document.getElementById("avst-status");
                if (response?.success) {
                    status.textContent = "✓ 数据已同步";
                    status.style.color = "#22c55e";
                } else {
                    status.textContent = "✗ 同步失败";
                    status.style.color = "#ef4444";
                }
            });
        });

        document.getElementById("avst-analyze").addEventListener("click", () => {
            const status = document.getElementById("avst-status");
            status.textContent = "分析请求已发送...";
            chrome.runtime.sendMessage({
                type: "PRODUCT_DATA",
                data: { ...data, requestAnalysis: true },
            });
        });
    }

    // ============================================================
    // 接收来自 background 的消息
    // ============================================================

    chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
        if (message.type === "SYNC_SUCCESS") {
            const status = document.getElementById("avst-status");
            if (status) {
                status.textContent = `✓ ${message.asin} 已同步`;
                status.style.color = "#22c55e";
            }
        }
        sendResponse({ received: true });
    });

    // ============================================================
    // 主逻辑
    // ============================================================

    function main() {
        const pageType = detectPageType();

        if (pageType === "product") {
            // 延迟执行，等待页面完全加载
            setTimeout(() => {
                const data = extractProductData();
                if (data.asin) {
                    injectFloatingPanel(data);
                    // 自动发送数据到 background
                    chrome.runtime.sendMessage({ type: "PRODUCT_DATA", data });
                }
            }, 2000);
        } else if (pageType === "search") {
            setTimeout(() => {
                const data = extractSearchResults();
                if (data.products.length > 0) {
                    chrome.runtime.sendMessage({ type: "SEARCH_RESULTS", data });
                }
            }, 2000);
        }
    }

    // 页面加载完成后执行
    if (document.readyState === "complete") {
        main();
    } else {
        window.addEventListener("load", main);
    }
})();
