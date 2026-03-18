"""
3D 资产生成 API 路由
对应 PRD 8.5 - 3D Asset Generation

端点:
    POST /api/v1/3d/generate                  发起 2D 转 3D 任务
    GET  /api/v1/3d/{asset_id}/status         轮询 3D 生成进度
    POST /api/v1/3d/{asset_id}/render-video   发起视频渲染任务
    GET  /api/v1/3d/{asset_id}/video          获取渲染视频
    GET  /api/v1/3d/assets                    获取用户的 3D 资产列表
    GET  /api/v1/3d/renders/<filename>        提供渲染视频文件访问
    GET  /api/v1/3d/templates                 获取可用运镜模板
    GET  /api/v1/3d/resolutions               获取可用分辨率
    DELETE /api/v1/3d/{asset_id}              删除 3D 资产
"""

import os
import json
from datetime import datetime

from flask import Blueprint, request, jsonify, send_from_directory

from auth.middleware import login_required
from auth.quota_middleware import quota_required
from utils.logger import get_logger

logger = get_logger()

threed_bp = Blueprint("threed", __name__, url_prefix="/api/v1/3d")

# 渲染视频输出目录
RENDERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "renders",
)
os.makedirs(RENDERS_DIR, exist_ok=True)


# ============================================================
# 数据库辅助函数
# ============================================================

def _get_db():
    """获取数据库连接（带降级到内存存储）"""
    try:
        from database.connection import db
        # 测试连接是否可用
        db.fetch_one("SELECT 1")
        return db
    except Exception:
        return None


def _create_asset_in_db(db, user_id, data):
    """在数据库中创建 3D 资产记录"""
    source_urls_json = json.dumps(data.get("image_urls", []))
    asset_id = db.insert_and_get_id("""
        INSERT INTO assets_3d (user_id, asin, source_image_urls, status, progress_pct)
        VALUES (%s, %s, %s, 'pending', 0)
    """, (user_id, data.get("asin"), source_urls_json))
    return asset_id


def _get_asset(db, asset_id, user_id):
    """从数据库获取 3D 资产"""
    return db.fetch_one("""
        SELECT * FROM assets_3d WHERE id = %s AND user_id = %s
    """, (asset_id, user_id))


def _update_asset(db, asset_id, **fields):
    """更新 3D 资产字段"""
    set_clauses = []
    values = []
    for key, val in fields.items():
        set_clauses.append(f"{key} = %s")
        values.append(val)
    values.append(asset_id)
    db.execute(
        f"UPDATE assets_3d SET {', '.join(set_clauses)}, updated_at = NOW() WHERE id = %s",
        tuple(values),
    )


# ============================================================
# 内存降级存储（数据库不可用时使用）
# ============================================================

_mem_assets = {}
_mem_counter = 0


def _mem_create_asset(user_id, data):
    global _mem_counter
    _mem_counter += 1
    asset_id = _mem_counter
    asset = {
        "id": asset_id,
        "user_id": user_id,
        "asin": data.get("asin"),
        "source_image_urls": json.dumps(data.get("image_urls", [])),
        "status": "pending",
        "progress_pct": 0,
        "glb_file_url": None,
        "thumbnail_url": None,
        "render_status": "none",
        "render_template": None,
        "render_resolution": None,
        "video_url": None,
        "error_message": None,
        "meshy_task_id": None,
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    }
    _mem_assets[asset_id] = asset
    return asset_id


def _mem_get_asset(asset_id, user_id):
    asset = _mem_assets.get(asset_id)
    if asset and asset["user_id"] == user_id:
        return asset
    return None


def _mem_update_asset(asset_id, **fields):
    if asset_id in _mem_assets:
        _mem_assets[asset_id].update(fields)
        _mem_assets[asset_id]["updated_at"] = datetime.now().isoformat()


# ============================================================
# 统一存储接口
# ============================================================

