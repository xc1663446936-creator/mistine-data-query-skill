#!/bin/sh
set -eu

repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
mode=${1:-workbuddy}

case "$mode" in
  codex) target="${CODEX_HOME:-"$HOME/.codex"}/skills/mistine-data-query" ;;
  workbuddy) target="$HOME/.workbuddy/skills/mistine-data-query" ;;
  --target)
    [ "$#" -eq 2 ] || { echo "Usage: $0 [codex|workbuddy|--target PATH]" >&2; exit 2; }
    target=$2
    ;;
  *) echo "Usage: $0 [codex|workbuddy|--target PATH]" >&2; exit 2 ;;
esac

mkdir -p "$target"
rsync -a --delete --exclude '__pycache__' "$repo_dir/skills/mistine-data-query/" "$target/"
chmod 755 "$target/scripts/mistine_data_query.py"
chmod 755 "$target/scripts/shop_order_query.py"
# Retire only the exact standalone 0.1.0 SKILL.md shipped by this repository.
# Keep all files recoverable; never touch a locally edited legacy skill.
python3 - "$target" <<'PY'
import hashlib
import pathlib
import sys

legacy = pathlib.Path(sys.argv[1]).parent / "weixin-shop-order-query" / "SKILL.md"
if legacy.is_file():
    digest = hashlib.sha256(legacy.read_bytes()).hexdigest()
    if digest == "0768cde700b02d148513b46c6b568fbfbe84163e601a90312326fa088744c3e0":
        legacy.rename(legacy.with_name("SKILL.md.retired"))
        print(f"Retired legacy standalone skill: {legacy.parent}")
    else:
        print(f"Preserved modified standalone skill: {legacy.parent}")
PY
python3 "$target/scripts/mistine_data_query.py" set-repo --path "$repo_dir" --target "$target" >/dev/null
if [ "$mode" = "workbuddy" ]; then
  python3 "$target/scripts/mistine_data_query.py" auto-update on >/dev/null
fi
echo "Installed: $target"
if [ "$mode" = "workbuddy" ]; then
  echo "Automatic updates: enabled (checked before every use)"
fi
echo "Existing API configuration: preserved"
echo "If this is the first install, ask WorkBuddy to configure the API address and personal key."
