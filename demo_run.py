#!/usr/bin/env python3
"""
Coupang 选品系统 - 演示运行脚本
使用模拟真实数据演示系统完整分析流程
"""

import os
import sys
import json
from datetime import datetime, timedelta
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from i18n import set_language, t
from utils.logger import get_logger
from analysis.data_filter import DataFilter
from analysis.profit_analysis.profit_calculator import ProfitCalculator
from analysis.market_analysis.report_generator import ReportGenerator

logger = get_logger()

# ============================================================
# 模拟数据：基于 Coupang "무선 이어폰" (无线耳机) 类目真实结构
# ============================================================

KEYWORD = "무선 이어폰"

MOCK_PRODUCTS = [
    {
        "coupang_product_id": "7612345001",
        "title": "삼성 갤럭시 버즈3 프로 무선 블루투스 이어폰 노이즈캔슬링",
        "url": "https://www.coupang.com/vp/products/7612345001",
        "price": 189000,
        "original_price": 259000,
        "rating": 4.8,
        "review_count": 15234,
        "brand_name": "Samsung",
        "delivery_type": "blue_rocket",
        "ranking": 1,
        "main_image_url": "https://example.com/img1.jpg",
        "weight_kg": 0.15,
    },
    {
        "coupang_product_id": "7612345002",
        "title": "애플 에어팟 프로 2세대 USB-C MagSafe 무선 이어폰",
        "url": "https://www.coupang.com/vp/products/7612345002",
        "price": 289000,
        "original_price": 359000,
        "rating": 4.9,
        "review_count": 28456,
        "brand_name": "Apple",
        "delivery_type": "blue_rocket",
        "ranking": 2,
        "main_image_url": "https://example.com/img2.jpg",
        "weight_kg": 0.12,
    },
    {
        "coupang_product_id": "7612345003",
        "title": "QCY T13 ANC 노이즈캔슬링 무선 블루투스 이어폰 IPX5 방수",
        "url": "https://www.coupang.com/vp/products/7612345003",
        "price": 19900,
        "original_price": 39900,
        "rating": 4.5,
        "review_count": 42310,
        "brand_name": "QCY",
        "delivery_type": "blue_rocket",
        "ranking": 3,
        "main_image_url": "https://example.com/img3.jpg",
        "weight_kg": 0.10,
    },
    {
        "coupang_product_id": "7612345004",
        "title": "KONLI 노이즈 캔슬링 커널형 무선 블루투스 이어폰 방수 T12",
        "url": "https://www.coupang.com/vp/products/7612345004",
        "price": 15900,
        "original_price": 29900,
        "rating": 4.3,
        "review_count": 18920,
        "brand_name": "KONLI",
        "delivery_type": "orange_rocket",
        "ranking": 4,
        "main_image_url": "https://example.com/img4.jpg",
        "weight_kg": 0.08,
    },
    {
        "coupang_product_id": "7612345005",
        "title": "소니 WF-1000XM5 노이즈캔슬링 무선 이어폰 블루투스",
        "url": "https://www.coupang.com/vp/products/7612345005",
        "price": 259000,
        "original_price": 359900,
        "rating": 4.7,
        "review_count": 8920,
        "brand_name": "Sony",
        "delivery_type": "blue_rocket",
        "ranking": 5,
        "main_image_url": "https://example.com/img5.jpg",
        "weight_kg": 0.18,
    },
    {
        "coupang_product_id": "7612345006",
        "title": "JBL TUNE BEAM 노이즈캔슬링 무선 블루투스 이어폰",
        "url": "https://www.coupang.com/vp/products/7612345006",
        "price": 69900,
        "original_price": 99900,
        "rating": 4.4,
        "review_count": 5670,
        "brand_name": "JBL",
        "delivery_type": "blue_rocket",
        "ranking": 6,
        "main_image_url": "https://example.com/img6.jpg",
        "weight_kg": 0.14,
    },
    {
        "coupang_product_id": "7612345007",
        "title": "EDIFIER NeoBuds Pro 2 하이레졸루션 무선 이어폰 ANC",
        "url": "https://www.coupang.com/vp/products/7612345007",
        "price": 89000,
        "original_price": 129000,
        "rating": 4.6,
        "review_count": 3240,
        "brand_name": "EDIFIER",
        "delivery_type": "orange_rocket",
        "ranking": 7,
        "main_image_url": "https://example.com/img7.jpg",
        "weight_kg": 0.12,
    },
    {
        "coupang_product_id": "7612345008",
        "title": "샤오미 Redmi Buds 5 Pro 무선 블루투스 이어폰 노이즈캔슬링",
        "url": "https://www.coupang.com/vp/products/7612345008",
        "price": 35900,
        "original_price": 59900,
        "rating": 4.4,
        "review_count": 7890,
        "brand_name": "Xiaomi",
        "delivery_type": "purple_rocket",
        "ranking": 8,
        "main_image_url": "https://example.com/img8.jpg",
        "weight_kg": 0.11,
    },
    {
        "coupang_product_id": "7612345009",
        "title": "보스 QuietComfort Ultra Earbuds 무선 이어폰",
        "url": "https://www.coupang.com/vp/products/7612345009",
        "price": 329000,
        "original_price": 399000,
        "rating": 4.8,
        "review_count": 2150,
        "brand_name": "Bose",
        "delivery_type": "blue_rocket",
        "ranking": 9,
        "main_image_url": "https://example.com/img9.jpg",
        "weight_kg": 0.16,
    },
    {
        "coupang_product_id": "7612345010",
        "title": "TOZO T6 무선 블루투스 이어폰 IPX8 방수 터치 컨트롤",
        "url": "https://www.coupang.com/vp/products/7612345010",
        "price": 22900,
        "original_price": 39900,
        "rating": 4.2,
        "review_count": 31200,
        "brand_name": "TOZO",
        "delivery_type": "orange_rocket",
        "ranking": 10,
        "main_image_url": "https://example.com/img10.jpg",
        "weight_kg": 0.09,
    },
    {
        "coupang_product_id": "7612345011",
        "title": "앤커 사운드코어 Liberty 4 NC 무선 이어폰 노이즈캔슬링",
        "url": "https://www.coupang.com/vp/products/7612345011",
        "price": 79900,
        "original_price": 109900,
        "rating": 4.5,
        "review_count": 4560,
        "brand_name": "Anker",
        "delivery_type": "blue_rocket",
        "ranking": 11,
        "main_image_url": "https://example.com/img11.jpg",
        "weight_kg": 0.13,
    },
    {
        "coupang_product_id": "7612345012",
        "title": "Nothing Ear (2) 무선 블루투스 이어폰 ANC 투명 디자인",
        "url": "https://www.coupang.com/vp/products/7612345012",
        "price": 119000,
        "original_price": 149000,
        "rating": 4.3,
        "review_count": 1890,
        "brand_name": "Nothing",
        "delivery_type": "blue_rocket",
        "ranking": 12,
        "main_image_url": "https://example.com/img12.jpg",
        "weight_kg": 0.11,
    },
    {
        "coupang_product_id": "7612345013",
        "title": "LENOVO LP40 프로 무선 블루투스 이어폰 초경량 게이밍",
        "url": "https://www.coupang.com/vp/products/7612345013",
        "price": 9900,
        "original_price": 19900,
        "rating": 4.0,
        "review_count": 56780,
        "brand_name": "Lenovo",
        "delivery_type": "purple_rocket",
        "ranking": 13,
        "main_image_url": "https://example.com/img13.jpg",
        "weight_kg": 0.07,
    },
    {
        "coupang_product_id": "7612345014",
        "title": "마샬 MOTIF II ANC 무선 블루투스 이어폰 프리미엄",
        "url": "https://www.coupang.com/vp/products/7612345014",
        "price": 249000,
        "original_price": 299000,
        "rating": 4.6,
        "review_count": 1230,
        "brand_name": "Marshall",
        "delivery_type": "blue_rocket",
        "ranking": 14,
        "main_image_url": "https://example.com/img14.jpg",
        "weight_kg": 0.15,
    },
    {
        "coupang_product_id": "7612345015",
        "title": "BASEUS Bowie 30 무선 블루투스 이어폰 ENC 통화 노이즈캔슬링",
        "url": "https://www.coupang.com/vp/products/7612345015",
        "price": 17900,
        "original_price": 32900,
        "rating": 4.1,
        "review_count": 9870,
        "brand_name": "BASEUS",
        "delivery_type": "orange_rocket",
        "ranking": 15,
        "main_image_url": "https://example.com/img15.jpg",
        "weight_kg": 0.09,
    },
]

