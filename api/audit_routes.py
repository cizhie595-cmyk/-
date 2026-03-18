"""
Coupang 选品系统 - 审计日志 API 路由
提供: 管理员查看审计日志
"""

from flask import Blueprint, request, jsonify
from auth.middleware import admin_required
from utils.audit_logger import audit

audit_bp = Blueprint("audit", __name__, url_prefix="/api/audit")


@audit_bp.route("/logs", methods=["GET"])
@admin_required
def get_audit_logs(current_user):
    """
    管理员查看审计日志

    查询参数:
    - user_id: 筛选用户ID
    - action: 筛选操作类型
    - target_type: 筛选目标类型
    - status: 筛选状态
    - start_date: 开始日期 (YYYY-MM-DD)
    - end_date: 结束日期 (YYYY-MM-DD)
    - page: 页码 (默认 1)
    - page_size: 每页数量 (默认 50, 最大 200)
    """
    user_id = request.args.get("user_id", type=int)
    action = request.args.get("action")
    target_type = request.args.get("target_type")
    status = request.args.get("status")
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")
    page = request.args.get("page", 1, type=int)
    page_size = min(request.args.get("page_size", 50, type=int), 200)

    result = audit.query(
        user_id=user_id,
        action=action,
        target_type=target_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )

    return jsonify({"success": True, **result}), 200


@audit_bp.route("/actions", methods=["GET"])
@admin_required
def get_audit_actions(current_user):
    """获取所有操作类型列表"""
    actions = [
        {"code": "login", "label": "用户登录"},
        {"code": "logout", "label": "用户登出"},
        {"code": "register", "label": "用户注册"},
        {"code": "password_change", "label": "修改密码"},
        {"code": "password_reset", "label": "重置密码"},
        {"code": "profile_update", "label": "更新资料"},
        {"code": "email_verify", "label": "邮箱验证"},
        {"code": "subscription_upgrade", "label": "订阅升级"},
        {"code": "subscription_cancel", "label": "取消订阅"},
        {"code": "project_create", "label": "创建项目"},
        {"code": "project_update", "label": "更新项目"},
        {"code": "project_delete", "label": "删除项目"},
        {"code": "project_run", "label": "执行项目"},
        {"code": "analysis_start", "label": "发起分析"},
        {"code": "3d_generate", "label": "3D 生成"},
        {"code": "report_generate", "label": "生成报告"},
        {"code": "data_export", "label": "数据导出"},
        {"code": "api_key_update", "label": "更新API密钥"},
        {"code": "admin_user_update", "label": "管理员修改用户"},
        {"code": "admin_user_disable", "label": "管理员禁用用户"},
    ]
    return jsonify({"success": True, "actions": actions}), 200
