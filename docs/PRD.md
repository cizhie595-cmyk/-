# 产品规格说明书 (PRD) - 极细化方案

**产品名称**：Amazon Visionary Sourcing Tool (暂定)

**产品定位**：面向亚马逊卖家的 AI 驱动一站式选品与 3D 展示 SaaS 平台

**终端形态**：Web SaaS 端 (核心工作台) + Chrome 浏览器插件 (数据抓取辅助)

**版本号**：V1.0

**撰写人**：Manus AI

---

## 1. 产品概述与系统架构 (Product Overview & Architecture)

### 1.1 产品愿景

本产品致力于解决亚马逊卖家在选品阶段面临的"数据获取难、分析维度浅、利润核算繁琐"问题，同时创新性地引入 AI 3D 建模技术，帮助卖家在完成选品后，零门槛生成高转化率的 3D 商品展示资产，实现"选品+展示"的闭环。

### 1.2 目标用户画像 (User Personas)

| 角色 | 痛点 | 核心需求 | 在系统中的行为路径 |
|------|------|---------|------------------|
| 新手卖家 (初创) | 资金有限，不懂选品逻辑，缺乏供应链资源。 | 找低竞争、高利润蓝海产品；低成本制作 Listing 素材。 | 依赖基础数据抓取 → 使用免费AI分析 → 尝试免费3D生成。 |
| 资深运营 (精品) | 现有工具数据维度不够，无法深度拆解竞品视觉和营销逻辑。 | 深度挖掘差评痛点；拆解竞品A+逻辑；核算精准利润。 | 导入ASIN清单 → 运行深度视觉与评论分析 → 导出分析报告。 |
| 视觉设计师 (电商) | 制作3D渲染图和视频耗时耗力，外包成本极高。 | 快速将2D产品图转化为可交互的3D模型和展示视频。 | 上传多角度产品图 → 调整3D模型材质/光影 → 导出视频。 |

### 1.3 核心业务流程图 (Core Workflow)

1. **API 配置阶段**：用户在系统后台配置自己的 Amazon SP-API、Keepa API 或 OpenAI 密钥。
2. **数据采集阶段**：用户输入关键词/ASIN，系统调度 API 或唤起 Chrome 插件抓取前端+后端数据。
3. **数据清洗阶段**：通过多条件筛选器与 AI 特征识别，剔除无关干扰项。
4. **深度解剖阶段**：系统下载竞品图片与评论，调用 AI 进行视觉语义拆解与评论情感分析。
5. **3D 资产生成阶段**：选中潜力产品，调用 Meshy AI 引擎将 2D 图片转为 3D 模型，并在 Web 端预览渲染。
6. **决策输出阶段**：结合全链路成本与市场大盘，输出单品利润表与综合风险评估报告。

### 1.4 系统架构设计 (System Architecture)

为规避平台数据抓取风险及降低服务器带宽成本，系统采用用户自备 API 密钥 (BYOK - Bring Your Own Key) 模式。

**前端层 (Frontend)**：

- **Web 端**：React.js 18 + TypeScript + Tailwind CSS。负责数据可视化（ECharts/Chart.js）与 3D 模型交互预览（Three.js + React Three Fiber）。
- **插件端**：Chrome Extension Manifest V3。负责在亚马逊前台页面注入抓取脚本，拦截 F12 网络请求获取隐藏数据。

**后端层 (Backend)**：

- **主服务**：Node.js (NestJS) 提供 RESTful API，处理用户鉴权、任务调度、订阅管理。
- **数据分析服务**：Python (FastAPI + Pandas/NumPy)，负责执行复杂的数据重算、利润公式计算与大盘趋势拟合。

**数据存储层 (Database)**：

- **关系型数据**：PostgreSQL。存储用户信息、订阅状态、API 配置、任务元数据。
- **文档型数据**：MongoDB。存储抓取回来的海量、非结构化 JSON 商品数据及评论数据。
- **对象存储**：AWS S3 或 Aliyun OSS。存储下载的竞品图片、生成的 3D 模型文件（.glb）及渲染视频。

**外部 API 集成层 (External Integrations)**：

- **Amazon SP-API**：调用 Catalog Items API (`GET /catalog/2022-04-01/items`) 获取基础商品属性。
- **Keepa API**：调用 Product Request 获取历史价格、BSR 排名趋势及 Buy Box 状态。
- **Meshy AI API**：调用 `POST /openapi/v1/image-to-3d` 执行 2D 转 3D 任务。
- **LLM API**：调用 OpenAI GPT-4o 或 Anthropic Claude 3.5 执行文本语义分析与总结。

---

## 2. 全局交互与公共规范 (Global UI/UX & Standards)

### 2.1 页面布局 (Layout)

