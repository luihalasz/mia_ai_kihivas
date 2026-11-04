"""
MIA promo video – 3D shots rendered from the parametric v2 model.

    blender -b --python blender/video/shots.py -- <frames_dir> [shot ...] [--test]

Shots (25 fps, 1280x720):
  A intro    175 f  slow orbit around the closed machine
  B load     300 f  drawer out with an empty pouch (film flashes) -> slides in -> two green start buttons
                    (flash, then light up)
  C process  450 f  cut-away: vacuum cups grip, ISO tube down + pressure fill, smoothing jaws + clipper,
                    water glass fill, sealer
  D safety   175 f  closed housing (flash), the two pouch sizes (flash)
  E fleet    300 f  four machines on the footprint of one Manyika 1; all drawers open, one operator walks
                    along, closes each drawer left to right and starts the machine

Highlights: the object being talked about gets a yellow outline that flashes twice. It is made in the
compositor from a second, cheap "mask" view layer that renders only the highlight objects as flat white
(material override driven by their pass index, which is keyed on only while that object's flash runs).

--test renders a few chosen frames per shot into <frames_dir>/_test.
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

S = g["S"]; P = g["P"]; POSE = g["POSE"]; T = g["TABLE_H"] * S
FPS = 25
RES = (1280, 720)
YELLOW = (1.0, 0.82, 0.05, 1.0)

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
    sc.cycles.samples = 6 if TEST else 14; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception: pass
    sc.cycles.max_bounces = 8; sc.cycles.transmission_bounces = 8; sc.cycles.transparent_max_bounces = 10
    sc.render.use_persistent_data = True
    sc.render.use_overwrite = False; sc.render.use_placeholder = True   # a re-run resumes where it stopped
    sc.render.resolution_x, sc.render.resolution_y = RES; sc.render.resolution_percentage = 100
    sc.render.fps = FPS
    vt = [i.identifier for i in sc.view_settings.bl_rna.properties["view_transform"].enum_items]
    sc.view_settings.view_transform = "AgX" if "AgX" in vt else "Filmic"
    if sc.view_settings.view_transform == "AgX": sc.view_settings.look = "AgX - Medium High Contrast"
    sc.render.image_settings.file_format = "PNG"
    # no highlight unless a shot asks for one
    ml = sc.view_layers.get("mask")
    if ml: ml.use = False
    sc.render.use_compositing = False
    return sc

def cam_rig(name, lens):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    cam = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(cam)
    tgt = bpy.data.objects.new(name + "_tgt", None); bpy.context.scene.collection.objects.link(tgt)
    c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
    bpy.context.scene.camera = cam
    return cam, tgt

# ---------------------------------------------------------------- yellow flashing outline
FLASH_LEN = 34

def highlight(sc, flashes, size=7):
    """flashes: [(start_frame, [object names])] – each set gets a yellow outline that pulses twice."""
    # every highlight object also goes into the HL collection (the only one the mask layer sees)
    hl = bpy.data.collections.get("HL") or bpy.data.collections.new("HL")
    if hl.name not in sc.collection.children: sc.collection.children.link(hl)
    for o in list(hl.objects): hl.objects.unlink(o)
    allnames = {n for _, ns in flashes for n in ns}
    for n in allnames:
        o = obj(n)
        if o is None: print("highlight: missing", n); continue
        hl.objects.link(o); o.pass_index = 0; o.keyframe_insert("pass_index", frame=1)
    for f0, ns in flashes:                      # pass index 1 only while its own flash runs
        for n in ns:
            o = obj(n)
            if o is None: continue
            for f, v in ((f0 - 3, 0), (f0 - 2, 1), (f0 + FLASH_LEN, 1), (f0 + FLASH_LEN + 1, 0)):
                o.pass_index = v; o.keyframe_insert("pass_index", frame=f)
            try:
                for fc in o.animation_data.action.fcurves:
                    if fc.data_path == "pass_index":
                        for kp in fc.keyframe_points: kp.interpolation = 'CONSTANT'
            except Exception: pass
    # mask view layer: highlight objects only, flat white = pass index
    ml = sc.view_layers.get("mask") or sc.view_layers.new("mask")
    ml.use = True
    for lc in ml.layer_collection.children:
        lc.exclude = lc.collection.name != "HL"
    ov = bpy.data.materials.get("mask_override")
    if ov is None:
        ov = bpy.data.materials.new("mask_override"); ov.use_nodes = True
        nt = ov.node_tree; nt.nodes.clear()
        # pass index 1 -> flat white, 0 -> fully transparent (an idle highlight object must not hide an active one)
        oi = nt.nodes.new("ShaderNodeObjectInfo"); em = nt.nodes.new("ShaderNodeEmission")
        tr = nt.nodes.new("ShaderNodeBsdfTransparent"); mx = nt.nodes.new("ShaderNodeMixShader")
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        em.inputs["Color"].default_value = (1, 1, 1, 1); em.inputs["Strength"].default_value = 1.0
        nt.links.new(oi.outputs["Object Index"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], out.inputs["Surface"])
    ml.material_override = ov
    ml.use_sky = False
    try: ml.samples = 4
    except Exception: pass
    try: ml.cycles.use_denoising = False
    except Exception: pass
    main = [v for v in sc.view_layers if v.name != "mask"][0]
    # compositor: ring = dilate(mask) - mask, times the pulse, yellow over the beauty pass
    ng = bpy.data.node_groups.new("outline_comp", "CompositorNodeTree")
    try: ng.interface.new_socket("Image", in_out='OUTPUT', socket_type='NodeSocketColor')
    except Exception as e: print("iface", e)
    N = ng.nodes; L = ng.links
    rm = N.new("CompositorNodeRLayers"); rm.scene = sc; rm.layer = main.name
    rk = N.new("CompositorNodeRLayers"); rk.scene = sc; rk.layer = "mask"
    bw = N.new("CompositorNodeRGBToBW"); L.new(rk.outputs["Image"], bw.inputs[0])
    dl = N.new("CompositorNodeDilateErode"); L.new(bw.outputs[0], dl.inputs["Mask"])
    dl.inputs["Size"].default_value = size
    try: dl.inputs["Type"].default_value = "Distance"
    except Exception as e: print("dilate type", e)
    sub = N.new("ShaderNodeMath"); sub.operation = 'SUBTRACT'; sub.use_clamp = True
    L.new(dl.outputs[0], sub.inputs[0]); L.new(bw.outputs[0], sub.inputs[1])
    pulse = N.new("ShaderNodeMath"); pulse.operation = 'MULTIPLY'; pulse.use_clamp = True; pulse.name = "pulse"
    L.new(sub.outputs[0], pulse.inputs[0])
    col = N.new("CompositorNodeRGB"); col.outputs[0].default_value = YELLOW
    ao = N.new("CompositorNodeAlphaOver")
    L.new(rm.outputs["Image"], ao.inputs["Background"]); L.new(col.outputs[0], ao.inputs["Foreground"])
    L.new(pulse.outputs[0], ao.inputs["Factor"])
    go = N.new("NodeGroupOutput"); L.new(ao.outputs[0], go.inputs[0])
    sc.compositing_node_group = ng; sc.render.use_compositing = True
    # two pulses per flash
    pv = pulse.inputs[1]
    pv.default_value = 0.0; pv.keyframe_insert("default_value", frame=1)
    for f0, _ in flashes:
        for f, v in ((f0, 0), (f0 + 4, 1), (f0 + 11, 1), (f0 + 15, 0), (f0 + 19, 0), (f0 + 23, 1), (f0 + 30, 1), (f0 + 34, 0)):
            pv.default_value = v; pv.keyframe_insert("default_value", frame=f)

def render(sc, shot, f0, f1, tests=()):
    out = os.path.join(FRAMES, shot); os.makedirs(out, exist_ok=True)
    ease_all()
    if TEST:
        for f in (tests or [(f0 + f1) // 2]):
            sc.frame_set(f)
            hl = bpy.data.collections.get("HL")
            if hl and sc.render.use_compositing:
                pl = sc.compositing_node_group.nodes.get("pulse")
                print("DBG", shot, f, "pulse", round(pl.inputs[1].default_value, 2) if pl else None,
                      [(o.name, o.pass_index, o.hide_render) for o in hl.objects if o.pass_index], flush=True)
            sc.render.filepath = os.path.join(FRAMES, "_test", f"{shot}_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
    else:
        sc.frame_start, sc.frame_end = f0, f1
        sc.render.filepath = os.path.join(out, "")
        bpy.ops.render.render(animation=True)
    print("SHOT DONE", shot, flush=True)

def mm(v): return v * S

FILM = ["pe_pouch", "alu_pouch"]
BUTTONS = ["btn_-185", "btn_185", "btn_ring_-185", "btn_ring_185"]
CUPS = ["cup_-1", "cup_1", "cup_neck_-1", "cup_neck_1", "cup_head_-1", "cup_head_1"]
FILL_A = ["filler_A_tube", "filler_A_valve", "filler_A_elbow", "liquid_mdi"]
SMOOTH = ["smoother_clip_-1", "smoother_clip_1", "smoother_weld_-1", "smoother_weld_1"]
CLIP = ["clip_C_back", "clip_C_lip-1", "clip_C_lip1", "clip_8_-1", "clip_8_1"]
WELD = ["weld_jaw_-1", "weld_jaw_1", "weld_heater", "weld_counter_pad"]
HOUSING = ["front_l", "front_r", "front_top", "front_bot", "panel_left", "panel_right", "top_cap", "plinth", "drawer_front"]

# ---------------------------------------------------------------- A: intro orbit
def shot_A():
    sc = setup(dict(POSE)); cam, tgt = cam_rig("camA", 32)
    tgt.location = (0, 0, 1.22)
    for f, ang in ((1, -122), (175, -72)):
        a = math.radians(ang); r = 5.0
        key(cam, "location", f, (r * math.cos(a) * 0.8, r * math.sin(a), 1.75))
    render(sc, "A", 1, 175, tests=[90])

# ---------------------------------------------------------------- B: loading + two-hand start
def shot_B():
    pose = dict(POSE, drawer=1.0, mdi=0.0, wg=0.0, clipFlat=0.0, weldFlat=0.0, cupsOpenMax=0.0, clipped=0)
    sc = setup(pose); cam, tgt = cam_rig("camB", 45)
    root = obj("DRAWER_ROOT")
    key(root, "location", 1, root.location[1], index=1)
    key(root, "location", 140, root.location[1], index=1)
    key(root, "location", 185, 0.0, index=1)
    # camera: on the open drawer, then down to the two green buttons
    key(cam, "location", 1, (1.6, -1.55, T + 0.95)); key(tgt, "location", 1, (0.02, -0.36, T + 0.5))
    key(cam, "location", 140, (1.45, -1.7, T + 0.85)); key(tgt, "location", 140, (0.02, -0.34, T + 0.45))
    key(cam, "location", 205, (0.9, -1.75, T + 0.45)); key(tgt, "location", 205, (0.0, -0.17, T + 0.12))
    key(cam, "location", 300, (0.72, -1.5, T + 0.37)); key(tgt, "location", 300, (0.0, -0.17, T + 0.1))
    # buttons light up (two-hand safety start) after their flash
    m = bpy.data.materials["btn_green"]; b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Emission Color"].default_value = (0.15, 1.0, 0.3, 1)
    es = b.inputs["Emission Strength"]
    for f, v in ((1, 0.0), (250, 0.0), (258, 6.0), (268, 1.5), (276, 6.0), (300, 6.0)):
        es.default_value = v; es.keyframe_insert("default_value", frame=f)
    highlight(sc, [(40, FILM), (215, BUTTONS)])
    render(sc, "B", 1, 300, tests=[44, 226, 280])

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
    key(cam, "location", 450, (1.45, -1.4, T + 0.78)); key(tgt, "location", 450, (0.0, -0.02, T + 0.58))
    # vacuum cups move in and grip the film
    for s_ in (-1, 1):
        c = obj(f"cup_head_{s_}"); x = c.location[0]
        key(c, "location", 1, x + s_ * mm(60), index=0); key(c, "location", 15, x + s_ * mm(60), index=0)
        key(c, "location", 50, x, index=0)
    # fill tubes: group the carriage parts so the whole tube assembly travels
    for k_, stroke, down0, down1, up0, up1 in (("A", P["strokeA"], 100, 150, 245, 268), ("B", P["strokeB"], 335, 355, 398, 412)):
        car = obj(f"filler_{k_}_carriage")
        for part in ("block", "armX", "armY", "tube", "clamp", "valve", "elbow"):
            o = obj(f"filler_{k_}_{part}")
            if o: reparent_keep(o, car)
        z = car.location[2]
        key(car, "location", 1, z, index=2); key(car, "location", down0, z, index=2)
        key(car, "location", down1, z - mm(stroke), index=2)
        key(car, "location", up0, z - mm(stroke), index=2); key(car, "location", up1, z, index=2)
    # liquids rise from the pouch bottom (pressure fill, no splashing)
    for name, zb, f0, f1 in (("liquid_mdi", P["pouchZ0"], 152, 235), ("liquid_wg", P["clipZ"] + 8, 357, 395)):
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
        key(h, "location", 1, x, index=0); key(h, "location", 290, x, index=0)
        key(h, "location", 312, x - s_ * mm(52), index=0); key(h, "location", 322, x - s_ * mm(52), index=0)
        key(h, "location", 336, x, index=0)
    for n_, s_ in (("clip_C_back", -1), ("clip_C_lip-1", -1), ("clip_C_lip1", -1), ("clip_8_-1", 1), ("clip_8_1", 1)):
        o = obj(n_)
        if not o: continue
        x = o.location[0]; key(o, "location", 290, x, index=0); key(o, "location", 312, x - s_ * mm(52), index=0)
    # sealer closes and opens
    for s_, side in ((-1, "L"), (1, "R")):
        h = obj(f"welder_head_{side}"); x = h.location[0]
        key(h, "location", 1, x, index=0); key(h, "location", 412, x, index=0)
        key(h, "location", 425, x - s_ * mm(52), index=0); key(h, "location", 438, x - s_ * mm(52), index=0)
        key(h, "location", 449, x, index=0)
    highlight(sc, [(18, CUPS), (160, FILL_A), (250, SMOOTH), (320, CLIP), (400, WELD)], size=6)
    render(sc, "C", 1, 450, tests=[24, 168, 256, 326, 418])

# ---------------------------------------------------------------- D: safety (closed housing) + two sizes
def shot_D():
    sc = setup(dict(POSE)); cam, tgt = cam_rig("camD", 32)
    key(cam, "location", 1, (-2.9, -3.9, 1.85)); key(tgt, "location", 1, (0.0, 0.0, 1.22))
    key(cam, "location", 175, (-2.1, -3.0, 1.72)); key(tgt, "location", 175, (0.0, -0.05, 1.2))
    highlight(sc, [(20, HOUSING), (105, FILM)])
    render(sc, "D", 1, 175, tests=[26, 112])

# ---------------------------------------------------------------- E: fleet of four on one Manyika 1 footprint
def shot_E():
    pose = dict(POSE, drawer=1.0, mdi=0.0, wg=0.0, clipFlat=0.0, weldFlat=0.0, cupsOpenMax=0.0, clipped=0)
    sc = setup(pose)
    xs = (-1.125, -0.375, 0.375, 1.125)
    # four real copies (linked mesh data) so that every drawer can move on its own
    src = []
    for cn in g["MACHINE_COLS"] + ("Table",):
        c = bpy.data.collections.get(cn)
        if c: src += [o for o in c.objects if not o.hide_render]
    srcset = set(src)
    roots = [None] * 4
    for i in (1, 2, 3, 0):                      # copies first: they must start from the unshifted original
        x = xs[i]
        if i == 0:
            m = {o: o for o in src}
        else:
            m = {}
            for o in src:
                n = o.copy(); m[o] = n
                for c in o.users_collection: c.objects.link(n)
        for o, n in m.items():
            if o.parent in srcset:
                if i: n.parent = m[o.parent]
            else:
                n.location.x += x
        roots[i] = m[obj("DRAWER_ROOT")]
    # Manyika 1 footprint: glowing dashed outline on the floor around all four
    em = bpy.data.materials.new("footprint"); em.use_nodes = True
    bsdf = em.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (1.0, 0.55, 0.1, 1)
    bsdf.inputs["Emission Color"].default_value = (1.0, 0.5, 0.08, 1); bsdf.inputs["Emission Strength"].default_value = 6
    W2, D2, t = 1.55, 0.62, 0.025
    for (sx, sy, lx, ly) in ((0, -D2, 2 * W2, t), (0, D2, 2 * W2, t), (-W2, 0, t, 2 * D2), (W2, 0, t, 2 * D2)):
        for i in range(12):
            frac = (i + 0.25) / 12; seg = 0.5 / 12
            if lx > ly: loc = (sx - W2 + (frac + seg / 2) * 2 * W2, sy, 0.004); size = (seg * 2 * W2, t, 0.004)
            else: loc = (sx, sy - D2 + (frac + seg / 2) * 2 * D2, 0.004); size = (t, seg * 2 * D2, 0.004)
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc); b = bpy.context.active_object
            b.scale = size; b.data.materials.append(em)
    # one operator walks along the row: stops, closes the drawer, starts the machine
    om = bpy.data.materials.new("operator"); om.use_nodes = True
    ob = om.node_tree.nodes["Principled BSDF"]; ob.inputs["Base Color"].default_value = (0.02, 0.035, 0.08, 1); ob.inputs["Roughness"].default_value = 0.7
    hm = bpy.data.materials.new("skin"); hm.use_nodes = True
    hm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.75, 0.55, 0.42, 1)
    op = bpy.data.objects.new("OPERATOR", None); bpy.context.scene.collection.objects.link(op)
    parts = []
    bpy.ops.mesh.primitive_cylinder_add(radius=0.15, depth=0.6, location=(0, 0, 1.2)); parts.append((bpy.context.active_object, om))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.15, location=(0, 0, 1.47)); bpy.context.active_object.scale.z = 0.45; parts.append((bpy.context.active_object, om))
    for lx in (-0.075, 0.075):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.065, depth=0.9, location=(lx, 0, 0.45)); parts.append((bpy.context.active_object, om))
    for ax in (-0.2, 0.2):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.045, depth=0.62, location=(ax, 0, 1.17)); parts.append((bpy.context.active_object, om))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.1, location=(0, 0, 1.66)); parts.append((bpy.context.active_object, hm))
    for o, m_ in parts:
        o.data.materials.append(m_); bpy.ops.object.shade_smooth(); o.parent = op
    y = -0.8
    walk0, walk, stop = 36, 30, 35
    key(op, "location", 1, (-1.95, y, 0))
    f = 1; arrive = []
    for i, x in enumerate(xs):
        f += walk0 if i == 0 else walk
        key(op, "location", f, (x, y, 0)); arrive.append(f)
        f += stop; key(op, "location", f, (x, y, 0))
    key(op, "location", 300, (xs[-1] + 0.75, y, 0))
    # drawers: all open, each closes when the operator reaches it (left to right)
    for r, fa in zip(roots, arrive):
        y0 = r.location[1]
        key(r, "location", 1, y0, index=1); key(r, "location", fa + 3, y0, index=1); key(r, "location", fa + 18, 0.0, index=1)
    # start: a green lamp at each machine lights up after its drawer is closed
    lm = bpy.data.materials.new("start_glow"); lm.use_nodes = True
    lb = lm.node_tree.nodes["Principled BSDF"]; lb.inputs["Base Color"].default_value = (0.1, 1, 0.25, 1)
    lb.inputs["Emission Color"].default_value = (0.1, 1, 0.25, 1)
    for x, fa in zip(xs, arrive):
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.035, location=(x - 0.1, -P["D"] * S / 2 - 0.02, T + 0.09))
        s_ = bpy.context.active_object; s_.data.materials.append(lm.copy())
        es = s_.data.materials[0].node_tree.nodes["Principled BSDF"].inputs["Emission Strength"]
        es.default_value = 0; es.keyframe_insert("default_value", frame=1); es.keyframe_insert("default_value", frame=fa + 22)
        es.default_value = 12; es.keyframe_insert("default_value", frame=fa + 28)
    cam, tgt = cam_rig("camE", 32)
    key(cam, "location", 1, (0.45, -5.5, 3.1)); key(tgt, "location", 1, (0.0, 0.0, 0.9))
    key(cam, "location", 300, (-0.35, -5.0, 2.85)); key(tgt, "location", 300, (0.0, 0.0, 0.95))
    render(sc, "E", 1, 300, tests=[20, 60, 200])

for s in WANT:
    {"A": shot_A, "B": shot_B, "C": shot_C, "D": shot_D, "E": shot_E}[s]()
print("ALL SHOTS DONE", flush=True)
