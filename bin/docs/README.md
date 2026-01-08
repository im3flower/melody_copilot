# Melody Copilot

AI-powered melody continuation tool with Ableton Live integration. Capture MIDI from Live, send to GPT-4, and get musically coherent continuations.

## Features

- **Backend API**: FastAPI server with `/complete` endpoint for melody generation
- **React Frontend**: Visual interface for melody input, mood/BPM/adventureness controls, and audio playback
- **Ableton Live Integration**: Max for Live device to capture clip notes and send to backend
- **Chord Support**: Provide harmonic context for better melody generation
- **Real-time Bridge**: UDP bridge connects Max for Live to backend seamlessly

---

## Quick Start

### 1. Environment Setup

Copy `.env.example` to `.env` and configure:

```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o-mini
OPENAI_API_BASE=
CORS_ALLOW_ORIGINS=*
DEFAULT_MIDI_PATH=default.mid
```

### 2. Install Dependencies

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Mac/Linux
pip install -r requirements.txt

cd UI
npm install
cd ..
```

### 3. Start All Services

```bash
python main_control.py
```

This launches:
- **Backend** (FastAPI) on `http://localhost:8000`
- **Bridge** (Max for Live UDP bridge) on ports 7400/7401
- **Frontend** (React/Vite) on `http://localhost:5173`

Press `Ctrl+C` to stop all services.

#### Start Options

```bash
# Backend + Bridge only (no frontend)
python main_control.py --skip-frontend

# Backend only (no bridge or frontend)
python main_control.py --skip-frontend --skip-bridge

# Backend with hot reload
python main_control.py --reload

# Custom ports
python main_control.py --backend-port 8080 --frontend-port 3000

# See all options
python main_control.py --help
```

---

## Architecture

```
┌─────────────────┐
│  Ableton Live   │
│   (MIDI Clip)   │
└────────┬────────┘
         │
    ┌────▼─────────────────┐
    │  Max for Live Device │
    │   (notesender.js)    │
    └────────┬─────────────┘
             │ UDP 7400
    ┌────────▼─────────┐
    │  Python Bridge   │
    │   (bridge.py)    │
    └────────┬─────────┘
             │ HTTP POST
    ┌────────▼─────────┐
    │  FastAPI Backend │
    │    (main.py)     │
    └────────┬─────────┘
             │ LLM Call
    ┌────────▼─────────┐
    │   OpenAI GPT-4   │
    └────────┬─────────┘
             │ Response
    ┌────────▼─────────┐
    │  Python Bridge   │
    └────────┬─────────┘
             │ UDP 7401
    ┌────────▼─────────────┐
    │  Max for Live Device │
    │  (play/write MIDI)   │
    └──────────────────────┘
```

---

## Max for Live Integration

### Setup

1. **Start Services**
   ```bash
   python main_control.py
   ```

2. **Open Max for Live Device**
   - In Ableton Live, load `max_for_live/未命名装置.amxd` onto a MIDI track
   - Or create a new Max MIDI Effect and open `max_for_live/get_midi.maxpat`

3. **Patch Configuration**

   **Send notes to backend:**
   ```
   [live.object] → [js notesender.js] → [prepend send] → [udpsend 127.0.0.1 7400]
   ```

   **Receive generated notes:**
   ```
   [udpreceive 7401] → [dict.deserialize] → [dict.unpack added_notes:] → (MIDI out)
   ```

4. **Usage**
   - Select a MIDI clip in Live
   - Click the trigger button in the Max device
   - Wait for generated notes (appears in Max Console and can be routed to MIDI out)

### Detailed Integration Guide

See [max_for_live/INTEGRATION.md](max_for_live/INTEGRATION.md) for:
- Complete patch examples
- Chord support setup
- Custom parameter configuration
- Troubleshooting tips

---

## API Reference

### POST `/complete`

Generate melody continuation.

**Request:**
```json
{
  "original_notes": [
    { "pitch": "C4", "start": 0.0, "duration": 1.0 },
    { "pitch": "E4", "start": 1.0, "duration": 1.0 }
  ],
  "mood": "happy",
  "bpm": 120,
  "length_value": 4,
  "length_unit": "bar",
  "adventureness": 35,
  "chords": [
    { "symbol": "Am", "start": 0.0, "duration": 4.0 },
    { "symbol": "F", "start": 4.0, "duration": 4.0 }
  ]
}
```

**Parameters:**
- `original_notes`: Array of existing melody notes
- `mood`: Single word describing desired mood (e.g., "happy", "melancholic", "energetic")
- `bpm`: Tempo in beats per minute
- `length_value`: How much to generate
- `length_unit`: `"bar"`, `"step"` (quarter notes), or `"ms"` (milliseconds)
- `adventureness`: 0-100, controls melodic creativity (0=safe/diatonic, 100=chromatic/varied)
- `chords` (optional): Harmonic context

**Response:**
```json
{
  "full_track": [ /* original + generated */ ],
  "added_notes": [ /* only generated notes */ ],
  "midi_file": null
}
```

