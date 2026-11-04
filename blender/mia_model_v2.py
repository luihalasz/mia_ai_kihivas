"""
MIA (Manyika) v2 – burst pouch filler / clipper / sealer
Parametric Blender model rebuilt to the configurator's final layout (all dimensions in mm).

Coordinate system (Blender metres, model built in mm and scaled /1000):
  X = width (515)  – jaws close along X, pouch faces are ±X
  Y = depth (340)  – front = -Y, drawer pulls out toward -Y; the utility skid stands behind (+Y)
  Z = height       – floor at Z=0
"""
import bpy, math, os
from mathutils import Vector

S = 0.001
OUT = os.environ.get("MIA_OUT", os.path.join(os.path.dirname(os.path.abspath(__file__)), "out_v2"))
os.makedirs(OUT, exist_ok=True)

# ----------------------------------------------------------------------------
# PARAMETERS (mm) – mirrors configurator.html
# ----------------------------------------------------------------------------
CFG = dict(kicsi=dict(k=255, w=192, peH=550, aluH=285), nagy=dict(k=380, w=345, peH=800, aluH=450))
PRESET = os.environ.get("MIA_PRESET", "kicsi")
FILL = dict(iso=100, wg=70)                      # 330 ml
P = dict(W=515, D=340, panel=6, peW=180, aluW=220, pouchZ0=200, clipLen=220, cupD=40, rodD=12,
         strokeA=475, tubeA=490, strokeB=140, tubeB=155, drawer_w=190)
c = CFG[PRESET]
P.update(peH=c["peH"], aluH=c["aluH"], k=c["k"], w=c["w"])
P["clipZ"] = P["pouchZ0"] + P["k"]
P["weldZ"] = P["clipZ"] + P["w"]
P["peTop"] = P["pouchZ0"] + P["peH"]
P["aluTop"] = P["pouchZ0"] + P["aluH"]
P["carA"] = (P["clipZ"] - 30) + P["tubeA"] - 20                 # ISO carriage, DOWN position
P["carB"] = (P["weldZ"] - 10) + P["tubeB"] - 20                 # water-glass carriage, DOWN position
big = CFG["nagy"]
peTopMax = P["pouchZ0"] + big["peH"]
carAmax = (P["pouchZ0"] + big["k"] - 30) + P["tubeA"] - 20
carBmax = (P["pouchZ0"] + big["k"] + big["w"] - 10) + P["tubeB"] - 20
P["H"] = max(carAmax + P["strokeA"], carBmax + P["strokeB"]) + 27 + 20      # 1542
P["zb0"] = P["pouchZ0"] - 35
P["zb1"] = peTopMax + 40                                                   # drawer frame sized for the large pouch
P["drawer_z0"] = P["zb0"] - 25
P["drawer_z1"] = P["zb1"] + 100
TABLE_H = 700            # stand height: handle centre (602) + 700 = ~1300 mm, chest height for the operator

# pose (idle = finished product, rods up, jaws open, clips on the pouch)
POSE = dict(drawer=0.0, cups=0.0, cupsOpen=0.0, cupsOpenMax=1.0, rodA=0.0, rodB=0.0, mdi=1.0, wg=1.0,
            clip=0.0, weld=0.0, clipFlat=1.0, weldFlat=1.0, clipped=1, cutaway=False, hide_housing=False)

# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def clean_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    MATS.clear(); COLS.clear()
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'; sc.unit_settings.length_unit = 'MILLIMETERS'
    return sc

COLS = {}
def col(name):
    if name not in COLS:
        c_ = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c_); COLS[name] = c_
    return COLS[name]
def link(obj, cname):
    for c_ in obj.users_collection: c_.objects.unlink(obj)
    col(cname).objects.link(obj)

MATS = {}
def mat(name, base=(0.5, 0.5, 0.5), metallic=0.0, rough=0.5, transmission=0.0, emission=None, emission_strength=0.0,
        alpha=1.0, coat=0.0, ior=1.45):
    if name in MATS: return MATS[name]
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*base, 1); b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough; b.inputs["IOR"].default_value = ior
    if "Transmission Weight" in b.inputs: b.inputs["Transmission Weight"].default_value = transmission
    if "Coat Weight" in b.inputs: b.inputs["Coat Weight"].default_value = coat
    b.inputs["Alpha"].default_value = alpha
    if emission:
        b.inputs["Emission Color"].default_value = (*emission, 1); b.inputs["Emission Strength"].default_value = emission_strength
    MATS[name] = m; return m

def materials():
    mat("alu_frame", (0.80, 0.80, 0.82), metallic=1.0, rough=0.32)           # silver extrusions / rims
    mat("alu_brushed", (0.72, 0.72, 0.74), metallic=1.0, rough=0.42)
    mat("smoked_glass", (0.42, 0.44, 0.47), rough=0.04, transmission=0.92, coat=0.4, ior=1.49)   # grey tinted panels
    mat("dark_panel", (0.10, 0.10, 0.11), metallic=0.6, rough=0.35, coat=0.3)  # gunmetal plinth / cap
    mat("black_matte", (0.012, 0.012, 0.013), rough=0.55)
    mat("black_gloss", (0.01, 0.01, 0.01), rough=0.15, coat=0.6)
    mat("steel", (0.62, 0.62, 0.64), metallic=1.0, rough=0.28)
    mat("alu_foil", (0.86, 0.86, 0.88), metallic=1.0, rough=0.18, alpha=0.9)
    mat("rubber", (0.02, 0.02, 0.02), rough=0.9)
    mat("tpu_grey", (0.28, 0.29, 0.3), rough=0.75)
    mat("white", (0.93, 0.93, 0.92), rough=0.5)
    mat("clip_yellow", (0.9, 0.72, 0.25), rough=0.45)
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
    mat("floor", (0.05, 0.05, 0.055), rough=0.3, coat=0.3)
    mat("pneu_blue", (0.05, 0.25, 0.75), rough=0.4)                            # 12 mm pneumatic PE tube
    mat("hose_clear", (0.9, 0.9, 0.85), rough=0.3, transmission=0.4, alpha=0.8)
    mat("tank_steel", (0.70, 0.71, 0.73), metallic=1.0, rough=0.35)
    mat("skid_black", (0.03, 0.03, 0.035), rough=0.6)
    mat("ibc_white", (0.92, 0.93, 0.9), rough=0.4, transmission=0.3, alpha=0.9)
    mat("ibc_cage", (0.75, 0.75, 0.77), metallic=1.0, rough=0.45)
    mat("led_strip", (1, 1, 1), rough=0.3, emission=(0.75, 0.85, 1.0), emission_strength=5)
    mat("silver_accent", (0.85, 0.85, 0.87), metallic=1.0, rough=0.2)

