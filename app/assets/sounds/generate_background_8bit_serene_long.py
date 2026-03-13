"""Generate a longer calmer retro background loop for EBBING_HOUSE.

Design intent:
- original composition (no melodic copy from references)
- longer cycle to reduce loop fatigue
- calm, study-friendly retro timbre (triangle + soft pulse)

Output:
    app/assets/sounds/background_8bit_serene_long.wav
"""

from __future__ import annotations

import math
import random
import struct
import wave
from dataclasses import dataclass
from pathlib import Path

SAMPLE_RATE = 22_050
TEMPO_BPM = 72
STEPS_PER_BEAT = 2  # Eighth-note grid keeps it retro but still fluid.
STEP_SECONDS = 60.0 / TEMPO_BPM / STEPS_PER_BEAT
BAR_STEPS = 8
TOTAL_BARS = 14  # ~46.7s loop
TOTAL_STEPS = BAR_STEPS * TOTAL_BARS
TOTAL_SECONDS = TOTAL_STEPS * STEP_SECONDS


@dataclass(frozen=True)
class NoteEvent:
    start_s: float
    duration_s: float
    midi_note: int
    amplitude: float
    waveform: str
    duty: float = 0.5
    vibrato_hz: float = 0.0
    vibrato_depth: float = 0.0


def midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12.0))


def triangle_wave(phase: float) -> float:
    return 1.0 - 4.0 * abs(phase - 0.5)


def pulse_wave(phase: float, duty: float) -> float:
    return 1.0 if phase < duty else -1.0


def envelope(local_t: float, duration: float) -> float:
    """Soft envelope to keep note edges smooth and calm."""
    attack = min(0.018, duration * 0.25)
    decay = min(0.080, max(0.0, duration - attack) * 0.30)
    release = min(0.110, max(0.0, duration - attack - decay) * 0.40)
    sustain = 0.62

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
    if release <= 0:
        return 0.0
    x = (local_t - sustain_end) / release
    return max(0.0, sustain * (1.0 - x))


def build_events() -> list[NoteEvent]:
    """Compose a longer loop with restrained harmonic movement.

    We use a 7-bar progression repeated twice with slight motif rotation.
    That gives familiarity without a short repetitive cycle.
    """
    progression = [
        [50, 53, 57],  # Dm
        [48, 52, 55],  # C
        [46, 50, 53],  # Bb
        [43, 46, 50],  # Gm
        [50, 53, 57],  # Dm
        [45, 50, 52],  # Asus color
        [41, 45, 48],  # F
    ]
    chords = progression + progression

    arp_motifs = [
        [0, 1, 2, 1, 0, 1, 2, 1],
        [0, 2, 1, 2, 0, 2, 1, 2],
        [1, 2, 1, 0, 1, 2, 1, 0],
        [0, 1, 0, 2, 0, 1, 0, 2],
    ]
    lead_motifs = [
        [None, 0, None, None, None, 1, None, None],
        [None, None, 1, None, None, 2, None, None],
        [None, 2, None, None, None, 1, None, None],
    ]

    events: list[NoteEvent] = []
    for bar_idx, chord in enumerate(chords):
        root, _, fifth = chord
        bar_step = bar_idx * BAR_STEPS

        # Gentle bass anchor, two long notes per bar.
        for i, note in enumerate((root - 24, fifth - 24)):
            start = (bar_step + i * 4) * STEP_SECONDS
            events.append(
                NoteEvent(
                    start_s=start,
                    duration_s=STEP_SECONDS * 3.6,
                    midi_note=note,
                    amplitude=0.14,
                    waveform="triangle",
                )
            )

        # Quiet pulse arpeggio with low amplitude.
        arp = arp_motifs[bar_idx % len(arp_motifs)]
        for step_in_bar, idx in enumerate(arp):
            events.append(
                NoteEvent(
                    start_s=(bar_step + step_in_bar) * STEP_SECONDS,
                    duration_s=STEP_SECONDS * 0.92,
                    midi_note=chord[idx] + 12,
                    amplitude=0.062,
                    waveform="pulse",
                    duty=0.28,
                )
            )

        # Sparse high motif keeps identity without being insistent.
        lead = lead_motifs[bar_idx % len(lead_motifs)]
        for step_in_bar, idx in enumerate(lead):
            if idx is None:
                continue
            note = chord[idx] + 24
            if bar_idx == TOTAL_BARS - 1 and step_in_bar >= 5:
                # Soft return tone helps seamless loop boundary.
                note = root + 24
            events.append(
                NoteEvent(
                    start_s=(bar_step + step_in_bar) * STEP_SECONDS,
                    duration_s=STEP_SECONDS * 1.75,
                    midi_note=note,
                    amplitude=0.072,
                    waveform="pulse",
                    duty=0.42,
                    vibrato_hz=4.2,
                    vibrato_depth=0.0038,
                )
            )

        # Minimal "clock" tick every beat, quieter than previous track.
        for beat in range(4):
            events.append(
                NoteEvent(
                    start_s=(bar_step + beat * 2) * STEP_SECONDS,
                    duration_s=0.045,
                    midi_note=74,
                    amplitude=0.012,
                    waveform="tick",
                )
            )

    return events


def synthesize(events: list[NoteEvent]) -> list[float]:
    total_samples = int(TOTAL_SECONDS * SAMPLE_RATE)
    samples = [0.0] * total_samples

    for event in events:
        start = max(0, int(event.start_s * SAMPLE_RATE))
        end = min(total_samples, int((event.start_s + event.duration_s) * SAMPLE_RATE))
        if end <= start:
            continue

        base_freq = midi_to_freq(event.midi_note)
        rng = random.Random((event.midi_note * 4099) ^ start)

        for idx in range(start, end):
            local_t = (idx - start) / SAMPLE_RATE
            env = envelope(local_t, event.duration_s)
            if env <= 0.0:
                continue

            if event.waveform == "tick":
                tone = (rng.uniform(-1.0, 1.0) + rng.uniform(-1.0, 1.0)) * 0.35
            else:
                freq = base_freq
                if event.vibrato_hz > 0.0 and event.vibrato_depth > 0.0:
                    freq *= 1.0 + math.sin(2.0 * math.pi * event.vibrato_hz * local_t) * event.vibrato_depth
                phase = (freq * local_t) % 1.0
                if event.waveform == "triangle":
                    tone = triangle_wave(phase)
                else:
                    tone = pulse_wave(phase, event.duty)

            samples[idx] += tone * env * event.amplitude

    # Very low floor to avoid sterile silence between motifs.
    noise = random.Random(1337)
    for i in range(total_samples):
        samples[i] += noise.uniform(-1.0, 1.0) * 0.0012

    peak = max(abs(v) for v in samples) or 1.0
    gain = 0.74 / peak
    return [max(-1.0, min(1.0, sample * gain)) for sample in samples]


def write_wav(path: Path, samples: list[float]) -> None:
    payload = bytearray()
    for sample in samples:
        payload.extend(struct.pack("<h", int(sample * 32767.0)))

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(bytes(payload))


def main() -> None:
    output = Path(__file__).resolve().parent / "background_8bit_serene_long.wav"
    events = build_events()
    samples = synthesize(events)
    write_wav(output, samples)
    print(f"Generated: {output}")
    print(f"Duration: {TOTAL_SECONDS:.2f}s | Samples: {len(samples)} | Events: {len(events)}")


if __name__ == "__main__":
    main()