- **左侧导航栏**：包含工作台、选品项目、深度分析、3D 实验室、利润计算器、API 配置中心、订阅管理。
- **顶部状态栏**：全局搜索、当前选定站点（如 Amazon US）、API 状态指示灯（绿/黄/红）、用户头像与消息通知。
- **主体内容区**：采用卡片式设计，数据表格支持固定表头、横向滚动、列宽拖拽、自定义列显隐。

### 2.2 状态指示灯与异常处理 (Status & Error Handling)

**API 状态灯**：

- 绿色：API 连接正常。
- 黄色：API 调用接近限流阈值（Rate Limit Warning）。
- 红色：API 密钥失效或欠费。鼠标悬停提示具体错误码（如 401 Unauthorized 或 402 Payment Required）。

**全局空状态 (Empty State)**：当表格无数据时，展示插画并配文"暂无数据，请尝试调整筛选条件或新建抓取任务"，并提供操作按钮。

**全局加载状态 (Loading State)**：页面级加载使用骨架屏（Skeleton），按钮级加载使用内部 Spinner，防止重复点击。

### 2.3 权限与额度校验 (Permissions & Quotas)

在用户触发任何消耗额度的操作（如发起抓取、生成 3D）前，前端必须拦截并调用 `/api/v1/user/quota` 接口检查剩余额度。若额度不足，弹出 Modal 提示"当前版本额度已耗尽"，并提供"升级登月版"的跳转按钮。

---

## 3. 核心功能模块详细设计 (Detailed Module Specifications)

### 3.1 模块一：数据抓取与初始挖掘 (Data Scraping & Mining)

#### 3.1.1 页面交互与输入 (UI Inputs)

**入口**：点击左侧导航栏"新建选品项目"。

**输入方式 1：关键词检索**

- 字段：Target Marketplace (下拉单选：US/UK/DE/JP 等)、Search Keyword (文本输入框)。
- 参数配置：Scrape Depth (滑块：Top 50, Top 100, Top 200)。

**输入方式 2：上传后台数据表**

- 交互：拖拽上传区域，支持 .csv 或 .xlsx 格式（亚马逊后台 Search Term Report）。
- 字段映射：系统自动读取表头，用户需确认哪一列是 ASIN，哪一列是 Search Term。

#### 3.1.2 抓取逻辑与数据流 (Scraping Logic & Data Flow)

**双重匹配降级逻辑 (针对上传数据表模式)**：

1. **首选匹配**：读取表中的 ASIN，直接调用 Amazon SP-API `GET /catalog/2022-04-01/items/{asin}`。
2. **降级匹配**：若 ASIN 为空或失效，读取 Search Term 调用 `GET /catalog/2022-04-01/items?keywords={SearchTerm}`。
3. **多结果处理**：若关键词搜索返回多个结果，系统自动取 SalesRank (BSR) 最高的第一个产品作为匹配对象。

**核心字段提取映射表**：

| 目标字段 | API 来源 |
|---------|---------|
| ASIN | SP-API `asin` |
| 主图 | SP-API `images[0].link` |
| 标题 | SP-API `summaries[0].itemName` |
| 品牌 | SP-API `summaries[0].brand` |
| 当前售价 | Keepa API `data.csv[1]` (Amazon Price) 或 `data.csv[18]` (Buy Box) |
| 星级 / 评论数 | Keepa API `data.csv[16]` (Rating) / `data.csv[17]` (Review Count) |

**隐藏数据挖掘 (依赖 Chrome 插件)**：

- **触发条件**：当用户在 Web 端点击"获取深度流量数据"时，系统通过 WebSocket 向已安装的 Chrome 插件发送指令。
- **插件行为**：插件在后台隐式打开对应 ASIN 的亚马逊前台页面，监听并拦截 F12 Network 面板中的 GraphQL/XHR 请求，解析出亚马逊未公开的 Estimated Sales 和 Impressions 参考值。
- **异常处理**：若插件未安装或掉线，Web 端弹出 Toast 提示"请安装/唤醒辅助插件以获取隐藏数据"，并降级使用第三方 API 的估算数据。

### 3.2 模块二：数据清洗与精准筛选 (Data Filtering & Refinement)

#### 3.2.1 页面交互 (UI Interactions)

**数据表格面板 (Data Grid)**：展示抓取回来的原始数据列表。

**快捷过滤器 (Quick Filters)**：

- 价格区间 (Min-Max Input)
- 评论数区间 (Min-Max Input)
- 星级过滤 (Checkbox: 4 星以上, 3-4 星等)
- 剔除特定品牌 (Tag Input，支持输入多个品牌名并按回车生成 Tag)

**AI 智能特征过滤 (AI Smart Filter)**：

- **输入**：提供一个 Textarea，提示语为"描述您想要保留的产品特征，例如：带手柄的保温杯，排除杯盖等配件"。
- **执行**：点击"AI 过滤"按钮，系统将当前表格中所有产品的 Title 和 Bullet Points 打包发送给 LLM。
- **Prompt 设计**：`"You are an Amazon product filter. Here is a list of products: [JSON list]. The user only wants products matching: '{User_Input}'. Return a JSON array containing only the ASINs that strictly match the criteria. Exclude any accessories or irrelevant items."`