def _apply(obj, m, cname, parent=None, bevel=None, local=False):
    if m: obj.data.materials.append(MATS[m])
    link(obj, cname)
    if bevel:
        b = obj.modifiers.new("bevel", 'BEVEL'); b.width = bevel * S; b.segments = 4; b.limit_method = 'ANGLE'
    if parent:
        obj.parent = parent
        if not local: obj.matrix_parent_inverse = parent.matrix_world.inverted()
    return obj

def box(name, size, loc, m, cname, parent=None, bevel=None, rot=(0, 0, 0), local=False):
    bpy.ops.mesh.primitive_cube_add(size=1, location=[v * S for v in loc], rotation=[math.radians(r) for r in rot])
    o = bpy.context.active_object; o.name = name; o.scale = [v * S for v in size]
    bpy.ops.object.transform_apply(scale=True)
    return _apply(o, m, cname, parent, bevel, local)

def cyl(name, r, h, loc, m, cname, axis='Z', parent=None, verts=48, local=False):
    rot = {'Z': (0, 0, 0), 'X': (0, math.pi / 2, 0), 'Y': (math.pi / 2, 0, 0)}[axis]
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r * S, depth=h * S, location=[v * S for v in loc], rotation=rot)
    o = bpy.context.active_object; o.name = name
    return _apply(o, m, cname, parent, None, local)

def sphere(name, r, loc, m, cname, parent=None):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r * S, location=[v * S for v in loc], segments=32, ring_count=16)
    o = bpy.context.active_object; o.name = name; bpy.ops.object.shade_smooth()
    return _apply(o, m, cname, parent)

def empty(name, loc, cname, parent=None):
    o = bpy.data.objects.new(name, None); o.location = [v * S for v in loc]; o.empty_display_size = 0.05
    col(cname).objects.link(o)
    if parent: o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def tube(name, points, r, m, cname, parent=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r * S; cu.bevel_resolution = 6; cu.resolution_u = 12
    sp = cu.splines.new('NURBS'); sp.points.add(len(points) - 1)
    for i, p in enumerate(points): sp.points[i].co = (p[0] * S, p[1] * S, p[2] * S, 1)
    sp.use_endpoint_u = True; sp.order_u = 3
    o = bpy.data.objects.new(name, cu); o.data.materials.append(MATS[m]); col(cname).objects.link(o)
    if parent: o.parent = parent; o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

def text(name, txt, size, loc, m, cname, rot=(90, 0, 0), extrude=0.6, align='CENTER'):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = txt; cu.size = size * S; cu.extrude = extrude * S; cu.align_x = align
    o = bpy.data.objects.new(name, cu); o.location = [v * S for v in loc]; o.rotation_euler = [math.radians(r) for r in rot]
    o.data.materials.append(MATS[m]); col(cname).objects.link(o); return o

def mesh_from_rings(name, rings, m, cname, parent=None, local=False, close=True, smooth=True):
    """rings: list of rows, each a list of (x,y,z) in mm with equal length -> quad strip surface"""
    verts, faces = [], []
    n = len(rings[0])
    for row in rings:
        for p in row: verts.append((p[0] * S, p[1] * S, p[2] * S))
    for v in range(len(rings) - 1):
        for u in range(n - 1):
            a = v * n + u; faces.append((a, a + 1, a + n + 1, a + n))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); col(cname).objects.link(o)
    if m: o.data.materials.append(MATS[m])
    if smooth:
        for p in me.polygons: p.use_smooth = True
    if parent:
        o.parent = parent
        if not local: o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o

# ----------------------------------------------------------------------------
# pouch cross-section (same rules as the configurator)
# ----------------------------------------------------------------------------
OPEN_R, NU, NV, CAP = 45, 40, 70, 4
def ramp(d, w): return max(0.0, min(1.0, d / w))
def profileF(z, p):
    z0, peTop, cz, wz = P["pouchZ0"], P["peTop"], P["clipZ"], P["weldZ"]
    liq = 0.0
    if p["mdi"] > 0:
        top = z0 + FILL["iso"] * p["mdi"]; liq = max(liq, 0.3 * ramp(z - z0, 35) * ramp(top - z, 12))
    if p["wg"] > 0:
        bot = cz + 8; top = bot + FILL["wg"] * p["wg"]; liq = max(liq, 0.6 * ramp(z - bot, 20) * ramp(top - z, 12))
    held = max(p["cupsOpen"], p["cupsOpenMax"]); above = ramp(z - wz, 12)
    opn = held * (1 - above) + p["cupsOpen"] * above
    cup = opn * ramp(z - z0, peTop - z0) ** 0.7
    band = lambda zc, amt: amt * math.exp(-((z - zc) / 22) ** 2)
    keep = max(0.0, 1 - band(cz, p["clipFlat"]) - band(wz, p["weldFlat"]))
    return dict(cup=cup * keep, liq=liq * keep)

def section(W, thick, extra, f):
    rCup = OPEN_R * f["cup"]; r = max(rCup, OPEN_R * f["liq"])
    return thick + r + extra * f["cup"], max(0.0, (W - math.pi * rCup) / 2)

def ring_pts(xf, a, z):
    nFlat = (NU - 2 * CAP) // 2; pts = []
    for u in range(NU + 1):
        if u <= nFlat: x, y = xf, -a + 2 * a * u / nFlat
        elif u <= nFlat + CAP: ang = math.pi * (u - nFlat) / CAP; x, y = xf * math.cos(ang), a + xf * math.sin(ang)
        elif u <= 2 * nFlat + CAP: x, y = -xf, a - 2 * a * (u - nFlat - CAP) / nFlat
        else: ang = math.pi * (u - 2 * nFlat - CAP) / CAP; x, y = -xf * math.cos(ang), -a - xf * math.sin(ang)
        pts.append((x, y, z))
    return pts

def build_pouch(name, W, Hh, thick, extra, m, p, parent):
    rings = []
    for v in range(NV + 1):
        z = P["pouchZ0"] + Hh * v / NV
        xf, a = section(W, thick, extra, profileF(z, p)); rings.append(ring_pts(xf, a, z))
    return mesh_from_rings(name, rings, m, "Pouch", parent)

