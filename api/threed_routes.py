"""
3D 资产生成 API 路由
对应 PRD 8.5 - 3D Asset Generation

端点:
    POST /api/v1/3d/generate                  发起 2D 转 3D 任务
    GET  /api/v1/3d/{asset_id}/status         轮询 3D 生成进度
    POST /api/v1/3d/{asset_id}/render-video   发起视频渲染任务
    GET  /api/v1/3d/{asset_id}/video          获取渲染视频
    GET  /api/v1/3d/assets                    获取用户的 3D 资产列表
"""

import uuid
from datetime import datetime

from flask import Blueprint, request, jsonify

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

threed_bp = Blueprint("threed", __name__, url_prefix="/api/v1/3d")

# 内存存储（生产环境应替换为数据库）
_3d_assets = {}


# ============================================================
# 2D 转 3D
# ============================================================

@threed_bp.route("/generate", methods=["POST"])
@login_required
@quota_required("3d_generate")
def generate_3d(current_user):
    """
    发起 2D 转 3D 任务

    请求体:
        image_urls: list[str] - 源图片 URL 列表 (1-3张)
        asin: str - 关联 ASIN (可选)
        provider: str - 3D 生成服务商 (meshy/tripo, 默认 meshy)
        art_style: str - 风格 (realistic/cartoon, 默认 realistic)
        output_format: str - 输出格式 (glb/fbx/obj, 默认 glb)
    """
    data = request.get_json() or {}

    image_urls = data.get("image_urls", [])
    if not image_urls:
        return jsonify({"success": False, "error": "请提供至少一张源图片URL"}), 400

    if len(image_urls) > 3:
        return jsonify({"success": False, "error": "最多支持3张源图片"}), 400

    provider = data.get("provider", "meshy")
    art_style = data.get("art_style", "realistic")
    output_format = data.get("output_format", "glb")

    asset_id = str(uuid.uuid4())[:12]
    asset = {
        "asset_id": asset_id,
        "user_id": current_user["user_id"],
        "asin": data.get("asin"),
        "source_image_urls": image_urls,
        "provider": provider,
        "art_style": art_style,
        "output_format": output_format,
        "status": "pending",
        "progress_pct": 0,
        "glb_file_url": None,
        "thumbnail_url": None,
        "render_status": "none",
        "video_url": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _3d_assets[asset_id] = asset

    # 异步执行 3D 生成
    _execute_3d_generation(asset, current_user["user_id"])

    return jsonify({
        "success": True,
        "data": {
            "asset_id": asset_id,
            "status": "pending",
        },
    }), 201


def _execute_3d_generation(asset: dict, user_id: int):
    """执行 3D 模型生成"""
    try:
        asset["status"] = "processing"
        asset["updated_at"] = datetime.now().isoformat()

        from analysis.model_3d.generator import ThreeDGenerator
        from auth.api_keys_config import APIKeysConfigManager

        # 获取用户的 API Key
        meshy_key = None
        tripo_key = None

        try:
            meshy_config = APIKeysConfigManager.get_service_config(
                user_id, "meshy", decrypt=True
            )
            if meshy_config:
                meshy_key = meshy_config.get("api_key")
        except Exception:
            pass

        try:
            tripo_config = APIKeysConfigManager.get_service_config(
                user_id, "tripo", decrypt=True
            )
            if tripo_config:
                tripo_key = tripo_config.get("api_key")
        except Exception:
            pass

        generator = ThreeDGenerator(
            meshy_key=meshy_key,
            tripo_key=tripo_key,
        )

        # 使用第一张图片生成 3D 模型
        image_url = asset["source_image_urls"][0]
        result = generator.generate_from_image(
            image_url=image_url,
            art_style=asset.get("art_style", "realistic"),
        )

        if result and result.get("model_url"):
            asset["status"] = "completed"
            asset["progress_pct"] = 100
            asset["glb_file_url"] = result.get("model_url")
            asset["thumbnail_url"] = result.get("thumbnail_url")
        else:
            asset["status"] = "failed"
            asset["error_message"] = "3D 模型生成未返回结果"

        asset["updated_at"] = datetime.now().isoformat()

    except Exception as e:
        asset["status"] = "failed"
        asset["error_message"] = str(e)
        asset["updated_at"] = datetime.now().isoformat()
        logger.error(f"3D 生成任务失败: {e}")


# ============================================================
# 轮询进度
# ============================================================

@threed_bp.route("/<asset_id>/status", methods=["GET"])
@login_required
def get_3d_status(current_user, asset_id):
    """轮询 3D 生成进度"""
    asset = _3d_assets.get(asset_id)
    if not asset or asset["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    response = {
        "asset_id": asset["asset_id"],
        "status": asset["status"],
        "progress_pct": asset["progress_pct"],
    }

    if asset["status"] == "completed":
        response["glb_file_url"] = asset["glb_file_url"]
        response["thumbnail_url"] = asset["thumbnail_url"]
    elif asset["status"] == "failed":
        response["error"] = asset.get("error_message")

    return jsonify({"success": True, "data": response})


# ============================================================
# 视频渲染
# ============================================================

@threed_bp.route("/<asset_id>/render-video", methods=["POST"])
@login_required
@quota_required("render_video")
def render_video(current_user, asset_id):
    """
    发起视频渲染任务

    请求体:
        template: str - 运镜模板 (turntable/zoom/orbit, 默认 turntable)
        resolution: str - 分辨率 (720p/1080p/4k, 默认 1080p)
        duration_sec: int - 时长秒数 (默认 10)
    """
    asset = _3d_assets.get(asset_id)
    if not asset or asset["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    if asset["status"] != "completed":
        return jsonify({"success": False, "error": "3D 模型尚未生成完成"}), 400

    if asset["render_status"] in ("pending", "rendering"):
        return jsonify({"success": False, "error": "视频正在渲染中"}), 409

    data = request.get_json() or {}
    template = data.get("template", "turntable")
    resolution = data.get("resolution", "1080p")
    duration_sec = data.get("duration_sec", 10)

    asset["render_status"] = "pending"
    asset["render_template"] = template
    asset["render_resolution"] = resolution
    asset["updated_at"] = datetime.now().isoformat()

    # 异步执行渲染（当前为模拟）
    _execute_video_render(asset, template, resolution, duration_sec)

    return jsonify({
        "success": True,
        "data": {
            "asset_id": asset_id,
            "render_status": "pending",
            "template": template,
            "resolution": resolution,
        },
    })


def _execute_video_render(asset: dict, template: str, resolution: str, duration_sec: int):
    """执行视频渲染（模拟）"""
    try:
        asset["render_status"] = "rendering"
        asset["updated_at"] = datetime.now().isoformat()

        # 在生产环境中，这里应调用 Meshy/Tripo 的视频渲染 API
        # 或使用 Three.js 服务端渲染
        # 当前为占位实现

        asset["render_status"] = "completed"
        asset["video_url"] = f"/static/renders/{asset['asset_id']}_{template}.mp4"
        asset["updated_at"] = datetime.now().isoformat()

    except Exception as e:
        asset["render_status"] = "failed"
        asset["error_message"] = str(e)
        asset["updated_at"] = datetime.now().isoformat()
        logger.error(f"视频渲染失败: {e}")


@threed_bp.route("/<asset_id>/video", methods=["GET"])
@login_required
def get_video(current_user, asset_id):
    """获取渲染视频"""
    asset = _3d_assets.get(asset_id)
    if not asset or asset["user_id"] != current_user["user_id"]:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    response = {
        "asset_id": asset_id,
        "render_status": asset["render_status"],
        "render_template": asset.get("render_template"),
        "render_resolution": asset.get("render_resolution"),
    }

    if asset["render_status"] == "completed":
        response["video_url"] = asset["video_url"]
    elif asset["render_status"] == "failed":
        response["error"] = asset.get("error_message")

    return jsonify({"success": True, "data": response})


# ============================================================
# 资产列表
# ============================================================

@threed_bp.route("/assets", methods=["GET"])
@login_required
def list_assets(current_user):
    """获取用户的 3D 资产列表"""
    user_id = current_user["user_id"]
    user_assets = [
        a for a in _3d_assets.values()
        if a["user_id"] == user_id
    ]
    user_assets.sort(key=lambda x: x["created_at"], reverse=True)

    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)
    start = (page - 1) * page_size
    end = start + page_size

    return jsonify({
        "success": True,
        "data": {
            "assets": user_assets[start:end],
            "total_count": len(user_assets),
            "page": page,
            "page_size": page_size,
        },
    })
