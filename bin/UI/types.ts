export type Note = {
  pitch: string;
  start: number;
  duration: number;
};

export type Chord = {
  symbol: string;
  start: number;
  duration: number;
};

export enum Mood {
  HAPPY = "happy",
  SAD = "sad",
  DARK = "dark",
  EPIC = "epic",
}

export type MelodyUnit = "bar" | "step" | "ms";

export type CompletionResponse = {
  full_track: Note[];
  added_notes: Note[];
  midi_file?: string | null;
};

export type DefaultSeed = {
  notes: Note[];
  bpm: number;
  notes_text: string;
  midi_file?: string | null;
  chords: Chord[];
  chords_text: string;
};


