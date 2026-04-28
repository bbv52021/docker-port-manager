# Docker Port Manager 配置文件

# Web 服务配置
WEB_HOST = "0.0.0.0"
WEB_PORT = 5800

# Docker 配置
DOCKER_SOCKET = "/var/run/docker.sock"

# 转发容器配置
FORWARD_IMAGE = "alpine/socat:latest"
FORWARD_CONTAINER_PREFIX = "dpm-forward-"
FORWARD_NETWORK = "host"  # 推荐使用 host 模式，端口直接绑定宿主机

# 数据存储
DATA_DIR = "/app/data"
RULES_FILE = "rules.json"

# 预设协议模板
PRESET_PROTOCOLS = {
    "rdp": {"name": "远程桌面 (RDP)", "port": 3389, "protocol": "tcp", "description": "Windows 远程桌面"},
    "ssh": {"name": "SSH", "port": 22, "protocol": "tcp", "description": "Secure Shell"},
    "vnc": {"name": "VNC", "port": 5900, "protocol": "tcp", "description": "虚拟网络计算机"},
    "http": {"name": "HTTP", "port": 80, "protocol": "tcp", "description": "Web 服务"},
    "https": {"name": "HTTPS", "port": 443, "protocol": "tcp", "description": "安全 Web 服务"},
    "smb": {"name": "SMB/CIFS", "port": 445, "protocol": "tcp", "description": "文件共享"},
    "ftp": {"name": "FTP", "port": 21, "protocol": "tcp", "description": "文件传输"},
    "mysql": {"name": "MySQL", "port": 3306, "protocol": "tcp", "description": "MySQL 数据库"},
    "postgresql": {"name": "PostgreSQL", "port": 5432, "protocol": "tcp", "description": "PostgreSQL 数据库"},
    "redis": {"name": "Redis", "port": 6379, "protocol": "tcp", "description": "Redis 缓存"},
}
