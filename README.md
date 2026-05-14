# MD转换神器

基于微软的 [markitdown](https://github.com/microsoft/markitdown)，使用 **Wails + Go + Python** 开发的桌面应用程序，可将各种文档格式批量转换为 Markdown 格式，支持图片提取与 DeepSeek-OCR 文字识别。

## ✨ 核心特性

- 📄 **多格式支持**：DOCX, DOC, XLSX, XLS, PPTX, PPT, PDF, HTML, TXT, CSV, XML, JSON, MD, RST, RTF 等
- 🖼️ **图片提取**：自动从 DOCX 文件中提取图片
- 🤖 **DeepSeek-OCR**：内置 DeepSeek-OCR 模型，自动识别图片中的文字
- 📁 **目录保持**：转换后自动保持原有目录结构
- ⚡ **批量转换**：支持批量处理大量文件
- 🎨 **独立运行**：单个 exe 文件，复制到任何 Windows 电脑即可使用

## 🚀 快速开始

### 使用方法

1. 双击运行 `MD转换神器.exe`
2. 点击「选择目录」按钮，选择要转换的源文档目录
3. 选择或创建目标目录（Markdown 输出目录）
4. 点击「开始转换」按钮
5. 等待转换完成，查看统计信息

### 界面说明

- **进度条**：实时显示转换进度
- **统计面板**：显示目录数、总文件数、已转换数、待转换数
- **日志区域**：显示详细转换日志
- **失败列表**：转换失败的文件会显示在此处

### 转换结果

- ✅ **成功转换**：生成 Markdown 文件
- ⏭️ **跳过（MD文件）**：直接复制到目标目录
- ❌ **转换失败**：自动复制原文件到目标目录
- 📝 **完成提示**：弹窗显示统计信息

## 🏗️ 技术架构

```
┌─────────────────────────────────────┐
│      MD转换神器.exe (Go/Wails)      │
│  ┌─────────────────────────────────┐ │
│  │   GUI 界面 (HTML/CSS/JS)        │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │   Go 后端 (Wails)               │ │
│  │   - 嵌入 bridge.exe             │ │
│  │   - 进程管理                     │ │
│  │   - 事件通信                     │ │
│  └─────────────────────────────────┘ │
│  ┌─────────────────────────────────┐ │
│  │   bridge.exe (PyInstaller)      │ │
│  │   - Python 完整环境              │ │
│  │   - markitdown 库               │ │
│  │   - DeepSeek-OCR                │ │
│  └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

### 技术栈

| 组件 | 技术 | 说明 |
|------|------|------|
| 桌面框架 | Wails v2.12.0 | Go + WebView2 |
| GUI | HTML/CSS/JavaScript | 原生前端 |
| 文档转换 | Python + markitdown | 核心转换逻辑 |
| OCR | DeepSeek-OCR (SiliconFlow API) | 图片文字识别 |
| 打包 | PyInstaller + Wails | 双层独立打包 |

## 📁 项目结构

```
software/
├── main.go                 # Go 主程序，Wails 应用入口
├── app.go                  # Go 应用逻辑
├── wails.json              # Wails 配置文件
├── go.mod / go.sum         # Go 模块依赖
├── .gitignore              # Git 忽略配置
│
├── frontend/               # 前端界面
│   ├── index.html         # 主界面
│   ├── img/               # 界面图片资源
│   └── wailsjs/           # Wails 自动生成的绑定
│
├── scripts/                # Python 脚本
│   └── bridge.py          # 核心转换逻辑
│
├── docs/                   # 文档资源
│   ├── logo.jpg
│   ├── wechat.jpg
│   └── alipay.jpg
│
└── build/                  # 编译输出（自动生成）
    └── bin/
        └── MD转换神器.exe  # 最终可执行文件
```

## 🔧 开发说明

### 环境要求

- Go 1.21+
- Python 3.11+ (开发时)
- Wails CLI
- PyInstaller

### 开发调试

```bash
# 1. 安装 Go 依赖
cd software
go mod tidy

# 2. 运行开发模式
wails dev

# 3. 修改 Python 脚本后重新打包
cd scripts
pyinstaller --onefile --name "markitdown_bridge" bridge.py
cd ..
copy scripts\dist\markitdown_bridge.exe .

# 4. 重新编译应用
wails build
```

### 重新打包步骤

1. 修改 `scripts/bridge.py` 代码
2. 打包 Python 脚本：
   ```bash
   cd scripts
   pyinstaller --onefile --name "markitdown_bridge" bridge.py
   ```
3. 复制打包结果到根目录：
   ```bash
   copy dist\markitdown_bridge.exe ..\
   ```
4. 编译 Go 应用：
   ```bash
   wails build
   ```

## 🔒 安全说明

### API Key 管理

本应用内置了 SiliconFlow API Key，用于 DeepSeek-OCR 功能：

- API Key 硬编码在 [main.go](main.go)
- 仅用于图片 OCR 识别
- API 调用受 SiliconFlow 账户限制

**注意事项**：
- 仅供个人/内部使用
- 如需商业部署，请联系开发者获取正式授权
- API Key 已嵌入打包后的 exe 中

### 文件安全

- 转换过程在本地执行，不上传文件到服务器
- 仅图片数据会发送到 SiliconFlow API 进行 OCR 识别
- 临时文件在转换完成后自动清理

## ⚠️ 限制与注意事项

1. **API 限制**：DeepSeek-OCR 使用 SiliconFlow API，有调用频率和额度限制
2. **文件大小**：大文件转换可能需要较长时间
3. **图片格式**：EMF/WMF 格式图片不支持 OCR 识别
4. **Python 环境**：打包后的 exe 不需要安装 Python

## 🐛 故障排除

### 常见问题

**Q: 转换失败提示 "Module not found"**
A: 这是打包问题，请重新运行打包命令

**Q: OCR 识别失败**
A: 检查网络连接，或 API 额度是否用完

**Q: 进度条不更新**
A: 等待一段时间，大文件转换需要较长时间

### 日志查看

转换过程中的详细日志会显示在界面的日志区域，方便排查问题。

## 💰 打赏支持

如果这个工具对你有帮助，欢迎打赏支持！

<div align="center">
  <img src="docs/微信收款码.jpg" alt="微信收款码" width="250" />
</div>

## 📝 许可证

本项目仅供内部使用。

## 🤝 联系方式

如有问题或建议，请联系开发者，邮箱：12777894@qq.com；微信号：cattei。
