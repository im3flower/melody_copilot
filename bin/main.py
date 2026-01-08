import sys
from pathlib import Path as PathlibPath

# Add parent directory to path to find midi_track_ctrl module
sys.path.insert(0, str(PathlibPath(__file__).resolve().parent.parent))

import os
import json
import socket
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, TypedDict
from datetime import datetime

from dotenv import load_dotenv #type: ignore
from fastapi import FastAPI, HTTPException #type: ignore
from fastapi.middleware.cors import CORSMiddleware #type: ignore
from langchain_core.messages import HumanMessage, SystemMessage #type: ignore
from langchain_openai import ChatOpenAI #type: ignore
from pydantic import BaseModel, Field #type: ignore

from midi_track_ctrl.midi_make import write_melody #type: ignore
from midi_track_ctrl.midi_read import read_melody # type: ignore
from music21 import chord as m21chord, stream as m21stream, tempo as m21tempo, note as m21note #type: ignore


PROJECT_ROOT = Path(__file__).resolve().parent
ROOT_DIR = PROJECT_ROOT.parent
load_dotenv(ROOT_DIR / ".env", override=True)

MAX_UDP_HOST = os.getenv("MAX_UDP_HOST", "127.0.0.1")
MAX_UDP_PORT = int(os.getenv("MAX_UDP_PORT", "7401"))

_default_midi_env = os.getenv("DEFAULT_MIDI_PATH", PROJECT_ROOT / "default.mid")
DEFAULT_MIDI_PATH = Path(_default_midi_env)
if not DEFAULT_MIDI_PATH.is_absolute():
    DEFAULT_MIDI_PATH = PROJECT_ROOT / DEFAULT_MIDI_PATH

DEFAULT_CHORDS_PATH = PROJECT_ROOT / "default_chords.mid"


SYSTEM_PROMPT = """
You are a music composition assistant.

Continue the given melody with strong stylistic continuity.

Rules:
1) Output ONLY new notes (do NOT repeat or duplicate any existing note).
2) Match the requested length: extend the melody by exactly the target duration (length_value + length_unit converted to quarterLength). Do not shorten or overshoot.
3) Keep the rhythmic feel of the provided melody; avoid defaulting to straight 4/4 on-beat patterns if the seed has syncopation or varied values.
4) Preserve the melodic contour and tone of the seed: similar step/leap balance, register, and motif development.
5) Format exactly: PITCH START DURATION (START and DURATION are quarterLength numbers).
6) Respect the requested mood.
7) Adventureness controls risk:
    - 0 percent: stepwise, diatonic, safe
    - 100 percent: wider leaps, more chromaticism, varied rhythms
8) End with a musically resolved phrase.
 9) Infer the implied meter/groove from the seed (accent placements, syncopation, subdivisions) and continue with the same rhythmic cells and bar feel; do not straighten or regularize the rhythm.
10) Reuse and develop rhythmic motifs from the seed (exact or slightly varied), keeping the same note density and subdivision palette.
"""


class NoteDict(TypedDict):
    pitch: str
    start: float
    duration: float


class ChordDict(TypedDict):
    symbol: str
    start: float
    duration: float


class NotePayload(BaseModel):
    pitch: str = Field(..., min_length=1)
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)


class ChordPayload(BaseModel):
    symbol: str = Field(..., min_length=1)
    start: float = Field(..., ge=0)
    duration: float = Field(..., gt=0)


class CompleteRequest(BaseModel):
    original_notes: List[NotePayload]
    mood: str = Field(..., min_length=1)
    bpm: float = Field(..., gt=0)
    length_value: float = Field(..., gt=0)
    length_unit: Literal["bar", "step", "ms"]
    adventureness: float = Field(..., ge=0, le=100)
    chords: Optional[List["ChordPayload"]] = None


class CompleteResponse(BaseModel):
    full_track: List[NotePayload]
    added_notes: List[NotePayload]
    midi_file: Optional[str] = None


class DefaultSeedResponse(BaseModel):
    notes: List[NotePayload]
    bpm: float
    notes_text: str
    midi_file: Optional[str] = None
    chords: List["ChordPayload"]
    chords_text: str


