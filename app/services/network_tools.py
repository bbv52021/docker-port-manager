"""
网络工具模块 - Ping、端口连通性测试等
"""

import socket
import subprocess
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class NetworkTools:
    """网络诊断工具"""

    @staticmethod
    def ping(host: str, count: int = 4, timeout: int = 5) -> Dict:
        """
        Ping 测试
        返回: {success, host, packets_sent, packets_received, packet_loss, avg_time, output}
        """
        try:
            # 使用系统 ping 命令
            cmd = ["ping", "-c", str(count), "-W", str(timeout), host]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=count * timeout + 5
            )
            output = result.stdout + result.stderr

            # 解析结果
            packets_sent = 0
            packets_received = 0
            avg_time = 0

            # 解析 Linux/macOS ping 输出
            loss_match = re.search(r"(\d+) packets transmitted, (\d+) (?:packets )?received", output)
            if loss_match:
                packets_sent = int(loss_match.group(1))
                packets_received = int(loss_match.group(2))

            time_match = re.search(
                r"(?:rtt|round-trip).*=.*?([\d.]+)/([\d.]+)/([\d.]+)",
                output
            )
            if time_match:
                avg_time = float(time_match.group(2))

            packet_loss = (
                ((packets_sent - packets_received) / packets_sent * 100)
                if packets_sent > 0
                else 0
            )

            return {
                "success": packets_received > 0,
                "host": host,
                "packets_sent": packets_sent,
                "packets_received": packets_received,
                "packet_loss": round(packet_loss, 1),
                "avg_time_ms": round(avg_time, 2),
                "output": output.strip(),
            }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "host": host,
                "error": "Ping 超时",
                "output": "",
            }
        except Exception as e:
            return {
                "success": False,
                "host": host,
                "error": str(e),
                "output": "",
            }

    @staticmethod
    def test_port(host: str, port: int, timeout: int = 3) -> Dict:
        """
        测试端口连通性
        返回: {open, host, port, response_time_ms}
        """
        try:
            import time
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            start = time.time()
            result = sock.connect_ex((host, port))
            elapsed = (time.time() - start) * 1000
            sock.close()

            return {
                "open": result == 0,
                "host": host,
                "port": port,
                "response_time_ms": round(elapsed, 2),
                "error": None if result == 0 else f"连接被拒绝 (错误码: {result})",
            }
        except socket.timeout:
            return {
                "open": False,
                "host": host,
                "port": port,
                "response_time_ms": timeout * 1000,
                "error": "连接超时",
            }
        except socket.gaierror as e:
            return {
                "open": False,
                "host": host,
                "port": port,
                "response_time_ms": 0,
                "error": f"DNS 解析失败: {e}",
            }
        except Exception as e:
            return {
                "open": False,
                "host": host,
                "port": port,
                "response_time_ms": 0,
                "error": str(e),
            }

    @staticmethod
    def test_port_range(host: str, start_port: int, end_port: int,
                        timeout: int = 1) -> List[Dict]:
        """
        扫描端口范围
        """
        results = []
        for port in range(start_port, end_port + 1):
            result = NetworkTools.test_port(host, port, timeout)
            results.append(result)
        return results

    @staticmethod
    def dns_resolve(host: str) -> Dict:
        """DNS 解析"""
        try:
            ip = socket.gethostbyname(host)
            return {
                "success": True,
                "host": host,
                "ip": ip,
            }
        except socket.gaierror as e:
            return {
                "success": False,
                "host": host,
                "error": str(e),
            }

    @staticmethod
    def get_local_ip() -> str:
        """获取本机 IP"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"
