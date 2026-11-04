"""
Render the "drawer pulled out" product shot from the parametric v2 model.

    blender -b --python blender/render_drawer.py -- [out_dir]

Builds the machine with mia_model_v2.py (idle pose = finished, filled pouch), pulls the
drawer out and renders a close shot of the drawer with the pouch, on the GPU if one is
available (OptiX > CUDA > CPU).
"""
import os, sys, runpy, math

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0]) if argv else os.path.join(HERE, "out_v2")
os.makedirs(OUT, exist_ok=True)

os.environ["MIA_MODE"] = "none"          # model script: build + save only, no preview shots
os.environ["MIA_OUT"] = OUT
g = runpy.run_path(os.path.join(HERE, "mia_model_v2.py"))

import bpy

def use_gpu(sc):
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind
            prefs.get_devices()
            devs = [d for d in prefs.devices if d.type == kind]
            if devs:
                for d in prefs.devices: d.use = d.type == kind
                sc.cycles.device = "GPU"
                print("render device:", kind, [d.name for d in devs])
                return
        except Exception as e:
            print("no", kind, e)
    sc.cycles.device = "CPU"; print("render device: CPU")

def black_screen():
    """tablet off: glossy black glass, no UI blocks (looks cleaner than the placeholder UI)"""
    g["hide"]([f"ui_{i}" for i in range(4)], True)
    m = bpy.data.materials.get("screen")
    if m:
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1)
        b.inputs["Roughness"].default_value = 0.04
        b.inputs["Emission Strength"].default_value = 0.0
        if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 1.0

def shot(name, pose, loc, target, lens, res, samples, hide_cols=(), camera_hidden=(), transparent=False):
    g["build_all"](pose)
    black_screen()
    for cn in hide_cols:                     # e.g. keep the utility unit out of a product close-up
        c_ = bpy.data.collections.get(cn)
        if c_:
            for o in c_.objects: o.hide_render = o.hide_viewport = True
    for n in camera_hidden:                  # still lights/reflects the scene, just not seen by the camera
        o = bpy.data.objects.get(n)
        if o: o.visible_camera = False
    bpy.context.scene.render.film_transparent = transparent
    cam = g["camera"]("cam_" + name, loc, target, lens)
    sc = bpy.context.scene; sc.camera = cam
    sc.render.engine = "CYCLES"; use_gpu(sc)
    sc.cycles.samples = samples; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 12; sc.cycles.transmission_bounces = 12; sc.cycles.transparent_max_bounces = 16
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    vt = [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
    sc.view_settings.view_transform = "AgX" if "AgX" in vt else "Filmic"
    if sc.view_settings.view_transform == "AgX": sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.join(OUT, name + ".png")
    bpy.ops.render.render(write_still=True); print("rendered", sc.render.filepath)

T = g["TABLE_H"] * g["S"]
POSE = g["POSE"]
DRAFT = bool(os.environ.get("MIA_DRAFT"))
WANT = argv[1:] or ["drawer", "hero"]      # which shots: blender ... -- out_dir [drawer] [hero]

if "drawer" in WANT:
    # drawer out by 320 mm toward -Y; pouch spans z = T+200 .. T+750 (small preset).
    # The pouch faces are +-X, so the camera looks from the right-front to see the pouch face-on.
    shot("07_drawer_out_pouch", dict(POSE, drawer=1.0),
         loc=(1.55, -1.5, T + 0.95), target=(0.02, -0.36, T + 0.52), lens=50, hide_cols=("Skid",),
         res=(700, 500) if DRAFT else (2100, 1500), samples=24 if DRAFT else 256)

if "hero" in WANT:
    # home page cut-out: whole machine on its stand incl. the full stack light, transparent background.
    # Closer, slightly low camera from the front-left (heroic perspective); the studio floor and backdrop
    # stay in the scene for reflections and bounce light but are hidden from the camera.
    top = T + g["P"]["H"] * g["S"] + 0.2                     # cap + stack light
    shot("hero_machine", dict(POSE),
         loc=(-1.3, -2.95, 1.95), target=(0.02, 0.0, top / 2 + 0.05), lens=38,
         hide_cols=("Skid",), camera_hidden=("studio_floor", "backdrop"), transparent=True,
         res=(440, 1000) if DRAFT else (968, 2200), samples=24 if DRAFT else 256)
