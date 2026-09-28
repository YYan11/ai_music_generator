const audioPlayer = document.getElementById("audio-player");
const pianoRollPanel = document.getElementById("piano-roll-panel");
const pianoRollSummary = document.getElementById("piano-roll-summary");
const pianoRollViewport = document.getElementById("piano-roll-viewport");
const pianoRollGrid = document.getElementById("piano-roll-grid");
const pianoRollPlayhead = document.getElementById("piano-roll-playhead");
const instrumentLegend = document.getElementById("instrument-legend");

let pianoRollState = {
  midiUrl: "",
  totalBeats: 0,
  bpm: 120,
  animationId: null,
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

export function stopPianoRollAnimation() {
  if (pianoRollState.animationId) {
    cancelAnimationFrame(pianoRollState.animationId);
    pianoRollState.animationId = null;
  }
}

export function updatePianoRollPlayhead(seconds) {
  if (!pianoRollPlayhead || !pianoRollViewport || !pianoRollState.totalBeats) {
    return;
  }

  const beat = Math.max(0, seconds * (pianoRollState.bpm / 60));
  const rollWidth = Math.max((pianoRollGrid?.offsetWidth || pianoRollViewport.scrollWidth) - 52, 1);
  const x = Math.min((beat / pianoRollState.totalBeats) * rollWidth, rollWidth);
  pianoRollPlayhead.style.transform = `translateX(${x}px)`;
}

export function startPianoRollAnimation(mode = "midi") {
  stopPianoRollAnimation();

  const tick = () => {
    const seconds = mode === "audio"
      ? audioPlayer.currentTime || 0
      : window.Tone?.Transport?.seconds || 0;
    updatePianoRollPlayhead(seconds);
    pianoRollState.animationId = requestAnimationFrame(tick);
  };

  tick();
}

export function resetPianoRoll() {
  stopPianoRollAnimation();
  pianoRollState = {
    midiUrl: "",
    totalBeats: 0,
    bpm: 120,
    animationId: null,
  };

  if (pianoRollGrid) {
    pianoRollGrid.innerHTML = "";
    pianoRollGrid.style.width = "";
    pianoRollGrid.style.height = "";
  }
  if (instrumentLegend) {
    instrumentLegend.innerHTML = "";
  }
  if (pianoRollSummary) {
    pianoRollSummary.textContent = "Waiting for generated MIDI.";
  }
  updatePianoRollPlayhead(0);
  pianoRollPanel?.classList.add("hidden");
}

function noteLabelFromMidi(midiNumber) {
  const names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
  return `${names[midiNumber % 12]}${Math.floor(midiNumber / 12) - 1}`;
}

function getTrackLabel(track, index) {
  const instrument = track.instrument?.name || track.name || `Track ${index + 1}`;
  const family = track.instrument?.family ? ` (${track.instrument.family})` : "";
  return `${instrument}${family}`;
}

function noteBeatPosition(note, midi) {
  const ppq = midi.header.ppq || 480;
  if (Number.isFinite(note.ticks) && Number.isFinite(note.durationTicks)) {
    return {
      start: note.ticks / ppq,
      duration: Math.max(note.durationTicks / ppq, 0.25),
    };
  }

  const bpm = midi.header.tempos?.[0]?.bpm || 120;
  return {
    start: note.time * (bpm / 60),
    duration: Math.max(note.duration * (bpm / 60), 0.25),
  };
}

export function renderPianoRoll(midi, midiUrl) {
  if (!pianoRollPanel || !pianoRollGrid || !instrumentLegend) {
    return;
  }

  const bpm = midi.header.tempos?.[0]?.bpm || 120;
  const timeSignature = midi.header.timeSignatures?.[0]?.timeSignature || [4, 4];
  const beatsPerBar = Number(timeSignature[0]) || 4;
  const beatWidth = 58;
  const rowHeight = 28;
  const labelWidth = 52;
  const topOffset = 38;
  const colors = ["#bdecc3", "#a7d8ff", "#f7c9ff", "#ffd58d", "#d7c6ff", "#ffb5b5", "#b9fff2"];
  const allNotes = [];
  const instruments = [];

  midi.tracks.forEach((track, trackIndex) => {
    if (!track.notes.length) {
      return;
    }

    const label = getTrackLabel(track, trackIndex);
    const color = colors[instruments.length % colors.length];
    instruments.push({ label, color });

    track.notes.forEach((note) => {
      const timing = noteBeatPosition(note, midi);
      allNotes.push({
        midi: note.midi,
        name: note.name || noteLabelFromMidi(note.midi),
        start: timing.start,
        duration: timing.duration,
        instrument: label,
        color,
      });
    });
  });

  if (!allNotes.length) {
    resetPianoRoll();
    if (pianoRollSummary) {
      pianoRollSummary.textContent = "This MIDI has no notes to display.";
    }
    return;
  }

  const minPitch = Math.min(...allNotes.map((note) => note.midi));
  const maxPitch = Math.max(...allNotes.map((note) => note.midi));
  const totalBeats = Math.max(
    beatsPerBar * 2,
    Math.ceil(Math.max(...allNotes.map((note) => note.start + note.duration)) / beatsPerBar) * beatsPerBar
  );
  const rowCount = maxPitch - minPitch + 1;
  const gridWidth = labelWidth + totalBeats * beatWidth;
  const gridHeight = topOffset + rowCount * rowHeight;

  pianoRollState = {
    midiUrl,
    totalBeats,
    bpm,
    animationId: pianoRollState.animationId,
  };

  const barLabels = Array.from({ length: totalBeats / beatsPerBar }, (_, index) => `
    <div class="piano-roll-bar-label" style="left:${labelWidth + index * beatsPerBar * beatWidth}px;width:${beatsPerBar * beatWidth}px">
      Bar ${index + 1}
    </div>
  `).join("");

  const beatLines = Array.from({ length: totalBeats + 1 }, (_, index) => {
    const isBar = index % beatsPerBar === 0;
    return `<div class="piano-roll-beat-line ${isBar ? "bar-line" : ""}" style="left:${labelWidth + index * beatWidth}px"></div>`;
  }).join("");

  const pitchRows = Array.from({ length: rowCount }, (_, index) => {
    const pitch = maxPitch - index;
    return `
      <div class="piano-roll-row" style="top:${topOffset + index * rowHeight}px">
        <span>${noteLabelFromMidi(pitch)}</span>
      </div>
    `;
  }).join("");

  const noteBlocks = allNotes.map((note) => {
    const top = topOffset + (maxPitch - note.midi) * rowHeight + 5;
    const left = labelWidth + note.start * beatWidth;
    const width = Math.max(note.duration * beatWidth, 12);
    return `
      <div
        class="piano-roll-note"
        title="${escapeHtml(note.name)} | ${escapeHtml(note.instrument)}"
        style="top:${top}px;left:${left}px;width:${width}px;background:${note.color};"
      ></div>
    `;
  }).join("");

  pianoRollGrid.style.width = `${gridWidth}px`;
  pianoRollGrid.style.height = `${gridHeight}px`;
  pianoRollGrid.innerHTML = barLabels + beatLines + pitchRows + noteBlocks;
  instrumentLegend.innerHTML = instruments.map((instrument) => `
    <span><i style="background:${instrument.color}"></i>${escapeHtml(instrument.label)}</span>
  `).join("");

  pianoRollSummary.textContent = `${allNotes.length} notes | ${instruments.length} instruments | ${beatsPerBar}/4 grid`;
  pianoRollPanel.classList.remove("hidden");
  updatePianoRollPlayhead(0);
}

export async function preparePianoRoll(midiUrl) {
  if (!window.Midi || !midiUrl) {
    return;
  }

  const response = await fetch(midiUrl);
  if (!response.ok) {
    throw new Error("Could not load the generated MIDI for piano roll preview.");
  }

  const arrayBuffer = await response.arrayBuffer();
  renderPianoRoll(new Midi(arrayBuffer), midiUrl);
}
