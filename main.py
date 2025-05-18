#!/usr/bin/env python3
import os
import re
import sys
import json
import shutil
import requests
from pathlib import Path
from datetime import datetime

# 你自己的配置路径（可修改）
CONFIG_FILE = "config.json"
DOWNLOAD_DIR = Path("downloads")

def log(msg):
    print(f"[INFO] {msg}")

def log_ok(msg):
    print(f"[OK] {msg}")

def log_clean(msg):
    print(f"[CLEAN] {msg}")

def is_stable_version(tag_name: str) -> bool:
    """判断版本是否稳定，过滤beta/rc/test等"""
    unstable_keywords = ['beta', 'rc', 'alpha', 'test', 'dev']
    tag_lower = tag_name.lower()
    return not any(k in tag_lower for k in unstable_keywords)

def get_releases(repo):
    """调用GitHub API获取releases"""
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    r = requests.get(url, headers=headers)
    if r.status_code != 200:
        log(f"Failed to fetch releases for {repo}, status: {r.status_code}")
        return []
    return r.json()

def download_asset(url, save_path):
    """下载release里的单个文件"""
    try:
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
            log_ok(f"Downloaded: {save_path}")
            return True
        else:
            log(f"Download failed: {url}, status {r.status_code}")
            return False
    except Exception as e:
        log(f"Exception during download: {e}")
        return False

def clean_old_versions(path: Path, keep=3):
    """保留最新keep个版本，删除旧版本"""
    if not path.exists():
        return
    versions = [d for d in path.iterdir() if d.is_dir()]
    # 按目录修改时间倒序排列
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    for old_dir in versions[keep:]:
        log_clean(f"Removing old version: {old_dir}")
        shutil.rmtree(old_dir)

def sync_plugin(plugin):
    log(f"Syncing {plugin['name']}...")
    releases = get_releases(plugin['repo'])
    if not releases:
        log(f"No releases found for {plugin['name']}.")
        return

    # 过滤稳定版本并按发布时间倒序排序
    stable_releases = [r for r in releases if is_stable_version(r['tag_name'])]
    stable_releases.sort(key=lambda r: r['published_at'], reverse=True)

    new_files_count = 0

    for release in stable_releases:
        tag = release['tag_name']
        published_at = release['published_at']
        log(f"Processing {tag} ...")

        for asset in release.get('assets', []):
            # 只下载zip文件，且名字包含平台信息（示例匹配）
            asset_name = asset['name']
            download_url = asset['browser_download_url']

            for platform in plugin['platforms']:
                if platform in asset_name:
                    # 保存路径：downloads/<platform>/<plugin>/<version>/<asset_name>
                    save_dir = DOWNLOAD_DIR / platform / plugin['name'] / tag
                    save_path = save_dir / asset_name

                    if save_path.exists():
                        log_ok(f"Already downloaded: {save_path}")
                        continue

                    success = download_asset(download_url, save_path)
                    if success:
                        new_files_count += 1

    # 每个平台清理旧版本，保留3个
    for platform in plugin['platforms']:
        clean_old_versions(DOWNLOAD_DIR / platform / plugin['name'], keep=3)

    log(f"{plugin['name']} sync completed. {new_files_count} new files.")

def main():
    if not os.path.isfile(CONFIG_FILE):
        log(f"Config file {CONFIG_FILE} not found!")
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    plugins = config.get("plugins", [])
    if not plugins:
        log("No plugins configured.")
        return

    log("Starting all plugin sync...")
    for plugin in plugins:
        sync_plugin(plugin)
    log("All plugin sync completed.")

if __name__ == "__main__":
    main()
