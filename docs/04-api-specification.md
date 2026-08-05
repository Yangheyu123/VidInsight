# VidInsight API 设计规范

## 1. 基础约定

- Base URL：`/api/v1`
- 协议：HTTPS + JSON；文件上传使用 `multipart/form-data`
- 文档：FastAPI 自动生成 `/docs`、`/redoc` 和 `/openapi.json`
- 命名：URL 使用复数 kebab-case，JSON 字段使用 snake_case
- 时间：ISO 8601 UTC，例如 `2026-08-05T08:00:00Z`
- ID：对外使用不透明 UUID/字符串，不暴露连续数据库主键
- 大整数：JSON 返回 number；前端生成类型需避免不安全整数，预计超过范围的标识使用 string
- 金额：最小货币单位整数；比例：API 返回 0-1 小数，界面格式化为百分比

## 2. 鉴权与工作区

请求使用安全 Cookie 会话或 `Authorization: Bearer <token>`。浏览器端优先使用 HttpOnly、Secure、SameSite Cookie，防止 Token 被脚本读取。

工作区由路由参数或经过验证的会话上下文确定：

```text
/api/v1/workspaces/{workspace_id}/accounts
```

服务端必须验证当前用户是目标工作区成员，禁止只信任前端传来的 `workspace_id`。修改请求应验证 CSRF（Cookie 模式）并写入审计日志。

## 3. 响应格式

单对象成功直接返回资源，列表返回统一分页结构：

```json
{
  "items": [],
  "page": 1,
  "page_size": 20,
  "total": 0,
  "has_next": false
}
```

错误使用 RFC 7807 风格：

```json
{
  "type": "https://docs.vidinsight.local/errors/account-auth-expired",
  "title": "账号授权已过期",
  "status": 409,
  "code": "ACCOUNT_AUTH_EXPIRED",
  "detail": "请重新授权后再发起同步。",
  "instance": "/api/v1/workspaces/ws_123/accounts/acc_123/sync",
  "request_id": "req_01J...",
  "errors": []
}
```

字段校验错误的 `errors` 项包含 `field`、`code` 和 `message`。响应头返回 `X-Request-ID`，接受客户端传入合法 `X-Request-ID`，否则由服务端生成。

## 4. HTTP 语义

| 场景 | 方法 / 状态 |
|---|---|
| 查询资源 | `GET 200` |
| 创建资源 | `POST 201`；异步任务可 `202` |
| 部分修改 | `PATCH 200` |
| 删除或解绑 | `DELETE 204`，高影响操作可用动作端点返回任务 |
| 输入不合法 | `422` |
| 未登录 / 无权限 | `401 / 403` |
| 资源不存在 | `404`，跨工作区对象同样返回 404 防枚举 |
| 状态冲突 | `409` |
| 请求过多 | `429`，返回 `Retry-After` |
| 幂等重放 | 返回首次请求结果，不重复创建 |

创建任务、提交导入、批量分析等接口接受 `Idempotency-Key`，服务端至少保留 24 小时。`DELETE` 不接受 request body；需要原因或复杂参数时使用明确动作端点。

## 5. 查询、分页与排序

- `page` 从 1 开始，`page_size` 默认 20，最大 100。
- 高频大列表后续可升级 cursor pagination，但同一接口版本不混用两种模型。
- 排序使用 `sort=-publish_time,play_count`，负号代表降序。
- 时间过滤使用 `start_at`、`end_at`，区间语义为 `[start_at, end_at)`。
- 多值过滤可重复参数：`status=active&status=expiring`。
- 搜索参数为 `q`；服务端限制长度并转义全文检索表达式。
- 所有列表响应在稳定字段上增加次级排序（通常为 `id`），避免翻页漂移。

## 6. 端点总览