#### 3.2.2 核心指标重算公式 (Recalculation Formulas)

为消除上架时间不同带来的数据偏差，所有流量与销量数据强制归一化至 **30 天** 周期：

- **30 天预估销量 (Sales_30D)**：若原始数据为近 7 天销量，则 `Sales_30D = Sales_7D / 7 * 30`；若直接从 Keepa/第三方获取月销量，则直接使用。
- **30 天预估点击量 (Clicks_30D)**：基于后台 Search Term Report 中的点击占比反推，或通过第三方流量 API 估算。
- **真实转化率 (CVR_30D)**：`CVR_30D = (Sales_30D / Clicks_30D) * 100%`。保留两位小数。

### 3.3 模块三：深度数据爬取与视觉语义分析 (Deep Crawling & Visual Semantics)

本模块是系统的核心数据分析引擎，包含多个子流程。

#### 3.3.1 基础信息补全 (Data Enrichment)

**发货方式识别 (fulfillment_type)**：

- 解析前台页面的 "Ships from" 字段。
- 规则：若 "Ships from" 为 Amazon，则判定为 FBA；若 "Ships from" 与 "Sold by" 同为卖家名称，判定为 FBM；若带有 Prime 标志且为卖家发货，判定为 SFP。

**素材批量下载**：

- 调用无头浏览器 (Puppeteer/Playwright) 抓取主图、变体图及 A+ 页面长图。
- 后端使用 archiver 库将图片打包为 ZIP 文件，提供下载链接。

#### 3.3.2 AI 视觉与文案深度解剖 (Visual & Copy Teardown)

**交互流程**：

1. 系统根据类目（如 Electronics）自动推荐 3 个分析维度（如：Battery Life, Material, Screen Size）。
2. 用户可在界面上点击 "x" 删除维度，或点击 "+ Add Dimension" 自定义输入维度。
3. 点击 "Start Deep Teardown" 按钮触发分析。

**执行逻辑与 Prompt 设计**：

系统调用具备视觉能力的 LLM (如 GPT-4o-Vision)。将下载的主图和 A+ 图片作为 Image Content 输入。

- **逻辑结构 (Logic Flow) Prompt**：`"Analyze these A+ page images. Identify the marketing structure (e.g., Pain point introduction -> Feature breakdown -> Comparison -> Trust signals). What psychological model (like AIDA) is driving the conversion?"`
- **文本语义 (OCR & Copy) Prompt**：`"Extract all text from these images. Identify the top 3 high-frequency keywords. Analyze the tone (Emotional vs. Technical). List the core Unique Selling Propositions (USPs)."`
- **信任锚点 (Trust Signals) Prompt**：`"Identify any certification logos (e.g., FDA, CE, UL), lab test reports, celebrity endorsements, or real-life usage scenarios in these images."`
- **视觉语义 (Visual Semantics) Prompt**：`"Analyze the color psychology used. Evaluate the font hierarchy and model localization. Is this brand positioning itself as 'Cost-effective' or 'Premium Professional'?"`

**输出展示**：将 LLM 返回的 JSON 结构化数据渲染为 Web 端的雷达图、标签云和结构化文本卡片。

#### 3.3.3 评论深度挖掘 (Review Mining)

**数据源**：调用第三方爬虫 API 获取该 ASIN 下的 Top 500 最新/最有用评论。

**刷单过滤 (Fake Review Filter)**：

- 规则引擎：剔除 "留评账号历史评价 100%为 5 星"、"留评内容仅有 Very good/Nice 无实质内容"、"留评时间密集扎堆" 的异常评论。

**变体销量反推 (Variant Sales Estimation)**：

- 解析每条评论附带的 Color / Size 属性。
- 计算公式：`变体 A 销量占比 = ( 变体 A 的评论数 / 总有效评论数 ) * 100%`。
- 图表展示：渲染为环形饼图 (Donut Chart)。

**生命周期推算**：

- 提取该 ASIN 下的最早一条评论的 Date，减去 14 天（预估早期测款期），作为该产品的 `Estimated_Launch_Date`。

**AI 痛点与卖点提炼**：

- 将 1-3 星评论打包给 LLM 提炼 "核心痛点 (Pain Points)"。
- 将 4-5 星评论打包给 LLM 提炼 "核心卖点 (Selling Points)" 和 "人群画像 (User Personas)"。

### 3.4 模块四：大盘与类目分析 (Market & Category Analysis)

#### 3.4.1 行业趋势追踪 (Trend Tracking)

- **数据源**：Google Trends API (pytrends 库) + Amazon Search Volume 历史数据。
- **展示**：折线图 (Line Chart)，X 轴为过去 12 个月，Y 轴为搜索热度指数 (0-100)。

