# Coupang 选品系统 - 用户登录注册模块使用指南

## 一、模块概述

本次新增的用户登录注册模块为 Coupang 跨境电商智能选品系统提供了完整的用户认证与权限管理功能。该模块基于 **Flask + JWT + bcrypt** 技术栈构建，支持多用户并行使用系统，每个用户可独立配置自己的 OpenAI API Key、Coupang 卖家账号等信息。

### 核心功能

| 功能 | 说明 |
|------|------|
| 用户注册 | 支持用户名+邮箱+密码注册，密码强度校验 |
| 用户登录 | 支持用户名或邮箱登录，登录日志记录 |
| JWT 鉴权 | Access Token + Refresh Token 双令牌机制 |
| 个人信息管理 | 修改昵称、手机号、语言偏好等 |
| 密钥配置 | 每个用户可配置自己的 OpenAI Key、Coupang 账号、Naver API |
| 修改密码 | 验证原密码后修改新密码 |
| 管理员功能 | 用户列表、启用/禁用用户、角色管理 |
| 安全审计 | 登录日志记录（IP、UA、成功/失败） |

### 角色权限

| 角色 | 权限说明 |
|------|----------|
| `admin` | 管理员，可管理所有用户、查看用户列表、修改角色 |
| `user` | 普通用户，可使用所有选品功能 |
| `viewer` | 只读用户，只能查看报告，不能发起选品任务 |

---

## 二、新增文件清单

```
coupang-repo/
├── auth/                          # 用户认证模块（新增）
│   ├── __init__.py                # 模块初始化
│   ├── password.py                # 密码加密、验证、强度校验
│   ├── jwt_handler.py             # JWT Token 生成、验证、刷新
│   ├── user_model.py              # 用户数据模型（CRUD 操作）
│   └── middleware.py              # 认证中间件（装饰器）
├── api/                           # API 路由模块（新增）
│   ├── __init__.py                # 模块初始化
│   └── auth_routes.py             # 用户认证 API 路由
├── database/
│   └── user_schema.sql            # 用户相关建表脚本（新增）
├── app.py                         # Flask Web API 服务器（新增）
├── test_auth.py                   # 认证模块单元测试（新增）
├── .env.example                   # 环境变量示例（已更新）
└── requirements.txt               # 依赖清单（已更新）
```

---

## 三、安装部署

### 3.1 安装新增依赖

```bash
pip install -r requirements.txt
```

或单独安装新增的依赖：

```bash
pip install flask flask-cors bcrypt PyJWT python-dotenv
```

### 3.2 创建数据库表

在 MySQL 中执行用户模块的建表脚本：

```bash
mysql -u root -p coupang_selection < database/user_schema.sql
```

该脚本会创建以下三张表：

| 表名 | 说明 |
|------|------|
| `users` | 用户主表，存储账号、密码哈希、角色、API配置等 |
| `user_login_logs` | 登录日志表，记录每次登录的IP、UA、状态 |
| `user_tasks` | 用户任务关联表，将选品任务与用户绑定 |

### 3.3 配置环境变量

复制 `.env.example` 为 `.env`，并修改以下新增配置项：

```bash
cp .env.example .env
```

```env
# JWT 认证配置（重要：生产环境务必修改为随机字符串）
JWT_SECRET_KEY=your-random-secret-key-change-this-in-production
JWT_ACCESS_TOKEN_EXPIRE_HOURS=24
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Flask 配置
FLASK_SECRET_KEY=your-flask-secret-key
FLASK_HOST=127.0.0.1
FLASK_PORT=5000
```

> **安全提醒**：`JWT_SECRET_KEY` 是签发 Token 的密钥，生产环境中必须使用足够长的随机字符串。可以使用以下命令生成：
> ```bash
> python3 -c "import secrets; print(secrets.token_hex(32))"
> ```

### 3.4 启动 API 服务器

```bash
# 开发模式
python app.py --debug

# 指定端口
python app.py --port 8080

# 允许外部访问
python app.py --host 0.0.0.0 --port 5000
```

启动后访问 `http://localhost:5000` 可看到系统信息。

---

## 四、API 接口文档