### 6.1 会话、工作区与成员

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/auth/login` | 公开 | 登录 |
| POST | `/auth/logout` | 已登录 | 退出并撤销会话 |
| GET | `/auth/me` | 已登录 | 当前用户、工作区和权限 |
| GET | `/workspaces` | 已登录 | 可访问工作区 |
| GET | `/workspaces/{wid}/members` | admin | 成员列表 |
| POST | `/workspaces/{wid}/members` | admin | 邀请成员 |
| PATCH | `/workspaces/{wid}/members/{member_id}` | admin | 修改角色 |
| DELETE | `/workspaces/{wid}/members/{member_id}` | admin | 移除成员 |

### 6.2 抖音 OAuth 与账号

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| POST | `/workspaces/{wid}/oauth/douyin/authorize` | admin | 创建授权 URL |
| GET | `/oauth/douyin/callback` | 公开回调 | 校验并完成授权 |
| GET | `/workspaces/{wid}/accounts` | viewer+ | 账号列表 |
| POST | `/workspaces/{wid}/accounts` | operator+ | 新增待授权账号 |
| POST | `/workspaces/{wid}/accounts/batch` | operator+ | 最多批量录入 100 个账号，返回逐行结果 |
| GET | `/workspaces/{wid}/accounts/{account_id}` | viewer+ | 账号详情 |
| PATCH | `/workspaces/{wid}/accounts/{account_id}` | operator+ | 修改别名、优先级、采集设置 |
| POST | `/workspaces/{wid}/accounts/{account_id}/sync` | operator+ | 创建手动同步任务，返回 202 |
| POST | `/workspaces/{wid}/accounts/{account_id}/reauthorize` | admin | 生成重新授权 URL |
| POST | `/workspaces/{wid}/accounts/{account_id}/enable` | operator+ | 启用账号采集 |
| POST | `/workspaces/{wid}/accounts/{account_id}/disable` | operator+ | 停用账号并撤销待执行任务 |
| DELETE | `/workspaces/{wid}/accounts/{account_id}` | admin | 解绑并停止采集 |

账号摘要示例：

```json
{
  "id": "acc_01J...",
  "platform": "douyin",
  "nickname": "示例账号",
  "avatar_url": "https://signed-cdn.example/...",
  "authorization_status": "active",
  "auth_expires_at": "2026-09-05T08:00:00Z",
  "follower_count": 128000,
  "video_count": 245,
  "last_synced_at": "2026-08-05T07:58:00Z",
  "data_freshness_seconds": 120,
  "source": "official_api"
}
```

### 6.3 Dashboard

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workspaces/{wid}/dashboard/overview` | 核心指标与环比 |
| GET | `/workspaces/{wid}/dashboard/trends` | 时间序列趋势 |
| GET | `/workspaces/{wid}/dashboard/top-videos` | Top 视频 |
| GET | `/workspaces/{wid}/dashboard/account-ranking` | 账号排行 |

公共参数：`period=day|week|month|custom`、`start_at`、`end_at`、`account_id`、`timezone`、`sort`。响应包含：

```json
{
  "range": {
    "start_at": "2026-07-29T00:00:00Z",
    "end_at": "2026-08-05T00:00:00Z",
    "timezone": "Asia/Shanghai"
  },
  "freshness": {
    "last_success_at": "2026-08-05T07:58:00Z",
    "status": "fresh"
  },
  "metrics": {
    "account_count": {"value": 12, "change": 1, "change_type": "absolute"},
    "total_plays": {"value": 12846000, "change": 0.124, "change_type": "rate"},
    "engagement_rate": {"value": 0.074, "change": -0.003, "change_type": "point"}
  }
}
```

### 6.4 视频与指标

| 方法 | 路径 | 权限 | 说明 |
|---|---|---|---|
| GET | `/workspaces/{wid}/videos` | viewer+ | 视频筛选、搜索、排序 |
| GET | `/workspaces/{wid}/videos/{video_id}` | viewer+ | 视频详情与最新指标 |
| GET | `/workspaces/{wid}/videos/{video_id}/metrics` | viewer+ | 指标时间序列 |
| GET | `/workspaces/{wid}/videos/{video_id}/comments` | viewer+ | 评论列表（按权限脱敏） |
| POST | `/workspaces/{wid}/videos/{video_id}/analysis-runs` | operator+ | 创建分析任务 |
| POST | `/workspaces/{wid}/videos/batch-analysis-runs` | operator+ | 批量分析，返回批次任务 |

