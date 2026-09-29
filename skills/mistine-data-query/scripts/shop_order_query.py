#!/usr/bin/env python3
"""Read-only, bounded MISTINE WeChat Shop order summaries."""

import argparse
import datetime as dt
import json
import pathlib
import re
import shlex
import sqlite3
import subprocess
import sys
from zoneinfo import ZoneInfo


LOCAL_DB = pathlib.Path("/Users/xuchao/Desktop/蜜丝婷工作文档/订单数据分析/database/微信小店订单.sqlite3")
REMOTE_DB = pathlib.Path("/data/weixin-shop-order-backup/微信小店订单.sqlite3")
REMOTE_MANIFEST = pathlib.Path("/data/weixin-shop-order-backup/manifest.json")
REMOTE_HOST = "xsc@172.18.3.55"
TIMEZONE = ZoneInfo("Asia/Shanghai")
SCOPE_CHANNELS = {"自播": ("关联账号", "自然成交"), "达播": ("达人带货", "机构推广")}
CHANNELS = set(SCOPE_CHANNELS["自播"] + SCOPE_CHANNELS["达播"])
SHOPS = {"底彩店", "防晒店"}
GRAINS = {
    "summary": (),
    "byday": ("pay_date",),
    "bymonth": ("pay_month",),
    "shop": ("shop_name",),
    "live_room": ("shop_name", "CASE WHEN sale_channel = '自然成交' AND COALESCE(account_nickname, '') = '' THEN '直播溢出成交' ELSE COALESCE(NULLIF(account_nickname, ''), '未识别账号') END AS live_room", "sale_channel"),
    "channel": ("project_scope", "sale_channel"),
    "product": ("shop_name", "product_id", "product_code", "product_name"),
    "sku": ("shop_name", "product_id", "platform_sku_id", "sku_code", "product_attributes"),
    "refund_reason": ("COALESCE(NULLIF(aftersale_reason, ''), '未标注') AS refund_reason",),
}
SORTS = {"gmv", "gsv", "refund_amount", "order_count", "sales_quantity"}


def parse_day(value):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("日期必须是 YYYY-MM-DD")
    return dt.date.fromisoformat(value)


def period(args):
    if args.date:
        day = dt.datetime.now(TIMEZONE).date() - dt.timedelta(days=1) if args.date == "yesterday" else (
            dt.datetime.now(TIMEZONE).date() if args.date == "today" else parse_day(args.date)
        )
        start, end = day, day
    else:
        if not args.start or not args.end:
            raise ValueError("query 必须同时指定 --start 和 --end，或使用 --date")
        start, end = parse_day(args.start), parse_day(args.end)
    if end < start:
        raise ValueError("结束日不能早于开始日")
    if (end - start).days > 366:
        raise ValueError("单次最多查询 367 个自然日；请按月分段")
    return start.isoformat() + " 00:00:00", (end + dt.timedelta(days=1)).isoformat() + " 00:00:00"


def connect_ro(path):
    if not path.is_file():
        raise FileNotFoundError(str(path))
    connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only=ON")
    connection.execute("PRAGMA busy_timeout=30000")
    required = {"import_runs", "orders", "v_order_item_metrics"}
    actual = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE name IN ('import_runs','orders','v_order_item_metrics')")}
    if not required <= actual:
        connection.close()
        raise ValueError("数据库缺少必需的订单表或视图，不能作为订单库使用")
    return connection


def freshness(connection, source, strict=True):
    row = connection.execute("SELECT run_id, started_at, finished_at, command, status, error_count FROM import_runs ORDER BY run_id DESC LIMIT 1").fetchone()
    if row is None:
        raise ValueError("没有入库批次，无法确认数据新鲜度")
    run = dict(row)
    healthy = run["status"] == "SUCCESS" and run["error_count"] == 0 and bool(run["finished_at"])
    if strict and not healthy:
        raise ValueError("最新入库批次不是无错误的 SUCCESS；停止输出业务数据：" + json.dumps(run, ensure_ascii=False))
    latest_pay_time = connection.execute("SELECT MAX(pay_time) FROM orders").fetchone()[0]
    result = {"source": source, "database": str(REMOTE_DB if source == "remote_backup" else LOCAL_DB), "latest_import_run": run, "latest_import_healthy": healthy, "latest_pay_time": latest_pay_time}
    if source == "remote_backup":
        manifest = json.loads(REMOTE_MANIFEST.read_text(encoding="utf-8"))
        manifest_healthy = (manifest.get("latest_import_run_id") == run["run_id"] and manifest.get("latest_import_status") == "SUCCESS"
                            and manifest.get("latest_import_error_count") == 0 and bool(manifest.get("sha256")) and bool(manifest.get("synced_at")))
        if strict and not manifest_healthy:
            raise ValueError("远程 manifest 与数据库最新成功批次不一致，停止查询")
        result["backup_synced_at"] = manifest.get("synced_at")
        result["backup_sha256"] = manifest.get("sha256")
        result["manifest_healthy"] = manifest_healthy
    return result


