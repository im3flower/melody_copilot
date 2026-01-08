import { Note, MelodyUnit, CompletionResponse, DefaultSeed, Chord } from "../types";

const RAW_BASE_URL =
  (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";
const BASE_URL = RAW_BASE_URL.replace(/\/$/, "");
const COMPLETE_URL = `${BASE_URL}/complete`;
const DEFAULT_URL = `${BASE_URL}/default`;
const BRIDGE_LATEST_URL = `${BASE_URL}/bridge/latest`;
const EXPORT_MIDI_URL = `${BASE_URL}/export/midi`;

export type CompletionRequest = {
  original_notes: Note[];
  mood: string;
  bpm: number;
  length_value: number;
  length_unit: MelodyUnit;
  adventureness: number;
  chords?: Chord[];
};

export type BridgeLatestResponse = {
  added_notes: Note[];
  full_track: Note[];
  timestamp: string | null;
  has_data: boolean;
};

export type NotifyMaxRequest = {
  event: string;
  data?: Record<string, unknown>;
};

export type NotifyMaxResponse = {
  status: string;
  message: string;
  host: string;
  port: number;
};

export type ExportMidiRequest = {
  notes: Note[];
  bpm: number;
  filename?: string;
};

export type ExportMidiResponse = {
  status: string;
  path: string;
};

export async function completeMelody(data: CompletionRequest): Promise<CompletionResponse> {
  const res = await fetch(COMPLETE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });

  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Backend error");
  }

  return res.json();
}

export async function fetchDefaultSeed(): Promise<DefaultSeed> {
  const res = await fetch(DEFAULT_URL, { method: "GET" });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Failed to load default seed");
  }
  return res.json();
}

export async function fetchBridgeLatest(): Promise<BridgeLatestResponse> {
  const res = await fetch(BRIDGE_LATEST_URL, { method: "GET" });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Failed to fetch bridge result");
  }
  return res.json();
}

export async function startLiveCapture(): Promise<{ status: string; message: string }> {
  const res = await fetch(`${BASE_URL}/bridge/start-capture`, { method: "POST" });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Failed to start capture");
  }
  return res.json();
}

export async function notifyMax(body: NotifyMaxRequest): Promise<NotifyMaxResponse> {
  const res = await fetch(`${BASE_URL}/bridge/notify-max`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Failed to notify Max");
  }
  return res.json();
}

export async function exportMidi(body: ExportMidiRequest): Promise<ExportMidiResponse> {
  const res = await fetch(EXPORT_MIDI_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errorText = await res.text();
    throw new Error(errorText || "Failed to export MIDI");
  }
  return res.json();
}
