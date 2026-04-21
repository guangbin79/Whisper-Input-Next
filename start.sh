#!/bin/bash

# Whisper-Input-Next 启动脚本 v2.1.0
# 用于启动语音转录工具
# 功能：自动检查并安装依赖，支持 WeNet 本地离线 ASR

echo "🚀 启动 Whisper-Input-Next 语音转录工具..."

# 创建日志目录(如果不存在)
if [ ! -d "logs" ]; then
  mkdir -p logs
fi

# 生成带时间戳的日志文件名
LOG_FILE="logs/Whisper-Input-Next-$(date +%Y%m%d-%H%M%S).log"
echo "📝 日志将保存到: $LOG_FILE"

# 检查.env文件是否存在
if [ ! -f ".env" ]; then
  echo "❌ 未找到 .env 配置文件"
  echo "请复制 env.example 到 .env 并配置您的API密钥"
  exit 1
fi

# 检查 WeNet 配置
if grep -q "TRANSCRIPTION_SERVICE=wenet" .env 2>/dev/null; then
  echo "🔍 检测到 WeNet 配置"
  
  # ========== WeNet 自动下载和启动功能 ==========
  
  # 1. 检查 Docker 环境
  echo "🐳 检查 Docker 环境..."
  if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装"
    echo "   请先安装 Docker: https://docs.docker.com/get-docker/"
    exit 1
  fi
  
  # 检查 Docker 服务是否运行
  if ! docker info &> /dev/null; then
    echo "❌ Docker 服务未运行"
    echo "   请启动 Docker 服务:"
    echo "   - Linux: sudo systemctl start docker"
    echo "   - macOS: 打开 Docker Desktop"
    exit 1
  fi
  echo "✅ Docker 环境正常"
  
  # 2. 检查并下载 WeNet Docker 镜像
  WENET_IMAGE="wenetorg/wenet:latest"
  echo "🐳 检查 WeNet Docker 镜像..."
  if ! docker images | grep -q "wenetorg/wenet"; then
    echo "📥 正在下载 WeNet Docker 镜像 (约 2GB，请耐心等待)..."
    if ! docker pull $WENET_IMAGE; then
      echo "❌ WeNet Docker 镜像下载失败"
      echo "   请检查网络连接或手动执行: docker pull $WENET_IMAGE"
      exit 1
    fi
    echo "✅ WeNet Docker 镜像下载完成"
  else
    echo "✅ WeNet Docker 镜像已存在"
  fi
  
  # 3. 检查并下载 WeNet 模型
  MODEL_DIR="./u2pp_conformer-asr-cn-16k-online"
  echo "📦 检查 WeNet 模型..."
  if [ ! -d "$MODEL_DIR" ]; then
    echo "📥 正在下载 WeNet 模型 (约 300MB)..."
    
    # 检查 git-lfs
    if ! command -v git-lfs &> /dev/null; then
      echo "   安装 git-lfs..."
      if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y git-lfs
      elif command -v brew &> /dev/null; then
        brew install git-lfs
      else
        echo "⚠️  请手动安装 git-lfs: https://git-lfs.github.com/"
        exit 1
      fi
    fi
    
    # 初始化 git-lfs
    git lfs install &> /dev/null
    
    # 克隆模型仓库
    if ! git clone https://www.modelscope.cn/wenet/u2pp_conformer-asr-cn-16k-online.git; then
      echo "❌ 模型仓库克隆失败"
      echo "   请检查网络连接或手动下载模型"
      exit 1
    fi
    
    # 下载 LFS 文件
    cd u2pp_conformer-asr-cn-16k-online
    if ! git lfs pull; then
      echo "❌ 模型文件下载失败"
      echo "   请检查网络连接或手动执行: git lfs pull"
      cd ..
      exit 1
    fi
    cd ..
    echo "✅ WeNet 模型下载完成"
  else
    echo "✅ WeNet 模型已存在"
  fi
  
  # 4. 检查并启动 WeNet 服务
  echo "🚀 检查 WeNet 服务状态..."
  if ! docker ps | grep -q "hx_asr_cpu"; then
    # 检查是否有停止的容器
    if docker ps -a | grep -q "hx_asr_cpu"; then
      echo "🔄 发现已停止的 WeNet 容器，正在启动..."
      docker start hx_asr_cpu
    else
      echo "🚀 启动 WeNet 服务..."
      docker run -d \
        --name hx_asr_cpu \
        --restart unless-stopped \
        --cpus="4" \
        -e OMP_NUM_THREADS=4 \
        -p 10086:10086 \
        -v "$(pwd)/u2pp_conformer-asr-cn-16k-online:/mnt/model" \
        $WENET_IMAGE \
        /home/wenet/runtime/libtorch/build/bin/websocket_server_main \
          --port 10086 \
          --chunk_size 16 \
          --model_path /mnt/model/final.zip \
          --unit_path /mnt/model/units.txt
    fi
    
    if [ $? -eq 0 ]; then
      echo "✅ WeNet 服务启动成功"
      echo "⏳ 等待服务初始化 (约 5 秒)..."
      sleep 5
    else
      echo "❌ WeNet 服务启动失败"
      echo "   请检查 Docker 日志: docker logs hx_asr_cpu"
      exit 1
    fi
  else
    echo "✅ WeNet 服务已在运行"
  fi
  
  echo "✅ WeNet 环境准备完成"
