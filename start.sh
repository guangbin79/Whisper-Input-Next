#!/bin/bash

# Whisper-Input-Next 启动脚本 v2.0.0
# 用于启动语音转录工具

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
  if ! docker ps | grep -q "hx_asr_cpu"; then
    echo "⚠️  WeNet 服务未运行，请先执行: ./scripts/wenet_service.sh start"
    echo "   或修改 .env 中的 TRANSCRIPTION_SERVICE 使用其他服务"
    exit 1
  fi
fi

# 检查是否已有名为Whisper-Input-Next的会话
if tmux has-session -t Whisper-Input-Next 2>/dev/null; then
  echo "🔄 已有Whisper-Input-Next会话存在，将关闭旧会话并创建新会话..."
  tmux kill-session -t Whisper-Input-Next
fi

# 创建虚拟环境(如果不存在)
if [ ! -d ".venv" ]; then
  echo "🐍 创建虚拟环境..."
  python3 -m venv .venv
  echo "✅ 虚拟环境创建完成"
fi

# 检查依赖是否已安装
if [ ! -f ".venv/pyvenv.cfg" ] || [ ! -f "venv/lib/python*/site-packages/openai" ]; then
  echo "📦 安装项目依赖..."
  source .venv/bin/activate
  # Select requirements file based on platform
  if [[ "$(uname)" == "Darwin" ]]; then
    pip install -r requirements.txt
  else
    pip install -r requirements-linux.txt
  fi
  echo "✅ 依赖安装完成"
fi

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
echo "📋 快捷键说明："
echo "   按住 Ctrl+F: 按住录音，松开转录 (根据配置: 豆包/WeNet/OpenAI)"
echo "   按住 Ctrl+I: 按住录音，松开转录 (本地 Whisper)"
echo ""
echo "🔧 会话管理："
echo "   按 Ctrl+B 然后 D 可以分离会话"
echo "   使用 'tmux attach -t Whisper-Input-Next' 重新连接"
echo ""
echo "📝 日志文件: $LOG_FILE"
echo ""

tmux attach -t Whisper-Input-Next