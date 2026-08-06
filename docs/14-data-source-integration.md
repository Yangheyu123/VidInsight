# 数据源全流程接入说明

## 已实现的采集顺序

1. `DATA_SOURCE_URL`：首选。适用于已签约/获准的数据服务；返回完整指标契约后，系统校验、去重并追加历史快照。
2. 抖音 OAuth：每个矩阵账号在界面点击“抖音授权”后，服务端安全保存令牌。授权并获批 `video.list` 后，定时和手动同步会调用官方 `GET https://open.douyin.com/video/list/`，自动发现作品并保存播放、点赞、评论、分享、转发。
3. `COMPUTER_USE_SOURCE_URL`：仅在 `ENABLE_COMPUTER_USE=true`、没有前两类来源可用时启用。它是公司自建且账号所有人明确授权的 Computer Use 工作器桥接，不向 VidInsight 传递密码、Cookie、验证码或代理池。
4. `CONTROLLED_CRAWLER_SOURCE_URL`：最后的可选桥接。须同时打开开关，使用 HTTPS，并将域名写入 `CRAWLER_ALLOWED_DOMAINS`；仅可采集已获平台和账号所有人许可的数据。

系统绝不会虚构完播率、视频级涨粉转化或粉丝增量。官方视频列表本身不包含这三项；需要完整验收字段时，配置一个获准的完整指标服务或桥接工作器。

## 统一数据契约

上述三个桥接地址都由 VidInsight 以如下方式请求：

```text
GET {BASE_URL}/accounts/{platform_open_id}/metrics
Authorization: Bearer {对应的 TOKEN，可选}
```

响应应为 JSON，使用已有的“批量导入”形状：

```json
{
  "account_snapshot": {
    "follower_count": 12000,
    "collected_at": "2026-08-06T10:00:00Z"
  },
  "videos": [
    {
      "platform_item_id": "官方 item_id",
      "title": "作品标题",
      "published_at": "2026-08-01T08:00:00Z",
      "play_count": 10000,
      "like_count": 500,
      "comment_count": 80,
      "share_count": 30,
      "forward_count": 10,
      "completion_rate": 0.42,
      "video_follow_conversion": 0.013,
      "collected_at": "2026-08-06T10:00:00Z"
    }
  ]
}
```

来源标识由 VidInsight 服务端强制写入，桥接端不能伪造来源。相同作品、采集时间和来源会被安全跳过，历史快照不会覆盖。

## 需要配置的变量

```dotenv
# 首选完整数据服务
DATA_SOURCE_URL=https://metrics.example.com/v1
DATA_SOURCE_TOKEN=secret-managed-by-deployment

# 官方抖音 OAuth（默认 scope 现为 user_info,video.list）
DOUYIN_CLIENT_KEY=...
DOUYIN_CLIENT_SECRET=...
DOUYIN_REDIRECT_URI=https://api.example.com/api/v1/integrations/douyin/callback
DOUYIN_SCOPES=user_info,video.list

# 可选：仅限已获授权的 Computer Use 工作器
ENABLE_COMPUTER_USE=true
COMPUTER_USE_SOURCE_URL=https://internal-worker.example.com/v1
COMPUTER_USE_SOURCE_TOKEN=secret-managed-by-deployment

# 可选：最后兜底的受控爬虫工作器
ENABLE_CONTROLLED_CRAWLER=true
CONTROLLED_CRAWLER_SOURCE_URL=https://crawler-worker.example.com/v1
CONTROLLED_CRAWLER_SOURCE_TOKEN=secret-managed-by-deployment
CRAWLER_ALLOWED_DOMAINS=crawler-worker.example.com
```

## 直接使用创作者后台采集器（推荐）

VidInsight 已兼容 [douyin-creator-data-collector](https://github.com/fxl1209739475-fxl/douyin-creator-data-collector) 的 `POST /api/self-data/ingest` 协议。此方式不需要抖音 Client Secret：账号管理者在浏览器中正常登录创作者中心并查看自己的数据，扩展才会将页面已返回的 JSON 上报到 VidInsight。

1. 先在 VidInsight 新建目标账号，复制该账号 UUID；若一个接收器只对应一个账号，写入：

   ```dotenv
   ENABLE_COMPUTER_USE=true
   COMPUTER_USE_INGEST_TOKEN=生成的独立长随机值
   COMPUTER_USE_DEFAULT_ACCOUNT_ID=VidInsight账号UUID
   ```

2. 从项目 Releases 下载扩展并加载到 Chrome/Edge。将扩展的 `manifest.json` 中 `http://localhost:8000/*` 改为你的 VidInsight API 根地址，例如 `https://api.example.com/*`，然后重新加载扩展。
3. 在扩展中填写：系统地址 `https://api.example.com`、上报 token `COMPUTER_USE_INGEST_TOKEN`；只打开“创作者中心”采集。
4. 由账号所有人在可见浏览器中正常登录 `creator.douyin.com`，手动浏览作品分析、数据概览和粉丝数据页面。插件会将真实响应发送至 VidInsight；每个事件保留原始记录及解析状态，可供字段变化时审计和补适配。
5. 在 VidInsight 点击“同步”查看快照、字段覆盖和诊断结果。若页面接口字段未被识别，事件会标为 `unmatched`，不会伪造数字。

多个账号应各自使用一个接收器实例并设置各自的 `COMPUTER_USE_DEFAULT_ACCOUNT_ID`，或在自建桥接层向请求体增加 `account_id`。不要将个人密码、Cookie、短信验证码或浏览器 Profile 提交给 VidInsight 或 Git 仓库。

部署后以内部管理员身份访问：

- `GET /api/v1/integrations/douyin/preflight`：确认 OAuth 配置和字段缺口；
- `GET /api/v1/integrations/sources/preflight`：确认各数据源的开关、桥接和允许域状态；
- 在账号详情中点击“抖音授权”，再点击“同步”。

## 对你提供 GitHub 项目的结论

`xopenapi/douyin-open-api-go` 是生成型 Go SDK，不是数据服务，且仓库未声明许可证。因此本项目不复制或内嵌其代码。它提供的旧接口路径与官方资料相符，但实际实现只以当前抖音官方文档为准。

官方资料：

- [查询授权账号视频列表](https://open.douyin.com/platform/resource/docs/openapi/video-management/douyin/search-video/account-video-list)
- [用户类型及权限说明](https://open.douyin.com/platform/resource/docs/accession-guide/type-and-permission)
- [经营授权视频数据查询](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/user-video-data/videobc)
