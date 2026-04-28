#!/bin/bash
# Docker Port Manager - 快速启动脚本

set -e

IMAGE_NAME="docker-port-manager"
CONTAINER_NAME="docker-port-manager"
PORT=5800

echo "========================================="
echo "  Docker Port Manager - 端口转发管理工具"
echo "========================================="
echo ""

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker 未运行，请先启动 Docker"
    exit 1
fi

# 检查容器是否已存在
if docker ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
    echo "⚠️  容器 ${CONTAINER_NAME} 已存在"
    read -p "是否删除并重新创建？(y/N): " confirm
    if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
        docker rm -f "${CONTAINER_NAME}" > /dev/null 2>&1
        echo "✓ 已删除旧容器"
    else
        echo "操作取消"
        exit 0
    fi
fi

# 构建镜像
echo "🔨 正在构建 Docker 镜像..."
docker build -t "${IMAGE_NAME}:latest" .

# 创建数据目录
mkdir -p ./data

# 启动容器（使用 host 网络模式，转发容器可直接绑定宿主机端口）
echo "🚀 正在启动容器..."
docker run -d \
    --name "${CONTAINER_NAME}" \
    --restart unless-stopped \
    --network host \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v "$(pwd)/data:/app/data" \
    -e TZ=Asia/Shanghai \
    "${IMAGE_NAME}:latest"

echo ""
echo "========================================="
echo "  ✅ 启动成功！"
echo "========================================="
echo ""
echo "  访问地址: http://localhost:${PORT}"
echo "  数据目录: $(pwd)/data"
echo ""
echo "  停止: docker stop ${CONTAINER_NAME}"
echo "  删除: docker rm -f ${CONTAINER_NAME}"
echo "  日志: docker logs -f ${CONTAINER_NAME}"
echo ""
