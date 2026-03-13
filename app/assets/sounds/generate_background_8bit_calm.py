"""Generate an original calm 8-bit background loop for EBBING_HOUSE.

This generator intentionally creates a fresh composition algorithmically instead
of encoding an existing melody. That keeps the result original while matching
the product mood:
- calm study background
- lightly mysterious / clockwork atmosphere
- retro 8-bit timbre

Output:
    app/assets/sounds/background_8bit_calm.wav
"""

from __future__ import annotations

import math
import random
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 22_050
TEMPO_BPM = 80
STEPS_PER_BEAT = 2  # Eighth-note grid.
STEP_SECONDS = 60.0 / TEMPO_BPM / STEPS_PER_BEAT
BAR_STEPS = 8
TOTAL_BARS = 12
TOTAL_STEPS = BAR_STEPS * TOTAL_BARS
TOTAL_SECONDS = TOTAL_STEPS * STEP_SECONDS


@dataclass(frozen=True)
class NoteEvent:
    """Simple scheduled note event in seconds."""

    start_s: float
    duration_s: float
    midi_note: int
    amplitude: float
    waveform: str
    duty: float = 0.5
    vibrato_hz: float = 0.0
    vibrato_depth: float = 0.0


def midi_to_freq(midi_note: int) -> float:
    return 440.0 * (2.0 ** ((midi_note - 69) / 12.0))


def triangle_wave(phase: float) -> float:
    # Triangle in [-1, 1], gentle for calm bass foundation.
    return 1.0 - 4.0 * abs(phase - 0.5)


def pulse_wave(phase: float, duty: float) -> float:
    return 1.0 if phase < duty else -1.0


def adsr_envelope(local_t: float, duration: float) -> float:
    """Light envelope to avoid clicks and keep notes soft.

    We intentionally keep long-ish release for smoother overlap and less harsh
    retriggering in loops.
    """
    attack = min(0.012, duration * 0.25)
    decay = min(0.060, max(0.0, duration - attack) * 0.35)
    release = min(0.070, max(0.0, duration - attack - decay) * 0.40)
    sustain = 0.68

    if local_t < 0.0 or local_t > duration:
        return 0.0

    if local_t < attack and attack > 0:
        return local_t / attack

    if local_t < attack + decay and decay > 0:
        x = (local_t - attack) / decay
        return 1.0 + (sustain - 1.0) * x

    sustain_end = max(0.0, duration - release)
    if local_t < sustain_end:
        return sustain

    if release <= 0.0:
        return 0.0

    x = (local_t - sustain_end) / release
    return max(0.0, sustain * (1.0 - x))


