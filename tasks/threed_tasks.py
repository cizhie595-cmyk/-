"""
3D 生成异步任务
对应 PRD 7 - 异步任务队列 (3D 生成相关)

任务:
    - generate_3d_model: 执行 2D 转 3D 模型生成
    - render_3d_video: 执行 3D 模型视频渲染（真实 VideoRenderer 调用）
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery
from utils.logger import get_logger

logger = get_logger()

# 渲染视频输出目录
RENDERS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "renders",
)
os.makedirs(RENDERS_DIR, exist_ok=True)


@celery.task(bind=True, name="tasks.threed_tasks.generate_3d_model",
             max_retries=2, time_limit=600)
def generate_3d_model(self, asset_id: int, user_id: int,
                      image_urls: list, provider: str = "meshy",
                      art_style: str = "realistic"):
    """
    执行 2D 转 3D 模型生成

    :param asset_id: 3D 资产 ID (数据库主键)
    :param user_id: 用户 ID
    :param image_urls: 源图片 URL 列表
    :param provider: 服务商 (meshy/tripo)
    :param art_style: 风格
    """
    logger.info(f"[Task] 3D 生成: asset_id={asset_id}, provider={provider}")

    try:
        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "initializing",
            "progress": 10,
        })

        _update_3d_status(asset_id, "processing", progress_pct=10)

        from analysis.model_3d.generator import ThreeDGenerator
        from auth.api_keys_config import APIKeysConfigManager

        # 获取用户 API Key
        meshy_key = None
        tripo_key = None

        try:
            config = APIKeysConfigManager.get_service_config(user_id, "meshy", decrypt=True)
            if config:
                meshy_key = config.get("api_key")
        except Exception:
            pass

        try:
            config = APIKeysConfigManager.get_service_config(user_id, "tripo", decrypt=True)
            if config:
                tripo_key = config.get("api_key")
        except Exception:
            pass

        if not meshy_key and not tripo_key:
            _update_3d_status(
                asset_id, "failed",
                error_msg="未配置 Meshy 或 Tripo API Key",
            )
            return {"asset_id": asset_id, "status": "failed", "error": "No API key configured"}

        generator = ThreeDGenerator(meshy_key=meshy_key, tripo_key=tripo_key)

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "generating",
            "progress": 30,
        })
        _update_3d_status(asset_id, "processing", progress_pct=30)

        # 生成 3D 模型
        image_url = image_urls[0]
        result = generator.generate_from_image(
            image_url=image_url,
            art_style=art_style,
        )

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "finalizing",
            "progress": 90,
        })

        # 保存结果到数据库
        if result and result.get("status") == "success":
            model_url = result.get("model_urls", {}).get("glb") or result.get("model_path")
            thumbnail = result.get("thumbnail", "")
            _save_3d_result(asset_id, model_url, thumbnail)

            self.update_state(state="PROGRESS", meta={
                "asset_id": asset_id,
                "step": "completed",
                "progress": 100,
            })

            return {
                "asset_id": asset_id,
                "status": "completed",
                "model_url": model_url,
            }
        else:
            error_msg = result.get("error", "3D 模型生成未返回结果") if result else "生成引擎无响应"
            _update_3d_status(asset_id, "failed", error_msg=error_msg)
            return {"asset_id": asset_id, "status": "failed", "error": error_msg}

    except Exception as exc:
        logger.error(f"3D 生成失败: {exc}")
        _update_3d_status(asset_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=120)


@celery.task(bind=True, name="tasks.threed_tasks.render_3d_video",
             max_retries=1, time_limit=300)
def render_3d_video(self, asset_id: int, user_id: int,
                    glb_file_url: str = None,
                    template: str = "turntable", resolution: str = "1080p",
                    environment: str = "studio",
                    duration_sec: int = 10):
    """
    执行 3D 模型视频渲染（真实 VideoRenderer 调用）

    :param asset_id: 3D 资产 ID
    :param user_id: 用户 ID
    :param glb_file_url: GLB 模型文件路径或 URL
    :param template: 运镜模板
    :param resolution: 分辨率
    :param environment: 环境光预设
    :param duration_sec: 时长
    """
    logger.info(f"[Task] 视频渲染: asset_id={asset_id}, template={template}")

    try:
        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "initializing",
            "progress": 10,
        })

        _update_render_status(asset_id, "rendering")

        # 如果没有传入 glb_file_url，从数据库获取
        if not glb_file_url:
            try:
                from database.connection import db
                asset = db.fetch_one(
                    "SELECT glb_file_url FROM assets_3d WHERE id = %s",
                    (asset_id,),
                )
                if asset:
                    glb_file_url = asset["glb_file_url"]
            except Exception:
                pass

        if not glb_file_url:
            _update_render_status(asset_id, "failed", error_msg="无 GLB 模型文件")
            return {"asset_id": asset_id, "status": "failed", "error": "No GLB file"}

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "rendering",
            "progress": 30,
        })

        # 使用真实的 VideoRenderer 进行渲染
        from analysis.model_3d.video_renderer import VideoRenderer
        renderer = VideoRenderer(output_dir=RENDERS_DIR)

        result = renderer.render_video(
            glb_file_path=glb_file_url,
            template=template,
            resolution=resolution,
            environment=environment,
            asset_id=str(asset_id),
        )

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "finalizing",
            "progress": 90,
        })

        if result.get("success"):
            video_url = result.get("video_url", "")
            _save_render_result(asset_id, video_url)

            self.update_state(state="PROGRESS", meta={
                "asset_id": asset_id,
                "step": "completed",
                "progress": 100,
            })

            logger.info(
                f"[Task] 视频渲染完成: asset_id={asset_id}, "
                f"size={result.get('file_size_mb', 0)}MB"
            )

            return {
                "asset_id": asset_id,
                "status": "completed",
                "video_url": video_url,
                "duration_sec": result.get("duration_sec"),
                "file_size_mb": result.get("file_size_mb"),
            }
        else:
            error_msg = result.get("error", "视频渲染失败")
            _update_render_status(asset_id, "failed", error_msg=error_msg)
            return {"asset_id": asset_id, "status": "failed", "error": error_msg}

    except Exception as exc:
        logger.error(f"视频渲染失败: {exc}")
        _update_render_status(asset_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=60)


# ============================================================
# 辅助函数
# ============================================================

def _save_3d_result(asset_id: int, model_url: str, thumbnail_url: str = None):
    """保存 3D 生成结果"""
    try:
        from database.connection import db
        db.execute("""
            UPDATE assets_3d
            SET status = 'completed',
                progress_pct = 100,
                glb_file_url = %s,
                thumbnail_url = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (model_url, thumbnail_url, asset_id))
    except Exception as e:
        logger.warning(f"3D 结果入库失败: {e}")


def _save_render_result(asset_id: int, video_url: str):
    """保存视频渲染结果"""
    try:
        from database.connection import db
        db.execute("""
            UPDATE assets_3d
            SET render_status = 'completed',
                video_url = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (video_url, asset_id))
    except Exception as e:
        logger.warning(f"渲染结果入库失败: {e}")


def _update_3d_status(asset_id: int, status: str, error_msg: str = None,
                      progress_pct: int = None):
    """更新 3D 资产状态"""
    try:
        from database.connection import db
        if progress_pct is not None:
            db.execute("""
                UPDATE assets_3d
                SET status = %s, error_message = %s, progress_pct = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, error_msg, progress_pct, asset_id))
        else:
            db.execute("""
                UPDATE assets_3d
                SET status = %s, error_message = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, error_msg, asset_id))
    except Exception as e:
        logger.warning(f"3D 状态更新失败: {e}")


def _update_render_status(asset_id: int, status: str, error_msg: str = None):
    """更新渲染状态"""
    try:
        from database.connection import db
        db.execute("""
            UPDATE assets_3d
            SET render_status = %s, error_message = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, error_msg, asset_id))
    except Exception as e:
        logger.warning(f"渲染状态更新失败: {e}")
