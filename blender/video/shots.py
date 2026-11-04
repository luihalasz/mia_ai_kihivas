"""
MIA promo video – 3D shots rendered from the parametric v2 model.

    blender -b --python blender/video/shots.py -- <frames_dir> [shot ...] [--test]

Shots (25 fps, 1280x720):
  A intro    125 f  slow orbit around the closed machine
  B load     175 f  drawer out with an empty pouch -> slides in -> two green start buttons light up
  C process  275 f  cut-away: vacuum cups grip, ISO tube down + pressure fill, clipper with smoothers,
                    water glass down + fill, sealer
  D safety   125 f  closed housing, slow push-in
  E fleet    200 f  four machines side by side on the footprint of one Manyika 1, one operator walks along

--test renders a single middle frame per shot (framing check).
"""
import os, sys, math, runpy

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
TEST = "--test" in argv
argv = [a for a in argv if a != "--test"]
FRAMES = os.path.abspath(argv[0]) if argv else os.path.join(HERE, "frames")
WANT = argv[1:] or ["A", "B", "C", "D", "E"]

os.environ["MIA_MODE"] = "none"
os.environ["MIA_OUT"] = os.path.join(FRAMES, "_model")
g = runpy.run_path(os.path.join(HERE, "..", "mia_model_v2.py"))

import bpy
from mathutils import Vector

S = g["S"]; P = g["P"]; POSE = g["POSE"]; T = g["TABLE_H"] * S
FPS = 25

# ---------------------------------------------------------------- helpers
def obj(n): return bpy.data.objects.get(n)

def reparent_keep(child, parent):
    bpy.context.view_layer.update()
    mw = child.matrix_world.copy(); child.parent = parent; child.matrix_world = mw

def key(o, path, frame, value, index=-1):
    if index >= 0:
        getattr(o, path)[index] = value
        o.keyframe_insert(data_path=path, index=index, frame=frame)
    else:
        setattr(o, path, value); o.keyframe_insert(data_path=path, frame=frame)

def ease_all():
    for o in bpy.data.objects:
        ad = o.animation_data
        if ad and ad.action:
            try:
                for fc in ad.action.fcurves:
                    for kp in fc.keyframe_points: kp.interpolation = 'BEZIER'; kp.easing = 'AUTO'
            except Exception:
                pass   # layered actions (Blender 5): default interpolation is already Bezier

def hide_cols(*names):
    for cn in names:
        c = bpy.data.collections.get(cn)
        if c:
            for o in c.objects: o.hide_render = o.hide_viewport = True

def black_screen():
    g["hide"]([f"ui_{i}" for i in range(4)], True)
    m = bpy.data.materials.get("screen")
    if m:
        b = m.node_tree.nodes["Principled BSDF"]
        b.inputs["Base Color"].default_value = (0.004, 0.004, 0.005, 1); b.inputs["Roughness"].default_value = 0.04
        b.inputs["Emission Strength"].default_value = 0.0
        if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = 1.0