def build_liquid(name, zBottom, h, m, p, parent):
    Wl = P["peW"] - 6; NL = 30; rings = []
    for v in range(NL + 3):
        vv = max(0, min(NL, v - 1)); z = zBottom + h * vv / NL; cap = v == 0 or v == NL + 2
        xf, a = section(Wl, 3, 0, profileF(z, p))
        rings.append(ring_pts(0 if cap else xf, 0 if cap else a, z))
    return mesh_from_rings(name, rings, m, "Pouch", parent)

def build_smoother(name, L, s, x0, z, close, parent):
    """D-profile bar (16 tall, 10 deep) bowed ')(' in the top view when open, straight when the jaws meet"""
    N, M_, R, T, BOW = 24, 12, 8, 10, 10 * (1 - close); rings = []
    for v in range(N + 3):
        cap = v == 0 or v == N + 2; vv = max(0, min(N, v - 1)); t = vv / N * 2 - 1; y = t * L / 2; xc = x0 - BOW * (1 - t * t)
        row = []
        for u in range(M_ + 2):
            if cap: dx, dz = s * T / 2, 0
            elif u <= M_: ang = -math.pi / 2 + math.pi * u / M_; dx, dz = s * T * math.cos(ang), R * math.sin(ang)
            else: dx, dz = 0, -R
            row.append((s * xc + dx, y, z + dz))
        rings.append(row)
    return mesh_from_rings(name, rings, "white", "Stations", parent, local=True)

# ----------------------------------------------------------------------------
# HOUSING – aluminium frame, smoked grey glass panels
# ----------------------------------------------------------------------------
def build_housing():
    W, D, H, t = P["W"], P["D"], P["H"], P["panel"]; hw, hd = W / 2, D / 2; C = "Housing"
    box("plinth", (W, D, 40), (0, 0, 20), "dark_panel", C, bevel=6)
    box("top_cap", (W, D, 12), (0, 0, H - 6), "dark_panel", C, bevel=4)
    box("top_rim", (W - 8, D - 8, 3), (0, 0, H + 1), "alu_frame", C)
    # frame posts + horizontal rails
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"post_{sx}_{sy}", (30, 30, H - 55), (sx * (hw - 15), sy * (hd - 15), 40 + (H - 55) / 2), "alu_frame", "Frame", bevel=3)
    for zz in (P["drawer_z0"] - 20, P["drawer_z1"] + 20, H - 14):
        box(f"rail_front_{zz}", (W - 60, 30, 24), (0, -hd + 15, zz), "alu_frame", "Frame")
        box(f"rail_back_{zz}", (W - 60, 30, 24), (0, hd - 15, zz), "alu_frame", "Frame")
        for sx in (-1, 1): box(f"rail_side_{sx}_{zz}", (30, D - 60, 24), (sx * (hw - 15), 0, zz), "alu_frame", "Frame")
    # glass panels
    box("panel_left", (t, D - 60, H - 80), (-hw + t / 2 + 2, 0, 40 + (H - 80) / 2), "smoked_glass", C)
    box("panel_right", (t, D - 60, H - 80), (hw - t / 2 - 2, 0, 40 + (H - 80) / 2), "smoked_glass", C)
    box("panel_back", (W - 60, t, H - 80), (0, hd - t / 2 - 2, 40 + (H - 80) / 2), "smoked_glass", C)
    dw, z0, z1 = P["drawer_w"], P["drawer_z0"], P["drawer_z1"]; y = -hd + t / 2 + 2
    box("front_l", ((W - dw) / 2 - 32, t, H - 80), (-(dw / 2 + (W - dw) / 4 - 16 + 1), y, 40 + (H - 80) / 2), "smoked_glass", C)
    box("front_r", ((W - dw) / 2 - 32, t, H - 80), ((dw / 2 + (W - dw) / 4 - 16 + 1), y, 40 + (H - 80) / 2), "smoked_glass", C)
    box("front_top", (dw + 2, t, (H - 40) - z1), (0, y, (H - 40 + z1) / 2), "smoked_glass", C)
    box("front_bot", (dw + 2, t, z0 - 40), (0, y, (z0 + 40) / 2), "smoked_glass", C)
    # drawer opening frame (silver)
    for nm, sz, lc in (("frame_l", (10, 10, z1 - z0 + 20), (-(dw / 2 + 5), -hd + 5, (z0 + z1) / 2)),
                       ("frame_r", (10, 10, z1 - z0 + 20), ((dw / 2 + 5), -hd + 5, (z0 + z1) / 2)),
                       ("frame_t", (dw + 20, 10, 10), (0, -hd + 5, z1 + 5)), ("frame_b", (dw + 20, 10, 10), (0, -hd + 5, z0 - 5))):
        box(nm, sz, lc, "alu_frame", C)
    # decks
    box("base_plate", (W - 40, D - 40, 6), (0, 0, 43), "black_matte", "Frame")
    box("mid_deck", (W - 40, D - 40, 6), (0, 0, 183), "alu_brushed", "Frame")
    # interior LED strips
    for sx in (-1, 1): box(f"led_strip_{sx}", (4, 6, H - 300), (sx * (hw - 34), -hd + 32, (H - 300) / 2 + 190), "led_strip", "Frame")
    box("led_strip_top", (W - 120, 6, 4), (0, -hd + 32, H - 40), "led_strip", "Frame")
    # branding top-right, silver; small POLINVENT under it
    text("logo_MIA", "MIA", 30, (hw - 40, -hd + 1.5, H - 100), "silver_accent", C, extrude=1.0, align='RIGHT')
    text("logo_pol", "POLINVENT", 11, (hw - 40, -hd + 1.5, H - 122), "silver_accent", C, extrude=0.6, align='RIGHT')
    # two-hand safety start: green buttons bottom left + right under the drawer
    for xx in (-185, 185):
        cyl(f"btn_ring_{xx}", 20, 6, (xx, -hd - 1, 92), "silver_accent", "HMI", axis='Y')
        cyl(f"btn_{xx}", 16, 10, (xx, -hd - 4, 92), "btn_green", "HMI", axis='Y')
    # rear grommets for the 12 mm pneumatic lines + power
    for xx in (-150, 150): cyl(f"grommet_{xx}", 12, 12, (xx, hd - 2, H - 120), "rubber", C, axis='Y')
    cyl("grommet_power", 10, 12, (0, hd - 2, 120), "rubber", C, axis='Y')

