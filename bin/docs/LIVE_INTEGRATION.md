# Melody Copilot: Live MIDI Integration Guide

## System Architecture

```
Ableton Live
    ↓ (MIDI selection)
Max for Live (notesender.js)
    ↓ (UDP port 7400)
Python Bridge (midi_track_ctrl/bridge.py)
    ↓ (HTTP POST)
FastAPI Backend (main.py)
    ↓ (HTTP GET /bridge/latest)
React Frontend (UI/App.tsx)
    ↓ (user interaction)
Display Results
```

## Components

### 1. Frontend UI (UI/App.tsx) ✅
- **"📡 从 Live 加载旋律" Button**
  - Located in the actions section (line ~353)
  - Disabled while `capturingFromLive === true`
  - Shows "📡 监听中…" while listening
  - Calls `handleLoadFromLive()` on click

- **handleLoadFromLive() Handler** ✅
  - Calls `/bridge/start-capture` to signal backend is ready
  - Polls `/bridge/latest` up to 15 times (1-second intervals)
  - Updates `notesInput` when data received
  - Shows status: "⏳ 等待中... (Ns)" during polling
  - Shows "✓ 成功从 Live 加载 X 个音符" on success
  - Shows "超时：未收到 Max for Live 的数据。请确认已在 Max 中点击捕获按钮" on timeout

- **Cleanup on Unmount** ✅
  - useEffect clears any pending capture timeout
  - Resets `capturingFromLive` state

### 2. API Layer (UI/services/api.ts) ✅
- `startLiveCapture()`: POST to `/bridge/start-capture`
  - Response: `{status: "listening", message: "..."}`
- `fetchBridgeLatest()`: GET `/bridge/latest`
  - Response: `BridgeLatestResponse` with `full_track`, `added_notes`, `has_data`

### 3. Backend State Management (main.py) ✅
- `_bridge_state` dict tracks:
  - `listening`: boolean (set to true by start-capture, false by store-result)
  - `listen_start_time`: ISO timestamp
  - `latest_result`: captured note data
  - `timestamp`: when data was stored

- **GET /bridge/latest**
  - Returns latest captured result (BridgeLatestResponse)
  - Frontend polls this during capture

- **POST /bridge/start-capture**
  - Sets `listening = True`
  - Frontend calls this first to signal readiness

- **POST /bridge/result**
  - Bridge calls this to store result from Max
  - Sets `listening = False`

### 4. UDP Bridge (midi_track_ctrl/bridge.py) ✅
- **Listens on UDP port 7400**
  - Max for Live sends captured notes here
  - Expected payload: `{full_track: [...], added_notes: [...]}`

- **Relays to Backend**
  - On receiving valid packet from Max, POSTs to `/bridge/result`
  - Parses JSON from UDP, validates structure, stores in backend

- **Sends to Max on UDP port 7401** (optional, for future)

## Setup Instructions

### 1. Start Backend
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot
python bin/main.py
# or with uvicorn for FastAPI
uvicorn main:app --reload --app-dir bin --port 8000
```

### 2. Start UDP Bridge (in separate terminal)
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot\bin\midi_track_ctrl
python bridge.py
```

### 3. Start Frontend (in separate terminal)
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot\bin\UI
npm install  # if needed
npm run dev
```

### 4. Configure Max for Live
- Create a js object in Max: `[js notesender.js]`
- Wire to capture notes from selected MIDI clip
- Output format: JSON with `full_track` and `added_notes`
- Send via: `[udpsend 127.0.0.1 7400]`

Example Max patch flow:
```
[live.object C clip] 
  → [get notes] 
  → [format as JSON {full_track: [...], added_notes: [...]}]
  → [udpsend 127.0.0.1 7400]
```

## Usage Flow

1. **User clicks "📡 从 Live 加载旋律" button in frontend**
   - Frontend shows "📡 监听中…" + "⏳ 等待中... (15s)"
   - Backend sets `listening = True`

2. **User clicks capture button in Max for Live**
   - Max script reads selected MIDI clip
   - Sends JSON via UDP to port 7400

3. **Bridge receives UDP packet**
   - Validates JSON structure
   - POSTs to backend `/bridge/result`
   - Backend updates `latest_result`, sets `listening = False`

4. **Frontend polls `/bridge/latest`**
   - Receives result with `has_data = True`
   - Updates `notesInput` textarea
   - Shows "✓ 成功从 Live 加载 X 个音符"

## Expected Responses

### POST /bridge/start-capture (Frontend → Backend)
```json
{
  "status": "listening",
  "message": "Now listening for Max capture. Click the capture button in Max for Live."
}
```

### GET /bridge/latest (Frontend ← Backend)
```json
{
  "added_notes": [
    {"pitch": "C4", "start": 0, "duration": 1},
    {"pitch": "D4", "start": 1, "duration": 1}
  ],
  "full_track": [...],
  "timestamp": "2024-01-15T10:30:45.123456",
  "has_data": true
}
```

### UDP Packet (Max → Bridge, port 7400)
```json
{
  "full_track": [
    {"pitch": "C4", "start": 0, "duration": 1},
    {"pitch": "D4", "start": 1, "duration": 1}
  ],
  "added_notes": [
    {"pitch": "E4", "start": 2, "duration": 1}
  ]
}
```

### POST /bridge/result (Bridge → Backend)
- Same payload as UDP packet
- Backend response: `{"status": "ok", "message": "Result stored for N notes"}`

## Timeout Behavior

- **Frontend polling**: 15 attempts × 1 second = 15-second maximum wait
- If no data received: Shows error "超时：未收到 Max for Live 的数据。请确认已在 Max 中点击捕获按钮"
- User can click button again to retry

## Debugging

### Check Backend State
```bash
curl http://localhost:8000/bridge/latest
```

### Check Bridge Status
- Look for "📡 Listening on UDP port 7400"
- Look for "📨 Received X bytes" when Max sends data
- Look for "✓ Stored X notes in backend" after POST

### Check Frontend
- Open browser console (F12)
- Look for `startLiveCapture()` and `fetchBridgeLatest()` calls
- Check Network tab for HTTP requests

## Files Modified/Created

- ✅ `main.py`: Added bridge endpoints + state management
- ✅ `midi_track_ctrl/bridge.py`: Created UDP listener + HTTP relay
- ✅ `UI/App.tsx`: Added capture button + polling handler + cleanup
- ✅ `UI/services/api.ts`: Added bridge API functions

## Notes

- Uses **manual triggering** (not continuous polling) to avoid memory leaks
- Backend tracks listening state; frontend respects 15-second timeout
- Bridge validates JSON payload before storing
- Cleanup on unmount prevents memory leaks from dangling timers