def setup(pose):
    g["build_all"](pose); black_screen(); hide_cols("Skid")
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            prefs.compute_device_type = kind; prefs.get_devices()
            if any(d.type == kind for d in prefs.devices):
                for d in prefs.devices: d.use = d.type == kind
                sc.cycles.device = "GPU"; break
        except Exception: pass
    sc.cycles.samples = 4 if TEST else 16; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.transparent_max_bounces = 10
    sc.render.use_persistent_data = True
    sc.render.use_overwrite = False; sc.render.use_placeholder = True   # a re-run resumes where it stopped
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1280, 720, 100
    sc.render.fps = FPS
    vt = [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
    sc.view_settings.view_transform = "AgX" if "AgX" in vt else "Filmic"
    if sc.view_settings.view_transform == "AgX": sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    return sc

def cam_rig(name, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    cam = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(cam)
    tgt = bpy.data.objects.new(name + "_tgt", None); bpy.context.scene.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam, tgt

def render(sc, shot, f0, f1):
    out = os.path.join(FRAMES, shot); os.makedirs(out, exist_ok=True)
    ease_all()
    if TEST:
        f = (f0 + f1) // 2; sc.frame_set(f)
        sc.render.filepath = os.path.join(FRAMES, "_test", f"{shot}.png")
        bpy.ops.render.render(write_still=True)
    else:
        sc.frame_start, sc.frame_end = f0, f1
        sc.render.filepath = os.path.join(out, "")
        bpy.ops.render.render(animation=True)
    print("SHOT DONE", shot, flush=True)

def mm(v): return v * S

# ---------------------------------------------------------------- A: intro orbit
def shot_A():
    sc = setup(dict(POSE)); cam, tgt = cam_rig("camA", 32)
    tgt.location = (0, 0, 1.22)
    for f, ang in ((1, -122), (125, -74)):
        a = math.radians(ang); r = 5.0
        key(cam, "location", f, (r * math.cos(a) * 0.8, r * math.sin(a), 1.75))
    render(sc, "A", 1, 125)

# ---------------------------------------------------------------- B: loading + two-hand start
def shot_B():
    pose = dict(POSE, drawer=1.0, mdi=0.0, wg=0.0, clipFlat=0.0, weldFlat=0.0, cupsOpenMax=0.0, clipped=0)
    sc = setup(pose); cam, tgt = cam_rig("camB", 45)
    root = obj("DRAWER_ROOT")
    key(root, "location", 1, root.location[1], index=1)
    key(root, "location", 70, root.location[1], index=1)
    key(root, "location", 115, 0.0, index=1)
    # camera: on the open drawer, then down to the two green buttons
    key(cam, "location", 1, (1.6, -1.55, T + 0.95)); key(tgt, "location", 1, (0.02, -0.36, T + 0.5))
    key(cam, "location", 70, (1.45, -1.7, T + 0.85)); key(tgt, "location", 70, (0.02, -0.34, T + 0.45))
    key(cam, "location", 125, (0.9, -1.75, T + 0.45)); key(tgt, "location", 125, (0.0, -0.17, T + 0.12))
    key(cam, "location", 175, (0.75, -1.55, T + 0.38)); key(tgt, "location", 175, (0.0, -0.17, T + 0.1))
    # buttons light up (two-hand safety start)
    m = bpy.data.materials["btn_green"]; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (0.15, 1.0, 0.3, 1)
    es = b.inputs["Emission Strength"]
    for f, v in ((1, 0.0), (125, 0.0), (135, 6.0), (150, 1.5), (160, 6.0), (175, 6.0)):
        es.default_value = v; es.keyframe_insert("default_value", frame=f)
    render(sc, "B", 1, 175)

# ---------------------------------------------------------------- C: process (cut-away)
def shot_C():
    pose = dict(POSE, cups=1.0, cupsOpen=1.0, cupsOpenMax=1.0, mdi=1.0, wg=1.0, clipFlat=0.0, weldFlat=0.0,
                clipped=0, clip=0.0, weld=0.0, rodA=0.0, rodB=0.0, drawer=0.0)
    sc = setup(pose)
    # open the view: front glass + front profiles + tablet out of the way
    front_frame = [o.name for o in bpy.data.objects if o.name.startswith(("rail_front_", "post_-1_-1", "post_1_-1"))]
    hmi = ["tablet_body", "tablet_screen", "arm", "arm_joint1", "arm_joint2", "arm_mount"]
    g["hide"](g["FRONT_PARTS"] + front_frame + hmi + ["panel_right", "pneu_A_inside", "pneu_B_inside"], True)
    cam, tgt = cam_rig("camC", 50)
    key(cam, "location", 1, (1.75, -1.65, T + 0.82)); key(tgt, "location", 1, (0.0, -0.02, T + 0.56))
    key(cam, "location", 275, (1.5, -1.45, T + 0.78)); key(tgt, "location", 275, (0.0, -0.02, T + 0.58))
    # vacuum cups move in and grip the film (0-25)
    for s_ in (-1, 1):
        c = obj(f"cup_head_{s_}"); x = c.location[0]
        key(c, "location", 1, x + s_ * mm(60), index=0); key(c, "location", 25, x, index=0)
    # fill tubes: group the carriage parts so the whole tube assembly travels
    for k_, stroke, down0, down1, up1 in (("A", P["strokeA"], 25, 55, 125), ("B", P["strokeB"], 160, 180, 235)):
        car = obj(f"filler_{k_}_carriage")
        for part in ("block", "armX", "armY", "tube", "clamp", "valve", "elbow"):
            o = obj(f"filler_{k_}_{part}")
            if o: reparent_keep(o, car)
        z = car.location[2]
        key(car, "location", 1, z, index=2); key(car, "location", down0, z, index=2)
        key(car, "location", down1, z - mm(stroke), index=2)
        key(car, "location", up1 - 20, z - mm(stroke), index=2); key(car, "location", up1, z, index=2)
    # liquids rise from the pouch bottom (pressure fill, no splashing)
    for name, zb, f0, f1 in (("liquid_mdi", P["pouchZ0"], 55, 100), ("liquid_wg", P["clipZ"] + 8, 180, 212)):
        o = obj(name)
        if not o: continue
        bpy.context.view_layer.update()
        bpy.context.scene.cursor.location = (0, 0, T + mm(zb))
        for x in bpy.context.selected_objects: x.select_set(False)
        o.select_set(True); bpy.context.view_layer.objects.active = o
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
        key(o, "scale", 1, 0.001, index=2); key(o, "scale", f0, 0.001, index=2); key(o, "scale", f1, 1.0, index=2)
    # clipper closes (smoothers flatten the film), the clip stays on the pouch
    for s_, side in ((-1, "L"), (1, "R")):
        h = obj(f"clipper_head_{side}"); x = h.location[0]
        key(h, "location", 1, x, index=0); key(h, "location", 128, x, index=0)
        key(h, "location", 145, x - s_ * mm(52), index=0); key(h, "location", 152, x - s_ * mm(52), index=0)
        key(h, "location", 162, x, index=0)
    for n_, s_ in (("clip_C_back", -1), ("clip_C_lip-1", -1), ("clip_C_lip1", -1), ("clip_8_-1", 1), ("clip_8_1", 1)):
        o = obj(n_)
        if not o: continue
        x = o.location[0]; key(o, "location", 128, x, index=0); key(o, "location", 145, x - s_ * mm(52), index=0)
    # sealer closes and opens
    for s_, side in ((-1, "L"), (1, "R")):
        h = obj(f"welder_head_{side}"); x = h.location[0]
        key(h, "location", 1, x, index=0); key(h, "location", 238, x, index=0)
        key(h, "location", 250, x - s_ * mm(52), index=0); key(h, "location", 262, x - s_ * mm(52), index=0)
        key(h, "location", 272, x, index=0)
    render(sc, "C", 1, 275)

# ---------------------------------------------------------------- D: safety (closed housing)
def shot_D():
    sc = setup(dict(POSE)); cam, tgt = cam_rig("camD", 32)
    key(cam, "location", 1, (-2.9, -3.9, 1.85)); key(tgt, "location", 1, (0.0, 0.0, 1.22))
    key(cam, "location", 125, (-2.2, -3.1, 1.75)); key(tgt, "location", 125, (0.0, -0.05, 1.22))
    render(sc, "D", 1, 125)

# ---------------------------------------------------------------- E: fleet of four on one Manyika 1 footprint
def shot_E():
    sc = setup(dict(POSE))
    # every machine part (incl. the stand) goes into one collection, instanced four times
    allm = bpy.data.collections.new("MIA_ALL")
    for cn in g["MACHINE_COLS"] + ("Table",):
        c = bpy.data.collections.get(cn)
        if not c: continue
        for o in list(c.objects): allm.objects.link(o)
        for parent in (bpy.context.scene.collection,):
            if c.name in parent.children: parent.children.unlink(c)
    xs = (-1.125, -0.375, 0.375, 1.125)
    for i, x in enumerate(xs):
        e = bpy.data.objects.new(f"MIA_inst_{i}", None); e.instance_type = 'COLLECTION'; e.instance_collection = allm
        e.location = (x, 0, 0); bpy.context.scene.collection.objects.link(e)
    # Manyika 1 footprint: glowing outline on the floor around all four
    em = bpy.data.materials.new("footprint"); em.use_nodes = True
    bsdf = em.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1.0, 0.55, 0.1, 1)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.5, 0.08, 1); bsdf.inputs["Emission Strength"].default_value = 6
    W2, D2, t = 1.55, 0.5, 0.025
    for (sx, sy, lx, ly) in ((0, -D2, 2 * W2, t), (0, D2, 2 * W2, t), (-W2, 0, t, 2 * D2), (W2, 0, t, 2 * D2)):
        for i in range(12):                                      # dashed
            frac = (i + 0.25) / 12; seg = 0.5 / 12
            if lx > ly: loc = (sx - W2 + (frac + seg / 2) * 2 * W2, sy, 0.004); size = (seg * 2 * W2, t, 0.004)
            else: loc = (sx, sy - D2 + (frac + seg / 2) * 2 * D2, 0.004); size = (t, seg * 2 * D2, 0.004)
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc); b = bpy.context.active_object
            b.scale = size; b.data.materials.append(em)
    # one operator walks along the row and starts each machine
    om = bpy.data.materials.new("operator"); om.use_nodes = True
    ob = om.node_tree.nodes["Principled BSDF"]; ob.inputs["Base Color"].default_value = (0.02, 0.035, 0.08, 1); ob.inputs["Roughness"].default_value = 0.7
    hm = bpy.data.materials.new("skin"); hm.use_nodes = True
    hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.55, 0.42, 1)
    op = bpy.data.objects.new("OPERATOR", None); bpy.context.scene.collection.objects.link(op)
    parts = []
    # stylised operator, ~1.75 m: torso, legs, arms, head (dark navy workwear)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.6, location=(0, 0, 1.2)); parts.append((bpy.context.active_object, om))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, 0, 1.47)); bpy.context.active_object.scale.z = 0.45; parts.append((bpy.context.active_object, om))
    for lx in (-0.075, 0.075):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.065, depth=0.9, location=(lx, 0, 0.45)); parts.append((bpy.context.active_object, om))
    for ax in (-0.2, 0.2):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.62, location=(ax, 0, 1.17)); parts.append((bpy.context.active_object, om))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, 1.66)); parts.append((bpy.context.active_object, hm))
    for o, m in parts:
        o.data.materials.append(m); bpy.ops.object.shade_smooth(); o.parent = op
    y = -0.72
    f = 1
    key(op, "location", f, (-1.9, y, 0))
    for i, x in enumerate(xs):                                   # walk -> stop at each machine (press start)
        f += 28; key(op, "location", f, (x, y, 0)); f += 14; key(op, "location", f, (x, y, 0))
    key(op, "location", 200, (xs[-1] + 0.6, y, 0))
    # each machine's stack light turns green when the operator has started it: shown with a small green lamp
    lm = bpy.data.materials.new("start_glow"); lm.use_nodes = True
    lb = lm.node_tree.nodes["Principled BSDF"]; lb.inputs["Base Color"].default_value = (0.1, 1, 0.25, 1)
    lb.inputs["Emission Color"].default_value = (0.1, 1, 0.25, 1)
    fs = 1 + 28
    for i, x in enumerate(xs):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(x - 0.1, -P["D"] * S / 2 - 0.02, T + 0.09))
        s_ = bpy.context.active_object; s_.data.materials.append(lm.copy())
        es = s_.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        es.default_value = 0; es.keyframe_insert("default_value", frame=1); es.keyframe_insert("default_value", frame=fs + i * 42)
        es.default_value = 12; es.keyframe_insert("default_value", frame=fs + i * 42 + 6)
    cam, tgt = cam_rig("camE", 32)
    key(cam, "location", 1, (0.4, -5.6, 3.2)); key(tgt, "location", 1, (0.0, 0.0, 0.9))
    key(cam, "location", 200, (-0.3, -5.2, 2.95)); key(tgt, "location", 200, (0.0, 0.0, 0.95))
    render(sc, "E", 1, 200)

for s in WANT:
    {"A": shot_A, "B": shot_B, "C": shot_C, "D": shot_D, "E": shot_E}[s]()
print("ALL SHOTS DONE", flush=True)
