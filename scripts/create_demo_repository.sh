#!/usr/bin/env bash
set -euo pipefail

script_directory=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
project_root=$(cd -- "$script_directory/.." && pwd)
repository_path=${1:-"$project_root/demo-repositories/vulnerable-python-project"}

if [[ -d "$repository_path" ]] && [[ -n "$(find "$repository_path" -mindepth 1 -maxdepth 1 -print -quit)" ]]; then
  printf 'Demo repository is not empty: %s\n' "$repository_path" >&2
  exit 1
fi

mkdir -p "$repository_path"
cp -R "$project_root/fixtures/vulnerable-python-project/." "$repository_path/"
git -C "$repository_path" init -q -b main
git -C "$repository_path" add .
git -C "$repository_path" \
  -c user.name="Dependency Sentinel Demo" \
  -c user.email="demo@example.invalid" \
  commit -qm "Create vulnerable dependency fixture"

printf '%s\n' "$repository_path"
