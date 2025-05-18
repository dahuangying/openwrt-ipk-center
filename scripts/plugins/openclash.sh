#!/bin/bash
# scripts/plugins/openclash.sh
# 同步 OpenClash 最新稳定版且保留最近10个版本

set -e
source "$(dirname "$0")/../utils.sh"

REPO="vernesong/OpenClash"
PLUGIN="openclash"
DOWNLOAD_DIR="output/$PLUGIN"

mkdir -p "$DOWNLOAD_DIR"
echo "[INFO] Fetching releases from $REPO ..."

releases=$(curl -s "https://api.github.com/repos/$REPO/releases" | jq -r '.[].tag_name')
count=0

for tag in $releases; do
  echo "[INFO] Processing $tag ..."
  tag_dir="$DOWNLOAD_DIR/$tag"
  if [ -d "$tag_dir" ]; then
    echo "[INFO] Already downloaded. Skipping."
    continue
  fi

  mkdir -p "$tag_dir"
  assets_url="https://github.com/$REPO/releases/expanded_assets/$tag"
  page=$(curl -sL "$assets_url")

  links=$(echo "$page" | grep -oE '/[^"\s]+\.ipk' | uniq)
  for link in $links; do
    filename=$(basename "$link")
    arch=$(get_arch "$filename")
    arch_dir="$tag_dir/$arch"
    mkdir -p "$arch_dir"
    echo "[INFO] Downloading $filename to $arch_dir"
    wget -q "https://github.com$link" -O "$arch_dir/$filename"
  done

  count=$((count+1))
  if [ $count -ge 10 ]; then
    break
  fi
done

cleanup_old_versions "$DOWNLOAD_DIR" 10

echo "[INFO] OpenClash sync completed."
