"""
UDP Bridge: Relays MIDI data from Max for Live (UDP port 7400) to FastAPI backend
Captures note data and stores it via HTTP POST to /bridge/result
"""

import socket
import json
import threading
import time
import urllib.request
import urllib.error
from datetime import datetime

# Configuration
LISTEN_PORT = 7400          # Port to receive from Max (UDP)
SEND_PORT = 7401            # Port to send to Max (UDP)
BACKEND_URL = "http://localhost:8000/bridge/result"
BACKEND_POLL_URL = "http://localhost:8000/bridge/latest"

# State
latest_result = None
listening = False
lock = threading.Lock()


def store_result(payload):
    """Send result to backend via HTTP POST"""
    print(f"\n🔄 Attempting to store result in backend...")
    print(f"   Payload keys: {list(payload.keys())}")
    print(f"   Full track notes: {len(payload.get('full_track', []))}")
    print(f"   Added notes: {len(payload.get('added_notes', []))}")
    
    try:
        data = json.dumps(payload).encode('utf-8')
        print(f"   Sending to: {BACKEND_URL}")
        req = urllib.request.Request(
            BACKEND_URL,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            resp_data = response.read().decode('utf-8')
            print(f"✅ SUCCESS! Stored {len(payload.get('added_notes', []))} notes in backend")
            print(f"   Backend response: {resp_data}")
            return json.loads(resp_data)
    except urllib.error.URLError as e:
        print(f"❌ Failed to POST to backend: {e}")
        print(f"   URL: {BACKEND_URL}")
        print(f"   Is backend running on port 8000?")
    except Exception as e:
        print(f"❌ Error storing result: {e}")
    return None


def listen_udp():
    """Listen for UDP packets from Max on port 7400"""
    global latest_result
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        sock.bind(('127.0.0.1', LISTEN_PORT))
        print(f"📡 Listening on UDP port {LISTEN_PORT}")
        
        while True:
            try:
                data, addr = sock.recvfrom(8192)
                print(f"\n📨 ========== NEW UDP PACKET ===========")
                print(f"   Received {len(data)} bytes from {addr}")
                print(f"   Raw data preview: {data[:100]}...")
                
                try:
                    text = data.decode('utf-8', errors='replace')
                    try:
                        payload = json.loads(text)
                    except json.JSONDecodeError:
                        # Some Max patches prepend symbols like "send" or "send,s".
                        # Strategy: locate the first "{" and last "}" and parse that slice.
                        lbrace = text.find('{')
                        rbrace = text.rfind('}')
                        if lbrace != -1 and rbrace != -1 and rbrace > lbrace:
                            candidate = text[lbrace:rbrace+1]
                            print("ℹ Detected prefix before JSON, retrying parse on braces slice")
                            payload = json.loads(candidate)
                        else:
                            raise

                    print(f"✅ JSON parsed successfully")
                    print(f"   Keys found: {list(payload.keys())}")

                    # Validate payload structure
                    if 'full_track' in payload and 'added_notes' in payload:
                        print(f"✅ Payload structure valid")
                        with lock:
                            latest_result = payload
                        
                        # Store in backend
                        store_result(payload)
                    else:
                        print(f"❌ Invalid payload structure")
                        print(f"   Expected keys: ['full_track', 'added_notes']")
                        print(f"   Found keys: {list(payload.keys())}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse JSON: {e}")
                    print(f"   Data: {text[:200]}")
                except Exception as e:
                    print(f"❌ Error processing payload: {e}")
                    import traceback
                    traceback.print_exc()
                    
            except socket.timeout:
                continue
            except Exception as e:
                print(f"⚠ Error receiving: {e}")
                
    except Exception as e:
        print(f"✗ Failed to bind UDP socket: {e}")
    finally:
        sock.close()


def send_udp(message, port=SEND_PORT):
    """Send UDP message to Max on specified port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(json.dumps(message).encode('utf-8'), ('127.0.0.1', port))
        sock.close()
        print(f"📤 Sent to port {port}: {message}")
    except Exception as e:
        print(f"✗ Failed to send UDP: {e}")


def start_listening_thread():
    """Start UDP listener in background thread"""
    thread = threading.Thread(target=listen_udp, daemon=True)
    thread.start()
    return thread


if __name__ == '__main__':
    print("🎹 MIDI Bridge (Max for Live ↔ FastAPI Backend)")
    print(f"   Listening on UDP {LISTEN_PORT}")
    print(f"   Sending to UDP {SEND_PORT}")
    print(f"   Backend: {BACKEND_URL}")
    print()
    
    # Start listener
    start_listening_thread()
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n✓ Bridge stopped")
