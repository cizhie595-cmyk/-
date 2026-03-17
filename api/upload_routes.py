"""
文件上传 API 路由
对应 PRD 3.1.1 - 输入方式 2：上传后台数据表
"""

import os
from flask import Blueprint, request, jsonify
from auth.user_model import token_required
from utils.file_upload_parser import FileUploadParser, FileUploadAPI
from utils.logger import get_logger

logger = get_logger()

upload_bp = Blueprint("upload", __name__, url_prefix="/api/v1/upload")


@upload_bp.route("/parse", methods=["POST"])
@token_required
def upload_and_parse(current_user):
    """
    上传并解析后台数据表

    POST /api/v1/upload/parse
    Content-Type: multipart/form-data
    Body: file (csv/xlsx)

    Response: {
        "success": bool,
        "headers": list,
        "column_mapping": dict,
        "total_rows": int,
        "asin_count": int,
        "search_term_count": int,
        "preview": list (前10行),
    }
    """
    if "file" not in request.files:
        return jsonify({"error": "未上传文件"}), 400

    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "文件名为空"}), 400

    try:
        # 保存文件
        save_result = FileUploadAPI.save_upload(file, current_user["id"])

        # 解析文件
        parse_result = FileUploadAPI.parse_upload(save_result["file_path"])

        if not parse_result["success"]:
            return jsonify({"error": parse_result["error"]}), 400

        # 返回预览（前10行）
        preview = parse_result["rows"][:10]
        for row in preview:
            row.pop("_raw", None)

        return jsonify({
            "success": True,
            "file_id": save_result["file_id"],
            "filename": save_result["filename"],
            "headers": parse_result["headers"],
            "column_mapping": parse_result["column_mapping"],
            "total_rows": parse_result["total_rows"],
            "asin_count": parse_result["asin_count"],
            "search_term_count": parse_result["search_term_count"],
            "preview": preview,
        })

    except Exception as e:
        logger.error(f"文件上传解析失败: {e}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/confirm-mapping", methods=["POST"])
@token_required
def confirm_column_mapping(current_user):
    """
    确认/修改列映射后重新解析

    POST /api/v1/upload/confirm-mapping
    Body: {
        "file_id": str,
        "column_mapping": {
            "asin": "用户选择的列名",
            "search_term": "...",
        }
    }
    """
    data = request.get_json()
    if not data or "file_id" not in data:
        return jsonify({"error": "缺少 file_id"}), 400

    file_id = data["file_id"]
    mapping = data.get("column_mapping", {})

    # 查找已上传的文件
    upload_dir = FileUploadAPI.UPLOAD_DIR
    matching_files = [
        f for f in os.listdir(upload_dir)
        if f.startswith(file_id)
    ] if os.path.exists(upload_dir) else []

    if not matching_files:
        return jsonify({"error": "文件不存在或已过期"}), 404

    file_path = os.path.join(upload_dir, matching_files[0])

    try:
        parser = FileUploadParser()
        result = parser.parse_file(file_path)

        if not result["success"]:
            return jsonify({"error": result["error"]}), 400

        # 使用用户指定的映射重新标准化
        parser.update_column_mapping(mapping)
        standardized = parser._standardize_rows(
            [r["_raw"] for r in result["rows"] if "_raw" in r],
            {**result["column_mapping"], **mapping},
        )

        # 提取查询项
        lookup_items = parser.get_asins_for_lookup(standardized)

        return jsonify({
            "success": True,
            "total_rows": len(standardized),
            "lookup_items": len(lookup_items),
            "asin_count": sum(1 for i in lookup_items if i["type"] == "asin"),
            "search_term_count": sum(1 for i in lookup_items if i["type"] == "search_term"),
        })

    except Exception as e:
        logger.error(f"列映射确认失败: {e}")
        return jsonify({"error": str(e)}), 500


@upload_bp.route("/trends", methods=["POST"])
@token_required
def get_google_trends(current_user):
    """
    获取 Google Trends 趋势数据

    POST /api/v1/upload/trends
    Body: {
        "keywords": ["keyword1", "keyword2"],
        "marketplace": "US",
    }
    """
    data = request.get_json()
    if not data or "keywords" not in data:
        return jsonify({"error": "缺少 keywords"}), 400

    keywords = data["keywords"][:5]
    marketplace = data.get("marketplace", "US")

    try:
        from scrapers.google_trends import GoogleTrendsCrawler

        crawler = GoogleTrendsCrawler(marketplace=marketplace)

        if len(keywords) == 1:
            result = crawler.get_comprehensive_trend(keywords[0])
        else:
            result = crawler.get_interest_over_time(keywords)

        return jsonify({"success": True, "data": result})

    except Exception as e:
        logger.error(f"Google Trends 查询失败: {e}")
        return jsonify({"error": str(e)}), 500
