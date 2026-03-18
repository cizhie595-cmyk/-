"""
Coupang 选品系统 - Swagger / OpenAPI 3.0 文档配置
使用 flask-restx 或手动生成 OpenAPI spec
"""

import os

# API 文档基本信息
SWAGGER_CONFIG = {
    "openapi": "3.0.3",
    "info": {
        "title": "Amazon Visionary Sourcing Tool API",
        "description": """
## 概述

Amazon Visionary Sourcing Tool 是一款跨境电商智能选品系统，提供产品数据抓取、
AI 分析、利润计算、3D 模型生成等功能。

## 认证方式

所有 API 端点（除登录/注册外）需要在请求头中携带 JWT Token：

```
Authorization: Bearer <your_jwt_token>
```

## 速率限制

- 免费用户: 60 次/分钟
- Pro 用户: 200 次/分钟
- Enterprise 用户: 1000 次/分钟

超出限制返回 HTTP 429。

## 错误格式

```json
{
    "success": false,
    "message": "错误描述",
    "error_code": "ERROR_CODE"
}
```
        """,
        "version": "1.0.0",
        "contact": {
            "name": "API Support",
            "email": os.getenv("SUPPORT_EMAIL", "support@visionary.tool"),
        },
        "license": {
            "name": "MIT",
        },
    },
    "servers": [
        {
            "url": os.getenv("API_BASE_URL", "http://localhost:5000"),
            "description": "当前环境",
        },
    ],
    "tags": [
        {"name": "Auth", "description": "用户认证（登录/注册/邮箱验证/密码重置）"},
        {"name": "OAuth", "description": "第三方登录（Google/GitHub）"},
        {"name": "Projects", "description": "选品项目管理"},
        {"name": "Analysis", "description": "深度分析（视觉/评论/报告）"},
        {"name": "Profit", "description": "利润计算器"},
        {"name": "3D Lab", "description": "3D 模型生成与渲染"},
        {"name": "Export", "description": "数据导出（CSV/Excel/PDF）"},
        {"name": "Teams", "description": "团队协作与权限管理"},
        {"name": "Notifications", "description": "通知系统"},
        {"name": "Stripe", "description": "支付与订阅"},
        {"name": "Settings", "description": "API 密钥与 AI 配置"},
        {"name": "Admin", "description": "管理员功能（审计/清理）"},
        {"name": "SSE", "description": "实时事件推送"},
    ],
    "components": {
        "securitySchemes": {
            "BearerAuth": {
                "type": "http",
                "scheme": "bearer",
                "bearerFormat": "JWT",
                "description": "JWT Token 认证",
            },
        },
        "schemas": {
            "Error": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": False},
                    "message": {"type": "string", "example": "请求失败"},
                    "error_code": {"type": "string", "example": "VALIDATION_ERROR"},
                },
            },
            "Success": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean", "example": True},
                    "message": {"type": "string", "example": "操作成功"},
                },
            },
            "PaginatedResponse": {
                "type": "object",
                "properties": {
                    "success": {"type": "boolean"},
                    "total": {"type": "integer"},
                    "page": {"type": "integer"},
                    "per_page": {"type": "integer"},
                },
            },
        },
    },
    "security": [{"BearerAuth": []}],
}


def get_openapi_spec() -> dict:
    """
    生成完整的 OpenAPI 3.0 规范

    自动扫描 Flask 蓝图路由并生成 paths
    """
    spec = dict(SWAGGER_CONFIG)
    spec["paths"] = _generate_paths()
    return spec


