# FedTracker WebUI ✨

<p align="center">
    <img src="https://img.shields.io/badge/Version-1.0.0-blue.svg" alt="Version">
    <img src="https://img.shields.io/badge/Python-3.8%2B-green.svg" alt="Python">
    <img src="https://img.shields.io/badge/Gradio-4.0%2B-orange.svg" alt="Gradio">
    <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License">
</p>

<p align="center">
    <strong>联邦学习扩散模型水印追踪系统</strong><br>
    <em>现代化 · 易用 · 美观 · 专业</em>
</p>

---

## 🌟 特性亮点

- 🎨 **现代化设计** - 采用豆包风格的清新界面，渐变配色与圆角卡片
- 🖼️ **图片生成** - 从扩散模型生成高质量图片，支持自定义参数
- 🔍 **泄漏模拟** - 模拟客户端模型泄漏场景
- 🎯 **所有者识别** - 基于指纹技术识别模型所有者
- 📊 **实时反馈** - 友好的状态提示和进度显示
- ⚡ **高效部署** - 一键启动，支持本地和远程访问

## 📦 安装依赖

```bash
# 进入 WebUI 目录
cd webui

# 安装依赖
pip install -r requirements.txt
```

## 🚀 快速开始

### 方法一：使用启动脚本（推荐）

```bash
# 添加执行权限（首次运行）
chmod +x run.sh

# 启动服务
./run.sh

# 自定义端口
./run.sh --port 8080

# 启用公网分享
./run.sh --share
```

### 方法二：直接运行

```bash
python app.py --port 7860 --host 0.0.0.0
```

访问 `http://localhost:7860` 即可使用！

## 🎯 功能指南

### Tab 1: 🎨 图片生成

从训练好的扩散模型生成图片

**操作步骤：**

1. 选择训练好的模型（从 `result/` 目录）
2. 查看模型参数（展开"📋 模型参数"）
3. 配置生成参数：
   - **类标签**：生成图片的目标类别（0-9 for CIFAR）
   - **生成数量**：一次生成的图片数
   - **推理步数**：扩散模型采样步骤（建议 100-1000）
   - **随机种子**：控制生成可重复性
4. 高级选项：
   - **水印图片**：勾选后生成触发器类水印图片
   - **计算设备**：选择 GPU 或 CPU
5. 点击 "🚀 开始生成"

**输出位置：** `webui/static/outputs/gen_YYYYMMDD_HHMMSS/`

---

### Tab 2: 🔍 泄漏模拟

模拟联邦学习中的客户端模型泄漏场景

**操作步骤：**

1. 选择包含追踪数据的源模型
2. 查看追踪数据信息（展开"ℹ️ 追踪数据信息"）
3. 选择要模拟泄漏的客户端索引
4. 设置输出参数：
   - **输出文件名**：泄漏模型保存名称
   - **输出目录**：默认为 `/home/ubuntu/Fedsd/leak_test/`
5. 点击 "🎭 模拟泄漏"

**说明：** 系统会模拟指定客户端的模型被泄漏，用于后续所有者识别测试。

---

### Tab 3: 🎯 所有者识别

识别泄漏模型的所有者

**操作步骤：**

1. 选择泄漏模型文件（从 `leak_test/` 目录）
2. 选择源模型的追踪数据
3. 点击 "🔍 识别所有者"
4. 查看识别结果：
   - **客户端ID**：最可能的所有者
   - **置信度**：识别可信度评分

**工作原理：** 通过比对模型指纹与追踪数据中的客户端指纹，找出最匹配的所有者。

## 🗂️ 项目结构

```
webui/
├── app.py                     # 主应用（Gradio 界面）
├── run.sh                     # 启动脚本
├── requirements.txt           # 依赖列表
├── modules/
│   ├── __init__.py           # 模块初始化
│   ├── utils.py              # 工具函数
│   ├── generation.py         # 图片生成模块
│   └── tracing.py            # 泄漏追踪模块
└── static/
    └── outputs/              # 生成的图片输出目录
```

## ⚙️ 配置选项

### 命令行参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--port` | 7860 | 服务端口 |
| `--host` | 0.0.0.0 | 服务主机 |
| `--share` | False | 创建公网分享链接 |

### 关键配置

```python
# app.py 中的配置
LEAK_TEST_DIR = "/home/ubuntu/Fedsd/leak_test/"  # 泄漏模型目录
```

## 🎨 界面设计

WebUI 采用豆包风格的现代化设计：

- **渐变背景**：流动的紫粉渐变背景，营造科技感
- **圆角卡片**：20px 大圆角设计，柔和不生硬
- **流畅动画**：所有交互配以平滑过渡效果
- **友好提示**：emoji 图标配合清晰的状态反馈
- **响应式布局**：适配各类屏幕尺寸

## 🔧 常见问题

<details>
<summary><b>Q: 模型列表为空？</b></summary>

**A:** 确保 `result/` 目录下有训练好的模型，且包含 `model_final.pth` 和 `args.txt` 文件。

```bash
ls result/simpleunet_cifar10_stage2/
# 应显示: args.txt, model_final.pth, trace_data/
```
</details>

<details>
<summary><b>Q: 图片生成失败？</b></summary>

**A:** 检查以下几点：
1. GPU 内存是否充足（建议 8GB+）
2. 模型文件是否完整
3. 类标签是否在合法范围内（如 CIFAR-10 为 0-9）
</details>

<details>
<summary><b>Q: 所有者识别置信度很低？</b></summary>

**A:** 可能原因：
1. 追踪数据不完整
2. 模型架构不匹配
3. 泄漏模型经过修改

建议重新训练模型并确保保存完整的追踪数据。
</details>

<details>
<summary><b>Q: 如何修改默认端口？</b></summary>

**A:** 使用 `--port` 参数：

```bash
python app.py --port 8080
```
</details>

## 📸 界面截图

### 主页面
![Main Page](docs/screenshots/main.png)

### 图片生成
![Image Generation](docs/screenshots/generation.png)

### 泄漏模拟
![Leak Simulation](docs/screenshots/leak.png)

### 所有者识别
![Owner Identification](docs/screenshots/identify.png)

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 👥 作者

FedTracker Team

## 🙏 致谢

- [Gradio](https://gradio.app/) - 强大的 WebUI 框架
- [PyTorch](https://pytorch.org/) - 深度学习框架
- [Diffusers](https://huggingface.co/docs/diffusers/) - 扩散模型库

---

<p align="center">
    Made with ❤️ by FedTracker Team<br>
    <em>联邦学习水印追踪领域的开源探索</em>
</p>