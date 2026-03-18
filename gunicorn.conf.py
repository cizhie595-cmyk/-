# ============================================================
# Gunicorn 生产环境配置
# 用法: gunicorn -c gunicorn.conf.py app:create_app()
# ============================================================
import os
import multiprocessing

# --- 绑定 ---
bind = f"{os.getenv('FLASK_HOST', '0.0.0.0')}:{os.getenv('FLASK_PORT', '5000')}"

# --- Worker 进程 ---
# 推荐公式: (2 × CPU核心数) + 1
workers = int(os.getenv("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", 4))

# --- 超时 ---
timeout = int(os.getenv("GUNICORN_TIMEOUT", 120))
graceful_timeout = 30
keepalive = 5

# --- 请求限制 ---
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", 2000))
max_requests_jitter = 200
limit_request_line = 8190
limit_request_fields = 100

# --- 预加载 ---
preload_app = True

# --- 日志 ---
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")  # "-" = stdout
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)sμs'

# --- 进程名 ---
proc_name = "click-stats"

# --- 安全 ---
forwarded_allow_ips = os.getenv("GUNICORN_FORWARDED_ALLOW_IPS", "*")
proxy_protocol = False

# --- 临时文件 ---
tmp_upload_dir = None
worker_tmp_dir = "/dev/shm"


# --- 钩子函数 ---
def on_starting(server):
    """服务启动时"""
    server.log.info("Click-Stats starting with %d workers", server.cfg.workers)


def post_fork(server, worker):
    """Worker 进程 fork 后"""
    server.log.info("Worker spawned (pid: %s)", worker.pid)


def pre_exec(server):
    """Master 进程 exec 前"""
    server.log.info("Forked child, re-executing.")


def when_ready(server):
    """服务就绪"""
    server.log.info("Server is ready. Spawning workers")


def worker_int(worker):
    """Worker 收到 INT 信号"""
    worker.log.info("Worker received INT or QUIT signal")


def worker_abort(worker):
    """Worker 超时被终止"""
    worker.log.info("Worker received SIGABRT signal (timeout)")
