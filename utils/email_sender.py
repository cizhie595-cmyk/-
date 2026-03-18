"""
Coupang 选品系统 - 邮件发送服务
支持 SMTP 发送验证邮件、密码重置邮件等
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from utils.logger import get_logger

logger = get_logger()

# SMTP 配置
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", "") or SMTP_USER
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")

# 应用配置
APP_NAME = "Amazon Visionary Sourcing Tool"
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:5000")


def send_email(to_email: str, subject: str, html_body: str,
               text_body: Optional[str] = None) -> bool:
    """
    发送邮件
    :param to_email: 收件人邮箱
    :param subject: 邮件主题
    :param html_body: HTML 邮件内容
    :param text_body: 纯文本邮件内容（备选）
    :return: 是否发送成功
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("[Email] SMTP 未配置，跳过邮件发送")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{APP_NAME} <{SMTP_FROM}>"
        msg["To"] = to_email
        msg["Subject"] = subject

        # 添加纯文本版本
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))

        # 添加 HTML 版本
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # 连接 SMTP 服务器
        if SMTP_USE_TLS:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.ehlo()
            server.starttls()
            server.ehlo()
        else:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=30)

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())
        server.quit()

        logger.info(f"[Email] 邮件发送成功: {to_email} - {subject}")
        return True

    except smtplib.SMTPAuthenticationError:
        logger.error("[Email] SMTP 认证失败，请检查用户名和密码")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"[Email] SMTP 错误: {e}")
        return False
    except Exception as e:
        logger.error(f"[Email] 邮件发送失败: {e}")
        return False


# ============================================================
# 邮件模板
# ============================================================