所有接口均返回 JSON 格式，统一响应结构：

```json
{
    "success": true/false,
    "message": "操作结果描述",
    "data": { ... }
}
```

### 4.1 用户注册

**POST** `/api/auth/register`

请求体：

```json
{
    "username": "myuser",
    "email": "user@example.com",
    "password": "MyPass123",
    "nickname": "我的昵称",
    "language": "zh_CN"
}
```

密码要求：
- 长度至少 8 位
- 包含大写字母
- 包含小写字母
- 包含数字

成功响应 (201)：

```json
{
    "success": true,
    "message": "注册成功",
    "data": {
        "user_id": 1,
        "username": "myuser",
        "email": "user@example.com",
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "Bearer"
    }
}
```

### 4.2 用户登录

**POST** `/api/auth/login`

请求体：

```json
{
    "login_id": "myuser",
    "password": "MyPass123"
}
```

> `login_id` 支持用户名或邮箱登录。

成功响应 (200)：

```json
{
    "success": true,
    "message": "登录成功",
    "data": {
        "user_id": 1,
        "username": "myuser",
        "email": "user@example.com",
        "nickname": "我的昵称",
        "role": "user",
        "language": "zh_CN",
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "Bearer"
    }
}
```

### 4.3 刷新 Token

**POST** `/api/auth/refresh`

当 Access Token 过期时，使用 Refresh Token 获取新的 Access Token：

```json
{
    "refresh_token": "eyJ..."
}
```

### 4.4 获取当前用户信息

**GET** `/api/auth/me`

请求头：

```
Authorization: Bearer <access_token>
```

### 4.5 更新用户信息

**PUT** `/api/auth/me`

请求头：

```
Authorization: Bearer <access_token>
```

请求体（所有字段均为可选）：

```json
{
    "nickname": "新昵称",
    "phone": "13800138000",
    "language": "en_US",
    "openai_api_key": "sk-...",
    "openai_model": "gpt-4o",
    "coupang_seller_email": "seller@coupang.com",
    "coupang_seller_password": "...",
    "naver_client_id": "...",
    "naver_client_secret": "..."
}
```

### 4.6 修改密码

**POST** `/api/auth/change-password`

请求头：

```
Authorization: Bearer <access_token>
```

请求体：

```json
{
    "old_password": "OldPass123",
    "new_password": "NewPass456"
}
```

### 4.7 管理员接口

以下接口需要 `admin` 角色的 Token：

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/auth/users` | GET | 获取用户列表（支持分页 `?page=1&page_size=20`） |
| `/api/auth/users/<id>/status` | PUT | 启用/禁用用户 `{"is_active": true/false}` |
| `/api/auth/users/<id>/role` | PUT | 设置角色 `{"role": "admin/user/viewer"}` |

---

## 五、在前端中使用

### 5.1 登录流程

```
1. 用户输入用户名+密码 → 调用 POST /api/auth/login
2. 获取 access_token 和 refresh_token
3. 将 access_token 存入 localStorage 或内存
4. 将 refresh_token 存入 httpOnly cookie（更安全）
5. 后续所有请求在 Header 中携带: Authorization: Bearer <access_token>
```

### 5.2 Token 刷新流程

```
1. 请求返回 401 状态码
2. 使用 refresh_token 调用 POST /api/auth/refresh
3. 获取新的 access_token
4. 用新 Token 重试原请求
5. 如果 refresh_token 也过期，跳转到登录页
```

### 5.3 前端示例代码（JavaScript）

```javascript
// 注册
const register = async (username, email, password) => {
    const resp = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
    });
    const data = await resp.json();
    if (data.success) {
        localStorage.setItem('access_token', data.data.access_token);
        localStorage.setItem('refresh_token', data.data.refresh_token);
    }
    return data;
};

// 登录
const login = async (loginId, password) => {
    const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ login_id: loginId, password }),
    });
    const data = await resp.json();
    if (data.success) {
        localStorage.setItem('access_token', data.data.access_token);
        localStorage.setItem('refresh_token', data.data.refresh_token);
    }
    return data;
};

