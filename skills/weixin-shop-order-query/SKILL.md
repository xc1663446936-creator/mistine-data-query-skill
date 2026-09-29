---
name: weixin-shop-order-query
description: 只读查询 MISTINE 微信小店订单数据库的自播、达播 GMV、GSV、退款、订单数和销量；支持按日、店铺、直播间、渠道、商品、SKU 与退款原因拆分，以及核对本地主库和服务器备份的新鲜度。不用于微信豆或 ADQ 广告消耗查询。
---

# 微信小店订单查询

用 `scripts/order_query.py` 查询。优先读本地主库；本机没有库时才自动尝试内网服务器只读备份。没有任意 SQL 或写入接口。首次使用先运行 `status`，再运行有明确日期范围的 `query`。

```bash
python3 scripts/order_query.py status
python3 scripts/order_query.py query --start 2026-09-01 --end 2026-09-28 --scope 自播 --grain byday
python3 scripts/order_query.py query --start 2026-09-01 --end 2026-09-28 --scope 达播 --grain live_room --shop 防晒店 --limit 30
python3 scripts/order_query.py query --start 2026-09-01 --end 2026-09-28 --scope 全部 --grain product --sort gmv --limit 50
```

`--start`、`--end` 是北京时间含首尾的自然日；也可用 `--date yesterday`。`--source local|remote|auto` 默认 `auto`。如本地库路径变更，可用 `--db-path` 指向已校验的本机库；不能用它指定服务器任意文件。服务器查询需要既有 SSH 授权和内网/VPN，脚本不包含密钥。

## 必须遵守的口径

- 销售按付款时间 `pay_time` 归日，只统计有明确付款时间的商品明细。自播 = `project_scope=自播` 且渠道为关联账号/自然成交；达播 = `project_scope=达播` 且渠道为达人带货/机构推广。`全部` 另含其他来源，不要与自播+达播混为一谈。
- GMV、退款、GSV 单位为元。退款率用汇总退款金额 ÷ 汇总 GMV，不能平均行级比率。订单数按店铺+订单 ID 去重，销量为商品数量之和；商品明细行数另列。
- 退款是查询时最新已成功售后金额，历史付款日的 GSV/退款率可能变化。退款原因聚合按付款日，不等于售后完成日；需要后者时先读 [字段与边界](references/data-contract.md)。
- 每次回答写明北京时间绝对日期范围、来源、本地或备份批次、数据截止时间、项目/渠道、金额单位和行数。若最新入库不干净、备份不同步或所需日期超过数据截止，不能声称结果完整或最新。
- 不输出买家、收件人、手机号、地址、原始 JSON、token、私钥。不要让用户的文字变成 SQL 片段。SSH/内网失败是访问问题，不等于数据库损坏。

`status` 和 `query` 都输出机器可读 JSON，包括来源与新鲜度。可用 `--grain bymonth` 看月度汇总。大范围查询可能较慢；按月分段查询，但合并时订单数须对跨段去重（自然日分段互不重叠时可求和）。字段、主备关系和售后边界详见 [字段与边界](references/data-contract.md)。
