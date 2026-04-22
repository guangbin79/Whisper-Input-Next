# Whisper-Input-Next for Ubuntu 22.04

<p align="center">
  <img src="docs/whisper_claudecode.png" alt="Project Poster" width="600"/>
</p>

<p align="center">
  <a href="./VERSION">
    <img src="https://img.shields.io/badge/version-3.3.0-blue.svg" alt="Version" />
  </a>
  <a href="https://www.python.org/">
    <img src="https://img.shields.io/badge/python-3.12+-green.svg" alt="Python" />
  </a>
  <a href="LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License" />
  </a>
  <a href="https://ubuntu.com/">
    <img src="https://img.shields.io/badge/Ubuntu-22.04%20LTS-orange.svg" alt="Ubuntu 22.04" />
  </a>
  <a href="#offline-asr">
    <img src="https://img.shields.io/badge/ASR-WeNet%20Offline-brightgreen.svg" alt="WeNet Offline ASR" />
  </a>
</p>

**Whisper-Input-Next 的 Ubuntu 22.04 适配版本**，基于离线 WeNet ASR 引擎，无需网络、无需 API Key、无需付费，按下快捷键即可语音输入文字到任意光标位置。

> 本项目 fork 自 [Mor-Li/Whisper-Input-Next](https://github.com/Mor-Li/Whisper-Input-Next)，针对 **Ubuntu 22.04 LTS** 进行了深度适配，并默认采用 **WeNet 离线流式 ASR**，实现完全本地化的中文语音识别。

---

## 为什么选择这个版本？

| 特性 | 本版本 (WeNet Offline) | 原版 (Doubao/OpenAI) |
|------|------------------------|----------------------|
| **网络依赖** | 完全离线，无需网络 | 需要联网调用云端 API |
| **费用** | 永久免费，零 API 费用 | 按量计费或订阅 |
| **隐私** | 语音数据不上传，本地处理 | 音频上传至第三方服务器 |
| **部署复杂度** | 一键 Docker 启动 WeNet 服务 | 需申请 API Key、配置密钥 |
| **识别延迟** | 本地实时流式，低延迟 | 受网络状况影响 |
| **适用场景** | 内网环境、隐私敏感、长期运行 | 有稳定外网、追求极致准确率 |

---

## 核心特性

### 完全离线的中文语音识别
- **WeNet 流式 ASR**：基于 Conformer 架构，针对中文优化，支持实时流式识别
- **零网络依赖**：所有语音数据本地处理，适合内网、隐私敏感场景
- **零成本**：无需申请任何 API Key，无后续费用
- **Docker 一键部署**：WeNet 服务通过 Docker 容器运行，启动即用

### Ubuntu 22.04 深度适配
- **原生 Linux 支持**：修复 macOS 专属依赖（AppKit、PyObjC），替换为 Linux 兼容实现
- **PyQt5 浮动预览**：实时显示识别结果，类似输入法候选框
- **终端状态栏**：简洁的状态指示（录音中/识别中/完成）
- **xdotool 自动输入**：识别结果自动输入到当前光标位置

### 快捷键操作
- **`Ctrl + F`**：按住开始录音，松开结束并识别（WeNet 离线流式 ASR）
- **`Ctrl + I`**：本地 whisper.cpp 模式（需额外安装，见下方可选配置）

### 其他功能
- **音频存档**：自动保存录音文件，支持历史回放
- **智能重试**：识别失败自动重试，无需重新录音
- **状态指示**：简洁数字状态（0=录音中, 1=识别中, !=错误）

---

## 系统要求

- **操作系统**：Ubuntu 22.04 LTS (Jammy)
- **Python**：3.12+
- **硬件**：
  - CPU：4 核及以上（WeNet ASR 推理占用）
  - 内存：4GB+
  - 磁盘：2GB+（含 Docker 镜像和模型）
- **其他**：
  - 麦克风设备
  - Docker & Docker Compose（用于运行 WeNet 服务）
  - sudo 权限

---

## 快速开始

### 1. 安装系统依赖

```bash
sudo apt update
sudo apt install -y \
  git xdotool xclip pulseaudio-utils \
  libportaudio2 libportaudiocpp0 portaudio19-dev \
  python3-xlib libx11-dev libxtst-dev \
  docker.io docker-compose
```

> **依赖说明**：
> - `xdotool`：模拟键盘输入，将识别文字输入到光标处
> - `portaudio`：音频采集底层库
> - `python3-xlib`, `libxtst-dev`：全局热键监听
> - `docker.io`：运行 WeNet ASR 服务容器

### 2. 安装 Python 3.12

Ubuntu 22.04 默认 Python 3.10，需通过 deadsnakes PPA 安装 3.12：

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.12 python3.12-venv python3.12-dev
```

### 3. 克隆仓库

```bash
git clone https://github.com/YOUR_USERNAME/Whisper-Input-Next-Ubuntu.git ~/Whisper-Input-Next
cd ~/Whisper-Input-Next
```

### 4. 创建虚拟环境并安装依赖

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements-linux.txt
```

### 5. 下载 WeNet 模型并启动服务

```bash
# 下载模型（约 300MB，仅需一次）
git clone https://www.modelscope.cn/wenet/u2pp_conformer-asr-cn-16k-online.git
cd u2pp_conformer-asr-cn-16k-online
git lfs install && git lfs pull
cd ..

# 启动 WeNet Docker 服务
./scripts/wenet_service.sh start
```

> 服务默认运行在 `ws://localhost:10086`，可通过 `docker ps` 查看容器状态。

### 6. 配置环境变量

```bash
cp env.example .env
```

编辑 `.env` 文件，确保以下配置：

```bash
# 启用 WeNet 离线 ASR
WENET_ENABLED=true
TRANSCRIPTION_SERVICE=wenet

# 系统平台设为 linux
SYSTEM_PLATFORM=linux

# 快捷键配置
TRANSCRIPTIONS_BUTTON=f
TRANSLATIONS_BUTTON=ctrl

# 功能开关
CONVERT_TO_SIMPLIFIED=false
ADD_SYMBOL=false
OPTIMIZE_RESULT=false
```

### 7. 权限配置（重要）

全局热键监听需要 `input` 用户组权限：

```bash
sudo usermod -aG input $USER
# 重新登录后生效
```

### 8. 启动程序

```bash
# 前台运行（调试用）
python main.py

# 后台运行（推荐日常使用）
./start.sh
```

---

## 使用方式

1. 确保 WeNet Docker 服务正在运行：`docker ps | grep hx_asr_cpu`
2. 确保 Whisper-Input-Next 程序已启动（前台或后台）
3. 将光标置于任意输入框（终端、浏览器、文档编辑器等）
4. 按下 **`Ctrl + F`** 开始录音，松开结束
5. 识别结果自动输入到光标位置

---

## 可选配置

### 使用本地 whisper.cpp（完全离线备选）

如需完全不依赖 Docker 的离线方案，可配置 whisper.cpp：

```bash
# 1. 安装 whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make
bash ./models/download-ggml-model.sh large-v3
cd ..

# 2. 在 .env 中配置路径
WHISPER_CLI_PATH=/path/to/whisper.cpp/build/bin/whisper-cli
WHISPER_MODEL_PATH=models/ggml-large-v3.bin
```

### 使用豆包流式 ASR（需要网络）

如需更高准确率且可接受联网，可切换至豆包 ASR：

```bash
# 在 .env 中配置
doUBAO_APP_KEY=your_app_id
DOUBAO_ACCESS_KEY=your_access_token
TRANSCRIPTION_SERVICE=doubao
```

获取 API Key：[火山引擎控制台 - 语音识别](https://console.volcengine.com/ark/region:ark+cn-beijing/tts/speechRecognition)

---

## 故障排除

| 问题 | 解决方案 |
|------|----------|
| `PortAudio library not found` | `sudo apt install libportaudio2 portaudio19-dev` |
| `Ctrl+F` 无响应 | 确认已执行 `sudo usermod -aG input $USER` 并重新登录 |
| WeNet 连接失败 | 检查 Docker 容器：`docker logs hx_asr_cpu` |
| 音频设备未检测到 | 检查 pulseaudio：`pulseaudio --check && echo OK` |
| PyQt5 浮动窗口不显示 | 确认 DISPLAY 环境变量：`echo $DISPLAY`，图形界面需运行 |
| 识别准确率低 | WeNet 模型对中文优化，英文识别较弱；嘈杂环境建议靠近麦克风 |

---

## 项目结构

```
~/Whisper-Input-Next/
├── .env                          # 环境变量配置
├── .venv/                        # Python 3.12 虚拟环境
├── main.py                       # 程序入口
├── start.sh                      # 后台启动脚本（tmux）
├── requirements-linux.txt        # Linux 依赖（无 macOS 专用包）
├── INSTALL_UBUNTU_2204.md        # 详细安装指南（含代码修改说明）
├── WeNet.md                      # WeNet 服务部署说明
├── u2pp_conformer-asr-cn-16k-online/  # WeNet 模型文件
├── scripts/
│   └── wenet_service.sh          # WeNet Docker 服务管理脚本
└── src/
    ├── keyboard/
    │   └── listener.py           # 全局热键监听（已适配 Linux）
    ├── transcription/
    │   ├── doubao_streaming.py   # 豆包流式 ASR
    │   └── wenet_streaming.py    # WeNet 流式 ASR
    └── ui/
        ├── status_bar.py         # Linux 终端状态栏
        └── floating_preview.py   # Linux PyQt5 浮动预览窗口
```

---

## 致谢

- 原项目：[Mor-Li/Whisper-Input-Next](https://github.com/Mor-Li/Whisper-Input-Next)
- 原始项目：[ErlichLiu/Whisper-Input](https://github.com/ErlichLiu/Whisper-Input)
- ASR 引擎：[WeNet](https://github.com/wenet-e2e/wenet)
- 模型来源：[ModelScope - u2pp_conformer-asr-cn-16k-online](https://www.modelscope.cn/wenet/u2pp_conformer-asr-cn-16k-online)

---

## 许可证

MIT License

---

**如果本项目对你有帮助，请给原项目 [Whisper-Input-Next](https://github.com/Mor-Li/Whisper-Input-Next) 点个 Star！**
