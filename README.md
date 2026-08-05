# VidInsight

内部抖音矩阵数据看板：账号管理、定时/手动采集、日周月汇总、Excel 导出和基于指标的内容诊断。

## 本地启动

1. 复制环境变量：`Copy-Item .env.example .env`。
2. 在 `.env` 中设置随机 `APP_SECRET_KEY`，以及受审批的数据源配置。
3. 启动：`docker compose up --build`。
4. 打开 `http://localhost`；默认开发账号为 `admin@vidinsight.local` / `ChangeMe123!`，首次部署后必须修改。

## 抖音 OAuth 配置

在抖音开放平台创建并审核网站应用后，设置 `DOUYIN_CLIENT_KEY`、`DOUYIN_CLIENT_SECRET`、`DOUYIN_REDIRECT_URI` 和申请通过的 `DOUYIN_SCOPES`。回调地址必须是 HTTPS，且与开放平台控制台登记的完整地址一致。进入账号管理后调用 `POST /api/v1/accounts/{account_id}/authorize`，将浏览器跳转到官方授权页；回调会把账户级令牌加密保存到服务端。

请只申请业务实际需要的 scope。官方移动/网站应用规范对用户数据的后台统计分析用途有额外限制，须在启用数据同步前完成用途书面确认。

## 自动采集适配器契约

Worker 每 5 分钟为启用账号请求：

`GET {DATA_SOURCE_URL}/accounts/{platform_open_id}/metrics`

设置 `DATA_SOURCE_TOKEN` 后会通过 Bearer Token 传递。适配器必须返回：

```json
{
  "account_snapshot": {
    "follower_count": 1200,
    "collected_at": "2026-08-05T08:00:00Z",
    "source": "douyin_api"
  },
  "videos": [{
    "platform_item_id": "video_001",
    "title": "作品标题",
    "published_at": "2026-08-01T08:00:00Z",
    "play_count": 1000,
    "like_count": 80,
    "comment_count": 10,
    "forward_count": 5,
    "completion_rate": 0.42,
    "video_follow_conversion": 0.02,
    "collected_at": "2026-08-05T08:00:00Z",
    "source": "douyin_api"
  }]
}
```

允许的来源为 `douyin_api`、`computer_use`、`authorized_import`、`contract_api` 和 `controlled_crawler`。系统只追加通过校验的快照；没有获批准的数据源时任务明确显示为 `partial`，不会用估算值填充验收字段。

## 验证

```powershell
cd frontend; npm.cmd run build
docker compose run --rm api pytest
```
