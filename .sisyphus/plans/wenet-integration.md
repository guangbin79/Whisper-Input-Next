# WeNet 本地离线 ASR 集成实施计划

## 项目背景

Whisper-Input-Next 是一个多服务语音识别输入工具，目前支持：
- 豆包流式 ASR（默认，WebSocket 实时流式）
- OpenAI GPT-4o transcribe（批量处理）
- 本地 Whisper.cpp（离线处理）
- 智谱 GLM-ASR、Groq Whisper 等

## WeNet 服务特点

根据 `WeNet.md`，WeNet 提供：
- **本地部署**：通过 Docker 运行，完全离线
- **WebSocket 流式接口**：`ws://localhost:10086`
- **中文优化**：基于 Conformer 的中文 ASR 模型
- **实时识别**：支持流式音频输入和实时返回结果

## 实施任务清单

### TODOs

- [x] **1. 创建 WeNet 处理器类**

  **What to do**:
  创建 `src/transcription/wenet_streaming.py`，实现 WeNet 本地流式 ASR 处理器
  
  **Implementation Details**:
  - 类名: `WeNetStreamingProcessor`
  - 方法: `__init__`, `is_available`, `connect`, `disconnect`, `process_audio_stream`
  - 使用 `websockets` 库连接 `ws://localhost:10086`
  - 协议: 发送 JSON `{"signal": "start", "nbest": 1, "continuous_decoding": True}`
  - 然后发送原始 PCM 音频字节
  - 接收 JSON 响应，解析 `nbest` 字段获取识别文本
  - 支持 `partial_result`（中间结果）和 `final_result`（最终结果）
  
  **Must NOT do**:
  - 不要修改其他文件
  - 不要添加新的依赖（使用已有的 websockets）
  
  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2 (main.py integration)
  - **Blocked By**: None
  
  **References**:
  - `src/transcription/doubao_streaming.py` - 流式处理器接口模式
  - `wenet_test.py` - WeNet WebSocket 协议实现
  - `src/audio/recorder.py:414-496` - stream_audio_chunks 方法
  
  **Acceptance Criteria**:
  - [ ] 文件 `src/transcription/wenet_streaming.py` 已创建
  - [ ] 类 `WeNetStreamingProcessor` 实现了所有必需方法
  - [ ] `is_available()` 能正确检测 WeNet 服务是否运行
  - [ ] `process_audio_stream()` 接受与豆包相同的回调签名
  
  **QA Scenarios**:
  ```
  Scenario: WeNet 服务未运行时
    Tool: Bash
    Preconditions: WeNet Docker 容器未启动
    Steps:
      1. python -c "from src.transcription.wenet_streaming import WeNetStreamingProcessor; p = WeNetStreamingProcessor(); print(p.is_available())"
    Expected Result: 输出 False
    Evidence: .sisyphus/evidence/task-1-wenet-unavailable.txt
  
  Scenario: WeNet 服务运行时
    Tool: Bash
    Preconditions: WeNet Docker 容器已启动 (docker run ...)
    Steps:
      1. python -c "from src.transcription.wenet_streaming import WeNetStreamingProcessor; p = WeNetStreamingProcessor(); print(p.is_available())"
    Expected Result: 输出 True
    Evidence: .sisyphus/evidence/task-1-wenet-available.txt
  ```

- [x] **2. 在 main.py 中集成 WeNet 处理器**

  **What to do**:
  修改 `main.py`，集成 WeNet 处理器到 VoiceAssistant 类
  
  **Implementation Details**:
  a) 导入 WeNet 处理器:
  ```python
  from src.transcription.wenet_streaming import WeNetStreamingProcessor
  ```
  
  b) 在 `VoiceAssistant.__init__` 中添加 `wenet_processor` 参数
  
  c) 在 Ctrl+F 路由中添加 WeNet 选项（优先级：wenet > doubao > glm-asr > groq > openai）
  
  d) 添加 WeNet 流式方法:
     - `start_wenet_streaming()` - 开始流式录音
     - `stop_wenet_streaming()` - 停止流式录音
     - `_run_wenet_streaming()` - 异步运行流式转录
  
  e) 在 `main()` 函数中初始化 WeNet 处理器（当 `WENET_ENABLED=true` 时）
  
  f) 在 `_handle_auto_stop` 和 `_handle_device_disconnect` 中处理 WENET_STREAMING 状态
  
  **Must NOT do**:
  - 不要破坏现有功能
  - 不要改变默认行为（豆包仍为默认）
  
  **Recommended Agent Profile**:
  - **Category**: `deep`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 2
  - **Blocks**: Task 7 (verification)
  - **Blocked By**: Task 1 (WeNet processor)
  
  **References**:
  - `main.py:53-128` - VoiceAssistant.__init__ 结构
  - `main.py:526-606` - 豆包流式方法实现
  - `main.py:632-719` - main() 函数处理器初始化
  
  **Acceptance Criteria**:
  - [ ] main.py 导入了 WeNetStreamingProcessor
  - [ ] VoiceAssistant 接受 wenet_processor 参数
  - [ ] Ctrl+F 路由支持 TRANSCRIPTION_SERVICE=wenet
  - [ ] 添加了 start_wenet_streaming, stop_wenet_streaming, _run_wenet_streaming 方法
  - [ ] main() 函数初始化 WeNet 处理器
  
  **QA Scenarios**:
  ```
  Scenario: 配置为 WeNet 模式时启动
    Tool: Bash
    Preconditions: .env 设置 TRANSCRIPTION_SERVICE=wenet, WENET_ENABLED=true
    Steps:
      1. python -c "import main; print('Import successful')"
    Expected Result: 成功导入，无错误
    Evidence: .sisyphus/evidence/task-2-import.txt
  ```