def _generate_paths() -> dict:
    """根据已注册的路由生成 API paths"""
    paths = {}

    # Auth 路由
    paths["/api/auth/register"] = {
        "post": {
            "tags": ["Auth"], "summary": "用户注册",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["username", "email", "password"],
                "properties": {
                    "username": {"type": "string", "example": "john_doe"},
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string", "minLength": 8},
                },
            }}}},
            "responses": {"201": {"description": "注册成功"}, "400": {"description": "参数错误"}},
            "security": [],
        },
    }

    paths["/api/auth/login"] = {
        "post": {
            "tags": ["Auth"], "summary": "用户登录",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["email", "password"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string"},
                },
            }}}},
            "responses": {"200": {"description": "登录成功，返回 JWT Token"}},
            "security": [],
        },
    }

    paths["/api/auth/verify-email"] = {
        "post": {
            "tags": ["Auth"], "summary": "验证邮箱",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "properties": {"token": {"type": "string"}},
            }}}},
            "responses": {"200": {"description": "验证成功"}},
            "security": [],
        },
    }

    paths["/api/auth/forgot-password"] = {
        "post": {
            "tags": ["Auth"], "summary": "忘记密码",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "properties": {"email": {"type": "string", "format": "email"}},
            }}}},
            "responses": {"200": {"description": "重置邮件已发送"}},
            "security": [],
        },
    }

    # Projects 路由
    paths["/api/v1/projects"] = {
        "get": {
            "tags": ["Projects"], "summary": "获取项目列表",
            "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "per_page", "in": "query", "schema": {"type": "integer", "default": 20}},
            ],
            "responses": {"200": {"description": "项目列表"}},
        },
        "post": {
            "tags": ["Projects"], "summary": "创建选品项目",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["name", "keyword"],
                "properties": {
                    "name": {"type": "string"},
                    "keyword": {"type": "string"},
                    "marketplace_id": {"type": "string", "default": "ATVPDKIKX0DER"},
                    "scrape_depth": {"type": "integer", "default": 100},
                },
            }}}},
            "responses": {"201": {"description": "项目创建成功"}},
        },
    }

    # Export 路由
    paths["/api/v1/export/products/{project_id}"] = {
        "get": {
            "tags": ["Export"], "summary": "导出产品列表",
            "parameters": [
                {"name": "project_id", "in": "path", "required": True, "schema": {"type": "string"}},
                {"name": "format", "in": "query", "schema": {"type": "string", "enum": ["csv", "xlsx", "pdf"], "default": "csv"}},
                {"name": "columns", "in": "query", "schema": {"type": "string"}, "description": "逗号分隔的列名"},
            ],
            "responses": {"200": {"description": "文件下载", "content": {"application/octet-stream": {}}}},
        },
    }

    # Teams 路由
    paths["/api/v1/teams"] = {
        "get": {"tags": ["Teams"], "summary": "获取团队列表", "responses": {"200": {"description": "团队列表"}}},
        "post": {
            "tags": ["Teams"], "summary": "创建团队",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "required": ["name"],
                "properties": {"name": {"type": "string"}, "description": {"type": "string"}},
            }}}},
            "responses": {"201": {"description": "团队创建成功"}},
        },
    }

    paths["/api/v1/teams/{team_id}/invite"] = {
        "post": {
            "tags": ["Teams"], "summary": "邀请成员",
            "parameters": [{"name": "team_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "required": ["email"],
                "properties": {
                    "email": {"type": "string", "format": "email"},
                    "role": {"type": "string", "enum": ["admin", "analyst", "viewer"], "default": "analyst"},
                },
            }}}},
            "responses": {"200": {"description": "邀请已发送"}},
        },
    }

    # Notifications 路由
    paths["/api/v1/notifications"] = {
        "get": {
            "tags": ["Notifications"], "summary": "获取通知列表",
            "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer", "default": 1}},
                {"name": "unread_only", "in": "query", "schema": {"type": "boolean", "default": False}},
            ],
            "responses": {"200": {"description": "通知列表"}},
        },
    }

    # Stripe 路由
    paths["/api/stripe/create-checkout-session"] = {
        "post": {
            "tags": ["Stripe"], "summary": "创建 Stripe Checkout 会话",
            "requestBody": {"content": {"application/json": {"schema": {
                "type": "object", "required": ["plan"],
                "properties": {"plan": {"type": "string", "enum": ["pro", "enterprise"]}},
            }}}},
            "responses": {"200": {"description": "返回 checkout URL"}},
        },
    }

    # SSE 路由
    paths["/api/sse/tasks"] = {
        "get": {
            "tags": ["SSE"], "summary": "任务状态实时事件流 (SSE)",
            "responses": {"200": {"description": "Server-Sent Events 流", "content": {"text/event-stream": {}}}},
        },
    }

    # Admin 路由
    paths["/api/v1/admin/cleanup/run"] = {
        "post": {
            "tags": ["Admin"], "summary": "执行数据清理",
            "responses": {"200": {"description": "清理结果"}, "403": {"description": "需要管理员权限"}},
        },
    }

    paths["/api/audit/logs"] = {
        "get": {
            "tags": ["Admin"], "summary": "查询审计日志",
            "parameters": [
                {"name": "page", "in": "query", "schema": {"type": "integer"}},
                {"name": "action", "in": "query", "schema": {"type": "string"}},
                {"name": "user_id", "in": "query", "schema": {"type": "integer"}},
            ],
            "responses": {"200": {"description": "审计日志列表"}},
        },
    }

    return paths
