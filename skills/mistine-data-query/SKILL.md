---
name: mistine-data-query
description: 通过公司只读 API 查询 MISTINE 微信豆、ADQ 和云视频管家数据，支持按日期、直播间、账户、计划、素材、上传人及映射关系筛选、排行和导出；不用于执行任意 SQL、抓取网页或修改生产数据。
---

# MISTINE 统一数据查询

使用 `scripts/mistine_data_query.py` 调用公司的只读查询 API。数据库、平台登录凭证和 SSH 均留在服务器；客户端只保存个人 API Key。

## 首次配置

```bash
python3 scripts/mistine_data_query.py setup --api-url https://管理员提供的地址
python3 scripts/mistine_data_query.py status
```

密钥通过隐藏输入读取，保存于 `~/.config/mistine-data-query/config.json`，权限为 `600`。禁止在回答、日志、截图、命令参数或 Git 仓库中回显密钥。

## 查询入口

```bash
python3 scripts/mistine_data_query.py weixin-materials --date yesterday --room 小粉帽 --min-cost 500 --sort cost
python3 scripts/mistine_data_query.py adq-videos --start 2026-09-01 --end 2026-09-07 --account 123 --sort cost
python3 scripts/mistine_data_query.py adq-adgroups --date yesterday --room MISTINE蜜丝婷防晒护肤店
python3 scripts/mistine_data_query.py adq-accounts --date yesterday
python3 scripts/mistine_data_query.py cloud-videos --uploaded-start 2026-09-01 --uploader 申丹丹 --not-deleted
python3 scripts/mistine_data_query.py mapping --adq-video-id 123456789
```

所有相对日期按北京时间解释。默认最多返回 100 行，服务端硬上限 5,000 行、单次日期范围 366 天。需要完整字段说明时读取 [references/queries.md](references/queries.md)。

## 输出要求

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

`status` 会比较本地与服务端推荐版本。运行 `update` 可从安装时记录的 Git 仓库执行 `git pull --ff-only` 后重装；`auto-update on` 可选择每天检查一次。更新失败时保留旧版本并报告原因。

