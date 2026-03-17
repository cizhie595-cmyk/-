"""
前端页面路由
注册所有 HTML 模板页面的 URL 路由
路由路径严格对齐 PRD 第9节 Page Inventory
"""

from flask import Blueprint, render_template, redirect, request

frontend_bp = Blueprint(
    "frontend",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


# ============================================================
# P-01 登录/注册页  /auth
# ============================================================
@frontend_bp.route("/")
def index():
    """首页重定向到 Dashboard"""
    return redirect("/dashboard")


@frontend_bp.route("/auth")
@frontend_bp.route("/auth/login")
@frontend_bp.route("/auth/register")
def auth_page():
    """登录/注册页面"""
    return render_template("auth.html")


# ============================================================
# P-02 工作台 Dashboard  /dashboard
# ============================================================
@frontend_bp.route("/dashboard")
def dashboard():
    """工作台 Dashboard"""
    return render_template("dashboard.html", active_page="dashboard")


# ============================================================
# P-03 新建选品项目  /projects/new
# ============================================================
@frontend_bp.route("/projects/new")
def new_project():
    """新建选品项目"""
    return render_template("new_project.html", active_page="new_project")


# ============================================================
# P-04 项目数据列表  /projects/{id}
# ============================================================
@frontend_bp.route("/projects/<project_id>")
def project_detail(project_id):
    """项目详情 - 数据列表"""
    return render_template("project_detail.html", active_page="dashboard", project_id=project_id)


# ============================================================
# P-05 单品深度分析  /products/{asin}/analysis
# ============================================================
@frontend_bp.route("/products/<asin>/analysis")
def product_analysis(asin):
    """单品深度分析"""
    return render_template("product_analysis.html", active_page="dashboard", asin=asin)


# ============================================================
# P-06 3D 实验室  /3d-lab
# ============================================================
@frontend_bp.route("/3d-lab")
def threed_lab():
    """3D 产品实验室"""
    return render_template("threed_lab.html", active_page="3d_lab")


# ============================================================
# P-07 大盘与类目分析  /market/{keyword}  (PRD 路由)
# 同时支持 /market 无参数访问和 /market?keyword=xxx 查询参数
# ============================================================
@frontend_bp.route("/market")
@frontend_bp.route("/market/<keyword>")
def market_analysis(keyword=None):
    """大盘与类目分析"""
    # 支持 URL 路径参数和查询参数两种方式
    kw = keyword or request.args.get("keyword", "")
    return render_template("market_analysis.html", active_page="market", keyword=kw)


# ============================================================
# P-08 利润计算器  /profit/{asin}  (PRD 路由)
# 同时支持 /profit 无参数访问和 /profit?asin=xxx 查询参数
# ============================================================
@frontend_bp.route("/profit")
@frontend_bp.route("/profit/<asin>")
def profit_calculator(asin=None):
    """利润计算器"""
    asin_val = asin or request.args.get("asin", "")
    return render_template("profit_calculator.html", active_page="profit", asin=asin_val)


# ============================================================
# P-09 综合决策报告  /reports/{id}
# ============================================================
@frontend_bp.route("/reports/<project_id>")
def report_page(project_id):
    """选品报告页"""
    return render_template("report.html", active_page="dashboard", project_id=project_id)


# ============================================================
# P-10 API 配置中心  /settings/api-keys
# ============================================================
@frontend_bp.route("/settings/api-keys")
def api_keys_settings():
    """API Keys 设置"""
    return render_template("api_keys_settings.html", active_page="api_keys")


# ============================================================
# P-11 订阅管理  /settings/subscription
# ============================================================
@frontend_bp.route("/settings/subscription")
def subscription_settings():
    """订阅管理"""
    return render_template("subscription.html", active_page="subscription")


# ============================================================
# AI 设置  /settings/ai
# ============================================================
@frontend_bp.route("/settings/ai")
def ai_settings():
    """AI 设置"""
    return render_template("ai_settings.html", active_page="ai_settings")