class AssetStore:
    """统一的资产存储接口，自动选择数据库或内存"""

    @staticmethod
    def create(user_id, data):
        db = _get_db()
        if db:
            return _create_asset_in_db(db, user_id, data)
        return _mem_create_asset(user_id, data)

    @staticmethod
    def get(asset_id, user_id):
        db = _get_db()
        if db:
            return _get_asset(db, asset_id, user_id)
        return _mem_get_asset(asset_id, user_id)

    @staticmethod
    def update(asset_id, **fields):
        db = _get_db()
        if db:
            _update_asset(db, asset_id, **fields)
        else:
            _mem_update_asset(asset_id, **fields)

    @staticmethod
    def list_by_user(user_id, page=1, page_size=20):
        db = _get_db()
        if db:
            total = db.fetch_one(
                "SELECT COUNT(*) AS cnt FROM assets_3d WHERE user_id = %s",
                (user_id,),
            )
            total_count = total["cnt"] if total else 0
            offset = (page - 1) * page_size
            assets = db.fetch_all("""
                SELECT * FROM assets_3d
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """, (user_id, page_size, offset))
            return assets, total_count
        else:
            user_assets = sorted(
                [a for a in _mem_assets.values() if a["user_id"] == user_id],
                key=lambda x: x["created_at"],
                reverse=True,
            )
            total_count = len(user_assets)
            start = (page - 1) * page_size
            return user_assets[start:start + page_size], total_count

    @staticmethod
    def delete(asset_id, user_id):
        db = _get_db()
        if db:
            return db.execute(
                "DELETE FROM assets_3d WHERE id = %s AND user_id = %s",
                (asset_id, user_id),
            )
        else:
            if asset_id in _mem_assets and _mem_assets[asset_id]["user_id"] == user_id:
                del _mem_assets[asset_id]
                return 1
            return 0


store = AssetStore()


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

    # 创建资产记录
    asset_id = store.create(current_user["user_id"], data)

    # 异步执行 3D 生成
    _execute_3d_generation_async(
        asset_id=asset_id,
        user_id=current_user["user_id"],
        image_urls=image_urls,
        provider=data.get("provider", "meshy"),
        art_style=data.get("art_style", "realistic"),
    )

    return jsonify({
        "success": True,
        "data": {
            "asset_id": asset_id,
            "status": "pending",
        },
    }), 201


def _execute_3d_generation_async(asset_id, user_id, image_urls, provider, art_style):
    """
    尝试通过 Celery 异步执行 3D 生成；
    如果 Celery 不可用，则同步执行。
    """
    try:
        from tasks.threed_tasks import generate_3d_model
        generate_3d_model.delay(
            asset_id=asset_id,
            user_id=user_id,
            image_urls=image_urls,
            provider=provider,
            art_style=art_style,
        )
        logger.info(f"[3D] Celery 异步任务已提交: asset_id={asset_id}")
    except Exception as e:
        logger.warning(f"[3D] Celery 不可用，使用同步执行: {e}")
        _execute_3d_generation_sync(asset_id, user_id, image_urls, provider, art_style)


def _execute_3d_generation_sync(asset_id, user_id, image_urls, provider, art_style):
    """同步执行 3D 模型生成"""
    try:
        store.update(asset_id, status="processing", progress_pct=10)

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

        if not meshy_key and not tripo_key:
            store.update(
                asset_id,
                status="failed",
                error_message="未配置 Meshy 或 Tripo API Key，请在 Settings > API Keys 中配置",
            )
            return

        generator = ThreeDGenerator(
            meshy_key=meshy_key,
            tripo_key=tripo_key,
        )

        store.update(asset_id, progress_pct=30)

        # 使用第一张图片生成 3D 模型
        image_url = image_urls[0]
        result = generator.generate_from_image(
            image_url=image_url,
            art_style=art_style,
        )

        if result and result.get("status") == "success":
            model_url = result.get("model_urls", {}).get("glb") or result.get("model_path")
            thumbnail = result.get("thumbnail", "")
            store.update(
                asset_id,
                status="completed",
                progress_pct=100,
                glb_file_url=model_url,
                thumbnail_url=thumbnail,
                meshy_task_id=result.get("task_id"),
            )
            logger.info(f"[3D] 生成完成: asset_id={asset_id}")
        else:
            error_msg = result.get("error", "3D 模型生成未返回结果") if result else "生成引擎无响应"
            store.update(asset_id, status="failed", error_message=error_msg)
            logger.warning(f"[3D] 生成失败: asset_id={asset_id}, error={error_msg}")

    except Exception as e:
        store.update(asset_id, status="failed", error_message=str(e))
        logger.error(f"[3D] 生成任务异常: {e}")


# ============================================================
# 轮询进度
# ============================================================

