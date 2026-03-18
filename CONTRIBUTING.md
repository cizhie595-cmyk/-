# Contributing to Click-Stats

感谢您对 Click-Stats（Coupang/Amazon 跨境电商智能选品系统）的关注！我们欢迎所有形式的贡献。

## 开发环境设置

### 前置要求

- Python 3.11+
- MySQL 8.0+
- Redis 6.0+
- Node.js 18+（Chrome Extension 开发）

### 快速开始

```bash
# 1. 克隆仓库
git clone https://github.com/avst-cloud/click-stats.git
cd click-stats

# 2. 创建环境配置
make env

# 3. 安装依赖
make deps-dev

# 4. 初始化数据库
make db-init

# 5. 启动开发服务器
make dev
```

## 分支策略

我们使用 **Git Flow** 工作流：

| 分支 | 用途 | 命名规范 |
|------|------|----------|
| `main` | 生产就绪代码 | - |
| `develop` | 开发集成分支 | - |
| `feature/*` | 新功能开发 | `feature/add-xxx` |
| `bugfix/*` | Bug 修复 | `bugfix/fix-xxx` |
| `hotfix/*` | 紧急修复 | `hotfix/patch-xxx` |

## 提交规范

使用 [Conventional Commits](https://www.conventionalcommits.org/) 格式：

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Type 类型

| Type | 说明 |
|------|------|
| `feat` | 新功能 |
| `fix` | Bug 修复 |
| `docs` | 文档更新 |
| `style` | 代码格式（不影响逻辑） |
| `refactor` | 重构（不新增功能或修复 Bug） |
| `perf` | 性能优化 |
| `test` | 测试相关 |
| `chore` | 构建/工具链变更 |

### 示例

```
feat(scraper): add Coupang keyword crawler
fix(auth): resolve token refresh race condition
docs(api): update Swagger endpoint descriptions
test(export): add PDF export unit tests
```

## 代码规范

### Python

- 遵循 PEP 8，行宽限制 120 字符
- 使用 Black 格式化，isort 排序导入
- 所有公共函数必须有 docstring
- 类型注解推荐但不强制

```bash
# 格式化代码
make format

# 代码检查
make lint

# 类型检查
make type-check
```

### JavaScript

- 使用 ES6+ 语法
- 使用 `async/await` 处理异步
- 遵循项目现有的命名约定

### HTML/CSS

- 使用语义化 HTML5 标签
- CSS 类名使用 BEM 命名法
- 所有用户可见文本添加 `data-i18n` 属性

## 测试要求

- 新功能必须附带对应的测试
- Bug 修复必须附带回归测试
- 测试覆盖率不低于 80%

```bash
# 运行测试
make test

# 运行测试并生成覆盖率报告
make test-cov
```

### 测试标记

```python
@pytest.mark.unit          # 单元测试
@pytest.mark.integration   # 集成测试
@pytest.mark.slow          # 耗时测试
@pytest.mark.scraper       # 爬虫测试
@pytest.mark.auth          # 认证测试
```

## Pull Request 流程

1. 从 `develop` 分支创建功能分支
2. 编写代码和测试
3. 确保 `make check` 通过（lint + test）
4. 提交 PR 到 `develop` 分支
5. 等待 Code Review
6. 合并后删除功能分支

### PR 模板

```markdown
## 变更描述
简要描述本次变更的内容和目的。

## 变更类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 文档更新
- [ ] 性能优化
- [ ] 重构

## 测试
- [ ] 已添加/更新测试
- [ ] 所有测试通过
- [ ] 已在本地验证

## 截图（如适用）
```

## 报告 Bug

请使用 GitHub Issues 报告 Bug，包含以下信息：

1. **环境信息**：操作系统、Python 版本、浏览器版本
2. **复现步骤**：详细的操作步骤
3. **期望行为**：你期望发生什么
4. **实际行为**：实际发生了什么
5. **错误日志**：相关的错误信息或截图

## 功能建议

欢迎通过 GitHub Issues 提交功能建议，请描述：

1. **使用场景**：为什么需要这个功能
2. **期望行为**：功能应该如何工作
3. **替代方案**：是否有其他解决方式

## 行为准则

- 尊重所有贡献者
- 保持专业和友好的沟通
- 接受建设性的批评
- 关注项目的最佳利益

## 联系方式

如有任何问题，请通过 GitHub Issues 联系我们。
