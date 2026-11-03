"""
MIA (Manyika) – burst pouch filler / clipper / sealer
Parametric Blender model, built from the concept spec (all dimensions in mm).

Coordinate system (Blender metres, model built in mm and scaled /1000):
  X = width  (515)  – jaws close along X, pouch faces are ±X
  Y = depth  (340)  – front = -Y, drawer pulls out toward -Y
  Z = height (1140) – floor at Z=0
Pouch plane = YZ plane (parallel to the drawer travel direction).

Usage (bpy module or Blender):
  python mia_model.py                -> builds + renders previews + exports
  blender -b --python mia_model.py   -> same
"""
import bpy, math, os, sys
from mathutils import Vector

# ----------------------------------------------------------------------------
# PARAMETERS (mm)
# ----------------------------------------------------------------------------
P = dict(
    W=515, D=340, H=1140,          # housing
    panel=6,                       # sheet thickness
    bevel=10,                      # housing edge radius
    # drawer opening in the front panel
    drawer_w=190, drawer_z0=140, drawer_z1=830,
    # pouch
    alu_w=220, alu_h=285,          # aluminium pouch (Y width, Z height)
    pe_w=180, pe_h=550,            # PE pouch
    pouch_z0=200,                  # bottom of both pouches (fixed in drawer)
    clip_from_alu_bottom=255,      # clip line
    weld_above_clip=192,           # weld line
    clip_len=220, clip_sec=10,
    rod_od=12, rod_id=8,
    stroke_A=350, stroke_B=150,     # guided fill cylinders (ISO / water glass)
    bay_top=183,                   # mid deck height (utility bay below)
    cup_d=40, opening_d=140,
)
P["clip_z"] = P["pouch_z0"] + P["clip_from_alu_bottom"]      # 555
P["weld_z"] = P["clip_z"] + P["weld_above_clip"]              # 747
P["pe_top"] = P["pouch_z0"] + P["pe_h"]                       # 850
P["alu_top"] = P["pouch_z0"] + P["alu_h"]                     # 585

# machine state (changed later by the animation)
STATE = dict(
    drawer_open=0.0,     # 0 closed .. 1 fully pulled out (320 mm)
    clip_close=0.0,      # 0 open .. 1 closed on the pouch
    weld_close=0.0,
    cups_open=0.0,       # 0 cups on pouch (flat) .. 1 pulled apart
    rodA=(0.0, 0.0),     # (forward 0..1 over pouch, down 0..1)
    rodB=(0.0, 0.0),
    mdi_level=1.0,       # 0..1 fill of isocyanate (below clip line)
    wg_level=1.0,        # 0..1 fill of water glass (between clip & weld)
    cutaway=False,       # hide front + right panels
)

