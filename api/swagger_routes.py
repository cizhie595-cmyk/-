"""
Coupang 选品系统 - Swagger UI 路由
端点:
    GET /api/docs          Swagger UI 页面
    GET /api/openapi.json  OpenAPI 3.0 JSON 规范
"""

from flask import Blueprint, jsonify, render_template_string

swagger_bp = Blueprint("swagger", __name__, url_prefix="/api")

SWAGGER_UI_HTML = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API 文档 - Amazon Visionary Sourcing Tool</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css">
    <style>
        body { margin: 0; background: #fafafa; }
        .topbar { display: none !important; }
        .swagger-ui .info { margin: 20px 0; }
        .swagger-ui .info .title { font-size: 28px; color: #333; }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        SwaggerUIBundle({
            url: '/api/openapi.json',
            dom_id: '#swagger-ui',
            deepLinking: true,
            presets: [
                SwaggerUIBundle.presets.apis,
                SwaggerUIBundle.SwaggerUIStandalonePreset,
            ],
            layout: 'BaseLayout',
            defaultModelsExpandDepth: 1,
            defaultModelExpandDepth: 2,
            docExpansion: 'list',
            filter: true,
            showExtensions: true,
            showCommonExtensions: true,
            persistAuthorization: true,
        });
    </script>
</body>
</html>
"""


@swagger_bp.route("/docs", methods=["GET"])
def swagger_ui():
    """Swagger UI 页面"""
    return render_template_string(SWAGGER_UI_HTML)


@swagger_bp.route("/openapi.json", methods=["GET"])
def openapi_spec():
    """返回 OpenAPI 3.0 JSON 规范"""
    from utils.swagger_config import get_openapi_spec
    return jsonify(get_openapi_spec())
