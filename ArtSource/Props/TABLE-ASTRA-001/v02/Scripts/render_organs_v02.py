"""Review renders of the v02 organ layout and OperationAbdomen_v02 on the lying patient (Eevee, background).

blender -b ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend --python render_organs_v02.py -- --out <dir>

Nothing is saved back into the opened .blend. For the review only, a copy of the posed body has its belly faces inside
ABDOMEN_MASK removed (in Unity the stencil mask does this); organs come from the recoloured KIDNEY/LIVER sources and are
placed exactly by ORGANS_LAYOUT_v02.json.
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
from mathutils import Matrix, Vector

REPO = Path(r"C:/Dev/Game")
V02 = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02"
LAYOUT = json.loads((REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v02/ORGANS_LAYOUT_v02.json").read_text(encoding="utf-8"))
KIDNEY = REPO / "ArtSource/Props/KIDNEY-ASTRA-001/KIDNEY-ASTRA-001_recolour_v01.blend"
LIVER = REPO / "ArtSource/Props/LIVER-ASTRA-001/LIVER-ASTRA-001_recolour_v01.blend"
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = Path(ARGS[ARGS.index("--out") + 1]) if "--out" in ARGS else REPO / "Working/Reviews/Operations/organs_v02"
OUT.mkdir(parents=True, exist_ok=True)
ONLY = ARGS[ARGS.index("--only") + 1].split(",") if "--only" in ARGS else None
sc = bpy.context.scene


def marker(name):
    tb = LAYOUT["table_rest"][name]["table_blender"]
    r = Matrix((tb["x_axis"], tb["y_axis"], tb["z_axis"])).transposed()
    return Matrix.Translation(tb["position"]) @ r.to_4x4()


def append(path, names=None, prefix=None):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if (names is None or n in names) and (prefix is None or n.startswith(prefix))]
    for o in dst.objects:
        sc.collection.objects.link(o)
    return {o.name: o for o in dst.objects}


def setup():
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.view_settings.view_transform = "Standard"
    try:
        sc.eevee.use_shadows = True
    except AttributeError:
        pass
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
    me = bpy.data.meshes.new("Floor")
    me.from_pydata([(-5, -5, 0), (5, -5, 0), (5, 5, 0), (-5, 5, 0)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("FloorM")
    fm.use_nodes = True
    next(n for n in fm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.55, 0.60, 0.63, 1)
    me.materials.append(fm)
    sc.collection.objects.link(bpy.data.objects.new("Floor", me))
    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return cam


def flat_mat(name, rgb, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    return m


def cut_body(mask):
    """Evaluated copy of the posed Body with an exact hole under ABDOMEN_MASK (review only; Unity uses a stencil)."""
    body = bpy.data.objects["Body"]
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    cut = bpy.data.objects.new("Body_OpenedForReview", me)
    sc.collection.objects.link(cut)
    cut.matrix_world = body.matrix_world
    body.hide_render = True
    body.hide_viewport = True
    # cutter = the cavity volume: the opening's interior surface (cut face, wall, floor) closed by a lid 3 cm above
    opening = bpy.data.objects["ABDOMEN_OPENING"]
    bm = bmesh.new()
    bm.from_mesh(opening.data)
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index == 0], context="FACES")
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context="VERTS")
    edges = [e for e in bm.edges if e.is_boundary]
    ext = bmesh.ops.extrude_edge_only(bm, edges=edges)
    top = [g for g in ext["geom"] if isinstance(g, bmesh.types.BMVert)]
    for v in top:
        v.co.z += 0.03
    bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if e.is_boundary], sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    for v in bm.verts:                     # 3 mm larger than the cavity: the body's pocket hides behind the cavity wall
        v.co += v.normal * 0.003
    for f in bm.faces:
        f.material_index = 0
    cm = bpy.data.meshes.new("HoleCutter")
    bm.to_mesh(cm)
    bm.free()
    cm.materials.append(flat_mat("HoleWall", (0.30, 0.06, 0.10)))   # pocket faces, hidden behind the cavity wall
    cutter = bpy.data.objects.new("HoleCutter", cm)
    sc.collection.objects.link(cutter)
    cutter.matrix_world = opening.matrix_world
    cutter.hide_render = True
    cutter.hide_viewport = True
    mod = cut.modifiers.new("Hole", "BOOLEAN")
    mod.operation = "DIFFERENCE"
    mod.solver = "EXACT"
    mod.object = cutter
    mod.use_self = True
    mod.use_hole_tolerant = True
    mod.material_mode = "TRANSFER"
    bpy.context.view_layer.update()
    ev = cut.evaluated_get(bpy.context.evaluated_depsgraph_get())
    return cut, len(me.polygons) - len(ev.data.polygons)


def section_on(objs_caps, point, normal):
    """Boolean half-space cut (side +normal removed) with a coloured cap per object."""
    mods = []
    for ob, rgb in objs_caps:
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=2.0)
        me = bpy.data.meshes.new("SectionBox")
        bm.to_mesh(me)
        bm.free()
        me.materials.append(flat_mat("Cap_" + ob.name, rgb, 0.8))
        box = bpy.data.objects.new("SectionBox_" + ob.name, me)
        sc.collection.objects.link(box)
        nrm = Vector(normal).normalized()
        box.matrix_world = Matrix.Translation(Vector(point) + nrm * 1.0) @ nrm.to_track_quat("Z", "Y").to_matrix().to_4x4()
        box.hide_render = True
        box.hide_viewport = True
        m = ob.modifiers.new("Section", "BOOLEAN")
        m.operation = "DIFFERENCE"
        m.solver = "EXACT"
        m.object = box
        m.use_self = ob.name.startswith("Body")
        m.use_hole_tolerant = True
        m.material_mode = "TRANSFER"
        mods.append((ob, m, box))
    return mods


def section_off(mods):
    for ob, m, box in mods:
        ob.modifiers.remove(m)
        bpy.data.objects.remove(box, do_unlink=True)


def place_organs():
    out = {}
    kid = append(KIDNEY)
    liv = append(LIVER)
    for o in list(kid.values()) + list(liv.values()):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    pairs = {"INC_KIDNEY_L": next(o for o in bpy.data.objects if o.name.startswith("R_Kidney")),
             "INC_KIDNEY_R": next(o for o in bpy.data.objects if o.name.startswith("L_Kidney")),
             "INC_LIVER": next(o for o in bpy.data.objects if o.name.startswith("LIVER-ASTRA"))}
    for name, ob in pairs.items():
        e = LAYOUT["organs"][name]
        s = e["model_scale_xyz"]
        S = Matrix.Diagonal((s[0], s[1], s[2], 1.0))
        ob.matrix_world = marker(name) @ Matrix.Rotation(math.radians(-90), 4, "X") @ S @ Matrix.Translation(-Vector(e["model_centre_offset"]))
        ob.name = "ORGAN_" + name[4:]
        out[name] = ob
    return out


def guide_overlay(abd_mw):
    """Teal review overlay: the midline cut guide (dashes on the skin) and the suggested liver loop."""
    mat = bpy.data.materials.new("Overlay")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        if n.type == "BSDF_PRINCIPLED":
            nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.25, 0.95, 0.85, 1)
    em.inputs["Strength"].default_value = 1.6
    nt.links.new(em.outputs[0], next(n for n in nt.nodes if n.type == "OUTPUT_MATERIAL").inputs[0])
    objs = []
    lp = LAYOUT["organs"]["INC_LIVER"]["loop"]
    cx, cy, cz = lp["centre_marker_local_blender"]
    rx, ry = lp["radius_xy_m"]
    bm = bmesh.new()
    for i in range(36):
        a0, a1 = 2 * math.pi * (i + 0.15) / 36, 2 * math.pi * (i + 0.75) / 36
        p0 = Vector((cx + rx * math.sin(a0), cy + ry * math.cos(a0), cz))
        p1 = Vector((cx + rx * math.sin(a1), cy + ry * math.cos(a1), cz))
        d = (p1 - p0)
        nx = Vector((-d.y, d.x, 0)).normalized() * 0.0024
        bm.faces.new([bm.verts.new(v) for v in (p0 - nx, p1 - nx, p1 + nx, p0 + nx)])
    me = bpy.data.meshes.new("LiverLoopGuide")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new("LiverLoopGuide", me)
    sc.collection.objects.link(ob)
    ob.matrix_world = marker("INC_LIVER")
    objs.append(ob)
    g = LAYOUT["guide"]
    a, b = Vector(g["abdomen_local_start"]), Vector(g["abdomen_local_end"])
    bm = bmesh.new()
    for i in range(16):
        p0, p1 = a.lerp(b, (i + 0.15) / 16), a.lerp(b, (i + 0.75) / 16)
        for p in (p0, p1):
            p.z = 0.010
        bm.faces.new([bm.verts.new(v) for v in (p0 + Vector((-0.0024, 0, 0)), p1 + Vector((-0.0024, 0, 0)),
                                                 p1 + Vector((0.0024, 0, 0)), p0 + Vector((0.0024, 0, 0)))])
    me = bpy.data.meshes.new("BellyGuide")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat)
    ob = bpy.data.objects.new("BellyGuide", me)
    sc.collection.objects.link(ob)
    ob.matrix_world = abd_mw
    objs.append(ob)
    # snip points on the cords (small teal spheres)
    for kid in ("INC_KIDNEY_L", "INC_KIDNEY_R"):
        for cd in LAYOUT["organs"][kid]["cords"].values():
            s = Vector(cd["table_blender_start"]).lerp(Vector(cd["table_blender_end"]), 0.5)
            bm = bmesh.new()
            bmesh.ops.create_uvsphere(bm, u_segments=12, v_segments=8, radius=0.0065)
            me = bpy.data.meshes.new("Snip")
            bm.to_mesh(me)
            bm.free()
            me.materials.append(mat)
            o = bpy.data.objects.new("SnipPoint", me)
            sc.collection.objects.link(o)
            o.location = s
            objs.append(o)
    return objs


def shoot(cam, name, loc, target, lens=None, fov_v=None, up=(0, 0, 1), res=(1280, 960), ortho=None, clip=(0.01, 50)):
    if ONLY and name not in ONLY:
        return
    sc.render.resolution_x, sc.render.resolution_y = res
    cam.location = loc
    fwd = (Vector(target) - Vector(loc)).normalized()
    upv = Vector(up)
    x = fwd.cross(upv).normalized()
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
    sc.render.filepath = str(OUT / f"{name}.png")
    bpy.ops.render.render(write_still=True)
    print("RENDERED", sc.render.filepath, flush=True)


def main():
    cam = setup()
    abd = append(V02 / "OperationAbdomen_v02.blend", prefix="ABDOMEN_")
    cords = append(V02 / "OperationAbdomen_v02.blend", prefix="CORD_")
    mask = abd["ABDOMEN_MASK"]
    mask.hide_render = True
    cut, killed = cut_body(mask)
    print("review body polygon count change after the boolean hole:", -killed)
    organs = place_organs()
    abd_mw = marker("INC_ABDOMEN")
    lv = Vector(LAYOUT["table_rest"]["INC_LIVER"]["table_blender"]["position"])

    # 1. operation camera = Unity OperationStage1_v02 cameraPosition (0.14, 2.03, 0.425) -> Blender (-0.14, -0.425, 2.03),
    #    straight down, screen up toward the head (-Y), vertical FOV 50, 1920x1080 like the v04 screenshots.
    shoot(cam, "01_operation_camera", (-0.14, -0.425, 2.03), (-0.14, -0.425, 0.89), fov_v=50, up=(0, -1, 0), res=(1920, 1080))
    overlay = guide_overlay(abd_mw)
    shoot(cam, "02_operation_camera_guides", (-0.14, -0.425, 2.03), (-0.14, -0.425, 0.89), fov_v=50, up=(0, -1, 0), res=(1920, 1080))
    for o in overlay:
        o.hide_render = True
    c = abd_mw.translation
    # 3. close top view of the opening (camera straight down, a bit closer)
    shoot(cam, "03_opening_top_close", (c.x, c.y - 0.01, c.z + 0.55), (c.x, c.y - 0.01, c.z), lens=50, up=(0, -1, 0), res=(1280, 1100))
    # 4. 3/4 view from the patient's right side, foot end
    shoot(cam, "04_three_quarter", (c.x + 0.62, c.y + 0.55, c.z + 0.55), (c.x, c.y - 0.02, c.z - 0.06), lens=50)
    # 5. edge close-up: patient's right rim seen from across the body (shows the cut layers)
    shoot(cam, "05_edge_closeup", (c.x - 0.05, c.y + 0.06, c.z + 0.17), (c.x + 0.105, c.y + 0.02, c.z - 0.015), lens=50)
    # 6. interior close-up: into the cavity over the left kidney toward the spine
    k = Vector(LAYOUT["table_rest"]["INC_KIDNEY_L"]["table_blender"]["position"])
    shoot(cam, "06_interior_closeup", (k.x + 0.02, k.y + 0.20, k.z + 0.30), (k.x + 0.03, k.y - 0.01, k.z), lens=50)
    solids = [(cut, (0.93, 0.74, 0.62)), (organs["INC_LIVER"], (0.50, 0.16, 0.10)), (organs["INC_KIDNEY_R"], (0.62, 0.16, 0.24)),
              (organs["INC_KIDNEY_L"], (0.62, 0.16, 0.24)), (abd["ABDOMEN_INTESTINES"], (0.80, 0.50, 0.46)),
              (abd["ABDOMEN_VESSELS"], (0.55, 0.14, 0.20))] + [(o, (0.55, 0.14, 0.20)) for o in cords.values()]
    # 7. sagittal section through the right kidney and the liver (plane at table x = +0.078, patient's right side)
    xs = Vector(LAYOUT["table_rest"]["INC_KIDNEY_R"]["table_blender"]["position"]).x - 0.002
    mods = section_on(solids, (xs, 0, 0), (1, 0, 0))
    shoot(cam, "07_section_sagittal", (1.2, c.y + 0.0, c.z - 0.07), (0.0, c.y + 0.0, c.z - 0.07), up=(0, 0, 1),
          ortho=0.40, clip=(1.2 - xs - 0.0005, 5.0), res=(1280, 900))
    section_off(mods)
    # 8. axial section through the left kidney centre, seen from the head end
    mods = section_on(solids, (0, k.y, 0), (0, -1, 0))
    shoot(cam, "08_section_axial", (0.0, k.y - 1.2, c.z - 0.07), (0.0, k.y, c.z - 0.07), up=(0, 0, 1),
          ortho=0.40, clip=(1.2 - 0.0005, 5.0), res=(1280, 900))
    section_off(mods)
    # 9. whole patient 3/4 (context)
    shoot(cam, "09_patient_wide", (1.35, 1.05, 1.75), (0.0, -0.12, 0.78), lens=35)


main()