#### 3.4.2 体量与 GMV 预估 (Market Size Estimation)

- **月度 GMV**：`Total_Monthly_GMV = SUM(Top_100_ASINs_Sales_30D * Current_Price)`。
- **年度 GMV 预估**：系统提取历史趋势折线图中的 12 个月数据，计算月度权重系数。`Yearly_GMV = 月度 GMV * (12 个月总权重 / 当前月权重)`。

#### 3.4.3 垄断程度评估 (Monopoly Analysis)

**CR 指标计算**：

- `CR3 (Top 3 集中度) = SUM(Top_3_Sales) / Total_Top_100_Sales * 100%`。
- `CR10 (Top 10 集中度) = SUM(Top_10_Sales) / Total_Top_100_Sales * 100%`。

**状态判定与提示**：

- 若 CR3 > 50%，界面标红提示："寡头垄断严重，新卖家不建议进入"。
- 若 CR10 < 30%，界面标绿提示："长尾市场，竞争分散，适合切入"。

#### 3.4.4 新品存活率分析 (New Product Survival Rate)

- **定义**："新品" 指 `Estimated_Launch_Date` 在近 3 个月或近 1 年内的 ASIN。
- **指标展示**：近 3 个月上架新品数量占比 (Pie Chart)。近 3 个月上架新品贡献的销量占比 (Bar Chart)。若销量占比 < 5%，提示"新品突围极度困难"。

### 3.5 模块五：利润核算与供应链匹配 (Profit Analysis & Supply Chain)

#### 3.5.1 1688 以图搜货 (Image-based Sourcing)

- **触发**：在单品详情页点击 "Find Suppliers"。
- **逻辑**：提取该 ASIN 主图，调用 1688 开放平台的以图搜图 API (`alibaba.cross.image.search`)。
- **返回字段**：供应商名称、商品链接、起批量 (MOQ)、阶梯采购价 (RMB)、预估国内运费。系统根据实时汇率将 RMB 转换为 USD。

#### 3.5.2 全链路成本计算器 (FBA Profit Calculator)

**UI 设计**：提供一个类似 Excel 的动态表单，左侧为固定参数（自动抓取），右侧为可调参数（用户输入）。

**固定参数 (只读)**：

| 参数 | 说明 |
|------|------|
| Selling_Price | 当前售价 |
| Item_Weight & Item_Dimensions | 从 SP-API 抓取，用于计算体积重 |
| Referral_Fee_Pct | 亚马逊销售佣金比例，系统内置各级类目费率表，通常为 15% |
| FBA_Fulfillment_Fee | FBA 配送费，系统内置 2026 年最新阶梯费率表，根据重量/尺寸自动匹配 |

**可调参数 (用户输入/默认值)**：

| 参数 | 说明 |
|------|------|
| Sourcing_Cost | 采购成本，默认填入 1688 抓取值 |
| Shipping_Cost_Per_KG | 头程运费/公斤，提供海运/空运默认参考值 |
| Estimated_CPA | 预估单次获客广告费 |
| Return_Rate | 预估退货率，默认 5% |

**核心计算公式**：

- `Landed_Cost (落地成本) = Sourcing_Cost + (Item_Weight * Shipping_Cost_Per_KG)`
- `Amazon_Fees = (Selling_Price * Referral_Fee_Pct) + FBA_Fulfillment_Fee`
- `Net_Profit (单品净利) = Selling_Price - Landed_Cost - Amazon_Fees - Estimated_CPA - (Selling_Price * Return_Rate)`
- `Net_Margin (净利润率) = (Net_Profit / Selling_Price) * 100%`
- `ROI (投资回报率) = (Net_Profit / Landed_Cost) * 100%`

**交互**：用户修改任何可调参数，右侧的利润率和 ROI 图表实时联动重绘。

### 3.6 模块六：AI 分析总结与风险预警 (AI Summary & Risk Assessment)

#### 3.6.1 综合决策报告 (Executive Report)

- **触发**：点击 "Generate Final Report"。
- **处理逻辑**：系统将模块一至五的所有核心数据（JSON 格式）发送给 LLM，要求生成一份执行级别的 Markdown 报告。

**报告模板结构**：

1. **Market Overview (市场现状)**：一句话总结该类目的体量与竞争格局。
2. **Opportunity Assessment (机会点)**：基于竞品差评提炼的具体微创新建议（如："现有产品普遍存在漏水问题，建议在杯盖处增加硅胶密封圈"）。
3. **Pricing Strategy (定价建议)**：结合利润计算器，推荐最佳切入价格带。

#### 3.6.2 风险雷达模型 (Risk Radar)

系统通过预设的算法模型，对该项目进行 1-100 分的风险打分（分数越高风险越大）。

**评估维度与扣分规则**：

