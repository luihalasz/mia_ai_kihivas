"""
Synthesised hype tech-trailer score for the MIA promo (120 BPM, 61 s), written as a 44.1 kHz stereo WAV.
Runs inside Blender's Python (numpy is bundled):

    blender -b --python blender/video/music.py -- <out.wav>

Sections follow the video cut (seconds): intro 0-7, load 7-19, process 19-37, safety 37-44,
fleet 44-56, logo hit at 56, tail to 61. A soft "ping" marks every yellow outline pulse.
"""
import sys, wave
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "score.wav"

SR = 44100
DUR = 61.0
N = int(SR * DUR)
BEAT = 0.5                                    # 120 BPM
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)              # dry bus
FX = np.zeros(N)                              # reverb send (mono)

def t_(d): return np.arange(int(SR * d)) / SR

def put(sig, start, gain=1.0, pan=0.0, send=0.0):
    i = int(start * SR)
    if i >= N: return
    s = sig[: N - i] * gain
    L[i:i + len(s)] += s * np.sqrt(0.5 * (1 - pan)) * 1.414
    R[i:i + len(s)] += s * np.sqrt(0.5 * (1 + pan)) * 1.414
    if send: FX[i:i + len(s)] += s * send

def fft_filter(x, lo=None, hi=None):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); g = np.ones_like(f)
    if hi: g *= 1 / np.sqrt(1 + (f / hi) ** 4)
    if lo: g *= 1 / np.sqrt(1 + (lo / np.maximum(f, 1e-3)) ** 4)
    return np.fft.irfft(X * g, len(x))

def saw(freq, d, detune=(0.0,)):
    t = t_(d); s = np.zeros_like(t)
    for c in detune:
        f = freq * 2 ** (c / 1200); s += 2 * ((t * f + rng.random()) % 1.0) - 1
    return s / len(detune)

def env(d, a=0.005, r=0.2, hold=0.0):
    t = t_(d); e = np.minimum(1, t / max(a, 1e-4))
    rel = np.clip((t - a - hold) / max(r, 1e-4), 0, None)
    return e * np.exp(-rel * 5)

# ---------------------------------------------------------------- instruments
def kick():
    t = t_(0.5); f = 45 + 110 * np.exp(-t * 28)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-t * 6.5) + 0.25 * fft_filter(rng.standard_normal(len(t)), lo=1500) * np.exp(-t * 120)
    return np.tanh(s * 1.6)

def clap():
    t = t_(0.35); n = fft_filter(rng.standard_normal(len(t)), lo=900, hi=6000)
    e = np.exp(-t * 18) + 0.6 * np.exp(-((t - 0.012) % 0.011) * 400) * (t < 0.035)
    return n * e * 0.8 + np.sin(2 * np.pi * 185 * t) * np.exp(-t * 30) * 0.4

def hat(open_=False):
    t = t_(0.25 if open_ else 0.06); n = fft_filter(rng.standard_normal(len(t)), lo=7000)
    return n * np.exp(-t * (14 if open_ else 70))

def bass_note(freq, d):
    return np.tanh(2.2 * fft_filter(saw(freq, d, (-6, 6)), hi=420)) * env(d, 0.004, d * 0.6, d * 0.2)

def pluck(freq, d=0.22):
    s = fft_filter(saw(freq, d, (-8, 8)) + 0.5 * np.sign(np.sin(2 * np.pi * freq * t_(d))), hi=2600)
    return s * env(d, 0.002, 0.12)

def pad(freqs, d):
    s = sum(saw(f, d, (-12, -4, 4, 12)) for f in freqs) / len(freqs)
    s = fft_filter(s, lo=90, hi=1400)
    t = t_(d); return s * np.minimum(1, t / 1.5) * np.minimum(1, (d - t) / 1.0)

def braam(d=3.0):
    t = t_(d)
    s = saw(55, d, (-10, 0, 10)) + 0.8 * saw(110, d, (-7, 7)) + 0.5 * saw(82.41, d, (-5, 5))
    s = fft_filter(s, hi=900)
    return np.tanh(1.8 * s) * np.exp(-t * 1.1) * np.minimum(1, t / 0.02)

def impact(d=4.0):
    t = t_(d); f = 32 + 70 * np.exp(-t * 9)
    boom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 1.6)
    crash = fft_filter(rng.standard_normal(len(t)), lo=2500) * np.exp(-t * 2.2) * 0.35
    return np.tanh(1.5 * boom) + crash

def riser(d):
    t = t_(d); n = rng.standard_normal(len(t)); out = np.zeros_like(t); seg = int(0.05 * SR)
    for i in range(0, len(t), seg):                          # band-pass sweeping upward
        c = 300 * (40 ** (i / len(t)))
        out[i:i + seg] = fft_filter(n[i:i + seg + 0], lo=c * 0.6, hi=c * 1.6)[: len(out[i:i + seg])]
    sweep = np.sin(2 * np.pi * np.cumsum(220 * 2 ** (3 * t / d)) / SR) * 0.25
    return (out * 1.4 + sweep) * (t / d) ** 2