视频列表参数包括：`account_id`、`published_start_at`、`published_end_at`、`analysis_status`、`min_play_count`、`tag`、`q` 和 `sort`。

### 6.5 AI 分析

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workspaces/{wid}/analysis-runs` | 分析任务列表 |
| GET | `/workspaces/{wid}/analysis-runs/{run_id}` | 步骤、进度、成本和错误 |
| POST | `/workspaces/{wid}/analysis-runs/{run_id}/retry` | 重试失败步骤 |
| POST | `/workspaces/{wid}/analysis-runs/{run_id}/cancel` | 取消未完成任务 |
| GET | `/workspaces/{wid}/videos/{video_id}/analyses/latest` | 最新可用分析 |
| GET | `/workspaces/{wid}/videos/{video_id}/analyses` | 历史版本 |
| GET | `/workspaces/{wid}/diagnoses` | 按规则、严重度、账号和周期筛选诊断 |
| POST | `/workspaces/{wid}/videos/{video_id}/diagnose` | 重跑五类 MVP 规则诊断，返回 202 |

分析结果必须区分事实、模型判断和建议：

```json
{
  "id": "ana_01J...",
  "video_id": "vid_01J...",
  "status": "completed",
  "summary": "...",
  "themes": [{"label": "职场效率", "confidence": 0.91}],
  "hook": {
    "type": "问题式开场",
    "score": 0.82,
    "evidence": [{"start_ms": 0, "end_ms": 2800, "text": "..."}]
  },
  "viral_score": {"value": 0.76, "confidence_low": 0.66, "confidence_high": 0.84},
  "suggestions": [{"title": "...", "reason": "...", "evidence_refs": ["metric:plays:7d"]}],
  "model": {"provider": "...", "name": "...", "version": "...", "prompt_version": "v1"},
  "analyzed_at": "2026-08-05T08:00:00Z"
}
```

### 6.6 任务、导入与导出

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workspaces/{wid}/jobs` | 按类型、状态和账号查询任务 |
| GET | `/workspaces/{wid}/jobs/{job_id}` | 任务进度与安全错误详情 |
| POST | `/workspaces/{wid}/jobs/{job_id}/retry` | 重试允许重试的任务 |
| POST | `/workspaces/{wid}/jobs/{job_id}/cancel` | 请求取消 |
| POST | `/workspaces/{wid}/imports` | 上传文件，返回预检任务 |
| GET | `/workspaces/{wid}/imports/{import_id}/preview` | 映射、样例和错误 |
| POST | `/workspaces/{wid}/imports/{import_id}/commit` | 确认导入 |
| GET | `/workspaces/{wid}/imports/{import_id}/errors` | 下载错误报告 |
| POST | `/workspaces/{wid}/exports` | 按当前筛选创建 XLSX 异步导出 |
| GET | `/workspaces/{wid}/exports/{export_id}/download` | 鉴权后流式下载，文件 24 小时过期 |

