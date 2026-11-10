"""Build the film's soundtrack: Pixabay "Cyber Security" (The_Mountain) as a bed + synthesized SFX on cues.

Cue frames come from src/Film.tsx / src/Opening.tsx (30 fps). Output: out/soundtrack.wav
Run: python3 audio/mix.py && ffmpeg -i out/agentaudit.mp4 -i out/soundtrack.wav -c:v copy -c:a aac -b:a 192k -shortest out/agentaudit_sound.mp4
"""
import subprocess, sys
import numpy as np

SR, FPS, TOTAL = 48000, 30, 2520
MUSIC = sys.argv[1] if len(sys.argv) > 1 else "../../cloudfluently/insidia-showreel/audio/cyber-security-the_mountain.mp3"
rng = np.random.default_rng(7)
n = int(TOTAL / FPS * SR)
out = np.zeros((n, 2))

def place(sig, frame, gain=1.0, pan=0.0):
    i = int(frame / FPS * SR)
    sig = sig[: max(0, n - i)]
    l, r = gain * (1 - max(0, pan)), gain * (1 + min(0, pan))
    out[i:i + len(sig), 0] += sig * l
    out[i:i + len(sig), 1] += sig * r

def env(length, a, d):
    t = np.arange(length) / SR
    return np.minimum(1, t / a) * np.exp(-np.maximum(0, t - a) / d)

def lowpass(x, cutoff):  # one-pole, cutoff may be an array
    y = np.zeros_like(x); a = 1 - np.exp(-2 * np.pi * np.asarray(cutoff) / SR)
    a = np.broadcast_to(a, x.shape); acc = 0.0
    for k in range(len(x)):
        acc += a[k] * (x[k] - acc); y[k] = acc
    return y

def whoosh(dur=0.7):
    L = int(dur * SR); t = np.linspace(0, 1, L)
    cut = 300 + 5000 * np.sin(np.pi * t) ** 2
    s = lowpass(rng.standard_normal(L), cut) * np.sin(np.pi * t) ** 1.5
    return s / np.abs(s).max()

def thud(f0=90, dur=0.35):
    L = int(dur * SR); t = np.arange(L) / SR
    s = np.sin(2 * np.pi * (f0 + 60 * np.exp(-t * 30)) * t) * env(L, 0.002, 0.09)
    s += 0.25 * lowpass(rng.standard_normal(L), 2500) * env(L, 0.001, 0.02)
    return s / np.abs(s).max()

def hit():
    L = int(1.4 * SR); t = np.arange(L) / SR
    s = np.sin(2 * np.pi * (55 + 90 * np.exp(-t * 18)) * t) * env(L, 0.002, 0.35)
    s += 0.5 * lowpass(rng.standard_normal(L), 4000) * env(L, 0.001, 0.06)
    s += 0.15 * np.sin(2 * np.pi * 220 * t) * env(L, 0.01, 0.5)
    return s / np.abs(s).max()

def tick(f=2400):
    L = int(0.06 * SR); t = np.arange(L) / SR
    s = np.sin(2 * np.pi * f * t) * env(L, 0.0005, 0.012)
    return s / np.abs(s).max()

def key():
    L = int(0.03 * SR)
    s = lowpass(rng.standard_normal(L), 3500) * env(L, 0.0005, 0.006)
    return s / np.abs(s).max()

# --- cues (frames)
OPEN, SITS, WALK, BENCH = 0, 480, 690, 1640
for fr in (190, SITS, WALK, BENCH):
    place(whoosh(), fr - 8, 0.55)
for fr, g in ((22, 0.7), (56, 0.45), (66, 0.35)):
    place(thud(), fr, g)
place(hit(), 418, 0.9)
place(thud(70, 0.5), 418 + 22, 0.5)            # dot becomes the full stop
for fr in range(80, 80 + 30 * 1, 2):           # headline letters
    place(tick(1800 + rng.integers(0, 600)), fr, 0.08, pan=float(rng.uniform(-0.4, 0.4)))
for a in (60, 272, 382, 492, 602, 712, 866):   # walkthrough callouts
    place(tick(2600), WALK + a, 0.35)
    place(tick(3400), WALK + a + 2, 0.2)
k = WALK + 18                                  # typing in the recording (~0.2s -> 4.6s)
while k < WALK + 140:
    place(key(), k, 0.22, pan=float(rng.uniform(-0.3, 0.3))); k += float(rng.uniform(1.6, 3.2))
place(thud(110, 0.3), 1640 + 150, 0.35)         # ROC operating point lands
place(thud(80, 0.5), 2370 + 24, 0.6)            # end card full stop
for i, fr in enumerate((480 + 14, 480 + 30, 480 + 46)):  # gate boxes draw
    place(tick(1500 + i * 300), fr, 0.15)

# --- music bed: start on a bar line (grid 3.0 s anchored at 9.623 s), fade in/out
start = 9.623 - 3.0
raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start}", "-i", MUSIC, "-t", f"{TOTAL / FPS + 1}",
                      "-f", "f32le", "-ac", "2", "-ar", str(SR), "-"], capture_output=True, check=True).stdout
mus = np.frombuffer(raw, np.float32).reshape(-1, 2)[:n].astype(np.float64)
fade = np.ones(len(mus)); fi, fo = int(1.5 * SR), int(3.5 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
music = mus * fade[:, None] * 0.42
# gentle duck under the big hit
d = int(418 / FPS * SR); duck = np.ones(len(music)); duck[d:d + int(1.2 * SR)] = np.linspace(0.55, 1, int(1.2 * SR))
music *= duck[:, None]
mix = out[: len(music)] * 0.6 + music
mix /= max(1.0, np.abs(mix).max() / 0.95)

import wave
with wave.open("out/soundtrack.wav", "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
print("wrote out/soundtrack.wav", len(mix) / SR, "s")
