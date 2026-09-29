# 订单数据库字段与边界

本机主库默认路径：`/Users/xuchao/Desktop/蜜丝婷工作文档/订单数据分析/database/微信小店订单.sqlite3`。服务器副本：`xsc@172.18.3.55:/data/weixin-shop-order-backup/微信小店订单.sqlite3`，元数据 `manifest.json`。主库事务性入库，备份通常在成功批次后静默 10 分钟才同步；服务器不能当作实时主库。

`v_order_item_metrics` 为已付款订单的商品明细视图，一行是一个商品明细，不是订单。查询列包括 `shop_name`、`order_id`、`pay_time`、`pay_date`、`project_scope`、`sale_channel`、`account_nickname`、`product_id`、`product_code`、`product_name`、`platform_sku_id`、`sku_code`、`product_attributes`、`quantity`、`gmv`、`refund_amount`、`gsv`、`aftersale_reason`。金额列已由分转元。`account_nickname` 为空的自播自然成交在直播间维度显示为“直播溢出成交”。

`orders` 是店铺订单粒度，含买家/收件个人信息，普通分析不要直接输出。`aftersales` 是售后单粒度；成功售后金额映射到订单商品后滚动更新视图中的 `refund_amount`。需要按售后完成日分析时，必须单独读取 `aftersales.complete_time`，不可把订单付款日退款视作当日退款发生额。多个售后单、未成功或已取消售后不能仅凭视图的单个 `aftersale_reason` 完整还原。

报告口径：`GMV=SUM(gmv)`，`退款=SUM(refund_amount)`，`GSV=GMV-退款`，`退款率=退款/GMV`，`订单数=COUNT(DISTINCT shop_name||':'||order_id)`，`销量=SUM(quantity)`。自播渠道为关联账号、自然成交；达播为达人带货、机构推广。`account_type` 不能替代 `project_scope+sale_channel`。不要按商品名模糊匹配替代商品链接 ID。

新鲜度：`import_runs` 最新批次须 `SUCCESS`、`error_count=0`、`finished_at` 非空；远程还需 `manifest.latest_import_run_id` 与 DB 一致，且如本地主库可访问，要比较本地批次和远程批次。备份批次落后时允许明确标注其为历史备份，不可称为最新。`MAX(orders.pay_time)` 是当前库中业务付款时间上界；不等于 API 实时完整性证明。