- **资金风险**：若 `Landed_Cost * 预估首批备货量 (如 1000 件) > 用户设置的初始资金池`，+30 风险分。
- **侵权风险**：若品牌集中度 (CR3) > 60%，或抓取到标题中含有知名大牌 (如 Apple, Nike)，+40 风险分，并标红提示 "高侵权概率"。
- **物流风险**：若 SP-API 返回的属性中包含 `Batteries_Required = True` 或 `Is_Liquid = True`，+20 风险分，提示 "需危险品/MSDS 审核"。

**可视化**：渲染为一个五维雷达图 (Radar Chart)，直观展示各项风险的短板。

---

## 4. 核心壁垒：3D 动态商品描述生成 (3D Asset Generation)

本模块旨在将 2D 图片转化为符合亚马逊官方要求的 3D 模型，是本产品区别于传统选品工具的核心壁垒。

### 4.1 输入与限制校验 (Input & Validation)

**入口**：在深度分析模块中，选中某个竞品或上传自有产品图，点击 "Generate 3D Model"。

**图片上传区**：

- 支持上传 1-3 张不同角度的高清图片（正视图、侧视图、背视图）。
- 格式要求：.jpg, .jpeg, .png，单张大小不超过 10MB。
- 预处理：前端使用 Canvas 自动将图片压缩至 1024x1024 像素，并去除背景（调用 remove-bg 库）。

**品类限制提示 (Category Constraints)**：

> 当前技术不支持以下品类，请勿浪费额度：透明材质（如玻璃杯）、反光/金属材质、毛发类（如毛绒玩具）、多部件复杂套装、细长线条结构（如自行车辐条）。

### 4.2 API 调用与参数映射 (API Integration)

**底层引擎**：调用 Meshy AI `POST /openapi/v1/image-to-3d` 接口。

**参数配置策略**：

| 参数 | 值 | 说明 |
|------|-----|------|
| image_url | S3 公开图片 URL | 前端预处理后上传至 S3 |
| ai_model | latest (Meshy-6) | 保证最高几何精度 |
| model_type | standard | 默认 |
| topology | triangle | 默认 |
| target_polycount | 30000 | 亚马逊官方建议面数 |
| should_texture | true | 生成带贴图的完整模型 |
| enable_pbr | true | 生成金属度、粗糙度、法线贴图 |
| remove_lighting | true | 去除原图光影 |

**轮询与进度反馈**：

由于 3D 生成耗时较长（约 1-3 分钟），系统获取 `task_id` 后，前端每隔 5 秒调用 `GET /openapi/v1/image-to-3d/{task_id}` 查询进度。界面展示环形进度条 (Progress Circle)，并配以随机轮播的文案（如 "正在重构几何拓扑..."，"正在烘焙 PBR 贴图..."）以缓解用户等待焦虑。

### 4.3 3D 预览与渲染工作台 (3D Viewer & Render Studio)

**3D 预览器 (Web 3D Viewer)**：

- 基于 Three.js 和 React Three Fiber 开发。
- 加载生成的 .glb 文件。
- 交互支持：鼠标左键拖拽进行 360 度旋转，滚轮缩放 (Zoom)，右键平移 (Pan)。

**材质与环境光调整 (Material & Lighting Adjustment)**：

- 右侧面板提供 Environment Map (HDRI) 选择器，内置 5 套预设环境光（如：Studio Light, Natural Daylight, Warm Room）。
- 提供滑块调整 Exposure (曝光度) 和 Roughness (整体粗糙度微调)。

**导出与渲染输出 (Export & Render)**：

- **导出 3D 资产**：点击 "Download .glb"，直接下载符合亚马逊上传标准的文件。
- **渲染 2D 视频**：
  - 提供 3 套运镜模板 (Camera Animations)：360° Turntable (平滑旋转), Zoom In & Pan (推近特写), Dynamic Orbit (动态环绕)。
  - 点击 "Render Video"，后端启动无头浏览器，使用 Three.js 结合 rrweb 或 CCapture 录制 Canvas 动画，通过 FFmpeg 合成为 1080P MP4 视频，时长 10-15 秒，供卖家用于亚马逊主图视频。

---

## 5. 商业化机制设计 (Commercialization & Monetization)

本产品采用显性订阅付费与隐性联盟返佣相结合的商业模式。

### 5.1 "登月计划" 阶梯式订阅 (Tiered Subscription)

采用 SaaS 行业标准的 Freemium 模式，按月/年订阅。所有版本均需用户自备基础 API Key。

| 功能权益 | 免费版 (Free) | 轨道版 (Orbit) | 登月版 (Moonshot) |
|---------|-------------|--------------|-----------------|
| 定价 | $0 / 月 | $39 / 月 | $99 / 月 |
| 基础数据抓取 | 每日限 5 次，每次 Top 20 | 每日限 50 次，每次 Top 100 | 无限制 |
| 插件隐藏数据 | 不支持 | 支持 | 支持 |
| AI 视觉与评论分析 | 不支持 | 每月 20 次 | 无限制 |
| 3D 动态模型生成 | 不支持 | 每月限生成 3 个模型 | 每月限生成 50 个模型 |
| 视频渲染输出 | 不支持 | 支持 720P 导出 | 支持 1080P/4K 导出 |
| API 接入支持 | 仅支持免费/基础 API | 支持绑定高级付费 API | 优先队列，专属技术支持 |