fi

# 检查是否已有名为Whisper-Input-Next的会话
if tmux has-session -t Whisper-Input-Next 2>/dev/null; then
  echo "🔄 已有Whisper-Input-Next会话存在，将关闭旧会话并创建新会话..."
  tmux kill-session -t Whisper-Input-Next
fi

# 检查 python3 是否可用
if ! command -v python3 &> /dev/null; then
  echo "❌ 未找到 python3 命令"
  echo "请先安装 Python 3: sudo apt-get install python3 python3-venv python3-pip"
  exit 1
fi

# 创建虚拟环境(如果不存在)
if [ ! -d ".venv" ]; then
  echo "🐍 创建虚拟环境..."
  python3 -m venv .venv
  if [ $? -ne 0 ]; then
    echo "❌ 虚拟环境创建失败"
    exit 1
  fi
  echo "✅ 虚拟环境创建完成"
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查并安装核心依赖
echo "📦 检查核心依赖..."

# 检查 websockets（WeNet 必需）
if ! python3 -c "import websockets" 2>/dev/null; then
  echo "   安装 websockets..."
  pip install websockets -q
  if [ $? -eq 0 ]; then
    echo "   ✅ websockets 安装完成"
  else
    echo "   ❌ websockets 安装失败"
  fi
else
  echo "   ✅ websockets 已安装"
fi

# 检查其他核心依赖
check_and_install() {
  local package=$1
  local import_name=${2:-$1}
  
  if ! python3 -c "import $import_name" 2>/dev/null; then
    echo "   安装 $package..."
    pip install $package -q
    if [ $? -eq 0 ]; then
      echo "   ✅ $package 安装完成"
    else
      echo "   ❌ $package 安装失败"
    fi
  else
    echo "   ✅ $package 已安装"
  fi
}

# 检查并安装项目依赖
echo "📦 检查项目依赖..."

# 根据平台选择 requirements 文件
if [[ "$(uname)" == "Darwin" ]]; then
  REQUIREMENTS_FILE="requirements.txt"
else
  REQUIREMENTS_FILE="requirements-linux.txt"
fi

# 如果 requirements 文件存在，检查是否需要安装
if [ -f "$REQUIREMENTS_FILE" ]; then
  # 检查关键包是否已安装
  NEED_INSTALL=false
  
  # 检查几个关键包
  if ! python3 -c "import openai" 2>/dev/null; then
    NEED_INSTALL=true
  fi
  
  if ! python3 -c "import pynput" 2>/dev/null; then
    NEED_INSTALL=true
  fi
  
  if ! python3 -c "import sounddevice" 2>/dev/null; then
    NEED_INSTALL=true
  fi
  
  if [ "$NEED_INSTALL" = true ]; then
    echo "📦 安装项目依赖（根据 $REQUIREMENTS_FILE）..."
    pip install -r $REQUIREMENTS_FILE -q
    if [ $? -eq 0 ]; then
      echo "✅ 项目依赖安装完成"
    else
      echo "⚠️  部分依赖安装失败，但将继续启动"
    fi
  else
    echo "✅ 项目依赖已安装"
  fi
