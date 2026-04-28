#!/bin/bash
# Docker Port Manager - 停止脚本

CONTAINER_NAME="docker-port-manager"

if docker ps --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    docker stop "${CONTAINER_NAME}"
    echo "✓ 容器已停止"
else
    echo "容器未在运行"
fi
