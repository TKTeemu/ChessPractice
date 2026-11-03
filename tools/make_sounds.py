"""Synthesise the event sounds into assets/sounds/ (standard library only)."""

import math
import random
import struct
import wave
from pathlib import Path

RATE = 44100
OUT_DIR = Path(__file__).resolve().parent.parent / "assets" / "sounds"


def buffer(seconds):
    return [0.0] * int(RATE * seconds)


def add_click(buf, start, gain=1.0, tone=520.0, decay=0.010, tick=2400.0, noise=0.08, seed=1):
    """A short, crisp wooden click.

    Made of a very fast high "tick" for the sharp attack, a short body resonance with
    an inharmonic overtone (like a wooden block), and only a trace of noise.
    """
    rng = random.Random(seed)
    begin = int(start * RATE)
    for i in range(int(decay * 8 * RATE)):
        if begin + i >= len(buf):
            break
        t = i / RATE
        attack = min(1.0, t / 0.0004)   # 0.4 ms ramp avoids a digital pop
        sample = (0.55 * math.sin(2 * math.pi * tick * t) * math.exp(-t / 0.0025)
                  + 0.8 * math.sin(2 * math.pi * tone * t) * math.exp(-t / decay)
                  + 0.35 * math.sin(2 * math.pi * tone * 2.76 * t) * math.exp(-t / (decay * 0.5))
                  + noise * rng.uniform(-1, 1) * math.exp(-t / 0.0015))
        buf[begin + i] += gain * attack * sample


def add_tone(buf, start, freq, seconds, gain=0.4, attack=0.003, decay=0.05):
    begin = int(start * RATE)
    for i in range(int(seconds * RATE)):
        if begin + i >= len(buf):
            break
        t = i / RATE
        env = min(1.0, t / attack) * math.exp(-t / decay)
        buf[begin + i] += gain * env * (math.sin(2 * math.pi * freq * t)
                                        + 0.2 * math.sin(4 * math.pi * freq * t))


def save(name, buf, peak=0.8):
    top = max(abs(s) for s in buf) or 1.0
    frames = b"".join(struct.pack("<h", int(s / top * peak * 32767)) for s in buf)
    with wave.open(str(OUT_DIR / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(frames)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    b = buffer(0.07)
    add_click(b, 0.0)
    save("move", b, peak=0.7)

    b = buffer(0.08)
    add_click(b, 0.0, gain=1.2, tone=640, decay=0.008, tick=3200, noise=0.12, seed=2)
    add_click(b, 0.006, gain=0.6, tone=470, decay=0.007, tick=2600, seed=3)
    save("capture", b, peak=0.9)

    b = buffer(0.14)
    add_click(b, 0.0, seed=4)
    add_click(b, 0.07, gain=0.9, tone=470, seed=5)
    save("castle", b, peak=0.75)

    b = buffer(0.16)
    add_click(b, 0.0, seed=6)
    add_tone(b, 0.02, 1175, 0.14, gain=0.35, decay=0.035)
    save("check", b, peak=0.8)

    b = buffer(0.18)
    add_tone(b, 0.0, 784, 0.09, decay=0.03)
    add_tone(b, 0.07, 1175, 0.11, decay=0.04)
    save("promote", b, peak=0.7)

    b = buffer(0.45)
    for freq in (523.25, 659.25, 783.99):
        add_tone(b, 0.0, freq, 0.45, gain=0.3, attack=0.008, decay=0.12)
    save("end", b, peak=0.6)

    b = buffer(0.08)
    add_click(b, 0.0, gain=0.5, tone=180, decay=0.012, tick=900, noise=0.04, seed=7)
    add_tone(b, 0.0, 120, 0.07, gain=0.7, attack=0.001, decay=0.018)
    save("illegal", b, peak=0.75)

    print(f"Sounds written to {OUT_DIR}")


if __name__ == "__main__":
    main()
