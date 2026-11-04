"""
Cut the rendered shots into the MIA promo (~61 s, 1280x720, 25 fps, H.264 MP4) with English captions,
a Polinvent logo end card and the synthesised trailer score (music.py).

    blender -b --python blender/video/assemble.py -- <frames_dir> <score.wav> <out.mp4>
"""
import os, sys, bpy

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
FRAMES = os.path.abspath(argv[0]); SCORE = os.path.abspath(argv[1]); OUT = os.path.abspath(argv[2])
LOGO = os.path.join(HERE, "polinvent_logo.png")
FPS = 25

SHOTS = [("A", 1, 175), ("B", 176, 300), ("C", 476, 450), ("D", 926, 175), ("E", 1101, 300)]   # name, start, length
END0, END_LEN = 1401, 125
TOTAL = END0 + END_LEN - 1

FONT_B = r"C:\Windows\Fonts\seguisb.ttf"   # Segoe UI Semibold
FONT_R = r"C:\Windows\Fonts\segoeui.ttf"

# (start, end, main, sub) – global frames; each line stays up for 3–6 s
CAPS = [
    (182, 355, "Pull out the drawer, insert the film", "No more threading the film blind through a part you can't see"),
    (365, 472, "Two green buttons: two-hand safety start", "…and the whole cycle runs on its own"),
    (480, 600, "Vacuum cups hold the film", "No slipping – unlike clamping it with a cylinder"),
    (605, 715, "Pressure filling, no splashing", "instead of direct peristaltic filling"),
    (720, 790, "Smoothing jaws", "The film corners can't fold in before clipping and sealing"),
    (795, 922, "Clip + 5 mm seal", "The clip stays on the pouch as a divider"),
    (930, 1015, "Closed housing, full protection", "The cylinder can't pinch the operator's hand"),
    (1018, 1098, "Two adjustable pouch sizes", "330 ml – 2.25 l, eight fill sizes"),
    (1106, 1250, "4 MIA = 1 Manyika footprint", "Four independent machines in the same floor space"),
    (1252, 1398, "1 operator instead of 5", "One person walks the line and starts each machine"),
]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
RW, RH = 1280, 720
K = RH / 1080                                 # sizes below are written for 1080p
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = RW, RH, 100
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

def text(name, ch, start, end, body, size, x, y, font, anchor="LEFT", box=False, color=(1, 1, 1, 1), n=8):
    t = effect(name, 'TEXT', ch, start, end - start)
    t.text = body; t.font_size = round(size * K); t.location = (x, y); t.color = color
    t.anchor_x = anchor; t.anchor_y = 'BOTTOM'
    if font: t.font = font
    t.use_shadow = True
    try: t.shadow_color = (0, 0, 0, 0.85)
    except Exception: pass
    if box:
        t.use_box = True; t.box_color = (0, 0, 0, 0.55)
        try: t.box_margin = 0.012
        except Exception: pass
    t.blend_type = 'ALPHA_OVER'
    fade(t, start, end, n)
    return t

base = effect("black", 'COLOR', 1, 1, TOTAL); base.color = (0, 0, 0)

for name, start, length in SHOTS:
    d = os.path.join(FRAMES, name)
    files = sorted(f for f in os.listdir(d) if f.lower().endswith(".png"))[:length]
    try:   # frames may come from a 1080p and a 720p run: always scale them to the canvas
        st = strips.new_image(name=f"shot_{name}", filepath=os.path.join(d, files[0]), channel=2, frame_start=start, fit_method='FIT')
    except TypeError:
        st = strips.new_image(name=f"shot_{name}", filepath=os.path.join(d, files[0]), channel=2, frame_start=start)
    for f in files[1:]: st.elements.append(f)
    st.blend_type = 'ALPHA_OVER'
    if name == "A": fade(st, start, start + len(files), 15)
    if name == "E":
        e = start + len(files)
        for f, a in ((start, 1.0), (e - 12, 1.0), (e, 0.0)):
            st.blend_alpha = a; st.keyframe_insert("blend_alpha", frame=f)

# title over the intro
text("title", 3, 15, 170, "MIA · Manyika 2", 132, 0.5, 0.17, fb, anchor="CENTER", n=12)
text("title_sub", 4, 28, 170, "Fill. Clip. Seal. One machine.", 50, 0.5, 0.1, fr, anchor="CENTER", color=(0.86, 0.88, 0.92, 1), n=12)

# lower-third captions
for i, (a, b, main, sub) in enumerate(CAPS):
    text(f"cap{i}", 3, a, b, main, 66, 0.05, 0.15, fb, box=True)
    text(f"sub{i}", 4, a + 5, b, sub, 40, 0.05, 0.088, fr, box=True, color=(0.88, 0.9, 0.94, 1))

# end card: Polinvent logo + coming soon
try:
    lg = strips.new_image(name="logo", filepath=LOGO, channel=3, frame_start=END0 + 2, fit_method='ORIGINAL')
except TypeError:
    lg = strips.new_image(name="logo", filepath=LOGO, channel=3, frame_start=END0 + 2)
lg.frame_final_duration = TOTAL - (END0 + 2) + 1
lg.blend_type = 'ALPHA_OVER'
try:
    lg.transform.scale_x = lg.transform.scale_y = 0.62 * K; lg.transform.offset_y = 90 * K
except Exception as e: print("logo transform", e)
for f, a in ((END0 + 2, 0.0), (END0 + 10, 1.0), (TOTAL - 20, 1.0), (TOTAL, 0.0)):
    lg.blend_alpha = a; lg.keyframe_insert("blend_alpha", frame=f)
text("end_soon", 4, END0 + 22, TOTAL, "Coming soon in 2027", 58, 0.5, 0.33, fr, anchor="CENTER", color=(0.9, 0.92, 0.95, 1), n=14)
text("end_disc", 5, END0 + 40, TOTAL, "AI-generated content – no criminal liability accepted. :)", 24, 0.5, 0.06,
     fr, anchor="CENTER", color=(0.5, 0.53, 0.57, 1), n=14)

# score
have_audio = False
try:
    strips.new_sound(name="score", filepath=SCORE, channel=6, frame_start=1); have_audio = True
except Exception as e:
    print("no audio:", e)

r = sc.render
try: r.image_settings.media_type = 'VIDEO'    # Blender 5.x: video formats live behind media_type
except Exception: pass
r.image_settings.file_format = 'FFMPEG'
r.ffmpeg.format = 'MPEG4'; r.ffmpeg.codec = 'H264'
try: r.ffmpeg.constant_rate_factor = 'HIGH'
except Exception: pass
r.ffmpeg.ffmpeg_preset = 'BEST'; r.ffmpeg.gopsize = 25
if have_audio: r.ffmpeg.audio_codec = 'AAC'; r.ffmpeg.audio_bitrate = 192; r.ffmpeg.audio_channels = 'STEREO'
r.filepath = OUT
bpy.ops.render.render(animation=True)
print("VIDEO DONE", OUT, flush=True)
