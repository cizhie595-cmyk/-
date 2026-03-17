-- ============================================================
-- 示例数据 - 用于测试数据库结构是否正常工作
-- 运行方式: mysql -u root -p coupang_selection < database/seeds/sample_data.sql
-- ============================================================

USE coupang_selection;

-- 插入示例关键词
INSERT INTO keywords (word, top_n, status) VALUES
('무선 이어폰', 50, 'completed'),
('보조배터리', 30, 'pending'),
('블루투스 스피커', 50, 'pending');

-- 插入示例类目
INSERT INTO categories (name, commission_rate, naver_trend_score, coupang_trend_score, monthly_gmv, yearly_gmv, top1_sales_ratio, top3_sales_ratio, top10_sales_ratio, new_3m_ratio, new_1y_ratio) VALUES
('이어폰/헤드폰', 0.0800, 85.50, 92.30, 5000000000, 60000000000, 0.1200, 0.2800, 0.5500, 0.0800, 0.2500),
('보조배터리', 0.0700, 72.30, 78.50, 3000000000, 36000000000, 0.1500, 0.3200, 0.6000, 0.0600, 0.2000);

-- 插入示例产品
INSERT INTO products (coupang_product_id, keyword_id, category_id, ranking, title, url, brand_name, manufacturer, price, rating, review_count, delivery_type) VALUES
('CP-001234567', 1, 1, 1, '삼성 갤럭시 버즈3 프로 무선 이어폰', 'https://www.coupang.com/vp/products/001234567', 'Samsung', '삼성전자', 259000, 4.70, 15230, 'blue_rocket'),
('CP-002345678', 1, 1, 2, '애플 에어팟 프로 2세대', 'https://www.coupang.com/vp/products/002345678', 'Apple', '애플코리아', 329000, 4.80, 28450, 'blue_rocket'),
('CP-003456789', 1, 1, 5, 'QCY T20 무선 블루투스 이어폰', 'https://www.coupang.com/vp/products/003456789', 'QCY', 'QCY', 19900, 4.30, 8920, 'orange_rocket');

-- 插入示例每日数据
INSERT INTO daily_metrics (product_id, record_date, daily_clicks, daily_sales, daily_views, conversion_rate) VALUES
(1, '2026-03-15', 3500, 280, 45000, 0.080000),
(1, '2026-03-16', 3200, 265, 42000, 0.082813),
(2, '2026-03-15', 4200, 350, 52000, 0.083333),
(2, '2026-03-16', 4000, 330, 50000, 0.082500),
(3, '2026-03-15', 1800, 220, 25000, 0.122222),
(3, '2026-03-16', 1650, 198, 23000, 0.120000);

-- 插入示例利润分析
INSERT INTO profit_analysis (product_id, source_1688_url, source_cost_rmb, freight_cost_rmb, commission_rate, delivery_fee_krw, exchange_rate, selling_price_krw, total_cost_krw, estimated_profit, profit_margin, roi) VALUES
(3, 'https://detail.1688.com/offer/example.html', 35.00, 8.00, 0.0800, 3500, 185.0000, 19900, 12455, 7445, 0.374121, 0.5978);
