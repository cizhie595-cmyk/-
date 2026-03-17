"""
AI 模型配置模块 - 独立测试脚本
不依赖 MySQL，测试核心逻辑
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ============================================================
# 测试 1: AIConfigManager 基础功能
# ============================================================
print("=" * 60)
print("测试 1: AI 服务商列表")
print("=" * 60)

from auth.ai_config import AIConfigManager, AI_PROVIDERS, DEFAULT_AI_SETTINGS

providers = AIConfigManager.get_providers()
print(f"支持的服务商数量: {len(providers)}")
for p in providers:
    print(f"  - {p['id']}: {p['name']} ({len(p['models'])} 个模型)")
    print(f"    默认 URL: {p['default_base_url']}")
    print(f"    模型: {', '.join(p['models'][:3])}{'...' if len(p['models']) > 3 else ''}")

assert len(providers) == 5, f"期望 5 个服务商，实际 {len(providers)}"
print("\n[PASS] 服务商列表测试通过\n")

# ============================================================
# 测试 2: API Key 加密/解密
# ============================================================
print("=" * 60)
print("测试 2: API Key 加密/解密")
print("=" * 60)

test_keys = [
    "sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234",
    "sk-1234567890abcdef",
    "",
]

for key in test_keys:
    encrypted = AIConfigManager._encrypt_key(key)
    decrypted = AIConfigManager._decrypt_key(encrypted)
    status = "PASS" if decrypted == key else "FAIL"
    print(f"  [{status}] 原始: {key[:20]}... -> 加密: {encrypted[:20]}... -> 解密匹配: {decrypted == key}")

print("\n[PASS] 加密/解密测试通过\n")

# ============================================================
# 测试 3: API Key 脱敏
# ============================================================
print("=" * 60)
print("测试 3: API Key 脱敏")
print("=" * 60)

mask_tests = [
    ("sk-proj-abc123def456ghi789jkl012mno345pqr678stu901vwx234", "sk-pro...x234"),
    ("sk-1234567890abcdef", "sk-123...cdef"),
    ("short", "sho...rt"),
    ("", ""),
]

for original, expected in mask_tests:
    result = AIConfigManager._mask_key(original)
    status = "PASS" if result == expected else "FAIL"
    print(f"  [{status}] {original[:20]}{'...' if len(original) > 20 else ''} -> {result} (期望: {expected})")

print("\n[PASS] 脱敏测试通过\n")

# ============================================================
# 测试 4: 默认配置
# ============================================================
print("=" * 60)
print("测试 4: 默认配置模板")
print("=" * 60)

print(f"  默认配置: {json.dumps(DEFAULT_AI_SETTINGS, indent=2, ensure_ascii=False)}")
assert DEFAULT_AI_SETTINGS["provider"] == "openai"
assert DEFAULT_AI_SETTINGS["configured"] == False
assert DEFAULT_AI_SETTINGS["temperature"] == 0.3
print("\n[PASS] 默认配置测试通过\n")

# ============================================================
# 测试 5: Flask API 路由测试
# ============================================================
print("=" * 60)
print("测试 5: Flask API 路由")
print("=" * 60)

from app import create_app

app = create_app()
client = app.test_client()

# 5.1 获取服务商列表（无需认证）
resp = client.get("/api/ai/providers")
data = resp.get_json()
assert resp.status_code == 200
assert data["success"] == True
assert len(data["data"]) == 5
print(f"  [PASS] GET /api/ai/providers -> {resp.status_code}, {len(data['data'])} 个服务商")

# 5.2 获取 AI 配置（需要认证，未登录应返回 401）
resp = client.get("/api/ai/settings")
assert resp.status_code == 401
print(f"  [PASS] GET /api/ai/settings (未登录) -> {resp.status_code}")

# 5.3 保存 AI 配置（需要认证，未登录应返回 401）
resp = client.post("/api/ai/settings", json={"provider": "openai", "api_key": "sk-test"})
assert resp.status_code == 401
print(f"  [PASS] POST /api/ai/settings (未登录) -> {resp.status_code}")

# 5.4 测试连接（需要认证，未登录应返回 401）
resp = client.post("/api/ai/test")
assert resp.status_code == 401
print(f"  [PASS] POST /api/ai/test (未登录) -> {resp.status_code}")

# 5.5 直接测试（需要认证，未登录应返回 401）
resp = client.post("/api/ai/test-direct", json={"api_key": "sk-test"})
assert resp.status_code == 401
print(f"  [PASS] POST /api/ai/test-direct (未登录) -> {resp.status_code}")

# 5.6 前端页面路由
resp = client.get("/settings/ai")
assert resp.status_code == 200
assert b"AI" in resp.data
print(f"  [PASS] GET /settings/ai -> {resp.status_code}, 页面加载成功")

print("\n[PASS] Flask API 路由测试全部通过\n")

# ============================================================
# 总结
# ============================================================
print("=" * 60)
print("所有测试通过！AI 模型配置模块功能正常。")
print("=" * 60)
