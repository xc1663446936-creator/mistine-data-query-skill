#!/bin/sh
set -eu

repo_url="https://github.com/xc1663446936-creator/mistine-data-query-skill.git"
repo_dir="$HOME/.local/share/mistine-data-query-skill"

command -v git >/dev/null 2>&1 || { echo "Git is required." >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required." >&2; exit 1; }
command -v rsync >/dev/null 2>&1 || { echo "rsync is required." >&2; exit 1; }

mkdir -p "$(dirname "$repo_dir")"
if [ -d "$repo_dir/.git" ]; then
  git -C "$repo_dir" remote set-url origin "$repo_url"
  git -C "$repo_dir" pull --ff-only
elif [ -e "$repo_dir" ]; then
  echo "Cannot install: $repo_dir exists but is not the Skill repository." >&2
  exit 1
else
  git clone --depth 1 "$repo_url" "$repo_dir"
fi

"$repo_dir/install.sh" workbuddy

echo
echo "MISTINE Data Query is ready in WorkBuddy."
echo "GitHub login is not required. Future updates are enabled automatically."
