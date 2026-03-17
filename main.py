#!/usr/bin/env python3
"""
Coupang 选品系统 - 命令行入口
用法:
  python main.py --keyword "키워드" [选项]
"""

import os
import sys
import argparse
import json

# 将项目根目录加入 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline import SelectionPipeline
from i18n import t, set_language


def parse_args():
    parser = argparse.ArgumentParser(
        description="Coupang Product Selection System / Coupang 选品系统 / 쿠팡 상품 선정 시스템",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples / 示例 / 예시:

  # 基础用法 - 搜索关键词并生成报告
  python main.py --keyword "무선 이어폰" --lang zh_CN

  # 跳过后台数据和1688搜货（快速模式）
  python main.py --keyword "보조배터리" --skip-backend --skip-1688

  # 完整模式（含Wing后台数据）
  python main.py --keyword "텀블러" --wing-user your@email.com --wing-pass yourpass

  # 使用配置文件
  python main.py --config config.json
        """
    )

    # 必需参数
    parser.add_argument("--keyword", "-k", type=str,
                        help="搜索关键词 / Search keyword / 검색 키워드")

    # 语言设置
    parser.add_argument("--lang", "-l", type=str, default="zh_CN",
                        choices=["zh_CN", "en_US", "ko_KR"],
                        help="输出语言 (default: zh_CN)")

    # 爬取参数
    parser.add_argument("--max-products", "-m", type=int, default=50,
                        help="最大产品数 (default: 50)")

    # 跳过选项
    parser.add_argument("--skip-backend", action="store_true",
                        help="跳过Wing后台数据爬取")
    parser.add_argument("--skip-1688", action="store_true",
                        help="跳过1688货源搜索")

    # Wing 后台账号
    parser.add_argument("--wing-user", type=str, default=None,
                        help="Coupang Wing 后台账号")
    parser.add_argument("--wing-pass", type=str, default=None,
                        help="Coupang Wing 后台密码")

    # AI 配置
    parser.add_argument("--openai-key", type=str, default=None,
                        help="OpenAI API Key (或设置环境变量 OPENAI_API_KEY)")

    # 输出配置
    parser.add_argument("--output-dir", "-o", type=str, default="reports",
                        help="报告输出目录 (default: reports)")
    parser.add_argument("--save-raw", action="store_true",
                        help="同时保存原始数据JSON")

    # 配置文件
    parser.add_argument("--config", "-c", type=str, default=None,
                        help="JSON配置文件路径")

    # 利润参数
    parser.add_argument("--exchange-rate", type=float, default=190.0,
                        help="人民币对韩元汇率 (default: 190)")
    parser.add_argument("--freight-per-kg", type=float, default=15.0,
                        help="头程运费 RMB/kg (default: 15)")
    parser.add_argument("--commission-rate", type=float, default=0.10,
                        help="平台佣金比例 (default: 0.10)")

    return parser.parse_args()


def load_config(args) -> dict:
    """合并配置文件和命令行参数"""
    config = {}

    # 从配置文件加载
    if args.config and os.path.exists(args.config):
        with open(args.config, "r", encoding="utf-8") as f:
            config = json.load(f)

    # 命令行参数覆盖
    config["language"] = args.lang
    config["output_dir"] = args.output_dir

    if args.openai_key:
        config["openai_api_key"] = args.openai_key

    # 利润参数
    config.setdefault("profit_params", {})
    config["profit_params"]["exchange_rate"] = args.exchange_rate
    config["profit_params"]["freight_per_kg"] = args.freight_per_kg
    config["profit_params"]["commission_rate"] = args.commission_rate

    return config


def print_banner(lang: str):
    """打印启动横幅"""
    banners = {
        "zh_CN": """
╔══════════════════════════════════════════════════╗
║         Coupang 跨境电商智能选品系统              ║
║         Cross-border Product Selection           ║
║                   v1.0                           ║
╚══════════════════════════════════════════════════╝
""",
        "en_US": """
╔══════════════════════════════════════════════════╗
║     Coupang Product Selection System             ║
║     Cross-border E-commerce Intelligence         ║
║                   v1.0                           ║
╚══════════════════════════════════════════════════╝
""",
        "ko_KR": """
╔══════════════════════════════════════════════════╗
║        쿠팡 크로스보더 상품 선정 시스템             ║
║        Cross-border Product Selection            ║
║                   v1.0                           ║
╚══════════════════════════════════════════════════╝
""",
    }
    print(banners.get(lang, banners["zh_CN"]))


def interactive_mode(config: dict):
    """交互式模式（无命令行参数时）"""
    lang = config.get("language", "zh_CN")
    set_language(lang)

    prompts = {
        "zh_CN": {
            "keyword": "请输入搜索关键词（韩文）: ",
            "max": "最大产品数 [50]: ",
            "wing": "是否有Wing后台账号? (y/N): ",
            "wing_user": "Wing账号: ",
            "wing_pass": "Wing密码: ",
            "source": "是否搜索1688货源? (Y/n): ",
        },
        "en_US": {
            "keyword": "Enter search keyword (Korean): ",
            "max": "Max products [50]: ",
            "wing": "Have Wing backend account? (y/N): ",
            "wing_user": "Wing username: ",
            "wing_pass": "Wing password: ",
            "source": "Search 1688 sources? (Y/n): ",
        },
        "ko_KR": {
            "keyword": "검색 키워드를 입력하세요: ",
            "max": "최대 제품 수 [50]: ",
            "wing": "Wing 계정이 있습니까? (y/N): ",
            "wing_user": "Wing 계정: ",
            "wing_pass": "Wing 비밀번호: ",
            "source": "1688 소싱 검색? (Y/n): ",
        },
    }
    p = prompts.get(lang, prompts["zh_CN"])

    keyword = input(p["keyword"]).strip()
    if not keyword:
        print("Error: keyword is required")
        sys.exit(1)

    max_str = input(p["max"]).strip()
    max_products = int(max_str) if max_str else 50

    skip_backend = True
    wing_user = None
    wing_pass = None
    if input(p["wing"]).strip().lower() == "y":
        wing_user = input(p["wing_user"]).strip()
        wing_pass = input(p["wing_pass"]).strip()
        skip_backend = False

    skip_1688 = input(p["source"]).strip().lower() == "n"

    return keyword, max_products, skip_backend, skip_1688, wing_user, wing_pass


def main():
    args = parse_args()
    config = load_config(args)

    print_banner(args.lang)
    set_language(args.lang)

    # 确定运行参数
    if args.keyword:
        keyword = args.keyword
        max_products = args.max_products
        skip_backend = args.skip_backend
        skip_1688 = args.skip_1688
        wing_user = args.wing_user
        wing_pass = args.wing_pass
    else:
        keyword, max_products, skip_backend, skip_1688, wing_user, wing_pass = interactive_mode(config)

    # 创建并运行 Pipeline
    pipeline = SelectionPipeline(config=config)

    report_path = pipeline.run(
        keyword=keyword,
        max_products=max_products,
        skip_backend=skip_backend,
        skip_1688=skip_1688,
        wing_username=wing_user,
        wing_password=wing_pass,
    )

    if report_path:
        print(f"\n✅ {t('pipeline.report_ready')}: {report_path}")

    # 保存原始数据
    if args.save_raw:
        raw_path = pipeline.save_raw_data(keyword)
        print(f"📦 Raw data: {raw_path}")


if __name__ == "__main__":
    main()
