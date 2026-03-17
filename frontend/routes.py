"""
前端页面路由
注册所有 HTML 模板页面的 URL 路由
"""

from flask import Blueprint, render_template, redirect

frontend_bp = Blueprint(
    "frontend",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


@frontend_bp.route("/")
def index():
    """首页重定向到 Dashboard"""
    return redirect("/dashboard")


@frontend_bp.route("/auth/login")
@frontend_bp.route("/auth/register")
def auth_page():
    """登录/注册页面"""
    return render_template("auth.html")


@frontend_bp.route("/dashboard")
def dashboard():
    """工作台 Dashboard"""
    return render_template("dashboard.html", active_page="dashboard")


@frontend_bp.route("/projects/new")
def new_project():
    """新建选品项目"""
    return render_template("new_project.html", active_page="new_project")


@frontend_bp.route("/projects/<project_id>")
def project_detail(project_id):
    """项目详情 - 数据列表"""
    return render_template("project_detail.html", active_page="dashboard")


@frontend_bp.route("/products/<asin>/analysis")
def product_analysis(asin):
    """单品深度分析"""
    return render_template("product_analysis.html", active_page="dashboard")


@frontend_bp.route("/market")
def market_analysis():
    """大盘与类目分析"""
    return render_template("market_analysis.html", active_page="market")


@frontend_bp.route("/profit")
def profit_calculator():
    """利润计算器"""
    return render_template("profit_calculator.html", active_page="profit")


@frontend_bp.route("/3d-lab")
def threed_lab():
    """3D 产品实验室"""
    return render_template("threed_lab.html", active_page="3d_lab")


@frontend_bp.route("/reports/<project_id>")
def report_page(project_id):
    """选品报告页"""
    return render_template("report.html", active_page="dashboard")


@frontend_bp.route("/settings/api-keys")
def api_keys_settings():
    """API Keys 设置"""
    return render_template("api_keys_settings.html", active_page="api_keys")


@frontend_bp.route("/settings/subscription")
def subscription_settings():
    """订阅管理"""
    return render_template("subscription.html", active_page="subscription")


@frontend_bp.route("/settings/ai")
def ai_settings():
    """AI 设置"""
    return render_template("ai_settings.html", active_page="ai_settings")