class ExportMidiRequest(BaseModel):
    notes: List[NotePayload]
    bpm: float = Field(..., gt=0)
    filename: Optional[str] = None  # optional custom name


class BridgeLatestResponse(BaseModel):
    added_notes: List[NotePayload]
    full_track: List[NotePayload]
    timestamp: Optional[str] = None
    has_data: bool = False


class MaxNotifyRequest(BaseModel):
    event: str = Field(..., min_length=1)
    data: Optional[Dict[str, Any]] = None


def _sorted_notes(notes: List[NoteDict]) -> List[NoteDict]:
    return sorted(notes, key=lambda n: (n["start"], n["pitch"]))


def send_udp_to_max(message: Dict[str, Any]) -> None:
    """Send a UDP packet to Max for Live (default: 127.0.0.1:7401)."""
    data = json.dumps(message).encode("utf-8")
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(data, (MAX_UDP_HOST, MAX_UDP_PORT))
    except Exception as exc:  # pragma: no cover - networking
        raise RuntimeError(f"Failed to send UDP to Max at {MAX_UDP_HOST}:{MAX_UDP_PORT}: {exc}") from exc


def _pad4(data: bytes) -> bytes:
    pad = (4 - (len(data) % 4)) % 4
    return data + (b"\0" * pad)


def build_osc_message(address: str, string_arg: str) -> bytes:
    """Build a minimal OSC packet: address + ",s" type tag + one string argument."""
    if not address.startswith("/"):
        address = "/" + address
    addr = _pad4(address.encode("utf-8") + b"\0")
    tags = _pad4(b",s\0")
    arg = _pad4(string_arg.encode("utf-8") + b"\0")
    return addr + tags + arg


def send_osc_json_to_max(message: Dict[str, Any]) -> None:
    """Send JSON to Max as OSC (/json, <string>) to satisfy udpreceive expectations."""
    payload = json.dumps(message)
    packet = build_osc_message("/json", payload)
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.sendto(packet, (MAX_UDP_HOST, MAX_UDP_PORT))
    except Exception as exc:  # pragma: no cover - networking
        raise RuntimeError(f"Failed to send OSC to Max at {MAX_UDP_HOST}:{MAX_UDP_PORT}: {exc}") from exc


def notes_to_text(notes: List[NoteDict]) -> str:
    ordered = _sorted_notes(notes)
    return "\n".join(
        f"{n['pitch']} {n['start']} {n['duration']}" for n in ordered
    )


def text_to_notes(text: str) -> List[NoteDict]:
    notes: List[NoteDict] = []
    lines = [line.strip() for line in text.strip().splitlines() if line.strip()]
    if not lines:
        raise ValueError("Model response did not contain any notes.")

    for line in lines:
        parts = line.split()
        if len(parts) != 3:
            raise ValueError(f"Invalid note format: '{line}'")
        pitch, start, duration = parts
        try:
            note_dict: NoteDict = {
                "pitch": pitch,
                "start": float(start),
                "duration": float(duration),
            }
        except ValueError as exc:  # pragma: no cover - defensive parsing
            raise ValueError(f"Invalid numeric value in '{line}'") from exc
        notes.append(note_dict)
    return notes


def setup_llm() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    return ChatOpenAI(
        model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        temperature=0.3,  # tighter adherence to constraints
        api_key=api_key, #type: ignore
        base_url=os.getenv("OPENAI_API_BASE"),
    )


def export_notes_to_midi(notes: List[NoteDict], bpm: float, path: Path) -> str:
    """Write notes to a MIDI file at the given path."""
    s = m21stream.Stream()
    s.append(m21tempo.MetronomeMark(number=bpm))

    for n in notes:
        m = m21note.Note(n["pitch"])
        m.duration.quarterLength = float(n["duration"])
        s.insert(float(n["start"]), m)

    path.parent.mkdir(parents=True, exist_ok=True)
    s.write("midi", fp=str(path))
    return str(path)