# 多语言邮件模板
EMAIL_TEMPLATES = {
    "zh_CN": {
        "verify_subject": f"{APP_NAME} - 邮箱验证",
        "verify_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#00d4ff;text-align:center;margin-bottom:30px;">📧 邮箱验证</h1>
            <p style="font-size:16px;line-height:1.6;">您好 <strong>{username}</strong>，</p>
            <p style="font-size:16px;line-height:1.6;">感谢注册 {app_name}！请点击下方按钮验证您的邮箱地址：</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{verify_url}" style="display:inline-block;background:#00d4ff;color:#1a1a2e;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">验证邮箱</a>
            </div>
            <p style="font-size:14px;color:#888;">如果按钮无法点击，请复制以下链接到浏览器：</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{verify_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">此链接 24 小时内有效。如果您没有注册账号，请忽略此邮件。</p>
        </div>
        """,
        "reset_subject": f"{APP_NAME} - 密码重置",
        "reset_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#ff6b6b;text-align:center;margin-bottom:30px;">🔑 密码重置</h1>
            <p style="font-size:16px;line-height:1.6;">您好 <strong>{username}</strong>，</p>
            <p style="font-size:16px;line-height:1.6;">我们收到了您的密码重置请求。请点击下方按钮设置新密码：</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{reset_url}" style="display:inline-block;background:#ff6b6b;color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">重置密码</a>
            </div>
            <p style="font-size:14px;color:#888;">如果按钮无法点击，请复制以下链接到浏览器：</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{reset_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">此链接 1 小时内有效，且只能使用一次。如果您没有请求密码重置，请忽略此邮件。</p>
        </div>
        """,
    },
    "en_US": {
        "verify_subject": f"{APP_NAME} - Email Verification",
        "verify_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#00d4ff;text-align:center;margin-bottom:30px;">📧 Email Verification</h1>
            <p style="font-size:16px;line-height:1.6;">Hello <strong>{username}</strong>,</p>
            <p style="font-size:16px;line-height:1.6;">Thank you for registering with {app_name}! Please click the button below to verify your email address:</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{verify_url}" style="display:inline-block;background:#00d4ff;color:#1a1a2e;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">Verify Email</a>
            </div>
            <p style="font-size:14px;color:#888;">If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{verify_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">This link expires in 24 hours. If you didn't create an account, please ignore this email.</p>
        </div>
        """,
        "reset_subject": f"{APP_NAME} - Password Reset",
        "reset_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#ff6b6b;text-align:center;margin-bottom:30px;">🔑 Password Reset</h1>
            <p style="font-size:16px;line-height:1.6;">Hello <strong>{username}</strong>,</p>
            <p style="font-size:16px;line-height:1.6;">We received a request to reset your password. Click the button below to set a new password:</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{reset_url}" style="display:inline-block;background:#ff6b6b;color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">Reset Password</a>
            </div>
            <p style="font-size:14px;color:#888;">If the button doesn't work, copy and paste this link into your browser:</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{reset_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">This link expires in 1 hour and can only be used once. If you didn't request a password reset, please ignore this email.</p>
        </div>
        """,
    },
    "ko_KR": {
        "verify_subject": f"{APP_NAME} - 이메일 인증",
        "verify_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#00d4ff;text-align:center;margin-bottom:30px;">📧 이메일 인증</h1>
            <p style="font-size:16px;line-height:1.6;"><strong>{username}</strong>님, 안녕하세요.</p>
            <p style="font-size:16px;line-height:1.6;">{app_name}에 가입해 주셔서 감사합니다! 아래 버튼을 클릭하여 이메일 주소를 인증해 주세요:</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{verify_url}" style="display:inline-block;background:#00d4ff;color:#1a1a2e;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">이메일 인증</a>
            </div>
            <p style="font-size:14px;color:#888;">버튼이 작동하지 않으면 아래 링크를 브라우저에 복사하여 붙여넣으세요:</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{verify_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">이 링크는 24시간 동안 유효합니다. 계정을 만들지 않으셨다면 이 이메일을 무시하세요.</p>
        </div>
        """,
        "reset_subject": f"{APP_NAME} - 비밀번호 재설정",
        "reset_body": """
        <div style="max-width:600px;margin:0 auto;font-family:'Segoe UI',Arial,sans-serif;background:#1a1a2e;color:#e0e0e0;padding:40px;border-radius:12px;">
            <h1 style="color:#ff6b6b;text-align:center;margin-bottom:30px;">🔑 비밀번호 재설정</h1>
            <p style="font-size:16px;line-height:1.6;"><strong>{username}</strong>님, 안녕하세요.</p>
            <p style="font-size:16px;line-height:1.6;">비밀번호 재설정 요청을 받았습니다. 아래 버튼을 클릭하여 새 비밀번호를 설정하세요:</p>
            <div style="text-align:center;margin:30px 0;">
                <a href="{reset_url}" style="display:inline-block;background:#ff6b6b;color:#fff;padding:14px 40px;border-radius:8px;text-decoration:none;font-weight:bold;font-size:16px;">비밀번호 재설정</a>
            </div>
            <p style="font-size:14px;color:#888;">버튼이 작동하지 않으면 아래 링크를 브라우저에 복사하여 붙여넣으세요:</p>
            <p style="font-size:12px;color:#666;word-break:break-all;">{reset_url}</p>
            <hr style="border:1px solid #333;margin:30px 0;">
            <p style="font-size:12px;color:#666;">이 링크는 1시간 동안 유효하며 한 번만 사용할 수 있습니다. 비밀번호 재설정을 요청하지 않으셨다면 이 이메일을 무시하세요.</p>
        </div>
        """,
    },
}


def send_verification_email(to_email: str, username: str,
                            verify_token: str, language: str = "zh_CN") -> bool:
    """
    发送邮箱验证邮件
    :param to_email: 收件人邮箱
    :param username: 用户名
    :param verify_token: 验证 Token
    :param language: 语言偏好
    :return: 是否发送成功
    """
    templates = EMAIL_TEMPLATES.get(language, EMAIL_TEMPLATES["en_US"])
    verify_url = f"{APP_BASE_URL}/api/auth/verify-email?token={verify_token}"

    subject = templates["verify_subject"]
    html_body = templates["verify_body"].format(
        username=username,
        app_name=APP_NAME,
        verify_url=verify_url,
    )

    return send_email(to_email, subject, html_body)


def send_password_reset_email(to_email: str, username: str,
                              reset_token: str, language: str = "zh_CN") -> bool:
    """
    发送密码重置邮件
    :param to_email: 收件人邮箱
    :param username: 用户名
    :param reset_token: 重置 Token
    :param language: 语言偏好
    :return: 是否发送成功
    """
    templates = EMAIL_TEMPLATES.get(language, EMAIL_TEMPLATES["en_US"])
    reset_url = f"{APP_BASE_URL}/auth/reset-password?token={reset_token}"

    subject = templates["reset_subject"]
    html_body = templates["reset_body"].format(
        username=username,
        app_name=APP_NAME,
        reset_url=reset_url,
    )

    return send_email(to_email, subject, html_body)
