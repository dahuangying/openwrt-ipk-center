#!/bin/bash
# scripts/main.sh
# 主调度脚本，依次同步所有插件

set -e
SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)

source "$SCRIPT_DIR/utils.sh"

echo "[INFO] Starting all plugin sync..."

plugins=("passwall" "passwall2" "openclash")

for plugin in "${plugins[@]}"; do
  echo "[INFO] Syncing $plugin..."
  bash "$SCRIPT_DIR/plugins/${plugin}.sh"
done

echo "[INFO] All plugin sync completed."