# ----------------------------------------------------------------------------
# DRAWER (sized for the large pouch), two rubber U-profiles, handle, slides
# ----------------------------------------------------------------------------
def build_drawer(pose):
    W, D, t = P["W"], P["D"], P["panel"]; hd = D / 2; dw = P["drawer_w"]; C = "Drawer"
    zb0, zb1 = P["zb0"], P["zb1"]; z0, z1 = P["drawer_z0"], P["drawer_z1"]
    root = empty("DRAWER_ROOT", (0, 0, 0), C)
    box("drawer_front", (dw - 3, t + 2, z1 - z0 - 3), (0, -hd + t / 2 + 2, (z0 + z1) / 2), "smoked_glass", C, parent=root, bevel=2)
    box("drawer_front_frame", (dw - 3, 4, z1 - z0 - 3), (0, -hd + 1, (z0 + z1) / 2), "alu_frame", C, parent=root, bevel=2)
    # vertical black pull handle, centred
    hz = (zb0 + zb1) / 2
    for e in (-1, 1): cyl(f"handle_standoff_{e}", 6, 22, (0, -hd - 11, hz + e * 70), "black_gloss", C, axis='Y', parent=root)
    cyl("handle_bar", 9, 160, (0, -hd - 24, hz), "black_gloss", C, parent=root)
    # frame: two vertical bars (Y = ±125), bottom bar, spines
    yb = P["aluW"] / 2 + 15
    for s_ in (-1, 1): box(f"bar_{s_}", (28, 22, zb1 - zb0), (0, s_ * yb, (zb0 + zb1) / 2), "alu_brushed", C, parent=root, bevel=2)
    box("bar_bottom", (28, 2 * yb + 22, 22), (0, 0, zb0 + 11), "alu_brushed", C, parent=root, bevel=2)
    box("spine_bottom", (28, (hd - 6) - (yb - 11), 22), (0, -(hd - 6 + yb - 11) / 2, zb0 + 11), "alu_brushed", C, parent=root)
    box("spine_top", (28, (hd - 6) - (yb - 11), 22), (0, -(hd - 6 + yb - 11) / 2, zb1 - 11), "alu_brushed", C, parent=root)
    # telescopic slides both sides at the bottom
    for sx in (-1, 1):
        box(f"slide_fixed_{sx}", (12, D - 50, 32), (sx * 24, 0, zb0 - 6), "steel", "Frame")
        box(f"slide_moving_{sx}", (10, D - 60, 24), (sx * 13, 0, zb0 - 6), "alu_brushed", C, parent=root)
    # rubber U-profiles, gaps at the clip and weld lines of BOTH presets
    gaps = sorted([P["pouchZ0"] + CFG["kicsi"]["k"], P["pouchZ0"] + CFG["kicsi"]["k"] + CFG["kicsi"]["w"],
                   P["pouchZ0"] + CFG["nagy"]["k"], P["pouchZ0"] + CFG["nagy"]["k"] + CFG["nagy"]["w"]])
    segs, a = [], P["pouchZ0"] - 5
    for g in gaps:
        segs.append((a, g - 17)); a = g + 17
    segs.append((a, peTopMax - 10))
    for s_ in (-1, 1):
        yc = s_ * (yb - 18)
        for i, (a_, b_) in enumerate(segs):
            box(f"U_{s_}_{i}_back", (16, 4, b_ - a_), (0, yc + s_ * 5, (a_ + b_) / 2), "rubber", C, parent=root)
            for sx in (-1, 1): box(f"U_{s_}_{i}_lip{sx}", (3, 14, b_ - a_), (sx * 6.5, yc, (a_ + b_) / 2), "rubber", C, parent=root)
    box("pouch_clamp", (10, P["aluW"] + 10, 16), (0, 0, P["pouchZ0"] + 2), "tpu_grey", C, parent=root, bevel=2)
    return root

def slide_drawer(root, pose):
    root.location.y = -320 * pose["drawer"] * S   # after all children are parented, so they travel with it

def build_pouches(root, pose):
    build_pouch("alu_pouch", P["aluW"], P["aluH"], 6, 3, "alu_foil", pose, root)
    build_pouch("pe_pouch", P["peW"], P["peH"], 4.5, 0, "pe_clear", pose, root)
    if pose["mdi"] > 0: build_liquid("liquid_mdi", P["pouchZ0"], FILL["iso"] * pose["mdi"], "mdi_orange", pose, root)
    if pose["wg"] > 0: build_liquid("liquid_wg", P["clipZ"] + 8, FILL["wg"] * pose["wg"], "waterglass", pose, root)
    for s_ in (-1, 1): box(f"silica_{s_}", (3, 40, 25), (s_ * 7, 0, P["pouchZ0"] + 30), "white", "Pouch", parent=root, bevel=1.5)

# ----------------------------------------------------------------------------
# STATIONS
# ----------------------------------------------------------------------------
def pneumatic_pair(name, z, jaw_builder, close, body_r=20, body_len=110):
    heads = []
    for s_ in (-1, 1):
        root = empty(f"{name}_head_{'L' if s_ < 0 else 'R'}", (s_ * (60 - 52 * close), 0, z), "Stations")
        cyl(f"{name}_body_{s_}", body_r, body_len, (s_ * (95 + body_len / 2), 0, z), "alu_brushed", "Stations", axis='X')
        for e in (-1, 1):
            box(f"{name}_cap_{s_}_{e}", (10, body_r * 2 + 6, body_r * 2 + 6), (s_ * (95 + body_len / 2 + e * (body_len / 2 - 5)), 0, z), "black_matte", "Stations", bevel=2)
            cyl(f"{name}_fit_{s_}_{e}", 4, 12, (s_ * (95 + body_len / 2 + e * 40), 0, z + body_r + 6), "copper", "Stations")
        cyl(f"{name}_rod_{s_}", 8, 60, (s_ * 30, 0, 0), "steel", "Stations", axis='X', parent=root, local=True)
        box(f"{name}_bracket_{s_}", (12, 90, 90), (s_ * (95 + body_len + 6), 0, z), "black_matte", "Stations", bevel=2)
        box(f"{name}_brace_{s_}", (12, 30, 200), (s_ * (P["W"] / 2 - 40), 0, z), "alu_brushed", "Frame")
        box(f"{name}_arm_{s_}", (P["W"] / 2 - 40 - (95 + body_len + 6), 30, 14), (s_ * ((P["W"] / 2 - 40 + 95 + body_len + 6) / 2), 0, z + 38), "alu_brushed", "Stations")
        jaw_builder(s_, root); heads.append(root)
    return heads