def build_events() -> list[NoteEvent]:
    """Compose a calm 12-bar loop with subtle variations.

    The harmonic movement is intentionally restrained and cyclic so the loop is
    listenable for long sessions without sounding static.
    """
    # Chords expressed as MIDI notes near middle register.
    chords: list[list[int]] = [
        [50, 53, 57],  # Dm
        [46, 50, 53],  # Bb
        [48, 52, 55],  # C
        [45, 50, 52],  # Asus-sus color
        [50, 53, 57],  # Dm
        [43, 46, 50],  # Gm
        [46, 50, 53],  # Bb
        [45, 50, 52],  # Asus-sus
        [41, 45, 48],  # F
        [48, 52, 55],  # C
        [43, 46, 50],  # Gm
        [50, 53, 57],  # Dm (loop return)
    ]

    # Slight rhythmic/melodic alternations per section to reduce irritation.
    arp_patterns = [
        [0, 1, 2, 1, 0, 1, 2, 1],  # A
        [0, 2, 1, 2, 0, 2, 1, 2],  # B
        [1, 2, 1, 0, 1, 2, 1, 0],  # C
    ]
    lead_patterns = [
        [None, 0, None, 1, None, 2, None, 1],
        [None, 1, None, 2, None, 1, None, 0],
        [None, 2, None, 1, None, 0, None, 1],
    ]

    events: list[NoteEvent] = []

    for bar_index, chord in enumerate(chords):
        bar_start_step = bar_index * BAR_STEPS
        section = 0 if bar_index < 4 else (1 if bar_index < 8 else 2)
        arp_pattern = arp_patterns[section]
        lead_pattern = lead_patterns[section]

        root, third, fifth = chord

        # Bass: one note on beat 1, one on beat 3.
        bass_notes = [root - 24, fifth - 24]
        for bass_i, bass_note in enumerate(bass_notes):
            start_step = bar_start_step + bass_i * 4
            # 1.5 beats-ish sustain keeps it warm but not muddy.
            duration = STEP_SECONDS * 3.2
            events.append(
                NoteEvent(
                    start_s=start_step * STEP_SECONDS,
                    duration_s=duration,
                    midi_note=bass_note,
                    amplitude=0.17,
                    waveform="triangle",
                )
            )

        # Clockwork arpeggio: quiet and steady.
        for step_in_bar, chord_idx in enumerate(arp_pattern):
            note = chord[chord_idx] + 12
            events.append(
                NoteEvent(
                    start_s=(bar_start_step + step_in_bar) * STEP_SECONDS,
                    duration_s=STEP_SECONDS * 0.92,
                    midi_note=note,
                    amplitude=0.085,
                    waveform="pulse",
                    duty=0.25,
                )
            )

        # Sparse lead motif with mild vibrato for a "memory machine" identity.
        for step_in_bar, lead_idx in enumerate(lead_pattern):
            if lead_idx is None:
                continue
            note = chord[lead_idx] + 24
            # Last section ends with a soft return tone for loop continuity.
            if bar_index == TOTAL_BARS - 1 and step_in_bar >= 6:
                note = root + 24
            events.append(
                NoteEvent(
                    start_s=(bar_start_step + step_in_bar) * STEP_SECONDS,
                    duration_s=STEP_SECONDS * 1.5,
                    midi_note=note,
                    amplitude=0.10,
                    waveform="pulse",
                    duty=0.40,
                    vibrato_hz=4.8,
                    vibrato_depth=0.005,
                )
            )

        # Subtle per-beat tick to suggest a calm "time" pulse.
        for beat in range(4):
            start_s = (bar_start_step + beat * 2) * STEP_SECONDS
            events.append(
                NoteEvent(
                    start_s=start_s,
                    duration_s=0.06,
                    midi_note=72,
                    amplitude=0.018,
                    waveform="tick",
                )
            )

    return events


def synthesize(events: list[NoteEvent]) -> list[float]:
    total_samples = int(TOTAL_SECONDS * SAMPLE_RATE)
    samples = [0.0] * total_samples

    for event in events:
        start_idx = max(0, int(event.start_s * SAMPLE_RATE))
        end_idx = min(total_samples, int((event.start_s + event.duration_s) * SAMPLE_RATE))
        if end_idx <= start_idx:
            continue

        base_freq = midi_to_freq(event.midi_note)
        rng = random.Random(event.midi_note * 997 + start_idx)

        for idx in range(start_idx, end_idx):
            local_t = (idx - start_idx) / SAMPLE_RATE
            env = adsr_envelope(local_t, event.duration_s)
            if env <= 0.0:
                continue

            if event.waveform == "tick":
                # Filtered pseudo-noise tick.
                tone = (rng.uniform(-1.0, 1.0) + rng.uniform(-1.0, 1.0)) * 0.5
            else:
                freq = base_freq
                if event.vibrato_hz > 0 and event.vibrato_depth > 0:
                    freq *= 1.0 + math.sin(2.0 * math.pi * event.vibrato_hz * local_t) * event.vibrato_depth

                phase = (freq * local_t) % 1.0
                if event.waveform == "triangle":
                    tone = triangle_wave(phase)
                else:
                    tone = pulse_wave(phase, event.duty)

            samples[idx] += tone * env * event.amplitude

    # Very light, constant floor so repeated loops feel less sterile.
    hiss = random.Random(42)
    for i in range(total_samples):
        samples[i] += hiss.uniform(-1.0, 1.0) * 0.0014

    # Normalize with conservative headroom to stay calm and avoid harshness.
    peak = max(abs(v) for v in samples) or 1.0
    target_peak = 0.78
    gain = target_peak / peak
    return [max(-1.0, min(1.0, s * gain)) for s in samples]


def write_wav(path: Path, samples: list[float]) -> None:
    pcm_bytes = bytearray()
    for sample in samples:
        value = int(sample * 32767.0)
        pcm_bytes.extend(struct.pack("<h", value))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(pcm_bytes))


def main() -> None:
    output_path = Path(__file__).resolve().parent / "background_8bit_calm.wav"
    events = build_events()
    samples = synthesize(events)
    write_wav(output_path, samples)
    print(f"Generated: {output_path}")
    print(f"Duration: {TOTAL_SECONDS:.2f}s | Samples: {len(samples)} | Events: {len(events)}")


if __name__ == "__main__":
    main()

