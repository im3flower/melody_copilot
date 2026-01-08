# Melody Copilot

AI-powered melody continuation with Ableton Live + Max for Live integration. Capture a MIDI clip from Live, relay it through a Python bridge, and get GPT-generated continuations rendered in a React UI.

## What’s inside
- **Backend**: FastAPI service (`bin/main.py`) with `/complete`, `/default`, and Live-capture endpoints.
- **Bridge**: UDP listener/relay (`bin/midi_track_ctrl/bridge.py`) between Max for Live and the backend.
- **Frontend**: React/Vite app (`bin/UI`) for editing, triggering generation, and previewing results.
- **Max for Live**: Helper scripts and device assets (`bin/max_for_live`) including `notesender.js`.

## Requirements
- Python 3.10+
- Node.js 18+ / npm
- Ableton Live + Max for Live
- OpenAI API key (set in `.env` at repo root)

Core env keys (root `.env`):
- `OPENAI_API_KEY`, `OPENAI_MODEL` (e.g., `gpt-4o-mini`)
- `CORS_ALLOW_ORIGINS` (dev: `*` or specific origin)
- `DEFAULT_MIDI_PATH` (defaults to `bin/default.mid`)
- `DEFAULT_CHORDS_PATH` (defaults to `bin/default_chords.mid`)

## Setup
1) Create virtual env & install backend deps
   - `python -m venv .venv`
   - `.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (macOS/Linux)
   - `pip install -r requirements.txt`
2) Install frontend deps
   - `cd bin/UI`
   - `npm install`
   - `cd ../..`

## Run
### One-shot (recommended)
- `python main_control.py`
  - Starts backend (http://localhost:8000), bridge (UDP 7400/7401), and frontend (http://localhost:5173).

### Manual control
- Backend: `python bin/main.py` (or `uvicorn main:app --reload --app-dir bin --port 8000`)
- Bridge: `python bin/midi_track_ctrl/bridge.py`
- Frontend: `cd bin/UI && npm run dev`

## Ableton Live / Max for Live
- Load the device in `bin/max_for_live` (e.g., `max_signal_proc.amxd`) or open `get_midi.maxpat` in a Max MIDI Effect.
- Sending notes: `[live.object] → [js notesender.js] → [udpsend 127.0.0.1 7400]`
- Receiving generated notes: `[udpreceive 7401] → [dict.deserialize] → [dict.unpack added_notes:] → MIDI out`

## API (quick reference)
- `POST /complete` → generate continuation. Payload includes `original_notes`, `mood`, `bpm`, `length_value`, `length_unit` (`bar|step|ms`), `adventureness` (0-100), optional `chords`.
- `POST /bridge/start-capture`, `GET /bridge/latest`, `POST /bridge/result` → Live capture flow.
- `GET /default` → default melody + chords (uses `bin/default.mid`, `bin/default_chords.mid`).

## Project layout
```
melody_copilot/
├── main_control.py         # Launcher
├── requirements.txt        # Backend deps
├── .env                    # Secrets/config (root)
└── bin/
    ├── main.py             # FastAPI backend
    ├── default.mid
    ├── default_chords.mid
    ├── midi_track_ctrl/
    │   ├── bridge.py
    │   ├── midi_make.py
    │   └── midi_read.py
    ├── max_for_live/
    │   ├── notesender.js
    │   ├── get_midi.maxpat
    │   └── INTEGRATION.md
    ├── UI/
    │   ├── App.tsx
    │   ├── services/
    │   └── package.json
    └── docs/               # Full documentation set
```

## Troubleshooting (quick)
- Backend health: `http://localhost:8000/docs`
- Bridge running: should log `📡 Listening on UDP port 7400`
- Frontend: `npm run dev` in `bin/UI`, open `http://localhost:5173`
- See `bin/docs/QUICK_START.md` and `bin/docs/TROUBLESHOOTING_CN.md` for detailed guidance.

## Docs
Full guides live in `bin/docs/`:
- `QUICK_START.md` – 5-minute setup
- `MAX_SETUP.md` – Max for Live walkthrough
- `LIVE_INTEGRATION.md` – endpoints & flow
- `IMPLEMENTATION_COMPLETE.md` – technical deep-dive
- `DOCUMENTATION_INDEX.md` – master index

