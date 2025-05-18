def generate_html_index(opkg_dir: Path, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)
    index_file = output_path / "index.html"

    html = ["<html><head><meta charset='utf-8'><title>OpenWrt IPK Center</title></head><body>"]
    html.append("<h1>OpenWrt IPK Center</h1>")
    html.append("<ul>")

    for platform_dir in sorted(opkg_dir.glob("*")):
        for plugin_dir in sorted(platform_dir.glob("*")):
            for version_dir in sorted(plugin_dir.glob("*")):
                rel_path = version_dir.relative_to("docs")
                html.append(f"<li><a href='{rel_path}/'>{rel_path}</a></li>")

    html.append("</ul></body></html>")

    with open(index_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    log_ok(f"Generated HTML index: {index_file}")


if __name__ == "__main__":
    main()
    generate_html_index(OPKG_DIR, Path("docs"))  # 👈 仅新增这一行调用