### 5.2 隐性联盟返佣机制 (Stealth Affiliate Mechanism)

这是本产品的核心隐蔽收入来源，通过在用户自然操作路径中静默植入联盟追踪代码（Affiliate Tag）实现变现。

#### 5.2.1 亚马逊前台跳转返佣 (Amazon Associates)

- **场景**：在数据表格或深度分析页面，用户点击某个 ASIN 的链接或图片，意图跳转至亚马逊前台查看该竞品的真实 Listing。
- **技术实现**：系统拦截 `<a>` 标签的默认跳转。后端构造重定向 URL，格式为：`https://www.amazon.com/dp/{ASIN}?tag={Developer_Affiliate_Tag}`。通过 HTTP 302 重定向至该 URL。

#### 5.2.2 供应链采购跳转返佣 (Alimama / 1688 Affiliate)

- **场景**：在利润核算模块，用户点击 "Find Suppliers" 查找到 1688 的同款货源后，点击链接跳转至 1688 采购页面。
- **技术实现**：调用阿里妈妈开放平台的 API，将原始 1688 商品链接转换为带有开发者 pid (推广位 ID) 的淘宝客/1688 客专属推广链接。

#### 5.2.3 第三方服务商推荐返佣 (SaaS/Service Affiliate)

- **场景**：在 "风险预警" 模块，系统根据分析结果动态推荐第三方服务。
  - 若提示 "侵权风险高"，则在下方显示 "推荐使用 Trademarkia 进行商标检索注册"，链接植入 Trademarkia 联盟代码。
  - 若提示 "需海外仓换标"，则推荐指定的海外仓服务商（如 Deliverr），链接植入专属邀请码。
- **技术实现**：前端根据风险标签，从后端的推荐广告池中匹配对应的服务商卡片并渲染。

---

## 6. 核心数据字典 (Data Dictionary)

本节定义了系统核心实体的数据结构，供后端数据库设计与前后端 API 联调参考。

### 6.1 Product (商品基础实体)

| 字段名 | 数据类型 | 描述说明 | 来源 / 备注 |
|--------|---------|---------|------------|
| id | UUID | 系统内部唯一标识 | Primary Key |
| asin | String(10) | 亚马逊标准识别号 | SP-API |
| marketplace_id | String | 站点ID (如 ATVPDKIKX0DER) | 区分不同国家 |
| title | String | 商品标题 | SP-API |
| brand | String | 品牌名称 | SP-API |
| main_image_url | String | 主图的高清下载链接 | SP-API / 爬虫 |
| price_current | Decimal(10,2) | 当前 Buy Box 售价 | Keepa API |
| fulfillment_type | Enum | 发货方式 (FBA/FBM/SFP) | 页面爬取识别 |
| est_sales_30d | Integer | 归一化后的 30 天预估销量 | 算法重算 |
| cvr_30d | Decimal(5,2) | 30 天预估转化率 (%) | 算法重算 |

### 6.2 Analysis_Report (AI 深度分析实体)

| 字段名 | 数据类型 | 描述说明 | 来源 / 备注 |
|--------|---------|---------|------------|
| report_id | UUID | 报告唯一标识 | Primary Key |
| product_id | UUID | 关联的商品 ID | Foreign Key |
| visual_usps | Array[String] | AI 提取的视觉核心卖点 | LLM Vision |
| trust_signals | Array[String] | AI 识别的信任背书 (如 FDA) | LLM Vision |
| pain_points | JSON | 从差评中提取的痛点及权重 | LLM Text |
| buyer_persona | String | AI 描绘的目标人群画像 | LLM Text |
| risk_score | Integer | 综合风险评分 (1-100) | 内部算法模型 |

### 6.3 Asset_3D (3D 资产实体)

| 字段名 | 数据类型 | 描述说明 | 来源 / 备注 |
|--------|---------|---------|------------|
| asset_id | UUID | 资产唯一标识 | Primary Key |
| product_id | UUID | 关联的商品 ID | Foreign Key |
| meshy_task_id | String | Meshy API 返回的任务 ID | 用于轮询状态 |
| status | Enum | 状态 (PENDING/PROCESSING/COMPLETED/FAILED) | 任务状态机 |
| glb_file_url | String | 生成的 .glb 模型在 S3 的存储路径 | Meshy 回传 |
| video_url | String | 渲染出的 MP4 视频在 S3 的存储路径 | 内部渲染引擎 |

---

## 7. 非功能性需求与性能指标 (Non-Functional Requirements)

