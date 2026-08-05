# 当前实现接口补充

以下接口已在当前 FastAPI 服务中实现：

| 接口 | 用途 |
|---|---|
| `POST /api/v1/accounts/{account_id}/authorize` | 生成抖音官方 OAuth 授权跳转地址 |
| `GET /api/v1/integrations/douyin/callback` | 校验 state、交换授权码并加密保存令牌 |
| `GET /api/v1/integrations/douyin/preflight` | 检查 Client Key、Secret、回调地址、scope 与字段缺口；不返回密钥 |
| `POST /api/v1/accounts/{account_id}/data/import` | 原子追加账号快照与最多 500 条视频指标，重复时间点跳过不覆盖 |
| `GET /api/v1/sync-jobs` | 按账号查看最近同步任务、写入数量、状态和错误原因 |

`data/import` 的请求体为 `{ "account_snapshot": {...}, "videos": [...] }`；其中 `videos` 的单条字段与 `POST /accounts/{account_id}/videos/import` 相同。调用方必须提供真实来源与采集时间，不接受模型估算值作为验收依据。

经营授权视频采集在配置 `DOUYIN_BUSINESS_ACCESS_TOKEN` 后自动运行，但只写入官方已确认返回的播放、点赞、评论、分享和转发字段。完播率和视频级涨粉转化仍由覆盖门禁保护，必须由另一个获批数据源补齐。
