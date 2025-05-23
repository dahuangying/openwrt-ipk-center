
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
                    rel_path = f"{platform_dir.name}/{plugin_dir.name}/{version_dir.name}/{ipk_file.name}"
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

