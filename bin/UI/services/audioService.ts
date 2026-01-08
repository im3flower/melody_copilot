import { Note } from "../types";
import { safePitchToMidi } from "../utils/pitch";

class AudioService {
  private context: AudioContext | null = null;

  init() {
    if (!this.context) {
      this.context = new (window.AudioContext || (window as any).webkitAudioContext)();
    }
  }

  // Fix: MIDI pitch to frequency conversion (MIDI 69 = A4 = 440Hz, 60 = C4 = 261.63Hz)
  getFrequency(pitch: number) {
    // Standard MIDI pitch to frequency formula: f = 440 * 2^((pitch - 69) / 12)
    return 440 * Math.pow(2, (pitch - 69) / 12);
  }

  // Fix: Property 'step' does not exist on type 'Note'. Using 'start' and 'duration' instead.
  async playMelody(notes: Note[], bpm: number = 120) {
    this.init();
    if (!this.context) return;

    // A beat (quarter note) duration in seconds for accurate timing calculation
    const beatDuration = 60 / bpm;
    const now = this.context.currentTime;

    notes.forEach(note => {
      // Calculate start and stop times using quarterLength units from the Note interface
      const startTime = now + (note.start * beatDuration);
      const playDuration = note.duration * beatDuration;
      const midiPitch = safePitchToMidi(note.pitch);
      
      const osc = this.context!.createOscillator();
      const gain = this.context!.createGain();

      osc.type = 'sine';
      osc.frequency.setValueAtTime(this.getFrequency(midiPitch), startTime);
      
      gain.gain.setValueAtTime(0, startTime);
      gain.gain.linearRampToValueAtTime(0.2, startTime + 0.05);
      gain.gain.linearRampToValueAtTime(0, startTime + playDuration - 0.01);

      osc.connect(gain);
      gain.connect(this.context!.destination);

      osc.start(startTime);
      osc.stop(startTime + playDuration);
    });
  }

  playNote(pitch: number) {
    this.init();
    if (!this.context) return;

    const osc = this.context.createOscillator();
    const gain = this.context.createGain();

    osc.type = 'sine';
    osc.frequency.setValueAtTime(this.getFrequency(pitch), this.context.currentTime);
    
    gain.gain.setValueAtTime(0.2, this.context.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, this.context.currentTime + 0.5);

    osc.connect(gain);
    gain.connect(this.context.destination);

    osc.start();
    osc.stop(this.context.currentTime + 0.5);
  }
}

export const audioService = new AudioService();
