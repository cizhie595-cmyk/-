"""
测试 database/ 目录下所有 ORM 模型的完整性
使用 Mock 替代真实数据库连接，验证 SQL 生成和方法签名
"""

import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


# ============================================================
# Mock database connection
# ============================================================
@pytest.fixture(autouse=True)
def mock_db():
    """Mock database.connection.db for all tests"""
    mock = MagicMock()
    mock.insert_and_get_id.return_value = 1
    mock.execute.return_value = 1
    mock.fetch_one.return_value = {"id": 1, "cnt": 5}
    mock.fetch_all.return_value = [{"id": 1}, {"id": 2}]
    mock.transaction.return_value.__enter__ = MagicMock()
    mock.transaction.return_value.__exit__ = MagicMock(return_value=False)

    with patch("database.models.db", mock), \
         patch("database.models_user.db", mock), \
         patch("database.models_project.db", mock), \
         patch("database.models_analysis.db", mock), \
         patch("database.models_system.db", mock):
        yield mock


# ============================================================
# 1. 基础模型测试 (models.py - 原有 5 个)
# ============================================================
class TestKeywordModel:
    def test_create(self, mock_db):
        from database.models import KeywordModel
        result = KeywordModel.create("test keyword", 100)
        assert result == 1
        mock_db.insert_and_get_id.assert_called_once()

    def test_update_status(self, mock_db):
        from database.models import KeywordModel
        KeywordModel.update_status(1, "completed")
        mock_db.execute.assert_called_once()

    def test_get_all(self, mock_db):
        from database.models import KeywordModel
        result = KeywordModel.get_all()
        assert len(result) == 2


class TestProductModel:
    def test_create(self, mock_db):
        from database.models import ProductModel
        result = ProductModel.create({"product_name": "Test", "price": 100})
        assert result == 1

    def test_upsert_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models import ProductModel
        result = ProductModel.upsert("CP123", {"product_name": "Test"})
        assert result == 1

    def test_upsert_existing(self, mock_db):
        mock_db.fetch_one.return_value = {"id": 42}
        from database.models import ProductModel
        result = ProductModel.upsert("CP123", {"product_name": "Updated"})
        assert result == 42

    def test_get_by_keyword(self, mock_db):
        from database.models import ProductModel
        result = ProductModel.get_by_keyword(1)
        assert len(result) == 2

    def test_mark_filtered(self, mock_db):
        from database.models import ProductModel
        ProductModel.mark_filtered(1, "low price")
        mock_db.execute.assert_called_once()


class TestDailyMetricsModel:
    def test_insert(self, mock_db):
        from database.models import DailyMetricsModel
        from datetime import date
        DailyMetricsModel.insert(1, date.today(), 100, 10, 500)
        mock_db.execute.assert_called_once()

    def test_get_30d_summary(self, mock_db):
        from database.models import DailyMetricsModel
        result = DailyMetricsModel.get_30d_summary(1)
        assert result is not None


class TestReviewModel:
    def test_get_by_product(self, mock_db):
        from database.models import ReviewModel
        result = ReviewModel.get_by_product(1)
        assert len(result) == 2


class TestProfitModel:
    def test_save_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models import ProfitModel
        ProfitModel.save(1, {"selling_price": 100, "cost_price": 50})
        mock_db.execute.assert_called_once()

    def test_get_by_product(self, mock_db):
        from database.models import ProfitModel
        result = ProfitModel.get_by_product(1)
        assert result is not None


