# 抖音数据接入技术确认（2026-08-05）

## 结论

当前代码已经具备可审计的采集适配器、快照存储、历史回溯和验收门禁；但不能在未完成平台授权与合规审批前，把真实抖音矩阵数据采集标记为上线完成。

官方资料显示，播放、点赞、评论、分享和账号粉丝等字段在特定授权能力下可获得；但不同接口的应用类型、授权关系、时间窗口和使用场景不同。尤其“用户互动数据”能力声明不得用于开发数据服务类型应用或进行平台统计分析。因此，本项目的“统一矩阵统计”用途必须先获得抖音的书面确认，或采用具有该用途授权的合同数据提供方。

## 字段可用性

| 验收字段 | 已确认的官方能力 | 关键限制 | 当前决定 |
|---|---|---|---|
| 播放、点赞、评论、分享 | 授权用户视频数据/互动数据 | 需权限申请和用户授权；部分能力首次授权后 T+1 才完整 | 可由合规适配器映射 |
| 粉丝总数、每日新增粉丝 | 用户互动数据 | 授权与用途限制 | 仅在书面确认后启用 |
| 完播率 | 短视频详细数据、短视频挂载小程序数据分析 | 主要限自挂载/达人挂载场景；近 90 天、T+1、当日不可查 | 不能作为通用矩阵账号的已确认字段 |
| 转发 | 需将供应方的“share”口径映射为转发口径 | 字段口径须由供应方书面确认 | 未确认前不通过覆盖门禁 |
| 视频级涨粉转化 | 未在本次核验资料中确认通用接口 | 诊断 `HIGH_PLAY_LOW_FOLLOW` 不能伪造输入 | 由合规数据源提供，否则不触发该规则 |

## 配额与频率

- 官方页面对部分接口只说明“串行调用、并发过高可能触发限流”，且错误码包含 `quota 已用完`；未给出适用于本项目的通用每分钟/每日额度。
- 适配器的默认调度为 5 分钟一次，但这是系统侧安全默认值，不是平台已批准配额。上线前应从抖音控制台或合同中填入账号数、接口日额度、瞬时并发、429 `Retry-After` 规则，并完成压测。
- 完播率相关离线接口仅支持昨天以前、近 90 天数据；因此日看板须标记 T+1 新鲜度，不能承诺当天实时完播率。

## 上线前必须取得的外部输入

1. 抖音对“内部多账号运营统计”用途的书面许可，或合规合作数据服务合同。
2. 已审批应用的 App ID、OAuth/经营授权流程、回调域名、权限集与测试账号。
3. 每个验收字段的实际响应样本、数据字典、刷新延迟、配额和限流策略。
4. 若采用 Computer Use 或受控爬虫，需另有平台许可、域名白名单、dry-run、审计与 Kill Switch 审批；不得把它当作绕过官方权限的手段。

在这些材料具备之前，`/api/v1/metrics/coverage` 应保持 `ready_for_acceptance=false`，这是有意的上线保护而非缺陷。

## 已实现的官方 OAuth 接入

系统使用网站应用授权码模式，已经实现以下固定流程：

1. `POST /api/v1/accounts/{account_id}/authorize` 创建十分钟有效、单次使用的 `state`，并生成官方授权页地址：`https://open.douyin.com/platform/oauth/connect/`。
2. 平台回调 `GET /api/v1/integrations/douyin/callback?code=...&state=...`；服务端验证 `state` 后，以 `application/x-www-form-urlencoded` 调用 `https://open.douyin.com/oauth/access_token/`。
3. access token 和 refresh token 仅以加密形式保存；前端和 API 响应不会返回令牌明文。
4. Celery Beat 每小时检查已过期的 access token，调用 `https://open.douyin.com/oauth/refresh_token/` 续期；失败后账号转为 `expired` 并要求重新授权。

待补配置：`DOUYIN_CLIENT_KEY`、`DOUYIN_CLIENT_SECRET`、`DOUYIN_REDIRECT_URI`（必须为控制台登记的 HTTPS 完整回调地址）和已审批的 `DOUYIN_SCOPES`。默认 scope 仅为 `user_info`，不要在未经批准时加入数据类 scope。

### 已实现的经营授权视频同步

配置 `DOUYIN_BUSINESS_ACCESS_TOKEN` 后，Worker 会对已保存 `platform_item_id` 的作品调用 `POST https://open.douyin.com/api/apps/v1/video_bc/query/?open_id=...`，每批最多 20 个 item ID。系统仅映射文档中明确返回的 `play_count`、`digg_count`、`comment_count`、`share_count`、`forward_count`；快照来源为 `douyin_api`、质量等级为 B。该调用不填充完播率或视频级涨粉转化，任务和覆盖门禁会保持 `partial`，直至第二个已批准来源提供这些字段。

## 参考资料

- [用户互动数据](https://developer.open-douyin.com/capacity-center-page/capacity-detail/7180284622729658424)
- [查询特定视频的视频数据](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/basic-abilities/video-id-convert/user-video-data/video-data)
- [短视频详细数据](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/develop/server/operation/data-analysis/video-analysis/video-detail-analysis-data)
- [短视频挂载小程序数据分析](https://developer.open-douyin.com/docs/resource/zh-CN/mini-app/operation/data/data-center/video)
- [抖音获取授权码](https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/douyin-get-permission-code)
- [获取 access_token](https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/get-access-token/)
- [刷新 access_token](https://developer.open-douyin.com/docs/resource/zh-CN/dop/develop/openapi/account-permission/refresh-access-token)
