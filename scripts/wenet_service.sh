#!/bin/bash

# WeNet 服务管理脚本

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
