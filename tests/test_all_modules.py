"""
综合测试脚本 - 验证所有新增模块的核心功能
"""

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

passed = 0
failed = 0


def test(name, func):
    global passed, failed
    try:
        func()
        print(f"  ✅ {name}")
        passed += 1
    except Exception as e:
        print(f"  ❌ {name}: {e}")
        failed += 1


# ============================================================
# 模块一：Amazon 爬虫模块
# ============================================================
print("\n📦 模块一：Amazon 数据抓取")


def test_sp_api_client():
    from scrapers.amazon.sp_api_client import AmazonSPAPIClient
    client = AmazonSPAPIClient.__new__(AmazonSPAPIClient)
    assert client is not None


def test_amazon_search_crawler():
    from scrapers.amazon.search_crawler import AmazonSearchCrawler
    crawler = AmazonSearchCrawler.__new__(AmazonSearchCrawler)
    assert crawler is not None


def test_amazon_detail_crawler():
    from scrapers.amazon.detail_crawler import AmazonDetailCrawler
    crawler = AmazonDetailCrawler.__new__(AmazonDetailCrawler)
    assert crawler is not None


def test_amazon_review_crawler():
    from scrapers.amazon.review_crawler import AmazonReviewCrawler
    crawler = AmazonReviewCrawler.__new__(AmazonReviewCrawler)
    assert crawler is not None


def test_backend_parser():
    from scrapers.amazon.backend_parser import AmazonBackendParser
    parser = AmazonBackendParser()
    assert parser is not None


def test_third_party_api():
    from scrapers.amazon.third_party_api import KeepaClient, RainforestClient
    assert KeepaClient is not None
    assert RainforestClient is not None


test("SP-API 客户端导入", test_sp_api_client)
test("Amazon 搜索爬虫导入", test_amazon_search_crawler)
test("Amazon 详情爬虫导入", test_amazon_detail_crawler)
test("Amazon 评论爬虫导入", test_amazon_review_crawler)
test("后台搜索词解析器导入", test_backend_parser)
test("第三方 API 客户端导入", test_third_party_api)

# ============================================================
# 模块二：Amazon 数据筛选
# ============================================================
print("\n🔍 模块二：Amazon 数据清洗筛选")


def test_amazon_data_filter():
    from analysis.amazon_data_filter import AmazonDataFilter
    f = AmazonDataFilter()
    assert f is not None
    # 测试筛选逻辑
    products = [
        {"asin": "B001", "price": 25.0, "reviews_count": 100, "bsr": 5000, "rating": 4.2},
        {"asin": "B002", "price": 5.0, "reviews_count": 2, "bsr": 500000, "rating": 2.0},
        {"asin": "B003", "price": 35.0, "reviews_count": 500, "bsr": 1000, "rating": 4.5},
    ]
    # 使用宽松条件的筛选器
    f2 = AmazonDataFilter(rules={
        "min_review_count": 0,
        "min_rating": 1.0,
        "min_conversion_rate": 0,
        "max_conversion_rate": 1.0,
        "exclude_amazon_brands": False,
    })
    result = f2.filter_products(products)
    assert isinstance(result, dict)
    assert "kept" in result
    assert len(result["kept"]) >= 1  # 至少有一个通过


test("Amazon 数据筛选器", test_amazon_data_filter)

# ============================================================
# 模块三：OCR 与深度爬取
# ============================================================
print("\n🔬 模块三：深度爬取与 OCR")


def test_ocr_extractor():
    from analysis.ai_analysis.ocr_extractor import OCRExtractor
    extractor = OCRExtractor.__new__(OCRExtractor)
    assert extractor is not None


def test_deep_crawler():
    from scrapers.amazon.deep_crawler import AmazonDeepCrawler
    crawler = AmazonDeepCrawler.__new__(AmazonDeepCrawler)
    assert crawler is not None


test("OCR 提取器导入", test_ocr_extractor)
test("深度爬取协调器导入", test_deep_crawler)

# ============================================================
# 模块四：3D 模型生成
# ============================================================
print("\n🎮 模块四：3D 模型生成")


def test_3d_generator():
    from analysis.model_3d.generator import MeshyClient, TripoClient, ThreeDGenerator
    assert MeshyClient is not None
    assert TripoClient is not None
    gen = ThreeDGenerator.__new__(ThreeDGenerator)
    assert gen is not None


test("3D 模型生成器导入", test_3d_generator)

# ============================================================
# 模块五：Amazon 类目分析
# ============================================================
print("\n📊 模块五：大盘与类目分析")


def test_amazon_category_analyzer():
    from analysis.market_analysis.amazon_category_analyzer import AmazonCategoryAnalyzer
    analyzer = AmazonCategoryAnalyzer.__new__(AmazonCategoryAnalyzer)
    assert analyzer is not None


test("Amazon 类目分析器导入", test_amazon_category_analyzer)

# ============================================================
# 模块六：Amazon FBA 利润计算
# ============================================================
print("\n💰 模块六：FBA 利润核算")


def test_fba_profit_calculator():
    from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
    calc = AmazonFBAProfitCalculator(marketplace="US", exchange_rate=7.25)

    result = calc.calculate_profit({
        "selling_price": 29.99,
        "category": "Home & Garden",
        "weight_lb": 1.5,
        "length_in": 10,
        "width_in": 6,
        "height_in": 4,
        "cogs_rmb": 35,
        "shipping_rmb_per_kg": 40,
        "weight_kg": 0.68,
        "ppc_cost_per_unit": 2.0,
        "return_rate": 0.03,
        "monthly_units": 200,
    })

    assert "profit" in result
    assert "costs" in result
    assert result["selling_price"] == 29.99
    assert result["profit"]["profit_per_unit_usd"] != 0
    assert result["health_check"]["grade"] in ("A", "B", "C", "D", "F")