def build_clipper(pose):
    z, L = P["clipZ"], P["clipLen"]
    def jaw(s_, root):
        box(f"clip_holder_{s_}", (22, L + 14, 34), (s_ * 11, 0, 0), "tpu_grey", "Stations", parent=root, bevel=3, local=True)
        box(f"clip_holder_bracket_{s_}", (14, L + 14, 24), (s_ * 13, 0, -29), "tpu_grey", "Stations", parent=root, local=True)
        build_smoother(f"smoother_clip_{s_}", L, s_, -10, -40, pose["clip"], root)
    heads = pneumatic_pair("clipper", z, jaw, pose["clip"])
    # clip pieces: on the pouch once clipped, else in the holders
    for s_ in (-1, 1):
        x = s_ * 3 if pose["clipped"] else s_ * (55 - 52 * pose["clip"])
        y = -320 * pose["drawer"] if pose["clipped"] else 0
        if s_ < 0:
            box("clip_C_back", (3, L, 10), (x - 3.5, y, z), "clip_yellow", "Stations")
            for e in (-1, 1): box(f"clip_C_lip{e}", (10, L, 2.2), (x, y, z + e * 3.9), "clip_yellow", "Stations")
        else:
            for e in (-1, 1): cyl(f"clip_8_{e}", 2.4, L, (x - 2.0, y, z + e * 2.6), "clip_yellow", "Stations", axis='Y')
    return heads

def build_welder(pose):
    z, L = P["weldZ"], P["clipLen"] + 10
    def jaw(s_, root):
        box(f"weld_jaw_{s_}", (16, L, 28), (s_ * 8, 0, 0), "alu_brushed", "Stations", parent=root, bevel=2, local=True)
        if s_ < 0:
            box("weld_heater", (1.2, L - 10, 5), (-0.6, 0, 0), "copper", "Stations", parent=root, local=True)
        else:
            box("weld_counter_pad", (2, L - 10, 12), (1, 0, 0), "rubber", "Stations", parent=root, local=True)
        box(f"weld_bracket_{s_}", (14, L + 14, 24), (s_ * 10, 0, -26), "tpu_grey", "Stations", parent=root, local=True)
        build_smoother(f"smoother_weld_{s_}", L, s_, 0, -40, pose["weld"], root)
    return pneumatic_pair("welder", z, jaw, pose["weld"])

def build_vacuum_cups(pose):
    z = P["peTop"] - 22
    for s_ in (-1, 1):
        x = 8.5 + (1 - pose["cups"]) * 60 + pose["cupsOpen"] * OPEN_R
        root = empty(f"cup_head_{s_}", (s_ * x, 0, z), "Stations")
        cyl(f"cup_{s_}", P["cupD"] / 2, 8, (s_ * 4, 0, 0), "rubber", "Stations", axis='X', parent=root, local=True)
        cyl(f"cup_neck_{s_}", 6, 20, (s_ * 16, 0, 0), "black_matte", "Stations", axis='X', parent=root, local=True)
        cyl(f"cup_rod_{s_}", 5, 70, (s_ * 55, 0, 0), "steel", "Stations", axis='X', parent=root, local=True)
        cyl(f"cup_cyl_{s_}", 13, 70, (s_ * 125, 0, z), "alu_brushed", "Stations", axis='X')
        box(f"cup_cyl_cap_{s_}", (8, 32, 32), (s_ * 162, 0, z), "black_matte", "Stations", bevel=1.5)
        box(f"cup_bracket_{s_}", (12, 40, 160), (s_ * 172, 0, z + 80), "black_matte", "Stations")
    box("cup_deck", (P["W"] - 100, 120, 8), (0, 0, z + 160), "alu_brushed", "Frame")

def build_fillers(pose):
    """side-mounted guided cylinders (ISO left 490/475, water glass right 155/140), rod up; carriage + L-arm + tube;
       12 mm pneumatic PE lines connect to the metal tube tops and leave through the rear grommets to the skid"""
    C = "Fillers"; ends = {}
    for key, s_, stroke, tube_len, car, line in (("A", -1, P["strokeA"], P["tubeA"], P["carA"], P["clipZ"] - 30),
                                                ("B", 1, P["strokeB"], P["tubeB"], P["carB"], P["weldZ"] - 10)):
        x, y = s_ * 150, 125; top = car - 12; body_len = stroke + 70
        cyl(f"filler_{key}_body", 20, body_len, (x, y, top - body_len / 2), "alu_brushed", C)
        box(f"filler_{key}_flange_top", (70, 50, 10), (x, y, top - 5), "black_matte", C, bevel=2)
        box(f"filler_{key}_flange_bot", (70, 50, 10), (x, y, top - body_len + 5), "black_matte", C, bevel=2)
        box(f"filler_{key}_mount", (12, 60, body_len - 20), (s_ * (P["W"] / 2 - 40), y, top - body_len / 2), "alu_brushed", "Frame")
        for e in (-1, 1): box(f"filler_{key}_mount_arm{e}", (P["W"] / 2 - 40 - 150 - 35, 40, 12), (s_ * ((P["W"] / 2 - 40 + 185) / 2), y, top - body_len / 2 + e * (body_len / 2 - 30)), "alu_brushed", C)
        for e in (-1, 1): cyl(f"filler_{key}_fit{e}", 4, 12, (x + s_ * 24, y + e * 15, top - body_len / 2 + e * (body_len / 2 - 20)), "copper", C, axis='X')
        lift = stroke * (1 - pose["rod" + key]); cz = car + lift
        g = empty(f"filler_{key}_carriage", (0, 0, cz), C)
        cyl(f"filler_{key}_piston", 8, cz - (top - 8), (x, y, (cz + top - 8) / 2), "steel", C)
        for e in (-1, 1): cyl(f"filler_{key}_guide{e}", 5, cz - top + 40, (x + s_ * 24, y + e * 16, (cz + top) / 2 + 20), "steel", C)
        box(f"filler_{key}_block", (76, 56, 14), (x, y, cz + 7), "black_matte", C, bevel=2)
        xi = s_ * 28
        box(f"filler_{key}_armX", (abs(x - xi) + 20, 22, 12), ((x + xi) / 2, y, cz + 21), "steel", C)
        box(f"filler_{key}_armY", (22, y + 12, 12), (xi, y / 2 - 2, cz + 21), "steel", C)
        tip = line + lift
        cyl(f"filler_{key}_tube", P["rodD"] / 2, tube_len, (xi, 0, tip + tube_len / 2), "steel", C, verts=32)
        cyl(f"filler_{key}_clamp", 11, 18, (xi, 0, cz + 21), "black_matte", C)
        cyl(f"filler_{key}_valve", 8, 16, (xi, 0, tip + 8), "steel", C)
        # push-in elbow at the tube top + 12 mm pneumatic line to the rear grommet (then outside to the skid)
        ztop = tip + tube_len
        cyl(f"filler_{key}_elbow", 7, 14, (xi, 0, ztop + 7), "black_matte", C)
        gz = P["H"] - 120
        tube(f"pneu_{key}_inside", [(xi, 0, ztop + 14), (xi, 0, ztop + 60), (xi, 60, ztop + 110), (s_ * 150, P["D"] / 2 - 40, gz), (s_ * 150, P["D"] / 2 + 10, gz)], 6, "pneu_blue", C)
        ends[key] = (s_ * 150, P["D"] / 2 + 10, gz)
    box("cable_duct", (60, 18, P["H"] - 320), (0, P["D"] / 2 - 26, (P["H"] - 320) / 2 + 60), "black_matte", "Frame")
    return ends

