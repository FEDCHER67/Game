"""Blender review renders of the v02 operating-table package (Eevee). Writes v02/Previews/*.png (refuses overwrite).

blender -b TABLE-ASTRA-001_v02.blend --factory-startup --python render_review_v02.py
"""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

import bpy
from mathutils import Matrix, Vector

from v02_common import V02, refuse_overwrite

OUT = V02 / "Previews"
OUT.mkdir(exist_ok=True)
STAND_AT = (0.57, 0.29, 0.0)          # TrayAnchor, table-local Blender


def append_all(path, prefix=None):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = [n for n in src.objects if prefix is None or n.startswith(prefix)]
    for o in dst.objects:
        bpy.context.scene.collection.objects.link(o)
    return {o.name: o for o in dst.objects}


def setup():
    sc = bpy.context.scene
    for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
        try:
            sc.render.engine = eng
            break
        except TypeError:
            pass
    sc.render.resolution_x, sc.render.resolution_y = 1280, 860
    sc.view_settings.view_transform = "Standard"
    w = bpy.data.worlds.new("W") if not sc.world else sc.world
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.20, 0.23, 0.26, 1)
    bg.inputs["Strength"].default_value = 0.9
    for name, rot, e in (("Key", (math.radians(50), 0, math.radians(35)), 3.2),
                         ("Fill", (math.radians(65), 0, math.radians(-140)), 1.0)):
        ld = bpy.data.lights.new(name, "SUN")
        ld.energy = e
        lo = bpy.data.objects.new(name, ld)
        lo.rotation_euler = rot
        sc.collection.objects.link(lo)
    me = bpy.data.meshes.new("Floor")
    me.from_pydata([(-4, -4, 0), (4, -4, 0), (4, 4, 0), (-4, 4, 0)], [], [(0, 1, 2, 3)])
    fm = bpy.data.materials.new("Floor")
    fm.use_nodes = True
    next(n for n in fm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.32, 0.34, 0.36, 1)
    me.materials.append(fm)
    sc.collection.objects.link(bpy.data.objects.new("Floor", me))
    cd = bpy.data.cameras.new("Cam")
    cam = bpy.data.objects.new("Cam", cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def shot(sc, cam, name, loc, target, lens=35):
    path = OUT / f"{name}.png"
    refuse_overwrite(path)
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens
    sc.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    print("RENDERED", path, flush=True)


def set_open(deg):
    for o in bpy.data.objects:
        if o.name.startswith("STRAP_"):
            if "_closed" not in o:
                o["_closed"] = [list(r) for r in o.matrix_basis]
            o.matrix_basis = Matrix(o["_closed"]) @ Matrix.Rotation(math.radians(deg), 4, "X")
    bpy.context.view_layer.update()


def main():
    sc, cam = setup()
    stand = append_all(V02 / "InstrumentStand_v01.blend")
    stand["STAND_Root"].location = STAND_AT
    inc = append_all(V02 / "OperationIncisions_v01.blend", "INCISION_")
    for n, o in inc.items():
        o.hide_render = n in ("INCISION_KIDNEY_L_COVER", "INCISION_LIVER_COVER", "INCISION_KIDNEY_R_OPEN")
    set_open(0)
    shot(sc, cam, "v02_01_three_quarter_closed", (1.9, 1.6, 1.75), (0.1, 0.0, 0.62), 32)
    shot(sc, cam, "v02_02_side_right", (2.6, 0.0, 0.95), (0.1, 0.0, 0.62), 32)
    shot(sc, cam, "v02_03_table_camera", (1.2, -0.2, 1.65), (0.05, -0.05, 0.78), 30)
    shot(sc, cam, "v02_04_belly_closeup", (0.42, -0.05, 1.33), (0.02, -0.16, 0.88), 50)
    shot(sc, cam, "v02_05_head_pillow", (0.9, -1.25, 0.95), (0.0, -0.65, 0.76), 45)
    shot(sc, cam, "v02_06_hands_arm_strap", (0.85, -0.35, 0.98), (0.2, -0.03, 0.70), 45)
    shot(sc, cam, "v02_07_legs_heels", (0.75, 1.35, 0.95), (0.0, 0.66, 0.70), 40)
    shot(sc, cam, "v02_08_top", (0.0, 0.0001, 3.6), (0.0, 0.0, 0.6), 35)
    shot(sc, cam, "v02_09_left_back", (-1.9, -1.4, 1.6), (0.0, 0.0, 0.62), 32)
    set_open(120)
    shot(sc, cam, "v02_10_three_quarter_open", (1.9, 1.6, 1.75), (0.1, 0.0, 0.62), 32)
    shot(sc, cam, "v02_11_foot_end_open", (0.0, 2.3, 1.15), (0.0, 0.2, 0.7), 35)
    set_open(60)
    shot(sc, cam, "v02_12_half_open", (1.9, 1.6, 1.75), (0.1, 0.0, 0.62), 32)


main()
