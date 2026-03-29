# FedTracker WebUI - 极简白色风格

一个简洁现代的联邦学习水印追踪系统Web界面。

## 特点

- 豆包风格的极简白色设计
- 卡片式功能入口
- 圆角、柔和阴影
- 流畅的交互体验

## 安装

```bash
cd webui
pip install -r requirements.txt
```

## 运行

### 本地访问
```bash
python app.py
# 或
./run.sh
```
访问: http://localhost:7860

### 公网访问 (Gradio隧道)

#### 方法1: 使用命令行参数
```bash
# 生成公网链接
python app.py --share

# 公网 + 密码保护
python app.py --share --auth admin:123456

# 自定义端口
python app.py --port 8080 --share
```

#### 方法2: 使用启动脚本
```bash
# 生成公网链接
./run.sh --share

# 公网 + 密码保护
./run.sh --share --auth admin:123456

# 自定义端口
./run.sh --port 8080 --share
```

启动后会输出类似:
```
本地访问: http://localhost:7860
公网链接: https://xxxxxxxx.gradio.live
```

### 安全建议

⚠️ **重要提示:**

1. **公网链接有效期**: Gradio生成的公网链接通常持续72小时
2. **密码保护**: 公网访问时强烈建议设置密码
3. **内网穿透**: 如需长期稳定访问，建议使用:
   - **frp** (内网穿透工具)
   - **ngrok** (隧道服务)
   - **Cloudflare Tunnel** (免费稳定)

### 使用 Cloudflare Tunnel (推荐长期方案)

```bash
# 1. 安装 cloudflared
brew install cloudflared  # macOS
# 或从官网下载: https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/install-and-setup/installation

# 2. 启动本地服务 (不启用share)
python app.py --port 7860

# 3. 创建隧道
cloudflared tunnel --url http://localhost:7860
```

这会生成一个长期有效的 `https://xxx.trycloudflare.com` 链接。

## 界面预览

主界面展示三个核心功能：
1. 图像生成 - 从训练好的模型生成图像
2. 泄露模拟 - 模拟客户端模型泄露
3. 所有者识别 - 识别泄露模型的所有者

## 命令行参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--share` | 启用Gradio公网分享 | `--share` |
| `--auth` | 设置用户名密码 | `--auth admin:123456` |
| `--port` | 自定义端口 | `--port 8080` |
| `--help` | 显示帮助 | `--help` |