@threed_bp.route("/<int:asset_id>/status", methods=["GET"])
@login_required
def get_3d_status(current_user, asset_id):
    """轮询 3D 生成进度"""
    asset = store.get(asset_id, current_user["user_id"])
    if not asset:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    response = {
        "asset_id": asset["id"],
        "status": asset["status"],
        "progress_pct": asset["progress_pct"],
    }

    if asset["status"] == "completed":
        response["glb_file_url"] = asset["glb_file_url"]
        response["model_url"] = asset["glb_file_url"]  # 前端兼容字段
        response["thumbnail_url"] = asset["thumbnail_url"]
    elif asset["status"] == "failed":
        response["error"] = asset.get("error_message")

    return jsonify({"success": True, "data": response})


# ============================================================
# 视频渲染（真实实现）
# ============================================================

@threed_bp.route("/<int:asset_id>/render-video", methods=["POST"])
@login_required
@quota_required("render_video")
def render_video(current_user, asset_id):
    """
    发起视频渲染任务

    请求体:
        template: str - 运镜模板 (turntable/zoom/orbit, 默认 turntable)
        resolution: str - 分辨率 (720p/1080p/4k, 默认 1080p)
        duration_sec: int - 时长秒数 (默认 10)
        environment: str - 环境光预设 (studio/daylight/warm/dark/gradient, 默认 studio)
    """
    asset = store.get(asset_id, current_user["user_id"])
    if not asset:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    if asset["status"] != "completed":
        return jsonify({"success": False, "error": "3D 模型尚未生成完成"}), 400

    if asset.get("render_status") in ("pending", "rendering"):
        return jsonify({"success": False, "error": "视频正在渲染中"}), 409

    data = request.get_json() or {}
    template = data.get("template", "turntable")
    resolution = data.get("resolution", "1080p")
    environment = data.get("environment", "studio")

    # 验证参数
    from analysis.model_3d.video_renderer import VideoRenderer
    valid_templates = [t["id"] for t in VideoRenderer.get_available_templates()]
    valid_resolutions = [r["id"] for r in VideoRenderer.get_available_resolutions()]

    if template not in valid_templates:
        return jsonify({"success": False, "error": f"不支持的运镜模板: {template}"}), 400
    if resolution not in valid_resolutions:
        return jsonify({"success": False, "error": f"不支持的分辨率: {resolution}"}), 400

    store.update(
        asset_id,
        render_status="pending",
        render_template=template,
        render_resolution=resolution,
    )

    # 尝试异步渲染，降级为同步
    _execute_video_render_async(
        asset_id=asset_id,
        user_id=current_user["user_id"],
        glb_file_url=asset["glb_file_url"],
        template=template,
        resolution=resolution,
        environment=environment,
    )

    return jsonify({
        "success": True,
        "data": {
            "asset_id": asset_id,
            "render_status": "pending",
            "template": template,
            "resolution": resolution,
        },
    })


def _execute_video_render_async(asset_id, user_id, glb_file_url, template, resolution, environment):
    """尝试通过 Celery 异步渲染，降级为同步"""
    try:
        from tasks.threed_tasks import render_3d_video
        render_3d_video.delay(
            asset_id=asset_id,
            user_id=user_id,
            glb_file_url=glb_file_url,
            template=template,
            resolution=resolution,
            environment=environment,
        )
        logger.info(f"[3D] 渲染任务已提交 Celery: asset_id={asset_id}")
    except Exception as e:
        logger.warning(f"[3D] Celery 不可用，同步渲染: {e}")
        _execute_video_render_sync(asset_id, glb_file_url, template, resolution, environment)


def _execute_video_render_sync(asset_id, glb_file_url, template, resolution, environment):
    """同步执行视频渲染"""
    try:
        store.update(asset_id, render_status="rendering")

        from analysis.model_3d.video_renderer import VideoRenderer
        renderer = VideoRenderer(output_dir=RENDERS_DIR)

        result = renderer.render_video(
            glb_file_path=glb_file_url,
            template=template,
            resolution=resolution,
            environment=environment,
            asset_id=str(asset_id),
        )

        if result.get("success"):
            store.update(
                asset_id,
                render_status="completed",
                video_url=result.get("video_url"),
            )
            logger.info(f"[3D] 视频渲染完成: asset_id={asset_id}")
        else:
            store.update(
                asset_id,
                render_status="failed",
                error_message=result.get("error", "视频渲染失败"),
            )
            logger.warning(f"[3D] 视频渲染失败: asset_id={asset_id}, error={result.get('error')}")

    except Exception as e:
        store.update(asset_id, render_status="failed", error_message=str(e))
        logger.error(f"[3D] 视频渲染异常: {e}")


