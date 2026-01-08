# Frontend "Load from Live" Button Implementation - Complete ✅

## What Was Done

### 1. Frontend UI Component (UI/App.tsx)
- **Added button** in the actions section (after Complete button):
  ```tsx
  <button
    className="secondary-button"
    onClick={handleLoadFromLive}
    disabled={capturingFromLive || loading}
    type="button"
  >
    {capturingFromLive ? "📡 监听中…" : "📡 从 Live 加载旋律"}
  </button>
  ```

- **Added state variables**:
  - `capturingFromLive`: boolean tracking capture status
  - `captureTimeout`: NodeJS.Timeout for cleanup

- **Implemented handler** `handleLoadFromLive()`:
  - Calls `/bridge/start-capture` to signal readiness
  - Polls `/bridge/latest` up to 15 times (1-second intervals)
  - Updates `notesInput` on success
  - Shows status messages during polling
  - Handles timeout gracefully

- **Added cleanup effect**:
  - Clears polling timeout on component unmount
  - Prevents memory leaks

### 2. API Layer (UI/services/api.ts)
- **Added type**: `BridgeLatestResponse` (full_track, added_notes, timestamp, has_data)
- **Added function**: `fetchBridgeLatest()` (GET /bridge/latest)
- **Added function**: `startLiveCapture()` (POST /bridge/start-capture)

### 3. Backend Endpoints (main.py)
- **GET /bridge/latest**: Returns latest captured notes
- **POST /bridge/start-capture**: Signals readiness to listen
- **POST /bridge/result**: Stores result from bridge

### 4. UDP Bridge (midi_track_ctrl/bridge.py)
- Listens on UDP port 7400 for Max data
- Validates JSON payload
- POSTs to `/bridge/result` to store in backend

## System Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. USER CLICKS BUTTON                                           │
│    "📡 从 Live 加载旋律"                                        │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 2. FRONTEND STATE CHANGE                                        │
│    capturingFromLive = true                                     │
│    Button shows "📡 监听中…"                                    │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 3. FRONTEND CALLS BACKEND                                       │
│    POST /bridge/start-capture                                   │
│    Backend sets listening = true                                │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 4. USER CLICKS CAPTURE IN MAX                                   │
│    Max reads selected MIDI clip                                 │
│    Sends JSON via UDP port 7400                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 5. BRIDGE RECEIVES UDP PACKET                                   │
│    Validates JSON structure                                     │
│    POSTs to /bridge/result                                      │
│    Backend stores latest_result                                 │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 6. FRONTEND POLLS /bridge/latest                                │
│    Polls every 1 second, max 15 attempts                        │
│    Gets has_data = true                                         │
└──────────────────────┬──────────────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│ 7. SUCCESS                                                      │
│    notesInput updated with captured notes                       │
│    Status: "✓ 成功从 Live 加载 X 个音符"                       │
│    capturingFromLive = false                                    │
│    Button returns to normal state                               │
└─────────────────────────────────────────────────────────────────┘
```

## Testing Checklist

### Prerequisites
- [ ] Backend running: `python bin/main.py` or `uvicorn main:app --reload --app-dir bin`
- [ ] Bridge running: `python bin/midi_track_ctrl/bridge.py`
- [ ] Frontend running: `cd bin/UI && npm run dev`
- [ ] Max for Live installed and open
- [ ] MIDI clip selected in Ableton Live

### Test Steps
1. [ ] Open frontend at http://localhost:5173
2. [ ] Click "📡 从 Live 加载旋律" button
3. [ ] Verify button shows "📡 监听中…" and status shows "⏳ 等待中..."
4. [ ] In Max, click capture button (or run notesender.js)
5. [ ] Verify bridge logs show "📨 Received X bytes from 127.0.0.1:XXXXX"
6. [ ] Verify bridge logs show "✓ Stored X notes in backend"
7. [ ] Verify frontend status updates to "✓ 成功从 Live 加载 X 个音符"
8. [ ] Verify notesInput textarea is populated with captured notes
9. [ ] Verify timeout occurs if no Max data received within 15 seconds
10. [ ] Click button again to retry

### Error Cases to Test
- [ ] **No Max data**: Button should timeout after 15s with error message
- [ ] **Max sends invalid JSON**: Bridge should log error, frontend should timeout
- [ ] **Backend not running**: Should see fetch error in console
- [ ] **Bridge not running**: Max sends data but backend /bridge/result fails
- [ ] **Component unmounts during polling**: Timeout should be cleared

## Key Code Sections

### Frontend Handler (UI/App.tsx, ~lines 180-230)
```tsx
const handleLoadFromLive = async () => {
  setCapturingFromLive(true);
  setError(null);
  setStatus("初始化 Max 连接…");
  
  try {
    await startLiveCapture();
    setStatus("⏳ 等待中... (15s)");
  } catch (err) {
    setCapturingFromLive(false);
    setError("Failed to initialize capture");
    setStatus("");
    return;
  }
  
  // Poll for results
  let attempts = 0;
  const maxAttempts = 15;
  
  const pollResult = async () => {
    if (attempts >= maxAttempts) {
      setCapturingFromLive(false);
      setError("超时：未收到 Max for Live 的数据。请确认已在 Max 中点击捕获按钮");
      setStatus("");
      return;
    }
    
    try {
      const result = await fetchBridgeLatest();
      if (result.has_data) {
        setNotesInput(result.full_track.map(n => `${n.pitch} ${n.start} ${n.duration}`).join("\n"));
        setAddedNotes(result.added_notes);
        setStatus(`✓ 成功从 Live 加载 ${result.full_track.length} 个音符`);
        setCapturingFromLive(false);
        return;
      }
    } catch (err) {
      console.error("Poll error", err);
    }
    
    attempts++;
    const remainingTime = maxAttempts - attempts;
    setStatus(`⏳ 等待中... (${remainingTime}s)`);
    
    const timeout = setTimeout(pollResult, 1000);
    setCaptureTimeout(timeout);
  };
  
  pollResult();
};
```

### Cleanup Effect (UI/App.tsx, ~lines 120-126)
```tsx
useEffect(() => {
  return () => {
    if (captureTimeout) {
      clearTimeout(captureTimeout);
    }
  };
}, [captureTimeout]);
```

### Bridge UDP Listener (midi_track_ctrl/bridge.py, ~lines 60-100)
```python
def listen_udp():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(('127.0.0.1', LISTEN_PORT))
    
    while True:
        data, addr = sock.recvfrom(8192)
        try:
            payload = json.loads(data.decode('utf-8'))
            if 'full_track' in payload and 'added_notes' in payload:
                store_result(payload)
            else:
                print("Invalid payload")
        except:
            print("JSON decode error")
