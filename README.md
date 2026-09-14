# MISTINE 数据查询 Skill

面向已授权同事的只读查询客户端，支持微信豆、ADQ 和云视频管家。数据访问由管理员按姓名签发的 API Key 控制；本仓库不包含数据库、平台凭证、服务器代码或任何 API Key。

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

如需关闭：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py auto-update off
```

## 查询示例

```bash
CLI=~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py
python3 "$CLI" status
python3 "$CLI" weixin-materials --date yesterday --room 小粉帽 --min-cost 500
python3 "$CLI" adq-accounts --date yesterday --limit 20
python3 "$CLI" adq-adgroups --date yesterday --room MISTINE蜜丝婷防晒护肤店
python3 "$CLI" adq-videos --start 2026-09-01 --end 2026-09-07 --sort cost
python3 "$CLI" cloud-videos --uploader 申丹丹 --not-deleted
```

查询服务只提供固定只读接口，不接受任意 SQL，也不能修改广告、素材或数据库。
