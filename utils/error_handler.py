"""
Coupang 选品系统 - 统一错误处理与全局异常中间件
提供: 自定义异常类、全局异常捕获、统一错误响应格式
"""

import traceback
from flask import Flask, jsonify, request
from utils.logger import get_logger

logger = get_logger()


# ============================================================
# 自定义异常类
# ============================================================

class AppException(Exception):
    """应用基础异常"""
    status_code = 500
    error_code = "internal_error"
    message = "服务器内部错误"

    def __init__(self, message=None, status_code=None, error_code=None, details=None):
        super().__init__(message or self.message)
        if message:
            self.message = message
        if status_code:
            self.status_code = status_code
        if error_code:
            self.error_code = error_code
        self.details = details or {}

    def to_dict(self):
        rv = {
            "success": False,
            "error": self.error_code,
            "message": self.message,
        }
        if self.details:
            rv["details"] = self.details
        return rv


class BadRequestError(AppException):
    """400 - 请求参数错误"""
    status_code = 400
    error_code = "bad_request"
    message = "请求参数错误"


class UnauthorizedError(AppException):
    """401 - 未认证"""
    status_code = 401
    error_code = "unauthorized"
    message = "请先登录"


class ForbiddenError(AppException):
    """403 - 无权限"""
    status_code = 403
    error_code = "forbidden"
    message = "没有权限执行此操作"


class NotFoundError(AppException):
    """404 - 资源不存在"""
    status_code = 404
    error_code = "not_found"
    message = "请求的资源不存在"


class ConflictError(AppException):
    """409 - 资源冲突"""
    status_code = 409
    error_code = "conflict"
    message = "资源冲突"


class QuotaExceededError(AppException):
    """429 - 额度超限"""
    status_code = 429
    error_code = "quota_exceeded"
    message = "操作额度已耗尽，请升级订阅"


class ExternalServiceError(AppException):
    """502 - 外部服务错误"""
    status_code = 502
    error_code = "external_service_error"
    message = "外部服务调用失败"


class ServiceUnavailableError(AppException):
    """503 - 服务不可用"""
    status_code = 503
    error_code = "service_unavailable"
    message = "服务暂时不可用，请稍后重试"


# ============================================================
# 全局异常处理注册
# ============================================================

def register_error_handlers(app: Flask):
    """
    注册全局异常处理器

    :param app: Flask 应用实例
    """

    @app.errorhandler(AppException)
    def handle_app_exception(error):
        """处理自定义应用异常"""
        response = jsonify(error.to_dict())
        response.status_code = error.status_code
        # 5xx 级别错误记录详细日志
        if error.status_code >= 500:
            logger.error(f"[AppException] {error.error_code}: {error.message} "
                         f"| path={request.path} | details={error.details}")
        else:
            logger.warning(f"[AppException] {error.error_code}: {error.message} "
                           f"| path={request.path}")
        return response

    @app.errorhandler(400)
    def handle_400(error):
        return jsonify({
            "success": False,
            "error": "bad_request",
            "message": "请求格式错误",
        }), 400

    @app.errorhandler(401)
    def handle_401(error):
        return jsonify({
            "success": False,
            "error": "unauthorized",
            "message": "未提供有效的认证信息",
        }), 401

    @app.errorhandler(403)
    def handle_403(error):
        return jsonify({
            "success": False,
            "error": "forbidden",
            "message": "没有权限访问此资源",
        }), 403

    @app.errorhandler(404)
    def handle_404(error):
        return jsonify({
            "success": False,
            "error": "not_found",
            "message": "请求的接口不存在",
        }), 404

    @app.errorhandler(405)
    def handle_405(error):
        return jsonify({
            "success": False,
            "error": "method_not_allowed",
            "message": "不支持的请求方法",
        }), 405

    @app.errorhandler(413)
    def handle_413(error):
        return jsonify({
            "success": False,
            "error": "payload_too_large",
            "message": "请求体过大",
        }), 413

    @app.errorhandler(422)
    def handle_422(error):
        return jsonify({
            "success": False,
            "error": "unprocessable_entity",
            "message": "请求参数无法处理",
        }), 422

    @app.errorhandler(429)
    def handle_429(error):
        return jsonify({
            "success": False,
            "error": "rate_limit_exceeded",
            "message": "请求过于频繁，请稍后再试",
        }), 429

    @app.errorhandler(500)
    def handle_500(error):
        # 记录完整堆栈
        logger.error(f"[500] 服务器内部错误: {error}\n"
                     f"Path: {request.path}\n"
                     f"Method: {request.method}\n"
                     f"Traceback:\n{traceback.format_exc()}")
        return jsonify({
            "success": False,
            "error": "internal_error",
            "message": "服务器内部错误，请稍后重试",
        }), 500

    @app.errorhandler(502)
    def handle_502(error):
        return jsonify({
            "success": False,
            "error": "bad_gateway",
            "message": "网关错误",
        }), 502

    @app.errorhandler(503)
    def handle_503(error):
        return jsonify({
            "success": False,
            "error": "service_unavailable",
            "message": "服务暂时不可用",
        }), 503

    # 捕获所有未处理的异常
    @app.errorhandler(Exception)
    def handle_unhandled_exception(error):
        logger.critical(
            f"[UNHANDLED] 未捕获异常: {type(error).__name__}: {error}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"Headers: {dict(request.headers)}\n"
            f"Traceback:\n{traceback.format_exc()}"
        )
        return jsonify({
            "success": False,
            "error": "internal_error",
            "message": "服务器遇到未知错误，请联系管理员",
        }), 500

    logger.info("[ErrorHandler] 全局异常处理器注册完成")