- **响应时间 (Response Time)**：
  - Web 端首屏加载时间 < 1.5 秒。
  - Top 100 列表数据抓取与初步清洗渲染，必须在 15 秒内完成。
- **并发与吞吐量 (Concurrency & Throughput)**：
  - 支持单租户（用户）同时运行最多 3 个深度分析任务。
  - 3D 生成任务采用消息队列 (如 RabbitMQ/Redis) 异步处理，避免阻塞主线程。
- **SLA (服务等级协议)**：
  - 3D 模型生成成功率需达到 95% 以上。若 Meshy API 失败，系统需自动重试 1 次。
  - 渲染 1080P 视频时长不得超过 5 分钟。
- **安全性与隐私 (Security & Privacy)**：
  - **BYOK 加密**：用户填写的 Amazon SP-API、Keepa API、OpenAI 密钥，必须在后端使用 AES-256-GCM 算法对称加密后存入数据库。加密密钥 (Salt) 存储在环境变量或 KMS 中，绝不硬编码。
  - **数据隔离**：基于租户 ID (Tenant ID) 进行严格的行级数据隔离，确保用户 A 无法通过越权访问 (IDOR) 查看到用户 B 的选品数据。

---

## 8. 系统内部 API 接口清单 (Internal API Endpoints)

以下为系统前后端交互的核心 RESTful API 端点定义，供前后端联调参考。

### 8.1 用户与鉴权 (Auth & User)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/auth/register | 用户注册 | email, password | user_id, jwt_token |
| POST | /api/v1/auth/login | 用户登录 | email, password | jwt_token, refresh_token |
| GET | /api/v1/user/profile | 获取用户信息与订阅状态 | - | user_id, plan, quota_remaining |
| GET | /api/v1/user/quota | 查询当前额度 | - | scrape_remaining, analysis_remaining, 3d_remaining |

### 8.2 API 配置中心 (API Key Management)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/keys/save | 保存用户 API Key | provider (amazon/keepa/openai/meshy), api_key, api_secret | status: saved |
| GET | /api/v1/keys/status | 检测所有 Key 连通性 | - | [{provider, status: ok/error, message}] |
| DELETE | /api/v1/keys/{provider} | 删除指定 Key | - | status: deleted |

### 8.3 选品项目与数据抓取 (Sourcing Projects)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/projects/create | 创建选品项目 | name, marketplace_id, keyword 或 file_upload_id | project_id |
| POST | /api/v1/projects/{id}/scrape | 发起数据抓取任务 | scrape_depth (50/100/200) | task_id, status: queued |
| GET | /api/v1/projects/{id}/products | 获取抓取结果列表 | Query: page, page_size, sort_by, filters | [Product], total_count |
| POST | /api/v1/projects/{id}/filter/ai | AI 智能过滤 | user_description | [filtered_asin_list] |

### 8.4 深度分析 (Deep Analysis)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/analysis/visual | 发起视觉语义分析 | asin, dimensions[] | task_id |
| POST | /api/v1/analysis/reviews | 发起评论深度挖掘 | asin, review_count (默认500) | task_id |
| GET | /api/v1/analysis/{task_id}/result | 获取分析结果 | - | Analysis_Report 完整对象 |
| POST | /api/v1/analysis/report/generate | 生成综合决策报告 | project_id | report_url (Markdown 文件链接) |

### 8.5 3D 资产生成 (3D Generation)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/3d/generate | 发起 2D 转 3D 任务 | image_urls[] (1-3 张) | asset_id, meshy_task_id |
| GET | /api/v1/3d/{asset_id}/status | 轮询 3D 生成进度 | - | status, progress_pct, glb_file_url |
| POST | /api/v1/3d/{asset_id}/render-video | 发起视频渲染任务 | template (turntable/zoom/orbit), resolution (720p/1080p/4k) | render_task_id |
| GET | /api/v1/3d/{asset_id}/video | 获取渲染视频 | - | video_url, status |

### 8.6 利润计算与供应链 (Profit & Supply Chain)

| 方法 | 端点 | 描述 | 请求体核心字段 | 响应体核心字段 |
|------|------|------|-------------|-------------|
| POST | /api/v1/profit/calculate | 计算单品利润 | asin, sourcing_cost, shipping_cost_per_kg, estimated_cpa, return_rate | net_profit, net_margin, roi |
| POST | /api/v1/supply/image-search | 以图搜货 (1688) | image_url | [{supplier_name, product_url, moq, price_rmb, price_usd}] |

---

## 9. 页面清单与导航结构 (Page Inventory & Navigation)

以下为系统所有页面的完整清单，供前端开发与设计师参考。

