# Docker Port Manager (DPM)

> 群晖 Docker 端口转发管理工具 — 通过 Web UI 轻松管理 Docker 端口转发，支持 SSH、RDP 等常用协议的快捷配置，自动检测端口冲突。

## 功能特性

- **端口转发管理** — 通过 Web UI 创建、启动、停止、删除端口转发规则
- **快捷模板** — 内置 RDP、SSH、VNC、HTTP、MySQL 等常用协议预设
- **端口冲突检测** — 自动扫描已用端口，创建规则时实时检查冲突
- **网络工具** — 集成 Ping 测试、端口连通性检测、DNS 解析
- **容器管理** — 查看所有 Docker 容器状态和端口映射
- **深色主题** — 现代化的深色 Web 界面，响应式设计

## 适用场景

```
公司电脑 ←—(节点小宝/VPN)—→ 群晖 NAS ←—(局域网)—→ 家中其他电脑
```

当你使用节点小宝等异地组网工具连接群晖时，免费账户通常只能开通 2 个节点。通过 DPM，你可以在群晖上创建端口转发规则，将 RDP、SSH 等端口转发到局域网内的其他电脑，无需额外开通节点。

## 快速开始

### 方式一：Docker Compose（推荐）

```bash
git clone https://github.com/your-username/docker-port-manager.git
cd docker-port-manager
docker compose up -d
```

### 方式二：Docker 命令

```bash
docker run -d \
    --name docker-port-manager \
    --restart unless-stopped \
    -p 5800:5800 \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v ./data:/app/data \
    -e TZ=Asia/Shanghai \
    docker-port-manager:latest
```

### 方式三：脚本启动

```bash
git clone https://github.com/your-username/docker-port-manager.git
cd docker-port-manager
chmod +x scripts/*.sh
./scripts/start.sh
```

启动后访问 **http://群晖IP:5800** 即可使用。

## 群晖安装指南

1. **开启 SSH**：控制面板 → 终端机和 SNMP → 勾选"启动 SSH 功能"
2. **SSH 登录群晖**：
   ```bash
   ssh admin@群晖IP
   sudo -i  # 切换到 root
   ```
3. **下载并启动**：
   ```bash
   cd /volume1/docker/
   git clone https://github.com/your-username/docker-port-manager.git
   cd docker-port-manager
   docker compose up -d
   ```
4. **访问**：浏览器打开 `http://群晖IP:5800`

## 使用方法

### 创建 RDP 转发规则

1. 点击 **"新建规则"** 按钮
2. 选择快捷模板 **"远程桌面 (RDP) - 3389"**
3. 填写规则名称（如 `office-rdp`）
4. 填写目标电脑的局域网 IP（如 `192.168.1.100`）
5. 监听端口和目标端口会自动填入 3389（如有冲突可修改监听端口）
6. 点击 **"创建规则"**

### 远程连接

创建规则后，在公司电脑上：

- **RDP**：打开 mstsc，输入 `群晖VPN_IP:3389`
- **SSH**：`ssh user@群晖VPN_IP -p 监听端口`
- **VNC**：VNC 客户端连接 `群晖VPN_IP:监听端口`

## 项目结构

```
docker-port-manager/
├── app/
│   ├── __init__.py
│   ├── main.py              # Flask 应用入口
│   ├── config.py            # 配置文件
│   ├── api/
│   │   └── routes.py        # REST API 路由
│   ├── core/
│   │   ├── docker_client.py # Docker API 封装
│   │   └── forward_engine.py# 端口转发引擎
│   ├── services/
│   │   └── network_tools.py # 网络工具
│   ├── static/
│   │   ├── css/style.css    # 样式
│   │   └── js/app.js        # 前端逻辑
│   └── templates/
│       └── index.html       # 主页面
├── scripts/
│   ├── start.sh             # 启动脚本
│   └── stop.sh              # 停止脚本
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── LICENSE
└── README.md
```

## API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/system/info` | 系统信息 |
| GET | `/api/system/health` | 健康检查 |
| GET | `/api/containers` | 容器列表 |
| GET | `/api/ports` | 端口使用状态 |
| GET | `/api/ports/check/<port>` | 检查端口冲突 |
| GET | `/api/rules` | 转发规则列表 |
| POST | `/api/rules` | 创建转发规则 |
| DELETE | `/api/rules/<name>` | 删除转发规则 |
| POST | `/api/rules/<name>/start` | 启动规则 |
| POST | `/api/rules/<name>/stop` | 停止规则 |
| GET | `/api/rules/<name>/logs` | 查看日志 |
| GET | `/api/presets` | 预设协议列表 |
| POST | `/api/network/ping` | Ping 测试 |
| POST | `/api/network/port-test` | 端口测试 |
| POST | `/api/network/dns` | DNS 解析 |

## 技术栈

- **后端**：Python 3.11 + Flask + Docker SDK
- **前端**：原生 HTML/CSS/JavaScript（无框架依赖）
- **转发引擎**：alpine/socat 容器
- **部署**：Docker + Docker Compose

## 配置说明

在 `app/config.py` 中可修改以下配置：

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| WEB_PORT | 5800 | Web 管理界面端口 |
| DOCKER_SOCKET | /var/run/docker.sock | Docker Socket 路径 |
| FORWARD_IMAGE | alpine/socat:latest | 转发容器镜像 |
| FORWARD_NETWORK | bridge | 容器网络模式 |

## 注意事项

- 本工具需要挂载 `/var/run/docker.sock`，请确保安全
- 转发容器默认使用 `bridge` 网络模式，如需转发到宿主机网络请改为 `host`
- 建议配合强密码使用，避免暴露在公网
- 删除规则会同时删除对应的 Docker 容器

## 许可证

[MIT License](LICENSE)

## 贡献

欢迎提交 Issue 和 Pull Request！