def build_inside_bay():
    C = "Utility"
    box("plc_box", (160, 70, 110), (-100, 20, 105), "black_matte", C, bevel=2)
    for i in range(8): box(f"plc_led_{i}", (4, 2, 4), (-150 + i * 12, -16, 150), "led_green", C)
    box("valve_manifold", (120, 50, 40), (110, 20, 70), "alu_brushed", C, bevel=2)
    for i in range(5): cyl(f"valve_{i}", 8, 30, (70 + i * 20, 20, 105), "black_matte", C)
    cyl("air_in", 8, 24, (0, P["D"] / 2 - 2, 70), "steel", C, axis='Y')

# ----------------------------------------------------------------------------
# UTILITY SKID behind the machine: 2 x ~100 l pressure tanks, 6 bar compressor, 1.5 bar switches, peristaltic pumps, IBC
# ----------------------------------------------------------------------------
def build_skid(pneu_ends):
    C = "Skid"; hd = P["D"] / 2
    sy = hd + 420                     # skid centre Y
    box("skid_frame", (900, 520, 40), (0, sy, 20), "skid_black", C, bevel=4)
    for xx in (-400, 0, 400): box(f"skid_cross_{xx}", (40, 520, 40), (xx, sy, 60), "skid_black", C)
    tanks = {}
    for key, xx, name in (("A", -230, "ISO"), ("B", 230, "WG")):
        # ~50 l pressure vessel: Ø300 x 700 (plus domes), on three legs
        R, TH = 150, 700; zb = 80 + 50; zc = zb + TH / 2
        cyl(f"tank_{name}", R, TH, (xx, sy, zc), "tank_steel", C, verts=64)
        for e, zz in ((-1, zb), (1, zb + TH)):
            sph = sphere(f"tank_{name}_dome{e}", R, (xx, sy, zz), "tank_steel", C); sph.scale.z = 0.3
        for zz in (zb + 100, zb + TH - 60): cyl(f"tank_{name}_ring{zz}", R + 4, 10, (xx, sy, zz), "black_matte", C, verts=64)
        for a in range(3):
            ang = math.radians(90 + a * 120)
            box(f"tank_{name}_leg{a}", (26, 26, 100), (xx + 125 * math.cos(ang), sy + 125 * math.sin(ang), 40 + 50), "black_matte", C)
        ztop = zb + TH + R * 0.3
        # top: air inlet with 1.5 bar pressure switch + gauge + safety valve; fill port
        cyl(f"tank_{name}_airport", 8, 40, (xx - 40, sy, ztop + 20), "copper", C)
        box(f"psw_{name}", (40, 40, 50), (xx - 40, sy, ztop + 65), "black_matte", C, bevel=3)
        cyl(f"psw_{name}_gauge", 22, 8, (xx - 40, sy - 26, ztop + 65), "white", C, axis='Y')
        cyl(f"psw_{name}_dial", 18, 2, (xx - 40, sy - 31, ztop + 65), "black_gloss", C, axis='Y')
        cyl(f"tank_{name}_safety", 7, 30, (xx + 40, sy - 30, ztop + 10), "copper", C)
        cyl(f"tank_{name}_fillport", 10, 30, (xx + 60, sy + 40, ztop + 10), "steel", C)
        tanks_top = ztop + 90
        # bottom liquid outlet + check valve -> 12 mm line to the machine grommet
        cyl(f"tank_{name}_outlet", 8, 50, (xx, sy - R - 15, 150), "copper", C, axis='Y')
        box(f"tank_{name}_valve", (24, 40, 24), (xx, sy - R - 50, 150), "black_matte", C, bevel=2)
        ex, ey, ez = pneu_ends[key]
        tube(f"pneu_{name}_outside", [(xx, sy - R - 70, 150), (xx, sy - R - 120, 150), (xx, sy - R - 120, ez - 100), (ex, ey + 60, ez), (ex, ey, ez)], 6, "pneu_blue", C)
        tanks[key] = xx
    # 6 bar compressor with receiver, behind the tanks
    cy = sy + 330
    box("comp_base", (700, 260, 30), (0, cy, 55), "skid_black", C)
    cyl("comp_receiver", 120, 600, (0, cy, 190), "tank_steel", C, axis='X', verts=48)
    for e in (-1, 1):
        sph = sphere(f"comp_receiver_dome{e}", 120, (e * 300, cy, 190), "tank_steel", C); sph.scale.x = 0.3
    cyl("comp_motor", 80, 220, (-150, cy, 380), "black_matte", C, axis='X')
    box("comp_pump", (150, 140, 150), (60, cy, 400), "alu_brushed", C, bevel=4)
    for i in range(2): cyl(f"comp_cyl_{i}", 40, 90, (20 + i * 80, cy, 520), "alu_brushed", C)
    box("comp_filter", (60, 60, 40), (60, cy - 110, 480), "black_matte", C)
    cyl("comp_gauge", 24, 8, (200, cy - 125, 300), "white", C, axis='Y')
    box("comp_regulator", (50, 40, 60), (260, cy - 110, 300), "black_matte", C, bevel=3)
    # air manifold from the receiver to both pressure switches
    tube("air_main", [(260, cy - 130, 330), (260, cy - 130, tanks_top), (0, sy, tanks_top)], 6, "pneu_blue", C)
    for key, xx in tanks.items(): tube(f"air_to_{key}", [(0, sy, tanks_top), (xx - 40, sy, tanks_top + 2), (xx - 40, sy, tanks_top - 10)], 6, "pneu_blue", C)
    # peristaltic pumps at the skid front, feeding the tanks from the IBC
    for key, xx in tanks.items():
        px = xx + (60 if key == "A" else -60); py = sy - 200
        cyl(f"pump_{key}_head", 34, 20, (px, py - 22, 150), "white", C, axis='Y')
        cyl(f"pump_{key}_rotor", 22, 22, (px, py - 24, 150), "black_matte", C, axis='Y')
        cyl(f"pump_{key}_motor", 26, 90, (px, py + 35, 150), "alu_brushed", C, axis='Y')
        box(f"pump_{key}_stand", (80, 60, 60), (px, py + 20, 90), "skid_black", C)
        tube(f"pump_{key}_to_tank", [(px, py - 34, 160), (px, py - 60, 260), (xx + 60, sy + 40, tanks_top - 200), (xx + 60, sy + 40, tanks_top - 85)], 5, "hose_clear", C)
    # two IBCs (1000 l each): isocyanate on the right, water glass on the left; each pump draws from its own IBC
    iy = sy + 150
    for key, ix, label in (("A", 1450, "ISO"), ("B", -1450, "WG")):
        box(f"ibc_pallet_{label}", (1200, 1000, 150), (ix, iy, 75), "skid_black", C)
        box(f"ibc_bottle_{label}", (1150, 950, 1000), (ix, iy, 150 + 500), "ibc_white", C, bevel=20)
        for sx in (-1, 1):
            for sy_ in (-1, 1): box(f"ibc_post_{label}_{sx}_{sy_}", (25, 25, 1010), (ix + sx * 585, iy + sy_ * 485, 150 + 505), "ibc_cage", C)
        for zz in (300, 550, 800, 1050):
            box(f"ibc_cage_f{label}{zz}", (1170, 25, 25), (ix, iy - 487, zz), "ibc_cage", C); box(f"ibc_cage_b{label}{zz}", (1170, 25, 25), (ix, iy + 487, zz), "ibc_cage", C)
            for sx in (-1, 1): box(f"ibc_cage_s{label}{sx}_{zz}", (25, 970, 25), (ix + sx * 585, iy, zz), "ibc_cage", C)
        inner = -1 if ix > 0 else 1                                   # valve on the side facing the skid
        cyl(f"ibc_valve_{label}", 30, 60, (ix + inner * 600, iy, 230), "black_matte", C, axis='X')
        cyl(f"ibc_cap_{label}", 90, 20, (ix, iy, 1160), "black_matte", C)
        text(f"ibc_label_{label}", label, 120, (ix, iy - 490, 650), "black_matte", C, extrude=2)
        xx = tanks[key]; px = xx + (60 if key == "A" else -60); py = sy - 200
        tube(f"ibc_to_pump_{label}", [(ix + inner * 630, iy, 230), (ix + inner * 700, iy - 150, 200), (px, py + 90, 150)], 5, "hose_clear", C)

