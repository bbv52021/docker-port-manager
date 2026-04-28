"""
Flask Web API 路由
"""

import logging
from flask import Blueprint, jsonify, request
from app.core.docker_client import DockerClient
from app.core.forward_engine import ForwardEngine
from app.services.network_tools import NetworkTools
from app.config import DOCKER_SOCKET

logger = logging.getLogger(__name__)

api_bp = Blueprint("api", __name__, url_prefix="/api")

# 全局实例
docker_client: DockerClient = None
forward_engine: ForwardEngine = None
network_tools = NetworkTools()


def init_api():
    """初始化 API（在 app 启动时调用）"""
    global docker_client, forward_engine
    docker_client = DockerClient(socket_path=DOCKER_SOCKET)
    forward_engine = ForwardEngine(docker_client)


# ============ 系统 API ============

@api_bp.route("/system/info", methods=["GET"])
def get_system_info():
    """获取系统信息"""
    try:
        docker_info = docker_client.get_docker_info()
        local_ip = network_tools.get_local_ip()
        return jsonify({
            "success": True,
            "data": {
                "docker": docker_info,
                "local_ip": local_ip,
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/system/health", methods=["GET"])
def health_check():
    """健康检查"""
    try:
        docker_client.client.ping()
        return jsonify({"success": True, "message": "系统正常运行"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 503


# ============ 容器 API ============

@api_bp.route("/containers", methods=["GET"])
def get_containers():
    """获取所有容器列表"""
    try:
        all_containers = request.args.get("all", "false").lower() == "true"
        containers = docker_client.get_containers(all_containers=all_containers)
        return jsonify({"success": True, "data": containers})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ 端口 API ============

@api_bp.route("/ports", methods=["GET"])
def get_ports():
    """获取端口使用情况"""
    try:
        status = forward_engine.get_port_status()
        return jsonify({"success": True, "data": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/ports/check/<int:port>", methods=["GET"])
def check_port(port):
    """检查指定端口是否可用"""
    try:
        result = forward_engine.check_port_available(port)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ 转发规则 API ============

@api_bp.route("/rules", methods=["GET"])
def get_rules():
    """获取所有转发规则"""
    try:
        rules = forward_engine.get_all_rules()
        return jsonify({"success": True, "data": rules})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/rules", methods=["POST"])
def create_rule():
    """创建转发规则"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "请求数据为空"}), 400

        name = data.get("name", "").strip()
        listen_port = data.get("listen_port")
        target_host = data.get("target_host", "").strip()
        target_port = data.get("target_port")
        protocol = data.get("protocol", "tcp")
        description = data.get("description", "")
        preset = data.get("preset", "")

        # 参数校验
        if not name:
            return jsonify({"success": False, "error": "规则名称不能为空"}), 400
        if not listen_port or not (1 <= listen_port <= 65535):
            return jsonify({"success": False, "error": "监听端口无效 (1-65535)"}), 400
        if not target_host:
            return jsonify({"success": False, "error": "目标地址不能为空"}), 400
        if not target_port or not (1 <= target_port <= 65535):
            return jsonify({"success": False, "error": "目标端口无效 (1-65535)"}), 400

        # 名称合法性检查
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', name):
            return jsonify({"success": False, "error": "规则名称只能包含字母、数字、下划线和连字符"}), 400

        result = forward_engine.create_rule(
            name=name,
            listen_port=int(listen_port),
            target_host=target_host,
            target_port=int(target_port),
            protocol=protocol,
            description=description,
            preset=preset,
        )
        return jsonify(result), 201
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        logger.error(f"创建规则失败: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/rules/<name>", methods=["DELETE"])
def delete_rule(name):
    """删除转发规则"""
    try:
        result = forward_engine.delete_rule(name)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/rules/<name>/start", methods=["POST"])
def start_rule(name):
    """启动转发规则"""
    try:
        result = forward_engine.start_rule(name)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/rules/<name>/stop", methods=["POST"])
def stop_rule(name):
    """停止转发规则"""
    try:
        result = forward_engine.stop_rule(name)
        return jsonify(result)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/rules/<name>/logs", methods=["GET"])
def get_rule_logs(name):
    """获取规则日志"""
    try:
        tail = request.args.get("tail", 100, type=int)
        logs = forward_engine.get_rule_logs(name, tail=tail)
        return jsonify({"success": True, "data": logs})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ============ 预设 API ============

@api_bp.route("/presets", methods=["GET"])
def get_presets():
    """获取预设协议模板"""
    presets = forward_engine.get_presets()
    return jsonify({"success": True, "data": presets})


# ============ 网络工具 API ============

@api_bp.route("/network/ping", methods=["POST"])
def ping_host():
    """Ping 测试"""
    try:
        data = request.get_json()
        host = data.get("host", "").strip()
        count = data.get("count", 4)

        if not host:
            return jsonify({"success": False, "error": "目标地址不能为空"}), 400

        result = network_tools.ping(host, count=count)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/network/port-test", methods=["POST"])
def test_port():
    """端口连通性测试"""
    try:
        data = request.get_json()
        host = data.get("host", "").strip()
        port = data.get("port")

        if not host:
            return jsonify({"success": False, "error": "目标地址不能为空"}), 400
        if not port or not (1 <= port <= 65535):
            return jsonify({"success": False, "error": "端口号无效 (1-65535)"}), 400

        result = network_tools.test_port(host, int(port))
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route("/network/dns", methods=["POST"])
def dns_resolve():
    """DNS 解析"""
    try:
        data = request.get_json()
        host = data.get("host", "").strip()

        if not host:
            return jsonify({"success": False, "error": "域名不能为空"}), 400

        result = network_tools.dns_resolve(host)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