| 页面编号 | 页面名称 | 路由路径 | 所属模块 | 核心组件 |
|---------|---------|---------|---------|---------|
| P-01 | 登录/注册页 | /auth | 鉴权 | 邮箱密码表单、OAuth 按钮 |
| P-02 | 工作台 (Dashboard) | /dashboard | 全局 | 项目卡片列表、快速操作入口、额度概览 |
| P-03 | 新建选品项目 | /projects/new | 数据抓取 | 关键词输入、文件上传、站点选择 |
| P-04 | 项目数据列表 | /projects/{id} | 数据筛选 | 数据表格、快捷过滤器、AI 过滤面板 |
| P-05 | 单品深度分析 | /products/{asin}/analysis | 深度分析 | 视觉拆解卡片、评论分析图表、变体饼图 |
| P-06 | 3D 实验室 | /3d-lab | 3D生成 | 图片上传区、3D 预览器、材质面板、渲染按钮 |
| P-07 | 大盘与类目分析 | /market/{keyword} | 大盘分析 | 趋势折线图、GMV 卡片、CR 指标、新品存活率 |
| P-08 | 利润计算器 | /profit/{asin} | 利润核算 | 动态表单、实时利润图表、供应商列表 |
| P-09 | 综合决策报告 | /reports/{id} | AI总结 | Markdown 渲染、风险雷达图、导出PDF 按钮 |
| P-10 | API 配置中心 | /settings/api-keys | 系统设置 | Key 输入表单、连通性检测按钮、状态灯 |
| P-11 | 订阅管理 | /settings/subscription | 商业化 | 当前版本卡片、升级按钮、支付历史 |

---

## 10. 开发里程碑与优先级 (Development Milestones)

| 阶段 | 时间周期 | 交付内容 | 优先级 |
|------|---------|---------|--------|
| MVP (最小可行产品) | 第 1-8 周 | 用户注册/登录、API 配置中心、关键词数据抓取 (Top 100)、基础筛选器、利润计算器 | P0 (必须) |
| Alpha (内测版) | 第 9-14 周 | Chrome 插件开发、AI 视觉分析、评论挖掘、大盘分析、综合报告生成 | P0 (必须) |
| Beta (公测版) | 第 15-20 周 | 3D 模型生成集成、3D 预览器、视频渲染、1688 以图搜货 | P1 (重要) |
| GA (正式发布) | 第 21-24 周 | 登月计划订阅系统、隐性返佣机制、性能优化、安全审计 | P1 (重要) |

---

## 11. 附录：外部 API 集成参考 (Appendix: External API Reference)

### 11.1 Amazon SP-API - Catalog Items v2022-04-01

该 API 用于获取亚马逊商品目录中的基础属性数据。开发者需在 Amazon Seller Central 注册开发者账号并获取 LWA (Login with Amazon) 凭证。

| 端点 | 方法 | 描述 |
|------|------|------|
| /catalog/2022-04-01/items | GET | 按关键词搜索商品，返回 ASIN 列表及摘要信息 |
| /catalog/2022-04-01/items/{asin} | GET | 按 ASIN 获取单个商品的详细属性 |

核心请求参数包括 `keywords` (搜索关键词)、`marketplaceIds` (站点 ID)、`includedData` (指定返回哪些数据块，如 summaries, images, salesRanks, dimensions)。响应体中 `summaries` 包含 `itemName`, `brand`, `manufacturer`；`images` 包含各尺寸图片的 URL；`salesRanks` 包含 BSR 排名及所属类目节点。

### 11.2 Keepa API - Product Request

该 API 用于获取亚马逊商品的历史价格、BSR 排名趋势及 Buy Box 状态。需在 Keepa 官网购买 API Token。

核心请求参数为 `domain` (站点编号，如 1=US, 3=UK)、`asin` (支持逗号分隔批量查询，最多 100 个)、`stats` (统计周期天数)、`history` (是否返回完整历史数据)、`offers` (是否返回 Offer 列表)。响应体中 `data.csv` 数组包含按固定索引排列的时间序列数据，其中索引 0 为 Amazon Price，索引 1 为 New Price，索引 16 为 Rating，索引 17 为 Review Count，索引 18 为 Buy Box Price。

### 11.3 Meshy AI - Image to 3D API

该 API 用于将 2D 图片转化为带纹理的 3D 模型文件。需在 Meshy 官网注册并获取 API Key。

核心端点为 `POST /openapi/v1/image-to-3d` (创建任务) 和 `GET /openapi/v1/image-to-3d/{task_id}` (查询进度)。创建任务时，必填参数为 `image_url` (公开可访问的图片 URL 或 base64 Data URI，支持 jpg/jpeg/png)。可选参数包括 `ai_model` (meshy-5/meshy-6/latest)、`topology` (quad/triangle)、`target_polycount` (100-300000)、`should_texture` (是否生成纹理)、`enable_pbr` (是否生成 PBR 贴图)。任务完成后，响应体中 `model_urls.glb` 字段包含可下载的 GLB 格式 3D 模型文件 URL。每次生成消耗 20-30 credits（取决于是否含纹理）。