# 模拟30天运营数据
def generate_daily_stats(products):
    stats = {}
    for p in products:
        pid = p["coupang_product_id"]
        stats[pid] = []
        base_clicks = random.randint(50, 5000)
        base_sales = max(1, int(base_clicks * random.uniform(0.02, 0.15)))
        for day in range(30):
            date = (datetime.now() - timedelta(days=29-day)).strftime("%Y-%m-%d")
            clicks = max(0, base_clicks + random.randint(-base_clicks//3, base_clicks//3))
            sales = max(0, base_sales + random.randint(-base_sales//2, base_sales//2))
            impressions = clicks * random.randint(5, 15)
            stats[pid].append({
                "record_date": date,
                "daily_clicks": clicks,
                "daily_sales": sales,
                "daily_views": clicks * random.randint(5, 15),
                "daily_revenue": sales * p["price"],
            })
    return stats

# 模拟评论分析结果
def generate_review_analyses(products):
    analyses = {}
    pain_points_pool = [
        {"point": "배터리 수명이 짧음 (电池续航短)", "frequency": 0.15, "severity": "medium"},
        {"point": "노이즈캔슬링 효과 부족 (降噪效果不足)", "frequency": 0.12, "severity": "high"},
        {"point": "통화 품질 불량 (通话质量差)", "frequency": 0.10, "severity": "medium"},
        {"point": "착용감 불편 (佩戴不舒适)", "frequency": 0.08, "severity": "high"},
        {"point": "연결 불안정 (连接不稳定)", "frequency": 0.07, "severity": "high"},
        {"point": "케이스 품질 저하 (充电盒质量差)", "frequency": 0.05, "severity": "low"},
    ]
    selling_points_pool = [
        {"point": "가성비 뛰어남 (性价比高)", "frequency": 0.25},
        {"point": "음질 우수 (音质优秀)", "frequency": 0.22},
        {"point": "노이즈캔슬링 효과 좋음 (降噪效果好)", "frequency": 0.18},
        {"point": "착용감 편안 (佩戴舒适)", "frequency": 0.15},
        {"point": "디자인 세련됨 (设计时尚)", "frequency": 0.12},
        {"point": "배터리 오래감 (续航持久)", "frequency": 0.10},
    ]
    for p in products[:10]:
        pid = p["coupang_product_id"]
        analyses[pid] = {
            "selling_points": random.sample(selling_points_pool, 3),
            "pain_points": random.sample(pain_points_pool, 3),
            "user_profile": {
                "age_groups": ["20대 (20s)", "30대 (30s)"],
                "usage_scenarios": ["출퇴근 (通勤)", "운동 (运动)", "공부 (学习)"],
                "gender_ratio": {"male": 0.55, "female": 0.45},
            },
            "overall_sentiment": random.uniform(0.65, 0.92),
            "improvement_suggestions": [
                "增强降噪效果，特别是低频噪音",
                "改善蓝牙连接稳定性",
                "增加续航时间至8小时以上",
            ],
        }
    return analyses

# 模拟1688货源数据
def generate_sources(products):
    for p in products:
        price_krw = p["price"]
        cost_rmb = price_krw / 190 * random.uniform(0.10, 0.35)
        p["sources_1688"] = [
            {
                "supplier_name": f"深圳{random.choice(['华强北','南山','宝安'])}电子厂",
                "price_rmb": round(cost_rmb, 2),
                "moq": random.choice([50, 100, 200, 500]),
                "supplier_rating": round(random.uniform(4.0, 5.0), 1),
                "transaction_count": random.randint(100, 50000),
            },
            {
                "supplier_name": f"东莞{random.choice(['长安','虎门','厚街'])}音频科技",
                "price_rmb": round(cost_rmb * random.uniform(0.85, 1.15), 2),
                "moq": random.choice([100, 200, 500]),
                "supplier_rating": round(random.uniform(3.8, 4.8), 1),
                "transaction_count": random.randint(50, 30000),
            },
        ]
    return products

# 模拟类目分析
MOCK_CATEGORY_ANALYSIS = {
    "keyword": KEYWORD,
    "gmv_estimate": {
        "monthly_gmv_krw": 85600000000,
        "daily_avg_krw": 2853000000,
        "method": "sales_extrapolation",
    },
    "monopoly_analysis": {
        "available": True,
        "top1_ratio": 0.18,
        "top3_ratio": 0.38,
        "top10_ratio": 0.62,
        "hhi_index": 0.08,
        "description": "中等集中度 (中等集中度) - 头部品牌有一定优势但非垄断",
    },
    "new_product_analysis": {
        "total_analyzed": 50,
        "new_3m_count": 8,
        "new_3m_ratio": 0.16,
        "new_6m_count": 15,
        "new_6m_ratio": 0.30,
        "market_maturity": "成长期 (Growth Stage)",
    },
    "price_distribution": {
        "available": True,
        "min": 6900,
        "max": 399000,
        "avg": 89500,
        "median": 49900,
        "price_segments": {
            "budget (<20000)": 0.22,
            "mid (20000-80000)": 0.35,
            "premium (80000-200000)": 0.28,
            "luxury (>200000)": 0.15,
        },
    },
    "naver_trend": {
        "available": True,
        "trend_direction": "stable_growth",
        "monthly_search_volume": 245000,
        "yoy_growth": 0.12,
    },
    "ai_assessment": {
        "market_score": 7.5,
        "opportunities": [
            "中低价位段(2-5万韩元)竞争相对较少，新品有机会切入",
            "ANC降噪功能需求增长迅速，消费者愿意为此支付溢价",
            "运动防水型耳机细分市场增长明显",
            "韩国消费者对中国品牌接受度逐年提高",
        ],
        "risks": [
            "三星/苹果等大品牌占据高端市场，价格战风险",
            "产品同质化严重，差异化难度大",
            "售后服务（退换货）成本较高",
            "Coupang平台佣金和物流费用持续上涨",
        ],
        "entry_strategy": "建议以中低价位(15000-35000 KRW)切入市场，主打ANC降噪+长续航+防水三大卖点。通过火箭配送（Rocket Growth）提升曝光，初期以低利润率换取销量和评论积累。",
    },
}


def main():
    set_language("zh_CN")

    print("""
╔══════════════════════════════════════════════════╗
║     Coupang 选品系统 - 演示运行 (Demo Mode)       ║
║     关键词: 무선 이어폰 (无线耳机)                 ║
╚══════════════════════════════════════════════════╝
    """)

    # Step 1: 准备模拟数据
    logger.info("Step 1/6: 加载产品数据 (15 products)...")
    products = MOCK_PRODUCTS

    # Step 2: 生成运营数据
    logger.info("Step 2/6: 生成30天运营数据...")
    daily_stats = generate_daily_stats(products)

    # Step 3: 数据筛选
    logger.info("Step 3/6: 执行数据筛选...")
    data_filter = DataFilter()
    filter_result = data_filter.filter_products(products, daily_stats)
    products = filter_result["kept"]
    logger.info(f"筛选后保留 {len(products)} 个产品")

    # Step 4: 评论分析
    logger.info("Step 4/6: 生成评论分析数据...")
    review_analyses = generate_review_analyses(products)

    # Step 5: 货源与利润计算
    logger.info("Step 5/6: 计算利润...")
    products = generate_sources(products)

    profit_calculator = ProfitCalculator(params={
        "exchange_rate": 190.0,
        "freight_per_kg": 15.0,
        "commission_rate": 0.10,
        "delivery_fee_krw": 3500,
        "vat_rate": 0.10,
        "misc_cost_rmb": 2.0,
        "return_rate": 0.05,
    })

    all_profit_results = []
    for p in products:
        sources = p.get("sources_1688", [])
        if sources and p.get("price"):
            results = profit_calculator.batch_compare(p["price"], sources, p.get("weight_kg", 0.1))
            p["profit_analysis"] = results
            all_profit_results.extend(results[:2])

    # Step 6: 生成报告
    logger.info("Step 6/6: 生成分析报告...")

    # 尝试使用AI生成建议
    ai_client = None
    try:
        from openai import OpenAI
        api_key = os.environ.get("OPENAI_API_KEY")
        if api_key:
            ai_client = OpenAI()
            logger.info("AI 模块已启用 (GPT-4.1-mini)")
    except Exception:
        pass

    generator = ReportGenerator(ai_client=ai_client)
    report_path = generator.generate(
        keyword=KEYWORD,
        products=products,
        category_analysis=MOCK_CATEGORY_ANALYSIS,
        profit_results=all_profit_results,
        review_analyses=review_analyses,
        detail_analyses={},
        output_dir="reports",
    )

    print(f"\n{'='*60}")
    print(f"  报告已生成: {report_path}")
    print(f"{'='*60}\n")

    # 同时保存原始数据
    raw_data = {
        "keyword": KEYWORD,
        "timestamp": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "products_count": len(products),
        "products": products,
        "category_analysis": MOCK_CATEGORY_ANALYSIS,
        "profit_results_count": len(all_profit_results),
    }
    os.makedirs("data", exist_ok=True)
    raw_path = f"data/raw_{KEYWORD}_{raw_data['timestamp']}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(raw_data, f, ensure_ascii=False, indent=2, default=str)
    print(f"  原始数据: {raw_path}")

    return report_path


if __name__ == "__main__":
    main()