# ============================================================
# 获取渲染视频
# ============================================================

@threed_bp.route("/<int:asset_id>/video", methods=["GET"])
@login_required
def get_video(current_user, asset_id):
    """获取渲染视频信息"""
    asset = store.get(asset_id, current_user["user_id"])
    if not asset:
        return jsonify({"success": False, "error": "资产不存在"}), 404

    response = {
        "asset_id": asset_id,
        "render_status": asset.get("render_status", "none"),
        "render_template": asset.get("render_template"),
        "render_resolution": asset.get("render_resolution"),
    }

    if asset.get("render_status") == "completed":
        response["video_url"] = asset.get("video_url")
    elif asset.get("render_status") == "failed":
        response["error"] = asset.get("error_message")

    return jsonify({"success": True, "data": response})


# ============================================================
# 渲染视频文件访问
# ============================================================

@threed_bp.route("/renders/<path:filename>", methods=["GET"])
def serve_render_file(filename):
    """提供渲染视频文件的静态访问"""
    return send_from_directory(RENDERS_DIR, filename)


# ============================================================
# 资产列表
# ============================================================

@threed_bp.route("/assets", methods=["GET"])
@login_required
def list_assets(current_user):
    """获取用户的 3D 资产列表"""
    page = request.args.get("page", 1, type=int)
    page_size = request.args.get("page_size", 20, type=int)

    assets, total_count = store.list_by_user(
        current_user["user_id"], page, page_size
    )

    # 标准化输出格式
    formatted = []
    for a in assets:
        source_urls = a.get("source_image_urls")
        if isinstance(source_urls, str):
            try:
                source_urls = json.loads(source_urls)
            except (json.JSONDecodeError, TypeError):
                source_urls = []

        formatted.append({
            "id": a["id"],
            "asset_id": a["id"],
            "asin": a.get("asin"),
            "status": a["status"],
            "progress_pct": a.get("progress_pct", 0),
            "glb_file_url": a.get("glb_file_url"),
            "model_url": a.get("glb_file_url"),  # 前端兼容字段
            "thumbnail_url": a.get("thumbnail_url"),
            "render_status": a.get("render_status", "none"),
            "render_template": a.get("render_template"),
            "video_url": a.get("video_url"),
            "source_image_urls": source_urls,
            "name": f"3D Model - {a.get('asin') or a['id']}",
            "format": "GLB",
            "created_at": str(a.get("created_at", "")),
            "updated_at": str(a.get("updated_at", "")),
        })

    return jsonify({
        "success": True,
        "data": {
            "assets": formatted,
            "total_count": total_count,
            "page": page,
            "page_size": page_size,
        },
    })


# ============================================================
# 删除资产
# ============================================================

@threed_bp.route("/<int:asset_id>", methods=["DELETE"])
@login_required
def delete_asset(current_user, asset_id):
    """删除 3D 资产"""
    affected = store.delete(asset_id, current_user["user_id"])
    if affected:
        return jsonify({"success": True, "message": "资产已删除"})
    return jsonify({"success": False, "error": "资产不存在"}), 404


# ============================================================
# 元数据接口
# ============================================================

@threed_bp.route("/templates", methods=["GET"])
def list_templates():
    """获取可用的运镜模板"""
    from analysis.model_3d.video_renderer import VideoRenderer
    return jsonify({
        "success": True,
        "data": VideoRenderer.get_available_templates(),
    })


@threed_bp.route("/resolutions", methods=["GET"])
def list_resolutions():
    """获取可用的分辨率"""
    from analysis.model_3d.video_renderer import VideoRenderer
    return jsonify({
        "success": True,
        "data": VideoRenderer.get_available_resolutions(),
    })


@threed_bp.route("/environments", methods=["GET"])
def list_environments():
    """获取可用的环境光预设"""
    from analysis.model_3d.video_renderer import VideoRenderer
    return jsonify({
        "success": True,
        "data": VideoRenderer.get_available_environments(),
    })