else
  echo "⚠️  未找到 $REQUIREMENTS_FILE，将尝试安装核心依赖"
  
  # 安装核心依赖
  check_and_install "openai"
  check_and_install "pynput"
  check_and_install "sounddevice"
  check_and_install "soundfile"
  check_and_install "numpy"
  check_and_install "pyperclip"
  check_and_install "python-dotenv"
  check_and_install "colorlog"
  check_and_install "PyQt5"
fi

# 额外检查 WeNet 相关依赖
if grep -q "TRANSCRIPTION_SERVICE=wenet" .env 2>/dev/null; then
  echo "🔍 检查 WeNet 依赖..."
  check_and_install "websockets"
fi

echo "✅ 依赖检查完成"

# 创建一个新的tmux会话
tmux new-session -d -s Whisper-Input-Next

# 确保在正确的目录
tmux send-keys -t Whisper-Input-Next "cd $(pwd)" C-m

# 激活虚拟环境
tmux send-keys -t Whisper-Input-Next "source .venv/bin/activate" C-m

# 启动应用程序并同时将输出保存到日志文件
echo "🎙️  启动语音转录服务..."
tmux send-keys -t Whisper-Input-Next "python3 main.py 2>&1 | tee $LOG_FILE" C-m

# 连接到会话
echo ""
echo "✅ Whisper-Input-Next 已启动！"
# 读取配置
HOLD_BUTTON=$(grep "^HOLD_BUTTON=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "')
TRANSCRIPTION_SERVICE=$(grep "^TRANSCRIPTION_SERVICE=" .env 2>/dev/null | cut -d'=' -f2 | tr -d ' "')

# 转换按键名称为可读格式
if [ "$HOLD_BUTTON" = "cmd_r" ]; then
    KEY_DISPLAY="右 Command 键"
elif [ "$HOLD_BUTTON" = "cmd_l" ]; then
    KEY_DISPLAY="左 Command 键"
elif [ "$HOLD_BUTTON" = "alt_r" ]; then
    KEY_DISPLAY="右 Alt 键"
elif [ "$HOLD_BUTTON" = "alt_l" ]; then
    KEY_DISPLAY="左 Alt 键"
elif [ "$HOLD_BUTTON" = "ctrl_r" ]; then
    KEY_DISPLAY="右 Ctrl 键"
elif [ "$HOLD_BUTTON" = "ctrl_l" ]; then
    KEY_DISPLAY="左 Ctrl 键"
else
    KEY_DISPLAY="${HOLD_BUTTON:-Ctrl+F}"
fi

# 转换服务名称为可读格式
if [ "$TRANSCRIPTION_SERVICE" = "wenet" ]; then
    SERVICE_DISPLAY="WeNet 本地离线 ASR"
elif [ "$TRANSCRIPTION_SERVICE" = "doubao" ]; then
    SERVICE_DISPLAY="豆包流媒体 ASR"
elif [ "$TRANSCRIPTION_SERVICE" = "openai" ]; then
    SERVICE_DISPLAY="OpenAI GPT-4o"
else
    SERVICE_DISPLAY="${TRANSCRIPTION_SERVICE:-转录服务}"
fi

echo "📋 快捷键说明："
if [ -n "$HOLD_BUTTON" ]; then
    echo "   按住 ${KEY_DISPLAY}: 按住录音，松开转录 (${SERVICE_DISPLAY})"
else
    echo "   按住 Ctrl+F: 按住录音，松开转录 (${SERVICE_DISPLAY})"
    echo "   按住 Ctrl+I: 按住录音，松开转录 (本地 Whisper)"
fi
echo ""
echo "🔧 会话管理："
echo "   按 Ctrl+B 然后 D 可以分离会话"
echo "   使用 'tmux attach -t Whisper-Input-Next' 重新连接"
echo ""
echo "📝 日志文件: $LOG_FILE"
echo ""

tmux attach -t Whisper-Input-Next