# ----------------------------------------------------------------------------
# HMI
# ----------------------------------------------------------------------------
def build_hmi():
    C = "HMI"; W, D, H = P["W"], P["D"], P["H"]; hw = W / 2
    box("arm_mount", (12, 70, 70), (hw + 6, -60, 1000), "black_matte", C, bevel=3)
    sphere("arm_joint1", 18, (hw + 24, -60, 1000), "black_gloss", C)
    arm = cyl("arm", 11, 150, (hw + 24 + 45, -60 - 55, 995), "alu_brushed", C, axis='X')
    arm.rotation_euler = (0, math.radians(94), math.radians(50))
    sphere("arm_joint2", 18, (hw + 24 + 90, -60 - 110, 990), "black_gloss", C)
    tab = empty("TABLET", (hw + 24 + 50, -60 - 130, 990), C); tab.rotation_euler = (math.radians(-14), 0, 0)
    box("tablet_body", (260, 10, 175), (0, 0, 0), "screen_bezel", C, parent=tab, bevel=3, local=True)
    box("tablet_screen", (240, 1.2, 155), (0, -5.3, 0), "screen", C, parent=tab, local=True)
    for i, (w, h, yy, zz, m) in enumerate(((190, 18, 0, 55, "silver_accent"), (90, 12, -60, 20, "led_green"), (90, 12, 60, 20, "white"), (200, 40, 0, -30, "black_gloss"))):
        box(f"ui_{i}", (w, 0.8, h), (yy, -6.2, zz), m, C, parent=tab, local=True)
    x, y = hw - 55, D / 2 - 55
    cyl("stack_base", 18, 24, (x, y, H + 14), "black_matte", C); cyl("stack_pole", 6, 30, (x, y, H + 26 + 15), "black_matte", C)
    for i, m in enumerate(("led_green", "led_amber", "led_red")):
        cyl(f"stack_{m}", 25, 34, (x, y, H + 56 + 17 + i * 36), m, C); cyl(f"stack_sep_{i}", 26, 3, (x, y, H + 56 + i * 36), "black_matte", C)
    cyl("stack_top", 25, 6, (x, y, H + 56 + 3 * 36 + 3), "black_matte", C)

