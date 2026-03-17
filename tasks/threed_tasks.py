"""
3D 生成异步任务
对应 PRD 7 - 异步任务队列 (3D 生成相关)

任务:
    - generate_3d_model: 执行 2D 转 3D 模型生成
    - render_3d_video: 执行 3D 模型视频渲染
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from celery_app import celery
from utils.logger import get_logger

logger = get_logger()


@celery.task(bind=True, name="tasks.threed_tasks.generate_3d_model",
             max_retries=2, time_limit=600)
def generate_3d_model(self, asset_id: str, user_id: int,
                      image_urls: list, provider: str = "meshy",
                      art_style: str = "realistic"):
    """
    执行 2D 转 3D 模型生成

    :param asset_id: 3D 资产 ID
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

        generator = ThreeDGenerator(meshy_key=meshy_key, tripo_key=tripo_key)

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "generating",
            "progress": 30,
        })

        # 生成 3D 模型
        image_url = image_urls[0]
        result = generator.generate_from_image(
            image_url=image_url,
            art_style=art_style,
        )

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "completed",
            "progress": 100,
        })

        # 保存结果到数据库
        _save_3d_result(asset_id, result)

        return {
            "asset_id": asset_id,
            "status": "completed",
            "model_url": result.get("model_url") if result else None,
        }

    except Exception as exc:
        logger.error(f"3D 生成失败: {exc}")
        _update_3d_status(asset_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=120)


@celery.task(bind=True, name="tasks.threed_tasks.render_3d_video",
             max_retries=1, time_limit=300)
def render_3d_video(self, asset_id: str, user_id: int,
                    template: str = "turntable", resolution: str = "1080p",
                    duration_sec: int = 10):
    """
    执行 3D 模型视频渲染

    :param asset_id: 3D 资产 ID
    :param user_id: 用户 ID
    :param template: 运镜模板
    :param resolution: 分辨率
    :param duration_sec: 时长
    """
    logger.info(f"[Task] 视频渲染: asset_id={asset_id}, template={template}")

    try:
        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "rendering",
            "progress": 30,
        })

        # 在生产环境中，这里应调用 Meshy/Tripo 的视频渲染 API
        # 或使用 Blender/Three.js 服务端渲染
        # 当前为占位实现

        video_url = f"/static/renders/{asset_id}_{template}.mp4"

        self.update_state(state="PROGRESS", meta={
            "asset_id": asset_id,
            "step": "completed",
            "progress": 100,
        })

        _save_render_result(asset_id, video_url)

        return {
            "asset_id": asset_id,
            "status": "completed",
            "video_url": video_url,
        }

    except Exception as exc:
        logger.error(f"视频渲染失败: {exc}")
        _update_3d_status(asset_id, "failed", str(exc))
        raise self.retry(exc=exc, countdown=60)


# ============================================================
# 辅助函数
# ============================================================

def _save_3d_result(asset_id: str, result: dict):
    """保存 3D 生成结果"""
    try:
        from database.connection import DatabaseManager

        db = DatabaseManager()
        db.execute("""
            UPDATE assets_3d
            SET status = 'completed',
                progress_pct = 100,
                glb_file_url = %s,
                thumbnail_url = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (
            result.get("model_url") if result else None,
            result.get("thumbnail_url") if result else None,
            asset_id,
        ))
    except Exception as e:
        logger.warning(f"3D 结果入库失败: {e}")


def _save_render_result(asset_id: str, video_url: str):
    """保存视频渲染结果"""
    try:
        from database.connection import DatabaseManager

        db = DatabaseManager()
        db.execute("""
            UPDATE assets_3d
            SET render_status = 'completed',
                video_url = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (video_url, asset_id))
    except Exception as e:
        logger.warning(f"渲染结果入库失败: {e}")


def _update_3d_status(asset_id: str, status: str, error_msg: str = None):
    """更新 3D 资产状态"""
    try:
        from database.connection import DatabaseManager

        db = DatabaseManager()
        db.execute("""
            UPDATE assets_3d
            SET status = %s, error_message = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, error_msg, asset_id))
    except Exception as e:
        logger.warning(f"3D 状态更新失败: {e}")
