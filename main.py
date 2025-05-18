#!/usr/bin/env python3
import os
import re
import sys
import json
import shutil
import requests
import subprocess
from pathlib import Path

# 配置
CONFIG_FILE = "config.json"
ARCHIVE_DIR = Path("docs/archive")
OPKG_DIR = Path("docs/opkg")

def log(msg): print(f"[INFO] {msg}")
def log_ok(msg): print(f"[OK] {msg}")
def log_clean(msg): print(f"[CLEAN] {msg}")

def is_stable_version(tag_name: str) -> bool:
    unstable_keywords = ['beta', 'rc', 'alpha', 'test', 'dev']
    return not any(k in tag_name.lower() for k in unstable_keywords)

def get_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    headers = {'Accept': 'application/vnd.github.v3+json'}
    r = requests.get(url, headers=headers)
    return r.json() if r.status_code == 200 else []

def download_asset(url, save_path):
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

def clean_old_versions(base_path: Path, keep=10):
    if not base_path.exists(): return
    versions = [d for d in base_path.iterdir() if d.is_dir()]
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    for old_dir in versions[keep:]:
        log_clean(f"Removing old version: {old_dir}")
        shutil.rmtree(old_dir)

def copy_latest_to_opkg(platform_path: Path, opkg_path: Path, keep=3):
    versions = [d for d in platform_path.iterdir() if d.is_dir()]
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    latest = versions[:keep]

    # 清空 opkg path
    if opkg_path.exists():
        shutil.rmtree(opkg_path)
    for version in latest:
        rel_ver = version.name
        target_ver = opkg_path / rel_ver
        shutil.copytree(version, target_ver)

def generate_packages_index(opkg_plugin_path: Path):
    pkg_files = list(opkg_plugin_path.glob("**/*.ipk"))
    if not pkg_files:
        log(f"No IPK files to generate Packages at {opkg_plugin_path}")
        return

    # 执行命令：opkg-utils 下的 'ipkg-make-index'（必须预装）
    try:
        subprocess.run(
            ["ipkg-make-index", "."],
            cwd=opkg_plugin_path,
            check=True,
            stdout=open(opkg_plugin_path / "Packages", "w")
        )
        log_ok(f"Generated Packages: {opkg_plugin_path/'Packages'}")
    except Exception as e:
        log(f"Failed to generate Packages: {e}")

def sync_plugin(plugin):
    log(f"Syncing {plugin['name']}...")
    releases = get_releases(plugin['repo'])
    if not releases:
        log(f"No releases found for {plugin['name']}.")
        return

    stable_releases = [r for r in releases if is_stable_version(r['tag_name'])]
    stable_releases.sort(key=lambda r: r['published_at'], reverse=True)
    new_count = 0

    for release in stable_releases:
        tag = release['tag_name']
        for asset in release.get('assets', []):
            asset_name = asset['name']
            asset_url = asset['browser_download_url']

            for platform in plugin['platforms']:
                if platform in asset_name:
                    archive_dir = ARCHIVE_DIR / platform / plugin['name'] / tag
                    save_path = archive_dir / asset_name
                    if not save_path.exists():
                        if download_asset(asset_url, save_path):
                            new_count += 1

    # 清理 archive 中旧版本（只保留10个）
    for platform in plugin['platforms']:
        clean_old_versions(ARCHIVE_DIR / platform / plugin['name'], keep=10)

        # 复制最新 3 个版本到 opkg 目录
        copy_latest_to_opkg(
            ARCHIVE_DIR / platform / plugin['name'],
            OPKG_DIR / platform / plugin['name'],
            keep=3
        )

        # 生成 Packages 索引
        generate_packages_index(OPKG_DIR / platform / plugin['name'])

    log_ok(f"{plugin['name']} sync completed. {new_count} new files.")

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

    for plugin in plugins:
        sync_plugin(plugin)

if __name__ == "__main__":
    main()


