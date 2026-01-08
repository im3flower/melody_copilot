const NOTE_SEQUENCE = [
  "C",
  "C#",
  "D",
  "D#",
  "E",
  "F",
  "F#",
  "G",
  "G#",
  "A",
  "A#",
  "B",
];

const LETTER_TO_OFFSET: Record<string, number> = {
  C: 0,
  D: 2,
  E: 4,
  F: 5,
  G: 7,
  A: 9,
  B: 11,
};

const normalizeAccidental = (accidental: string): "#" | "b" | "" => {
  if (!accidental) return "";
  const symbol = accidental.replace("♯", "#").replace("♭", "b");
  return symbol === "#" || symbol === "b" ? symbol : "";
};

export function midiToPitch(midi: number): string {
  if (Number.isNaN(midi)) {
    return "C4";
  }
  const clamped = Math.max(0, Math.min(127, Math.round(midi)));
  const octave = Math.floor(clamped / 12) - 1;
  const noteName = NOTE_SEQUENCE[clamped % 12];
  return `${noteName}${octave}`;
}

export function pitchToMidi(pitch: string): number {
  const match = pitch
    .trim()
    .match(/^([A-Ga-g])([#b♯♭]?)(-?\d+)$/);

  if (!match) {
    throw new Error(`Invalid pitch: ${pitch}`);
  }

  const [, letterRaw, accidentalRaw, octaveRaw] = match;
  const letter = letterRaw.toUpperCase();
  const accidental = normalizeAccidental(accidentalRaw);
  let octave = parseInt(octaveRaw, 10);

  let semitone = LETTER_TO_OFFSET[letter];
  if (typeof semitone !== "number") {
    throw new Error(`Unknown note letter: ${letter}`);
  }

  if (accidental === "#") {
    semitone += 1;
  } else if (accidental === "b") {
    semitone -= 1;
  }

  if (semitone < 0) {
    semitone += 12;
    octave -= 1;
  } else if (semitone > 11) {
    semitone -= 12;
    octave += 1;
  }

  const midi = (octave + 1) * 12 + semitone;
  if (midi < 0 || midi > 127) {
    throw new Error(`Pitch out of MIDI range: ${pitch}`);
  }

  return midi;
}

export function safePitchToMidi(pitch: string, fallback = 60): number {
  try {
    return pitchToMidi(pitch);
  } catch {
    return fallback;
  }
}
