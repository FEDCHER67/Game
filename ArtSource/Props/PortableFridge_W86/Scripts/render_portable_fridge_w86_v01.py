"""PortableFridge_W86 v01 - review renders + slot fit check (Blender 5.2, background).

blender -b --factory-startup --python render_portable_fridge_w86_v01.py
env PF_BLEND (source blend), PF_PANELS (panel output dir), PF_FIT (fit-check json path)
Opens the built blend, adds render-only markers / organ models / crowd NPC, renders
panels. Never saves the blend. Sheets are composed by compose_sheets_v01.py.
"""
import bpy, json, math, os
from mathutils import Vector, Matrix

ROOT = r"C:\Dev\Game\ArtSource\Props\PortableFridge_W86"
BLEND = os.environ.get("PF_BLEND", os.path.join(ROOT, "PortableFridge_W86_v01.blend"))
PANELS = os.environ["PF_PANELS"]
FIT = os.environ.get("PF_FIT", "")
ASSETS = r"C:\Dev\Game\Assets\OnlyVolunteers"
ITEMS = [  # (slot, label, fbx, keep-mesh filter)
    (1, "liver", ASSETS + r"\Props\Organs\LIVER-ASTRA-001_recolour_v01.fbx", None),
    (2, "heart", ASSETS + r"\Props\Organs\HEART-ASTRA-007_recolour_v01.fbx", None),
    (3, "kidney", ASSETS + r"\Props\Organs\KIDNEY-ASTRA-001_recolour_v01.fbx", "L_Kidney"),
    (4, "kidney (second)", ASSETS + r"\Props\Organs\KIDNEY-ASTRA-001_recolour_v01.fbx", "R_Kidney"),
    (5, "lungs", ASSETS + r"\Props\Organs\LUNGS-ASTRA-001_recolour_v01.fbx", None),
    (6, "organ bag (sealed)", r"C:\Dev\Game\ArtSource\Props\ORGANBAG-ASTRA-001\G34_v02\ORGANBAG_ASTRA_001_v02.fbx", "SM_OrganBag_Sealed"),
    (7, "brain", ASSETS + r"\Props\Organs\BRAIN-ASTRA-002_recolour_v01.fbx", None),
    (8, "eye pair (one eye model)", ASSETS + r"\Props\Organs\EYE_ASTRA_001_v05.fbx", None),
    (None, "blood bag (size check only)", ASSETS + r"\Operation\Stage1\Art\BloodBag_v05\BLOOD_BAG_ASTRA_001_v05.fbx", None),
]
NPC = ASSETS + r"\Characters\SausageBuddy\SAUSAGE_BUDDY_A_v04.fbx"
SLOT_H = 0.305

os.makedirs(PANELS, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=BLEND)
scn = bpy.context.scene
for eng in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
    try:
        scn.render.engine = eng
        break
    except TypeError:
        continue
scn.render.resolution_x, scn.render.resolution_y = 1000, 760
scn.render.film_transparent = False
try:
    scn.view_settings.view_transform = "AgX"
    scn.view_settings.look = "AgX - Medium High Contrast"
except TypeError:
    pass
try:
    scn.eevee.taa_render_samples = 64
except AttributeError:
    pass

O = bpy.data.objects
root, mroot = O["PortableFridge_W86"], O["PortableFridge_W86_VanMount"]
LIDS = [O["SM_PortableFridge_Lid_LOD0"], O["SM_PortableFridge_Lid_LOD1"]]


def set_lid(deg):
    for o in LIDS:
        o.rotation_mode = "XYZ"
        o.rotation_euler.x = math.radians(deg)

for o in O:
    if o.name.startswith("UCX_") or o.name.endswith("_LOD1"):
        o.hide_render = True


# ---------------------------------------------------------------- environment
def mat_simple(name, col, rough=0.8, emit=None, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*col, 1)
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = 1.0
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "DITHERED"
        except (AttributeError, TypeError):
            pass
    return m


world = bpy.data.worlds.new("Review")
scn.world = world
world.use_nodes = True
bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs["Color"].default_value = (0.30, 0.32, 0.35, 1)
bg.inputs["Strength"].default_value = 0.9

coll = bpy.data.collections.new("ReviewOnly")
scn.collection.children.link(coll)


def link(o):
    coll.objects.link(o)
    return o


bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
ground = bpy.context.active_object
ground.data.materials.append(mat_simple("M_Ground", (0.33, 0.34, 0.36), 0.9))

sun = bpy.data.lights.new("Key", "SUN")
sun.energy = 3.2
sun.angle = math.radians(8)
so = bpy.data.objects.new("Key", sun)
scn.collection.objects.link(so)
so.rotation_euler = (math.radians(50), 0, math.radians(-35))
fill = bpy.data.lights.new("Fill", "AREA")
fill.energy = 250
fill.size = 4
fo = bpy.data.objects.new("Fill", fill)
scn.collection.objects.link(fo)
fo.location = (3, -3, 2.5)
fo.rotation_euler = (math.radians(60), 0, math.radians(45))

cam_data = bpy.data.cameras.new("Cam")
cam = bpy.data.objects.new("Cam", cam_data)
scn.collection.objects.link(cam)
scn.camera = cam


def shoot(name, target, direction, dist, lens=50, ortho=None):
    direction = Vector(direction).normalized()
    cam.location = Vector(target) + direction * dist
    if direction.z > 0.999:
        cam.rotation_euler = (0.0, 0.0, 0.0)   # straight down, image up = +Y (rear)
    else:
        cam.rotation_euler = (-direction).to_track_quat("-Z", "Y").to_euler()
    if ortho:
        cam_data.type = "ORTHO"
        cam_data.ortho_scale = ortho
    else:
        cam_data.type = "PERSP"
        cam_data.lens = lens
    scn.render.filepath = os.path.join(PANELS, name + ".png")
    bpy.ops.render.render(write_still=True)


def bounds(objs):
    dg = bpy.context.evaluated_depsgraph_get()
    mn = Vector((1e9,) * 3)
    mx = Vector((-1e9,) * 3)
    for o in objs:
        if o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        for v in me.vertices:
            w = ev.matrix_world @ v.co
            mn = Vector(map(min, mn, w))
            mx = Vector(map(max, mx, w))
        ev.to_mesh_clear()
    return mn, mx


def import_fbx(path):
    before = set(O)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in O if o not in before]
    for o in new:
        for c in o.users_collection:
            c.objects.unlink(o)
        coll.objects.link(o)
    return new


def set_visible(objs, flag):
    for o in objs:
        o.hide_render = not flag


cooler_vis = [O["SM_PortableFridge_Body_LOD0"], O["SM_PortableFridge_Lid_LOD0"]]
mount_vis = [O["SM_PortableFridge_VanMount_LOD0"]]
mroot.location = (0, 0, 0)
set_visible(mount_vis, False)
bpy.context.view_layer.update()
C = Vector((0, 0, 0.21))

# ---------------------------------------------------------------- 01 closed
shoot("p01_front", C, (0, -1, 0.18), 1.9, 60)
shoot("p01_threequarter", C, (-0.75, -1, 0.65), 2.0, 60)
shoot("p01_back", C, (0.8, 1, 0.5), 2.0, 60)
shoot("p01_side", C, (1, -0.05, 0.12), 1.9, 60)
lod1 = [O["SM_PortableFridge_Body_LOD1"], O["SM_PortableFridge_Lid_LOD1"]]
set_visible(cooler_vis, False)
set_visible(lod1, True)
shoot("p01_lod1", C, (-0.75, -1, 0.65), 2.0, 60)
set_visible(lod1, False)
set_visible(cooler_vis, True)

# ---------------------------------------------------------------- 02 open + slot markers
set_lid(-95)
bpy.context.view_layer.update()
m_fill = mat_simple("M_SlotFill", (0.2, 0.85, 0.4), 0.5, emit=(0.05, 0.4, 0.15), alpha=0.35)
m_wire = mat_simple("M_SlotWire", (0.1, 1.0, 0.3), 0.5, emit=(0.1, 1.0, 0.3))
m_num = mat_simple("M_SlotNum", (1, 1, 1), 0.5, emit=(1, 1, 1))
m_dot = mat_simple("M_SlotDot", (1.0, 0.25, 0.1), 0.4, emit=(1.0, 0.2, 0.05))
markers = []
slots = sorted([o for o in O if o.name.startswith("SLOT_")], key=lambda o: o.name)
for s in slots:
    a = s.matrix_world.translation
    for kind, mat in (("fill", m_fill), ("wire", m_wire)):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(a.x, a.y, a.z + 0.075))
        b = bpy.context.active_object
        b.scale = (s["slot_box"][0] - 0.012, s["slot_box"][1] - 0.008, 0.15)
        b.data.materials.append(mat)
        if kind == "wire":
            wm = b.modifiers.new("w", "WIREFRAME")
            wm.thickness = 0.004
        markers.append(b)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.009, location=a)
    d = bpy.context.active_object
    d.data.materials.append(m_dot)
    markers.append(d)
    cu = bpy.data.curves.new("n" + s.name, "FONT")
    cu.body = str(int(s.name[-2:]))
    cu.size = 0.07
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.extrude = 0.002
    t = bpy.data.objects.new("num" + s.name, cu)
    scn.collection.objects.link(t)
    t.location = (a.x, a.y, a.z + 0.165)
    t.data.materials.append(m_num)
    markers.append(t)
