import os
import requests
import json
from pathlib import Path
from urllib.parse import urlparse

# === CONFIGURATION ===
CONFIG_FILE = "config.json"
DOWNLOAD_DIR = Path("downloads")
MAX_VERSIONS = 10
SUPPORTED_PLATFORMS = ["aarch64_cortex-a53", "x86_64"]


def load_config():
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_releases(repo):
    url = f"https://api.github.com/repos/{repo}/releases"
    res = requests.get(url, timeout=10)
    if res.status_code != 200:
        print(f"[ERROR] Failed to fetch releases from {repo}: {res.status_code}")
        return []
    return res.json()


def download_asset(asset_url, target_path):
    headers = {"Accept": "application/octet-stream"}
    try:
        with requests.get(asset_url, headers=headers, stream=True, timeout=15) as r:
            if r.status_code == 200:
                with open(target_path, 'wb') as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"[OK] Downloaded: {target_path}")
            else:
                print(f"[WARN] Skipped {asset_url}: {r.status_code}")
    except Exception as e:
        print(f"[ERROR] Failed to download {asset_url}: {e}")


def clean_old_versions(path):
    versions = sorted(path.iterdir(), key=os.path.getmtime, reverse=True)
    for extra in versions[MAX_VERSIONS:]:
        print(f"[CLEAN] Removing old version: {extra}")
        if extra.is_dir():
            for f in extra.glob("**/*"):
                f.unlink()
            extra.rmdir()


def sync_plugin(plugin):
    print(f"[INFO] Syncing {plugin['name']}...")
    releases = get_releases(plugin['repo'])
    count = 0
    for release in releases:
        tag = release.get("tag_name")
        assets = release.get("assets", [])
        for asset in assets:
            asset_name = asset['name']
            asset_url = asset['browser_download_url']
            for platform in SUPPORTED_PLATFORMS:
                if platform in asset_name:
                    target_dir = DOWNLOAD_DIR / platform / plugin['name'] / tag
                    target_dir.mkdir(parents=True, exist_ok=True)
                    target_path = target_dir / asset_name
                    if not target_path.exists():
                        download_asset(asset_url, target_path)
                        count += 1
        clean_old_versions(DOWNLOAD_DIR / platform / plugin['name'])
    print(f"[INFO] {plugin['name']} sync completed. {count} new files.")


def main():
    config = load_config()
    print("[INFO] Starting all plugin sync...")
    for plugin in config.get("plugins", []):
        sync_plugin(plugin)
    print("[INFO] All plugin sync completed.")


if __name__ == "__main__":
    main()
