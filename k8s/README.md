# Kubernetes 部署方案

## 架构概览

```
                    ┌─────────────┐
                    │   Ingress   │  (NGINX + TLS)
                    │  (L7 LB)   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Web Service │  (2-10 Pods, HPA)
                    │  Flask App   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │  MySQL  │  │  Redis  │  │ Celery  │
       │ (STS)   │  │  (Deploy)│  │ Workers │
       └─────────┘  └─────────┘  └─────────┘
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `namespace.yaml` | 命名空间定义 |
| `configmap.yaml` | 配置项 + Secret |
| `mysql.yaml` | MySQL StatefulSet + Service |
| `redis.yaml` | Redis Deployment + Service |
| `web.yaml` | Flask Web Deployment + Service + HPA + PVC |
| `celery.yaml` | Celery Workers (scraping/analysis/3d/beat) |
| `ingress.yaml` | Ingress (NGINX + TLS) |

## 快速部署

```bash
# 1. 创建命名空间
kubectl apply -f k8s/namespace.yaml

# 2. 修改 Secret 中的敏感信息
vim k8s/configmap.yaml

# 3. 部署基础设施
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/mysql.yaml
kubectl apply -f k8s/redis.yaml

# 4. 等待数据库就绪
kubectl -n avst wait --for=condition=ready pod -l app=mysql --timeout=120s

# 5. 构建并推送镜像
docker build -t your-registry/avst-web:latest .
docker push your-registry/avst-web:latest

# 6. 部署应用
kubectl apply -f k8s/web.yaml
kubectl apply -f k8s/celery.yaml

# 7. 配置 Ingress
kubectl apply -f k8s/ingress.yaml

# 8. 验证部署
kubectl -n avst get pods
kubectl -n avst get svc
kubectl -n avst get ingress
```

## 扩缩容

```bash
# 手动扩容 Web
kubectl -n avst scale deployment web --replicas=5

# 手动扩容分析 Worker
kubectl -n avst scale deployment celery-analysis --replicas=4

# HPA 自动扩缩 (已配置)
kubectl -n avst get hpa
```

## 监控

```bash
# 查看 Pod 状态
kubectl -n avst get pods -o wide

# 查看日志
kubectl -n avst logs -f deployment/web
kubectl -n avst logs -f deployment/celery-analysis

# 查看资源使用
kubectl -n avst top pods
```

## 注意事项

1. **生产环境必须修改** `configmap.yaml` 中的 Secret 值
2. **镜像地址** 需替换 `your-registry/avst-web:latest` 为实际 Registry
3. **域名** 需替换 `your-domain.com` 为实际域名
4. **存储** 需确保集群有可用的 StorageClass (`standard`)
5. **TLS** 需安装 cert-manager 并配置 ClusterIssuer
6. **MySQL** 生产环境建议使用云托管数据库 (RDS/Cloud SQL)