shoot("p02_open_threequarter", Vector((0, 0.02, 0.2)), (-0.3, -0.5, 1.4), 1.95, 55)
shoot("p02_open_top", Vector((0, 0.05, 0.2)), (0, 0, 1), 2.0, 50, ortho=0.95)
set_visible(markers, False)

# fit check with the real item models
fit = []
items = []
for slot, label, path, keep in ITEMS:
    new = import_fbx(path)
    for o in new:  # heart/lungs FBX carry actions that would override the placement at render time
        if o.animation_data:
            o.animation_data_clear()
        if o.type == "ARMATURE":
            for pbn in o.pose.bones:
                pbn.location = (0, 0, 0)
                pbn.rotation_quaternion = (1, 0, 0, 0)
                pbn.rotation_euler = (0, 0, 0)
                pbn.scale = (1, 1, 1)
    meshes = [o for o in new if o.type == "MESH"]
    if keep:
        drop = [o for o in meshes if keep not in o.name]
        new = [o for o in new if o not in drop]
        for o in drop:
            bpy.data.objects.remove(o, do_unlink=True)
        meshes = [o for o in new if o.type == "MESH"]
    for o in meshes:
        if o.name.startswith("UCX_"):
            o.hide_render = True
    meshes = [o for o in meshes if not o.name.startswith("UCX_")]
    bpy.context.view_layer.update()
    mn, mx = bounds(meshes)
    sl = O["SLOT_%02d" % (slot or 6)]
    anchor = sl.matrix_world.translation
    off = Vector((anchor.x - (mn.x + mx.x) / 2, anchor.y - (mn.y + mx.y) / 2, anchor.z - mn.z))
    for o in new:
        if o.parent is None:
            o.location += off
    bpy.context.view_layer.update()
    mn, mx = bounds(meshes)
    size = mx - mn
    res = {"slot": slot, "item": label, "size_xyz": [round(v, 4) for v in size]}
    for cls, dep in (("thin", 0.090), ("wide", 0.172)):
        margin = [round(0.267 - size.x, 4), round(dep - size.y, 4), round(SLOT_H - size.z, 4)]
        res[cls] = {"margin_xyz_m": margin, "fits": all(m >= -0.002 for m in margin)}
    res["placed_slot_class"] = sl["slot_class"] if slot else None
    fit.append(res)
    if slot is None:
        for o in new:
            o.hide_render = True
    items += new
shoot("p02_fit_threequarter", Vector((0, 0.02, 0.2)), (-0.3, -0.5, 1.4), 1.95, 55)
if FIT:
    with open(FIT, "w", encoding="utf-8") as f:
        json.dump({"slot_box_thin_xyz": [0.267, 0.090, SLOT_H], "slot_box_wide_xyz": [0.267, 0.172, SLOT_H], "items": fit,
                   "note": "item bounds placed bottom-centre on each SLOT_ anchor; margin = slot - item (negative = overhang)"},
                  f, indent=1)
for o in items:
    o.hide_render = True
set_lid(0)

# ---------------------------------------------------------------- 03 carry reference
npc = import_fbx(NPC)
arm = next(o for o in npc if o.type == "ARMATURE")
for o in npc:  # the FBX carries an action that moves the rig; use the rest (T) pose
    if o.animation_data:
        o.animation_data_clear()
for b in arm.pose.bones:
    b.location = (0, 0, 0)
    b.rotation_quaternion = (1, 0, 0, 0)
    b.rotation_euler = (0, 0, 0)
    b.scale = (1, 1, 1)