def convert_length_to_quarters(
    length_value: float,
    unit: str,
    bpm: float,
) -> float:
    if unit == "bar":
        return length_value * 4.0
    if unit == "step":
        return length_value
    if unit == "ms":
        seconds = length_value / 1000.0
        return seconds * (bpm / 60.0)
    raise ValueError("Unsupported length unit")


def _calculate_end_time(notes: List[NoteDict]) -> float:
    if not notes:
        return 0.0
    return max(n["start"] + n["duration"] for n in notes)


def complete_melody(
    original_notes: List[NoteDict],
    mood: str,
    bpm: float,
    length_value: float,
    length_unit: str,
    adventureness: float,
    chords: Optional[List[ChordDict]] = None,
    output_path: Optional[str] = None,
) -> Dict[str, Optional[str] | List[NoteDict]]:
    if not original_notes:
        raise ValueError("original_notes must contain at least one note.")

    end_time = _calculate_end_time(original_notes)

    target_end = convert_length_to_quarters(
        length_value,
        length_unit,
        bpm,
    )

    if target_end <= end_time:
        raise ValueError(
            f"Target total length ({target_end} ql) must exceed existing melody end ({end_time} ql)."
        )

    # basic rhythmic profile of the seed for guidance
    durations = [n["duration"] for n in original_notes]
    unique_durs = sorted(set(durations))
    avg_dur = sum(durations) / len(durations)
    last_note = original_notes[-1]

    llm = setup_llm()

    chord_text = ""
    if chords:
        ordered_chords = sorted(chords, key=lambda c: (c["start"], c["symbol"]))
        chord_lines = [
            f"{c['symbol']} {c['start']} {c['duration']}" for c in ordered_chords
        ]
        chord_text = "\nChords (symbol start duration):\n" + "\n".join(chord_lines)

    user_prompt = f"""
Mood: {mood}
Adventureness: {adventureness} percent
BPM: {bpm}

Existing melody:
{notes_to_text(original_notes)}

Use these chords as harmonic context (if provided):
{chord_text or 'No chords provided; assume default vi-IV-I-V repeating.'}

Seed rhythm profile:
- Unique durations: {unique_durs}
- Average duration: {avg_dur:.3f}

The current melody ends at {end_time} quarterLength.
TOTAL target length (including seed) = {target_end} quarterLength.
You MUST continue until the final note end equals {target_end}; do not stop early or go beyond.
Start times of new notes must be >= {end_time}.
Maintain the same rhythmic character (accents, subdivisions, syncopation) as the seed; reuse its rhythmic cells and density.
Keep rhythmic feel similar to the seed (avoid default straight 4/4 on-beat patterns if the seed is varied).
Last seed note: {last_note['pitch']} at {last_note['start']} len {last_note['duration']}.
"""

    messages = [
        SystemMessage(content=SYSTEM_PROMPT.strip()),
        HumanMessage(content=user_prompt.strip()),
    ]

    response = llm.invoke(messages)
    content = getattr(response, "content", None)
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Language model returned empty content.")

    new_notes = text_to_notes(content)
    full_track = original_notes + new_notes

    result: Dict[str, Optional[str] | List[NoteDict]] = {
        "full_track": full_track,
        "added_notes": new_notes,
        "midi_file": None,
    }

    if output_path:
        write_melody(original_notes, new_notes, output_path)
        result["midi_file"] = output_path

    return result


def ensure_chord_midi(chords: List[ChordDict], path: Path, bpm: float = 96.0) -> str:
    if path.exists():
        return str(path)

    s = m21stream.Stream()
    s.append(m21tempo.MetronomeMark(number=bpm))

    for chord_dict in chords:
        pitches = []
        # Basic voicing: duplicate symbol root as triad if not a known chord name
        symbol = chord_dict["symbol"]
        if symbol.lower() in {"am", "a-"}:
            pitches = ["A3", "C4", "E4"]
        elif symbol.lower() == "f":
            pitches = ["F3", "A3", "C4"]
        elif symbol.lower() == "c":
            pitches = ["C3", "E3", "G3"]
        elif symbol.lower() == "g":
            pitches = ["G3", "B3", "D4"]
        else:
            # fallback single-note root
            pitches = [symbol]

        c = m21chord.Chord(pitches)
        c.duration.quarterLength = float(chord_dict["duration"])
        s.insert(float(chord_dict["start"]), c)

    s.write("midi", fp=str(path))
    return str(path)


