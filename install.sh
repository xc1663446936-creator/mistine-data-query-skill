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
python3 "$target/scripts/mistine_data_query.py" set-repo --path "$repo_dir" --target "$target" >/dev/null
if [ "$mode" = "workbuddy" ]; then
  python3 "$target/scripts/mistine_data_query.py" auto-update on >/dev/null
fi
echo "Installed: $target"
if [ "$mode" = "workbuddy" ]; then
  echo "Automatic updates: enabled (checked at most once every 24 hours when used)"
fi
echo "Existing API configuration: preserved"
echo "If this is the first install, ask WorkBuddy to configure the API address and personal key."
