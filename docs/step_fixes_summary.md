# Step 1-10 集成修复总结

## 修复概览

本次开发按照 Pipeline Step 1-10 的顺序，对整个选品流程中发现的集成 bug 和数据不一致问题进行了系统性修复。共修改 **3 个核心文件**，新增 **1 个测试文件**，总计 **445 行新增代码**，全部 **61 个测试通过**，无回归。

## 修复详情

### Step 9: FBA 利润计算器 (`amazon_profit_calculator.py`)

| 问题 | 修复方案 |
|------|----------|
| `_calc_storage_fee` 计算了 `per_unit` 但返回 `total_storage`，导致存储费计算错误 | 修正为直接返回 `volume_cuft * rate`（单件月度仓储费） |
| API 路由传入 `sourcing_cost_rmb` 但计算器期望 `cogs_rmb` | 添加参数名兼容：`cogs_rmb` / `sourcing_cost_rmb` |
| API 路由传入 `length_cm` 但计算器期望 `length_in` | 添加自动单位转换：cm -> in（除以 2.54） |
| API 路由传入 `shipping_cost_per_kg` 但计算器期望 `shipping_rmb_per_kg` | 添加参数名兼容 |
| API 路由传入 `estimated_cpa` 但计算器期望 `ppc_cost_per_unit` | 添加参数名兼容 |
| 只传入 `weight_kg` 时 `weight_lb` 为 0，导致 FBA 费用计算错误 | 添加 kg <-> lb 自动转换 |

### Step 1/3: 数据持久化字段映射 (`project_routes.py`)

| 问题 | 修复方案 |
|------|----------|
| 爬虫输出 `main_image`，但入库使用 `p.get("main_image_url")`，导致图片丢失 | 添加字段回退链：`main_image_url` -> `main_image` |
| 入库时缺少 `bsr_rank`、`fulfillment_type` 字段 | INSERT 语句新增这两个字段，并从爬虫/SP-API 数据中正确映射 |
| 前端使用 `monthly_sales`/`bsr`/`main_image`/`fulfillment`，但 API 返回 `est_sales_30d`/`bsr_rank`/`main_image_url`/`fulfillment_type` | 在 `_db_get_products` 中添加兼容别名映射 |

### Step 10: 报告生成数据传递 (`analysis_routes.py`)

| 问题 | 修复方案 |
|------|----------|
| `_execute_report_sync` 传入 `products=[]`，报告无产品数据 | 从 `project_products` 表查询项目的未过滤产品 |
| `_execute_report_sync` 传入 `profit_results=[]`，报告无利润数据 | 从 `profit_calculations` 表查询用户的利润计算记录 |
| `_execute_report_sync` 传入 `category_analysis={}`，报告无市场分析 | 基于产品数据自动生成类目分析摘要（GMV、均价、均评分等） |
| 报告标题使用 `project_id` 而非关键词 | 从 `sourcing_projects` 表获取项目关键词 |

## 测试覆盖

新增 `tests/test_step_fixes.py`，包含 10 个专项测试：

- **TestProfitCalculatorFixes** (5 个测试)
  - 原始参数名兼容性
  - API 路由参数名兼容性（cm/sourcing_cost_rmb/estimated_cpa）
  - kg -> lb 自动转换
  - 存储费单件计算正确性
  - 混合参数（部分英寸部分厘米）

- **TestFieldMappingFixes** (3 个测试)
  - 爬虫输出字段名验证
  - SP-API 输出字段名验证
  - 持久化字段映射逻辑

- **TestProductFieldAliases** (1 个测试)
  - 数据库行到前端字段的别名映射

- **TestReportDataCollection** (1 个测试)
  - 从产品数据生成类目分析

## 提交信息

```
commit 215645c
fix: Step 1-10 集成修复 - 参数映射/字段兼容/报告数据
4 files changed, 445 insertions(+), 17 deletions(-)
```
