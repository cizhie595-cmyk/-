"""
Coupang 选品系统 - 团队协作 API 路由
端点:
    POST   /api/v1/teams                     创建团队
    GET    /api/v1/teams                     获取用户的团队列表
    GET    /api/v1/teams/<id>/members        获取团队成员
    POST   /api/v1/teams/<id>/invite         邀请成员
    POST   /api/v1/teams/join                接受邀请
    PUT    /api/v1/teams/<id>/members/<uid>  更新成员角色
    DELETE /api/v1/teams/<id>/members/<uid>  移除成员
"""

from flask import Blueprint, request, jsonify
from auth.middleware import login_required
from auth.team_manager import team_mgr, Role, Permission, has_permission
from utils.logger import get_logger

logger = get_logger()

team_bp = Blueprint("teams", __name__, url_prefix="/api/v1/teams")


def _uid(current_user):
    return current_user.get("user_id") or current_user.get("sub")


# ============================================================
# POST /api/v1/teams - 创建团队
# ============================================================
@team_bp.route("", methods=["POST"])
@login_required
def create_team(current_user):
    """创建团队"""
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "message": "团队名称不能为空"}), 400

    result = team_mgr.create_team(
        owner_id=_uid(current_user),
        name=name,
        description=data.get("description", ""),
    )
    status = 201 if result.get("success") else 400
    return jsonify(result), status


# ============================================================
# GET /api/v1/teams - 获取用户的团队列表
# ============================================================
@team_bp.route("", methods=["GET"])
@login_required
def list_teams(current_user):
    """获取当前用户所属的所有团队"""
    user_id = _uid(current_user)

    try:
        from database.connection import db
        teams = db.fetch_all(
            """SELECT t.id, t.name, t.description, t.owner_id, t.invite_code,
                      tm.role AS my_role, t.created_at,
                      (SELECT COUNT(*) FROM team_members WHERE team_id = t.id) AS member_count
               FROM teams t
               JOIN team_members tm ON t.id = tm.team_id
               WHERE tm.user_id = %s
               ORDER BY t.created_at DESC""",
            (user_id,),
        )
        return jsonify({
            "success": True,
            "teams": [dict(t) for t in teams] if teams else [],
        }), 200
    except Exception as e:
        logger.error(f"[Team API] 获取团队列表失败: {e}")
        return jsonify({"success": False, "message": "获取团队列表失败"}), 500


# ============================================================
# GET /api/v1/teams/<id>/members - 获取团队成员
# ============================================================
@team_bp.route("/<int:team_id>/members", methods=["GET"])
@login_required
def get_members(current_user, team_id):
    """获取团队成员列表"""
    result = team_mgr.get_team_members(team_id, _uid(current_user))
    status = 200 if result.get("success") else 403
    return jsonify(result), status


# ============================================================
# POST /api/v1/teams/<id>/invite - 邀请成员
# ============================================================
@team_bp.route("/<int:team_id>/invite", methods=["POST"])
@login_required
def invite_member(current_user, team_id):
    """邀请成员加入团队"""
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip()
    role = data.get("role", Role.ANALYST)

    if not email:
        return jsonify({"success": False, "message": "邮箱不能为空"}), 400

    result = team_mgr.invite_member(
        team_id=team_id,
        inviter_id=_uid(current_user),
        email=email,
        role=role,
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


# ============================================================
# POST /api/v1/teams/join - 接受邀请
# ============================================================
@team_bp.route("/join", methods=["POST"])
@login_required
def join_team(current_user):
    """通过邀请 token 加入团队"""
    data = request.get_json(silent=True) or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"success": False, "message": "邀请 token 不能为空"}), 400

    result = team_mgr.accept_invitation(token, _uid(current_user))
    status = 200 if result.get("success") else 400
    return jsonify(result), status


# ============================================================
# PUT /api/v1/teams/<id>/members/<uid> - 更新成员角色
# ============================================================
@team_bp.route("/<int:team_id>/members/<int:user_id>", methods=["PUT"])
@login_required
def update_role(current_user, team_id, user_id):
    """更新团队成员角色"""
    data = request.get_json(silent=True) or {}
    new_role = data.get("role", "")

    result = team_mgr.update_member_role(
        team_id=team_id,
        operator_id=_uid(current_user),
        target_user_id=user_id,
        new_role=new_role,
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


# ============================================================
# DELETE /api/v1/teams/<id>/members/<uid> - 移除成员
# ============================================================
@team_bp.route("/<int:team_id>/members/<int:user_id>", methods=["DELETE"])
@login_required
def remove_member(current_user, team_id, user_id):
    """移除团队成员"""
    result = team_mgr.remove_member(
        team_id=team_id,
        operator_id=_uid(current_user),
        target_user_id=user_id,
    )
    status = 200 if result.get("success") else 400
    return jsonify(result), status


# ============================================================
# GET /api/v1/teams/roles - 获取角色列表
# ============================================================
@team_bp.route("/roles", methods=["GET"])
@login_required
def list_roles(current_user):
    """获取所有可分配角色及其权限"""
    roles = []
    for role_id in Role.ALL:
        roles.append({
            "id": role_id,
            "label": Role.LABELS.get(role_id, role_id),
            "permissions": [p for p in (Permission.__dict__) if not p.startswith("_")],
            "assignable": role_id != Role.OWNER,
        })
    return jsonify({"success": True, "roles": roles}), 200