### GET `/default`

Get default seed melody and chords.

**Response:**
```json
{
  "notes": [ /* notes from default.mid */ ],
  "bpm": 96,
  "notes_text": "C4 0.0 1.0\nD4 1.0 1.0\n...",
  "midi_file": "C:/path/to/default.mid",
  "chords": [
    { "symbol": "Am", "start": 0.0, "duration": 4.0 },
    { "symbol": "F", "start": 4.0, "duration": 4.0 },
    { "symbol": "C", "start": 8.0, "duration": 4.0 },
    { "symbol": "G", "start": 12.0, "duration": 4.0 }
  ],
  "chords_text": "Am 0.0 4.0\nF 4.0 4.0\n..."
}
```

---

## CLI Usage

Generate melody completions from the command line:

```bash
python bin/main.py
```

Follow prompts:
1. Input MIDI file path
2. Mood (single word)
3. BPM
4. Length value and unit
5. Adventureness (0-100)

Output: `original_completed.mid` written to same directory.

---

## Frontend Usage

After starting services with `python main_control.py`, open `http://localhost:5173`:

1. **Load Default** - Loads `default.mid` with default chord progression
2. **Edit Notes** - Manually add/edit melody notes
3. **Set Parameters** - Adjust mood, BPM, length, adventureness
4. **Generate** - Send to backend and receive continuation
5. **Play/Download** - Listen to result or download as MIDI

---

## Project Structure

```
melody_copilot/
├── main_control.py         # All-in-one launcher (root)
├── requirements.txt        # Python dependencies
├── .env                    # Configuration (create from .env.example)
└── bin/
  ├── main.py             # FastAPI backend + CLI
  ├── default.mid         # Default seed melody
  ├── default_chords.mid  # Default chord progression
  ├── midi_track_ctrl/    # MIDI read/write utilities + bridge
  │   ├── bridge.py
  │   ├── midi_make.py
  │   └── midi_read.py
  ├── max_for_live/       # Ableton Live integration assets
  │   ├── notesender.js   # Max JS object for note collection
  │   ├── bridge.py       # UDP bridge (Max ↔ Backend)
  │   ├── get_midi.maxpat # Max patch
  │   ├── 未命名装置.amxd  # Max for Live device
  │   └── INTEGRATION.md  # Detailed setup guide
  └── UI/                 # React frontend
    ├── App.tsx
    ├── services/
    │   ├── api.ts
    │   └── audioService.ts
    └── package.json
```

---

## Troubleshooting

### Backend Issues

**"OPENAI_API_KEY is not configured"**
- Copy `.env.example` to `.env` and add your API key

**CORS errors from frontend**
- Set `CORS_ALLOW_ORIGINS=*` in `.env` for development
- Or specify exact origin: `CORS_ALLOW_ORIGINS=http://localhost:5173`

**"default.mid not found"**
- Ensure `bin/default.mid` exists (or update path)
- Or set custom path: `DEFAULT_MIDI_PATH=path/to/your.mid` in `.env`

### Bridge Issues

**"Bridge listening on UDP port 7400" but Max can't connect**
- Check firewall settings (allow UDP 7400/7401)
- Verify Max patch uses correct IP: `127.0.0.1`
- Use `netstat -an | findstr 7400` (Windows) to confirm port is listening

**Bridge receives data but backend returns errors**
- Check backend logs for detailed error messages
- Test backend directly: `curl -X POST http://localhost:8000/complete -H "Content-Type: application/json" -d '{"original_notes":[{"pitch":"C4","start":0,"duration":1}],"mood":"happy","bpm":120,"length_value":4,"length_unit":"bar","adventureness":35}'`

### Max for Live Issues

**"js: no function get_selected_notes"**
- Use `[js notesender.js]` instead of `[node.script]`
- Ensure `notesender.js` is in same directory as Max device

**No output from Max device**
- Check Max Console (Window → Max Console)
- Look for `dbg init notesender.js loaded` on startup
- Add `[print]` objects to debug data flow

**"Node script not ready"**
- `node.script` is unreliable in Max for Live; use `[js]` instead
- See INTEGRATION.md for corrected patch configuration

### Frontend Issues

**"npm not found"**
- Install Node.js from https://nodejs.org
- Restart terminal after installation

**Frontend won't connect to backend**
- Check backend is running: `http://localhost:8000/docs`
- Verify frontend API_BASE_URL in `UI/services/api.ts`

---

## Development

### Run services individually

**Backend only:**
```bash
uvicorn main:app --reload --app-dir bin --host 0.0.0.0 --port 8000
```

**Bridge only:**
```bash
python bin/midi_track_ctrl/bridge.py
```

**Frontend only:**
```bash
cd bin/UI
npm run dev
```

### Hot reload

Backend with `--reload`:
```bash
python main_control.py --reload
```

Frontend automatically hot-reloads via Vite.

---

## License

MIT

---

## Credits

Built with:
- FastAPI
- React + Vite
- LangChain + OpenAI
- music21
- Max/MSP for Live
