"""
Docker 客户端封装 - 与群晖 Docker Engine 通信
"""

import docker
import logging
from typing import Dict, List, Optional, Any
from app.config import FORWARD_IMAGE, FORWARD_CONTAINER_PREFIX, FORWARD_NETWORK

logger = logging.getLogger(__name__)


class DockerClient:
    """Docker API 封装类"""

    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        self.socket_path = socket_path
        self.client: Optional[docker.DockerClient] = None
        self._connect()

    def _connect(self):
        """连接 Docker Engine"""
        try:
            self.client = docker.DockerClient(
                base_url=f"unix://{self.socket_path}",
                timeout=10
            )
            self.client.ping()
            logger.info("成功连接到 Docker Engine")
        except docker.errors.DockerException as e:
            logger.error(f"连接 Docker Engine 失败: {e}")
            raise ConnectionError(f"无法连接 Docker Engine: {e}")

    def get_containers(self, all_containers: bool = False) -> List[Dict]:
        """获取容器列表"""
        try:
            containers = self.client.containers.list(all=all_containers)
            result = []
            for c in containers:
                ports_info = []
                if c.attrs.get("NetworkSettings", {}).get("Ports"):
                    for port, bindings in c.attrs["NetworkSettings"]["Ports"].items():
                        if bindings:
                            for binding in bindings:
                                ports_info.append({
                                    "container_port": port,
                                    "host_ip": binding.get("HostIp", "0.0.0.0"),
                                    "host_port": binding.get("HostPort", "")
                                })
                result.append({
                    "id": c.short_id,
                    "name": c.name,
                    "image": str(c.image.tags[0]) if c.image.tags else str(c.image.id[:12]),
                    "status": c.status,
                    "state": c.attrs["State"]["Status"],
                    "created": c.attrs["Created"],
                    "ports": ports_info,
                    "labels": c.labels or {},
                })
            return result
        except docker.errors.DockerException as e:
            logger.error(f"获取容器列表失败: {e}")
            return []

    def get_used_ports(self) -> List[Dict]:
        """获取所有已使用的宿主机端口"""
        ports = []
        containers = self.client.containers.list(all=True)
        for c in containers:
            container_name = c.name
            network_settings = c.attrs.get("NetworkSettings", {}).get("Ports", {})
            if network_settings:
                for port_key, bindings in network_settings.items():
                    if bindings:
                        for binding in bindings:
                            host_port = binding.get("HostPort", "")
                            if host_port:
                                ports.append({
                                    "host_port": int(host_port),
                                    "container_port": port_key,
                                    "container_name": container_name,
                                    "host_ip": binding.get("HostIp", "0.0.0.0"),
                                })
        # 去重并排序
        seen = set()
        unique_ports = []
        for p in sorted(ports, key=lambda x: x["host_port"]):
            key = (p["host_port"], p["container_name"])
            if key not in seen:
                seen.add(key)
                unique_ports.append(p)
        return unique_ports

    def check_port_conflict(self, port: int) -> Optional[Dict]:
        """检查指定端口是否被占用"""
        used_ports = self.get_used_ports()
        for p in used_ports:
            if p["host_port"] == port:
                return p
        return None

    def create_forward_container(
        self,
        name: str,
        listen_port: int,
        target_host: str,
        target_port: int,
        protocol: str = "tcp",
        network_mode: str = None
    ) -> Dict:
        """创建端口转发容器"""
        container_name = f"{FORWARD_CONTAINER_PREFIX}{name}"

        # 默认使用配置中的网络模式
        if network_mode is None:
            network_mode = FORWARD_NETWORK

        # 检查端口冲突（host 模式下需要检查）
        if network_mode != "host":
            conflict = self.check_port_conflict(listen_port)
            if conflict:
                raise ValueError(
                    f"端口 {listen_port} 已被容器 '{conflict['container_name']}' 使用"
                )

        # 检查容器名是否已存在
        try:
            existing = self.client.containers.get(container_name)
            raise ValueError(f"转发规则 '{name}' 已存在（容器 {container_name}）")
        except docker.errors.NotFound:
            pass

        # 构建 socat 命令（支持 TCP 和 UDP）
        proto = protocol.lower()
        if proto == "udp":
            socat_cmd = (
                f"UDP-LISTEN:{listen_port},fork,reuseaddr "
                f"UDP:{target_host}:{target_port}"
            )
        else:
            socat_cmd = (
                f"TCP-LISTEN:{listen_port},fork,reuseaddr "
                f"TCP:{target_host}:{target_port}"
            )

        # 容器标签
        labels = {
            "dpm.managed": "true",
            "dpm.rule_name": name,
            "dpm.listen_port": str(listen_port),
            "dpm.target": f"{target_host}:{target_port}",
            "dpm.protocol": protocol,
        }

        # 构建运行参数
        run_kwargs = {
            "image": FORWARD_IMAGE,
            "name": container_name,
            "command": socat_cmd,
            "detach": True,
            "restart_policy": {"Name": "unless-stopped"},
            "labels": labels,
            "stdin_open": True,
            "tty": True,
        }

        # 根据网络模式配置端口映射
        if network_mode == "host":
            run_kwargs["network_mode"] = "host"
        else:
            # bridge 模式需要发布端口
            port_binding = f"{listen_port}/tcp" if proto == "tcp" else f"{listen_port}/udp"
            run_kwargs["ports"] = {port_binding: listen_port}

        try:
            container = self.client.containers.run(**run_kwargs)
            logger.info(f"创建转发容器成功: {container_name}")
            return {
                "id": container.short_id,
                "name": container_name,
                "status": "created",
                "listen_port": listen_port,
                "target": f"{target_host}:{target_port}",
                "created": container.attrs.get("Created", ""),
            }
        except docker.errors.DockerException as e:
            logger.error(f"创建转发容器失败: {e}")
            raise RuntimeError(f"创建容器失败: {e}")

    def remove_forward_container(self, name: str, force: bool = False) -> bool:
        """删除端口转发容器"""
        container_name = f"dpm-forward-{name}"
        try:
            container = self.client.containers.get(container_name)
            container.remove(force=force)
            logger.info(f"删除转发容器成功: {container_name}")
            return True
        except docker.errors.NotFound:
            raise ValueError(f"转发规则 '{name}' 不存在")
        except docker.errors.DockerException as e:
            logger.error(f"删除转发容器失败: {e}")
            raise RuntimeError(f"删除容器失败: {e}")

    def get_forward_containers(self) -> List[Dict]:
        """获取所有由 DPM 管理的转发容器"""
        containers = self.client.containers.list(
            all=True,
            filters={"label": "dpm.managed=true"}
        )
        result = []
        for c in containers:
            labels = c.labels or {}
            result.append({
                "id": c.short_id,
                "name": c.name,
                "status": c.status,
                "state": c.attrs["State"]["Status"],
                "rule_name": labels.get("dpm.rule_name", ""),
                "listen_port": int(labels.get("dpm.listen_port", 0)),
                "target": labels.get("dpm.target", ""),
                "protocol": labels.get("dpm.protocol", "tcp"),
                "created": c.attrs["Created"],
            })
        return result

    def start_container(self, name: str) -> bool:
        """启动容器"""
        container_name = f"dpm-forward-{name}"
        try:
            container = self.client.containers.get(container_name)
            container.start()
            return True
        except docker.errors.NotFound:
            raise ValueError(f"转发规则 '{name}' 不存在")

    def stop_container(self, name: str) -> bool:
        """停止容器"""
        container_name = f"dpm-forward-{name}"
        try:
            container = self.client.containers.get(container_name)
            container.stop()
            return True
        except docker.errors.NotFound:
            raise ValueError(f"转发规则 '{name}' 不存在")

    def get_container_logs(self, name: str, tail: int = 100) -> str:
        """获取容器日志"""
        container_name = f"dpm-forward-{name}"
        try:
            container = self.client.containers.get(container_name)
            return container.logs(tail=tail).decode("utf-8", errors="replace")
        except docker.errors.NotFound:
            raise ValueError(f"转发规则 '{name}' 不存在")

    def get_docker_info(self) -> Dict:
        """获取 Docker 引擎信息"""
        try:
            info = self.client.info()
            return {
                "version": info.get("ServerVersion", "unknown"),
                "containers": info.get("Containers", 0),
                "containers_running": info.get("ContainersRunning", 0),
                "images": info.get("Images", 0),
                "operating_system": info.get("OperatingSystem", "unknown"),
                "architecture": info.get("Architecture", "unknown"),
                "cpu_count": info.get("NCPU", 0),
                "total_memory": info.get("MemTotal", 0),
            }
        except docker.errors.DockerException as e:
            logger.error(f"获取 Docker 信息失败: {e}")
            return {}
