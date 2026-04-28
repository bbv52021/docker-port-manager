"""
端口转发管理引擎
"""

import json
import os
import logging
from typing import Dict, List, Optional
from app.core.docker_client import DockerClient
from app.config import DATA_DIR, RULES_FILE, PRESET_PROTOCOLS

logger = logging.getLogger(__name__)


class ForwardEngine:
    """端口转发管理引擎"""

    def __init__(self, docker_client: DockerClient):
        self.docker = docker_client
        self.data_dir = DATA_DIR
        self.rules_file = os.path.join(self.data_dir, RULES_FILE)
        os.makedirs(self.data_dir, exist_ok=True)

    def _load_rules(self) -> Dict:
        """从文件加载规则"""
        if os.path.exists(self.rules_file):
            try:
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"加载规则文件失败: {e}")
        return {}

    def _save_rules(self, rules: Dict):
        """保存规则到文件"""
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
        except IOError as e:
            logger.error(f"保存规则文件失败: {e}")

    def create_rule(
        self,
        name: str,
        listen_port: int,
        target_host: str,
        target_port: int,
        protocol: str = "tcp",
        description: str = "",
        preset: str = ""
    ) -> Dict:
        """创建端口转发规则"""
        # 检查端口冲突
        conflict = self.docker.check_port_conflict(listen_port)
        if conflict:
            raise ValueError(
                f"端口 {listen_port} 已被容器 '{conflict['container_name']}' 占用 "
                f"（{conflict['container_port']}）"
            )

        # 创建转发容器
        result = self.docker.create_forward_container(
            name=name,
            listen_port=listen_port,
            target_host=target_host,
            target_port=target_port,
            protocol=protocol,
        )

        # 保存规则记录
        rules = self._load_rules()
        rules[name] = {
            "listen_port": listen_port,
            "target_host": target_host,
            "target_port": target_port,
            "protocol": protocol,
            "description": description,
            "preset": preset,
            "created": result.get("created", ""),
        }
        self._save_rules(rules)

        return {
            "success": True,
            "message": f"转发规则 '{name}' 创建成功",
            "data": {
                "name": name,
                "listen_port": listen_port,
                "target": f"{target_host}:{target_port}",
                "protocol": protocol,
                "container_id": result["id"],
            }
        }

    def delete_rule(self, name: str) -> Dict:
        """删除端口转发规则"""
        self.docker.remove_forward_container(name, force=True)

        rules = self._load_rules()
        if name in rules:
            del rules[name]
            self._save_rules(rules)

        return {"success": True, "message": f"转发规则 '{name}' 已删除"}

    def start_rule(self, name: str) -> Dict:
        """启动转发规则"""
        self.docker.start_container(name)
        return {"success": True, "message": f"转发规则 '{name}' 已启动"}

    def stop_rule(self, name: str) -> Dict:
        """停止转发规则"""
        self.docker.stop_container(name)
        return {"success": True, "message": f"转发规则 '{name}' 已停止"}

    def get_all_rules(self) -> List[Dict]:
        """获取所有转发规则（合并容器状态和规则配置）"""
        containers = self.docker.get_forward_containers()
        rules = self._load_rules()

        # 以容器列表为主，补充规则文件中的额外信息
        result = []
        for c in containers:
            rule_name = c["rule_name"]
            rule_config = rules.get(rule_name, {})
            result.append({
                "name": rule_name,
                "listen_port": c["listen_port"],
                "target": c["target"],
                "protocol": c["protocol"],
                "status": c["status"],
                "state": c["state"],
                "container_id": c["id"],
                "description": rule_config.get("description", ""),
                "preset": rule_config.get("preset", ""),
                "created": c.get("created", ""),
            })

        return result

    def get_rule_logs(self, name: str, tail: int = 100) -> str:
        """获取规则日志"""
        return self.docker.get_container_logs(name, tail=tail)

    def get_port_status(self) -> Dict:
        """获取端口使用概况"""
        used_ports = self.docker.get_used_ports()
        forward_ports = self.docker.get_forward_containers()

        forward_port_numbers = {c["listen_port"] for c in forward_ports}

        return {
            "total_used_ports": len(used_ports),
            "forward_rules_count": len(forward_ports),
            "used_ports": used_ports,
            "forward_ports": [
                {
                    "port": c["listen_port"],
                    "target": c["target"],
                    "name": c["rule_name"],
                    "status": c["status"],
                }
                for c in forward_ports
            ],
        }

    def get_presets(self) -> Dict:
        """获取预设协议模板"""
        return PRESET_PROTOCOLS

    def check_port_available(self, port: int) -> Dict:
        """检查端口是否可用"""
        conflict = self.docker.check_port_conflict(port)
        if conflict:
            return {
                "available": False,
                "port": port,
                "conflict": conflict,
            }
        return {
            "available": True,
            "port": port,
        }
