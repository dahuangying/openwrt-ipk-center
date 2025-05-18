from pathlib import Path

def log_ok(msg):
    print("[OK]", msg)

def generate_html_index(opkg_dir: Path, output_path: Path):
    output_path.mkdir(parents=True, exist_ok=True)
    index_file = output_path / "index.html"

    html = ["<html><head><meta charset='utf-8'><title>OpenWrt IPK Center</title></head><body>"]
    html.append("<h1>OpenWrt IPK Center</h1>")
    html.append("<ul>")

    for platform_dir in sorted(opkg_dir.glob("*")):
        for plugin_dir in sorted(platform_dir.glob("*")):
            for version_dir in sorted(plugin_dir.glob("*")):
                # 用 opkg_dir 做基准路径
                try:
                    rel_path = version_dir.relative_to(opkg_dir)
                except ValueError:
                    rel_path = version_dir.name  # 退化处理

                html.append(f"<li><a href='{rel_path}/'>{rel_path}</a></li>")

    html.append("</ul></body></html>")

    with open(index_file, "w", encoding="utf-8") as f:
        f.write("\n".join(html))

    log_ok(f"Generated HTML index: {index_file}")

def main():
    # 示例：生成假的 IPK 目录结构（可删除）
    (OPKG_DIR / "x86_64" / "luci-app-demo" / "1.0.0").mkdir(parents=True, exist_ok=True)
    fake_ipk = OPKG_DIR / "x86_64" / "luci-app-demo" / "1.0.0" / "luci-app-demo_1.0.0_all.ipk"
    fake_ipk.write_text("Fake IPK Content")

    (OPKG_DIR / "aarch64_cortex-a53" / "luci-app-hello" / "2.0.0").mkdir(parents=True, exist_ok=True)
    fake_ipk2 = OPKG_DIR / "aarch64_cortex-a53" / "luci-app-hello" / "2.0.0" / "luci-app-hello_2.0.0_aarch64.ipk"
    fake_ipk2.write_text("Another fake IPK")

# 这里改成你实际存放 ipk 目录路径
OPKG_DIR = Path("output")

if __name__ == "__main__":
    main()
    generate_html_index(OPKG_DIR, Path("docs"))







