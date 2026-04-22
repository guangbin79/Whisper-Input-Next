"""
WeNet 本地流式语音识别处理器

通过 WebSocket 连接本地 WeNet 服务，支持：
- 本地离线识别
- 实时流式转录
- 中文优化
"""

import asyncio
import json
from typing import Optional, Callable, AsyncGenerator

try:
    import websockets
except ImportError:
    websockets = None

from ..utils.logger import logger

DEFAULT_SAMPLE_RATE = 16000


class WeNetStreamingProcessor:
    """WeNet 本地流式语音识别处理器"""

    def __init__(self, ws_url: str = "ws://localhost:10086"):
        self.ws_url = ws_url
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._is_connected = False

    def is_available(self) -> bool:
        """检查 WeNet 服务是否可用"""
        if websockets is None:
            logger.warning("websockets 库未安装，WeNet 功能不可用")
            return False
        try:
            # 创建新的事件循环来运行异步检查
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._check_connection())
            loop.close()
            return result
        except Exception as e:
            logger.debug(f"WeNet 可用性检查失败: {e}")
            return False

    async def _check_connection(self) -> bool:
        """异步检查 WeNet 连接"""
        try:
            async with websockets.connect(self.ws_url, close_timeout=2) as ws:
                return True
        except Exception:
            return False

    async def connect(self) -> bool:
        """建立 WebSocket 连接"""
        try:
            self._ws = await websockets.connect(self.ws_url)
            self._is_connected = True
            logger.info("WeNet 本地 ASR 连接成功")
            return True
        except Exception as e:
            logger.error(f"连接 WeNet 失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        self._is_connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def process_audio_stream(
        self,
        audio_chunk_generator: AsyncGenerator[bytes, None],
        on_preview_text: Callable[[str], None],
        on_final_text: Callable[[str], None],
        on_complete: Callable[[], None],
        on_error: Callable[[str], None],
        sample_rate: int = DEFAULT_SAMPLE_RATE
    ):
        """
        流式处理音频

        Args:
            audio_chunk_generator: 异步生成器，yield 音频块 (bytes)
            on_preview_text: 收到文本更新时调用
            on_final_text: 流式结束后调用，传入最终完整文本
            on_complete: 转录完成时调用
            on_error: 发生错误时调用
            sample_rate: 音频采样率（默认 16000）
        """
        if not await self.connect():
            on_error("无法连接到 WeNet 服务，请确保服务已启动")
            return

        try:
            # 发送开始信号
            await self._ws.send(json.dumps({
                "signal": "start",
                "nbest": 1,
                "continuous_decoding": True
            }))

            final_text = ""
            accumulated_text = ""

            # 启动发送任务
            async def sender():
                chunk_count = 0
                async for chunk in audio_chunk_generator:
                    chunk_count += 1
                    await self._ws.send(chunk)
                # 发送结束信号
                await self._ws.send(json.dumps({"signal": "end"}))
                logger.info(f"WeNet: 发送完成，共 {chunk_count} 个音频块")

            # 启动接收任务
            async def receiver():
                nonlocal final_text, accumulated_text
                while True:
                    try:
                        raw_res = await asyncio.wait_for(
                            self._ws.recv(), timeout=5.0
                        )
                        data = json.loads(raw_res)

                        # 解析 nbest 字段
                        nbest_str = data.get('nbest', '')
                        if nbest_str and isinstance(nbest_str, str):
                            try:
                                nbest_list = json.loads(nbest_str)
                                if nbest_list and len(nbest_list) > 0:
                                    text = nbest_list[0].get('sentence', '')
                                    if data.get('type') == 'partial_result':
                                        on_preview_text(accumulated_text + text)
                                    else:
                                        accumulated_text += text
                                        final_text = accumulated_text
                                        on_preview_text(accumulated_text)
                            except json.JSONDecodeError:
                                pass

                        # 检查是否结束（发送方已完成）
                        # 注意：在 continuous_decoding 模式下，final_result 只是端点检测
                        # 不表示整个录音结束，所以不在这里 break
                        # 只有在连接关闭时才退出

                    except asyncio.TimeoutError:
                        # 检查发送方是否已完成
                        if sender_task.done():
                            break
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        break

            # 启动发送任务并保存引用
            sender_task = asyncio.create_task(sender())

            # 并行执行发送和接收
            await asyncio.gather(sender_task, receiver())

            # 输出最终文本
            if final_text:
                on_final_text(final_text)

            on_complete()

        except Exception as e:
            on_error(f"WeNet 处理失败: {e}")
        finally:
            await self.disconnect()
