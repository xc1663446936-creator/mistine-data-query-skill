# 查询口径

## 单位（强制）

| 数据/字段 | 源数据库单位 | CLI 输出及报告单位 |
| --- | --- | --- |
| 微信豆 `cost`、`direct_gmv`、`net_gmv` | 元 | 元 |
| ADQ `cost`、`order_amount`、`order_24h_amount`、`first_day_order_amount`、`order_net_amount`、`order_coupon_amount` | 分 | 元；CLI 已自动除以 100 |
| 云视频 `sum_stat_cost`、`sum_pay_order_amount` | 元 | 元 |
| ROI | 倍数 | 倍数，不加 `%` |
| CTR、CVR、完播率等 rate 字段 | 0–1 小数 | 展示百分比时乘以 100 |
| 曝光、播放、点击、转化、订单数 | 次/人/单 | 原计数，不换算 |

ADQ 查询的 `--min-cost` 也按元填写，CLI 会在请求前转换为源数据库需要的分。CLI 响应会附带 `units`；以它为准，禁止对已归一化的 ADQ 金额再次除以 100。跨平台金额合计前必须确认两边均为元。

校验示例：ADQ 原始 `cost=24219` 分，CLI 应输出 `cost=242.19` 元；若报告仍显示 `24219元`，必须停止交付并修正。ROI 应从统一单位后的汇总金额重算，不能平均明细 ROI。CVR 等比率不得先取整；净订单数 1、商品点击数 1 时净 CVR 为 100%。Excel/WPS 合计公式必须为 `=SUM(...)`，不能是 `==SUM(...)`。

## 微信豆

`weixin-materials` 按公开素材编号汇总所选日期的数据，支持直播间、投放创建人（`--creator`）、云视频上传人/视频作者（`--uploader`）、素材编号、订单类型、最低消耗和最低净 ROI。返回消耗、播放、完播、进房、商品曝光与点击、直接/7日归因/净成交、GMV、ROI、CVR 和 CPA。`--uploader` 直接读取 `dim_material` 中后台物化的云视频字段，不把投放创建人当成视频作者。

### 微信豆计划 × 素材

`weixin-plan-materials` 查询独立的“计划 × 素材”事实，支持 `--plan-id`、`--material-id`、`--creator`、`--uploader`、`--order-class`、最低消耗、最低净 ROI 和日期范围。返回计划 ID、微信豆长素材 ID、可用时的素材短编码/标题、投放创建人、订单类型、活跃天数、累计消耗、按消耗加权的直接/7日归因/净 ROI，以及云视频映射字段。

单日查询粒度是“日期 × 计划 × 素材”；多日查询按计划与素材汇总，ROI 按消耗加权，不能平均每日 ROI。该接口来自分析页返回的数据关系，不是计划配置清单：有播放但零消耗的关系可以返回，完全零曝光、零播放、零消耗的已配置素材可能缺席。汇报时将“进入计划”“产生播放/曝光”“产生消耗”分开，不把进入计划当作实际投放。

## ADQ

- `adq-accounts`：账户 × 日期汇总。
- `adq-adgroups`：广告计划 × 日期汇总，并关联计划名称和直播间。
- `adq-videos`：账户 × 素材 × 日期汇总，直接读取 `video_assets` 中已物化的云视频映射字段；支持用 `--uploader` 按云视频当前素材或原创素材上传人筛选。

ADQ 的 `order_roi`、`order_24h_roi`、`first_day_order_roi` 和 `order_net_roi` 口径不同，输出时保留字段名，不混称为同一个 ROI。

## 云视频管家

`cloud-videos` 查询素材主档，支持素材 ID、标题、上传人、分组、类型、上传日期和是否删除。返回原始素材关系、累计千川消耗/成交、内部视频地址及公开地址；地址仅供已授权内部使用。

`mapping` 查询 ADQ 素材与云视频素材的确定/候选映射，可按 ADQ 素材 ID、云视频 ID、账户或上传人筛选，必须保留 `match_status` 和 `match_method`。`matched` 才是确定映射；`ambiguous` 和 `unmatched` 不得并入上传人的确定投放结果。
