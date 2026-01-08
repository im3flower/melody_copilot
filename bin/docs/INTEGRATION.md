# Max for Live 集成指南

## 架构概览
```
Ableton Live → Max for Live (notesender.js) 
    ↓ UDP
Python Bridge (bridge.py, port 7400)
    ↓ HTTP POST
FastAPI Backend (/complete)
    ↓ HTTP Response
Python Bridge
    ↓ UDP
Max for Live → Ableton Live (MIDI)
```

## 1. 启动桥接脚本

在项目根目录运行：
```bash
python max_for_live/bridge.py
```

应该看到：
```
Bridge listening on UDP port 7400
Will send responses to Max on port 7401
Backend: http://127.0.0.1:8000/complete
Waiting for data from Max...
```

## 2. Max 补丁配置

在 Max for Live 装置里需要的对象：

### 发送端（音符 → 后端）
```
[js notesender.js]
    ↓
[prepend send]
    ↓
[udpsend 127.0.0.1 7400]
```

连线说明：
- `js notesender.js` 的 outlet 连到 `[prepend send]`
- `[prepend send]` 输出连到 `[udpsend 127.0.0.1 7400]` 的第一个 inlet

### 接收端（后端 → MIDI）
```
[udpreceive 7401]
    ↓
[dict.deserialize]
    ↓
[dict.unpack added_notes:]
    ↓
(解析并转换为 MIDI)
```

详细流程：
1. `[udpreceive 7401]` 接收 JSON 字符串
2. `[dict.deserialize]` 将 JSON 转为 Max dictionary
3. `[dict.unpack added_notes:]` 提取新增音符列表
4. 遍历音符，用 `[makenote]` 转换为 MIDI，发送到 Live

## 3. 完整补丁示例

### 发送音符到后端
```maxpat
[live.object] (获取 clip 音符)
    ↓
[js notesender.js] (收集并打包)
    ↓
[prepend send]
    ↓
[udpsend 127.0.0.1 7400]
```

### 接收并播放结果
```maxpat
[udpreceive 7401]
    ↓
[print backend_response]
    ↓
[dict.deserialize @embed 1]
    ↓
[dict.unpack added_notes:]
    ↓
[iter]
    ↓
[dict.unpack pitch: start: duration:]
    ↓
[js convert_to_midi.js]
    ↓
[makenote 100 500]
    ↓
[noteout]
```

## 4. 测试流程

### 4.1 启动后端
```bash
python bin/main.py
# 或
uvicorn main:app --reload --app-dir bin
```

### 4.2 启动桥接
```bash
python bin/midi_track_ctrl/bridge.py
```

### 4.3 在 Ableton Live 里
1. 打开 MIDI clip
2. 录入一些音符
3. 加载 Max for Live 装置
4. 点击触发按钮（连到 `[live.object]` 的 bang）

### 4.4 观察日志
- **Max Console**：应该看到 `dbg recv ...`, `dbg sending payload ...`
- **Bridge 终端**：应该看到 `← Received ...`, `→ Posting ...`, `✓ Backend responded ...`
- **Backend 终端**：应该看到 POST 请求日志

## 5. 自定义参数

编辑 `notesender.js` 里的 `sendPayload()` 函数，修改默认值：
```javascript
var payload = {
  original_notes: acc,
  mood: "happy",        // 改成你想要的 mood
  bpm: 120,             // 改成当前 Live 工程的 BPM
  length_value: 4,      // 生成长度
  length_unit: "bar",   // "bar" / "step" / "ms"
  adventureness: 35     // 0-100，控制创意度
};
```

或在 Max 补丁里用消息框动态设置：
```
[message set_mood $1]
    ↓
[js notesender.js]
```

然后在 notesender.js 里添加：
```javascript
var current_mood = "happy";
function set_mood(m) {
  current_mood = String(m);
  log("mood set to " + current_mood);
}
```

## 6. 和弦支持

在 `sendPayload()` 里添加 chords 字段：
```javascript
var payload = {
  original_notes: acc,
  mood: "happy",
  bpm: 120,
  length_value: 4,
  length_unit: "bar",
  adventureness: 35,
  chords: [
    {symbol: "Am", start: 0.0, duration: 4.0},
    {symbol: "F", start: 4.0, duration: 4.0},
    {symbol: "C", start: 8.0, duration: 4.0},
    {symbol: "G", start: 12.0, duration: 4.0}
  ]
};
```

## 7. 前端集成（可选）

如果想通过前端界面触发：

### 方案 A：前端直接调用后端
- 前端发送 POST `/complete` 到后端
- 显示结果或下载 MIDI
- 不需要 Max for Live 参与

### 方案 B：前端触发 Max
- 前端通过 WebSocket 或文件通知 Max
- Max 读取 Live 音符，通过 bridge 发送
- 结果返回给前端或直接播放

## 8. 故障排查

### Bridge 收不到数据
- 确认 Max 里 `[udpsend 127.0.0.1 7400]` 已创建并连接
- 在 Max 里用 `[print]` 查看 js 对象的输出格式
- 确认防火墙没有阻止 UDP 7400/7401

### Backend 报错
- 检查 bridge.py 终端的详细错误
- 确认后端在运行且可访问 `http://127.0.0.1:8000/complete`
- 用 Postman 或 curl 直接测试后端端点

### Max 收不到结果
- 确认 `[udpreceive 7401]` 已创建
- 在 bridge.py 看到 "✓ Sent response to Max" 但 Max 没反应时，检查端口是否被占用
- 用 `netstat -an | findstr 7401` (Windows) 确认端口监听

### JSON 解析失败
- 在 Max Console 查看 js 对象输出的原始 JSON
- 确认格式正确（用在线 JSON validator）
- 检查是否有特殊字符或编码问题

## 9. 下一步

- 添加 UI 控件到 Max 装置（mood/BPM/adventureness 滑块）
- 实现和弦轨道读取（用另一个 live.object 读取和弦 clip）
- 将返回的音符自动写入新的 MIDI clip
- 集成前端界面，提供可视化控制面板