### 6.7 审计与健康

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workspaces/{wid}/audit-logs` | admin 查看工作区审计事件 |
| GET | `/health/live` | 进程存活，不检查外部依赖 |
| GET | `/health/ready` | 检查必要依赖能否服务 |
| GET | `/version` | 构建版本和提交号，不泄露秘密 |

### 6.8 数据源连接器（仅 admin）

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/workspaces/{wid}/connectors` | 查看官方 API、Computer Use、导入和受控爬虫连接器状态 |
| POST | `/workspaces/{wid}/connectors` | 创建待审批连接器配置，不自动启用 |
| GET | `/workspaces/{wid}/connectors/{connector_id}` | 查看字段白名单、审批摘要、健康度和最近错误 |
| PATCH | `/workspaces/{wid}/connectors/{connector_id}` | 收紧配置；扩大范围需创建新审批版本 |
| POST | `/workspaces/{wid}/connectors/{connector_id}/dry-run` | 单页测试，只写 staging 并返回脱敏预览 |
| POST | `/workspaces/{wid}/connectors/{connector_id}/enable` | 验证审批、owner 和到期时间后启用 |
| POST | `/workspaces/{wid}/connectors/{connector_id}/disable` | 立即停用并撤销待执行任务 |
| GET | `/workspaces/{wid}/connectors/{connector_id}/samples` | 查看抽样对账、schema 指纹和 quarantine 摘要 |

连接器创建/修改请求必须包含 `source_type`、账号范围、允许域名/路径、允许字段、业务目的、审批编号、最大频率/并发、响应大小上限、`enabled_from/expires_at`、owner。Cookie、Token、浏览器 profile 和完整页面内容不得通过 API 返回。

## 7. 错误码

| code | HTTP | 含义 | 客户端动作 |
|---|---:|---|---|
| `AUTH_REQUIRED` | 401 | 未登录或会话失效 | 跳转登录并保留返回地址 |
| `PERMISSION_DENIED` | 403 | 角色不足 | 显示需要的权限 |
| `RESOURCE_NOT_FOUND` | 404 | 资源不存在或不可见 | 返回列表或显示空状态 |
| `ACCOUNT_AUTH_EXPIRED` | 409 | 平台授权过期 | 引导重新授权 |
| `ACCOUNT_SYNC_RUNNING` | 409 | 同类同步已运行 | 跳转现有任务 |
| `IDEMPOTENCY_CONFLICT` | 409 | 同 Key 对应不同请求 | 生成新 Key 或检查重复提交 |
| `SOURCE_RATE_LIMITED` | 429 | 外部平台限流 | 显示预计恢复时间，不频繁重试 |
| `IMPORT_VALIDATION_FAILED` | 422 | 文件预检失败 | 展示字段与行错误 |
| `ANALYSIS_BUDGET_EXCEEDED` | 409 | 超出工作区预算 | 联系管理员调整预算 |
| `UPSTREAM_UNAVAILABLE` | 503 | 外部平台或模型不可用 | 稍后重试并显示 request ID |
| `CONNECTOR_APPROVAL_REQUIRED` | 403 | 连接器无有效审批或范围超出审批 | 停止操作并联系管理员/合规负责人 |
| `CONNECTOR_POLICY_DENIED` | 403 | URL、字段、账号或频率不在 Policy Gate 白名单 | 不重试，检查配置范围 |
| `CONNECTOR_CHALLENGE_DETECTED` | 409 | 检测到验证码、登录墙或挑战页 | 连接器已熔断，转人工处理 |
| `CONNECTOR_SCHEMA_DRIFT` | 409 | 页面指纹或字段结构变化 | 查看 dry-run/quarantine，更新解析器后重新审批 |

## 8. 版本与兼容

- `/api/v1` 内只做向后兼容的字段增加；客户端必须忽略未知字段。
- 删除或改变字段语义需要新主版本，并提供迁移期。
- 枚举新增值属于兼容变化，前端必须有 unknown fallback。
- OpenAPI 在 CI 中生成并比较；破坏性变化阻止合并。
- 前端类型从 OpenAPI 自动生成，禁止手工维护重复接口类型。

## 9. 安全与限流

- 登录、OAuth、导出和 AI 任务使用独立限流桶。
- 列表查询限制时间跨度、页大小和排序字段白名单。
- 上传文件校验扩展名、MIME、签名、大小和压缩炸弹；异步扫描后处理。
- 返回第三方 URL 前校验允许域名，服务端下载防 SSRF。
- CORS 使用显式源列表；生产禁止 `*` 与凭证组合。
- OpenAPI 生产环境可限制为内部访问，但健康接口保持最小信息。
