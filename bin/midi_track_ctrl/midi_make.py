from music21 import note, stream, duration


def write_melody(original_notes, new_notes, output_path: str):
    s = stream.Stream()

    for n in original_notes + new_notes:
        nt = note.Note(n["pitch"])
        nt.duration = duration.Duration(n["duration"])
        nt.volume.velocity = 80
        s.append(nt)

    s.write("midi", fp=output_path)
