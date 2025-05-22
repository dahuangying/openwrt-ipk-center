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
DOCS_DIR = Path("docs")  # 用来存放 index.html

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

def copy_latest_to_opkg(platform_path: Path, opkg_path: Path, keep=1):
    versions = [d for d in platform_path.iterdir() if d.is_dir()]
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    latest = versions[:keep]

    # 清空 opkg path
    if opkg_path.exists():
        shutil.rmtree(opkg_path)

    for version in latest:
        target_ver = opkg_path / version.name
        shutil.copytree(version, target_ver)
        generate_packages_index(target_ver)  # 👈 在版本目录中生成 Packages

def generate_packages_index(opkg_plugin_path: Path):
    pkg_files = list(opkg_plugin_path.glob("*.ipk"))
    if not pkg_files:
        log(f"No IPK files to generate Packages at {opkg_plugin_path}")
        return

    try:
        subprocess.run(
            ["ipkg-make-index", "."],
            cwd=opkg_plugin_path,
            check=True,
            stdout=open(opkg_plugin_path / "Packages", "w")
        )
        log_ok(f"Generated Packages in {opkg_plugin_path}")
    except Exception as e:
        log(f"Failed to generate Packages: {e}")

def sync_plugin(plugin):
    log(f"Syncing {plugin['name']}...")
    releases = get_releases(plugin['repo'])
    if not releases:
        log(f"No releases found for {plugin['name']}.")
        return

    release_type = plugin.get("release_type", "stable").lower()
    if release_type == "stable":
        filtered_releases = [r for r in releases if not r.get("prerelease", False) and is_stable_version(r['tag_name'])]
    elif release_type == "pre_release":
        filtered_releases = [r for r in releases if r.get("prerelease", False)]
    else:
        filtered_releases = releases

    # 排序：先按发布时间，再尝试 tag_name 最大的
    releases_by_time = sorted(filtered_releases, key=lambda r: r['published_at'], reverse=True)
    releases_by_tag = sorted(filtered_releases, key=lambda r: r['tag_name'], reverse=True)

    new_count = 0
    found = False

    for release_list in [releases_by_time, releases_by_tag]:
        for release in release_list:
            tag = release['tag_name']
            ipk_assets = [a for a in release.get("assets", []) if a['name'].endswith(".ipk")]
            if not ipk_assets:
                continue

            found = True
            for asset in ipk_assets:
                asset_name = asset['name']
                asset_url = asset['browser_download_url']

                for platform in plugin['platforms']:
                    if platform in asset_name or asset_name.endswith("_all.ipk"):
                        archive_dir = ARCHIVE_DIR / platform / plugin['name'] / tag
                        save_path = archive_dir / asset_name
                        if not save_path.exists():
                            if download_asset(asset_url, save_path):
                                new_count += 1
            break
        if found:
            break

    if not found:
        log(f"No IPK found in latest or highest versioned release for {plugin['name']}")
        return

    for platform in plugin['platforms']:
        platform_archive_path = ARCHIVE_DIR / platform / plugin['name']
        opkg_path = OPKG_DIR / platform / plugin['name']

        if platform_archive_path.exists():
            clean_old_versions(platform_archive_path, keep=1)
            copy_latest_to_opkg(platform_archive_path, opkg_path, keep=1)
        else:
            log(f"Directory not found, skipping copy and index generation: {platform_archive_path}")

    log_ok(f"{plugin['name']} sync completed. {new_count} new files.")

def generate_html_index(opkg_dir: Path, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)
    index_file = output_path / "index.html"

    html = ["<html><head><meta charset='utf-8'><title>OpenWrt IPK Center</title></head><body>"]
    html.append("<h1>OpenWrt IPK Center</h1>")
    html.append("<ul>")

    for platform_dir in sorted(opkg_dir.glob("*")):
        for plugin_dir in sorted(platform_dir.glob("*")):
            for version_dir in sorted(plugin_dir.glob("*")):
                ipk_files = sorted(version_dir.glob("*.ipk"))
                for ipk_file in ipk_files:
                    rel_path = f"opkg/{platform_dir.name}/{plugin_dir.name}/{version_dir.name}/{ipk_file.name}"
                    html.append(f"<li><a href='{rel_path}'>{rel_path}</a></li>")

    html.append("</ul></body></html>")

    with open(index_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    log_ok(f"Generated HTML index: {index_file}")

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

    generate_html_index(OPKG_DIR, OPKG_DIR)

if __name__ == "__main__":
    main()