- [x] **3. 更新 InputState 添加 WENET_STREAMING 状态**

  **What to do**:
  修改 `src/keyboard/inputState.py`，添加 WENET_STREAMING 状态
  
  **Implementation Details**:
  ```python
  class InputState(Enum):
      # ... 现有状态 ...
      DOUBAO_STREAMING = auto()
      WENET_STREAMING = auto()  # 新增
      # ... 其他状态 ...
      
      @property
      def is_recording(self):
          return self in (
              # ... 现有状态 ...
              InputState.DOUBAO_STREAMING,
              InputState.WENET_STREAMING,  # 新增
          )
  ```
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2 (main.py), Task 4 (keyboard listener)
  - **Blocked By**: None
  
  **Acceptance Criteria**:
  - [ ] InputState.WENET_STREAMING 已添加
  - [ ] is_recording 属性包含 WENET_STREAMING

- [x] **4. 更新键盘监听器支持 WeNet 快捷键**

  **What to do**:
  修改 `src/keyboard/listener.py`，在状态消息映射中添加 WENET_STREAMING
  
  **Implementation Details**:
  在 `KeyboardManager.__init__` 的 `_state_messages` 字典中添加:
  ```python
  self._state_messages = {
      # ... 现有状态 ...
      InputState.DOUBAO_STREAMING: "0",  # 流式识别中显示 0
      # WENET_STREAMING 使用相同的 "0" 状态符号
  }
  ```
  
  注意：WeNet 使用与豆包相同的流式录音机制，不需要新的快捷键。
  Ctrl+F 根据 TRANSCRIPTION_SERVICE 配置自动选择处理器。
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: Task 2 (main.py)
  - **Blocked By**: Task 3 (InputState)
  
  **Acceptance Criteria**:
  - [ ] 键盘监听器正确处理 WENET_STREAMING 状态

- [x] **5. 添加 WeNet 环境变量配置**

  **What to do**:
  修改 `.env.example`，添加 WeNet 配置选项
  
  **Implementation Details**:
  ```bash
  # ===== WeNet 本地 ASR 配置 (可选) =====
  # 启用 WeNet 本地离线识别
  # WENET_ENABLED=true
  # WeNet WebSocket 服务地址（默认 localhost:10086）
  # WENET_WS_URL=ws://localhost:10086
  
  # 转录服务选择: "doubao" (默认) / "wenet" (本地) / "openai" / "glm-asr" / "groq"
  # TRANSCRIPTION_SERVICE=wenet
  ```
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: None
  - **Blocked By**: None
  
  **Acceptance Criteria**:
  - [ ] .env.example 包含 WENET_ENABLED 和 WENET_WS_URL 配置

