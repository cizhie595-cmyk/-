"""
Coupang 选品系统 - Swagger / OpenAPI 3.0 文档配置
完整覆盖所有 API 端点
"""
import os


SWAGGER_CONFIG = {
    "openapi": "3.0.3",
    "info": {
        "title": "Amazon Visionary Sourcing Tool API",
        "description": (
            "## 概述\n"
            "Amazon Visionary Sourcing Tool 是一款跨境电商智能选品系统，提供产品数据抓取、"
            "AI 分析、利润计算、3D 模型生成等功能。\n\n"
            "## 认证方式\n"
            "所有 API 端点（除登录/注册外）需要在请求头中携带 JWT Token：\n"
            "```\nAuthorization: Bearer <your_jwt_token>\n```\n\n"
            "## 速率限制\n"
            "- Free 用户: 60 次/分钟\n"
            "- Orbit 用户: 200 次/分钟\n"
            "- Moonshot 用户: 1000 次/分钟\n\n"
            "超出限制返回 HTTP 429。\n\n"
            "## 错误格式\n"
            '```json\n{"success": false, "message": "错误描述", "error_code": "ERROR_CODE"}\n```'
        ),
        "version": "1.0.0",
        "contact": {"name": "API Support", "email": os.getenv("SUPPORT_EMAIL", "support@visionary.tool")},
        "license": {"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
    },
    "servers": [{"url": "/", "description": "当前服务器"}],
}


def _jwt():
    return [{"BearerAuth": []}]


def _err(msg="操作失败"):
    return {"description": msg, "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponse"}}}}


def _ok(desc, data_schema=None):
    props = {"success": {"type": "boolean", "example": True}}
    if data_schema:
        props["data"] = data_schema
    return {"description": desc, "content": {"application/json": {"schema": {"type": "object", "properties": props}}}}


def _body(schema, required=True):
    return {"required": required, "content": {"application/json": {"schema": schema}}}


def _param(name, location="path", schema_type="string", required=True, **kw):
    p = {"name": name, "in": location, "required": required, "schema": {"type": schema_type}}
    p["schema"].update(kw)
    return p


