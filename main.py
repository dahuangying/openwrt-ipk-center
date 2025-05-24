#!/usr/bin/env python3
import datetime  
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
ARCHIVE_DIR = Path("archive")
OPKG_DIR = Path("opkg")
DOCS_DIR = Path(".")

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

# ✅ 修改：只复制最新版本，不再生成每个插件的 Packages.gz
def copy_latest_to_opkg(platform_path: Path, opkg_path: Path, keep=1):
    versions = [d for d in platform_path.iterdir() if d.is_dir()]
    versions.sort(key=lambda d: d.stat().st_mtime, reverse=True)
    latest = versions[:keep]

    if opkg_path.exists():
        shutil.rmtree(opkg_path)

    for version in latest:
        target_ver = opkg_path / version.name
        shutil.copytree(version, target_ver)

def generate_packages_index(opkg_plugin_path: Path):
    pkg_files = list(opkg_plugin_path.glob("*.ipk"))
    if not pkg_files:
        log(f"No IPK files at {opkg_plugin_path}")
        return

    packages_file = opkg_plugin_path / "Packages"
    gz_file = opkg_plugin_path / "Packages.gz"

    try:
        subprocess.run(
            ["ipkg-make-index", "."],
            cwd=opkg_plugin_path,
            check=True,
            stdout=open(packages_file, "w")
        )
        if not packages_file.exists():
            raise FileNotFoundError("Packages file not created")

        subprocess.run(
            ["gzip", "-9c", "Packages"],
            cwd=opkg_plugin_path,
            stdout=open(gz_file, "wb"),
            check=True
        )

    except Exception as e:
        log(f"Primary method failed: {str(e)}")
        with open(packages_file, "w") as f:
            for ipk in pkg_files:
                name_parts = ipk.stem.split('_')
                pkg_name = '_'.join(name_parts[:-2]) if len(name_parts) > 2 else name_parts[0]
                version = name_parts[-2] if len(name_parts) >= 2 else "1.0"
                f.write(f"Package: {pkg_name}\n")
                f.write(f"Version: {version}\n")
                f.write(f"Architecture: {name_parts[-1]}\n")
                f.write(f"Filename: ./{ipk.name}\n")
                f.write(f"Size: {ipk.stat().st_size}\n\n")

        subprocess.run(
            ["gzip", "-9c", "Packages"],
            cwd=opkg_plugin_path,
            stdout=open(gz_file, "wb"),
            check=True
        )

    log_ok(f"Index files generated at {opkg_plugin_path}")

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
    last_updated = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    platforms = sorted([p.name for p in opkg_dir.glob("*") if p.is_dir()])

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OpenWrt 软件包中心</title>
    <style>
        /* 保持之前的样式不变，只添加以下新样式 */
        .platform-content {{
            display: none;
            animation: fadeIn 0.3s;
        }}
        .platform-content.active {{
            display: block;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; }}
            to {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>OpenWrt 软件包中心</h1>
            <div class="last-updated">最后更新: {last_updated}</div>
        </header>

        <div class="platform-tabs">
            <div class="platform-tab active" onclick="showPlatform('all')">全部平台</div>
            {"".join(f'<div class="platform-tab" onclick="showPlatform(\'{p}\')">{p}</div>' for p in platforms)}
        </div>

        <!-- 全部平台内容 -->
        <div id="platform-all" class="platform-content active">
            {"".join(generate_platform_html(opkg_dir / p) for p in platforms)}
        </div>

        <!-- 各平台单独内容 -->
        {"".join(f'''
        <div id="platform-{p}" class="platform-content">
            {generate_platform_html(opkg_dir / p)}
        </div>
        ''' for p in platforms)}
"""

    html += """
        <script>
            function showPlatform(platform) {
                // 更新标签状态
                document.querySelectorAll('.platform-tab').forEach(tab => {
                    tab.classList.remove('active');
                    if (tab.textContent === platform || 
                        (platform === 'all' && tab.textContent === '全部平台')) {
                        tab.classList.add('active');
                    }
                });
                
                // 更新内容显示
                document.querySelectorAll('.platform-content').forEach(content => {
                    content.classList.remove('active');
                    if (content.id === 'platform-' + platform || 
                        (platform === 'all' && content.id === 'platform-all')) {
                        content.classList.add('active');
                    }
                });
            }
        </script>
    </div>
</body>
</html>
"""

    with open(index_file, "w", encoding="utf-8") as f:
        f.write(html)
    log_ok(f"Generated HTML index: {index_file}")

def generate_platform_html(platform_dir: Path) -> str:
    """生成单个平台的HTML内容"""
    html = []
    for plugin_dir in sorted(platform_dir.glob("*")):
        if not plugin_dir.is_dir():
            continue
            
        for version_dir in sorted(plugin_dir.glob("*")):
            if not version_dir.is_dir():
                continue
                
            for ipk_file in sorted(version_dir.glob("*.ipk")):
                file_size = ipk_file.stat().st_size
                size_str = f"{file_size/1024:.1f} KB" if file_size < 1024*1024 else f"{file_size/(1024*1024):.1f} MB"
                rel_path = f"opkg/{platform_dir.name}/{plugin_dir.name}/{version_dir.name}/{ipk_file.name}"
                
                html.append(f"""
                <div class="package-item">
                    <a href="{rel_path}">
                        <div class="package-name">{ipk_file.name}</div>
                        <div class="package-meta">
                            <span>版本: {version_dir.name}</span>
                            <span>大小: {size_str}</span>
                        </div>
                    </a>
                </div>
                """)
    return "\n".join(html)

# ✅ 生成平台级 Packages.gz（用于 opkg 源）
def generate_platform_level_packages_index(opkg_dir: Path):
    for platform_dir in opkg_dir.glob("*"):
        if not platform_dir.is_dir():
            continue
        all_ipks = list(platform_dir.glob("**/*.ipk"))
        if not all_ipks:
            continue
        packages_file = platform_dir / "Packages"
        gz_file = platform_dir / "Packages.gz"
        with open(packages_file, "w") as f:
            for ipk in all_ipks:
                name_parts = ipk.stem.split('_')
                pkg_name = '_'.join(name_parts[:-2]) if len(name_parts) > 2 else name_parts[0]
                version = name_parts[-2] if len(name_parts) >= 2 else "1.0"
                f.write(f"Package: {pkg_name}\n")
                f.write(f"Version: {version}\n")
                f.write(f"Architecture: {name_parts[-1]}\n")
                f.write(f"Filename: {ipk.relative_to(platform_dir)}\n")
                f.write(f"Size: {ipk.stat().st_size}\n\n")
        subprocess.run(["gzip", "-9c", "Packages"], cwd=platform_dir, stdout=open(gz_file, "wb"), check=True)
        log_ok(f"Generated platform-level Packages.gz in {platform_dir}")

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

    generate_html_index(OPKG_DIR, Path("."))
    Path(".nojekyll").touch()
    log_ok("Created .nojekyll")

    # ✅ 添加平台级 Packages.gz 生成
    generate_platform_level_packages_index(OPKG_DIR)

if __name__ == "__main__":
    main()

















