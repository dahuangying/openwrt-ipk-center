#!/bin/bash
# scripts/utils.sh
# 通用工具函数：架构识别 & 清理旧版本

set -e

# get_arch: 根据 IPK 文件名判断所属平台
get_arch() {
  local filename="$1"
  if [[ "$filename" =~ (aarch64_cortex-a53|aarch64|arm64) ]]; then
    echo "aarch64_cortex-a53"
  elif [[ "$filename" =~ (x86_64|amd64) ]]; then
    echo "x86_64"
  else
    echo "other"
  fi
}

# cleanup_old_versions: 删除旧版本，只保留指定数量
# $1: 插件下载目录  $2: 保留数量
cleanup_old_versions() {
  local dir="$1"
  local keep_num=$2

  # 获取版本子目录，按名称倒序（假设 tag_name 递增）
  local versions=($(ls -1 "$dir" | sort -r))
  local count=0

  for version in "${versions[@]}"; do
    count=$((count + 1))
    if [ $count -gt $keep_num ]; then
      echo "[INFO] Removing old version: $version"
      rm -rf "$dir/$version"
    fi
  done
}