def get_openapi_spec():
    spec = dict(SWAGGER_CONFIG)
    spec["tags"] = [
        {"name": "Auth", "description": "用户认证（注册、登录、邮箱验证、密码重置）"},
        {"name": "OAuth", "description": "第三方 OAuth 登录（Google / GitHub）"},
        {"name": "Projects", "description": "选品项目管理（创建、查询、爬取、筛选）"},
        {"name": "Analysis", "description": "AI 分析（市场分析、产品分析、评论分析）"},
        {"name": "Profit", "description": "利润计算（单品、批量、历史记录）"},
        {"name": "3D Lab", "description": "3D 模型生成与视频渲染"},
        {"name": "Export", "description": "数据导出（CSV / Excel / PDF）"},
        {"name": "Supply", "description": "1688 供应商搜索"},
        {"name": "Subscription", "description": "订阅管理与配额"},
        {"name": "Stripe", "description": "Stripe 支付集成"},
        {"name": "Teams", "description": "团队协作管理"},
        {"name": "Notifications", "description": "站内通知系统"},
        {"name": "Dashboard", "description": "仪表盘统计数据"},
        {"name": "Audit", "description": "操作审计日志"},
        {"name": "Admin", "description": "管理员功能（APM、数据清理）"},
        {"name": "Settings", "description": "API 密钥与 AI 设置"},
        {"name": "i18n", "description": "国际化语言包"},
        {"name": "System", "description": "系统健康检查与监控"},
    ]
    spec["components"] = {
        "securitySchemes": {"BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}},
        "schemas": {
            "ErrorResponse": {"type": "object", "properties": {
                "success": {"type": "boolean", "example": False},
                "message": {"type": "string"}, "error_code": {"type": "string"},
            }},
            "User": {"type": "object", "properties": {
                "id": {"type": "integer"}, "username": {"type": "string"},
                "email": {"type": "string", "format": "email"},
                "role": {"type": "string", "enum": ["user", "admin"]},
                "subscription_plan": {"type": "string", "enum": ["free", "orbit", "moonshot"]},
                "email_verified": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"},
            }},
            "Project": {"type": "object", "properties": {
                "id": {"type": "integer"}, "name": {"type": "string"}, "keyword": {"type": "string"},
                "marketplace": {"type": "string"},
                "status": {"type": "string", "enum": ["active", "completed", "archived"]},
                "product_count": {"type": "integer"},
                "created_at": {"type": "string", "format": "date-time"},
            }},
            "Product": {"type": "object", "properties": {
                "asin": {"type": "string"}, "title": {"type": "string"},
                "price": {"type": "number"}, "rating": {"type": "number"},
                "reviews_count": {"type": "integer"}, "bsr": {"type": "integer"},
                "category": {"type": "string"}, "monthly_revenue": {"type": "number"},
            }},
            "Notification": {"type": "object", "properties": {
                "id": {"type": "integer"}, "type": {"type": "string"},
                "title": {"type": "string"}, "message": {"type": "string"},
                "is_read": {"type": "boolean"},
                "created_at": {"type": "string", "format": "date-time"},
            }},
            "Team": {"type": "object", "properties": {
                "id": {"type": "integer"}, "name": {"type": "string"},
                "owner_id": {"type": "integer"}, "member_count": {"type": "integer"},
            }},
            "ProfitResult": {"type": "object", "properties": {
                "selling_price": {"type": "number"}, "total_cost": {"type": "number"},
                "net_profit": {"type": "number"}, "roi": {"type": "number"}, "margin": {"type": "number"},
            }},
            "ThreeDAsset": {"type": "object", "properties": {
                "id": {"type": "integer"}, "name": {"type": "string"},
                "format": {"type": "string"}, "status": {"type": "string"},
                "model_url": {"type": "string"}, "thumbnail_url": {"type": "string"},
            }},
        },
    }
    spec["paths"] = _build_all_paths()
    return spec


def _build_all_paths():
    p = {}

    # ── Auth ──────────────────────────────────────────────
    p["/api/auth/register"] = {"post": {"tags": ["Auth"], "summary": "用户注册", "security": [],
        "requestBody": _body({"type": "object", "required": ["username", "email", "password"], "properties": {
            "username": {"type": "string"}, "email": {"type": "string", "format": "email"},
            "password": {"type": "string", "minLength": 8}, "language": {"type": "string", "default": "zh_CN"},
        }}), "responses": {"201": _ok("注册成功"), "400": _err("参数错误")}}}

    p["/api/auth/login"] = {"post": {"tags": ["Auth"], "summary": "用户登录", "security": [],
        "requestBody": _body({"type": "object", "required": ["login_id", "password"], "properties": {
            "login_id": {"type": "string", "description": "用户名或邮箱"}, "password": {"type": "string"},
        }}), "responses": {"200": _ok("登录成功", {"type": "object", "properties": {
            "access_token": {"type": "string"}, "refresh_token": {"type": "string"},
            "user": {"$ref": "#/components/schemas/User"}}}), "401": _err("认证失败")}}}

    p["/api/auth/me"] = {
        "get": {"tags": ["Auth"], "summary": "获取当前用户信息", "security": _jwt(), "responses": {"200": _ok("成功", {"$ref": "#/components/schemas/User"})}},
        "put": {"tags": ["Auth"], "summary": "更新用户信息", "security": _jwt(),
            "requestBody": _body({"type": "object", "properties": {"username": {"type": "string"}, "email": {"type": "string"}}}, False),
            "responses": {"200": _ok("更新成功")}},
    }
    p["/api/auth/verify-email"] = {"get": {"tags": ["Auth"], "summary": "邮箱验证", "security": [],
        "parameters": [_param("token", "query")], "responses": {"200": _ok("验证成功"), "400": _err("Token 无效")}}}
    p["/api/auth/resend-verification"] = {"post": {"tags": ["Auth"], "summary": "重新发送验证邮件", "security": _jwt(), "responses": {"200": _ok("已发送")}}}
    p["/api/auth/forgot-password"] = {"post": {"tags": ["Auth"], "summary": "忘记密码", "security": [],
        "requestBody": _body({"type": "object", "required": ["email"], "properties": {"email": {"type": "string", "format": "email"}}}),
        "responses": {"200": _ok("重置邮件已发送")}}}
    p["/api/auth/reset-password"] = {"post": {"tags": ["Auth"], "summary": "重置密码", "security": [],
        "requestBody": _body({"type": "object", "required": ["token", "new_password"], "properties": {
            "token": {"type": "string"}, "new_password": {"type": "string", "minLength": 8}}}),
        "responses": {"200": _ok("密码已重置"), "400": _err("Token 无效")}}}
    p["/api/auth/change-password"] = {"post": {"tags": ["Auth"], "summary": "修改密码", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["old_password", "new_password"], "properties": {
            "old_password": {"type": "string"}, "new_password": {"type": "string"}}}),
        "responses": {"200": _ok("密码已修改")}}}
    p["/api/auth/refresh"] = {"post": {"tags": ["Auth"], "summary": "刷新 Token", "security": [],
        "requestBody": _body({"type": "object", "required": ["refresh_token"], "properties": {"refresh_token": {"type": "string"}}}),
        "responses": {"200": _ok("Token 已刷新", {"type": "object", "properties": {"access_token": {"type": "string"}}})}}}
    p["/api/auth/quota"] = {"get": {"tags": ["Auth"], "summary": "获取用户配额", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/auth/users"] = {"get": {"tags": ["Auth"], "summary": "用户列表（管理员）", "security": _jwt(),
        "parameters": [_param("page", "query", "integer", False, default=1), _param("per_page", "query", "integer", False, default=20)],
        "responses": {"200": _ok("成功")}}}
    p["/api/auth/users/{user_id}/role"] = {"put": {"tags": ["Auth"], "summary": "修改用户角色", "security": _jwt(),
        "parameters": [_param("user_id", schema_type="integer")],
        "requestBody": _body({"type": "object", "properties": {"role": {"type": "string", "enum": ["user", "admin"]}}}, False),
        "responses": {"200": _ok("角色已更新")}}}
    p["/api/auth/users/{user_id}/status"] = {"put": {"tags": ["Auth"], "summary": "修改用户状态", "security": _jwt(),
        "parameters": [_param("user_id", schema_type="integer")],
        "requestBody": _body({"type": "object", "properties": {"status": {"type": "string", "enum": ["active", "suspended"]}}}, False),
        "responses": {"200": _ok("状态已更新")}}}

    # ── OAuth ─────────────────────────────────────────────
    p["/api/oauth/providers"] = {"get": {"tags": ["OAuth"], "summary": "获取 OAuth 提供商列表", "security": [], "responses": {"200": _ok("成功")}}}
    p["/api/oauth/{provider}/authorize"] = {"get": {"tags": ["OAuth"], "summary": "获取 OAuth 授权 URL", "security": [],
        "parameters": [_param("provider", enum=["google", "github"])],
        "responses": {"200": _ok("成功", {"type": "object", "properties": {"auth_url": {"type": "string"}}})}}}
    p["/api/oauth/{provider}/callback"] = {"get": {"tags": ["OAuth"], "summary": "OAuth 回调处理", "security": [],
        "parameters": [_param("provider"), _param("code", "query")],
        "responses": {"200": _ok("登录成功")}}}

    # ── Projects ──────────────────────────────────────────
    p["/api/v1/projects"] = {"get": {"tags": ["Projects"], "summary": "获取项目列表", "security": _jwt(),
        "parameters": [_param("page", "query", "integer", False, default=1), _param("per_page", "query", "integer", False, default=20), _param("status", "query", "string", False)],
        "responses": {"200": _ok("成功", {"type": "object", "properties": {"projects": {"type": "array", "items": {"$ref": "#/components/schemas/Project"}}, "total": {"type": "integer"}}})}}}
    p["/api/v1/projects/create"] = {"post": {"tags": ["Projects"], "summary": "创建新项目", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["name", "keyword"], "properties": {
            "name": {"type": "string"}, "keyword": {"type": "string"}, "marketplace": {"type": "string", "default": "US"}, "description": {"type": "string"}}}),
        "responses": {"201": _ok("项目已创建", {"$ref": "#/components/schemas/Project"})}}}
    p["/api/v1/projects/{project_id}"] = {
        "get": {"tags": ["Projects"], "summary": "获取项目详情", "security": _jwt(), "parameters": [_param("project_id")], "responses": {"200": _ok("成功", {"$ref": "#/components/schemas/Project"})}},
        "delete": {"tags": ["Projects"], "summary": "删除项目", "security": _jwt(), "parameters": [_param("project_id")], "responses": {"200": _ok("项目已删除")}},
    }
    p["/api/v1/projects/{project_id}/products"] = {"get": {"tags": ["Projects"], "summary": "获取项目产品列表", "security": _jwt(),
        "parameters": [_param("project_id"), _param("page", "query", "integer", False, default=1), _param("per_page", "query", "integer", False, default=50)],
        "responses": {"200": _ok("成功", {"type": "object", "properties": {"products": {"type": "array", "items": {"$ref": "#/components/schemas/Product"}}, "total": {"type": "integer"}}})}}}
    p["/api/v1/projects/{project_id}/scrape"] = {"post": {"tags": ["Projects"], "summary": "启动产品爬取", "security": _jwt(),
        "parameters": [_param("project_id")],
        "requestBody": _body({"type": "object", "properties": {"max_products": {"type": "integer", "default": 100}, "sources": {"type": "array", "items": {"type": "string"}}}}, False),
        "responses": {"202": _ok("任务已提交", {"type": "object", "properties": {"task_id": {"type": "string"}}})}}}
    p["/api/v1/projects/{project_id}/filter/rules"] = {"post": {"tags": ["Projects"], "summary": "规则筛选产品", "security": _jwt(),
        "parameters": [_param("project_id")],
        "requestBody": _body({"type": "object", "properties": {"min_price": {"type": "number"}, "max_price": {"type": "number"}, "min_reviews": {"type": "integer"}, "min_rating": {"type": "number"}, "max_bsr": {"type": "integer"}}}, False),
        "responses": {"200": _ok("筛选完成")}}}
    p["/api/v1/projects/{project_id}/filter/ai"] = {"post": {"tags": ["Projects"], "summary": "AI 智能筛选", "security": _jwt(),
        "parameters": [_param("project_id")], "responses": {"200": _ok("AI 筛选完成")}}}
    p["/api/v1/projects/{project_id}/archive"] = {"post": {"tags": ["Projects"], "summary": "归档项目", "security": _jwt(),
        "parameters": [_param("project_id", schema_type="integer")], "responses": {"200": _ok("项目已归档")}}}

    # ── Analysis ──────────────────────────────────────────
    p["/api/v1/analysis/market"] = {"post": {"tags": ["Analysis"], "summary": "市场分析", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["keyword"], "properties": {"keyword": {"type": "string"}, "marketplace": {"type": "string"}}}),
        "responses": {"202": _ok("分析任务已提交")}}}
    p["/api/v1/analysis/product/{asin}"] = {"get": {"tags": ["Analysis"], "summary": "单品深度分析", "security": _jwt(),
        "parameters": [_param("asin")], "responses": {"200": _ok("分析完成")}}}
    p["/api/v1/analysis/reviews"] = {"post": {"tags": ["Analysis"], "summary": "评论分析", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"asin": {"type": "string"}, "max_reviews": {"type": "integer", "default": 100}}}, False),
        "responses": {"200": _ok("评论分析完成")}}}
    p["/api/v1/analysis/visual"] = {"post": {"tags": ["Analysis"], "summary": "视觉分析（OCR）", "security": _jwt(), "responses": {"200": _ok("视觉分析完成")}}}
    p["/api/v1/analysis/report/generate"] = {"post": {"tags": ["Analysis"], "summary": "生成分析报告", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"project_id": {"type": "string"}}}, False), "responses": {"200": _ok("报告已生成")}}}
    p["/api/v1/analysis/report/{project_id}"] = {"get": {"tags": ["Analysis"], "summary": "获取分析报告", "security": _jwt(),
        "parameters": [_param("project_id")], "responses": {"200": _ok("成功")}}}
    p["/api/v1/analysis/{task_id}/result"] = {"get": {"tags": ["Analysis"], "summary": "获取异步任务结果", "security": _jwt(),
        "parameters": [_param("task_id")], "responses": {"200": _ok("成功")}}}

    # ── Profit ────────────────────────────────────────────
    p["/api/v1/profit/calculate"] = {"post": {"tags": ["Profit"], "summary": "计算单品利润", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {
            "selling_price": {"type": "number"}, "product_cost": {"type": "number"},
            "shipping_to_fba": {"type": "number"}, "weight_lb": {"type": "number"},
            "category": {"type": "string"}, "marketplace": {"type": "string", "default": "US"}}}),
        "responses": {"200": _ok("计算完成", {"$ref": "#/components/schemas/ProfitResult"})}}}
    p["/api/v1/profit/batch"] = {"post": {"tags": ["Profit"], "summary": "批量利润计算", "security": _jwt(), "responses": {"200": _ok("批量计算完成")}}}
    p["/api/v1/profit/history"] = {"get": {"tags": ["Profit"], "summary": "利润计算历史", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/profit/save"] = {"post": {"tags": ["Profit"], "summary": "保存计算结果", "security": _jwt(), "responses": {"200": _ok("已保存")}}}

    # ── 3D Lab ────────────────────────────────────────────
    p["/api/v1/3d/generate"] = {"post": {"tags": ["3D Lab"], "summary": "生成 3D 模型", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["prompt"], "properties": {
            "prompt": {"type": "string"}, "format": {"type": "string", "enum": ["glb", "obj", "fbx", "stl"], "default": "glb"}}}),
        "responses": {"202": _ok("生成任务已提交", {"$ref": "#/components/schemas/ThreeDAsset"})}}}
    p["/api/v1/3d/assets"] = {"get": {"tags": ["3D Lab"], "summary": "获取 3D 资产列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/3d/{asset_id}"] = {
        "get": {"tags": ["3D Lab"], "summary": "获取 3D 资产详情", "security": _jwt(), "parameters": [_param("asset_id", schema_type="integer")], "responses": {"200": _ok("成功")}},
        "delete": {"tags": ["3D Lab"], "summary": "删除 3D 资产", "security": _jwt(), "parameters": [_param("asset_id", schema_type="integer")], "responses": {"200": _ok("已删除")}},
    }
    p["/api/v1/3d/{asset_id}/status"] = {"get": {"tags": ["3D Lab"], "summary": "3D 生成状态", "security": _jwt(), "parameters": [_param("asset_id", schema_type="integer")], "responses": {"200": _ok("成功")}}}
    p["/api/v1/3d/{asset_id}/render-video"] = {"post": {"tags": ["3D Lab"], "summary": "渲染 3D 视频", "security": _jwt(),
        "parameters": [_param("asset_id", schema_type="integer")],
        "requestBody": _body({"type": "object", "properties": {"resolution": {"type": "string", "default": "1080p"}, "environment": {"type": "string", "default": "studio"}, "duration": {"type": "integer", "default": 10}}}, False),
        "responses": {"202": _ok("渲染任务已提交")}}}
    p["/api/v1/3d/{asset_id}/video"] = {"get": {"tags": ["3D Lab"], "summary": "获取渲染视频", "security": _jwt(), "parameters": [_param("asset_id", schema_type="integer")],
        "responses": {"200": {"description": "视频文件", "content": {"video/mp4": {}}}}}}
    p["/api/v1/3d/templates"] = {"get": {"tags": ["3D Lab"], "summary": "3D 模板列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/3d/environments"] = {"get": {"tags": ["3D Lab"], "summary": "渲染环境列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/3d/resolutions"] = {"get": {"tags": ["3D Lab"], "summary": "可用分辨率", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/3d/renders/{filename}"] = {"get": {"tags": ["3D Lab"], "summary": "获取渲染文件", "security": _jwt(), "parameters": [_param("filename")],
        "responses": {"200": {"description": "文件下载"}}}}

    # ── Export ────────────────────────────────────────────
    p["/api/v1/export/products/{project_id}"] = {"get": {"tags": ["Export"], "summary": "导出产品数据", "security": _jwt(),
        "parameters": [_param("project_id"), _param("format", "query", enum=["csv", "xlsx", "pdf"])],
        "responses": {"200": {"description": "文件下载", "content": {"application/octet-stream": {}}}}}}
    p["/api/v1/export/report/{project_id}"] = {"get": {"tags": ["Export"], "summary": "导出报告 PDF", "security": _jwt(),
        "parameters": [_param("project_id")], "responses": {"200": {"description": "PDF 文件", "content": {"application/pdf": {}}}}}}
    p["/api/v1/export/profit/{project_id}"] = {"get": {"tags": ["Export"], "summary": "导出利润报告", "security": _jwt(),
        "parameters": [_param("project_id"), _param("format", "query", "string", False, enum=["csv", "xlsx"])],
        "responses": {"200": {"description": "文件下载"}}}}
    p["/api/v1/export/analysis/{task_id}"] = {"get": {"tags": ["Export"], "summary": "导出分析结果", "security": _jwt(),
        "parameters": [_param("task_id")], "responses": {"200": {"description": "文件下载"}}}}

    # ── Supply ────────────────────────────────────────────
    p["/api/v1/supply/keyword-search"] = {"post": {"tags": ["Supply"], "summary": "1688 关键词搜索", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["keyword"], "properties": {"keyword": {"type": "string"}, "max_results": {"type": "integer", "default": 20}}}),
        "responses": {"200": _ok("搜索完成")}}}
    p["/api/v1/supply/image-search"] = {"post": {"tags": ["Supply"], "summary": "1688 以图搜货", "security": _jwt(),
        "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"image": {"type": "string", "format": "binary"}}}}}},
        "responses": {"200": _ok("搜索完成")}}}

    # ── Subscription ──────────────────────────────────────
    p["/api/subscription/plans"] = {"get": {"tags": ["Subscription"], "summary": "获取订阅计划列表", "security": [], "responses": {"200": _ok("成功")}}}
    p["/api/subscription/me"] = {"get": {"tags": ["Subscription"], "summary": "获取当前订阅信息", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/subscription/usage"] = {"get": {"tags": ["Subscription"], "summary": "获取配额使用情况", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/subscription/upgrade"] = {"post": {"tags": ["Subscription"], "summary": "升级订阅", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"plan": {"type": "string", "enum": ["orbit", "moonshot"]}}}),
        "responses": {"200": _ok("升级成功")}}}
    p["/api/subscription/cancel"] = {"post": {"tags": ["Subscription"], "summary": "取消订阅", "security": _jwt(), "responses": {"200": _ok("已取消")}}}

    # ── Stripe ────────────────────────────────────────────
    p["/api/stripe/create-checkout-session"] = {"post": {"tags": ["Stripe"], "summary": "创建支付会话", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["plan"], "properties": {"plan": {"type": "string", "enum": ["orbit", "moonshot"]}}}),
        "responses": {"200": _ok("成功", {"type": "object", "properties": {"checkout_url": {"type": "string"}, "session_id": {"type": "string"}}})}}}
    p["/api/stripe/customer-portal"] = {"post": {"tags": ["Stripe"], "summary": "客户门户 URL", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/stripe/config"] = {"get": {"tags": ["Stripe"], "summary": "Stripe 公钥配置", "security": [], "responses": {"200": _ok("成功")}}}
    p["/api/stripe/webhook"] = {"post": {"tags": ["Stripe"], "summary": "Stripe Webhook", "security": [], "responses": {"200": {"description": "处理成功"}}}}

    # ── Teams ─────────────────────────────────────────────
    p["/api/v1/teams"] = {
        "get": {"tags": ["Teams"], "summary": "获取团队列表", "security": _jwt(), "responses": {"200": _ok("成功")}},
        "post": {"tags": ["Teams"], "summary": "创建团队", "security": _jwt(),
            "requestBody": _body({"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}, "description": {"type": "string"}}}),
            "responses": {"201": _ok("团队已创建", {"$ref": "#/components/schemas/Team"})}},
    }
    p["/api/v1/teams/{team_id}/members"] = {"get": {"tags": ["Teams"], "summary": "获取团队成员", "security": _jwt(),
        "parameters": [_param("team_id", schema_type="integer")], "responses": {"200": _ok("成功")}}}
    p["/api/v1/teams/{team_id}/invite"] = {"post": {"tags": ["Teams"], "summary": "邀请成员", "security": _jwt(),
        "parameters": [_param("team_id", schema_type="integer")],
        "requestBody": _body({"type": "object", "required": ["email"], "properties": {"email": {"type": "string", "format": "email"}, "role": {"type": "string", "default": "member"}}}),
        "responses": {"200": _ok("邀请已发送")}}}
    p["/api/v1/teams/{team_id}/members/{user_id}"] = {
        "put": {"tags": ["Teams"], "summary": "更新成员角色", "security": _jwt(),
            "parameters": [_param("team_id", schema_type="integer"), _param("user_id", schema_type="integer")],
            "requestBody": _body({"type": "object", "properties": {"role": {"type": "string", "enum": ["admin", "member", "viewer"]}}}, False),
            "responses": {"200": _ok("角色已更新")}},
        "delete": {"tags": ["Teams"], "summary": "移除成员", "security": _jwt(),
            "parameters": [_param("team_id", schema_type="integer"), _param("user_id", schema_type="integer")],
            "responses": {"200": _ok("成员已移除")}},
    }
    p["/api/v1/teams/join"] = {"post": {"tags": ["Teams"], "summary": "加入团队", "security": _jwt(),
        "requestBody": _body({"type": "object", "required": ["invite_code"], "properties": {"invite_code": {"type": "string"}}}),
        "responses": {"200": _ok("已加入团队")}}}
    p["/api/v1/teams/roles"] = {"get": {"tags": ["Teams"], "summary": "可用角色列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}

    # ── Notifications ─────────────────────────────────────
    p["/api/v1/notifications"] = {
        "get": {"tags": ["Notifications"], "summary": "获取通知列表", "security": _jwt(),
            "parameters": [_param("page", "query", "integer", False, default=1), _param("type", "query", "string", False), _param("is_read", "query", "boolean", False)],
            "responses": {"200": _ok("成功", {"type": "array", "items": {"$ref": "#/components/schemas/Notification"}})}},
        "post": {"tags": ["Notifications"], "summary": "创建通知（内部）", "security": _jwt(), "responses": {"201": _ok("通知已创建")}},
    }
    p["/api/v1/notifications/unread-count"] = {"get": {"tags": ["Notifications"], "summary": "未读通知数量", "security": _jwt(),
        "responses": {"200": _ok("成功", {"type": "object", "properties": {"count": {"type": "integer"}}})}}}
    p["/api/v1/notifications/mark-read"] = {"post": {"tags": ["Notifications"], "summary": "批量标记已读", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"notification_ids": {"type": "array", "items": {"type": "integer"}}}}, False),
        "responses": {"200": _ok("已标记")}}}
    p["/api/v1/notifications/{notification_id}/read"] = {"put": {"tags": ["Notifications"], "summary": "标记单条已读", "security": _jwt(),
        "parameters": [_param("notification_id")], "responses": {"200": _ok("已标记")}}}
    p["/api/v1/notifications/read-all"] = {"put": {"tags": ["Notifications"], "summary": "全部标记已读", "security": _jwt(), "responses": {"200": _ok("已标记")}}}
    p["/api/v1/notifications/preferences"] = {
        "get": {"tags": ["Notifications"], "summary": "获取通知偏好", "security": _jwt(), "responses": {"200": _ok("成功")}},
        "put": {"tags": ["Notifications"], "summary": "更新通知偏好", "security": _jwt(),
            "requestBody": _body({"type": "object", "properties": {
                "email_enabled": {"type": "boolean"}, "push_enabled": {"type": "boolean"},
                "task_complete": {"type": "boolean"}, "quota_warning": {"type": "boolean"}}}, False),
            "responses": {"200": _ok("设置已更新")}},
    }

    # ── Dashboard ─────────────────────────────────────────
    p["/api/v1/dashboard/stats"] = {"get": {"tags": ["Dashboard"], "summary": "仪表盘统计", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/dashboard/activities"] = {"get": {"tags": ["Dashboard"], "summary": "最近活动", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/dashboard/activity-chart"] = {"get": {"tags": ["Dashboard"], "summary": "活动图表数据", "security": _jwt(), "responses": {"200": _ok("成功")}}}

    # ── Audit ─────────────────────────────────────────────
    p["/api/audit/logs"] = {"get": {"tags": ["Audit"], "summary": "查询审计日志", "security": _jwt(),
        "parameters": [_param("page", "query", "integer", False, default=1), _param("per_page", "query", "integer", False, default=50),
            _param("action", "query", "string", False), _param("start_date", "query", "string", False), _param("end_date", "query", "string", False)],
        "responses": {"200": _ok("成功")}}}
    p["/api/audit/actions"] = {"get": {"tags": ["Audit"], "summary": "审计动作类型", "security": _jwt(), "responses": {"200": _ok("成功")}}}

    # ── Admin ─────────────────────────────────────────────
    p["/api/v1/admin/apm"] = {"get": {"tags": ["Admin"], "summary": "APM 监控数据", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/admin/apm/slow"] = {"get": {"tags": ["Admin"], "summary": "慢查询列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/v1/admin/cleanup/run"] = {"post": {"tags": ["Admin"], "summary": "执行数据清理", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"dry_run": {"type": "boolean", "default": False}, "targets": {"type": "array", "items": {"type": "string"}}}}, False),
        "responses": {"200": _ok("清理完成")}}}
    p["/api/v1/admin/cleanup/preview"] = {"post": {"tags": ["Admin"], "summary": "预览清理结果", "security": _jwt(), "responses": {"200": _ok("预览完成")}}}
    p["/api/v1/admin/cleanup/stats"] = {"get": {"tags": ["Admin"], "summary": "存储统计", "security": _jwt(), "responses": {"200": _ok("成功")}}}

    # ── Settings ──────────────────────────────────────────
    p["/api/keys/services"] = {"get": {"tags": ["Settings"], "summary": "可配置的 API 服务列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/keys/all"] = {"get": {"tags": ["Settings"], "summary": "所有已配置的 API 密钥", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/keys/{service_id}"] = {
        "get": {"tags": ["Settings"], "summary": "获取 API 密钥", "security": _jwt(), "parameters": [_param("service_id")], "responses": {"200": _ok("成功")}},
        "put": {"tags": ["Settings"], "summary": "更新 API 密钥", "security": _jwt(), "parameters": [_param("service_id")],
            "requestBody": _body({"type": "object", "properties": {"api_key": {"type": "string"}, "api_secret": {"type": "string"}}}, False),
            "responses": {"200": _ok("密钥已更新")}},
        "delete": {"tags": ["Settings"], "summary": "删除 API 密钥", "security": _jwt(), "parameters": [_param("service_id")], "responses": {"200": _ok("密钥已删除")}},
    }
    p["/api/keys/{service_id}/test"] = {"post": {"tags": ["Settings"], "summary": "测试 API 密钥", "security": _jwt(), "parameters": [_param("service_id")], "responses": {"200": _ok("测试成功")}}}
    p["/api/ai/settings"] = {
        "get": {"tags": ["Settings"], "summary": "获取 AI 设置", "security": _jwt(), "responses": {"200": _ok("成功")}},
        "put": {"tags": ["Settings"], "summary": "更新 AI 设置", "security": _jwt(),
            "requestBody": _body({"type": "object", "properties": {"provider": {"type": "string"}, "model": {"type": "string"}, "temperature": {"type": "number"}}}, False),
            "responses": {"200": _ok("设置已更新")}},
    }
    p["/api/ai/providers"] = {"get": {"tags": ["Settings"], "summary": "AI 提供商列表", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/ai/test"] = {"post": {"tags": ["Settings"], "summary": "测试 AI 连接", "security": _jwt(), "responses": {"200": _ok("测试成功")}}}
    p["/api/ai/test-direct"] = {"post": {"tags": ["Settings"], "summary": "直接测试 AI API", "security": _jwt(), "responses": {"200": _ok("测试成功")}}}

    # ── i18n ──────────────────────────────────────────────
    p["/api/i18n/languages"] = {"get": {"tags": ["i18n"], "summary": "支持的语言列表", "security": [], "responses": {"200": _ok("成功")}}}
    p["/api/i18n/{lang}"] = {"get": {"tags": ["i18n"], "summary": "获取语言翻译包", "security": [],
        "parameters": [_param("lang", example="zh_CN")], "responses": {"200": _ok("成功")}}}
    p["/api/i18n/preference"] = {"put": {"tags": ["i18n"], "summary": "设置语言偏好", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"language": {"type": "string", "enum": ["zh_CN", "en_US", "ko_KR"]}}}, False),
        "responses": {"200": _ok("设置已保存")}}}

    # ── SSE / System ──────────────────────────────────────
    p["/api/sse/tasks"] = {"get": {"tags": ["System"], "summary": "SSE 任务事件流", "security": _jwt(),
        "description": "Server-Sent Events 端点，实时推送异步任务进度",
        "responses": {"200": {"description": "SSE 事件流", "content": {"text/event-stream": {}}}}}}
    p["/api/sse/status"] = {"get": {"tags": ["System"], "summary": "SSE 连接状态", "security": _jwt(), "responses": {"200": _ok("成功")}}}
    p["/api/health"] = {"get": {"tags": ["System"], "summary": "健康检查", "security": [], "responses": {"200": _ok("健康"), "503": _err("服务不可用")}}}
    p["/api/metrics"] = {"get": {"tags": ["System"], "summary": "Prometheus 指标", "security": [],
        "responses": {"200": {"description": "Prometheus 格式指标", "content": {"text/plain": {}}}}}}

    # ── Upload ────────────────────────────────────────────
    p["/api/v1/upload/parse"] = {"post": {"tags": ["Projects"], "summary": "上传并解析数据文件", "security": _jwt(),
        "requestBody": {"required": True, "content": {"multipart/form-data": {"schema": {"type": "object", "properties": {"file": {"type": "string", "format": "binary"}}}}}},
        "responses": {"200": _ok("解析完成")}}}
    p["/api/v1/upload/confirm-mapping"] = {"post": {"tags": ["Projects"], "summary": "确认字段映射", "security": _jwt(), "responses": {"200": _ok("映射已确认")}}}
    p["/api/v1/upload/trends"] = {"post": {"tags": ["Projects"], "summary": "上传趋势数据", "security": _jwt(), "responses": {"200": _ok("上传成功")}}}

    # ── Assets ────────────────────────────────────────────
    p["/api/v1/assets/download/{asin}"] = {"get": {"tags": ["Export"], "summary": "下载产品资源", "security": _jwt(),
        "parameters": [_param("asin")], "responses": {"200": {"description": "文件下载"}}}}
    p["/api/v1/assets/download/project/{project_id}"] = {"get": {"tags": ["Export"], "summary": "下载项目所有资源", "security": _jwt(),
        "parameters": [_param("project_id")], "responses": {"200": {"description": "ZIP 文件下载"}}}}

    # ── Affiliate ─────────────────────────────────────────
    p["/api/affiliate/link"] = {"post": {"tags": ["Settings"], "summary": "生成联盟推广链接", "security": _jwt(),
        "requestBody": _body({"type": "object", "properties": {"url": {"type": "string"}, "platform": {"type": "string"}}}, False),
        "responses": {"200": _ok("链接已生成")}}}
    p["/api/affiliate/batch"] = {"post": {"tags": ["Settings"], "summary": "批量生成推广链接", "security": _jwt(), "responses": {"200": _ok("批量生成完成")}}}

    # ── User Quota ────────────────────────────────────────
    p["/api/v1/user/quota"] = {"get": {"tags": ["Subscription"], "summary": "用户配额详情", "security": _jwt(), "responses": {"200": _ok("成功")}}}

    return p
