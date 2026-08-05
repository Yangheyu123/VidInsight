# VidInsight 开发指南

## 1. 环境基线

| 工具 | 建议版本 | 说明 |
|---|---:|---|
| Git | 2.40+ | 版本管理 |
| Node.js | 22 LTS | 前端构建；提交锁文件 |
| Python | 3.12 | FastAPI 与 Worker |
| PostgreSQL | 16 | 主库 |
| Redis | 7 | Celery Broker 与缓存 |
| Docker Desktop / Engine | 当前稳定版 | 本地依赖与部署 |

依照最终技术选型，Python 依赖使用 `requirements.txt` 固定版本；前端统一使用 npm 并提交 `package-lock.json`。不允许多个包管理器并存。

## 2. 目标目录

```text
VidInsight/
├─ backend/
│  ├─ app/
│  │  ├─ api/
│  │  ├─ core/
│  │  ├─ db/
│  │  ├─ integrations/
│  │  ├─ modules/
│  │  ├─ tasks/
│  │  └─ main.py
│  ├─ alembic/
│  ├─ tests/
│  ├─ requirements.txt
│  └─ Dockerfile
├─ frontend/
│  ├─ src/
│  ├─ tests/
│  ├─ package.json
│  ├─ package-lock.json
│  └─ Dockerfile
├─ infra/
│  ├─ nginx/
│  ├─ monitoring/
│  └─ scripts/
├─ docs/
├─ docker-compose.yml
├─ .env.example
├─ Makefile
└─ README.md
```

## 3. 本地启动约定

项目落地代码后，根目录应提供一致命令：

```bash
cp .env.example .env
docker compose up -d postgres redis
make backend-install
make frontend-install
make db-upgrade
make dev
```

预期地址：

| 服务 | 地址 |
|---|---|
| Web | `http://localhost:5173` |
| API | `http://localhost:8000/api/v1` |
| Swagger | `http://localhost:8000/docs` |

`.env.example` 只提供变量名和安全示例，不提交真实凭证。建议变量：

```dotenv
APP_ENV=development
APP_SECRET_KEY=change-me
DATABASE_URL=postgresql+asyncpg://vidinsight:vidinsight@localhost:5432/vidinsight
REDIS_URL=redis://localhost:6379/0
DOUYIN_CLIENT_KEY=
DOUYIN_CLIENT_SECRET=
AI_PROVIDER=
AI_API_KEY=
ENABLE_COMPUTER_USE=false
ENABLE_CONTROLLED_CRAWLER=false
CRAWLER_ALLOWED_DOMAINS=
CRAWLER_DEFAULT_RATE_LIMIT=1/5s
```

配置启动时做类型校验；生产缺少必需配置必须 fail fast。

## 4. 后端工程规范

- FastAPI 路由保持薄层：校验 → 鉴权 → use case → response schema。
- 全链路使用 async SQLAlchemy；不要在事件循环中调用阻塞 SDK，必要时放 Worker 或线程池。
- ORM 实体、输入 schema 和输出 schema 分离，禁止直接返回 ORM 对象的全部字段。
- 事务边界由 use case 管理，repository 不隐式 commit。
- 外部 Douyin/AI/Computer Use/受控爬虫客户端包装为 typed adapter，设置显式 timeout、重试与错误映射。
- 业务异常使用稳定错误码；禁止将第三方原始错误、SQL 或堆栈返回给前端。
- Celery task 只解析 task 参数并调用领域用例；参数只传 ID，不传大对象或 Token。
- 所有时间使用 aware datetime；所有计数和金额避免浮点误差。

建议质量工具：Ruff（lint/format）、mypy 或 pyright（类型）、pytest、pytest-asyncio。检查规则在 CI 与本地完全一致。

## 5. 前端工程规范

- TypeScript 开启 strict；禁止通过 `any` 绕过 API 与状态模型。
- 服务端数据只由 TanStack Query 管理；局部交互用 React state，不为简单状态引入 Redux。
- query key 由集中工厂生成并包含工作区与筛选条件。
- API client 集中处理 base URL、会话、request ID、错误模型和取消信号。
- API 类型从 OpenAPI 自动生成；业务展示模型可通过 adapter 派生。
- 页面筛选写 URL；格式化数字、日期、比率和来源用统一函数。
- 组件优先组合，避免巨大万能组件；业务组件不直接写未封装图表主题。
- 用户可见文案集中维护，状态枚举必须有 unknown fallback。

建议质量工具：ESLint、Prettier、Vitest、Testing Library、Playwright。Tailwind class 排序使用统一插件或 lint 规则。

## 6. 数据库迁移

```bash
# 生成迁移后必须人工审查
alembic revision --autogenerate -m "add video metrics snapshot"
alembic upgrade head
alembic check
```

- 每个 schema 变化必须带 migration 和测试。
- 不在已有迁移文件上修改历史，新增修复迁移。
- 加非空列先 nullable/默认值、回填，再加约束。
- 删除字段至少经过一个发布周期，先停止读写再 contract。
- 本地和 CI 使用全新数据库从零执行全部迁移。

## 7. API 联调流程

1. 后端先更新 Pydantic schema 和 OpenAPI。
2. CI 生成并比较 `openapi.json`，检查破坏性变化。
3. 前端重新生成类型与 client。
4. 使用契约样例完成 Mock，后端完成后切换真实环境。
5. 联调验证空值、未知枚举、分页边界、权限和错误，而不只验证 happy path。

## 8. Git 与提交

- `main` 保持可发布，功能通过短分支和 PR 合并。
- 分支建议：`feat/dashboard-overview`、`fix/oauth-refresh`、`docs/api-errors`。
- Conventional Commits：`feat:`、`fix:`、`docs:`、`refactor:`、`test:`、`chore:`。
- PR 聚焦一个可审查目标，描述背景、方案、测试、截图、迁移与风险。
- 不提交 `.env`、Token、用户数据、平台响应、媒体文件和本地浏览器 profile。

## 9. 日志与调试

- 本地日志可读，生产日志为 JSON。
- 日志级别：INFO 记录生命周期，WARNING 记录可恢复异常，ERROR 记录需要处理的失败。
- 敏感字段过滤器覆盖 token、secret、authorization、cookie、手机号、评论用户 ID。
- 用户报告问题时使用页面提供的 `request_id` 定位，不要求用户提供凭证或完整响应。

## 10. 完成定义（DoD）

一个功能只有同时满足以下条件才算完成：

- 需求和验收标准已实现，权限与工作区隔离已验证；
- 代码通过格式、lint、类型、单元与集成测试；
- API、迁移、错误、Loading、空状态和可访问性均已覆盖；
- 有影响的文档和 OpenAPI 已更新；
- 新日志和指标可支持生产排障且不泄露敏感数据；
- UI 通过亮/暗主题、1024px、键盘与核心浏览器检查；
- PR 有风险说明、验证证据和必要截图。
