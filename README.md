# 🌐 OpenWrt 软件包中心

📦 项目主页：  
👉 [https://dahuangying.github.io/openwrt-ipk-center/](https://dahuangying.github.io/openwrt-ipk-center/)

本项目为 OpenWrt 用户提供第三方 IPK 插件源，支持多平台的插件索引、搜索、安装与更新。界面清晰、使用便捷，适合软路由用户快速部署如 PassWall、OpenClash、Shadowsocks 等常用插件。

---

## 📥 OPKG 插件源配置方法

1. 登录 OpenWrt 管理后台。
2. 打开菜单：**系统 → 软件包 → 配置OPKG**。
3. 编辑文件 /etc/opkg/customfeeds.conf，根据你的设备添加对应插件源地址。
4. 注释掉检查签名 #option check_signature，在/etc/opkg.conf文件里面，把option check_signature文件前面加“#”号。
5. 保存后点击“更新列表”。
6. 进入“可用软件包”中搜索并安装插件。

---

## ✅ 插件源地址（按平台分类）

### 🟦 `aarch64_generic`

**适用设备：**
- 树莓派 4B / 5
- NanoPi R6S / R6C
- FriendlyARM NEO 系列（部分型号）
- RK3399 系列开发板

**OPKG 配置地址：**
```shell
src/gz custom https://dahuangying.github.io/openwrt-ipk-center/opkg/aarch64_generic
```

---

### 🟨 `aarch64_cortex-a53`

**适用设备：**
- NanoPi R2S / R4S
- Orange Pi R1 Plus / R1 Plus LTS
- 其他基于 Cortex-A53 架构的 ARM64 路由器

**OPKG 配置地址：**
```shell
src/gz custom https://dahuangying.github.io/openwrt-ipk-center/opkg/aarch64_cortex-a53
```

---

### 🟥 `x86_64`

**适用设备：**
- 各类 x86_64 架构软路由
- 工控机（如 NUC / J4125 / N5105 / i3-i7 等）
- 在 ESXi / Proxmox 上运行的 OpenWrt 虚拟机

**OPKG 配置地址：**
```shell
src/gz custom https://dahuangying.github.io/openwrt-ipk-center/opkg/x86_64
```

---

## 📚 OpenWrt 官方依赖源（建议同时添加）

若插件提示依赖缺失，请确保已配置以下官方源：

```shell
src/gz openwrt_core     https://downloads.openwrt.org/releases/【版本号】/targets/【平台】/packages
src/gz openwrt_base     https://downloads.openwrt.org/releases/【版本号】/packages/【架构】/base
src/gz openwrt_luci     https://downloads.openwrt.org/releases/【版本号】/packages/【架构】/luci
src/gz openwrt_packages https://downloads.openwrt.org/releases/【版本号】/packages/【架构】/packages
```

🔧 **示例：**
```shell
src/gz openwrt_packages https://downloads.openwrt.org/releases/23.05.3/packages/aarch64_generic/packages
```

---

## 🛠 插件说明与支持

- 所有插件均来自 GitHub Releases，默认优先使用稳定版，确保兼容性与安全性。
- 支持自动构建索引页面，通过浏览器按平台浏览、搜索、下载插件。
- 如遇依赖缺失，请配置官方源，或稍后重试以等待依赖包自动补全。

---

## 🤝 感谢与贡献

欢迎通过 Issue 或 PR：
- 添加更多插件
- 增加架构平台支持
- 提出功能改进建议

---
