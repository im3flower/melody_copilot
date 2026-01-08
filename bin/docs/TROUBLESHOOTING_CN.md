# 🔧 故障排查指南：Max for Live 输出但前端收不到数据

## 问题现象
Max for Live 一直在输出数据，但前端收不到。

## 常见原因和解决方案

### 1. 后端或 Bridge 没有运行 ⚠️ **最常见**

**检查方法：**
```powershell
# 运行检查脚本
.\bin\check_services.ps1

# 或手动检查
curl http://localhost:8000/bridge/latest
```

**解决方案：**
需要在 3 个独立的终端中启动服务：

**终端 1 - 后端：**
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot
python bin/main.py
```
应该看到：`INFO:     Uvicorn running on http://127.0.0.1:8000`

**终端 2 - Bridge：**
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot
python bin\midi_track_ctrl\bridge.py
```
应该看到：
```
🎹 MIDI Bridge (Max for Live ↔ FastAPI Backend)
   Listening on UDP 7400
   ...
📡 Listening on UDP port 7400
```

**终端 3 - 前端：**
```bash
cd c:\Users\18200\Desktop\gen_ai\melody_copilot\bin\UI
npm run dev
```

---

### 2. Max 发送的数据格式不正确

**检查方法：**
查看 Bridge 终端的输出，应该看到：
```
📨 ========== NEW UDP PACKET ===========
   Received X bytes from ('127.0.0.1', XXXXX)
   ...
✅ JSON parsed successfully
✅ Payload structure valid
```

如果看到 `❌ Invalid payload structure`，说明数据格式有问题。

**正确的格式：**
```json
{
  "full_track": [
    {"pitch": "C4", "start": 0, "duration": 1, "velocity": 100},
    {"pitch": "D4", "start": 1, "duration": 1, "velocity": 100}
  ],
  "added_notes": [
    {"pitch": "E4", "start": 2, "duration": 1, "velocity": 100}
  ]
}
```

**必需的字段：**
- `full_track` - 数组，包含所有音符
- `added_notes` - 数组，包含新增音符

---

### 3. UDP 端口被占用或防火墙阻止

**检查方法：**
```powershell
# 检查端口 7400 是否被占用
netstat -ano | findstr :7400
```

**解决方案：**
- 如果被占用，杀掉占用进程或修改 bridge.py 中的端口
- 检查防火墙设置，允许本地 UDP 通信

---

### 4. 测试 UDP 连接

使用提供的测试脚本：
```bash
python bin/test_udp_send.py
```

这会发送测试数据到 Bridge，你应该看到：
1. **Bridge 终端：**显示收到数据
2. **Backend 终端：**显示存储数据
3. **测试结果：**显示成功

---

### 5. 前端没有点击 "Load from Live" 按钮

**解决方案：**
1. 打开前端：http://localhost:5173
2. 点击 **"📡 从 Live 加载旋律"** 按钮
3. 按钮会变成 **"📡 监听中…"**
4. 然后在 Max 中发送数据
5. 前端应该在 15 秒内收到数据

---

### 6. 前端轮询超时了

前端会轮询 15 次（每次 1 秒），如果超过 15 秒没收到数据就会超时。

**解决方案：**
1. 确保在点击前端按钮后的 15 秒内发送 Max 数据
2. 如果超时了，再次点击按钮重试

---

## 完整的调试流程

### Step 1: 确保所有服务运行
```powershell
# 运行检查脚本
.\bin\check_services.ps1
```

### Step 2: 测试 UDP 连接
```bash
python bin/test_udp_send.py
```

如果测试成功，应该看到：
- Bridge: `✅ SUCCESS! Stored X notes in backend`
- Backend: `🔵 Backend: Received POST to /bridge/result`

### Step 3: 测试前端查询
```bash
curl http://localhost:8000/bridge/latest
```

应该返回：
```json
{
  "full_track": [...],
  "added_notes": [...],
  "has_data": true,
  "timestamp": "..."
}
```

### Step 4: 测试完整流程
1. 打开前端：http://localhost:5173
2. 点击 **"📡 从 Live 加载旋律"**
3. 在 Max 中发送数据
4. 观察前端是否收到数据

---

## 调试日志解释

### Bridge 日志（正常情况）
```
📨 ========== NEW UDP PACKET ===========
   Received 456 bytes from ('127.0.0.1', 54321)
   Raw data preview: b'{"full_track":[...
✅ JSON parsed successfully
   Keys found: ['full_track', 'added_notes', 'timestamp']
✅ Payload structure valid

🔄 Attempting to store result in backend...
   Payload keys: ['full_track', 'added_notes', 'timestamp']
   Full track notes: 4
   Added notes: 2
   Sending to: http://localhost:8000/bridge/result
✅ SUCCESS! Stored 2 notes in backend
   Backend response: {"status":"ok","message":"Result stored for 2 notes"}
```

### Backend 日志（正常情况）
```
🔵 Backend: Received POST to /bridge/result
   Payload keys: ['full_track', 'added_notes', 'timestamp']
   Full track: 4 notes
   Added notes: 2 notes
✅ Backend: Stored result, timestamp: 2026-01-04T12:00:00.123456
   State has_data: True
```

### 前端轮询日志（正常情况）
在浏览器控制台（F12）应该看到：
```
fetchBridgeLatest() called
{has_data: true, full_track: Array(4), added_notes: Array(2), ...}
```

---

## 常见错误信息

### `❌ Failed to POST to backend: <urlopen error [Errno 111] Connection refused>`
**原因：**后端没有运行  
**解决：**启动 `python bin/main.py`

### `❌ Invalid payload structure`
**原因：**Max 发送的 JSON 缺少 `full_track` 或 `added_notes` 字段  
**解决：**检查 Max patch 的输出格式

### `⏳ 等待中... (0s)` 然后超时
**原因：**15 秒内没收到数据  
**解决：**
1. 检查 Max 是否真的发送了数据
2. 检查 Bridge 是否收到（看 Bridge 终端）
3. 重新点击前端按钮

---

## 快速自检清单

运行每一步，确保都通过：

- [ ] **后端运行中** - `curl http://localhost:8000/bridge/latest` 有响应
- [ ] **Bridge 运行中** - 看到 `📡 Listening on UDP port 7400`
- [ ] **前端运行中** - 打开 http://localhost:5173 能看到界面
- [ ] **测试 UDP** - `python bin/test_udp_send.py` 成功
- [ ] **测试查询** - `curl http://localhost:8000/bridge/latest` 返回 has_data=true
- [ ] **点击按钮** - 前端按钮显示 "📡 监听中…"
- [ ] **Max 发送** - Bridge 终端显示收到数据
- [ ] **前端收到** - 前端显示 "✓ 成功从 Live 加载 X 个音符"

---

## 还是不行？

### 收集更多信息：

1. **Bridge 终端输出**（完整的）
2. **Backend 终端输出**（完整的）
3. **浏览器控制台输出**（F12 → Console）
4. **Max 发送的数据格式**（如果能看到的话）

然后检查：
- Bridge 是否显示收到 UDP 包？
- Backend 是否显示收到 POST 请求？
- 前端是否在轮询？

---

## 联系支持

如果问题仍然存在，提供以下信息：
1. 所有终端的输出（Backend、Bridge、前端）
2. Max for Live 的输出格式
3. 浏览器控制台的错误信息
4. 按照上面的清单标记哪些步骤失败了
