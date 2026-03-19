# Step 1-10 审查发现

## 问题清单

### Bug 1: Step 5 - amazon_pipeline 评论数据结构不匹配
- **文件**: amazon_pipeline.py L354-386
- **问题**: `crawl_reviews()` 返回 `dict`（包含 `reviews`, `statistics` 等），但 pipeline 将整个 dict 传给 `_detect_fake_reviews(reviews)` 和 `analyzer.analyze(reviews, title)`，两者都期望 `list[dict]`
- **修复**: 从返回结果中提取 `result["reviews"]` 列表

### Bug 2: Step 7 - AmazonCategoryAnalyzer 构造函数签名不匹配
- **文件**: amazon_pipeline.py L417-419 vs amazon_category_analyzer.py L31
- **问题**: Pipeline 传入 `http_client=` 和 `ai_client=`，但 AmazonCategoryAnalyzer.__init__ 只接受 `ai_client=` 和 `ai_model=`，不接受 `http_client`
- **修复**: 修正构造函数调用

### Bug 3: Step 7 - analyze_category 参数顺序错误
- **文件**: amazon_pipeline.py L423-425
- **问题**: Pipeline 调用 `analyze_category(keyword, self.products, self.keepa_data)`，但方法签名是 `analyze_category(products, keyword, trends_data=None)`，参数顺序反了
- **修复**: 修正参数顺序

### Bug 4: Step 7 - AmazonCategoryAnalyzer 没有 close() 方法
- **文件**: amazon_pipeline.py L430-433
- **问题**: Pipeline 调用 `analyzer.close()` 但类没有定义该方法
- **修复**: 添加 close() 方法或移除调用

### Bug 5: Step 10 - ReportGenerator 完全是 Coupang 格式
- **文件**: report_generator.py
- **问题**: 
  - 标题硬编码 "Coupang"
  - 市场概况期望 `gmv_estimate.monthly_gmv_krw`、`monopoly_analysis`、`new_product_analysis`、`price_distribution`（Coupang 格式），但 AmazonCategoryAnalyzer 输出 `market_size`、`competition`、`pricing`、`brand_concentration` 等（Amazon 格式）
  - 利润表格期望 `source.supplier_name`、`selling_price_krw`、`profit_per_unit_krw`（Coupang/KRW），但 AmazonFBAProfitCalculator 输出嵌套结构 `costs.cogs_rmb`、`profit.profit_per_unit_usd`（Amazon/USD）
  - 竞品表格使用 `delivery_type`（Coupang），Amazon 应该用 `fulfillment_type`
  - 机会与风险期望 `ai_assessment`，但 Amazon 分析器输出 `opportunity`
- **修复**: 创建 AmazonReportGenerator 或让 ReportGenerator 支持双平台

### Bug 6: Step 8 - 1688 以图搜货的图片路径不可用
- **文件**: amazon_pipeline.py L443-458
- **问题**: 查找 `images[*].local_path` where `type=='main'`，但 Amazon 爬虫不会产生这种格式的 images 数组，main_image 是一个 URL 字符串
- **修复**: 支持从 main_image URL 下载图片后搜索，或直接用关键词搜索
