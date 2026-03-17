# ============================================================
# Coupang/Amazon 跨境电商智能选品系统 - Dockerfile
# 多阶段构建，最终镜像约 300MB
# ============================================================

# --- Stage 1: Python 依赖安装 ---
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# --- Stage 2: 最终运行镜像 ---
FROM python:3.11-slim

LABEL maintainer="AVST Team"
LABEL description="Amazon Visionary Sourcing Tool - 跨境电商智能选品系统"

WORKDIR /app

# 安装运行时系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制 Python 包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY . .

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser appuser \
    && mkdir -p /app/data /app/reports /app/logs \
    && chown -R appuser:appuser /app

USER appuser

# 环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_HOST=0.0.0.0 \
    FLASK_PORT=5000

# 暴露端口
EXPOSE 5000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# 启动命令
CMD ["python", "app.py", "--host", "0.0.0.0", "--port", "5000"]
