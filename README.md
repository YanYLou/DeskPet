# 🐾 DesktopPet

一个基于 PySide6 的桌面宠物应用。透明无边框窗口，支持 PNG 序列帧 / GIF 动画，可拖拽、行走、换肤，打包后单文件即可运行。

![preview](docs/preview.gif)

## ✨ 功能

- 透明无边框窗口，始终置顶
- 支持 PNG 序列帧 & GIF 动画
- 多状态切换：`idle` / `hover` / `click` / `drag` / `walk`
- 行走时自动翻转朝向，随机漫步
- 皮肤系统：`.tar` 打包，热切换无需重启
- 右键菜单：刷新 / 散步 / 退出
- 配置 & 皮肤缓存存放于 `%AppData%`，不污染程序目录
- PyInstaller 单文件打包，陌生电脑双击即用

## 📁 项目结构

```
DesktopPet/
├── main.py                 # 入口
├── src/
│   ├── pet_widget.py       # 宠物主窗口
│   ├── config_manager.py   # 配置管理（AppData 读写）
│   ├── skin_manager.py     # 皮肤加载 / 解压
│   └── settings_window.py  # 设置窗口
├── res/
│   └── skins/
│       └── default/        # 内置默认皮肤
│           ├── idle/
│           │   ├── 0.png
│           │   └── 1.png
│           ├── walk/
│           ├── hover/
│           ├── click/
│           └── drag/
├── build.bat               # Windows 一键打包脚本
├── requirements.txt
├── LICENSE                 # Unlicense
└── README.md
```

## 🚀 快速开始

### 开发环境运行

```bash
# 1. 克隆仓库
git clone https://github.com/<你的用户名>/DesktopPet.git
cd DesktopPet

# 2. 创建虚拟环境（推荐）
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

# 3. 安装依赖
pip install -r requirements.txt

# 4. 运行
python main.py
```

### 打包为 exe（Windows）

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --add-data "res;res" --name DesktopPet main.py
```

产物位于 `dist/DesktopPet.exe`，可直接拷贝到任意 Windows 电脑运行，无需安装 Python。

> **Linux / macOS** 将 `--add-data "res;res"` 改为 `--add-data "res:res"`。

## 🎨 皮肤格式

每个皮肤是一个文件夹（或 `.tar` 包），内部按状态分子目录：

```
my_skin/
├── skin.json          # 元信息（名称、作者、fps、scale）
├── idle/
│   ├── 0.png
│   ├── 1.png
│   └── ...
├── walk/
├── hover/
├── click/
└── drag/
```

`skin.json` 示例：

```json
{
  "name": "My Skin",
  "author": "YourName",
  "fps": 8,
  "scale": 1.0
}
```

将皮肤文件夹或 `.tar` 放入 `%LocalAppData%\DesktopPet\Skins\` 即可在设置中切换。

## ⚙️ 数据存储

| 内容 | 路径 |
|------|------|
| 配置文件 | `%AppData%\DesktopPet\pet_config.json` |
| 行为配置 | `%AppData%\DesktopPet\behaviors.json` |
| 皮肤缓存 | `%LocalAppData%\DesktopPet\Skins\` |

首次运行自动创建，卸载时删除对应文件夹即可完全清理。

## 🛠️ 依赖

- Python ≥ 3.10
- PySide6 ≥ 6.5

```
# requirements.txt
PySide6>=6.5
```

## 📜 License

[Unlicense](LICENSE) — 公共领域，随意使用、修改、分发，无需署名。

```
This is free and unencumbered software released into the public domain.
```
```