// 带认证的请求
const authFetch = async (url, options = {}) => {
    const token = localStorage.getItem('access_token');
    const resp = await fetch(url, {
        ...options,
        headers: {
            ...options.headers,
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
        },
    });

    // Token 过期，尝试刷新
    if (resp.status === 401) {
        const refreshToken = localStorage.getItem('refresh_token');
        const refreshResp = await fetch('/api/auth/refresh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken }),
        });
        const refreshData = await refreshResp.json();
        if (refreshData.success) {
            localStorage.setItem('access_token', refreshData.data.access_token);
            // 用新 Token 重试
            return authFetch(url, options);
        } else {
            // Refresh Token 也过期，需要重新登录
            window.location.href = '/login';
        }
    }

    return resp;
};
```

---

## 六、在现有模块中使用认证

### 6.1 保护现有路由

在任何需要登录才能访问的路由上添加 `@login_required` 装饰器：

```python
from auth.middleware import login_required, admin_required, role_required
from flask import g

@app.route("/api/pipeline/start", methods=["POST"])
@login_required
def start_pipeline():
    user_id = g.current_user["user_id"]
    username = g.current_user["username"]
    # ... 执行选品流程
```

### 6.2 获取用户的 API Key

```python
from auth.user_model import UserModel

@app.route("/api/analysis/run", methods=["POST"])
@login_required
def run_analysis():
    user_id = g.current_user["user_id"]
    user = UserModel.get_by_id(user_id)

    # 获取用户配置的 OpenAI API Key
    api_key = user.get("openai_api_key") or os.getenv("OPENAI_API_KEY")
    model = user.get("openai_model") or "gpt-4"

    # 使用用户的 Key 调用 AI 分析
    # ...
```

### 6.3 角色权限控制

```python
# 只有管理员可以访问
@app.route("/api/admin/settings")
@admin_required
def admin_settings():
    pass

# 管理员和普通用户可以访问，只读用户不行
@app.route("/api/pipeline/start")
@role_required("admin", "user")
def start_pipeline():
    pass
```

---

## 七、创建初始管理员账号

首次部署后，可以通过以下方式创建管理员账号：

### 方式一：通过 Python 脚本

```python
# create_admin.py
from auth.user_model import UserModel

user_id = UserModel.create(
    username="admin",
    email="admin@example.com",
    password="Admin123456",
    nickname="系统管理员",
    role="admin",
)
print(f"管理员账号创建成功，ID: {user_id}")
```

### 方式二：通过 SQL 直接修改角色

先通过 API 正常注册，然后在数据库中修改角色：

```sql
UPDATE users SET role = 'admin' WHERE username = 'your_username';
```

---

## 八、安全建议

1. **JWT_SECRET_KEY**：生产环境必须使用随机生成的强密钥，不要使用默认值
2. **HTTPS**：生产环境务必使用 HTTPS，防止 Token 在传输中被截获
3. **Token 存储**：前端建议将 Refresh Token 存入 httpOnly Cookie，Access Token 存入内存
4. **密码策略**：当前要求至少 8 位，含大小写字母和数字，可根据需要在 `password.py` 中调整
5. **登录限流**：建议在生产环境中添加登录频率限制（如 Flask-Limiter），防止暴力破解
6. **敏感信息加密**：用户配置的 `openai_api_key` 等敏感信息建议使用 AES 加密后存储

---

## 九、测试

运行单元测试（不依赖数据库）：

```bash
python test_auth.py
```

测试内容包括：
- 密码加密与验证
- 密码强度校验
- 邮箱/用户名格式验证
- JWT Token 生成与验证
- Token 刷新机制
- Flask API 路由注册与参数校验
- 认证中间件拦截

---

## 十、后续扩展建议

| 功能 | 说明 |
|------|------|
| 邮箱验证 | 注册后发送验证邮件，验证后 `is_verified` 设为 1 |
| 忘记密码 | 通过邮箱发送重置密码链接 |
| OAuth 登录 | 支持 Google、GitHub 等第三方登录 |
| 登录限流 | 使用 Flask-Limiter 限制登录频率 |
| 操作日志 | 记录用户的关键操作（发起选品、导出报告等） |
| API Key 加密 | 使用 AES 对存储的第三方 API Key 进行加密 |