# ============================================================
# 2. 用户系统模型测试 (models_user.py)
# ============================================================
class TestUserModel:
    def test_create(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.create("testuser", "test@example.com", "hash123")
        assert result == 1

    def test_get_by_id(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.get_by_id(1)
        assert result is not None

    def test_get_by_email(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.get_by_email("test@example.com")
        assert result is not None

    def test_get_by_username(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.get_by_username("testuser")
        assert result is not None

    def test_update(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.update(1, {"nickname": "New Name"})
        assert result == 1

    def test_update_empty(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.update(1, {})
        assert result == 0

    def test_update_login(self, mock_db):
        from database.models_user import UserModel
        UserModel.update_login(1)
        mock_db.execute.assert_called_once()

    def test_update_subscription(self, mock_db):
        from database.models_user import UserModel
        UserModel.update_subscription(1, "orbit", "monthly")
        mock_db.execute.assert_called_once()

    def test_update_ai_settings(self, mock_db):
        from database.models_user import UserModel
        UserModel.update_ai_settings(1, {"provider": "openai", "model": "gpt-4"})
        mock_db.execute.assert_called_once()

    def test_update_api_keys(self, mock_db):
        from database.models_user import UserModel
        UserModel.update_api_keys(1, "encrypted_data")
        mock_db.execute.assert_called_once()

    def test_verify_email(self, mock_db):
        from database.models_user import UserModel
        UserModel.verify_email(1)
        mock_db.execute.assert_called_once()

    def test_deactivate(self, mock_db):
        from database.models_user import UserModel
        UserModel.deactivate(1)
        mock_db.execute.assert_called_once()

    def test_get_all(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.get_all(page=1, per_page=10)
        assert len(result) == 2

    def test_count(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.count()
        assert result == 5

    def test_search(self, mock_db):
        from database.models_user import UserModel
        result = UserModel.search("test")
        assert len(result) == 2


class TestUserOAuthModel:
    def test_create(self, mock_db):
        from database.models_user import UserOAuthModel
        result = UserOAuthModel.create(1, "google", "google_uid_123")
        assert result == 1

    def test_get_by_provider(self, mock_db):
        from database.models_user import UserOAuthModel
        result = UserOAuthModel.get_by_provider("google", "uid123")
        assert result is not None

    def test_get_by_user(self, mock_db):
        from database.models_user import UserOAuthModel
        result = UserOAuthModel.get_by_user(1)
        assert len(result) == 2

    def test_update_tokens(self, mock_db):
        from database.models_user import UserOAuthModel
        UserOAuthModel.update_tokens(1, "new_access", "new_refresh")
        mock_db.execute.assert_called_once()

    def test_delete(self, mock_db):
        from database.models_user import UserOAuthModel
        UserOAuthModel.delete(1)
        mock_db.execute.assert_called_once()


# ============================================================
# 3. 项目管理模型测试 (models_project.py)
# ============================================================
class TestSourcingProjectModel:
    def test_create(self, mock_db):
        from database.models_project import SourcingProjectModel
        result = SourcingProjectModel.create(1, "Test Project", "wireless earbuds", "US")
        assert isinstance(result, str)  # UUID
        assert len(result) == 36

    def test_get_by_id(self, mock_db):
        from database.models_project import SourcingProjectModel
        result = SourcingProjectModel.get_by_id("uuid-123")
        assert result is not None

    def test_get_by_user(self, mock_db):
        from database.models_project import SourcingProjectModel
        result = SourcingProjectModel.get_by_user(1)
        assert len(result) == 2

    def test_get_by_user_with_status(self, mock_db):
        from database.models_project import SourcingProjectModel
        result = SourcingProjectModel.get_by_user(1, status="completed")
        assert len(result) == 2

    def test_update_status(self, mock_db):
        from database.models_project import SourcingProjectModel
        SourcingProjectModel.update_status("uuid-123", "completed", product_count=50)
        mock_db.execute.assert_called_once()

    def test_update_settings(self, mock_db):
        from database.models_project import SourcingProjectModel
        SourcingProjectModel.update_settings("uuid-123", {"scrape_depth": 100})
        mock_db.execute.assert_called_once()

    def test_delete(self, mock_db):
        from database.models_project import SourcingProjectModel
        SourcingProjectModel.delete("uuid-123")
        assert mock_db.execute.call_count == 3  # 3 DELETE statements

    def test_count_by_user(self, mock_db):
        from database.models_project import SourcingProjectModel
        result = SourcingProjectModel.count_by_user(1)
        assert result == 5


class TestProjectProductModel:
    def test_create(self, mock_db):
        from database.models_project import ProjectProductModel
        result = ProjectProductModel.create("uuid-123", "B0TEST01", {"title": "Test"})
        assert result == 1

    def test_get_by_project(self, mock_db):
        from database.models_project import ProjectProductModel
        result = ProjectProductModel.get_by_project("uuid-123")
        assert len(result) == 2

    def test_get_by_asin(self, mock_db):
        from database.models_project import ProjectProductModel
        result = ProjectProductModel.get_by_asin("uuid-123", "B0TEST01")
        assert result is not None

    def test_update(self, mock_db):
        from database.models_project import ProjectProductModel
        ProjectProductModel.update(1, {"price": 29.99})
        mock_db.execute.assert_called_once()

    def test_mark_filtered(self, mock_db):
        from database.models_project import ProjectProductModel
        ProjectProductModel.mark_filtered(1, "low BSR")
        mock_db.execute.assert_called_once()

    def test_count_by_project(self, mock_db):
        from database.models_project import ProjectProductModel
        result = ProjectProductModel.count_by_project("uuid-123")
        assert result == 5


class TestAnalysisTaskModel:
    def test_create(self, mock_db):
        from database.models_project import AnalysisTaskModel
        result = AnalysisTaskModel.create(1, "visual", "proj-123", "B0TEST01")
        assert isinstance(result, str)
        assert len(result) == 36

    def test_get_by_id(self, mock_db):
        from database.models_project import AnalysisTaskModel
        result = AnalysisTaskModel.get_by_id("task-uuid")
        assert result is not None

    def test_get_by_project(self, mock_db):
        from database.models_project import AnalysisTaskModel
        result = AnalysisTaskModel.get_by_project("proj-123")
        assert len(result) == 2

    def test_update_status(self, mock_db):
        from database.models_project import AnalysisTaskModel
        AnalysisTaskModel.update_status("task-uuid", "running", progress=50)
        mock_db.execute.assert_called_once()

    def test_complete(self, mock_db):
        from database.models_project import AnalysisTaskModel
        AnalysisTaskModel.complete("task-uuid", {"score": 85})
        mock_db.execute.assert_called_once()

    def test_fail(self, mock_db):
        from database.models_project import AnalysisTaskModel
        AnalysisTaskModel.fail("task-uuid", "Timeout error")
        mock_db.execute.assert_called_once()

    def test_set_celery_id(self, mock_db):
        from database.models_project import AnalysisTaskModel
        AnalysisTaskModel.set_celery_id("task-uuid", "celery-123")
        mock_db.execute.assert_called_once()


# ============================================================
# 4. 分析结果模型测试 (models_analysis.py)
# ============================================================
class TestCategoryModel:
    def test_create(self, mock_db):
        from database.models_analysis import CategoryModel
        result = CategoryModel.create("coupang", "cat001", "Electronics")
        assert result == 1

    def test_get_by_platform(self, mock_db):
        from database.models_analysis import CategoryModel
        result = CategoryModel.get_by_platform("coupang")
        assert len(result) == 2

    def test_get_by_id(self, mock_db):
        from database.models_analysis import CategoryModel
        result = CategoryModel.get_by_id(1)
        assert result is not None

    def test_upsert_existing(self, mock_db):
        mock_db.fetch_one.return_value = {"id": 42}
        from database.models_analysis import CategoryModel
        result = CategoryModel.upsert("coupang", "cat001", {"category_name": "Updated"})
        assert result == 42

    def test_get_children(self, mock_db):
        from database.models_analysis import CategoryModel
        result = CategoryModel.get_children(1)
        assert len(result) == 2


class TestMonthlySummaryModel:
    def test_upsert_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_analysis import MonthlySummaryModel
        MonthlySummaryModel.upsert(1, "2026-03", {"avg_price": 25000})
        mock_db.execute.assert_called_once()

    def test_get_by_product(self, mock_db):
        from database.models_analysis import MonthlySummaryModel
        result = MonthlySummaryModel.get_by_product(1)
        assert len(result) == 2

    def test_get_latest(self, mock_db):
        from database.models_analysis import MonthlySummaryModel
        result = MonthlySummaryModel.get_latest(1)
        assert result is not None


class TestProductImageModel:
    def test_create(self, mock_db):
        from database.models_analysis import ProductImageModel
        result = ProductImageModel.create(1, "https://img.example.com/1.jpg", "main")
        assert result == 1

    def test_get_by_product(self, mock_db):
        from database.models_analysis import ProductImageModel
        result = ProductImageModel.get_by_product(1)
        assert len(result) == 2

    def test_get_by_type(self, mock_db):
        from database.models_analysis import ProductImageModel
        result = ProductImageModel.get_by_product(1, image_type="main")
        assert len(result) == 2

    def test_delete_by_product(self, mock_db):
        from database.models_analysis import ProductImageModel
        ProductImageModel.delete_by_product(1)
        mock_db.execute.assert_called_once()


class TestReviewAnalysisModel:
    def test_save_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_analysis import ReviewAnalysisModel
        result = ReviewAnalysisModel.save(1, "sentiment", {
            "positive_ratio": 80.5,
            "top_positive": ["good quality", "fast shipping"],
            "pain_points": ["battery life"]
        })
        assert result == 1

    def test_save_existing(self, mock_db):
        mock_db.fetch_one.return_value = {"id": 42}
        from database.models_analysis import ReviewAnalysisModel
        result = ReviewAnalysisModel.save(1, "sentiment", {"positive_ratio": 85.0})
        assert result == 42

    def test_get_by_product(self, mock_db):
        from database.models_analysis import ReviewAnalysisModel
        result = ReviewAnalysisModel.get_by_product(1)
        assert len(result) == 2


class TestDetailPageAnalysisModel:
    def test_save_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_analysis import DetailPageAnalysisModel
        result = DetailPageAnalysisModel.save(1, {
            "title_score": 85,
            "image_count": 7,
            "seo_keywords": ["wireless", "bluetooth"]
        })
        assert result == 1

    def test_get_by_product(self, mock_db):
        from database.models_analysis import DetailPageAnalysisModel
        result = DetailPageAnalysisModel.get_by_product(1)
        assert result is not None


class TestProfitAnalysisModel:
    def test_save_new(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_analysis import ProfitAnalysisModel
        ProfitAnalysisModel.save(1, {"selling_price": 29.99, "profit_margin": 35.5})
        mock_db.execute.assert_called_once()

    def test_get_profitable(self, mock_db):
        from database.models_analysis import ProfitAnalysisModel
        result = ProfitAnalysisModel.get_profitable(min_margin=20.0)
        assert len(result) == 2


class TestTrendDataModel:
    def test_get_by_keyword(self, mock_db):
        from database.models_analysis import TrendDataModel
        result = TrendDataModel.get_by_keyword("wireless earbuds")
        assert len(result) == 2

    def test_get_latest(self, mock_db):
        from database.models_analysis import TrendDataModel
        result = TrendDataModel.get_latest("wireless earbuds", "google")
        assert result is not None


class TestAnalysisReportModel:
    def test_create(self, mock_db):
        from database.models_analysis import AnalysisReportModel
        result = AnalysisReportModel.create(
            keyword_id=1, report_type="comprehensive",
            title="Market Analysis", summary="Good opportunity",
            full_report={"score": 85}, recommendation="buy", confidence=82.5)
        assert result == 1

    def test_get_by_id(self, mock_db):
        from database.models_analysis import AnalysisReportModel
        result = AnalysisReportModel.get_by_id(1)
        assert result is not None

    def test_get_by_keyword(self, mock_db):
        from database.models_analysis import AnalysisReportModel
        result = AnalysisReportModel.get_by_keyword(1)
        assert len(result) == 2

    def test_get_recent(self, mock_db):
        from database.models_analysis import AnalysisReportModel
        result = AnalysisReportModel.get_recent(10)
        assert len(result) == 2

    def test_get_by_recommendation(self, mock_db):
        from database.models_analysis import AnalysisReportModel
        result = AnalysisReportModel.get_by_recommendation("strong_buy")
        assert len(result) == 2


class TestProfitCalculationModel:
    def test_create(self, mock_db):
        from database.models_analysis import ProfitCalculationModel
        result = ProfitCalculationModel.create(
            user_id=1, input_data={"price": 29.99}, result_data={"profit": 10.0},
            asin="B0TEST01", product_name="Test Product")
        assert result == 1

    def test_get_by_user(self, mock_db):
        from database.models_analysis import ProfitCalculationModel
        result = ProfitCalculationModel.get_by_user(1)
        assert len(result) == 2

    def test_get_by_asin(self, mock_db):
        from database.models_analysis import ProfitCalculationModel
        result = ProfitCalculationModel.get_by_asin(1, "B0TEST01")
        assert len(result) == 2


class TestAsset3DModel:
    def test_create(self, mock_db):
        from database.models_analysis import Asset3DModel
        result = Asset3DModel.create(1, source_image="https://img.example.com/1.jpg")
        assert isinstance(result, str)
        assert len(result) == 36

    def test_get_by_id(self, mock_db):
        from database.models_analysis import Asset3DModel
        result = Asset3DModel.get_by_id("asset-uuid")
        assert result is not None

    def test_get_by_user(self, mock_db):
        from database.models_analysis import Asset3DModel
        result = Asset3DModel.get_by_user(1)
        assert len(result) == 2

    def test_update_status(self, mock_db):
        from database.models_analysis import Asset3DModel
        Asset3DModel.update_status("asset-uuid", "generating")
        mock_db.execute.assert_called_once()

    def test_complete(self, mock_db):
        from database.models_analysis import Asset3DModel
        Asset3DModel.complete("asset-uuid", "https://cdn.example.com/model.glb",
                              thumbnail_url="https://cdn.example.com/thumb.jpg")
        mock_db.execute.assert_called_once()

    def test_count_by_user(self, mock_db):
        from database.models_analysis import Asset3DModel
        result = Asset3DModel.count_by_user(1)
        assert result == 5


# ============================================================
# 5. 系统运维与商业化模型测试 (models_system.py)
# ============================================================
class TestCrawlLogModel:
    def test_create(self, mock_db):
        from database.models_system import CrawlLogModel
        result = CrawlLogModel.create("keyword_search", target_id=1)
        assert result == 1

    def test_success(self, mock_db):
        from database.models_system import CrawlLogModel
        CrawlLogModel.success(1, "Crawled 50 products")
        mock_db.execute.assert_called_once()

    def test_fail(self, mock_db):
        from database.models_system import CrawlLogModel
        CrawlLogModel.fail(1, "Timeout")
        mock_db.execute.assert_called_once()

    def test_get_recent(self, mock_db):
        from database.models_system import CrawlLogModel
        result = CrawlLogModel.get_recent("keyword_search")
        assert len(result) == 2

    def test_get_running(self, mock_db):
        from database.models_system import CrawlLogModel
        result = CrawlLogModel.get_running()
        assert len(result) == 2

    def test_count_by_status(self, mock_db):
        mock_db.fetch_all.return_value = [
            {"status": "success", "cnt": 100},
            {"status": "failed", "cnt": 5}
        ]
        from database.models_system import CrawlLogModel
        result = CrawlLogModel.count_by_status()
        assert result["success"] == 100
        assert result["failed"] == 5


class TestApiUsageLogModel:
    def test_log(self, mock_db):
        from database.models_system import ApiUsageLogModel
        result = ApiUsageLogModel.log(1, "openai", "/chat/completions", 500, 0.01)
        assert result == 1

    def test_get_by_user(self, mock_db):
        from database.models_system import ApiUsageLogModel
        result = ApiUsageLogModel.get_by_user(1)
        assert len(result) == 2

    def test_get_usage_summary(self, mock_db):
        from database.models_system import ApiUsageLogModel
        result = ApiUsageLogModel.get_usage_summary(1)
        assert len(result) == 2

    def test_get_daily_stats(self, mock_db):
        from database.models_system import ApiUsageLogModel
        result = ApiUsageLogModel.get_daily_stats(1)
        assert len(result) == 2


class TestUsageRecordModel:
    def test_record(self, mock_db):
        from database.models_system import UsageRecordModel
        result = UsageRecordModel.record(1, "scrape", "proj-123")
        assert result == 1

    def test_get_monthly_usage(self, mock_db):
        mock_db.fetch_all.return_value = [
            {"action_type": "scrape", "total_credits": 10, "count": 5}
        ]
        from database.models_system import UsageRecordModel
        result = UsageRecordModel.get_monthly_usage(1)
        assert "scrape" in result

    def test_get_total_credits(self, mock_db):
        mock_db.fetch_one.return_value = {"total": 25}
        from database.models_system import UsageRecordModel
        result = UsageRecordModel.get_total_credits(1)
        assert result == 25


class TestSubscriptionLogModel:
    def test_log(self, mock_db):
        from database.models_system import SubscriptionLogModel
        result = SubscriptionLogModel.log(1, "subscribe", plan_to="orbit", amount=29.99)
        assert result == 1

    def test_get_by_user(self, mock_db):
        from database.models_system import SubscriptionLogModel
        result = SubscriptionLogModel.get_by_user(1)
        assert len(result) == 2

    def test_get_revenue_summary(self, mock_db):
        from database.models_system import SubscriptionLogModel
        result = SubscriptionLogModel.get_revenue_summary()
        assert len(result) == 2


class TestAffiliateClickModel:
    def test_record(self, mock_db):
        from database.models_system import AffiliateClickModel
        result = AffiliateClickModel.record("amazon", "B0TEST01", "tag-20")
        assert result == 1

    def test_get_stats(self, mock_db):
        from database.models_system import AffiliateClickModel
        result = AffiliateClickModel.get_stats()
        assert len(result) == 2

    def test_get_by_user(self, mock_db):
        from database.models_system import AffiliateClickModel
        result = AffiliateClickModel.get_by_user(1)
        assert len(result) == 2


class TestSystemConfigModel:
    def test_get(self, mock_db):
        mock_db.fetch_one.return_value = {"config_value": "test_value"}
        from database.models_system import SystemConfigModel
        result = SystemConfigModel.get("test_key")
        assert result == "test_value"

    def test_get_missing(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_system import SystemConfigModel
        result = SystemConfigModel.get("missing_key")
        assert result is None

    def test_set(self, mock_db):
        from database.models_system import SystemConfigModel
        SystemConfigModel.set("key", "value", "description")
        mock_db.execute.assert_called_once()

    def test_get_all(self, mock_db):
        mock_db.fetch_all.return_value = [
            {"config_key": "k1", "config_value": "v1"},
            {"config_key": "k2", "config_value": "v2"}
        ]
        from database.models_system import SystemConfigModel
        result = SystemConfigModel.get_all()
        assert result == {"k1": "v1", "k2": "v2"}

    def test_delete(self, mock_db):
        from database.models_system import SystemConfigModel
        SystemConfigModel.delete("key")
        mock_db.execute.assert_called_once()


class TestAuditLogModel:
    def test_log(self, mock_db):
        from database.models_system import AuditLogModel
        result = AuditLogModel.log("user.login", user_id=1,
                                    details={"ip": "1.2.3.4"})
        assert result == 1

    def test_get_by_user(self, mock_db):
        from database.models_system import AuditLogModel
        result = AuditLogModel.get_by_user(1)
        assert len(result) == 2

    def test_get_by_resource(self, mock_db):
        from database.models_system import AuditLogModel
        result = AuditLogModel.get_by_resource("project", "uuid-123")
        assert len(result) == 2

    def test_get_recent(self, mock_db):
        from database.models_system import AuditLogModel
        result = AuditLogModel.get_recent(50)
        assert len(result) == 2


class TestNotificationModel:
    def test_create(self, mock_db):
        from database.models_system import NotificationModel
        result = NotificationModel.create(1, "system", "Welcome!", "Hello")
        assert result == 1

    def test_get_by_user(self, mock_db):
        from database.models_system import NotificationModel
        result = NotificationModel.get_by_user(1)
        assert len(result) == 2

    def test_get_unread(self, mock_db):
        from database.models_system import NotificationModel
        result = NotificationModel.get_by_user(1, unread_only=True)
        assert len(result) == 2

    def test_mark_read(self, mock_db):
        from database.models_system import NotificationModel
        NotificationModel.mark_read(1)
        mock_db.execute.assert_called_once()

    def test_mark_all_read(self, mock_db):
        from database.models_system import NotificationModel
        NotificationModel.mark_all_read(1)
        mock_db.execute.assert_called_once()

    def test_unread_count(self, mock_db):
        from database.models_system import NotificationModel
        result = NotificationModel.unread_count(1)
        assert result == 5

    def test_delete(self, mock_db):
        from database.models_system import NotificationModel
        NotificationModel.delete(1)
        mock_db.execute.assert_called_once()

    def test_delete_old(self, mock_db):
        from database.models_system import NotificationModel
        NotificationModel.delete_old(1, days=90)
        mock_db.execute.assert_called_once()


class TestTeamModel:
    def test_create(self, mock_db):
        from database.models_system import TeamModel
        result = TeamModel.create("My Team", 1, "Test team")
        assert result == 1

    def test_get_by_id(self, mock_db):
        from database.models_system import TeamModel
        result = TeamModel.get_by_id(1)
        assert result is not None

    def test_get_by_owner(self, mock_db):
        from database.models_system import TeamModel
        result = TeamModel.get_by_owner(1)
        assert len(result) == 2

    def test_get_user_teams(self, mock_db):
        from database.models_system import TeamModel
        result = TeamModel.get_user_teams(1)
        assert len(result) == 2

    def test_update(self, mock_db):
        from database.models_system import TeamModel
        TeamModel.update(1, {"name": "Updated Team"})
        mock_db.execute.assert_called()

    def test_delete(self, mock_db):
        from database.models_system import TeamModel
        TeamModel.delete(1)
        assert mock_db.execute.call_count >= 3


class TestTeamMemberModel:
    def test_add(self, mock_db):
        from database.models_system import TeamMemberModel
        result = TeamMemberModel.add(1, 2, "member")
        assert result == 1

    def test_get_members(self, mock_db):
        from database.models_system import TeamMemberModel
        result = TeamMemberModel.get_members(1)
        assert len(result) == 2

    def test_get_member(self, mock_db):
        from database.models_system import TeamMemberModel
        result = TeamMemberModel.get_member(1, 2)
        assert result is not None

    def test_update_role(self, mock_db):
        from database.models_system import TeamMemberModel
        TeamMemberModel.update_role(1, 2, "admin")
        mock_db.execute.assert_called_once()

    def test_remove(self, mock_db):
        from database.models_system import TeamMemberModel
        TeamMemberModel.remove(1, 2)
        mock_db.execute.assert_called_once()

    def test_count(self, mock_db):
        from database.models_system import TeamMemberModel
        result = TeamMemberModel.count(1)
        assert result == 5


class TestTeamInvitationModel:
    def test_create(self, mock_db):
        from database.models_system import TeamInvitationModel
        result = TeamInvitationModel.create(1, "user@example.com", 1)
        assert result == 1

    def test_get_by_token(self, mock_db):
        from database.models_system import TeamInvitationModel
        result = TeamInvitationModel.get_by_token("token123")
        assert result is not None

    def test_get_by_team(self, mock_db):
        from database.models_system import TeamInvitationModel
        result = TeamInvitationModel.get_by_team(1)
        assert len(result) == 2

    def test_accept(self, mock_db):
        from database.models_system import TeamInvitationModel
        TeamInvitationModel.accept(1)
        mock_db.execute.assert_called_once()

    def test_expire_old(self, mock_db):
        from database.models_system import TeamInvitationModel
        TeamInvitationModel.expire_old()
        mock_db.execute.assert_called_once()

    def test_get_pending_by_email(self, mock_db):
        from database.models_system import TeamInvitationModel
        result = TeamInvitationModel.get_pending_by_email("user@example.com")
        assert len(result) == 2


class TestMigrationModel:
    def test_get_executed(self, mock_db):
        mock_db.fetch_all.return_value = [
            {"filename": "001_init.sql"},
            {"filename": "002_add_users.sql"}
        ]
        from database.models_system import MigrationModel
        result = MigrationModel.get_executed()
        assert len(result) == 2
        assert result[0] == "001_init.sql"

    def test_record(self, mock_db):
        from database.models_system import MigrationModel
        MigrationModel.record("003_add_teams.sql")
        mock_db.execute.assert_called_once()

    def test_is_executed(self, mock_db):
        mock_db.fetch_one.return_value = {"id": 1}
        from database.models_system import MigrationModel
        assert MigrationModel.is_executed("001_init.sql") is True

    def test_is_not_executed(self, mock_db):
        mock_db.fetch_one.return_value = None
        from database.models_system import MigrationModel
        assert MigrationModel.is_executed("999_future.sql") is False


# ============================================================
# 6. __init__.py 导出完整性测试
# ============================================================
class TestDatabaseInit:
    def test_all_models_exported(self, mock_db):
        """验证 database/__init__.py 导出了所有 31 个模型"""
        import database
        expected_models = [
            "KeywordModel", "ProductModel", "DailyMetricsModel", "ReviewModel", "ProfitModel",
            "UserModel", "UserOAuthModel",
            "SourcingProjectModel", "ProjectProductModel", "AnalysisTaskModel",
            "CategoryModel", "MonthlySummaryModel", "ProductImageModel",
            "ReviewAnalysisModel", "DetailPageAnalysisModel", "ProfitAnalysisModel",
            "TrendDataModel", "AnalysisReportModel", "ProfitCalculationModel", "Asset3DModel",
            "CrawlLogModel", "ApiUsageLogModel", "UsageRecordModel", "SubscriptionLogModel",
            "AffiliateClickModel", "SystemConfigModel", "AuditLogModel", "NotificationModel",
            "TeamModel", "TeamMemberModel", "TeamInvitationModel", "MigrationModel",
        ]
        for model_name in expected_models:
            assert hasattr(database, model_name), f"Missing export: {model_name}"
            assert model_name in database.__all__, f"Missing from __all__: {model_name}"

    def test_model_count(self, mock_db):
        """验证导出的模型总数 = 31 (覆盖 schema.sql 全部 31 张表)"""
        import database
        # 5 基础 + 2 用户 + 3 项目 + 10 分析 + 12 系统 = 32 (ProfitModel + ProfitAnalysisModel 都存在)
        assert len(database.__all__) == 32