def complete_melody_from_midi(
    midi_path: str,
    mood: str,
    bpm: float,
    length_value: float,
    length_unit: str,
    adventureness: float,
) -> Dict[str, Optional[str] | List[NoteDict]]:
    original_notes, _, _ = read_melody(midi_path)
    output_path = str(
        Path(midi_path).with_name(
            f"{Path(midi_path).stem}_completed{Path(midi_path).suffix or '.mid'}"
        )
    )
    return complete_melody(
        original_notes,
        mood,
        bpm,
        length_value,
        length_unit,
        adventureness,
        output_path=output_path,
    )


app = FastAPI(title="Melody Copilot API", version="1.0.0")

cors_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allowed_origins = [origin.strip() for origin in cors_origins.split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = ["*"]
if "*" in allowed_origins:
    allowed_origins = ["*"]
    allow_credentials = False  # allow "*" only when not sending cookies/credentials
else:
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/complete", response_model=CompleteResponse)
def complete_endpoint(payload: CompleteRequest) -> CompleteResponse:
    notes = [note.model_dump() for note in payload.original_notes]
    chords = [c.model_dump() for c in payload.chords] if payload.chords else None
    try:
        result = complete_melody(
            notes, #type: ignore
            payload.mood,
            payload.bpm,
            payload.length_value,
            payload.length_unit,
            payload.adventureness,
            chords=chords, #type: ignore
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return CompleteResponse(**result)  # type: ignore[arg-type]


@app.get("/default", response_model=DefaultSeedResponse)
def default_seed() -> DefaultSeedResponse:
    midi_path = DEFAULT_MIDI_PATH
    if not midi_path.exists():
        raise HTTPException(status_code=404, detail="Default MIDI not found.")

    notes, _, tempo = read_melody(str(midi_path))
    if not notes:
        raise HTTPException(status_code=500, detail="Default MIDI contains no notes.")

    # Default chord progression: vi-IV-I-V in C major (Am, F, C, G), 1 bar each
    default_chords: List[ChordDict] = [
        {"symbol": "Am", "start": 0.0, "duration": 4.0},
        {"symbol": "F", "start": 4.0, "duration": 4.0},
        {"symbol": "C", "start": 8.0, "duration": 4.0},
        {"symbol": "G", "start": 12.0, "duration": 4.0},
    ]

    payload_notes = [NotePayload(**n) for n in notes]
    notes_text = notes_to_text(notes)
    chords_midi_path = ensure_chord_midi(default_chords, DEFAULT_CHORDS_PATH, bpm=float(tempo))

    return DefaultSeedResponse(
        notes=payload_notes,
        bpm=float(tempo),
        notes_text=notes_text,
        midi_file=str(midi_path),
        chords=[ChordPayload(**c) for c in default_chords],
        chords_text="\n".join(f"{c['symbol']} {c['start']} {c['duration']}" for c in default_chords),
        # expose chords MIDI path primarily for debugging/reference
        # clients can ignore if not needed
        
    )


# Bridge 状态存储（用于 Max → Frontend 通信）
_bridge_state: Dict[str, Optional[Any]] = {
    "latest_result": None,
    "timestamp": None,
    "listening": False,
    "listen_start_time": None
}


@app.get("/bridge/latest", response_model=BridgeLatestResponse)
def bridge_latest() -> BridgeLatestResponse:
    """获取最新的生成结果（从 Max for Live 发来）"""
    latest = _bridge_state.get("latest_result")
    timestamp = _bridge_state.get("timestamp")
    
    print(f"\n🔍 Backend: GET /bridge/latest called")
    print(f"   Has latest_result: {latest is not None}")
    print(f"   Timestamp: {timestamp}")
    
    if not latest:
        print(f"   ❌ No data available, returning has_data=False")
        return BridgeLatestResponse(
            added_notes=[],
            full_track=[],
            timestamp=None,
            has_data=False
        )
    
    added_notes = [NotePayload(**n) for n in latest.get("added_notes", [])]
    full_track = [NotePayload(**n) for n in latest.get("full_track", [])]
    
    print(f"   ✅ Returning data: {len(full_track)} notes, has_data=True")
    
    return BridgeLatestResponse(
        added_notes=added_notes,
        full_track=full_track,
        timestamp=timestamp,
        has_data=True
    )


@app.post("/bridge/start-capture", response_model=None)
def bridge_start_capture() -> Dict[str, str]:
    """前端调用：告诉用户在 Max 中执行旋律捕获"""
    _bridge_state["listening"] = True
    _bridge_state["listen_start_time"] = datetime.now().isoformat()
    # 清空上一次结果，避免立刻返回旧数据导致“秒回”（尤其是和弦按钮）
    _bridge_state["latest_result"] = None
    _bridge_state["timestamp"] = None
    return {"status": "listening", "message": "Now listening for Max capture. Click the capture button in Max for Live."}


@app.post("/bridge/result", response_model=None)
def bridge_store_result(payload: Dict[str, Any]) -> Dict[str, str]:
    """桥接脚本调用此端点存储结果（供前端查询）"""
    print(f"\n🔵 Backend: Received POST to /bridge/result")
    print(f"   Payload keys: {list(payload.keys())}")
    print(f"   Full track: {len(payload.get('full_track', []))} notes")
    print(f"   Added notes: {len(payload.get('added_notes', []))} notes")
    
    _bridge_state["latest_result"] = payload
    _bridge_state["timestamp"] = datetime.now().isoformat()
    _bridge_state["listening"] = False
    
    print(f"✅ Backend: Stored result, timestamp: {_bridge_state['timestamp']}")
    print(f"   State has_data: True")
    
    return {"status": "ok", "message": f"Result stored for {len(payload.get('added_notes', []))} notes"}


@app.post("/bridge/notify-max")
def bridge_notify_max(req: MaxNotifyRequest) -> Dict[str, Any]:
    """Frontend can call this to send a one-shot UDP event to Max (no polling)."""
    payload = {"event": req.event, "data": req.data}
    try:
        send_osc_json_to_max(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return {
        "status": "sent",
        "message": f"Sent event '{req.event}' to Max",
        "host": MAX_UDP_HOST,
        "port": MAX_UDP_PORT, 
    }


@app.post("/export/midi")
def export_midi(req: ExportMidiRequest) -> Dict[str, Any]:
    """Export given notes to MIDI file and (on Windows) open folder."""
    if not req.notes:
        raise HTTPException(status_code=400, detail="notes is empty")

    notes: List[NoteDict] = [n.model_dump() for n in req.notes]  # type: ignore[assignment]
    # Build filename
    if req.filename:
        name = req.filename
    else:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        name = f"generated_{ts}.mid"

    out_path = ROOT_DIR / name
    try:
        written = export_notes_to_midi(notes, req.bpm, out_path)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write MIDI: {exc}")

    # Try to open folder on Windows for convenience
    try:
        if os.name == "nt":
            os.startfile(str(Path(written).parent))  # type: ignore[attr-defined]
    except Exception:
        pass  # non-fatal

    return {"status": "ok", "path": written}


def main():
    print("Melody Completion Tool")
    print("----------------------")

    midi_file = input("Input MIDI file path: ").strip()
    mood = input("Mood (single word): ").strip()
    bpm = float(input("BPM: ").strip())

    length_value = float(input("Length value: ").strip())
    length_unit = input("Length unit (bar/step/ms): ").strip()

    adventureness = float(
        input("Adventureness (0-100): ").strip()
    )

    completion = complete_melody_from_midi(
        midi_file,
        mood,
        bpm,
        length_value,
        length_unit,
        adventureness,
    )

    print("Completed MIDI written to:", completion.get("midi_file"))


if __name__ == "__main__":
    main()



