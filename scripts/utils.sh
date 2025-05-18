#!/bin/bash
# utils.sh - 工具函数及配置文件

# GitHub API 请求函数，自动添加Accept头，返回json
gh_api() {
    local url="$1"
    curl -s -H "Accept: application/vnd.github+json" "$url"
}

# 统一的下载根目录，所有插件统一存放于此
DOWNLOAD_DIR="downloads"

# 日志输出辅助函数，带时间戳和等级标识
log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_warn() {
    echo "[WARN] $(date '+%Y-%m-%d %H:%M:%S') $*"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') $*" >&2
}

# 判断命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 确保依赖环境，缺失则打印提示
check_dependencies() {
    local deps=("curl" "jq" "tar" "find" "date" "mkdir" "rm" "cp")
    for cmd in "${deps[@]}"; do
        if ! command_exists "$cmd"; then
            log_error "缺少必要命令：$cmd ，请先安装。"
            exit 1
        fi
    done
}

# 运行前检查环境
check_dependencies

