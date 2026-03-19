"""
Coupang 选品系统 - 数据库模型层
统一导出所有 ORM 模型，覆盖 schema.sql 中的 31 张表
"""

# 基础模型 (原有)
from database.models import (
    KeywordModel,
    ProductModel,
    DailyMetricsModel,
    ReviewModel,
    ProfitModel,
)

# 用户系统模型
from database.models_user import (
    UserModel,
    UserOAuthModel,
)

# 项目管理模型
from database.models_project import (
    SourcingProjectModel,
    ProjectProductModel,
    AnalysisTaskModel,
)

# 分析结果模型
from database.models_analysis import (
    CategoryModel,
    MonthlySummaryModel,
    ProductImageModel,
    ReviewAnalysisModel,
    DetailPageAnalysisModel,
    ProfitAnalysisModel,
    TrendDataModel,
    AnalysisReportModel,
    ProfitCalculationModel,
    Asset3DModel,
)

# 系统运维与商业化模型
from database.models_system import (
    CrawlLogModel,
    ApiUsageLogModel,
    UsageRecordModel,
    SubscriptionLogModel,
    AffiliateClickModel,
    SystemConfigModel,
    AuditLogModel,
    NotificationModel,
    TeamModel,
    TeamMemberModel,
    TeamInvitationModel,
    MigrationModel,
)

__all__ = [
    # 基础模型
    "KeywordModel",
    "ProductModel",
    "DailyMetricsModel",
    "ReviewModel",
    "ProfitModel",
    # 用户系统
    "UserModel",
    "UserOAuthModel",
    # 项目管理
    "SourcingProjectModel",
    "ProjectProductModel",
    "AnalysisTaskModel",
    # 分析结果
    "CategoryModel",
    "MonthlySummaryModel",
    "ProductImageModel",
    "ReviewAnalysisModel",
    "DetailPageAnalysisModel",
    "ProfitAnalysisModel",
    "TrendDataModel",
    "AnalysisReportModel",
    "ProfitCalculationModel",
    "Asset3DModel",
    # 系统运维与商业化
    "CrawlLogModel",
    "ApiUsageLogModel",
    "UsageRecordModel",
    "SubscriptionLogModel",
    "AffiliateClickModel",
    "SystemConfigModel",
    "AuditLogModel",
    "NotificationModel",
    "TeamModel",
    "TeamMemberModel",
    "TeamInvitationModel",
    "MigrationModel",
]
