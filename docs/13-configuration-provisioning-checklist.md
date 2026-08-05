# VidInsight 配置与数据提供清单

本清单用于将已完成的业务逻辑接入真实环境。机密值只能写入部署平台的 Secret 或本机未提交的 `.env`，不要通过聊天、截图、Git 仓库或 Excel 传递。

## 1. 部署基础配置

| 配置项 | 示例/格式 | 获取或生成方式 | 必填 |
|---|---|---|---|
| `APP_SECRET_KEY` | 至少 32 位随机字符串 | 使用密码管理器生成 | 是 |
| `TOKEN_ENCRYPTION_KEY` | 至少 32 位随机字符串 | 使用密码管理器生成；用于加密抖音令牌 | 是 |
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL 实例连接串 | 是（生产） |
| `REDIS_URL` | `redis://.../0` | Redis 实例连接串 | 是（定时任务） |
| `FRONTEND_ORIGINS` | `https://console.example.com` | 你的正式前端域名 | 是（生产） |
| `FRONTEND_APP_URL` | `https://console.example.com` | 你的正式前端域名 | 是（OAuth 回跳） |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | 内部管理员账号 | 首次部署前设置；登录后应轮换初始密码 | 是 |

复制 `.env.example` 为 `.env` 后填写；`.env` 已被 Git 忽略。

## 2. 抖音网站应用 OAuth

1. 进入 [抖音开放平台](https://developer.open-douyin.com/)，完成开发者入驻。
2. 在控制台创建并提交审核“网站应用”；官方创建说明见[移动/网站应用概述](https://developer.open-douyin.com/docs/resource/zh-CN/dop/overview/platform-introduction/)。
3. 在“我的应用 → 网站应用 → 应用信息/总览”获取 Client Key 与 Client Secret。
4. 在“设置 → 开发配置 → 授权回调地址”登记**完整 HTTPS 地址**：

   ```text
   https://你的-api-域名/api/v1/integrations/douyin/callback
   ```

   回调地址必须和控制台登记的域名与路径一致；不要附加自定义 query 参数。官方授权说明见[手机号和扫码登录授权](https://developer.open-douyin.com/m/docs/resource/zh-CN/dop/develop/sdk/web-app/web/permission/)。
5. 在“能力管理”申请实际需要的数据能力，并记录每项能力批准的 scope、配额、场景说明和审批编号。先只配置获批 scope，默认值可保留 `user_info`。

填入：

```dotenv
DOUYIN_CLIENT_KEY=从控制台复制
DOUYIN_CLIENT_SECRET=从控制台复制（仅 Secret）
DOUYIN_REDIRECT_URI=https://你的-api-域名/api/v1/integrations/douyin/callback
DOUYIN_SCOPES=已获批的scope1,已获批的scope2
```

配置后，以管理员登录 VidInsight，调用 `GET /api/v1/integrations/douyin/preflight` 确认 `ready_for_oauth=true`；再为每个账号启动授权。系统自行取得并加密保存 access/refresh token，不需要、也不应人工提供用户 token。

## 3. 经营授权视频指标

若你的应用已完成品牌号、员工号或合作号的经营关系授权，并获批“视频数据查询”能力：

1. 按[经营授权视频查询文档](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/user-video-data/videobc)取得用于该能力的 business access token。
2. 将该令牌只写入部署 Secret：

   ```dotenv
   DOUYIN_BUSINESS_ACCESS_TOKEN=业务授权调用凭证
   ```

3. 确保需要同步的作品已有官方 `item_id`（即账号下 `platform_item_id`）。系统每 5 分钟采集已知作品的播放、点赞、评论、分享和转发。

该接口不提供通用完播率和视频级涨粉转化；这不是配置遗漏。

## 4. 完播率与涨粉转化数据源

为完成验收中的完播率、视频级涨粉转化，请提供以下任一合规来源：

| 需要提供的材料 | 要求 |
|---|---|
| 供应商/官方数据接口地址 | HTTPS、可从部署网络访问、无重定向到未批准域名 |
| 鉴权方式 | 使用 Secret 管理；例如服务端 Bearer token，不提供给前端 |
| 真实脱敏样例响应 | 至少 2 个账号、5 条视频、2 个采集时点 |
| 字段字典 | 包含单位、分母、时区、延迟、空值语义、更新频率 |
| 配额与限流说明 | 每分钟/每天额度、429 处理、最大并发 |
| 用途授权/合同 | 明确允许内部矩阵运营统计与历史留存 |

适配器契约见项目根目录 `README.md` 的“自动采集适配器契约”。提供方返回的数据会经过校验、去重并追加为历史快照，不能覆盖旧记录。

## 5. 上线前验证步骤

1. 执行 `docker compose up --build`，确认 API、worker、beat、PostgreSQL、Redis 健康。
2. 使用管理员登录，检查 `/api/v1/integrations/douyin/preflight`。
3. 新增一个测试账号，完成 OAuth 授权；确认账号状态为 `active`。
4. 手动刷新一次，检查 `/api/v1/sync-jobs` 状态、写入数量和错误信息。
5. 导入/同步两次快照，确认历史记录增加且没有覆盖旧数据。
6. 检查 `/api/v1/metrics/coverage`；只有所有必填字段真实来源覆盖后才应为 `ready_for_acceptance=true`。
7. 导出 Excel，检查“汇总、视频明细、口径说明”三个工作表以及当前筛选一致性。

## 6. 不要提供的内容

- 个人抖音密码、短信验证码、扫码截图或 Cookie。
- 未经授权的爬虫账号、绕过验证的脚本或代理池。
- 将 Client Secret、business token、数据库密码提交到 Git。

如平台未批准相应用途、scope 或字段，保持对应配置为空；系统会显示 `partial` 或覆盖未通过，而不是伪造指标。