def build_query(args, start_at, end_exclusive):
    fields = GRAINS[args.grain]
    select = list(fields) + [
        "ROUND(COALESCE(SUM(gmv),0),2) AS gmv",
        "ROUND(COALESCE(SUM(refund_amount),0),2) AS refund_amount",
        "ROUND(COALESCE(SUM(gsv),0),2) AS gsv",
        "CASE WHEN COALESCE(SUM(gmv),0)=0 THEN NULL ELSE ROUND(SUM(refund_amount)/SUM(gmv),6) END AS refund_rate",
        "COUNT(DISTINCT shop_name || ':' || order_id) AS order_count",
        "COALESCE(SUM(quantity),0) AS sales_quantity",
        "COUNT(*) AS item_count",
    ]
    where = ["pay_time >= ?", "pay_time < ?"]
    params = [start_at, end_exclusive]
    if args.scope in SCOPE_CHANNELS:
        where += ["project_scope = ?", "sale_channel IN (?,?)"]
        params += [args.scope, *SCOPE_CHANNELS[args.scope]]
    if args.channel:
        if args.scope in SCOPE_CHANNELS and args.channel not in SCOPE_CHANNELS[args.scope]:
            raise ValueError("成交来源与自播/达播范围冲突")
        where.append("sale_channel = ?")
        params.append(args.channel)
    if args.shop:
        where.append("shop_name = ?")
        params.append(args.shop)
    if args.product_id:
        where.append("product_id = ?")
        params.append(args.product_id)
    if args.sku_code:
        where.append("sku_code = ?")
        params.append(args.sku_code)
    if args.account:
        where.append("account_nickname = ?")
        params.append(args.account)
    if args.grain == "refund_reason":
        where.append("refund_amount > 0")
    sql = "SELECT " + ", ".join(select) + " FROM v_order_item_metrics WHERE " + " AND ".join(where)
    if fields:
        # Every dimension expression is a fixed constant, never user-provided SQL.
        sql += " GROUP BY " + ", ".join(str(i) for i in range(1, len(fields) + 1))
        sql += " ORDER BY " + (fields[0] + " ASC" if args.grain in ("byday", "bymonth") else args.sort + " DESC")
        sql += " LIMIT ?"
        params.append(args.limit + 1)
    return sql, params


def local_run(args, source):
    path = REMOTE_DB if source == "remote_backup" else pathlib.Path(args.db_path).expanduser()
    connection = connect_ro(path)
    try:
        meta = freshness(connection, source, strict=args.command == "query")
        meta["database"] = str(path)
        meta["timezone"] = "Asia/Shanghai"
        if args.command == "status":
            warnings = []
            if not meta["latest_import_healthy"]:
                warnings.append("最新入库批次不干净，不应将业务数据称为最新完整数据")
            if source == "remote_backup" and not meta["manifest_healthy"]:
                warnings.append("远程 manifest 与数据库批次不一致")
            if source == "remote_backup" and args.expected_min_run and meta["latest_import_run"]["run_id"] < args.expected_min_run:
                warnings.append("服务器备份批次落后于本地主库")
            meta["warnings"] = warnings
            return {"ok": True, **meta}
        start_at, end_exclusive = period(args)
        sql, params = build_query(args, start_at, end_exclusive)
        rows = [dict(row) for row in connection.execute(sql, params)]
        truncated = args.grain != "summary" and len(rows) > args.limit
        rows = rows[:args.limit]
        warnings = []
        requested_end = (dt.date.fromisoformat(end_exclusive[:10]) - dt.timedelta(days=1)).isoformat()
        if not meta["latest_pay_time"] or requested_end > meta["latest_pay_time"][:10]:
            warnings.append("所选时间段超过库中最新付款日期；末尾日期可能尚未入库")
        if source == "remote_backup" and args.expected_min_run and meta["latest_import_run"]["run_id"] < args.expected_min_run:
            warnings.append("服务器备份批次落后于本地主库，不可作为最新数据")
        return {
            "ok": True, **meta, "start_at": start_at, "end_exclusive": end_exclusive,
            "grain": args.grain, "project_scope": args.scope,
            "sale_channels": list(SCOPE_CHANNELS[args.scope]) if args.scope in SCOPE_CHANNELS else "全部已入库来源",
            "filters": {k: v for k, v in {"shop": args.shop, "channel": args.channel, "product_id": args.product_id, "sku_code": args.sku_code, "account_nickname": args.account}.items() if v},
            "amount_unit": "CNY yuan", "refund_basis": "latest_successful_aftersale_amount_at_query_time",
            "row_count": len(rows), "truncated": truncated, "warnings": warnings, "data": rows,
        }
    finally:
        connection.close()