npc_meshes = [o for o in npc if o.type == "MESH"]
bpy.context.view_layer.update()
nmn, nmx = bounds(npc_meshes)
height = nmx.z - nmn.z
# belly front at carry height
dg = bpy.context.evaluated_depsgraph_get()
belly = 0.0
for o in npc_meshes:
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    for v in me.vertices:
        w = ev.matrix_world @ v.co
        if 0.70 < w.z < 1.05 and abs(w.x) < 0.25:
            belly = min(belly, w.y)
    ev.to_mesh_clear()
pb = arm.pose.bones
sh = (arm.matrix_world @ pb["mixamorig:LeftArm"].head)
L = (pb["mixamorig:LeftArm"].bone.length + pb["mixamorig:LeftForeArm"].bone.length)
grip_half = 0.332
cmn, cmx = bounds(cooler_vis)
cy = belly - 0.012 - cmx.y                          # cooler centre y (hinge side touches the belly)
wrist_off = Vector((0.02, 0.05, 0.02))              # wrist behind/outside the bar so the palm sits on it
dx = grip_half + wrist_off.x - abs(sh.x)
dy = cy + wrist_off.y - sh.y
reach = 0.97 * L
dz = math.sqrt(max(reach ** 2 - dx ** 2 - dy ** 2, 0.0))
wrist_z = sh.z - dz
grip_z = wrist_z - wrist_off.z
carry_root_z = grip_z - 0.255
carry = {"npc_height": round(height, 3), "belly_y": round(belly, 3), "shoulder": [round(v, 3) for v in sh],
         "arm_chain": round(L, 3), "grip_z": round(grip_z, 3), "cooler_bottom_z": round(carry_root_z, 3)}
print("CARRY", json.dumps(carry))
with open(os.path.join(PANELS, "carry.json"), "w") as f:
    json.dump(carry, f)

root.location = (0, cy, carry_root_z)
for side, sx in (("Left", 1), ("Right", -1)):
    tgt = link(bpy.data.objects.new("IK_" + side, None))
    tgt.location = (sx * (grip_half + wrist_off.x), cy + wrist_off.y, wrist_z)
    pole = link(bpy.data.objects.new("Pole_" + side, None))
    pole.location = (sx * 0.75, 0.35, 0.75)
    c = pb["mixamorig:%sForeArm" % side].constraints.new("IK")
    c.target = tgt
    c.pole_target = pole
    c.pole_angle = math.radians(-90 if sx > 0 else -90)
    c.chain_count = 2
bpy.context.view_layer.update()
# second cooler on the ground beside the NPC (instanced copy of the closed LOD0 meshes)
ground_copies = []
for src in cooler_vis:
    cp = src.copy()
    cp.parent = None
    cp.matrix_world = Matrix.Translation((0.85, -0.15, 0)) @ (Matrix.Translation(-root.location) @ src.matrix_world)
    coll.objects.link(cp)
    ground_copies.append(cp)
bpy.context.view_layer.update()
mid = Vector((0.35, -0.2, height * 0.5))
shoot("p03_carry_front", mid, (-0.35, -1, 0.12), 4.3, 50)
shoot("p03_carry_side", Vector((0, -0.2, height * 0.5)), (-1, -0.12, 0.08), 4.0, 50)
for o in npc + ground_copies:
    o.hide_render = True
root.location = (0, 0, 0)

# ---------------------------------------------------------------- 04 van mount
set_visible(mount_vis, True)
wall_mat = mat_simple("M_VanWall", (0.62, 0.60, 0.55), 0.85)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, O["REF_WallPlane"].matrix_world.translation.y + 0.01, 0.6))
wall = bpy.context.active_object
wall.scale = (1.6, 0.02, 1.2)
wall.data.materials.append(wall_mat)
set_visible(cooler_vis, False)
shoot("p04_mount_empty", Vector((0, 0.05, 0.1)), (-0.6, -1, 0.7), 1.9, 55)
set_visible(cooler_vis, True)
root.location = (0, 0, 0.010)
set_lid(-95)
bpy.context.view_layer.update()
shoot("p04_mount_open", Vector((0, 0.05, 0.3)), (-0.75, -1, 0.55), 2.3, 55)
shoot("p04_mount_side", Vector((0, 0.05, 0.35)), (1, 0.0, 0.1), 2.3, 55)
print("RENDER_DONE", PANELS)