# ----------------------------------------------------------------------------
# STUDIO / RENDER
# ----------------------------------------------------------------------------
def build_studio():
    bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 0, 0)); fl = bpy.context.active_object; fl.name = "studio_floor"; _apply(fl, "floor", "Studio")
    bpy.ops.mesh.primitive_plane_add(size=16, location=(0, 4.5, 2), rotation=(math.pi / 2, 0, 0)); bd = bpy.context.active_object; bd.name = "backdrop"; _apply(bd, "floor", "Studio")
    w = bpy.data.worlds.new("World"); bpy.context.scene.world = w; w.use_nodes = True
    bg = w.node_tree.nodes["Background"]; bg.inputs[0].default_value = (0.012, 0.014, 0.02, 1); bg.inputs[1].default_value = 1.0
    def area(name, loc, rot, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.size = size; ld.color = color
        o = bpy.data.objects.new(name, ld); o.location = loc; o.rotation_euler = [math.radians(r) for r in rot]; col("Studio").objects.link(o)
    area("key", (-2.0, -2.4, 3.0), (50, -18, -40), 320, 2.0, (1, 0.97, 0.92))
    area("fill", (2.6, -1.8, 1.6), (62, 25, 55), 120, 2.8, (0.85, 0.9, 1))
    area("rim", (0.8, 2.4, 2.6), (-50, 10, 160), 300, 1.2)
    area("top", (0, 0.6, 3.6), (0, 0, 0), 90, 2.5)

def camera(name, loc, target, lens=50):
    cd = bpy.data.cameras.new(name); cd.lens = lens
    o = bpy.data.objects.new(name, cd); o.location = loc; col("Studio").objects.link(o)
    tgt = bpy.data.objects.new(name + "_target", None); tgt.location = target; col("Studio").objects.link(tgt)
    c_ = o.constraints.new('TRACK_TO'); c_.target = tgt; c_.track_axis = 'TRACK_NEGATIVE_Z'; c_.up_axis = 'UP_Y'
    return o

def render(cam, path, samples=36, res=(1400, 1000)):
    sc = bpy.context.scene; sc.camera = cam
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = samples; sc.cycles.use_denoising = True
    try: sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except Exception: pass
    sc.cycles.max_bounces = 10; sc.cycles.transmission_bounces = 10; sc.cycles.transparent_max_bounces = 12
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.resolution_percentage = 100
    vt = [i.identifier for i in sc.view_settings.bl_rna.properties['view_transform'].enum_items]
    sc.view_settings.view_transform = 'AgX' if 'AgX' in vt else 'Filmic'
    if sc.view_settings.view_transform == 'AgX': sc.view_settings.look = 'AgX - Medium High Contrast'
    sc.render.image_settings.file_format = 'PNG'; sc.render.filepath = path
    bpy.ops.render.render(write_still=True); print("rendered", path)

def hide(names, flag):
    for n in names:
        o = bpy.data.objects.get(n)
        if o: o.hide_render = o.hide_viewport = flag

FRONT_PARTS = ["front_l", "front_r", "front_top", "front_bot", "frame_l", "frame_r", "frame_t", "frame_b", "drawer_front", "drawer_front_frame",
               "logo_MIA", "logo_pol", "handle_bar", "handle_standoff_-1", "handle_standoff_1"]
GLASS = ["panel_left", "panel_right", "panel_back", "front_l", "front_r", "front_top", "front_bot", "drawer_front"]

def build_table():
    """steel stand under the machine: handle at chest height; shelf for consumables"""
    W, D = P["W"] + 40, P["D"] + 40; C = "Table"
    box("table_top", (W, D, 30), (0, 0, TABLE_H - 15), "dark_panel", C, bevel=4)
    for sx in (-1, 1):
        for sy in (-1, 1): box(f"table_leg_{sx}_{sy}", (40, 40, TABLE_H - 30), (sx * (W / 2 - 25), sy * (D / 2 - 25), (TABLE_H - 30) / 2), "alu_frame", C)
    box("table_shelf", (W - 60, D - 60, 20), (0, 0, 200), "dark_panel", C)
    for sx in (-1, 1): box(f"table_brace_{sx}", (W - 90, 20, 20), (0, sx * (D / 2 - 25), TABLE_H - 50), "alu_frame", C)
    for sx in (-1, 1):
        for sy in (-1, 1): cyl(f"table_foot_{sx}_{sy}", 25, 12, (sx * (W / 2 - 25), sy * (D / 2 - 25), 6), "rubber", C)

MACHINE_COLS = ("Housing", "Frame", "Drawer", "Pouch", "Stations", "Fillers", "Utility", "HMI")
def lift_machine():
    m = empty("MACHINE", (0, 0, 0), "Frame"); m.location.z = TABLE_H * S
    for cn in MACHINE_COLS:
        for o in list(col(cn).objects):
            if o is m or o.parent is not None: continue
            o.parent = m; o.matrix_parent_inverse = m.matrix_world.inverted()
    return m

def build_all(pose):
    clean_scene(); materials()
    build_housing(); root = build_drawer(pose); build_pouches(root, pose); slide_drawer(root, pose)
    build_clipper(pose); build_welder(pose); build_vacuum_cups(pose)
    ends = build_fillers(pose); build_inside_bay(); build_hmi()
    build_table(); lift_machine()
    build_skid({k: (v[0], v[1], v[2] + TABLE_H) for k, v in ends.items()}); build_studio()

if __name__ == "__main__" or True:
    mode = os.environ.get("MIA_MODE", "preview")
    H = (P["H"] + TABLE_H) * S; T = TABLE_H * S
    shots = []
    if mode in ("preview", "all"):
        shots = [
            ("01_hero", dict(POSE), (3.4, -3.9, 2.1), (0.0, 0.05, H * 0.52), 50, []),
            ("02_drawer_open", dict(POSE, drawer=1.0), (-2.8, -3.6, 2.0), (0, -0.2, H * 0.52), 48, []),
            ("03_rear_skid", dict(POSE), (-3.6, 4.4, 2.7), (0.2, 0.6, 0.9), 38, []),
            ("04_process_cutaway", dict(POSE, cupsOpen=1.0, cups=1.0, rodA=1.0, mdi=0.6, wg=0.0, clipFlat=0.0, weldFlat=0.0, cupsOpenMax=1.0, clipped=0), (2.0, -1.9, T + 0.9), (0.0, 0.0, T + 0.62), 55, FRONT_PARTS + ["panel_right"]),
            ("05_inside_front", dict(POSE), (0.0, -3.6, T + 0.75), (0.0, 0.0, T + P["H"] * S * 0.5), 50, FRONT_PARTS),
        ]
    for name, pose, loc, tgt, lens, hidden in shots:
        build_all(pose)
        hide(hidden, True)
        cam = camera("cam_" + name, loc, tgt, lens)
        render(cam, os.path.join(OUT, name + ".png"), res=(1400, 1000) if name != "05_inside_front" else (1000, 1400))
    build_all(dict(POSE))
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "MIA_model_v2.blend"))
    try:
        for o in bpy.data.objects:
            o.select_set(bool(o.users_collection) and o.users_collection[0].name != "Studio" and o.type in ('MESH', 'CURVE', 'FONT', 'EMPTY'))
        bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "MIA_model_v2.glb"), export_format='GLB', use_selection=True, export_apply=True)
        print("exported glb")
    except Exception as e:
        print("glb export failed:", e)
