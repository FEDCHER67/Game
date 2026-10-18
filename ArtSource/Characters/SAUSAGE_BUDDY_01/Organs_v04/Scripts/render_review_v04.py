"""Review renders for organs v04 / Patient_v04 / OperationAbdomen_v04 (Blender 5.2 Eevee, background).
Same scenes as render_review_v03.py; v04 adds --tag (suffix for the tile names, used for the v03d BEFORE renders), a
lower dissection window and the rim close-up tile.

blender -b ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend --python render_review_v04.py -- --out <dir>
        [--organs <Organs_v03.blend>] [--abdomen <OperationAbdomen_v03.blend>] [--patient <SAUSAGE_BUDDY_PATIENT_v03.blend>]
        [--layout <ORGANS_LAYOUT_v03.json>] [--only name,name]
Nothing is saved. Review-only tricks: the posed body gets a boolean hole where Unity uses the ABDOMEN_MASK stencil; the
"open torso" views cut a dissection window into a copy of the body; the "flipped patient" views emulate the Unity
stencil per face (a face of a stencil-tested material is hidden when the camera ray through it crosses ABDOMEN_MASK).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

REPO = Path(r"C:/Dev/Game")
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def arg(name, default):
    return Path(ARGS[ARGS.index(name) + 1]) if name in ARGS else default


OUT = arg("--out", REPO / "Working/Reviews/Operations/organs_v04/tiles")
ORGANS = arg("--organs", REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/Organs_v04.blend")
ABD = arg("--abdomen", REPO / "ArtSource/Props/TABLE-ASTRA-001/v04/OperationAbdomen_v04.blend")
PATIENT = arg("--patient", REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v04/SAUSAGE_BUDDY_PATIENT_v04.blend")
LAYOUT = json.loads(arg("--layout", REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v04/ORGANS_LAYOUT_v04.json").read_text(encoding="utf-8"))
TAG = ARGS[ARGS.index("--tag") + 1] if "--tag" in ARGS else ""
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
OUT.mkdir(parents=True, exist_ok=True)
T = Matrix(LAYOUT["table_rest_transform_rest_to_table_blender"])
sc = bpy.context.scene


def want(name):
    return ONLY is None or name in ONLY


# --------------------------------------------------------------------------------------------- scene setup
def setup():
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.view_settings.view_transform = "Standard"
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("W")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.62, 0.68, 0.72, 1)
    bg.inputs["Strength"].default_value = 0.6
    for name, rot, e, ang in (("Key", (math.radians(28), 0, math.radians(25)), 3.0, 8),
                              ("Fill", (math.radians(60), 0, math.radians(-150)), 0.9, 20)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = e
        ld.angle = math.radians(ang)
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        sc.collection.objects.link(lo)
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def flat_mat(name, rgb, rough=0.6, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if alpha < 1:
        b.inputs["Alpha"].default_value = alpha
        try:
            m.surface_render_method = "BLENDED"
        except AttributeError:
            pass
    return m


def inner_lining(mat, rgb=(0.32, 0.07, 0.10)):
    """Make a skin material show a dark cavity colour on back faces (the inside of a cut body)."""
    m = mat.copy()
    nt = m.node_tree
    out = next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL")
    surf = out.inputs["Surface"].links[0].from_socket
    geo = nt.nodes.new("ShaderNodeNewGeometry")
    dark = nt.nodes.new("ShaderNodeBsdfPrincipled")
    dark.inputs["Base Color"].default_value = (*rgb, 1)
    dark.inputs["Roughness"].default_value = 0.5
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(geo.outputs["Backfacing"], mix.inputs["Fac"])
    nt.links.new(surf, mix.inputs[1])
    nt.links.new(dark.outputs["BSDF"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])
    return m


def append(path, filt):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if filt(n)]
    objs = [o for o in dst.objects if o is not None]
    coll = bpy.data.collections.new("APPENDED_" + Path(path).stem)
    sc.collection.children.link(coll)
    linked = set()
    for o in objs:
        p = o
        while p is not None and p.name not in linked:
            coll.objects.link(p)
            linked.add(p.name)
            p = p.parent
    bpy.context.view_layer.update()
    return {o.name.split(".")[0]: o for o in objs}, coll


def bake_world(objs, M=Matrix.Identity(4)):
    """Unparent, keeping (M @ current world) as the new world matrix."""
    bpy.context.view_layer.update()
    mws = {o.name: M @ o.matrix_world.copy() for o in objs}
    for o in objs:
        o.parent = None
    for o in objs:
        o.matrix_world = mws[o.name]
    bpy.context.view_layer.update()


def shoot(cam, name, loc, target, lens=None, fov_v=None, up=(0, 0, 1), res=(1280, 960), ortho=None, clip=(0.01, 50)):
    if not want(name):
        return
    sc.render.resolution_x, sc.render.resolution_y = res
    fwd = (Vector(target) - Vector(loc)).normalized()
    x = fwd.cross(Vector(up)).normalized()
    y = x.cross(fwd)
    cam.matrix_world = Matrix.Translation(loc) @ Matrix((x, y, -fwd)).transposed().to_4x4()
    cd = cam.data
    cd.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        cd.ortho_scale = ortho
    if fov_v:
        cd.sensor_fit = "VERTICAL"
        cd.angle = math.radians(fov_v)
    elif lens:
        cd.sensor_fit = "AUTO"
        cd.lens = lens
    cd.clip_start, cd.clip_end = clip
    sc.render.filepath = str(OUT / f"{name}{TAG}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath, flush=True)


def cavity_cutter(opening, lift=0.03, grow=0.003):
    bm = bmesh.new()
    bm.from_mesh(opening.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == 0], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    ext = bmesh.ops.extrude_edge_only(bm, edges=[e for e in bm.edges if e.is_boundary])
    for v in [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]:
        v.co.z += lift
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for v in bm.verts:
        v.co += v.normal * grow
    me = bpy.data.meshes.new("HoleCutter")
    bm.to_mesh(me)
    bm.free()
    c = bpy.data.objects.new("HoleCutter", me)
    sc.collection.objects.link(c)
    c.matrix_world = opening.matrix_world
    c.hide_render = c.hide_viewport = True
    return c


def boolean_copy(body, cutters, name):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    ob.matrix_world = body.matrix_world
    for c in cutters:
        m = ob.modifiers.new("Cut", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = c
        m.use_self = True
        m.use_hole_tolerant = True
        m.material_mode = "TRANSFER"
    return ob


# --------------------------------------------------------------------------------------------- A. lying patient, op camera
def scene_table(cam):
    abd, _ = append(ABD, lambda n: n.startswith(("ABDOMEN_", "CORD_")))
    abd["ABDOMEN_MASK"].hide_render = True
    org, _ = append(ORGANS, lambda n: n.startswith(("ORGAN_", "RIB_", "STERNUM_", "SPINE_", "VESSELS_", "AIRWAY_", "DIAPHRAGM")))
    bake_world(list(org.values()), T)
    body = bpy.data.objects["Body"]
    cutter = cavity_cutter(abd["ABDOMEN_OPENING"])
    cut = boolean_copy(body, [cutter], "Body_Open")
    body.hide_render = body.hide_viewport = True
    c = Vector(LAYOUT["table_rest"]["INC_ABDOMEN"]["table_blender"]["position"])
    # 01 = the v04/v02 operation camera (Unity cameraPosition (0.14, 2.03, 0.425), straight down, FOV 50)
    shoot(cam, "01_operation_camera", (-0.14, -0.425, 2.03), (-0.14, -0.425, 0.89), fov_v=50, up=(0, -1, 0), res=(1920, 1080))
    shoot(cam, "02_opening_top_close", (c.x, c.y - 0.03, c.z + 0.55), (c.x, c.y - 0.03, c.z), lens=50, up=(0, -1, 0), res=(1280, 1100))
    shoot(cam, "03_three_quarter", (c.x + 0.62, c.y + 0.50, c.z + 0.58), (c.x, c.y - 0.05, c.z - 0.06), lens=50)
    # rim close-ups: across the body at the patient's right rim (cut layers + skin lip), and the chest end of the rim
    shoot(cam, "15_rim_closeup", (c.x - 0.06, c.y + 0.02, c.z + 0.20), (c.x + 0.115, c.y - 0.02, c.z - 0.012), lens=45, res=(1280, 960))
    shoot(cam, "16_rim_chest_end", (c.x + 0.02, c.y + 0.20, c.z + 0.30), (c.x, c.y - 0.12, c.z - 0.02), lens=45, res=(1280, 960))
    # 04: chest under the skin (skin semi-transparent): what the operation camera could see of a future chest opening
    if want("04_chest_xray"):
        ghost = flat_mat("GhostSkin", (0.93, 0.62, 0.46), 0.5, alpha=0.30)
        mats = list(cut.data.materials)
        for i, m in enumerate(mats):
            if m and m.name.startswith("Buddy_Skin"):
                cut.data.materials[i] = ghost
        shoot(cam, "04_chest_xray", (c.x, c.y - 0.12, c.z + 0.62), (c.x, c.y - 0.12, c.z), lens=45, up=(0, -1, 0), res=(1280, 1100))
        for i, m in enumerate(mats):
            cut.data.materials[i] = m


# --------------------------------------------------------------------------------------------- B. standing patient v03
def load_patient_v03():
    with bpy.data.libraries.load(str(PATIENT), link=False) as (src, dst):
        dst.objects = ["Body", "Face", "Shorts", "Buddy_Rig_Mixamo65"]
    coll = bpy.data.collections.new("PATIENT_v03")
    sc.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    rig = next(o for o in dst.objects if o.type == "ARMATURE")
    if rig.animation_data:
        rig.animation_data.action = None
    rig.data.pose_position = "POSE"
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    # review only: arms down (the rest pose is a T-pose), rotating each upper arm about the world Y axis at the shoulder
    pose_arm(rig, "Left", 72)
    pose_arm(rig, "Right", -72)
    return {o.name.split(".")[0]: o for o in dst.objects}, coll


def pose_arm(rig, side, ang):
    pb = rig.pose.bones["mixamorig:" + side + "Arm"]
    head = pb.bone.head_local
    R = Matrix.Translation(head) @ Matrix.Rotation(math.radians(ang), 4, "Y") @ Matrix.Translation(-head)
    pb.matrix = R @ pb.bone.matrix_local
    bpy.context.view_layer.update()


def scene_standing(cam):
    """All of scene A is hidden; the v03 patient stands in its rest frame at x = 3 m so both scenes share the file."""
    for o in list(sc.objects):
        if o.type in ("MESH", "EMPTY", "ARMATURE"):
            o.hide_render = True
    off = Matrix.Translation((3.0, 0, 0))
    pt, pcoll = load_patient_v03()
    root = bpy.data.objects.new("PatientRoot", None)
    sc.collection.objects.link(root)
    root.matrix_world = off
    pt["Buddy_Rig_Mixamo65"].parent = root
    for o in pt.values():
        o.hide_render = False
    org, _ = append(ORGANS, lambda n: n.startswith(("ORGAN_", "RIB_", "STERNUM_", "SPINE_", "VESSELS_", "AIRWAY_", "DIAPHRAGM")))
    bake_world(list(org.values()), off)
    abd, _ = append(ABD, lambda n: n.startswith(("ABDOMEN_", "CORD_")))
    bake_world(list(abd.values()), off @ T.inverted())
    for o in list(org.values()) + list(abd.values()):
        o.hide_render = False
    abd["ABDOMEN_MASK"].hide_render = True
    bpy.context.view_layer.update()
    body = pt["Body"]
    return pt, org, abd, body, off


def dissection(body, off, kind="front"):
    """Copy of the body with a dissection window (front: chest + belly wall; side: the patient's left flank). The
    boolean's cut walls are deleted so the window shows the body's own inside (dark lining on back faces)."""
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        if kind == "front":
            v.co = Vector((v.co.x * 0.27, v.co.y * 0.20 - 0.10 - 0.045, v.co.z * 0.33 + 0.975))
        else:
            v.co = Vector((v.co.x * 0.20 + 0.10 + 0.055, v.co.y * 0.26 - 0.005, v.co.z * 0.33 + 0.975))
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.03, segments=4, affect="EDGES")
    me = bpy.data.meshes.new("Window")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(flat_mat("WindowCut", (1, 0, 1)))
    win = bpy.data.objects.new("Window", me)
    sc.collection.objects.link(win)
    win.matrix_world = off
    win.hide_render = win.hide_viewport = True
    cut = boolean_copy(body, [win], "Body_Dissected_" + kind)
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(cut.evaluated_get(dg), depsgraph=dg)
    cut.modifiers.clear()
    cut.data = me2
    bm = bmesh.new()
    bm.from_mesh(me2)
    names = [m.name if m else "" for m in me2.materials]
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if names[f.material_index].startswith("WindowCut")], context="FACES")
    bm.to_mesh(me2)
    bm.free()
    for i, m in enumerate(list(me2.materials)):
        if m and m.name.startswith(("Buddy_Skin", "Patient_Skin")):
            me2.materials[i] = inner_lining(m)
    return cut


def stencil_emulation(body, mask, cam_loc, stencil_names, name):
    """Unity-like screen-space stencil from one camera: faces of stencil-tested materials whose camera ray crosses the
    ABDOMEN_MASK are removed (review copy only)."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    me.transform(body.matrix_world)
    mm = mask.data.copy()
    mm.transform(mask.matrix_world)
    mbvh = BVHTree.FromPolygons([v.co for v in mm.vertices], [p.vertices for p in mm.polygons])
    names = [m.name if m else "" for m in me.materials]
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = []
    cl = Vector(cam_loc)
    for f in bm.faces:
        if not any(names[f.material_index].startswith(s) for s in stencil_names):
            continue
        c = f.calc_center_median()
        d = (c - cl).normalized()
        if mbvh.ray_cast(cl, d, 50.0)[0] is not None:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    sc.collection.objects.link(ob)
    return ob, len(kill)


def scene_standing_views(cam):
    pt, org, abd, body, off = scene_standing(cam)
    o = off.translation
    # 05 front open torso (dissection window, all organs; the cavity asset hidden so the abdominal organs show)
    if want("05_front_open_torso") or want("05b_front_open_torso_no_ribs") or want("06_side_open_torso"):
        for n in ("ABDOMEN_OPENING", "ABDOMEN_INTESTINES"):
            abd[n].hide_render = True
        body.hide_render = True
        cut = dissection(body, off, "front")
        shoot(cam, "05_front_open_torso", o + Vector((0.0, -1.5, 0.98)), o + Vector((0.0, 0.0, 0.975)), lens=105, res=(1000, 1200))
        cage = [x for k, x in org.items() if k.startswith(("RIB_", "STERNUM_"))]
        for x in cage:
            x.hide_render = True
        shoot(cam, "05b_front_open_torso_no_ribs", o + Vector((0.0, -1.5, 1.01)), o + Vector((0.0, 0.0, 1.0)), lens=105, res=(1000, 1200))
        for x in cage:
            x.hide_render = False
        cut.hide_render = True
        pose_arm(pt["Buddy_Rig_Mixamo65"], "Left", -80)          # left arm raised out of the side view
        cut2 = dissection(body, off, "side")
        shoot(cam, "06_side_open_torso", o + Vector((1.5, -0.10, 0.98)), o + Vector((0.0, -0.005, 0.975)), lens=105, res=(1000, 1200))
        cut2.hide_render = True
        pose_arm(pt["Buddy_Rig_Mixamo65"], "Left", 72)
        body.hide_render = False
        for n in ("ABDOMEN_OPENING", "ABDOMEN_INTESTINES"):
            abd[n].hide_render = False
    # 07/08 flipped onto the belly, seen from above-behind: v02 behaviour (every Buddy_Skin face stencil-tested) vs v03
    if want("07_back_v02_bug") or want("08_back_v03_closed"):
        root = bpy.data.objects["PatientRoot"]
        # prone: rotate the standing patient +90 deg about X (front -> down, head -> -Y), belly resting on the floor
        flip = Matrix.Translation((3.0, 0, 0.13)) @ Matrix.Rotation(math.radians(90), 4, "X") @ Matrix.Translation((0, 0, -1.0))
        movers = [root] + list(org.values()) + list(abd.values())
        mws = {m.name: m.matrix_world.copy() for m in movers}
        R = flip @ off.inverted()
        for m in movers:
            if m is root:
                m.matrix_world = R @ mws[m.name]
            elif m.parent is None:
                m.matrix_world = R @ mws[m.name]
        bpy.context.view_layer.update()
        floor = bpy.data.meshes.new("Floor")
        floor.from_pydata([(-1, -2, 0), (5, -2, 0), (5, 2, 0), (-1, 2, 0)], [], [(0, 1, 2, 3)])
        floor.materials.append(flat_mat("FloorM", (0.45, 0.50, 0.55)))
        fo = bpy.data.objects.new("Floor", floor)
        sc.collection.objects.link(fo)
        cam_loc = Vector((3.35, -0.55, 1.05))
        target = Vector((3.0, 0.0, 0.10))
        body.hide_render = True
        mask = abd["ABDOMEN_MASK"]
        bug, n1 = stencil_emulation(body, mask, cam_loc, ["Buddy_Skin", "Patient_Skin_Closed"], "Body_v02_stencil")
        bug.hide_render = False
        shoot(cam, "07_back_v02_bug", cam_loc, target, lens=45, res=(1280, 960))
        bug.hide_render = True
        fixed, n2 = stencil_emulation(body, mask, cam_loc, ["Buddy_Skin"], "Body_v03_stencil")
        fixed.hide_render = False
        shoot(cam, "08_back_v03_closed", cam_loc, target, lens=45, res=(1280, 960))
        print("STENCIL faces hidden v02-like:", n1, "v03:", n2, flush=True)
        fixed.hide_render = True
        body.hide_render = False
        for m in movers:
            m.matrix_world = mws[m.name]
        bpy.data.objects.remove(fo, do_unlink=True)
        bpy.context.view_layer.update()
    # 09 stencil zone: Buddy_Skin (front zone, stencil-tested) vs Patient_Skin_Closed (never stencil-tested)
    if want("09_stencil_zone"):
        for oo in list(org.values()) + list(abd.values()):
            oo.hide_render = True
        mats = list(body.data.materials)
        zone = flat_mat("ZoneTint", (0.30, 0.80, 0.78), 0.5)
        for i, m in enumerate(mats):
            if m.name.split(".")[0] == "Buddy_Skin":
                body.data.materials[i] = zone
        shoot(cam, "09_stencil_zone", o + Vector((0.55, -1.25, 1.12)), o + Vector((0.0, 0.0, 1.0)), lens=60, res=(900, 1100))
        for i, m in enumerate(mats):
            body.data.materials[i] = m


# --------------------------------------------------------------------------------------------- C. studio: lineup, ribcage, heart
def scene_studio(cam):
    for o in list(sc.objects):
        if o.type in ("MESH", "EMPTY", "ARMATURE"):
            o.hide_render = True
    off = Vector((0, 6.0, 0))
    org, _ = append(ORGANS, lambda n: n.startswith(("ORGAN_", "RIB", "STERNUM_", "SPINE_", "VESSELS_", "AIRWAY_", "DIAPHRAGM",
                                                     "SOCKET_THORAX")))
    bpy.context.view_layer.update()
    for o in org.values():
        o.hide_render = True
    bg = bpy.data.meshes.new("Backdrop")
    bg.from_pydata([(-1, 0.4, -1), (1, 0.4, -1), (1, 0.4, 1), (-1, 0.4, 1)], [], [(0, 1, 2, 3)])
    bg.materials.append(flat_mat("BackdropM", (0.20, 0.22, 0.25), 0.8))
    bo = bpy.data.objects.new("Backdrop", bg)
    sc.collection.objects.link(bo)
    bo.matrix_world = Matrix.Translation(off)
    # 10 lineup at 1:1: each organ alone at identity orientation (its socket frame) rotated to stand up (local +Y up,
    # local +Z toward the camera at -Y)
    if want("10_lineup"):
        order = ["ORGAN_HEART", "ORGAN_LUNG_R", "ORGAN_LUNG_L", "ORGAN_LIVER", "ORGAN_KIDNEY_R", "ORGAN_KIDNEY_L"]
        x = -0.36
        place = {}
        stand = Matrix.Rotation(math.radians(90), 4, "X")       # local Y -> world Z, local Z -> world -Y (front to camera)
        for n in order:
            ob = org[n]
            ob.parent = None
            ob.hide_render = False
            mn = Vector((min(v.co.x for v in ob.data.vertices), min(v.co.y for v in ob.data.vertices), 0))
            mx = Vector((max(v.co.x for v in ob.data.vertices), max(v.co.y for v in ob.data.vertices), 0))
            w = mx.x - mn.x
            ob.matrix_world = Matrix.Translation(off + Vector((x - mn.x, 0, -mn.y))) @ stand
            place[n] = {"x_left": round(x, 4), "width": round(w, 4), "height": round(mx.y - mn.y, 4)}
            x += w + 0.03
        # 10 cm scale bar (alternating 1 cm blocks) on the ground line
        bm = bmesh.new()
        for k in range(10):
            v0 = bm.verts.new((k * 0.01, -0.001, -0.012))
            v1 = bm.verts.new(((k + 1) * 0.01, -0.001, -0.012))
            v2 = bm.verts.new(((k + 1) * 0.01, -0.001, -0.004))
            v3 = bm.verts.new((k * 0.01, -0.001, -0.004))
            f = bm.faces.new((v0, v1, v2, v3))
            f.material_index = k % 2
        me = bpy.data.meshes.new("ScaleBar")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(flat_mat("BarW", (0.95, 0.95, 0.95), 0.9))
        me.materials.append(flat_mat("BarK", (0.05, 0.05, 0.05), 0.9))
        bar = bpy.data.objects.new("ScaleBar", me)
        sc.collection.objects.link(bar)
        bar.matrix_world = Matrix.Translation(off + Vector((-0.36, -0.2, 0)))
        width = x - 0.03 + 0.36
        cx = -0.36 + width / 2
        ortho = width + 0.08
        shoot(cam, "10_lineup", off + Vector((cx, -2.0, 0.085)), off + Vector((cx, 0, 0.085)), ortho=ortho, res=(2000, 520))
        (OUT / "10_lineup_layout.json").write_text(json.dumps({"ortho_width_m": ortho, "centre_x": cx, "x0": -0.36,
                                                              "organs": place, "res": [2000, 520]}, indent=1))
        bar.hide_render = True
        for n in order:
            org[n].hide_render = True
    # 11 ribcage closed and opened (halves rotated about their hinges)
    th = org.get("SOCKET_THORAX")
    if th is not None and (want("11_ribcage_closed") or want("12_ribcage_open")):
        th.parent = None
        th.matrix_world = Matrix.Translation(off + Vector((0, 0, 0.12))) @ Matrix.Rotation(math.radians(90), 4, "X")
        bpy.context.view_layer.update()
        rib = [o for o in org.values() if o.name.startswith(("RIB_", "STERNUM_", "SPINE_"))]
        for o in rib:
            o.hide_render = False
        c = off + Vector((0, 0, 0.12))
        shoot(cam, "11_ribcage_closed", c + Vector((0.42, -0.62, 0.22)), c, lens=60, res=(1000, 1000))
        hl = org.get("RIBCAGE_HALF_L")
        hr = org.get("RIBCAGE_HALF_R")
        ang = math.radians(35)
        if hl and hr:
            bl, br = hl.matrix_basis.copy(), hr.matrix_basis.copy()
            hl.matrix_basis = bl @ Matrix.Rotation(ang, 4, "Y")
            hr.matrix_basis = br @ Matrix.Rotation(-ang, 4, "Y")
            bpy.context.view_layer.update()
            shoot(cam, "12_ribcage_open", c + Vector((0.30, -0.70, 0.30)), c, lens=60, res=(1000, 1000))
            hl.matrix_basis, hr.matrix_basis = bl, br
        for o in rib:
            o.hide_render = True


def scene_heart(cam):
    """Heart with its great vessels and lungs, in place (rest frame, offset), seen from the front-left and above."""
    for o in list(sc.objects):
        if o.type in ("MESH", "EMPTY", "ARMATURE"):
            o.hide_render = True
    off = Matrix.Translation((-3.0, 0, 0))
    org, _ = append(ORGANS, lambda n: n.startswith(("ORGAN_HEART", "ORGAN_LUNG", "VESSELS_", "AIRWAY_", "DIAPHRAGM", "SPINE_")))
    bake_world(list(org.values()), off)
    abd, _ = append(ABD, lambda n: n.startswith("ABDOMEN_VESSELS"))
    bake_world(list(abd.values()), off @ T.inverted())
    for o in list(org.values()) + list(abd.values()):
        o.hide_render = False
    h = off @ Vector(LAYOUT["organs"]["ORGAN_HEART"]["rest_socket"]["rest_position"])
    shoot(cam, "13_heart_vessels", h + Vector((0.16, -0.40, 0.10)), h + Vector((0.0, 0.0, 0.02)), lens=70, res=(1100, 1100))
    org["ORGAN_LUNG_L"].hide_render = True
    org["ORGAN_LUNG_R"].hide_render = True
    shoot(cam, "14_heart_vessels_nolungs", h + Vector((0.12, -0.36, 0.06)), h + Vector((0.0, 0.0, 0.0)), lens=70, res=(1100, 1100))


def main():
    cam = setup()
    if any(want(n) for n in ("01_operation_camera", "02_opening_top_close", "03_three_quarter", "04_chest_xray", "15_rim_closeup",
                             "16_rim_chest_end")):
        scene_table(cam)
    if any(want(n) for n in ("05_front_open_torso", "05b_front_open_torso_no_ribs", "06_side_open_torso", "07_back_v02_bug", "08_back_v03_closed", "09_stencil_zone")):
        scene_standing_views(cam)
    if any(want(n) for n in ("10_lineup", "11_ribcage_closed", "12_ribcage_open")):
        scene_studio(cam)
    if any(want(n) for n in ("13_heart_vessels", "14_heart_vessels_nolungs")):
        scene_heart(cam)


main()
