"""
Amazon Visionary Sourcing Tool - Test Configuration

pytest conftest.py 提供公共 fixture 和测试环境配置。
"""

import os
import sys
import pytest

# 确保项目根目录在 sys.path 中
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# 设置测试环境变量
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("TESTING", "1")


@pytest.fixture(scope="session")
def app():
    """创建 Flask 应用实例（测试模式）"""
    from app import app as flask_app
    flask_app.config["TESTING"] = True
    flask_app.config["WTF_CSRF_ENABLED"] = False
    return flask_app


@pytest.fixture(scope="session")
def client(app):
    """创建 Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def sample_product():
    """示例产品数据"""
    return {
        "asin": "B0TEST12345",
        "title": "Test Product - Wireless Bluetooth Speaker",
        "price": 29.99,
        "rating": 4.3,
        "review_count": 1250,
        "bsr": 5432,
        "brand": "TestBrand",
        "category": "Electronics",
        "fulfillment": {"type": "FBA", "is_prime": True},
        "is_sponsored": False,
        "image_url": "https://example.com/image.jpg",
    }


@pytest.fixture
def sample_products():
    """示例产品列表"""
    return [
        {
            "asin": "B0TEST00001",
            "title": "Bluetooth Speaker Portable",
            "price": 25.99,
            "rating": 4.5,
            "review_count": 3200,
            "bsr": 1200,
            "brand": "SpeakerPro",
            "fulfillment": {"type": "FBA", "is_prime": True},
        },
        {
            "asin": "B0TEST00002",
            "title": "Wireless Speaker Waterproof",
            "price": 35.99,
            "rating": 4.2,
            "review_count": 890,
            "bsr": 3500,
            "brand": "AquaSound",
            "fulfillment": {"type": "FBA", "is_prime": True},
        },
        {
            "asin": "B0TEST00003",
            "title": "Mini Bluetooth Speaker",
            "price": 15.99,
            "rating": 3.8,
            "review_count": 450,
            "bsr": 8900,
            "brand": "MiniAudio",
            "fulfillment": {"type": "FBM", "is_prime": False},
        },
        {
            "asin": "B0TEST00004",
            "title": "Speaker Charging Cable",
            "price": 8.99,
            "rating": 4.0,
            "review_count": 120,
            "bsr": 25000,
            "brand": "CableCo",
            "fulfillment": {"type": "FBA", "is_prime": True},
        },
        {
            "asin": "B0TEST00005",
            "title": "Premium Sound System 5.1",
            "price": 299.99,
            "rating": 4.7,
            "review_count": 5600,
            "bsr": 450,
            "brand": "AudioElite",
            "fulfillment": {"type": "FBA", "is_prime": True},
        },
    ]


@pytest.fixture
def sample_keepa_data():
    """示例 Keepa 数据"""
    return {
        "B0TEST00001": {
            "estimated_monthly_sales": 850,
            "estimated_monthly_revenue": 22093.5,
            "avg_price": 25.99,
            "avg_bsr": 1150,
        },
        "B0TEST00002": {
            "estimated_monthly_sales": 320,
            "estimated_monthly_revenue": 11516.8,
            "avg_price": 35.99,
            "avg_bsr": 3400,
        },
    }
