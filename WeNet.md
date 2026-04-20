WeNet 流式ASR服务部署及测试

1. 下载WeNet 流式ASR模型

   ```shell
   git clone https://www.modelscope.cn/wenet/u2pp_conformer-asr-cn-16k-online.git
   cd u2pp_conformer-asr-cn-16k-online
   git lfs install
   git lfs pull
   ```

2. 部署WeNet 服务

   ```shell
   docker run -d \
     --name hx_asr_cpu \
     --restart unless-stopped \
     --cpus="4" \
     -e OMP_NUM_THREADS=4 \
     -p 10086:10086 \
     -v $(pwd)/u2pp_conformer-asr-cn-16k-online:/mnt/model \
     wenetorg/wenet:latest \
     /home/wenet/runtime/libtorch/build/bin/websocket_server_main \
       --port 10086 \
       --chunk_size 16 \
       --model_path /mnt/model/final.zip \
       --unit_path /mnt/model/units.txt
   ```

3. 运行测试脚本

   ```shell
   pip install sounddevice numpy websockets
   python3 wenet_test.py
   ```

   