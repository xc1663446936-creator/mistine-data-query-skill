# 查询口径

## 微信豆

`weixin-materials` 按公开素材编号汇总所选日期的数据，支持直播间、投放创建人（`--creator`）、云视频上传人/视频作者（`--uploader`）、素材编号、订单类型、最低消耗和最低净 ROI。返回消耗、播放、完播、进房、商品曝光与点击、直接/7日归因/净成交、GMV、ROI、CVR 和 CPA。`--uploader` 通过 `material_cloud_video_link` 映射，不把投放创建人当成视频作者。

## ADQ

- `adq-accounts`：账户 × 日期汇总。
- `adq-adgroups`：广告计划 × 日期汇总，并关联计划名称和直播间。
- `adq-videos`：账户 × 素材 × 日期汇总，并关联素材名称、来源类型与云视频映射；支持用 `--uploader` 按云视频当前素材或原创素材上传人筛选。

ADQ 的 `order_roi`、`order_24h_roi`、`first_day_order_roi` 和 `order_net_roi` 口径不同，输出时保留字段名，不混称为同一个 ROI。

## 云视频管家

`cloud-videos` 查询素材主档，支持素材 ID、标题、上传人、分组、类型、上传日期和是否删除。返回原始素材关系、累计千川消耗/成交、内部视频地址及公开地址；地址仅供已授权内部使用。

`mapping` 查询 ADQ 素材与云视频素材的确定/候选映射，可按 ADQ 素材 ID、云视频 ID、账户或上传人筛选，必须保留 `match_status` 和 `match_method`。`matched` 才是确定映射；`ambiguous` 和 `unmatched` 不得并入上传人的确定投放结果。