OUT = os.environ.get("MIA_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
os.makedirs(OUT, exist_ok=True)

S = 0.001  # mm -> m

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    sc.unit_settings.length_unit = 'MILLIMETERS'
    return sc

COLS = {}
def col(name):
    if name not in COLS:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
        COLS[name] = c
    return COLS[name]

def link(obj, cname):
    for c in obj.users_collection:
        c.objects.unlink(obj)
    col(cname).objects.link(obj)

MATS = {}
def mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, transmission=0.0,
        emission=None, emission_strength=0.0, alpha=1.0, coat=0.0, ior=1.45):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*base, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["IOR"].default_value = ior
    if "Transmission Weight" in bsdf.inputs:
        bsdf.inputs["Transmission Weight"].default_value = transmission
    if "Coat Weight" in bsdf.inputs:
        bsdf.inputs["Coat Weight"].default_value = coat
    bsdf.inputs["Alpha"].default_value = alpha
    if emission:
        bsdf.inputs["Emission Color"].default_value = (*emission, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength
    if transmission > 0 or alpha < 1:
        m.blend_method = 'BLEND' if hasattr(m, "blend_method") else None
    MATS[name] = m
    return m

def materials():
    mat("paint_blue", (0.055, 0.075, 0.13), metallic=0.35, rough=0.42, coat=0.4)
    mat("smoked_glass", (0.16, 0.24, 0.45), metallic=0.0, rough=0.06, transmission=0.9, coat=0.5, ior=1.49)
    mat("led_strip", (1, 1, 1), rough=0.3, emission=(0.75, 0.85, 1.0), emission_strength=6)
    mat("black_matte", (0.012, 0.012, 0.013), rough=0.55)
    mat("black_gloss", (0.01, 0.01, 0.01), rough=0.15, coat=0.6)
    mat("steel", (0.62, 0.62, 0.64), metallic=1.0, rough=0.28)
    mat("alu_brushed", (0.78, 0.78, 0.8), metallic=1.0, rough=0.4)
    mat("alu_foil", (0.86, 0.86, 0.88), metallic=1.0, rough=0.18)
    mat("rubber", (0.02, 0.02, 0.02), rough=0.9)
    mat("tpu_grey", (0.28, 0.29, 0.3), rough=0.75)
    mat("silicone", (0.5, 0.52, 0.55), rough=0.6, alpha=0.9)
    mat("clip_white", (0.9, 0.9, 0.88), rough=0.45)
    mat("pe_clear", (0.95, 0.97, 1.0), rough=0.08, transmission=1.0, ior=1.5)
    mat("mdi_orange", (1.0, 0.42, 0.03), rough=0.1, transmission=0.85, ior=1.4)
    mat("waterglass", (0.85, 0.95, 1.0), rough=0.05, transmission=1.0, ior=1.38)
    mat("copper", (0.95, 0.55, 0.35), metallic=1.0, rough=0.3)
    mat("screen", (0.02, 0.03, 0.06), rough=0.2, emission=(0.1, 0.35, 0.9), emission_strength=1.2)
    mat("screen_bezel", (0.015, 0.015, 0.015), rough=0.3)
    mat("led_green", (0.0, 0.6, 0.1), rough=0.3, emission=(0.1, 1.0, 0.2), emission_strength=4)
    mat("led_amber", (0.6, 0.35, 0.0), rough=0.3, emission=(1.0, 0.6, 0.05), emission_strength=0.4)
    mat("led_red", (0.6, 0.0, 0.0), rough=0.3, emission=(1.0, 0.05, 0.05), emission_strength=0.4)
    mat("btn_green", (0.1, 0.7, 0.2), rough=0.35, coat=0.5)
    mat("btn_red", (0.8, 0.08, 0.05), rough=0.35, coat=0.5)
    mat("floor", (0.05, 0.05, 0.055), rough=0.3, coat=0.3)
    mat("hose", (0.9, 0.9, 0.85), rough=0.3, transmission=0.4, alpha=0.8)
    mat("silver_accent", (0.85, 0.85, 0.87), metallic=1.0, rough=0.2)

def _apply(obj, m, cname, parent=None, bevel=None, local=False):
    if m:
        obj.data.materials.append(MATS[m])
    link(obj, cname)
    if bevel:
        b = obj.modifiers.new("bevel", 'BEVEL')
        b.width = bevel * S
        b.segments = 4
        b.limit_method = 'ANGLE'
    if parent:
        obj.parent = parent
        if not local:
            obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def box(name, size, loc, m, cname, parent=None, bevel=None, rot=(0, 0, 0), local=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[v * S for v in loc],
                                    rotation=[math.radians(r) for r in rot])
    o = bpy.context.active_object
    o.name = name
    o.scale = [v * S for v in size]
    bpy.ops.object.transform_apply(scale=True)
    return _apply(o, m, cname, parent, bevel, local)

def cyl(name, r, h, loc, m, cname, axis='Z', parent=None, verts=48, local=False):
    rot = {'Z': (0, 0, 0), 'X': (0, math.pi / 2, 0), 'Y': (math.pi / 2, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * S, depth=h * S,
                                        location=[v * S for v in loc], rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return _apply(o, m, cname, parent, None, local)

def sphere(name, r, loc, m, cname, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r * S, location=[v * S for v in loc], segments=32, ring_count=16)
    o = bpy.context.active_object
    o.name = name
    bpy.ops.object.shade_smooth()
    return _apply(o, m, cname, parent)

def empty(name, loc, cname, parent=None):
    o = bpy.data.objects.new(name, None)
    o.location = [v * S for v in loc]
    o.empty_display_size = 0.05
    col(cname).objects.link(o)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def tube(name, points, r, m, cname, parent=None):
    """polyline tube through points (mm)"""
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r * S
    cu.bevel_resolution = 6
    cu.resolution_u = 12
    sp = cu.splines.new('NURBS')
    sp.points.add(len(points) - 1)
    for i, p in enumerate(points):
        sp.points[i].co = (p[0] * S, p[1] * S, p[2] * S, 1)
    sp.use_endpoint_u = True
    sp.order_u = 3
    o = bpy.data.objects.new(name, cu)
    o.data.materials.append(MATS[m])
    col(cname).objects.link(o)
    if parent:
        o.parent = parent
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def text(name, txt, size, loc, m, cname, rot=(90, 0, 0), extrude=0.6, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT')
    cu.body = txt
    cu.size = size * S
    cu.extrude = extrude * S
    cu.align_x = align
    o = bpy.data.objects.new(name, cu)
    o.location = [v * S for v in loc]
    o.rotation_euler = [math.radians(r) for r in rot]
    o.data.materials.append(MATS[m])
    col(cname).objects.link(o)
    return o

# ----------------------------------------------------------------------------
# HOUSING
# ----------------------------------------------------------------------------
def build_housing():
    W, D, H, t, b = P["W"], P["D"], P["H"], P["panel"], P["bevel"]
    hw, hd = W / 2, D / 2
    C = "Housing"
    # plinth + top cap (black bands) give the "sporty" two-tone look
    box("plinth", (W, D, 40), (0, 0, 20), "black_matte", C, bevel=b)
    box("top_cap", (W, D, 36), (0, 0, H - 18), "black_gloss", C, bevel=b)
    # side panels (blue), slightly inset
    box("panel_left", (t, D - 4, H - 76), (-hw + t / 2, 0, H / 2), "smoked_glass", C)
    box("panel_right", (t, D - 4, H - 76), (hw - t / 2, 0, H / 2), "smoked_glass", C)
    box("panel_back", (W - 4, t, H - 76), (0, hd - t / 2, H / 2), "smoked_glass", C)
    # front panel = 4 strips around the drawer opening + a black frame recess
    dw, z0, z1 = P["drawer_w"], P["drawer_z0"], P["drawer_z1"]
    y = -hd + t / 2
    zc = (40 + H - 36) / 2
    hh = H - 76
    box("front_l", ((W - dw) / 2 - 2, t, hh), (-(dw / 2 + (W - dw) / 4) + 1, y, zc), "smoked_glass", C)
    box("front_r", ((W - dw) / 2 - 2, t, hh), ((dw / 2 + (W - dw) / 4) - 1, y, zc), "smoked_glass", C)
    box("front_top", (dw + 2, t, (H - 36) - z1), (0, y, (H - 36 + z1) / 2), "smoked_glass", C)
    box("front_bot", (dw + 2, t, z0 - 40), (0, y, (z0 + 40) / 2), "smoked_glass", C)
    # black recess frame around the opening (drawer gap shadow line)
    fw, fz0, fz1 = dw + 18, z0 - 9, z1 + 9
    for nm, sz, lc in (
        ("frame_l", (9, 4, fz1 - fz0), (-(dw / 2 + 4.5), -hd - 1, (fz0 + fz1) / 2)),
        ("frame_r", (9, 4, fz1 - fz0), ((dw / 2 + 4.5), -hd - 1, (fz0 + fz1) / 2)),
        ("frame_t", (fw, 4, 9), (0, -hd - 1, z1 + 4.5)),
        ("frame_b", (fw, 4, 9), (0, -hd - 1, z0 - 4.5)),
    ):
        box(nm, sz, lc, "black_gloss", C)
    # internal frame posts (aluminium extrusion look) + base plate
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"post_{sx}_{sy}", (30, 30, H - 80), (sx * (hw - 25), sy * (hd - 25), H / 2), "alu_brushed", "Frame")
    box("base_plate", (W - 20, D - 20, 6), (0, 0, 43), "black_matte", "Frame")
    for sx in (-1, 1):
        box(f"led_strip_{sx}", (4, 6, H - 300), (sx * (hw - 42), -hd + 24, (H - 300) / 2 + 190), "led_strip", "Frame")
    box("led_strip_top", (W - 120, 6, 4), (0, -hd + 24, H - 60), "led_strip", "Frame")
    box("mid_deck", (W - 20, D - 20, 6), (0, 0, P["bay_top"]), "alu_brushed", "Frame")   # separates utility bay / process bay
    # branding
    text("logo_MIA", "MIA", 30, (hw - 28, -hd - 0.5, H - 36 - 62), "silver_accent", C, rot=(90, 0, 0), extrude=1.0, align='RIGHT')
    text("logo_pol", "POLINVENT", 11, (hw - 28, -hd - 0.5, H - 36 - 84), "silver_accent", C, extrude=0.6, align='RIGHT')
    # ventilation slots on back
    for i in range(8):
        box(f"vent_{i}", (160, 3, 4), (0, hd + 0.5, 90 + i * 14), "black_matte", C)

# ----------------------------------------------------------------------------
# DRAWER (front plate + frame + two rubber U-profiles + pouch clamp)
# ----------------------------------------------------------------------------
def build_drawer():
    W, D, H, t = P["W"], P["D"], P["H"], P["panel"]
    hd = D / 2
    dw, z0, z1 = P["drawer_w"], P["drawer_z0"], P["drawer_z1"]
    C = "Drawer"
    root = empty("DRAWER_ROOT", (0, 0, 0), C)
    # front plate (carries the housing panel piece)
    box("drawer_front", (dw - 3, t + 2, z1 - z0 - 3), (0, -hd + t / 2, (z0 + z1) / 2), "smoked_glass", C, parent=root, bevel=2)
    # recessed pull handle (black slot) + silver lip
    box("handle_slot", (130, 16, 34), (0, -hd + 5, 520), "black_gloss", C, parent=root)
    box("handle_lip", (130, 4, 5), (0, -hd - 1, 539), "silver_accent", C, parent=root)
    # drawer frame: two vertical bars (Y = ±125), bottom bar, front spine
    yb = P["alu_w"] / 2 + 15          # 125
    zb0, zb1 = P["pouch_z0"] - 35, P["pe_top"] + 40     # 265 .. 890
    for s in (-1, 1):
        box(f"bar_{'f' if s<0 else 'b'}", (28, 22, zb1 - zb0), (0, s * yb, (zb0 + zb1) / 2), "alu_brushed", C, parent=root, bevel=2)
    box("bar_bottom", (28, 2 * yb + 22, 22), (0, 0, zb0 + 11), "alu_brushed", C, parent=root, bevel=2)
    box("spine_bottom", (28, (yb - 11) - (hd - t), 22), (0, (-hd + t - yb + 11) / 2, zb0 + 11), "alu_brushed", C, parent=root)
    box("spine_top", (28, (yb - 11) - (hd - t), 22), (0, (-hd + t - yb + 11) / 2, zb1 - 11), "alu_brushed", C, parent=root)
    # linear guide rail + carriage under the drawer (stays in machine; carriage moves)
    # telescopic drawer slides, one each side of the bottom bar (fixed member on the frame, moving member on the drawer)
    for sx in (-1, 1):
        box(f"slide_fixed_{sx}", (12, D - 50, 32), (sx * 24, 0, zb0 - 6), "steel", "Frame")
        box(f"slide_moving_{sx}", (10, D - 60, 24), (sx * 13, 0, zb0 - 6), "alu_brushed", C, parent=root)
        box(f"slide_bracket_{sx}", (8, 60, 40), (sx * 34, -hd + 60, zb0 - 6), "black_matte", "Frame")
        box(f"slide_bracket2_{sx}", (8, 60, 40), (sx * 34, hd - 60, zb0 - 6), "black_matte", "Frame")
    box("slide_crossbar", (90, D - 50, 8), (0, 0, zb0 - 26), "alu_brushed", "Frame")
    # two rubber U-profiles on the inner face of each bar, gaps at clip & weld lines
    gap = 34
    segs = [(P["pouch_z0"] - 5, P["clip_z"] - gap / 2),
            (P["clip_z"] + gap / 2, P["weld_z"] - gap / 2),
            (P["weld_z"] + gap / 2, P["pe_top"] - 10)]
    for s in (-1, 1):
        for i, (a, b) in enumerate(segs):
            yc = s * (yb - 11 - 7)
            # U profile = back + two lips (14 wide in Y, 16 in X, 3 mm walls)
            box(f"U_{s}_{i}_back", (16, 4, b - a), (0, yc + s * 5, (a + b) / 2), "rubber", C, parent=root)
            for sx in (-1, 1):
                box(f"U_{s}_{i}_lip{sx}", (3, 14, b - a), (sx * 6.5, yc, (a + b) / 2), "rubber", C, parent=root)
    # bottom pouch clamp (holds the bottom edge of the pouches)
    box("pouch_clamp", (10, P["alu_w"] + 10, 16), (0, 0, P["pouch_z0"] + 2), "tpu_grey", C, parent=root, bevel=2)
    box("pouch_clamp_lever", (6, 30, 20), (12, -yb + 28, P["pouch_z0"] + 4), "silver_accent", C, parent=root)
    return root

# ----------------------------------------------------------------------------
# POUCHES + LIQUIDS
# ----------------------------------------------------------------------------
def build_pouches(root):
    C = "Pouch"
    z0 = P["pouch_z0"]
    # aluminium pouch (3-side sealed, open top) – slight inflation
    box("alu_pouch", (12, P["alu_w"], P["alu_h"]), (0, 0, z0 + P["alu_h"] / 2), "alu_foil", C, parent=root, bevel=4)
    # alu side seals (5 mm flat bands)
    for s in (-1, 1):
        box(f"alu_seal_{s}", (0.6, 5, P["alu_h"]), (0, s * (P["alu_w"] / 2 - 2.5), z0 + P["alu_h"] / 2), "alu_foil", C, parent=root)
    # PE pouch (clear), sits inside the alu pouch, extends above
    box("pe_pouch", (9, P["pe_w"], P["pe_h"]), (0, 0, z0 + P["pe_h"] / 2), "pe_clear", C, parent=root, bevel=3)
    # silica gel pillows (between alu and PE, bottom corners)
    for s in (-1, 1):
        box(f"silica_{s}", (3, 40, 25), (s * 5.5, 0, z0 + 30), "clip_white", C, parent=root, bevel=1.5)
    # liquids
    mdi_h = (P["clip_z"] - 8) - (z0 + 6)
    o = box("liquid_mdi", (7, P["pe_w"] - 12, mdi_h), (0, 0, z0 + 6 + mdi_h / 2), "mdi_orange", C, parent=root, bevel=2)
    wg_h = (P["weld_z"] - 10) - (P["clip_z"] + 8)
    box("liquid_wg", (7, P["pe_w"] - 12, wg_h), (0, 0, P["clip_z"] + 8 + wg_h / 2), "waterglass", C, parent=root, bevel=2)

# ----------------------------------------------------------------------------
# PROCESS STATIONS (fixed in the machine)
# ----------------------------------------------------------------------------
def pneumatic_pair(name, z, jaw_builder, body_r=20, body_len=110, bracket=True):
    """two opposed pneumatic cylinders along X at height z; returns (left_head, right_head) empties"""
    heads = []
    for s in (-1, 1):
        root = empty(f"{name}_head_{'L' if s<0 else 'R'}", (s * 60, 0, z), "Stations")
        # cylinder body + end caps + rod (body fixed, rod + head move)
        cyl(f"{name}_body_{s}", body_r, body_len, (s * (95 + body_len / 2), 0, z), "alu_brushed", "Stations", axis='X')
        for e in (-1, 1):
            box(f"{name}_cap_{s}_{e}", (10, body_r * 2 + 6, body_r * 2 + 6), (s * (95 + body_len / 2 + e * (body_len / 2 - 5)), 0, z), "black_matte", "Stations", bevel=2)
        cyl(f"{name}_rod_{s}", 8, 60, (s * (60 + 30), 0, z), "steel", "Stations", axis='X', parent=root)
        # fittings
        for e in (-1, 1):
            cyl(f"{name}_fit_{s}_{e}", 4, 12, (s * (95 + body_len / 2 + e * 40), 0, z + body_r + 6), "copper", "Stations")
        if bracket:
            box(f"{name}_bracket_{s}", (12, 90, 90), (s * (95 + body_len + 6), 0, z), "black_matte", "Stations", bevel=2)
            box(f"{name}_brace_{s}", (12, 30, 250), (s * (P["W"] / 2 - 25), 0, z), "alu_brushed", "Frame")
            box(f"{name}_arm_{s}", (P["W"] / 2 - 25 - (95 + body_len + 6), 30, 14), (s * ((P["W"] / 2 - 25 + 95 + body_len + 6) / 2), 0, z + 38), "alu_brushed", "Stations")
        jaw_builder(s, root)
        heads.append(root)
    return heads

def build_clipper():
    z = P["clip_z"]
    L = P["clip_len"]
    def jaw(s, root):
        # TPU holder block with a pocket, clip inside
        box(f"clip_holder_{s}", (22, L + 14, 34), (s * (-2 + 11), 0, 0), "tpu_grey", "Stations", parent=root, bevel=3, local=True)
        if s < 0:
            # C-profile clip: back + two lips (10x10 section)
            box("clip_C_back", (3, L, 10), (-3.5, 0, 0), "clip_white", "Stations", parent=root, local=True)
            for e in (-1, 1):
                box(f"clip_C_lip{e}", (10, L, 2.2), (0, 0, e * 3.9), "clip_white", "Stations", parent=root, local=True)
        else:
            # mating "figure-8" profile = two 4.5 mm rods side by side (lying 8)
            for e in (-1, 1):
                cyl(f"clip_8_{e}", 2.4, L, (-2.0, 0, e * 2.6), "clip_white", "Stations", axis='Y', parent=root, local=True)
        # smoother below (D profile): half cylinder = cylinder clipped by box look-alike
        # D-profile smoother bolted to the underside of the clip holder (moves with the jaw)
        box(f"smoother_clip_bracket_{s}", (14, L + 14, 24), (s * 13, 0, -29), "tpu_grey", "Stations", parent=root, local=True)
        d = cyl(f"smoother_clip_{s}", 8, L, (s * 6, 0, -40), "silicone", "Stations", axis='Y', parent=root, local=True)
        d.scale.x = 0.55
    return pneumatic_pair("clipper", z, jaw)

def build_welder():
    z = P["weld_z"]
    L = P["clip_len"] + 10
    def jaw(s, root):
        box(f"weld_jaw_{s}", (16, L, 28), (s * 8, 0, 0), "alu_brushed", "Stations", parent=root, bevel=2, local=True)
        if s < 0:
            box("weld_heater", (1.2, L - 10, 5), (-0.6, 0, 0), "copper", "Stations", parent=root, local=True)
            box("weld_ptfe", (0.6, L - 10, 12), (-0.3, 0, 0), "clip_white", "Stations", parent=root, local=True)
        else:
            box("weld_counter_pad", (2, L - 10, 12), (1, 0, 0), "rubber", "Stations", parent=root, local=True)
        # D-profile smoother bolted to the underside of the weld jaw (moves with the jaw)
        box(f"smoother_weld_bracket_{s}", (14, L + 14, 24), (s * 10, 0, -26), "tpu_grey", "Stations", parent=root, local=True)
        d = cyl(f"smoother_weld_{s}", 8, L, (s * 6, 0, -40), "silicone", "Stations", axis='Y', parent=root, local=True)
        d.scale.x = 0.55
    return pneumatic_pair("welder", z, jaw)

def build_vacuum_cups():
    """two 40 mm suction cups gripping the two faces at the top of the PE pouch, pulling apart ±X, tilted 1.5° up"""
    z = P["pe_top"] - 22
    heads = []
    for s in (-1, 1):
        root = empty(f"cup_head_{'L' if s<0 else 'R'}", (s * 7, 0, z), "Stations")
        cyl(f"cup_{s}", P["cup_d"] / 2, 8, (s * 4, 0, 0), "rubber", "Stations", axis='X', parent=root, local=True)
        cyl(f"cup_neck_{s}", 6, 20, (s * 16, 0, 0), "black_matte", "Stations", axis='X', parent=root, local=True)
        cyl(f"cup_rod_{s}", 5, 70, (s * 55, 0, 0), "steel", "Stations", axis='X', parent=root, local=True)
        root.rotation_euler.y = math.radians(-1.5 * s)
        # small cylinder body + bracket hanging from the top deck
        cyl(f"cup_cyl_{s}", 13, 70, (s * 125, 0, z), "alu_brushed", "Stations", axis='X')
        box(f"cup_cyl_cap_{s}", (8, 32, 32), (s * 162, 0, z), "black_matte", "Stations", bevel=1.5)
        box(f"cup_bracket_{s}", (12, 40, 160), (s * 172, 0, z + 80), "black_matte", "Stations")
        heads.append(root)
    box("top_deck", (P["W"] - 80, 120, 8), (0, 0, P["pe_top"] + 120), "alu_brushed", "Frame")
    return heads

def build_fillers():
    """two guided pneumatic cylinders (left = ISO/MDI, stroke 350; right = water glass, stroke 150),
       rod pointing UP. Extended = tube tip above the pouch; retracted = filling position
       (tip 30 mm below the clip line / weld line). 12x8 stainless tube with check valve at the tip."""
    heads = {}
    y_c = 125                 # behind the pouch (pouch spans y ±110)
    z_car_low = P["pe_top"] + 20          # carriage in retracted state (still above the pouch top)
    for key, s, stroke, line in (("A", -1, P["stroke_A"], P["clip_z"]), ("B", 1, P["stroke_B"], P["weld_z"])):
        x = s * 150
        body_len = stroke + 70
        z_body_top = z_car_low - 12
        # cylinder body + guide rods + end plates (fixed)
        cyl(f"filler_{key}_body", 20, body_len, (x, y_c, z_body_top - body_len / 2), "alu_brushed", "Fillers")
        box(f"filler_{key}_flange_top", (70, 50, 10), (x, y_c, z_body_top - 5), "black_matte", "Fillers", bevel=2)
        box(f"filler_{key}_flange_bot", (70, 50, 10), (x, y_c, z_body_top - body_len + 5), "black_matte", "Fillers", bevel=2)
        box(f"filler_{key}_mount", (12, 60, body_len - 20), (s * (P["W"] / 2 - 25), y_c, z_body_top - body_len / 2), "alu_brushed", "Frame")
        box(f"filler_{key}_mount_arm", (P["W"] / 2 - 25 - abs(x) - 35, 40, 12), (s * ((P["W"] / 2 - 25 + abs(x) + 35) / 2), y_c, z_body_top - body_len + 20), "alu_brushed", "Fillers")
        for e in (-1, 1):
            cyl(f"filler_{key}_fit{e}", 4, 12, (x + s * 24, y_c + e * 15, z_body_top - body_len / 2 + e * (body_len / 2 - 20)), "copper", "Fillers", axis='X')
        # moving part: carriage plate on the rod + two guide rods + L-arm to the pouch centre + tube
        car = empty(f"filler_{key}_vert", (x, y_c, z_car_low), "Fillers")
        cyl(f"filler_{key}_rod", 8, stroke + 20, (x, y_c, z_car_low - (stroke + 20) / 2 + 10), "steel", "Fillers", parent=car)
        for e in (-1, 1):
            cyl(f"filler_{key}_guide{e}", 5, stroke + 40, (x + s * 24, y_c + e * 16, z_car_low - (stroke + 40) / 2 + 10), "steel", "Fillers", parent=car)
        box(f"filler_{key}_carriage", (76, 56, 14), (x, y_c, z_car_low + 7), "black_matte", "Fillers", parent=car, bevel=2)
        xi = s * 28                                       # tube position over the pouch
        box(f"filler_{key}_armX", (abs(x - xi) + 20, 22, 12), ((x + xi) / 2, y_c, z_car_low + 8), "alu_brushed", "Fillers", parent=car)
        box(f"filler_{key}_armY", (22, y_c + 12, 12), (xi, y_c / 2 - 2, z_car_low + 8), "alu_brushed", "Fillers", parent=car)
        tip_hi = z_car_low + stroke - (line - 30) + (line - 30)   # = tip when extended
        tube_len = z_car_low + 20 - (line - 30) - stroke         # tip (retracted) = line - 30
        tip_z = z_car_low + 20 - tube_len                        # retracted-state tip
        cyl(f"filler_{key}_tube", P["rod_od"] / 2, tube_len, (xi, 0, tip_z + tube_len / 2), "steel", "Fillers", parent=car, verts=32)
        cyl(f"filler_{key}_tube_clamp", 11, 18, (xi, 0, z_car_low + 8), "black_matte", "Fillers", parent=car)
        cyl(f"filler_{key}_valve", 8, 16, (xi, 0, tip_z + 8), "steel", "Fillers", parent=car)
        cyl(f"filler_{key}_tipbore", P["rod_id"] / 2, 2, (xi, 0, tip_z - 0.5), "black_matte", "Fillers", parent=car)
        # supply hose: from the tube top, along the arm, down the back wall to the vessel (thin, tidy)
        tube(f"filler_{key}_hose", [(xi, 0, z_car_low + 24), (xi, y_c, z_car_low + 24), (x, y_c + 30, z_car_low + 10),
                                    (x, P["D"] / 2 - 30, z_car_low - 60), (x, P["D"] / 2 - 30, P["bay_top"] + 10), (s * 120, 60, P["bay_top"] - 30)],
             4, "hose", "Fillers")
        heads[key] = (None, car)
    # cable duct on the back wall
    box("cable_duct", (60, 18, P["H"] - 300), (0, P["D"] / 2 - 18, (P["H"] - 300) / 2 + 60), "black_matte", "Frame")
    return heads

def build_utility_bay():
    """below the mid deck: 2 horizontal pressure vessels (air + liquid), peristaltic pumps, regulators, IBC inlets"""
    C = "Utility"
    zc = (40 + P["bay_top"]) / 2 + 2
    for s, name in ((-1, "MDI"), (1, "WG")):
        x = s * 120
        cyl(f"vessel_{name}", 48, 180, (x, 30, zc), "steel", C, axis='Y')
        for e, yy in ((-1, -60), (1, 120)):
            sph = sphere(f"vessel_{name}_dome{e}", 48, (x, yy, zc), "steel", C)
            sph.scale.y = 0.35
        for yy in (-30, 90):
            cyl(f"vessel_{name}_ring{yy}", 51, 6, (x, yy, zc), "black_matte", C, axis='Y')
        for yy in (-30, 90):
            box(f"vessel_{name}_saddle{yy}", (110, 24, 30), (x, yy, 55), "black_matte", C)
        # air inlet w/ regulator on top (rear), liquid outlet at the bottom front
        cyl(f"vessel_{name}_airport", 5, 20, (x, 100, zc + 55), "copper", C)
        box(f"regulator_{name}", (26, 26, 24), (x, 100, zc + 75), "black_matte", C, bevel=2)
        cyl(f"regulator_{name}_gauge", 12, 5, (x, 86, zc + 75), "clip_white", C, axis='Y')
        cyl(f"vessel_{name}_outlet", 5, 24, (x, -60, zc - 50), "copper", C, axis='Y')
        # peristaltic pump (head disc + motor) at the front
        cyl(f"pump_{name}_head", 26, 16, (x + s * 60, -120, 100), "clip_white", C, axis='Y')
        cyl(f"pump_{name}_rotor", 17, 18, (x + s * 60, -122, 100), "black_matte", C, axis='Y')
        cyl(f"pump_{name}_motor", 20, 60, (x + s * 60, -80, 100), "alu_brushed", C, axis='Y')
        # IBC inlet port through the back panel
        cyl(f"ibc_inlet_{name}", 9, 24, (x, P["D"] / 2 - 2, 90), "steel", C, axis='Y')
        tube(f"pump_{name}_hose_in", [(x, P["D"] / 2 - 10, 90), (x + s * 60, 0, 80), (x + s * 60, -100, 100)], 4, "hose", C)
        tube(f"pump_{name}_hose_out", [(x + s * 60, -130, 100), (x + s * 30, -140, 140), (x, 110, zc + 70)], 4, "hose", C)
    # compressor air inlet + manifold, control electronics box
    cyl("air_inlet", 8, 24, (0, P["D"] / 2 - 2, 130), "steel", C, axis='Y')
    box("plc_box", (110, 60, 100), (0, 20, 100), "black_matte", C, bevel=2)
    for i in range(6):
        box(f"plc_led_{i}", (4, 2, 4), (-30 + i * 12, -11, 135), "led_green", C)

def build_hmi():
    """tablet on an articulated arm on the right side, two buttons, 3-colour stack light on top"""
    C = "HMI"
    W, D, H = P["W"], P["D"], P["H"]
    hw = W / 2
    # arm: wall mount on the right panel -> ball joint -> arm forward/outward -> ball joint -> tablet facing the FRONT
    box("arm_mount", (12, 70, 70), (hw + 6, -60, 900), "black_matte", C, bevel=3)
    sphere("arm_joint1", 18, (hw + 24, -60, 900), "black_gloss", C)
    arm = cyl("arm", 11, 150, (hw + 24 + 45, -60 - 55, 895), "alu_brushed", C, axis='X')
    arm.rotation_euler = (0, math.radians(90 + 4), math.radians(50))
    sphere("arm_joint2", 18, (hw + 24 + 90, -60 - 110, 890), "black_gloss", C)
    tab = empty("TABLET", (hw + 24 + 90 - 40, -60 - 130, 890), C)
    tab.rotation_euler = (math.radians(-14), 0, 0)      # tilted back 14°, screen toward -Y (operator)
    box("tablet_body", (260, 10, 175), (0, 0, 0), "screen_bezel", C, parent=tab, bevel=3, local=True)
    box("tablet_screen", (240, 1.2, 155), (0, -5.3, 0), "screen", C, parent=tab, local=True)
    # UI mock on screen: a few bars
    for i, (w, h, yy, zz, m) in enumerate((
        (190, 18, 0, 55, "silver_accent"), (90, 12, -60, 20, "led_green"), (90, 12, 60, 20, "clip_white"),
        (200, 40, 0, -30, "black_gloss"))):
        box(f"ui_{i}", (w, 0.8, h), (yy, -6.2, zz), m, C, parent=tab, local=True)
    # two-hand safety start: two green buttons on the front, bottom left + bottom right under the drawer
    for xx, nm in ((-185, "btn_start_L"), (185, "btn_start_R")):
        cyl(f"{nm}_ring", 20, 6, (xx, -D / 2 - 1, 92), "silver_accent", C, axis='Y')
        cyl(nm, 16, 10, (xx, -D / 2 - 4, 92), "btn_green", C, axis='Y')
        cyl(f"{nm}_guard", 24, 3, (xx, -D / 2 - 2, 92), "black_matte", C, axis='Y')
    # 3-colour stack light, top rear right
    x, y = hw - 55, D / 2 - 55
    cyl("stack_base", 18, 24, (x, y, H + 12), "black_matte", C)
    cyl("stack_pole", 6, 30, (x, y, H + 24 + 15), "black_matte", C)
    for i, m in enumerate(("led_green", "led_amber", "led_red")):
        cyl(f"stack_{m}", 25, 34, (x, y, H + 54 + 17 + i * 36), m, C)
        cyl(f"stack_sep_{i}", 26, 3, (x, y, H + 54 + i * 36), "black_matte", C)
    cyl("stack_top", 25, 6, (x, y, H + 54 + 3 * 36 + 3), "black_matte", C)

# ----------------------------------------------------------------------------
# STATE  (drawer / jaws / cups / rods / liquids / cutaway)
# ----------------------------------------------------------------------------
def apply_state(st, objs):
    O = bpy.data.objects
    O["DRAWER_ROOT"].location.y = -320 * st["drawer_open"] * S
    for hd, s in ((objs["clip"][0], -1), (objs["clip"][1], 1)):
        hd.location.x = s * (60 - 50 * st["clip_close"]) * S
    for hd, s in ((objs["weld"][0], -1), (objs["weld"][1], 1)):
        hd.location.x = s * (60 - 52 * st["weld_close"]) * S
    for hd, s in ((objs["cups"][0], -1), (objs["cups"][1], 1)):
        hd.location.x = s * (7 + 60 * st["cups_open"]) * S
        hd.rotation_euler.y = math.radians(-1.5 * s * st["cups_open"])
    for key in ("A", "B"):
        _, vert = objs["fill"][key]
        fwd, down = st["rod" + key]
        stroke = P["stroke_A"] if key == "A" else P["stroke_B"]
        vert.location.z = stroke * (1.0 - down) * S      # extended (up) when not filling
    # liquids: scale from bottom
    for nm, lvl in (("liquid_mdi", st["mdi_level"]), ("liquid_wg", st["wg_level"])):
        o = O[nm]
        o.scale.z = max(lvl, 0.001)
        o.hide_render = o.hide_viewport = lvl <= 0.001
    # pouch opening: scale PE pouch top? keep simple – cups pull faces apart (visual only)
    cut = st["cutaway"]
    for nm in ("front_l", "front_r", "front_top", "front_bot", "panel_right", "frame_l", "frame_r", "frame_t", "frame_b",
               "drawer_front", "handle_slot", "handle_lip", "logo_MIA", "logo_pol"):
        if nm in O:
            O[nm].hide_render = O[nm].hide_viewport = cut

# ----------------------------------------------------------------------------
# SCENE: lights, floor, cameras, render
# ----------------------------------------------------------------------------
def build_studio():
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 0, 0))
    fl = bpy.context.active_object
    fl.name = "studio_floor"
    _apply(fl, "floor", "Studio")
    # curved backdrop
    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, 3.0, 1.5), rotation=(math.pi / 2, 0, 0))
    bd = bpy.context.active_object
    bd.name = "backdrop"
    _apply(bd, "floor", "Studio")
    w = bpy.context.scene.world or bpy.data.worlds.new("World")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.012, 0.014, 0.02, 1)
    bg.inputs[1].default_value = 1.0
    def area(name, loc, rot, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, 'AREA')
        ld.energy = energy
        ld.size = size
        ld.color = color
        o = bpy.data.objects.new(name, ld)
        o.location = loc
        o.rotation_euler = [math.radians(r) for r in rot]
        col("Studio").objects.link(o)
        return o
    area("key", (-1.8, -2.0, 2.6), (52, -18, -40), 220, 1.8, (1, 0.97, 0.92))
    area("fill", (2.4, -1.6, 1.4), (62, 25, 55), 90, 2.5, (0.85, 0.9, 1))
    area("rim", (0.8, 1.6, 2.3), (-50, 10, 160), 260, 1.0)
    area("top", (0, 0, 3.2), (0, 0, 0), 60, 2.0)

