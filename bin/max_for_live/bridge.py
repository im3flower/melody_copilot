#!/usr/bin/env python3
"""
Max for Live 桥接脚本：接收 Max 发来的音符数据，POST 到后端，返回结果

使用 UDP 端口通信：
- 接收端口 7400：从 Max 接收 JSON payload
- 发送端口 7401：返回结果给 Max

HTTP 端点（由 FastAPI 后端集成）：
- GET /bridge/latest：获取最新的生成结果（供前端查询）
- GET /bridge/status：获取桥接状态

运行方式：
    python bridge.py
"""

import json
import socket
import sys
import threading
import urllib.request
import urllib.error
from typing import Any, Dict, Optional
from datetime import datetime

# 配置
LISTEN_PORT = 7400  # 接收 Max 数据
SEND_PORT = 7401    # 发送结果回 Max
MAX_HOST = "127.0.0.1"
BACKEND_URL = "http://127.0.0.1:8000/complete"
BUFFER_SIZE = 65536  # 64KB

# 全局状态（供 HTTP 端点查询）
latest_result: Optional[Dict[str, Any]] = None
latest_result_lock = threading.Lock()
last_update_time: Optional[str] = None


def send_to_max(sock: socket.socket, data: Dict[str, Any]) -> None:
    """发送数据回 Max"""
    try:
        msg = json.dumps(data).encode("utf-8")
        sock.sendto(msg, (MAX_HOST, SEND_PORT))
        print(f"✓ Sent response to Max ({len(msg)} bytes)")
    except Exception as e:
        print(f"✗ Failed to send to Max: {e}")


def post_to_backend(payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST 到后端 API"""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            BACKEND_URL,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=30) as response:
            resp_data = response.read().decode("utf-8")
            return json.loads(resp_data)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8") if e.fp else str(e)
        raise RuntimeError(f"Backend HTTP {e.code}: {error_body}") from e
    except Exception as e:
        raise RuntimeError(f"Backend error: {e}") from e


def store_result(result: Dict[str, Any]) -> None:
    """存储最新结果供前端查询"""
    global latest_result, last_update_time
    with latest_result_lock:
        latest_result = result
        last_update_time = datetime.now().isoformat()
    
    # 同时 POST 到后端存储
    try:
        data = json.dumps(result).encode("utf-8")
        req = urllib.request.Request(
            "http://127.0.0.1:8000/bridge/result",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            response.read()
    except Exception as e:
        print(f"⚠ Warning: Failed to notify backend: {e}")
    
    print(f"✓ Stored result for frontend (timestamp: {last_update_time})")


def main() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", LISTEN_PORT))
    
    print(f"Bridge listening on UDP port {LISTEN_PORT}")
    print(f"Will send responses to Max on port {SEND_PORT}")
    print(f"Backend: {BACKEND_URL}")
    print("Waiting for data from Max...\n")
    
    while True:
        try:
            data, addr = sock.recvfrom(BUFFER_SIZE)
            msg = data.decode("utf-8")
            print(f"← Received from {addr} ({len(data)} bytes)")
            
            payload = json.loads(msg)
            print(f"  Notes: {len(payload.get('original_notes', []))}")
            print(f"  Mood: {payload.get('mood')}, BPM: {payload.get('bpm')}")
            
            # POST 到后端
            print("→ Posting to backend...")
            result = post_to_backend(payload)
            print(f"✓ Backend responded: {len(result.get('added_notes', []))} new notes")
            
            # 存储结果供前端查询
            store_result(result)
            
            # 返回给 Max
            send_to_max(sock, result)
            print()
            
        except json.JSONDecodeError as e:
            print(f"✗ JSON decode error: {e}")
            send_to_max(sock, {"error": f"Invalid JSON: {e}"})
        except RuntimeError as e:
            print(f"✗ {e}")
            send_to_max(sock, {"error": str(e)})
        except KeyboardInterrupt:
            print("\nShutting down bridge...")
            break
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            send_to_max(sock, {"error": f"Bridge error: {e}"})
    
    sock.close()


if __name__ == "__main__":
    main()
