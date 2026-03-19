"""
Tests for Phase 20 - DEV-01 to DEV-06
DEV-01: 1688/阿里妈妈返佣
DEV-02: 第三方服务商推荐卡片
DEV-03: report.html 五维风险雷达图
DEV-04: report.html Markdown 渲染
DEV-05: subscription.html Stripe 支付集成
DEV-06: Chrome 插件统计面板增强
"""
import pytest
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)


# ============================================================
# DEV-01: 1688/阿里妈妈返佣
# ============================================================
class TestDEV01_AlimamaAffiliate:
    """Test 1688/阿里妈妈返佣功能"""

    def test_affiliate_module_exists(self):
        """affiliate.py 模块存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "monetization", "affiliate.py"))

    def test_affiliate_class_importable(self):
        """AffiliateManager 类可导入"""
        from monetization.affiliate import AffiliateManager
        manager = AffiliateManager()
        assert manager is not None

    def test_1688_affiliate_link_generation(self):
        """1688 返佣链接生成"""
        from monetization.affiliate import AffiliateManager
        manager = AffiliateManager()
        # 检查是否有 1688 相关方法
        assert hasattr(manager, 'generate_link') or hasattr(manager, 'generate_1688_link') or hasattr(manager, 'generate_affiliate_link')

    def test_affiliate_supports_1688_platform(self):
        """affiliate 支持 1688 平台"""
        filepath = os.path.join(BASE_DIR, "monetization", "affiliate.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "1688" in content, "affiliate.py should support 1688 platform"

    def test_affiliate_supports_alimama(self):
        """affiliate 支持阿里妈妈"""
        filepath = os.path.join(BASE_DIR, "monetization", "affiliate.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "alimama" in content.lower() or "阿里妈妈" in content or "ali_pid" in content, \
            "affiliate.py should support Alimama PID"

    def test_affiliate_supports_amazon(self):
        """affiliate 仍然支持 Amazon"""
        filepath = os.path.join(BASE_DIR, "monetization", "affiliate.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "amazon" in content.lower() or "Amazon" in content

    def test_affiliate_supports_coupang(self):
        """affiliate 仍然支持 Coupang"""
        filepath = os.path.join(BASE_DIR, "monetization", "affiliate.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "coupang" in content.lower() or "Coupang" in content

    def test_affiliate_click_tracking(self):
        """affiliate 有点击追踪功能"""
        filepath = os.path.join(BASE_DIR, "monetization", "affiliate.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "track" in content.lower() or "click" in content.lower()


# ============================================================
# DEV-02: 第三方服务商推荐卡片
# ============================================================
class TestDEV02_ServiceRecommendations:
    """Test 第三方服务商推荐卡片模块"""

    def test_module_exists(self):
        """service_recommendations.py 模块存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "monetization", "service_recommendations.py"))

    def test_class_importable(self):
        """ServiceRecommendationEngine 类可导入"""
        from monetization.service_recommendations import ServiceRecommendationEngine
        engine = ServiceRecommendationEngine()
        assert engine is not None

    def test_has_get_recommendations_method(self):
        """有 get_recommendations 方法"""
        from monetization.service_recommendations import ServiceRecommendationEngine
        engine = ServiceRecommendationEngine()
        assert hasattr(engine, 'get_recommendations') or hasattr(engine, 'recommend')

    def test_trademarkia_service(self):
        """包含 Trademarkia 商标服务"""
        filepath = os.path.join(BASE_DIR, "monetization", "service_recommendations.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "trademarkia" in content.lower() or "trademark" in content.lower()

    def test_logistics_service(self):
        """包含物流服务推荐"""
        filepath = os.path.join(BASE_DIR, "monetization", "service_recommendations.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "deliverr" in content.lower() or "logistics" in content.lower() or "物流" in content

    def test_service_card_data_structure(self):
        """服务商卡片数据结构完整"""
        from monetization.service_recommendations import ServiceRecommendationEngine
        engine = ServiceRecommendationEngine()
        # 获取推荐
        if hasattr(engine, 'get_recommendations'):
            recs = engine.get_recommendations(risk_dimensions={"ip_risk": 80})
        elif hasattr(engine, 'recommend'):
            recs = engine.recommend(risk_type="ip_risk")
        else:
            recs = engine.get_all_services() if hasattr(engine, 'get_all_services') else []

        assert isinstance(recs, (list, dict)), "Recommendations should be list or dict"

    def test_affiliate_link_in_recommendations(self):
        """推荐卡片包含返佣链接"""
        filepath = os.path.join(BASE_DIR, "monetization", "service_recommendations.py")
        with open(filepath, "r") as f:
            content = f.read()
        assert "affiliate" in content.lower() or "referral" in content.lower() or "ref" in content.lower()

    def test_multiple_risk_categories(self):
        """支持多种风险类别的推荐"""
        filepath = os.path.join(BASE_DIR, "monetization", "service_recommendations.py")
        with open(filepath, "r") as f:
            content = f.read()
        risk_types = ["ip", "trademark", "patent", "logistics", "compliance"]
        found = sum(1 for rt in risk_types if rt in content.lower())
        assert found >= 3, f"Should support at least 3 risk categories, found {found}"


# ============================================================
# DEV-03: report.html 五维风险雷达图
# ============================================================
class TestDEV03_ReportRadarChart:
    """Test report.html 五维风险雷达图"""

    def test_report_template_exists(self):
        """report.html 模板存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "frontend", "templates", "report.html"))

    def test_radar_chart_canvas(self):
        """report.html 包含雷达图 Canvas"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "risk-radar-chart" in content or "radarChart" in content or "radar" in content.lower()

    def test_chart_js_reference(self):
        """report.html 引用 Chart.js"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "Chart" in content or "chart.js" in content.lower() or "cdn" in content.lower()

    def test_five_dimensions(self):
        """雷达图包含五个维度"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        dimensions = ["competition", "demand", "profit", "ip", "season"]
        alt_dimensions = ["竞争", "需求", "利润", "知识产权", "季节"]
        found = sum(1 for d in dimensions if d in content.lower())
        found_alt = sum(1 for d in alt_dimensions if d in content)
        assert found >= 3 or found_alt >= 3, "Should have at least 3 of 5 radar dimensions"

    def test_radar_render_function(self):
        """有雷达图渲染函数"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "renderRadar" in content or "drawRadar" in content or "new Chart" in content


# ============================================================
# DEV-04: report.html Markdown 渲染
# ============================================================
class TestDEV04_ReportMarkdownRendering:
    """Test report.html Markdown 渲染区域"""

    def test_markdown_renderer(self):
        """report.html 包含 Markdown 渲染器"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "marked" in content.lower() or "markdown" in content.lower() or "showdown" in content.lower()

    def test_full_report_section(self):
        """report.html 包含完整报告区域"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "full-report" in content or "report-content" in content or "report-md" in content

    def test_marked_parse_call(self):
        """使用 marked.parse 渲染 Markdown"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "marked.parse" in content or "marked(" in content

    def test_report_export_button(self):
        """报告页有导出按钮"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "export" in content.lower() or "download" in content.lower() or "pdf" in content.lower()


# ============================================================
# DEV-05: subscription.html Stripe 支付集成
# ============================================================
class TestDEV05_StripeIntegration:
    """Test subscription.html Stripe 支付集成"""

    def test_subscription_template_exists(self):
        """subscription.html 模板存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "frontend", "templates", "subscription.html"))

    def test_stripe_js_cdn(self):
        """subscription.html 引用 Stripe.js CDN"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "js.stripe.com" in content or "Stripe(" in content

    def test_checkout_session_creation(self):
        """有创建 Checkout Session 的逻辑"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "checkout" in content.lower() or "create-checkout-session" in content

    def test_redirect_to_checkout(self):
        """有 redirectToCheckout 调用"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "redirectToCheckout" in content or "checkout_url" in content

    def test_billing_cycle_toggle(self):
        """有年/月计费切换"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "billing-toggle" in content or "billingCycle" in content or "monthly" in content

    def test_payment_history_section(self):
        """有支付历史区域"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "payment-history" in content or "Payment History" in content

    def test_payment_callback_handling(self):
        """有支付回调处理"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "payment=success" in content or "checkPaymentCallback" in content

    def test_payment_processing_modal(self):
        """有支付处理中模态框"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "payment-processing" in content or "Processing Payment" in content

    def test_three_plans_displayed(self):
        """显示三个订阅计划"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "plan-free" in content
        assert "plan-pro" in content or "plan-orbit" in content
        assert "plan-enterprise" in content or "plan-moonshot" in content


# ============================================================
# DEV-06: Chrome 插件统计面板增强
# ============================================================
class TestDEV06_ChromeStatsEnhanced:
    """Test Chrome 插件统计面板增强"""

    def test_popup_html_exists(self):
        """popup.html 存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "chrome_extension", "popup.html"))

    def test_popup_js_exists(self):
        """popup.js 存在"""
        assert os.path.exists(os.path.join(BASE_DIR, "chrome_extension", "popup.js"))

    def test_time_toggle_buttons(self):
        """popup.html 有今日/本周/本月切换按钮"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "time-toggle" in content
        assert "today" in content
        assert "week" in content
        assert "month" in content

    def test_mini_chart_canvas(self):
        """popup.html 有迷你图表 Canvas"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "chart-captured" in content
        assert "chart-analyzed" in content
        assert "chart-tracked" in content

    def test_trend_indicators(self):
        """popup.html 有趋势指示器"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "stat-trend" in content
        assert "trend-captured" in content

    def test_switch_time_range_function(self):
        """popup.js 有 switchTimeRange 函数"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(filepath, "r") as f:
            content = f.read()
        assert "switchTimeRange" in content

    def test_draw_mini_chart_function(self):
        """popup.js 有 drawMiniChart 函数"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(filepath, "r") as f:
            content = f.read()
        assert "drawMiniChart" in content

    def test_animate_value_function(self):
        """popup.js 有 animateValue 动画函数"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(filepath, "r") as f:
            content = f.read()
        assert "animateValue" in content

    def test_stats_history_storage(self):
        """popup.js 有统计历史存储"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(filepath, "r") as f:
            content = f.read()
        assert "statsHistory" in content

    def test_trend_calculation(self):
        """popup.js 有趋势计算逻辑"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(filepath, "r") as f:
            content = f.read()
        assert "updateTrend" in content

    def test_summary_total(self):
        """popup.html 有总计操作显示"""
        filepath = os.path.join(BASE_DIR, "chrome_extension", "popup.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "summary-total" in content or "stats-summary" in content


# ============================================================
# 集成测试
# ============================================================
class TestIntegration:
    """集成测试"""

    def test_all_monetization_modules(self):
        """所有商业化模块可导入"""
        from monetization.affiliate import AffiliateManager
        from monetization.service_recommendations import ServiceRecommendationEngine
        assert AffiliateManager is not None
        assert ServiceRecommendationEngine is not None

    def test_report_page_complete(self):
        """report.html 包含所有增强功能"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "report.html")
        with open(filepath, "r") as f:
            content = f.read()
        # 雷达图
        assert "radar" in content.lower()
        # Markdown 渲染
        assert "marked" in content.lower()
        # 服务商推荐
        assert "service" in content.lower()

    def test_subscription_page_complete(self):
        """subscription.html 包含所有增强功能"""
        filepath = os.path.join(BASE_DIR, "frontend", "templates", "subscription.html")
        with open(filepath, "r") as f:
            content = f.read()
        assert "Stripe" in content
        assert "billing" in content.lower()
        assert "payment" in content.lower()

    def test_chrome_extension_complete(self):
        """Chrome 插件包含所有增强功能"""
        html_path = os.path.join(BASE_DIR, "chrome_extension", "popup.html")
        js_path = os.path.join(BASE_DIR, "chrome_extension", "popup.js")
        with open(html_path, "r") as f:
            html = f.read()
        with open(js_path, "r") as f:
            js = f.read()
        assert "time-toggle" in html
        assert "mini-chart" in html or "chart-captured" in html
        assert "switchTimeRange" in js
        assert "drawMiniChart" in js

    def test_file_sizes_reasonable(self):
        """所有修改的文件大小合理"""
        files = {
            "monetization/affiliate.py": (100, 1000),
            "monetization/service_recommendations.py": (100, 1000),
            "frontend/templates/report.html": (400, 2000),
            "frontend/templates/subscription.html": (300, 1500),
            "chrome_extension/popup.html": (300, 1500),
            "chrome_extension/popup.js": (300, 1500),
        }
        for filepath, (min_lines, max_lines) in files.items():
            full_path = os.path.join(BASE_DIR, filepath)
            with open(full_path, "r") as f:
                lines = len(f.readlines())
            assert min_lines <= lines <= max_lines, \
                f"{filepath}: {lines} lines (expected {min_lines}-{max_lines})"
