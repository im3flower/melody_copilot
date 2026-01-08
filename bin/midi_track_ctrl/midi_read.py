from music21 import converter, note, chord


def read_melody(midi_path: str):
    score = converter.parse(midi_path)

    notes = []
    current_offset = 0.0

    for element in score.recurse().notes:
        dur = float(element.duration.quarterLength)

        if isinstance(element, note.Note):
            notes.append(
                {
                    "pitch": element.pitch.nameWithOctave,
                    "start": current_offset,
                    "duration": dur,
                }
            )
            current_offset += dur

        elif isinstance(element, chord.Chord):
            
            pitch = element.sortAscending().pitches[-1] #type: ignore
            notes.append(
                {
                    "pitch": pitch.nameWithOctave,
                    "start": current_offset,
                    "duration": dur,
                }
            )
            current_offset += dur

    tempo = score.metronomeMarkBoundaries()[0][2].number
    return notes, current_offset, tempo