def remote_run(args):
    # Execute this installed, audited script on the server via stdin; no remote files are written.
    argv = ["python3", "-", "--remote-exec", args.command]
    if args.command == "query":
        argv += ["--start", args.start, "--end", args.end] if not args.date else ["--date", args.date]
        argv += ["--scope", args.scope, "--grain", args.grain, "--sort", args.sort, "--limit", str(args.limit)]
        for flag, value in (("--shop", args.shop), ("--channel", args.channel), ("--product-id", args.product_id), ("--sku-code", args.sku_code), ("--account", args.account)):
            if value:
                argv += [flag, value]
    if args.expected_min_run:
        argv += ["--expected-min-run", str(args.expected_min_run)]
    command = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "IdentitiesOnly=yes"]
    if args.ssh_identity:
        command += ["-i", args.ssh_identity]
    command += [REMOTE_HOST, shlex.join(argv)]
    completed = subprocess.run(command, input=pathlib.Path(__file__).read_text(encoding="utf-8"), text=True, capture_output=True, timeout=90)
    if completed.returncode:
        raise RuntimeError("服务器只读查询失败；检查内网/VPN、SSH 授权与远程数据库。" + (" 远端错误：" + completed.stderr.strip()[-500:] if completed.stderr.strip() else ""))
    return json.loads(completed.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote-exec", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--expected-min-run", type=int, default=0, help=argparse.SUPPRESS)
    parser.add_argument("command", choices=("status", "query"))
    parser.add_argument("--source", choices=("auto", "local", "remote"), default="auto")
    parser.add_argument("--db-path", default=str(LOCAL_DB))
    parser.add_argument("--ssh-identity", help="已有 SSH 私钥路径，仅在本机使用，不会复制到服务器")
    parser.add_argument("--date", help="YYYY-MM-DD、today 或 yesterday")
    parser.add_argument("--start", help="北京时间开始日期 YYYY-MM-DD")
    parser.add_argument("--end", help="北京时间结束日期 YYYY-MM-DD，含当日")
    parser.add_argument("--scope", choices=("自播", "达播", "全部"), default="全部")
    parser.add_argument("--grain", choices=tuple(GRAINS), default="summary")
    parser.add_argument("--shop", choices=tuple(sorted(SHOPS)))
    parser.add_argument("--channel", choices=tuple(sorted(CHANNELS)))
    parser.add_argument("--product-id")
    parser.add_argument("--sku-code")
    parser.add_argument("--account")
    parser.add_argument("--sort", choices=tuple(sorted(SORTS)), default="gmv")
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.limit <= 5000:
        parser.error("--limit 必须在 1–5000 之间")
    if args.command == "query":
        period(args)
    if args.remote_exec:
        result = local_run(args, "remote_backup")
    elif args.source == "local" or (args.source == "auto" and pathlib.Path(args.db_path).expanduser().is_file()):
        result = local_run(args, "local_primary")
    else:
        if pathlib.Path(args.db_path).expanduser().is_file():
            connection = connect_ro(pathlib.Path(args.db_path).expanduser())
            try:
                args.expected_min_run = freshness(connection, "local_primary")["latest_import_run"]["run_id"]
            finally:
                connection.close()
        result = remote_run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, FileNotFoundError, sqlite3.Error, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)
