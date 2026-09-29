# MISTINE 数据查询 Skill

面向已授权同事的只读查询客户端，包含两个独立 Skill：`mistine-data-query`（微信豆、ADQ、云视频管家，只读 API）和 `weixin-shop-order-query`（微信小店订单，本地主库或内网服务器备份）。本仓库不包含数据库、平台凭证、服务器代码、SSH 私钥或任何 API Key。订单库访问需要本机数据库或已授权的内网 SSH，不由原有 API Key 自动授予。

## WorkBuddy 一键安装（推荐）

```bash
curl -fsSL https://raw.githubusercontent.com/xc1663446936-creator/mistine-data-query-skill/main/install-workbuddy.sh | sh
```

这一条命令会自动完成公开仓库下载、安装到 WorkBuddy、记录更新源并开启自动更新，全程不需要 GitHub 登录。重复执行同一条命令就是一键升级，已有 API 地址和个人密钥会保留。

首次安装后，在 WorkBuddy 中说：

> 配置 MISTINE 数据查询。

WorkBuddy 会使用固定 HTTPS 入口 `https://115.159.197.237` 调用 Skill 的 `setup`，并通过 Skill 内置 CA 证书校验 HTTPS，再通过隐藏输入读取个人 API Key。密钥不会出现在聊天、命令历史或 Git 仓库中。

## Codex 安装

```bash
git clone https://github.com/xc1663446936-creator/mistine-data-query-skill.git
cd mistine-data-query-skill
./install.sh codex
```

安装后配置个人密钥：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py setup
```

密钥输入不会回显，本机配置文件权限为 `600`。不要把密钥发送到群聊、提交到 Git，或写进自动化脚本。

## WorkBuddy 中更新

直接对 WorkBuddy 说“更新 MISTINE 数据查询 Skill”，或执行：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py update
```

WorkBuddy 安装时已经默认开启自动更新。每次查询或状态检查前都会从公开 GitHub 检查更新，失败时继续保留并使用旧版本。无需另装定时器，也无需 GitHub 登录。

查询结果中的金额统一为人民币元：微信豆源数据本身为元，ADQ 源数据虽以分存储，但客户端会自动换算成元，并在响应的 `units` 中明确标注。`--min-cost` 在两个平台也统一按元填写。

如需关闭：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py auto-update off
```

## 查询示例

```bash
CLI=~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py
python3 "$CLI" status
python3 "$CLI" weixin-materials --date yesterday --room 小粉帽 --min-cost 500
python3 "$CLI" weixin-plan-materials --date yesterday --plan-id 1_5241694310_130 --sort cost
python3 "$CLI" adq-accounts --date yesterday --limit 20
python3 "$CLI" adq-adgroups --date yesterday --room MISTINE蜜丝婷防晒护肤店
python3 "$CLI" adq-videos --start 2026-09-01 --end 2026-09-07 --sort cost
python3 "$CLI" cloud-videos --uploader 申丹丹 --not-deleted
```

`weixin-plan-materials` 是独立的“计划 × 素材”查询，可查看每条计划实际返回了哪些素材及其消耗、加权 ROI、创建人和云视频映射。完全零曝光、零播放、零消耗的纯配置素材可能不会被分析接口返回，因此“进入计划”和“实际产生投放数据”需要分开判断。

查询服务只提供固定只读接口，不接受任意 SQL，也不能修改广告、素材或数据库。

## 微信小店订单查询

安装器会同时安装 `weixin-shop-order-query`。它与微信豆广告消耗不是同一数据源，查询已付款订单的 GMV、GSV、滚动退款、订单数和销量：

```bash
python3 ~/.workbuddy/skills/weixin-shop-order-query/scripts/order_query.py status
python3 ~/.workbuddy/skills/weixin-shop-order-query/scripts/order_query.py query --start 2026-09-01 --end 2026-09-28 --scope 自播 --grain byday
```

在 Codex 中安装时，对应路径是 `~/.codex/skills/weixin-shop-order-query/`。默认先读本机主库；本机没有数据库时才尝试公司内网服务器只读备份。明确要求服务器时使用 `--source remote`，需要既有 SSH 授权和内网/VPN。查询必须有日期边界，不提供任意 SQL，也不输出买家/收件信息。细节见 [订单查询 Skill](skills/weixin-shop-order-query/SKILL.md)。
