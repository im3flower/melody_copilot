# Max for Live Implementation Guide

## Overview
This guide explains how to set up Max for Live to work with the Melody Copilot frontend "Load from Live" button.

## What Max for Live Needs to Do

When the user clicks "📡 从 Live 加载旋律" in the frontend:
1. Frontend sends signal to backend
2. Backend sets "listening" mode
3. **User clicks button in Max patch**
4. Max reads the selected MIDI clip
5. Max sends the note data via UDP to port 7400
6. Bridge captures it and stores in backend
7. Frontend polls and displays the notes

## Max Patch Implementation

### Minimal Setup

Create a simple Max patch with these components:

```
┌─────────────────────────────────────┐
│ [button] "Capture from Live"        │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│ [live.object]                       │
│ (gets selected clip from Live)      │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│ [get notes] (from clip)             │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│ [js notesender.js]                  │
│ (formats as JSON)                   │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│ [prepend send]                      │
└──────────────────┬──────────────────┘
                   │
┌──────────────────▼──────────────────┐
│ [udpsend 127.0.0.1 7400]            │
│ (sends JSON to bridge)              │
└─────────────────────────────────────┘
```

### Step-by-Step Instructions

#### 1. Create Button for Capture
```max
[button] 
  | (labeling)
  (set label to "Capture from Live")
```

#### 2. Get Selected Clip from Ableton Live
```max
[live.object C clip]
  | (this references the current selected MIDI clip)
```

The `C clip` path in Live means "current clip". If you need to get the clip differently:
- Use `C track` for current track
- Use `set_current_track` to change selection
- Use `live.observer` to watch for changes

#### 3. Extract Notes from Clip
```max
[live.object C clip]
  |
[get notes]
  | (returns list of notes with their properties)
```

The `notes` property returns a list of note objects with:
- `pitch`: MIDI note number (0-127)
- `start_time`: start time in quarter notes
- `duration`: length in quarter notes
- `velocity`: MIDI velocity
- `mute`: whether note is muted

#### 4. Format as JSON
```max
[js notesender.js]
  | (takes raw notes, outputs JSON)
```

The JavaScript should format notes like:
```json
{
  "full_track": [
    {"pitch": "C4", "start": 0, "duration": 1, "velocity": 100},
    {"pitch": "D4", "start": 1, "duration": 1, "velocity": 100}
  ],
  "added_notes": [],
  "timestamp": "2024-01-15T10:30:45Z",
  "source": "Max for Live"
}
```

#### 5. Send via UDP
```max
[udpsend 127.0.0.1 7400]
  | (sends JSON to bridge listening on port 7400)
```

Use `[udpsend hostname port]` to specify:
- `127.0.0.1`: localhost (same computer)
- `7400`: port that bridge listens on

## JavaScript Implementation (notesender.js)

Place this in a `[js]` object in your Max patch:

```javascript
/* notesender.js
   Input: [bang] to read current clip
          or raw note list from Live
   Output: JSON string with note data
*/

inlets = 1;
outlets = 1;

var live_api = null;

function bang() {
  try {
    // Method 1: If called with bang from button
    var notes = get_selected_clip_notes();
    send_json(notes);
  } catch (err) {
    post("Error: " + err + "\n");
  }
}

function list(args) {
  // Method 2: If receiving note data as list
  try {
    var notes = parse_note_list(args);
    send_json(notes);
  } catch (err) {
    post("Error: " + err + "\n");
  }
}

function get_selected_clip_notes() {
  // TODO: Implement using Live API
  // Should return list of notes from selected MIDI clip
  post("get_selected_clip_notes() - needs Live API implementation\n");
  return [];
}

function parse_note_list(raw_notes) {
  // Convert from Live note format to our JSON format
  var full_track = [];
  
  for (var i = 0; i < raw_notes.length; i += 4) {
    // Assuming format: [pitch start duration velocity ...]
    var pitch = raw_notes[i];
    var start = raw_notes[i + 1];
    var duration = raw_notes[i + 2];
    var velocity = raw_notes[i + 3] || 100;
    
    full_track.push({
      pitch: midi_to_note_name(pitch),
      start: start,
      duration: duration,
      velocity: velocity
    });
  }
  
  return {
    full_track: full_track,
    added_notes: [],
    timestamp: new Date().toISOString(),
    source: "Max for Live"
  };
}

function send_json(data) {
  var json_str = JSON.stringify(data);
  outlet(0, json_str);
  post("Sent " + data.full_track.length + " notes\n");
}

function midi_to_note_name(pitch) {
  var notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  var octave = Math.floor(pitch / 12) - 1;
  var note = notes[pitch % 12];
  return note + octave;
}
```

