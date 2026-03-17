"""
素材批量下载 API 路由 (PRD 3.3.1)

提供:
  - 单品图片 ZIP 打包下载
  - 项目级素材批量导出
  - 3D 资产文件下载
"""

import os
import io
import zipfile
from flask import Blueprint, request, jsonify, send_file

from auth.middleware import login_required
from utils.logger import get_logger

logger = get_logger()

asset_download_bp = Blueprint("asset_download", __name__, url_prefix="/api/v1/assets")


# ============================================================
# GET /api/v1/assets/download/<asin> - 下载单品素材 ZIP
# ============================================================
@asset_download_bp.route("/download/<asin>", methods=["GET"])
@login_required
def download_product_assets(current_user, asin):
    """
    打包下载指定 ASIN 的所有素材（主图、附图、A+ 图片等）

    查询参数:
        include_3d: bool - 是否包含 3D 模型文件 (默认 false)
        include_video: bool - 是否包含渲染视频 (默认 false)

    响应: application/zip 文件流
    """
    include_3d = request.args.get("include_3d", "false").lower() == "true"
    include_video = request.args.get("include_video", "false").lower() == "true"

    try:
        # 查找产品图片目录
        base_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
        product_dir = os.path.join(base_dir, "products", asin)

        if not os.path.exists(product_dir):
            return jsonify({
                "success": False,
                "message": f"未找到 ASIN {asin} 的素材文件",
            }), 404

        # 创建内存中的 ZIP 文件
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            files_added = 0

            # 添加产品图片
            images_dir = os.path.join(product_dir, "images")
            if os.path.exists(images_dir):
                for fname in os.listdir(images_dir):
                    fpath = os.path.join(images_dir, fname)
                    if os.path.isfile(fpath) and _is_image(fname):
                        zf.write(fpath, f"images/{fname}")
                        files_added += 1

            # 添加 A+ 内容图片
            aplus_dir = os.path.join(product_dir, "aplus")
            if os.path.exists(aplus_dir):
                for fname in os.listdir(aplus_dir):
                    fpath = os.path.join(aplus_dir, fname)
                    if os.path.isfile(fpath) and _is_image(fname):
                        zf.write(fpath, f"aplus/{fname}")
                        files_added += 1

            # 添加 3D 模型文件
            if include_3d:
                threed_dir = os.path.join(product_dir, "3d")
                if os.path.exists(threed_dir):
                    for fname in os.listdir(threed_dir):
                        fpath = os.path.join(threed_dir, fname)
                        if os.path.isfile(fpath) and _is_3d_file(fname):
                            zf.write(fpath, f"3d_models/{fname}")
                            files_added += 1

            # 添加渲染视频
            if include_video:
                video_dir = os.path.join(product_dir, "videos")
                if os.path.exists(video_dir):
                    for fname in os.listdir(video_dir):
                        fpath = os.path.join(video_dir, fname)
                        if os.path.isfile(fpath) and _is_video(fname):
                            zf.write(fpath, f"videos/{fname}")
                            files_added += 1

            if files_added == 0:
                return jsonify({
                    "success": False,
                    "message": f"ASIN {asin} 的素材目录为空",
                }), 404

        zip_buffer.seek(0)
        logger.info(f"[Asset Download] 已打包 {asin} 的 {files_added} 个文件")

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{asin}_assets.zip",
        )

    except Exception as e:
        logger.error(f"[Asset Download] 打包失败: {e}")
        return jsonify({
            "success": False,
            "message": f"素材打包失败: {str(e)}",
        }), 500


# ============================================================
# GET /api/v1/assets/download/project/<project_id> - 项目级批量导出
# ============================================================
@asset_download_bp.route("/download/project/<project_id>", methods=["GET"])
@login_required
def download_project_assets(current_user, project_id):
    """
    打包下载整个项目的所有产品素材

    查询参数:
        max_products: int - 最多包含多少个产品 (默认 50)
        image_only: bool - 仅包含图片 (默认 true)
    """
    max_products = int(request.args.get("max_products", 50))
    image_only = request.args.get("image_only", "true").lower() == "true"

    try:
        base_dir = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "data"))
        project_dir = os.path.join(base_dir, "projects", str(project_id))

        if not os.path.exists(project_dir):
            return jsonify({
                "success": False,
                "message": f"未找到项目 {project_id} 的数据目录",
            }), 404

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            files_added = 0
            products_added = 0

            # 遍历项目下的产品目录
            products_dir = os.path.join(project_dir, "products")
            if os.path.exists(products_dir):
                for asin_dir_name in sorted(os.listdir(products_dir)):
                    if products_added >= max_products:
                        break

                    asin_path = os.path.join(products_dir, asin_dir_name)
                    if not os.path.isdir(asin_path):
                        continue

                    # 添加该产品的图片
                    images_dir = os.path.join(asin_path, "images")
                    if os.path.exists(images_dir):
                        for fname in os.listdir(images_dir):
                            fpath = os.path.join(images_dir, fname)
                            if os.path.isfile(fpath) and _is_image(fname):
                                zf.write(fpath, f"{asin_dir_name}/images/{fname}")
                                files_added += 1

                    if not image_only:
                        # 添加 3D 模型
                        threed_dir = os.path.join(asin_path, "3d")
                        if os.path.exists(threed_dir):
                            for fname in os.listdir(threed_dir):
                                fpath = os.path.join(threed_dir, fname)
                                if os.path.isfile(fpath):
                                    zf.write(fpath, f"{asin_dir_name}/3d/{fname}")
                                    files_added += 1

                    products_added += 1

            if files_added == 0:
                return jsonify({
                    "success": False,
                    "message": "项目中没有可下载的素材",
                }), 404

        zip_buffer.seek(0)
        logger.info(f"[Asset Download] 项目 {project_id}: 打包 {products_added} 个产品, {files_added} 个文件")

        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"project_{project_id}_assets.zip",
        )

    except Exception as e:
        logger.error(f"[Asset Download] 项目素材打包失败: {e}")
        return jsonify({
            "success": False,
            "message": f"项目素材打包失败: {str(e)}",
        }), 500


# ============================================================
# Helper functions
# ============================================================

def _is_image(filename: str) -> bool:
    """判断是否为图片文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff")


def _is_3d_file(filename: str) -> bool:
    """判断是否为 3D 模型文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in (".glb", ".gltf", ".obj", ".fbx", ".stl", ".usdz")


def _is_video(filename: str) -> bool:
    """判断是否为视频文件"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in (".mp4", ".webm", ".mov", ".avi")
