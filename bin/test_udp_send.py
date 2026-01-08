"""
测试 UDP 发送 - 模拟 Max for Live 发送数据
用于测试 bridge.py 是否正常接收
"""

import socket
import json
import time

# 配置
TARGET_HOST = '127.0.0.1'
TARGET_PORT = 7400

# 测试数据
test_payload = {
    "full_track": [
        {"pitch": "C4", "start": 0, "duration": 1, "velocity": 100},
        {"pitch": "D4", "start": 1, "duration": 1, "velocity": 100},
        {"pitch": "E4", "start": 2, "duration": 1, "velocity": 100},
        {"pitch": "F4", "start": 3, "duration": 1, "velocity": 100},
    ],
    "added_notes": [
        {"pitch": "G4", "start": 4, "duration": 1, "velocity": 100},
        {"pitch": "A4", "start": 5, "duration": 1, "velocity": 100},
    ],
    "timestamp": "2026-01-04T12:00:00",
    "source": "Test Script"
}

def send_test_data():
    """发送测试数据到 bridge"""
    try:
        # 创建 UDP socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 转换为 JSON 并编码
        data = json.dumps(test_payload).encode('utf-8')
        
        print(f"📤 Sending test data to {TARGET_HOST}:{TARGET_PORT}")
        print(f"   Data size: {len(data)} bytes")
        print(f"   Full track: {len(test_payload['full_track'])} notes")
        print(f"   Added notes: {len(test_payload['added_notes'])} notes")
        print()
        print(f"Payload:")
        print(json.dumps(test_payload, indent=2))
        print()
        
        # 发送数据
        sock.sendto(data, (TARGET_HOST, TARGET_PORT))
        
        print(f"✅ Data sent successfully!")
        print(f"\nNow check:")
        print(f"1. Bridge terminal should show '📨 Received X bytes'")
        print(f"2. Bridge should show '✅ SUCCESS! Stored X notes in backend'")
        print(f"3. Backend terminal should show '🔵 Backend: Received POST to /bridge/result'")
        print(f"4. Frontend should be able to query: curl http://localhost:8000/bridge/latest")
        
        sock.close()
        
    except Exception as e:
        print(f"❌ Error sending data: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    print("=" * 60)
    print("UDP Test Sender - Testing Bridge Connection")
    print("=" * 60)
    print()
    print("⚠️  Make sure the following are running:")
    print("   1. Backend: python main.py")
    print("   2. Bridge: python midi_track_ctrl/bridge.py")
    print()
    input("Press Enter when ready to send test data...")
    print()
    
    send_test_data()
    
    print()
    print("=" * 60)
    print("Test complete! Check the terminals for output.")
    print("=" * 60)