def test_pricing_comparison():
    from analysis.profit_analysis.amazon_profit_calculator import AmazonFBAProfitCalculator
    calc = AmazonFBAProfitCalculator()
    results = calc.compare_pricing_strategies({
        "selling_price": 25.0,
        "category": "Kitchen",
        "weight_lb": 1.0,
        "length_in": 8,
        "width_in": 5,
        "height_in": 3,
        "cogs_rmb": 30,
        "weight_kg": 0.45,
    })
    assert len(results) == 11


test("FBA 利润计算", test_fba_profit_calculator)
test("定价策略对比", test_pricing_comparison)

# ============================================================
# 模块七：AI 风险预警
# ============================================================
print("\n⚠️ 模块七：AI 风险预警")


def test_risk_analyzer():
    from analysis.ai_analysis.risk_analyzer import RiskAnalyzer
    analyzer = RiskAnalyzer()

    report = analyzer.analyze_risks({
        "asin": "B0TEST123",
        "title": "Wireless Bluetooth Earbuds for Kids",
        "brand": "Generic",
        "category": "Electronics Accessories",
    })

    assert "risk_score" in report
    assert "ip_risk" in report
    assert "compliance_risk" in report
    assert report["compliance_risk"]["required_certifications"]  # 应检测到 FCC/CPSC


def test_product_summarizer():
    from analysis.ai_analysis.risk_analyzer import AIProductSummarizer
    summarizer = AIProductSummarizer()
    report = summarizer.generate_final_report({
        "title": "Test Product",
        "asin": "B0TEST",
        "price": 25.0,
        "brand": "TestBrand",
    })
    assert "product_score" in report
    assert "decision" in report


test("风险分析器", test_risk_analyzer)
test("AI 选品总结器", test_product_summarizer)

# ============================================================
# 模块八：第三方 API 密钥配置
# ============================================================
print("\n🔑 模块八：API 密钥配置")


def test_api_keys_config():
    from auth.api_keys_config import APIKeysConfigManager, THIRD_PARTY_SERVICES
    services = APIKeysConfigManager.get_services()
    assert len(services) == len(THIRD_PARTY_SERVICES)
    assert any(s["id"] == "keepa" for s in services)
    assert any(s["id"] == "meshy" for s in services)
    assert any(s["id"] == "amazon_sp_api" for s in services)


test("第三方 API 服务列表", test_api_keys_config)

# ============================================================
# 模块九：商业化
# ============================================================
print("\n🚀 模块九：商业化")


def test_subscription_plans():
    from monetization.subscription import SubscriptionManager, SUBSCRIPTION_PLANS
    plans = SubscriptionManager.get_plans()
    assert len(plans) == 3
    assert plans[0]["id"] == "free"
    assert plans[1]["id"] == "orbit"
    assert plans[2]["id"] == "moonshot"
    assert plans[0]["price_monthly"] == 0
    assert plans[1]["price_monthly"] == 29.99
    assert plans[2]["price_monthly"] == 99.99


def test_affiliate_manager():
    from monetization.affiliate import AffiliateManager
    mgr = AffiliateManager()

    # 测试 ASIN 转链接
    link = mgr.generate_affiliate_link("B0EXAMPLE1", "US", "mytag-20")
    assert "amazon.com" in link
    assert "tag=mytag-20" in link

    # 测试批量处理
    products = [
        {"asin": "B001", "title": "Product 1"},
        {"asin": "B002", "title": "Product 2", "url": "https://www.amazon.com/dp/B002"},
    ]
    processed = mgr.inject_tags_batch(products, "US", "testtag-20")
    assert all("url" in p for p in processed)
    assert "tag=testtag-20" in processed[0]["url"]


def test_module_access_check():
    from monetization.subscription import SUBSCRIPTION_PLANS
    # 验证免费版不能用 3D
    free_plan = SUBSCRIPTION_PLANS["free"]
    assert free_plan["modules"]["model_3d"] == False
    assert free_plan["modules"]["search_crawler"] == True

    # 验证登月版全功能
    moonshot = SUBSCRIPTION_PLANS["moonshot"]
    assert all(v == True for v in moonshot["modules"].values())


test("订阅计划定义", test_subscription_plans)
test("Affiliate 链接生成", test_affiliate_manager)
test("模块权限检查", test_module_access_check)

# ============================================================
# Flask 路由注册测试
# ============================================================
print("\n🌐 Flask 路由注册")


def test_flask_app():
    from app import create_app
    app = create_app()
    client = app.test_client()

    # 测试根路由
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["system"] == "Coupang 跨境电商智能选品系统"

    # 测试 API 文档
    resp = client.get("/api/docs")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "auth" in data
    assert "ai_config" in data
    assert "api_keys" in data
    assert "subscription" in data

    # 测试健康检查
    resp = client.get("/api/health")
    assert resp.status_code == 200

    # 测试订阅计划（无需登录）
    resp = client.get("/api/subscription/plans")
    assert resp.status_code == 200
    data = resp.get_json()
    assert len(data["plans"]) == 3


test("Flask 应用启动与路由", test_flask_app)

# ============================================================
# 总结
# ============================================================
print(f"\n{'='*50}")
print(f"测试完成: ✅ {passed} 通过 | ❌ {failed} 失败")
print(f"{'='*50}")

sys.exit(0 if failed == 0 else 1)
