# MISTINE 数据查询 Skill

面向已授权同事的只读查询客户端，支持微信豆、ADQ 和云视频管家。数据访问由管理员按姓名签发的 API Key 控制；本仓库不包含数据库、平台凭证、服务器代码或任何 API Key。

## Codex 安装

```bash
git clone https://github.com/xc1663446936-creator/mistine-data-query-skill.git
cd mistine-data-query-skill
./install.sh codex
```

## WorkBuddy 安装

```bash
git clone https://github.com/xc1663446936-creator/mistine-data-query-skill.git
cd mistine-data-query-skill
./install.sh workbuddy
```

安装后配置管理员单独提供的 HTTPS API 地址和个人密钥：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py setup \
  --api-url https://<管理员提供的查询地址>
```

密钥输入不会回显，本机配置文件权限为 `600`。不要把密钥发送到群聊、提交到 Git，或写进自动化脚本。

## 更新

手动更新：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py update
```

选择每日自动检查：

```bash
python3 ~/.workbuddy/skills/mistine-data-query/scripts/mistine_data_query.py auto-update on
```

自动更新使用公开 GitHub 仓库，无需 GitHub 登录。更新使用 `git pull --ff-only`，失败时保留当前版本。

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

