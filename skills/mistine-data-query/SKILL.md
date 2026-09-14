---
name: mistine-data-query
description: 通过公司只读 API 查询 MISTINE 微信豆、ADQ 和云视频管家数据，支持按日期、直播间、账户、计划、计划素材关系、素材、上传人及映射关系筛选、排行和导出；不用于执行任意 SQL、抓取网页或修改生产数据。
---

# MISTINE 统一数据查询

使用 `scripts/mistine_data_query.py` 调用公司的只读查询 API。数据库、平台登录凭证和 SSH 均留在服务器；客户端只保存个人 API Key。

## 首次配置

```bash
python3 scripts/mistine_data_query.py setup
python3 scripts/mistine_data_query.py status
```

固定入口为 `https://115.159.197.237`，Skill 内置该入口的 CA 证书并执行完整 TLS 校验；只有管理员迁移服务时才需要用 `--api-url` 覆盖。密钥通过隐藏输入读取，保存于 `~/.config/mistine-data-query/config.json`，权限为 `600`。禁止在回答、日志、截图、命令参数或 Git 仓库中回显密钥。

WorkBuddy 安装器会默认开启自动更新。若用户要求安装或升级本 Skill，优先运行公开的一键安装命令；它不需要 GitHub 登录，并会保留已有 API 配置：

```bash
curl -fsSL https://raw.githubusercontent.com/xc1663446936-creator/mistine-data-query-skill/main/install-workbuddy.sh | sh
```

## 查询入口

```bash
python3 scripts/mistine_data_query.py weixin-materials --date yesterday --room 小粉帽 --min-cost 500 --sort cost
python3 scripts/mistine_data_query.py weixin-materials --start 2026-09-01 --end 2026-09-07 --uploader 申丹丹 --sort cost
python3 scripts/mistine_data_query.py weixin-plan-materials --date yesterday --plan-id 1_5241694310_130 --sort cost
python3 scripts/mistine_data_query.py weixin-plan-materials --start 2026-09-01 --end 2026-09-07 --material-id 85102405 --sort cost
python3 scripts/mistine_data_query.py adq-videos --start 2026-09-01 --end 2026-09-07 --account 123 --sort cost
python3 scripts/mistine_data_query.py adq-videos --start 2026-09-01 --end 2026-09-07 --uploader 申丹丹 --sort cost
python3 scripts/mistine_data_query.py adq-adgroups --date yesterday --room MISTINE蜜丝婷防晒护肤店
python3 scripts/mistine_data_query.py adq-accounts --date yesterday
python3 scripts/mistine_data_query.py cloud-videos --uploaded-start 2026-09-01 --uploader 申丹丹 --not-deleted
python3 scripts/mistine_data_query.py mapping --adq-video-id 123456789
```

所有相对日期按北京时间解释。默认最多返回 100 行，服务端硬上限 5,000 行、单次日期范围 366 天。需要完整字段说明时读取 [references/queries.md](references/queries.md)。

## 输出要求

- 人名必须先判定角色。问题出现“视频、素材、上传、作者、谁做的”等素材语境时，默认把人名解释为云视频管家的上传人/视频作者，并用 `--uploader` 经映射查询微信豆或 ADQ 投放事实；不得把该人直接当成投手、账户负责人或平台“创建人”。
- 如果只有人名而没有素材或投放角色语境，且不同解释会改变查询结果，先简短反问：“你指云视频上传人/视频作者，还是投手/账户负责人？”若用户已说“视频作者”或“上传人”，不要重复反问。
- 微信豆 `dim_material` 和 ADQ `video_assets` 已物化云视频上传人、标题、分组、类型及映射状态，普通素材查询直接读取这些维表字段。后台映射表仍是证据源；结果必须保留映射状态，未匹配或候选歧义不得强填，也不得用平台创建人或账户归属代替确定映射。
- `--creator` 仅表示微信豆平台记录的投放创建人，不等于云视频上传人或实际视频作者。
- 微信豆计划维度使用独立的 `weixin-plan-materials` 命令，粒度为“计划 × 素材”（单日查询时即“日期 × 计划 × 素材”）。返回计划 ID、素材 ID/短编码、投放创建人、订单类型、活跃日期、消耗、加权 ROI 和云视频映射。它不能与 `weixin-materials` 明细直接逐行相加，否则会重复计算。
- “素材出现在计划分析结果”只表示该组合产生过平台可返回的数据；要分别报告关系素材数、有播放/曝光素材数和有消耗素材数。完全零曝光、零播放、零消耗的纯配置素材可能不返回，不能据此断言计划没有配置该素材。
- 所有对外金额统一使用人民币“元”。微信豆金额源数据本身是元；ADQ 金额源数据是分，但 CLI 会自动除以 100 后输出元，禁止再次除以 100。`--min-cost` 对微信豆和 ADQ 都按元输入。
- ROI 是无单位倍数，必须用同一币种的汇总 GMV ÷ 汇总消耗重算；CTR、CVR、完播率等比率返回 0–1 小数，只在展示为百分比时乘以 100。计数类字段不得做金额换算。
- 不得用 `空值→0` 或整数取整处理 ROI/CVR。若响应同时给出分子、分母，应按汇总值复算并交叉验证；例如净订单数 1、商品点击数 1 时，净 CVR 是 100%，不是 0。
- 输出表格或文档前先读取响应中的 `units`，抽查至少一条 ADQ 素材的消耗与订单金额。双平台合计只能相加已经统一成元的金额。
- 生成 Excel/WPS 公式时只写一个等号，例如 `=SUM(B2:B10)`；禁止生成 `==SUM(...)`，并在交付前触发重算或检查公式字符串。
- 必须说明数据源、北京时间范围、筛选条件、服务端刷新时间和返回行数。
- 消耗、订单、GMV 可求和；ROI 必须用汇总 GMV ÷ 汇总消耗重算，不能平均每日 ROI。
- 空值和无返回保持为空，不得解释成 0。
- 微信豆、ADQ、云视频素材身份优先通过映射接口核对；标题相似不能冒充确定映射。
- 查询失败、无权限、数据截止落后或部分源不可用时失败关闭，不用缓存冒充最新结果。

## 安全边界

- 只调用固定 API，不直接连接生产数据库，不接受或拼接用户提供的 SQL。
- 查询是只读的；创建、禁用密钥、部署服务、刷新生产库和修改广告不属于普通 Skill 使用范围。
- 个人密钥只授权给指定姓名，可按 `weixin`、`adq`、`cloud` 范围独立控制并记录审计。

## 更新

`status` 会比较本地与服务端推荐版本。运行 `update` 可从安装时记录的公开 Git 仓库执行 `git pull --ff-only` 后重装。WorkBuddy 安装默认启用 `auto-update on`：每次查询或状态检查前都检查更新，不需要独立后台任务。更新失败时保留旧版本并报告原因。