- [x] **6. 创建 WeNet 服务管理脚本**

  **What to do**:
  创建 `scripts/wenet_service.sh`，管理 WeNet Docker 服务
  
  **Implementation Details**:
  ```bash
  #!/bin/bash
  
  MODEL_DIR="./u2pp_conformer-asr-cn-16k-online"
  CONTAINER_NAME="hx_asr_cpu"
  
  start() {
      echo "启动 WeNet 服务..."
      docker run -d \
          --name $CONTAINER_NAME \
          --restart unless-stopped \
          --cpus="4" \
          -e OMP_NUM_THREADS=4 \
          -p 10086:10086 \
          -v $(pwd)/$MODEL_DIR:/mnt/model \
          wenetorg/wenet:latest \
          /home/wenet/runtime/libtorch/build/bin/websocket_server_main \
              --port 10086 \
              --chunk_size 16 \
              --model_path /mnt/model/final.zip \
              --unit_path /mnt/model/units.txt
      echo "WeNet 服务已启动 (ws://localhost:10086)"
  }
  
  stop() {
      echo "停止 WeNet 服务..."
      docker stop $CONTAINER_NAME
      docker rm $CONTAINER_NAME
      echo "WeNet 服务已停止"
  }
  
  status() {
      if docker ps | grep -q $CONTAINER_NAME; then
          echo "WeNet 服务运行中"
      else
          echo "WeNet 服务未运行"
      fi
  }
  
  case "$1" in
      start)
          start
          ;;
      stop)
          stop
          ;;
      restart)
          stop
          start
          ;;
      status)
          status
          ;;
      *)
          echo "用法: $0 {start|stop|restart|status}"
          exit 1
          ;;
  esac
  ```
  
  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: YES
  - **Parallel Group**: Wave 1
  - **Blocks**: None
  - **Blocked By**: None
  
  **Acceptance Criteria**:
  - [ ] scripts/wenet_service.sh 已创建
  - [ ] 脚本支持 start/stop/restart/status 命令

- [x] **7. 验证和测试集成**

  **What to do**:
  验证所有修改是否正确，测试 WeNet 集成
  
  **Implementation Details**:
  1. 检查所有文件修改是否正确
  2. 运行 Python 语法检查
  3. 测试导入是否成功
  4. 验证 WeNet 服务检测
  
  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: []
  
  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Wave 3 (Final)
  - **Blocks**: None
  - **Blocked By**: Tasks 1-6
  
  **Acceptance Criteria**:
  - [ ] Python 语法检查通过
  - [ ] 导入测试通过
  - [ ] 所有文件修改符合预期
  
  **QA Scenarios**:
  ```
  Scenario: 完整集成测试
    Tool: Bash
    Preconditions: 所有代码修改完成
    Steps:
      1. python -m py_compile main.py
      2. python -m py_compile src/transcription/wenet_streaming.py
      3. python -m py_compile src/keyboard/inputState.py
      4. python -c "from src.transcription.wenet_streaming import WeNetStreamingProcessor; print('WeNet import OK')"
    Expected Result: 所有命令成功执行，无错误
    Evidence: .sisyphus/evidence/task-7-verification.txt
  ```

## 执行策略

### 并行执行波次

```
Wave 1 (Start Immediately - 基础文件):
├── Task 1: 创建 WeNet 处理器类
├── Task 3: 更新 InputState
├── Task 4: 更新键盘监听器
├── Task 5: 添加环境变量配置
└── Task 6: 创建服务管理脚本

Wave 2 (After Wave 1 - 核心集成):
└── Task 2: 在 main.py 中集成 WeNet 处理器

Wave 3 (After Wave 2 - 验证):
└── Task 7: 验证和测试集成
```

### 依赖矩阵

- **Task 1**: None → Blocks Task 2
- **Task 2**: Task 1 → Blocks Task 7
- **Task 3**: None → Blocks Task 2, Task 4
- **Task 4**: Task 3 → Blocks Task 2
- **Task 5**: None → No blocks
- **Task 6**: None → No blocks
- **Task 7**: Tasks 1-6 → No blocks

## 使用方式

1. 启动 WeNet 服务：
   ```bash
   ./scripts/wenet_service.sh start
   ```

2. 配置环境变量（在 .env 文件中）：
   ```bash
   WENET_ENABLED=true
   TRANSCRIPTION_SERVICE=wenet
   ```

3. 运行程序：
   ```bash
   python main.py
   ```

4. 使用 Ctrl+F 触发 WeNet 本地流式识别

## 优势

- **完全离线**：不需要网络连接，保护隐私
- **中文优化**：基于 Conformer 的中文 ASR 模型
- **实时流式**：边说边转，体验与豆包类似
- **本地部署**：数据不上传，安全性高
- **成本为零**：无需 API 费用

## 注意事项

1. **Docker 依赖**：需要安装 Docker 来运行 WeNet 服务
2. **模型下载**：首次使用需要下载模型（约 300MB）
3. **资源占用**：CPU 占用较高（建议 4 核以上）
4. **识别准确率**：可能略低于云端服务（如豆包、OpenAI）
5. **启动时间**：Docker 容器启动需要几秒钟
