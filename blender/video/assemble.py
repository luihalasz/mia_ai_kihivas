"""
Cut the rendered shots into the MIA promo (~41 s, 1280x720, 25 fps, H.264 MP4) with Hungarian captions,
an end card and a soft synthesized pad.

    blender -b --python blender/video/assemble.py -- <frames_dir> <out.mp4>
"""
import os, sys, bpy

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = os.path.abspath(argv[0]); OUT = os.path.abspath(argv[1])
FPS = 25

SHOTS = [("A", 1, 125), ("B", 126, 175), ("C", 301, 275), ("D", 576, 125), ("E", 701, 200)]   # name, start, length
END0, END_LEN = 901, 125
TOTAL = END0 + END_LEN - 1

FONT_B = r"C:\Windows\Fonts\seguisb.ttf"   # Segoe UI Semibold (full Hungarian glyph set)
FONT_R = r"C:\Windows\Fonts\segoeui.ttf"

# (start, end, main, sub)
CAPS = [
    (131, 232, "Kihúzod a fiókot, behelyezed a fóliát", "Nem kell vakon, egy nem látható részen átfűzni, mint a Manyika 1-nél"),
    (236, 298, "Két zöld gomb: kétkezes biztonsági indítás", "és lefut a teljes ciklus"),
    (303, 358, "Vákuumkorongok fogják a fóliát", "nem csúszik le, mint a munkahengeres összeszorításnál"),
    (360, 428, "Nyomással töltünk, fröcsögés nélkül", "a korábbi direkt perisztaltikus töltés helyett"),
    (430, 500, "Simító pofák", "a fólia sarkai nem fordulnak be klipszelés és hegesztés előtt"),
    (502, 573, "Klipsz és 5 mm-es hegesztés", "a klipsz térelválasztóként a tasakon marad"),
    (578, 636, "Zárt burkolat, teljes védelem", "a munkahenger nem csípheti oda az operátor kezét"),
    (638, 698, "Két állítható zacskóméret", "330 ml – 2,25 l, nyolc kiszerelés"),
    (703, 800, "4 MIA = 1 Manyika 1 helye", "ugyanakkora alapterületen négy önálló gép"),
    (802, 898, "5 operátor helyett 1", "végigsétál a soron, és sorban elindítja őket"),
]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 100
sc.render.fps = FPS; sc.frame_start, sc.frame_end = 1, TOTAL
se = sc.sequence_editor_create()
strips = se.strips if hasattr(se, "strips") else se.sequences
fb = bpy.data.fonts.load(FONT_B) if os.path.exists(FONT_B) else None
fr = bpy.data.fonts.load(FONT_R) if os.path.exists(FONT_R) else None

def effect(name, kind, ch, start, length):
    try: return strips.new_effect(name=name, type=kind, channel=ch, frame_start=start, length=length)
    except TypeError: return strips.new_effect(name=name, type=kind, channel=ch, frame_start=start, frame_end=start + length)

def fade(st, start, end, n=8):
    for f, a in ((start, 0.0), (start + n, 1.0), (end - n, 1.0), (end, 0.0)):
        st.blend_alpha = a; st.keyframe_insert("blend_alpha", frame=f)

def text(name, ch, start, end, body, size, x, y, font, anchor="LEFT", box=False, color=(1, 1, 1, 1)):
    t = effect(name, 'TEXT', ch, start, end - start)
    t.text = body; t.font_size = size; t.location = (x, y); t.color = color
    t.anchor_x = anchor; t.anchor_y = 'BOTTOM'
    if font: t.font = font
    t.use_shadow = True
    try: t.shadow_color = (0, 0, 0, 0.8)
    except Exception: pass
    if box:
        t.use_box = True; t.box_color = (0, 0, 0, 0.5)
        try: t.box_margin = 0.012
        except Exception: pass
    t.blend_type = 'ALPHA_OVER'
    fade(t, start, end, 7)
    return t

# black base under everything
base = effect("black", 'COLOR', 1, 1, TOTAL); base.color = (0, 0, 0)

for name, start, length in SHOTS:
    d = os.path.join(FRAMES, name)
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".png"))[:length]
    st = strips.new_image(name=f"shot_{name}", filepath=os.path.join(d, files[0]), channel=2, frame_start=start)
    for f in files[1:]: st.elements.append(f)
    st.blend_type = 'ALPHA_OVER'
    if name == "A": fade(st, start, start + len(files), 12)
    if name == "E":
        e = start + len(files)
        for f, a in ((start, 1.0), (e - 18, 1.0), (e, 0.0)):
            st.blend_alpha = a; st.keyframe_insert("blend_alpha", frame=f)

# title over the intro
text("title", 3, 12, 122, "MIA · Manyika 2", 86, 0.5, 0.17, fb, anchor="CENTER")
text("title_sub", 4, 22, 122, "Tölt. Klipszel. Hegeszt. Egyetlen gép.", 34, 0.5, 0.1, fr, anchor="CENTER", color=(0.85, 0.87, 0.9, 1))

# lower-third captions
for i, (a, b, main, sub) in enumerate(CAPS):
    text(f"cap{i}", 3, a, b, main, 48, 0.055, 0.15, fb, box=True)
    text(f"sub{i}", 4, a + 4, b, sub, 28, 0.055, 0.085, fr, color=(0.86, 0.88, 0.92, 1))

# end card
text("end_main", 3, END0 + 4, TOTAL, "Még mindig nincs kész. :)", 72, 0.5, 0.52, fb, anchor="CENTER")
text("end_disc", 4, END0 + 40, TOTAL, "Ez AI által generált tartalom, amiért semmilyen büntetőjogi felelősséget nem vállalunk.",
     26, 0.5, 0.38, fr, anchor="CENTER", color=(0.75, 0.78, 0.82, 1))
text("end_brand", 5, END0 + 40, TOTAL, "Equipment R&D · Polinvent · MIA (Manyika 2)", 22, 0.5, 0.08, fr, anchor="CENTER", color=(0.55, 0.58, 0.62, 1))

# soft synthesized pad (A major-ish chord), fades in/out; skipped if the audio API is unavailable
have_audio = False
try:
    import aud
    secs = TOTAL / FPS
    wav = os.path.join(FRAMES, "pad.wav")
    snd = None
    for f, v in ((110.0, 0.05), (164.81, 0.035), (220.0, 0.03), (277.18, 0.022), (329.63, 0.018)):
        s = aud.Sound.sine(f, 48000).volume(v).limit(0, secs)
        snd = s if snd is None else snd.mix(s)
    snd = snd.lowpass(1200, 0.7).fadein(0, 2.5).fadeout(secs - 3.5, 3.5)
    snd.write(wav, 48000, aud.CHANNELS_STEREO, aud.FORMAT_S16, aud.CONTAINER_WAV, aud.CODEC_PCM)
    strips.new_sound(name="pad", filepath=wav, channel=6, frame_start=1)
    have_audio = True
except Exception as e:
    print("no audio:", e)

r = sc.render
try: r.image_settings.media_type = 'VIDEO'    # Blender 5.x: video formats live behind media_type
except Exception: pass
r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'
try: r.ffmpeg.constant_rate_factor = 'HIGH'
except Exception: pass
r.ffmpeg.ffmpeg_preset = 'GOOD'; r.ffmpeg.gopsize = 25
if have_audio: r.ffmpeg.audio_codec = 'AAC'; r.ffmpeg.audio_bitrate = 160
r.filepath = OUT
bpy.ops.render.render(animation=True)
print("VIDEO DONE", OUT, flush=True)
