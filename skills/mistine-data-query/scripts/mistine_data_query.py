#!/usr/bin/env python3
"""Stdlib-only client for the MISTINE read-only data API."""
from __future__ import annotations

import argparse
import datetime as dt
import getpass
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from zoneinfo import ZoneInfo

VERSION = "0.1.2"
CONFIG = Path.home() / ".config/mistine-data-query/config.json"


def load_stored_config() -> dict:
    if CONFIG.exists():
        return json.loads(CONFIG.read_text("utf-8"))
    return {}


def load_config() -> dict:
    data = load_stored_config()
    data["api_url"] = os.getenv("MISTINE_DATA_API_URL", data.get("api_url", ""))
    data["api_token"] = os.getenv("MISTINE_DATA_API_TOKEN", data.get("api_token", ""))
    return data


def save_config(**updates) -> dict:
    data = load_stored_config()
    data.update({k: v for k, v in updates.items() if v is not None})
    if not data.get("api_url"): data.pop("api_url", None)
    if not data.get("api_token"): data.pop("api_token", None)
    CONFIG.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    data.setdefault("device_id", str(uuid.uuid4()))
    fd = os.open(CONFIG, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.chmod(CONFIG, 0o600)
    return data


def request(path: str, params: list[tuple[str, str]] | None = None):
    cfg = load_config()
    if not cfg.get("api_url") or not cfg.get("api_token"):
        raise RuntimeError("尚未配置 API。请先运行 setup。")
    url = cfg["api_url"].rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + cfg["api_token"],
        "X-Device-ID": cfg.get("device_id", "unknown"),
        "User-Agent": f"mistine-data-query/{VERSION}",
    })
    try:
        with urllib.request.urlopen(req, timeout=90) as response:
            return json.loads(response.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"服务返回 HTTP {exc.code}: {body[:800]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"无法连接查询服务: {exc.reason}") from exc


def dates(args) -> list[tuple[str, str]]:
    if not any((getattr(args, "date", None), getattr(args, "start", None), getattr(args, "end", None))):
        return []
    today = dt.datetime.now(ZoneInfo("Asia/Shanghai")).date()
    if args.date:
        value = args.date.lower()
        day = today - dt.timedelta(days=1) if value == "yesterday" else today if value == "today" else dt.date.fromisoformat(value)
        return [("start", day.isoformat()), ("end", day.isoformat())]
    if not args.start or not args.end:
        raise RuntimeError("--start 和 --end 必须同时提供。")
    return [("start", dt.date.fromisoformat(args.start).isoformat()), ("end", dt.date.fromisoformat(args.end).isoformat())]


def common_params(args) -> list[tuple[str, str]]:
    out = dates(args)
    for name in ("account", "room", "creator", "material_id", "adq_video_id", "cloud_video_id", "uploader", "title", "group", "type", "uploaded_start", "uploaded_end"):
        value = getattr(args, name, None)
        if value not in (None, ""):
            out.append((name.replace("_", "-"), str(value)))
    for name in ("min_cost", "min_roi", "sort", "limit"):
        value = getattr(args, name, None)
        if value is not None:
            out.append((name.replace("_", "-"), str(value)))
    if getattr(args, "not_deleted", False):
        out.append(("not-deleted", "1"))
    return out


def add_dates(p):
    p.add_argument("--date", help="YYYY-MM-DD、today 或 yesterday")
    p.add_argument("--start")
    p.add_argument("--end")


def add_metric_query(p):
    add_dates(p)
    p.add_argument("--account")
    p.add_argument("--room")
    p.add_argument("--min-cost", type=float)
    p.add_argument("--min-roi", type=float)
    p.add_argument("--sort", default="cost")
    p.add_argument("--limit", type=int, default=100)


def run_update(force: bool = False) -> dict:
    cfg = load_config()
    repo = Path(cfg.get("repo_dir", "")).expanduser()
    if not repo or not (repo / ".git").exists() or not (repo / "install.sh").exists():
        raise RuntimeError("未记录可更新的 Git 仓库。请从 GitHub clone 后运行仓库内 install.sh。")
    if not force and time.time() - float(cfg.get("last_update_check", 0)) < 86400:
        return {"ok": True, "skipped": True, "reason": "checked_within_24h"}
    pull = subprocess.run(["git", "-C", str(repo), "pull", "--ff-only"], text=True, capture_output=True, timeout=120)
    save_config(last_update_check=int(time.time()))
    if pull.returncode:
        raise RuntimeError("Git 更新失败，旧版本已保留: " + (pull.stderr.strip() or pull.stdout.strip()))
    target = cfg.get("install_target")
    install_cmd = [str(repo / "install.sh")] + (["--target", target] if target else [])
    install = subprocess.run(install_cmd, text=True, capture_output=True, timeout=120)
    if install.returncode:
        raise RuntimeError("仓库已更新但安装失败: " + (install.stderr.strip() or install.stdout.strip()))
    return {"ok": True, "updated": True, "git": pull.stdout.strip(), "install": install.stdout.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description="MISTINE 微信豆、ADQ、云视频只读查询")
    sub = parser.add_subparsers(dest="command", required=True)
    setup = sub.add_parser("setup")
    setup.add_argument("--api-url", required=True)
    setup.add_argument("--token-file", help=argparse.SUPPRESS)
    sub.add_parser("status")
    set_repo = sub.add_parser("set-repo", help="记录安装源（通常由 install.sh 调用）")
    set_repo.add_argument("--path", required=True)
    set_repo.add_argument("--target")
    update = sub.add_parser("update"); update.add_argument("--force", action="store_true")
    auto = sub.add_parser("auto-update"); auto.add_argument("state", choices=["on", "off"])

    wx = sub.add_parser("weixin-materials"); add_metric_query(wx); wx.add_argument("--creator"); wx.add_argument("--material-id")
    for name in ("adq-accounts", "adq-adgroups", "adq-videos"):
        p = sub.add_parser(name); add_metric_query(p)
        if name == "adq-videos": p.add_argument("--adq-video-id")
    cloud = sub.add_parser("cloud-videos")
    cloud.add_argument("--cloud-video-id"); cloud.add_argument("--uploader"); cloud.add_argument("--title"); cloud.add_argument("--group"); cloud.add_argument("--type")
    cloud.add_argument("--uploaded-start"); cloud.add_argument("--uploaded-end"); cloud.add_argument("--not-deleted", action="store_true"); cloud.add_argument("--sort", default="uploaded_at"); cloud.add_argument("--limit", type=int, default=100)
    mapping = sub.add_parser("mapping"); mapping.add_argument("--account"); mapping.add_argument("--adq-video-id"); mapping.add_argument("--cloud-video-id"); mapping.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()

    if args.command == "set-repo":
        target = str(Path(args.target).expanduser().resolve()) if args.target else None
        save_config(repo_dir=str(Path(args.path).expanduser().resolve()), install_target=target)
        return 0
    if args.command == "setup":
        token = Path(args.token_file).read_text("utf-8").strip() if args.token_file else getpass.getpass("个人 API Key（输入不回显）: ").strip()
        if not token: raise RuntimeError("API Key 不能为空。")
        save_config(api_url=args.api_url.rstrip("/"), api_token=token)
        print(json.dumps({"ok": True, "config": str(CONFIG)}, ensure_ascii=False))
        return 0
    if args.command == "auto-update":
        save_config(auto_update=args.state == "on")
        print(json.dumps({"ok": True, "auto_update": args.state == "on"}, ensure_ascii=False))
        return 0
    if args.command == "update":
        print(json.dumps(run_update(force=True), ensure_ascii=False, indent=2)); return 0
    if load_config().get("auto_update"):
        try: run_update()
        except RuntimeError as exc: print(json.dumps({"warning": str(exc)}, ensure_ascii=False), file=sys.stderr)
    if args.command == "status":
        result = request("/health")
        result["local_skill_version"] = VERSION
        result["update_available"] = result.get("skill_version") not in (None, VERSION)
    else:
        paths = {
            "weixin-materials": "/v1/weixin/materials", "adq-accounts": "/v1/adq/accounts",
            "adq-adgroups": "/v1/adq/adgroups", "adq-videos": "/v1/adq/videos",
            "cloud-videos": "/v1/cloud/videos", "mapping": "/v1/mapping",
        }
        result = request(paths[args.command], common_params(args))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try: raise SystemExit(main())
    except (RuntimeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        raise SystemExit(1)
