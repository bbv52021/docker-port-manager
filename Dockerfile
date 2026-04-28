FROM python:3.11-slim

LABEL maintainer="Docker Port Manager Contributors"
LABEL description="群晖 Docker 端口转发管理工具"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends iputils-ping && \
    rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 创建数据目录
RUN mkdir -p /app/data

# 暴露 Web 端口
EXPOSE 5800

# 健康检查
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5800/api/system/health')" || exit 1

# 启动命令
CMD ["gunicorn", "--bind", "0.0.0.0:5800", "--workers", "1", "--threads", "4", "--timeout", "120", "app.main:create_app()"]
