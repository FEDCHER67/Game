"""Shared helpers for the TABLE-ASTRA-001 v02 operating-table package (Blender 5.2, background mode).

All coordinates are TABLE-LOCAL Blender metres: RIG_Table_Root sits at the world origin with identity transform,
+Z up, the table head end is -Y, the foot end (push handle) is +Y. The lying patient's LEFT is table -X.
Unity (prefab-local) = (-x, z, -y) for points; see table_rest_contract_v01.json.
"""
import math
import sys
from pathlib import Path

import bpy
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

REPO = Path(r"C:/Dev/Game")
TABLE_DIR = REPO / "ArtSource/Props/TABLE-ASTRA-001"
V02 = TABLE_DIR / "v02"
TABLE_V01_BLEND = TABLE_DIR / "TABLE-ASTRA-001.blend"
TABLE_V02_BLEND = V02 / "TABLE-ASTRA-001_v02.blend"
PATIENT_BLEND = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.blend"
PATIENT_FBX = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v01/SAUSAGE_BUDDY_PATIENT_v01.fbx"
P = "mixamorig:"
RIG_NAME = "Buddy_Rig_Mixamo65"
PATIENT_MESHES = ("Body", "Face", "Shorts")
INC_NAMES = ("INC_KIDNEY_L", "INC_KIDNEY_R", "INC_LIVER")
TABLE_COLLECTIONS = ("TABLE_ASTRA_Geometry", "TABLE_ASTRA_Rig")

# Unity prefab-local <- Blender table-local (proper rotation conjugated with the X mirror of the FBX import).
C_B2U = Matrix(((-1, 0, 0), (0, 0, 1), (0, -1, 0)))


def log(*a):
    print("[V02]", *a, flush=True)


def clean_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.cameras, bpy.data.lights, bpy.data.actions,
                  bpy.data.armatures, bpy.data.images):
        for item in list(block):
            if item.users == 0:
                block.remove(item)


def ensure_collection(name, parent=None):
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        (parent or bpy.context.scene.collection).children.link(coll)
    return coll


def append_objects(blend_path, names, collection):
    """Append named objects (with their data) from a .blend into a collection; returns {name: object}."""
    with bpy.data.libraries.load(str(blend_path), link=False) as (src, dst):
        missing = [n for n in names if n not in src.objects]
        assert not missing, f"missing in {blend_path}: {missing}"
        dst.objects = list(names)
    out = {}
    for ob in dst.objects:
        collection.objects.link(ob)
        out[ob.name] = ob
    return out


def collection_object_names(blend_path, coll_names):
    with bpy.data.libraries.load(str(blend_path), link=False) as (src, dst):
        dst.collections = [c for c in coll_names if c in src.collections]
    names = []
    for coll in dst.collections:
        names += [o.name for o in coll.all_objects]
        bpy.data.collections.remove(coll)
    for ob in list(bpy.data.objects):
        if ob.users == 0:
            bpy.data.objects.remove(ob)
    return names


def load_table(blend_path=TABLE_V01_BLEND, collection_name="TABLE"):
    """Append the gurney (geometry + caster rig, no preview floor/lights/camera)."""
    coll = ensure_collection(collection_name)
    with bpy.data.libraries.load(str(blend_path), link=False) as (src, dst):
        dst.collections = [c for c in src.collections if c.startswith("TABLE_ASTRA_") and "Preview" not in c]
    objs = {}
    for c in dst.collections:
        coll.children.link(c)
        for ob in c.all_objects:
            objs[ob.name] = ob
    return objs


def load_patient(collection_name="PATIENT"):
    coll = ensure_collection(collection_name)
    objs = append_objects(PATIENT_BLEND, [RIG_NAME, *PATIENT_MESHES, *INC_NAMES], coll)
    rig = objs[RIG_NAME]
    if rig.animation_data:
        rig.animation_data.action = None
    for pb in rig.pose.bones:
        pb.matrix_basis.identity()
    return objs


def bvh_world(ob, depsgraph=None):
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(depsgraph)
    me = eo.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    eo.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, epsilon=0.0), verts, polys


def evaluated_world_verts(ob, depsgraph=None):
    depsgraph = depsgraph or bpy.context.evaluated_depsgraph_get()
    eo = ob.evaluated_get(depsgraph)
    me = eo.to_mesh()
    mw = ob.matrix_world
    verts = [mw @ v.co for v in me.vertices]
    eo.to_mesh_clear()
    return verts


def tri_count(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def q_axis(axis, deg):
    return Quaternion(Vector(axis).normalized(), math.radians(deg))


def rx(deg):
    return q_axis((1, 0, 0), deg)


def ry(deg):
    return q_axis((0, 1, 0), deg)


def rz(deg):
    return q_axis((0, 0, 1), deg)


def unity_pos(v):
    return [-v[0], v[2], -v[1]]


def unity_rot_matrix(m3):
    return C_B2U @ m3 @ C_B2U.transposed()


def unity_quat(m3):
    """Unity Quaternion (x, y, z, w) of a Blender table-local rotation matrix."""
    q = unity_rot_matrix(m3).to_quaternion()
    return [q.x, q.y, q.z, q.w]


def unity_euler(m3):
    """Unity Euler angles (degrees, Unity's ZXY order) of a Blender table-local rotation matrix."""
    r = unity_rot_matrix(m3)
    # Unity: R = Ry(y) * Rx(x) * Rz(z) (applied z, then x, then y); extract.
    sx = -r[1][2]
    sx = max(-1.0, min(1.0, sx))
    x = math.asin(sx)
    if abs(math.cos(x)) > 1e-6:
        y = math.atan2(r[0][2], r[2][2])
        z = math.atan2(r[1][0], r[1][1])
    else:
        y = math.atan2(-r[2][0], r[0][0])
        z = 0.0
    return [round(math.degrees(a) % 360.0, 4) for a in (x, y, z)]


def rnd(v, n=5):
    return [round(float(x), n) for x in v]


def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def make_material(name, rgba, rough=0.9, metal=0.0):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = rgba
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    mat.diffuse_color = rgba
    return mat


def refuse_overwrite(*paths):
    for p in paths:
        assert not Path(p).exists(), f"Refusing to overwrite {p}"


def argv_after_dashes():
    return sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
