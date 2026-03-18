# ============================================================
# Click-Stats Makefile
# 项目常用命令快捷入口
# ============================================================

.PHONY: help dev test lint format docker-build docker-up docker-down migrate clean celery beat

# 默认目标
help: ## 显示帮助信息
	@echo "Click-Stats - Coupang/Amazon 跨境电商智能选品系统"
	@echo ""
	@echo "用法: make [target]"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ==================== 开发 ====================

dev: ## 启动开发服务器 (Flask debug mode)
	FLASK_ENV=development python app.py

dev-gunicorn: ## 使用 gunicorn 启动 (模拟生产)
	gunicorn -c gunicorn.conf.py "app:create_app()"

run: ## 启动生产服务器
	gunicorn -c gunicorn.conf.py "app:create_app()"

# ==================== 测试 ====================

test: ## 运行所有测试
	python -m pytest tests/ -v --tb=short

test-cov: ## 运行测试并生成覆盖率报告
	python -m pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing

test-unit: ## 只运行单元测试
	python -m pytest tests/ -v -m "not integration" --tb=short

test-integration: ## 只运行集成测试
	python -m pytest tests/ -v -m "integration" --tb=short

test-fast: ## 快速运行测试 (并行)
	python -m pytest tests/ -v --tb=line -q

# ==================== 代码质量 ====================

lint: ## 运行代码检查 (flake8)
	flake8 --max-line-length=120 --exclude=.git,__pycache__,venv,node_modules \
		--ignore=E501,W503,E402 \
		app.py api/ auth/ utils/ scrapers/ analysis/ monetization/ tasks/

format: ## 格式化代码 (black + isort)
	black --line-length=120 app.py api/ auth/ utils/ scrapers/ analysis/ monetization/ tasks/
	isort --profile=black app.py api/ auth/ utils/ scrapers/ analysis/ monetization/ tasks/

type-check: ## 类型检查 (mypy)
	mypy --ignore-missing-imports app.py api/ auth/ utils/

# ==================== 数据库 ====================

migrate: ## 运行数据库迁移
	@echo "运行数据库迁移脚本..."
	@for f in database/migrations/*.sql; do \
		echo "  执行: $$f"; \
		mysql -u$$DB_USER -p$$DB_PASSWORD $$DB_NAME < $$f 2>/dev/null || true; \
	done
	@echo "迁移完成"

db-init: ## 初始化数据库 (创建所有表)
	mysql -u$$DB_USER -p$$DB_PASSWORD $$DB_NAME < database/schema.sql

db-reset: ## 重置数据库 (危险! 删除所有数据)
	@echo "⚠️  即将删除所有数据并重建数据库!"
	@read -p "确认? [y/N] " confirm && [ "$$confirm" = "y" ] || exit 1
	mysql -u$$DB_USER -p$$DB_PASSWORD -e "DROP DATABASE IF EXISTS $$DB_NAME; CREATE DATABASE $$DB_NAME;"
	mysql -u$$DB_USER -p$$DB_PASSWORD $$DB_NAME < database/schema.sql

# ==================== Docker ====================

docker-build: ## 构建 Docker 镜像
	docker build -t click-stats:latest .

docker-up: ## 启动所有 Docker 服务
	docker-compose up -d

docker-down: ## 停止所有 Docker 服务
	docker-compose down

docker-logs: ## 查看 Docker 日志
	docker-compose logs -f --tail=100

docker-restart: ## 重启所有 Docker 服务
	docker-compose restart

docker-clean: ## 清理 Docker 资源 (镜像/容器/卷)
	docker-compose down -v --rmi local
	docker system prune -f

# ==================== Celery ====================

celery: ## 启动 Celery Worker
	celery -A celery_app.celery worker --loglevel=info --concurrency=4

beat: ## 启动 Celery Beat 定时任务调度器
	celery -A celery_app.celery beat --loglevel=info

celery-flower: ## 启动 Celery Flower 监控面板
	celery -A celery_app.celery flower --port=5555

# ==================== K8s ====================

k8s-apply: ## 部署到 Kubernetes
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/configmap.yaml
	kubectl apply -f k8s/mysql.yaml
	kubectl apply -f k8s/redis.yaml
	kubectl apply -f k8s/celery.yaml
	kubectl apply -f k8s/web.yaml
	kubectl apply -f k8s/ingress.yaml
	kubectl apply -f k8s/monitoring.yaml

k8s-delete: ## 从 Kubernetes 删除所有资源
	kubectl delete -f k8s/ --ignore-not-found

k8s-status: ## 查看 Kubernetes 资源状态
	kubectl get all -n click-stats

k8s-logs: ## 查看 Kubernetes Web Pod 日志
	kubectl logs -f -l app=click-stats-web -n click-stats --tail=100

# ==================== 工具 ====================

clean: ## 清理临时文件
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	rm -rf reports/*.tmp data/*.tmp logs/*.log

deps: ## 安装 Python 依赖
	pip install -r requirements.txt

deps-dev: ## 安装开发依赖
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 black isort mypy

env: ## 从 .env.example 创建 .env 文件
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env 文件已创建，请编辑填入实际配置"; \
	else \
		echo "⚠️  .env 文件已存在，跳过"; \
	fi

check: ## 运行完整检查 (lint + test)
	@echo "=== 代码检查 ==="
	$(MAKE) lint
	@echo ""
	@echo "=== 运行测试 ==="
	$(MAKE) test
	@echo ""
	@echo "✅ 所有检查通过"