## Alternative: Using Live.Observer

If you want real-time updates when the selected clip changes:

```max
[live.observer]
  @root live_set
  @mode selected
  
  | [prepend set_path]
  | [live.object C clip]
  |
  [get notes]
  |
  [js notesender.js]
  |
  [prepend send]
  |
  [udpsend 127.0.0.1 7400]
```

## Testing Your Max Patch

### 1. Start Bridge
```bash
python bin/midi_track_ctrl/bridge.py
```
Should show: `📡 Listening on UDP port 7400`

### 2. Start Backend
```bash
python bin/main.py
# or: uvicorn main:app --reload --app-dir bin
```

### 3. Check Backend State
```bash
curl http://localhost:8000/bridge/latest
```
Should return: `{"has_data": false, "added_notes": [], "full_track": [], "timestamp": null}`

### 4. Run Max Patch
- Click the "Capture from Live" button
- Should see in bridge output: `📨 Received X bytes from 127.0.0.1:XXXXX`
- Should see: `✓ Stored X notes in backend`

### 5. Check Backend Updated
```bash
curl http://localhost:8000/bridge/latest
```
Should now return: `{"has_data": true, "full_track": [...], "added_notes": [...], "timestamp": "..."}`

### 6. Check Frontend
Click "📡 从 Live 加载旋律" in web UI, should show the captured notes

## Troubleshooting

### Issue: "No MIDI clip selected" error
- **Solution**: Make sure you have a MIDI clip in the current track and it's selected

### Issue: No notes captured
- **Solution**: Check that the MIDI clip has notes in it
- Check: `get notes` in your Max patch should output something

### Issue: Bridge doesn't receive UDP packet
- **Solution**: Check firewall isn't blocking port 7400
- Test with: `python -m udp_test` (check bridge.py has test mode)

### Issue: JSON parsing error in bridge
- **Solution**: Check JavaScript output format matches expected:
  ```json
  {
    "full_track": [{"pitch": "C4", "start": 0, "duration": 1}],
    "added_notes": []
  }
  ```

### Issue: Frontend timeout (waiting 15 seconds)
- **Solution**: Make sure you clicked the capture button in Max AFTER clicking the frontend button
- Check: Bridge logs should show "📨 Received" message

## Performance Tips

1. **Keep Max patch simple**: Only send what you need (notes data)
2. **Cache note format**: Don't recompute MIDI→note conversion every time
3. **Use throttling**: If observing changes, add a delay to avoid flooding UDP
4. **Close unused inlets**: Reduces Max CPU usage

## Example Files

See these files for reference:
- `notesender.js` - JavaScript helper for formatting
- `midi_track_ctrl/bridge.py` - Bridge that receives UDP
- `LIVE_INTEGRATION.md` - Complete architecture guide
- `IMPLEMENTATION_COMPLETE.md` - Implementation checklist

## Next Steps

1. Create Max device (`.amxd` file) with the patch above
2. Test with manual UDP sends
3. Integrate with Ableton Live clips
4. Add UI refinements (buttons, displays, etc.)
5. Package as Max for Live device for distribution

## Reference: Live API Paths

Common `live.object` paths:
- `live_set` - Root of Live set
- `live_set clips` - All clips in the set
- `C clip` - Current selected clip
- `C track` - Current selected track
- `live_set master_track` - Master track
- `live_set tracks X` - Specific track by index
- `live_set tracks X devices Y` - Device in track

## Reference: Max/MSP Networking

### UDP Receive
```max
[udpreceive 7401]
  | (receives on port 7401)
```

### Send to Different Port
```max
[udpsend host port]
  | (change 'port' dynamically with [set port_number])
```

### OSC Alternative
```max
[sendosc 127.0.0.1 9000 /melody/capture]
  | (if you prefer OSC protocol instead of raw UDP)
```

Good luck with your Max for Live integration! Let me know if you have questions about any part of this implementation.