def camera(name, loc, target, lens=50):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    o = bpy.data.objects.new(name, cd)
    o.location = loc
    col("Studio").objects.link(o)
    tgt = bpy.data.objects.new(name + "_target", None)
    tgt.location = target
    col("Studio").objects.link(tgt)
    c = o.constraints.new('TRACK_TO')
    c.target = tgt
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    return o

def render(cam, path, samples=36, res=(1400, 1000)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception:
        pass
    sc.cycles.max_bounces = 8
    sc.cycles.transmission_bounces = 8
    sc.cycles.transparent_max_bounces = 12
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = 'AgX' if 'AgX' in [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items] else 'Filmic'
    sc.view_settings.look = 'AgX - Medium High Contrast' if sc.view_settings.view_transform == 'AgX' else 'None'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("rendered", path)

# ----------------------------------------------------------------------------
def build_all():
    clean_scene()
    materials()
    build_housing()
    root = build_drawer()
    build_pouches(root)
    objs = dict(clip=build_clipper(), weld=build_welder(), cups=build_vacuum_cups(), fill=build_fillers())
    build_utility_bay()
    build_hmi()
    build_studio()
    return objs

if __name__ == "__main__" or True:
    objs = build_all()
    mode = os.environ.get("MIA_MODE", "preview")
    H = P["H"] * S
    cam_hero = camera("cam_hero", (2.3, -2.3, 1.2), (0.0, 0, H * 0.5), 55)
    cam_open = camera("cam_open", (-1.9, -2.5, 1.3), (0, -0.15, H * 0.5), 50)
    cam_cut = camera("cam_cut", (2.0, -2.2, 1.2), (-0.05, 0, H * 0.5), 50)
    cam_front = camera("cam_front", (0.4, -3.2, 0.7), (0, 0, H * 0.5), 60)
    cam_detail = camera("cam_detail", (0.75, -0.55, 0.78), (0, 0, 0.66), 60)

    if mode == "preview":
        # 1) hero, closed
        apply_state(dict(STATE), objs)
        render(cam_hero, os.path.join(OUT, "01_hero.png"))
        render(cam_front, os.path.join(OUT, "02_front.png"))
        # 2) drawer open, pouch loaded, clips in
        st = dict(STATE); st["drawer_open"] = 1.0; st["mdi_level"] = 0; st["wg_level"] = 0
        apply_state(st, objs)
        render(cam_open, os.path.join(OUT, "03_drawer_open.png"))
        # 3) cutaway, process mid-way: cups open, MDI rod down filling, clip open
        st = dict(STATE); st["cutaway"] = True; st["cups_open"] = 1.0; st["rodA"] = (1.0, 1.0); st["mdi_level"] = 0.6; st["wg_level"] = 0
        apply_state(st, objs)
        render(cam_cut, os.path.join(OUT, "04_cutaway_fill.png"))
        # 4) cutaway detail: clip + weld closed, both liquids in
        st = dict(STATE); st["cutaway"] = True; st["clip_close"] = 1.0; st["weld_close"] = 1.0
        apply_state(st, objs)
        render(cam_detail, os.path.join(OUT, "05_cutaway_detail.png"), samples=40)
        # back to closed for export
        apply_state(dict(STATE), objs)

    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "MIA_model.blend"))
    try:
        for o in bpy.data.objects:
            o.select_set(o.users_collection and o.users_collection[0].name != "Studio" and o.type in ('MESH', 'CURVE', 'FONT', 'EMPTY'))
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "MIA_model.glb"), export_format='GLB',
                                  use_selection=True, export_apply=True)
        print("exported glb")
    except Exception as e:
        print("glb export failed:", e)
