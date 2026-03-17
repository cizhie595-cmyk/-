-- ============================================================
-- 迁移脚本 001: 增加 AI 模型动态配置字段
-- 将原有的单一 openai_api_key / openai_model 字段
-- 替换为更灵活的 ai_settings JSON 字段
-- 执行时间: 2026-03-18
-- ============================================================

USE coupang_selection;

-- 1. 新增 ai_settings JSON 字段（存储完整的 AI 配置）
ALTER TABLE users
    ADD COLUMN ai_settings JSON DEFAULT NULL
    COMMENT 'AI模型配置(JSON): provider, api_key, base_url, model, temperature 等'
    AFTER openai_model;

-- 2. 将旧字段的数据迁移到新的 JSON 字段中
UPDATE users
SET ai_settings = JSON_OBJECT(
    'provider', 'openai',
    'api_key', COALESCE(openai_api_key, ''),
    'base_url', '',
    'model', COALESCE(openai_model, 'gpt-4'),
    'temperature', 0.3,
    'max_tokens', 4000
)
WHERE openai_api_key IS NOT NULL AND openai_api_key != '';

-- 注意: 旧字段 openai_api_key 和 openai_model 暂时保留，待前端全面切换后可删除
