/* Max for Live JavaScript - notesender.js
   Captures notes from selected MIDI clip and sends via UDP
   
   Usage: Put this in a [js] object in Max
   Wire outputs to [prepend send] → [udpsend 127.0.0.1 7400]
*/

inlets = 1;
outlets = 1;

// Global state
var live_api = null;
var current_clip = null;
var notes_buffer = [];

function init() {
    // Initialize Max/MSP environment
    if (typeof(max) !== 'undefined') {
        post("notesender.js loaded\n");
    }
}

function capture_notes(msg) {
    try {
        // Try to get current selected MIDI clip from Live
        if (!live_api) {
            post("notesender: live.object not available\n");
            return;
        }
        
        // Get current clip
        var clip = get_selected_clip();
        if (!clip) {
            post("notesender: No MIDI clip selected\n");
            return;
        }
        
        // Get all notes from clip
        var all_notes = get_all_notes(clip);
        var added_notes = [];  // For now, mark all as "added"
        
        // Format output
        var output = {
            full_track: all_notes,
            added_notes: all_notes,
            timestamp: new Date().toISOString(),
            source: "Max for Live"
        };
        
        // Send as JSON via outlet
        outlet(0, JSON.stringify(output));
        
        post("notesender: Captured " + all_notes.length + " notes\n");
        
    } catch (err) {
        post("notesender: Error - " + err + "\n");
    }
}

function get_selected_clip() {
    // This is a placeholder - actual implementation depends on 
    // how Live exposes the current clip through Max API
    try {
        // Example: access through live.object
        if (typeof(live) !== 'undefined') {
            // Implementation would go here
            post("notesender: Attempting to get selected clip...\n");
            return null;  // Placeholder
        }
    } catch (err) {
        post("notesender: Could not access clip - " + err + "\n");
    }
    return null;
}

function get_all_notes(clip) {
    var notes = [];
    try {
        // This would iterate through clip.notes and extract:
        // - pitch: MIDI note number (convert to note name)
        // - start: note start time in quarter notes
        // - duration: note duration in quarter notes
        
        // Placeholder implementation
        post("notesender: get_all_notes() - implement based on Live API\n");
        
    } catch (err) {
        post("notesender: Error getting notes - " + err + "\n");
    }
    return notes;
}

function note_name_from_pitch(pitch) {
    // Convert MIDI pitch number to note name
    var notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    var octave = Math.floor(pitch / 12) - 1;
    var note = notes[pitch % 12];
    return note + octave;
}

function bang() {
    capture_notes();
}

// Initialize on load
init();