```

### Backend State (main.py, ~lines 380-390)
```python
_bridge_state = {
    "latest_result": None,
    "timestamp": None,
    "listening": False,
    "listen_start_time": None
}

@app.get("/bridge/latest", response_model=BridgeLatestResponse)
def bridge_latest() -> BridgeLatestResponse:
    latest = _bridge_state.get("latest_result")
    if not latest:
        return BridgeLatestResponse(added_notes=[], full_track=[], has_data=False)
    return BridgeLatestResponse(
        added_notes=[NotePayload(**n) for n in latest.get("added_notes", [])],
        full_track=[NotePayload(**n) for n in latest.get("full_track", [])],
        timestamp=_bridge_state.get("timestamp"),
        has_data=True
    )
```

## Files Modified
- ✅ `UI/App.tsx`: Added button, handler, state, cleanup
- ✅ `UI/services/api.ts`: Added bridge API functions and types
- ✅ `main.py`: Added bridge endpoints and state management
- ✅ `midi_track_ctrl/bridge.py`: Created UDP listener + relay
- ✅ `notesender.js`: Created Max helper script

## What's Not Included Yet

1. **Max for Live device file (.amxd)**
   - Needs implementation specific to your Ableton Live setup
   - Should use `live.object` to access selected clip
   - Needs js object to format and send JSON via UDP

2. **Chord extraction from piano roll** (marked as "占位符" in code)
   - Can be implemented in future when needed

3. **Advanced UI features** (optional)
   - Visual countdown timer during polling
   - Spinner animation while listening
   - Retry button that appears on timeout

## Debugging Commands

### Check backend state
```bash
curl http://localhost:8000/bridge/latest
```

### Check bridge is listening
```bash
# Should see "📡 Listening on UDP port 7400"
python bin/midi_track_ctrl/bridge.py
```

### Send test UDP packet (for testing without Max)
```bash
# From PowerShell
$socket = [System.Net.Sockets.UdpClient]::new()
$bytes = [System.Text.Encoding]::UTF8.GetBytes('{"full_track":[{"pitch":"C4","start":0,"duration":1}],"added_notes":[]}')
$socket.Send($bytes, $bytes.Length, "127.0.0.1", 7400) | Out-Null
```

## Architecture Advantages

1. **Manual Triggering**: Avoids continuous polling that caused memory leaks
2. **Timeout Protection**: 15-second maximum wait prevents hanging
3. **State Persistence**: Backend maintains latest result for queries
4. **Error Handling**: Clear timeout messages guide users
5. **Memory Safety**: Cleanup effect prevents dangling timers
6. **Separation of Concerns**: Bridge, backend, and frontend are independent

## Next Steps (If Needed)

1. **Create Max for Live device**
   - Implement `get_selected_clip()` using Live API
   - Format notes as JSON
   - Send via UDP

2. **Add visual polish**
   - Spinner during "⏳ 等待中..."
   - Sound/notification on success
   - Toast notification on timeout

3. **Error recovery**
   - Retry button on timeout
   - Manual refresh of latest result

4. **Logging/Debugging**
   - Store capture history
   - Show last X captures in UI
   - Backend request logging