def ping():
    t = t_(0.5)
    return (np.sin(2 * np.pi * 1760 * t) + 0.4 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 9) * np.minimum(1, t / 0.003)

# ---------------------------------------------------------------- arrangement
CHORDS = [(55.00, (220.0, 261.63, 329.63)),   # Am
          (43.65, (174.61, 220.0, 261.63)),   # F
          (65.41, (196.0, 261.63, 329.63)),   # C
          (49.00, (196.0, 246.94, 293.66))]   # G
BAR = 4 * BEAT

def chord_at(t): return CHORDS[int(t // BAR) % 4]

K, CL = kick(), clap()
H, HO = hat(), hat(True)

def drums(t0, t1, full=True, clap_on=True, hats=True, half=False):
    t = t0
    while t < t1 - 1e-6:
        b = round((t - t0) / BEAT)
        if not half or b % 2 == 0: put(K, t, 0.9)
        if clap_on and b % 2 == 1: put(CL, t, 0.45, send=0.25)
        if hats:
            for k in range(4):
                put(HO if (full and k == 2) else H, t + k * BEAT / 4, 0.16 if k % 2 else 0.09, pan=0.3 * (1 if k % 2 else -1))
        t += BEAT

def bassline(t0, t1, g=0.55):
    t = t0
    while t < t1 - 1e-6:
        root, _ = chord_at(t)
        put(bass_note(root * (2 if (round(t / (BEAT / 2)) % 4 == 3) else 1), BEAT / 2 * 0.95), t, g)
        t += BEAT / 2

def arp(t0, t1, g=0.16):
    t = t0; i = 0
    while t < t1 - 1e-6:
        _, ch = chord_at(t); notes = [ch[0] * 2, ch[1] * 2, ch[2] * 2, ch[1] * 4]
        put(pluck(notes[i % 4]), t, g, pan=0.5 * np.sin(i * 0.7), send=0.35)
        put(pluck(notes[i % 4]), t + 0.375, g * 0.35, pan=-0.5 * np.sin(i * 0.7), send=0.2)   # dotted-8th echo
        t += BEAT / 4; i += 1

# pad bed across the whole piece, chord per bar
t = 0.0
while t < 56:
    _, ch = chord_at(t); put(pad([c / 2 for c in ch], BAR + 1.0), t - 0.5 if t else 0, 0.22, send=0.4); t += BAR

# intro: heartbeat kick, sparse hats, riser into the load section
for i in range(14):
    if i % 2 == 0: put(K, i * BEAT, 0.55 + 0.03 * i)
for i in range(4, 14): put(H, i * BEAT + BEAT / 2, 0.06)
put(riser(2.0), 5.0, 0.35)
# sections
for t0, kind in ((7, "load"), (19, "process"), (37, "safety"), (44, "fleet")):
    put(braam(3.0), t0, 0.5, send=0.5); put(impact(2.0), t0, 0.35, send=0.4)
drums(7, 19, full=False, clap_on=False); bassline(7, 19, 0.45); arp(11, 19, 0.10)
drums(19, 37); bassline(19, 37); arp(19, 37)
arp(37, 44, 0.14); bassline(41, 44, 0.4); drums(41, 44, full=False, clap_on=False, half=True)
put(riser(1.0), 43.0, 0.3)
drums(44, 54); bassline(44, 55.5); arp(44, 56, 0.18)
for i in range(8): put(K, 54 + i * BEAT / 4, 0.5 + 0.05 * i)              # snare-roll style build on the kick
put(riser(4.0), 52.0, 0.55)
# logo hit
put(impact(5.0), 56.0, 0.9, send=0.6); put(braam(5.0), 56.0, 0.7, send=0.7)
put(pad([110, 164.81, 220, 277.18], 5.0), 56.0, 0.25, send=0.6)
# pings on the yellow outline pulses (video frames at 25 fps; each flash pulses at +4 and +23)
for f0 in (215, 390, 493, 635, 725, 795, 875, 945, 1030):
    for d in (4, 23):
        put(ping(), (f0 + d - 1) / 25.0, 0.12, pan=0.2, send=0.5)

# ---------------------------------------------------------------- reverb + master
ir_t = t_(2.6); ir = rng.standard_normal(len(ir_t)) * np.exp(-ir_t * 2.4); ir[0] = 0
ir = fft_filter(ir, hi=5000); ir /= np.sqrt(np.sum(ir ** 2))
nfft = 1 << int(np.ceil(np.log2(N + len(ir))))
wet = np.fft.irfft(np.fft.rfft(FX, nfft) * np.fft.rfft(ir, nfft), nfft)[:N] * 0.6
wetR = np.roll(wet, int(0.013 * SR))
L += wet; R += wetR
mix = np.stack([L, R])
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.6)
fade = np.ones(N); fi = int(0.4 * SR); fo = int(2.5 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo) ** 2
mix *= fade * (0.89 / np.max(np.abs(mix)))
pcm = (np.clip(mix.T, -1, 1) * 32767).astype("<i2")
with wave.open(OUT, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("MUSIC DONE", OUT, flush=True)
