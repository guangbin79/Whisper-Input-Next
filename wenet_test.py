import asyncio
import json
import sounddevice as sd
import websockets

async def run_final_test():
    uri = "ws://localhost:10086"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({"signal": "start", "nbest": 1, "continuous_decoding": True}))
        
        audio_queue = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def callback(indata, frames, time, status):
            loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

        with sd.RawInputStream(samplerate=16000, blocksize=1024, dtype='int16', channels=1, callback=callback):
            while True:
                # 发送音频
                if not audio_queue.empty():
                    await websocket.send(await audio_queue.get())

                # 接收并处理嵌套 JSON
                try:
                    raw_res = await asyncio.wait_for(websocket.recv(), timeout=0.01)
                    data = json.loads(raw_res)
                    
                    # 关键逻辑：对 nbest 字段进行二次解析
                    nbest_str = data.get('nbest', '')
                    if nbest_str and isinstance(nbest_str, str):
                        try:
                            nbest_list = json.loads(nbest_str) # 二次解析
                            if nbest_list and len(nbest_list) > 0:
                                text = nbest_list[0].get('sentence', '')
                                if data.get('type') == 'partial_result':
                                    print(f"\r[识别中]: {text}", end='', flush=True)
                                else:
                                    print(f"\n[最终结果]: {text}\n")
                        except: pass
                except asyncio.TimeoutError:
                    pass

if __name__ == "__main__":
    asyncio.run(run_final_test())
