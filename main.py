#!/usr/bin/env python3
import os
import sys
import json
import shutil
import requests
from pathlib import Path
from time import sleep

# 配置文件路径，可自行修改
CONFIG_FILE = "config.json"
DOWNLOAD_DIR = Path("downloads")
RETRY_LIMIT = 3  # 下载失败重试次数

def log(msg):
    print(f"[INFO] {msg}")

def log_ok(msg):
    print(f"[OK] {msg}")

def log_error(msg):
    print(f"[ERROR] {msg}")

def log_clean(msg):
    print(f"[CLEAN] {msg}")

def is_stable_version(tag_name: str) -> bool:
    """判断版本是否稳定，过滤beta/rc/alpha/test/dev等不稳定版本"""
    unstable_keywords = ['beta', 'rc', 'alpha', 'test', 'dev']
    tag_lower = tag_name.lower()
    return not any(k in tag_lower for k in unstable_keywords)

def get_releases(repo):
    """调用GitHub API获取release信息"""
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        log_error(f"获取 {repo} 的releases失败: {e}")
        return []

def download_asset(url, save_path):
    """下载单个release文件，支持重试"""
    attempt = 0
    while attempt < RETRY_LIMIT:
        try:
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                save_path.parent.mkdir(parents=True, exist_ok=True)
                with open(save_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                log_ok(f"下载完成: {save_path}")
                return True
            else:
                log_error(f"下载失败（状态码 {r.status_code}）: {url}")
                return False
        except requests.exceptions.RequestException as e:
            attempt += 1
            log_error(f"下载失败，第{attempt}次重试: {url}")
            sleep(2)
    log_error(f"重试{RETRY_LIMIT}次后依然失败: {url}")
    return False

def clean_old_versions(path: Path, keep=3):
    """保留最新keep个版本，删除旧版本文件夹"""
    if not path.exists():
        return
    versions = [d for d in path.iterdir() if d.is_dir()]
    # 按修改时间倒序排序
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    for old_dir in versions[keep:]:
        log_clean(f"删除旧版本: {old_dir}")
        shutil.rmtree(old_dir)

def sync_plugin(plugin):
    log(f"开始同步插件 {plugin['name']} ...")

    releases = get_releases(plugin['repo'])
    if not releases:
        log_error(f"{plugin['name']} 没有找到release。")
        return

    # 过滤稳定版本并按发布时间倒序排序
    stable_releases = [r for r in releases if is_stable_version(r['tag_name'])]
    stable_releases.sort(key=lambda r: r['published_at'], reverse=True)

    new_files_count = 0

    for release in stable_releases:
        tag = release['tag_name']
        log(f"处理版本 {tag} ...")

        for asset in release.get('assets', []):
            asset_name = asset['name']
            download_url = asset['browser_download_url']

            for platform in plugin['platforms']:
                if platform in asset_name:
                    save_dir = DOWNLOAD_DIR / platform / plugin['name'] / tag
                    save_path = save_dir / asset_name

                    if save_path.exists():
                        log_ok(f"已存在，无需下载: {save_path}")
                        continue

                    if download_asset(download_url, save_path):
                        new_files_count += 1

    # 每个平台保留最新3个版本，清理旧版本
    for platform in plugin['platforms']:
        clean_old_versions(DOWNLOAD_DIR / platform / plugin['name'], keep=3)

    log(f"{plugin['name']} 同步完成，共下载新文件 {new_files_count} 个。")

def main():
    if not os.path.isfile(CONFIG_FILE):
        log_error(f"配置文件 {CONFIG_FILE} 不存在！")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            log_error(f"解析配置文件失败: {e}")
            sys.exit(1)

    plugins = config.get("plugins", [])
    if not plugins:
        log_error("配置文件中未找到任何插件信息。")
        return

    log("开始同步所有插件...")
    for plugin in plugins:
        sync_plugin(plugin)
    log("所有插件同步完成。")

if __name__ == "__main__":
    main()

