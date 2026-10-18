"""v04 rib trim: pull the POSTERIOR tips of RIB_L/R_03 and RIB_L/R_04 inside the back skin, rebuild only their UCX pieces.

blender -b ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/Organs_v04.blend --python trim_back_ribs_v04.py [-- --dry <dir>]

After the v04 move the posterior tips of the G38 ribs 3-4 poked out of the back (rib 4 up to 4.6 mm). Each G38 rib is
32 rings x 10 vertices (ring 0 = posterior tip). The fix bends the tip inward: every ring is TRANSLATED (never scaled), so
the cross-section, thickness and style stay exactly G38's; the translation fades out along the rib (smooth bend) and is
solved until every vertex of the rib is >= 2 mm inside the trunk skin in rest AND in TABLE_REST.
Colliders: only UCX pieces whose ring range contains a moved ring are rebuilt, with G38's own recipe (convex hull of the
same ring range, organ trim at 3.15 mm in closed + opened-35 poses, G38 hull clean-up and <= 64 vertex budget), and checked
against the G38 contract: convex, <= 64 vertices, <= 2 mm outside the bone, <= 1 mm bone uncovered, >= 3 mm to organs
closed/open35, >= 8 mm between neighbouring ribs. Untouched pieces keep their v04 data.
Writes in place (v04 is not integrated yet): Organs_v04.blend, Organs_InBody_v04.fbx, FBX/RIBCAGE_v04.fbx,
G38_collisions_manifest_v04.json, organs_v04_build.json (rib entries), Patient_v04/ORGANS_LAYOUT_v04.json (rib entries).
"""
import json
import math
import sys
from pathlib import Path

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

HERE = Path(__file__).resolve().parent
REPO = Path(r"C:/Dev/Game")
G38 = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03/Scripts"
sys.path.insert(0, str(G38))
import g38_build_v03b as B  # noqa: E402  (G38 helpers: make_hull, trim_to_obstacles, create_collision, opened)
import g38_measure as M     # noqa: E402

OUT = HERE.parent
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
DRY = Path(ARGS[ARGS.index("--dry") + 1]) if "--dry" in ARGS else None
PATIENT = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v04/SAUSAGE_BUDDY_PATIENT_v04.blend"
TABLE_REST = REPO / "ArtSource/Props/TABLE-ASTRA-001/v02/Patient_TableRest_v01.blend"
LAYOUT = REPO / "ArtSource/Characters/SAUSAGE_BUDDY_01/Patient_v04/ORGANS_LAYOUT_v04.json"
RIBS = ("RIB_L_03", "RIB_R_03", "RIB_L_04", "RIB_R_04")
SHORTEN = {"RIB_L_04": 1, "RIB_R_04": 1}    # rib 4: its very tip ring sat 2.9 mm from the diaphragm when opened 35 deg
RING_RANGES_V03D = json.loads((REPO / "Working/Reviews/Operations/organs_v03/G38_work/colliders_v03d_01.json").read_text(encoding="utf-8"))["objects"]
TARGET = 0.0023          # >= 2 mm inside the skin, +0.3 mm for float noise
ORGAN_TARGET = 0.0034    # bone >= 3.4 mm from organs closed and open35 (UCX are trimmed at 3.15 mm)
FALLOFF = [1.0, 1.0, 0.95, 0.85, 0.7, 0.5, 0.3, 0.15, 0.05]
sc = bpy.context.scene
assert Path(bpy.data.filepath).name == "Organs_v04.blend"
REPORT = {}


def log(*a):
    print("[TRIM_v04]", *a, flush=True)


# ------------------------------------------------------------------------------------------------ trunk skin (two poses)
def trunk_mesh(path, posed):
    with bpy.data.libraries.load(str(path), link=False) as (src, dst):
        dst.objects = ["Body", "Buddy_Rig_Mixamo65"]
    coll = bpy.data.collections.new("_trunk")
    sc.collection.children.link(coll)
    for o in dst.objects:
        coll.objects.link(o)
    rig = next(o for o in dst.objects if o.type == "ARMATURE")
    if posed:
        sc.frame_set(1)
    else:
        rig.data.pose_position = "REST"
    bpy.context.view_layer.update()
    pb = rig.pose.bones["mixamorig:Spine"]
    T = rig.matrix_world @ pb.matrix @ pb.bone.matrix_local.inverted()
    body = next(o for o in dst.objects if o.type == "MESH")
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(body.evaluated_get(dg), depsgraph=dg)
    me.transform((T.inverted() if posed else Matrix.Identity(4)) @ body.matrix_world)
    for o in dst.objects:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.data.collections.remove(coll)
    for a in [a for a in bpy.data.actions if a.users == 0]:
        bpy.data.actions.remove(a)
    # biggest connected island = the trunk (the head capsule is a separate island that overlaps the chest)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen, best = set(), set()
    for v in bm.verts:
        if v.index in seen:
            continue
        stack, comp = [v], set()
        seen.add(v.index)
        while stack:
            x = stack.pop()
            comp.add(x)
            for e in x.link_edges:
                o = e.other_vert(x)
                if o.index not in seen:
                    seen.add(o.index)
                    stack.append(o)
        if len(comp) > len(best):
            best = comp
    faces = {f for x in best for f in x.link_faces}
    idx = {x.index: k for k, x in enumerate(best)}
    bvh = BVHTree.FromPolygons([x.co.copy() for x in best], [[idx[x.index] for x in f.verts] for f in faces])
    bm.free()
    bpy.data.meshes.remove(me)
    return bvh


def inside(bvh, p, ray=Vector((0.0123, 0.0071, 1.0)).normalized()):
    hits, o = 0, Vector(p)
    for _ in range(64):
        h = bvh.ray_cast(o + ray * 1e-5, ray)
        if h[0] is None:
            break
        hits += 1
        o = h[0]
    return hits % 2 == 1


def signed(bvh, p):
    """Signed distance to the skin (+ inside) and the direction that points from the skin into the body."""
    loc, nrm, _, d = bvh.find_nearest(p)
    ins = inside(bvh, p)
    if d > 1e-6:
        into = (p - loc).normalized() if ins else (loc - p).normalized()
    else:
        into = -nrm if not inside(bvh, loc + nrm * 1e-4) else nrm
    return (d if ins else -d), into


# ------------------------------------------------------------------------------------------------ bend solve
def rings_world(ob):
    mw = ob.matrix_world
    n = len(ob.data.vertices) // 10
    return [[mw @ v.co for v in ob.data.vertices[k * 10:(k + 1) * 10]] for k in range(n)]


def shorten(ob, r):
    """Remove the first r rings (posterior tip) and re-close the rib like G38's tip: the new first ring is tapered to
    0.78 of its section around its centre and capped with a triangulated 10-gon (bone material, smooth)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in range(10 * r)], context="VERTS")
    bm.verts.ensure_lookup_table()
    ring = [bm.verts[i] for i in range(10)]
    nxt = [bm.verts[i] for i in range(10, 20)]
    c0 = sum((v.co for v in ring), Vector()) / 10
    c1 = sum((v.co for v in nxt), Vector()) / 10
    for v in ring:
        v.co = c0 + (v.co - c0) * 0.78
    f = bm.faces.new(ring)
    f.normal_update()
    if f.normal.dot(c0 - c1) < 0:
        f.normal_flip()
    f.material_index = 0
    f.smooth = True
    bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="BEAUTY")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def ring_needs(rw, disp, skins, organs, opened_T):
    """Per ring: the worst constraint deficit and the direction that fixes it (closed-frame vectors).
    Skin: every vertex >= TARGET inside the trunk (rest and TABLE_REST). Organs: every vertex >= ORGAN_TARGET from every
    organ / vessel / airway / diaphragm surface, ribs closed and opened 35 deg (so the rebuilt UCX, trimmed at 3.15 mm,
    still covers the bone)."""
    rinv = opened_T.inverted().to_3x3()
    out = []
    for k in range(len(rw)):
        vec, worst_skin, worst_org = Vector(), 9.0, 9.0
        best_s, best_o = (0.0, None), (0.0, None)
        for p in rw[k]:
            q = p + disp[k]
            for bvh in skins:
                sd, into = signed(bvh, q)
                worst_skin = min(worst_skin, sd)
                if TARGET - sd > best_s[0]:
                    best_s = (TARGET - sd, into)
            for T, rot in ((None, None), (opened_T, rinv)):
                qq = q if T is None else T @ q
                for bvh in organs:
                    loc, nrm, _, d = bvh.find_nearest(qq)
                    if loc is None:
                        continue
                    ins = False      # unsigned: organ meshes are not all consistently oriented; G38 verified no containment
                    dd = d
                    worst_org = min(worst_org, dd)
                    if ORGAN_TARGET - dd > best_o[0]:
                        away = (qq - loc).normalized() if d > 1e-6 else nrm
                        if ins:
                            away = -away
                        best_o = (ORGAN_TARGET - dd, away if rot is None else rot @ away)
        if best_s[1] is not None:
            vec += best_s[1] * best_s[0]
        if best_o[1] is not None:
            vec += best_o[1] * best_o[0]
        out.append((vec, worst_skin, worst_org))
    return out


def solve_bend(ob, skins, organs, opened_T):
    rw = rings_world(ob)
    n = len(rw)
    disp = [Vector() for _ in range(n)]
    for it in range(40):
        st = ring_needs(rw, disp, skins, organs, opened_T)
        if all(v.length < 1e-6 for v, _, _ in st):
            break
        inc = []
        for j in range(n):
            d = Vector()
            for k in range(n):
                w = FALLOFF[abs(j - k)] if abs(j - k) < len(FALLOFF) else 0.0
                if w > 0 and st[k][0].length > 0 and (st[k][0] * w).length > d.length:
                    d = st[k][0] * w
            inc.append(d)
        for j in range(n):
            disp[j] += inc[j] * 0.8
    final = ring_needs(rw, disp, skins, organs, opened_T)
    return disp, [round(s * 1000, 2) for _, s, _ in final], [round(o * 1000, 2) for _, _, o in final], it


def estimate_outside(bm, bone, spacing=.001):
    """G38 cost: the largest outward bulge of a hull beyond the bone (sampled)."""
    import types
    verts, faces = B.hull_data(bm)
    mesh = types.SimpleNamespace(v=np.array([list(v) for v in verts], float), t=np.array(faces, int))
    best = 0.0
    for p in M.surface_samples(mesh, spacing):
        loc, nrm, _, d = bone.bvh.find_nearest(Vector(p))
        if d > best + 1e-6 and (Vector(p) - loc).dot(nrm) > 0:
            best = d
    return best


def shave_to_bone(bm, bone, ring_pts, limit=.00165, offset=.0015, rounds=12):
    """Clip a convex piece where it bulges more than `limit` beyond the bone: half-space at `offset` outside the nearest
    bone point, normal along the bulge. The bone stays inside (checked afterwards by the coverage test)."""
    import types
    cuts = 0
    for _ in range(rounds):
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
        verts, faces = B.hull_data(bm)
        mesh = types.SimpleNamespace(v=np.array([list(v) for v in verts], float), t=np.array(faces, int))
        worst = None
        for p in M.surface_samples(mesh, .001):
            q = Vector(p)
            loc, nrm, _, d = bone.bvh.find_nearest(q)
            if d > limit and (q - loc).dot(nrm) > 0 and (worst is None or d > worst[0]):
                worst = (d, loc, (q - loc).normalized())
        if worst is None:
            break
        d, loc, n = worst
        # never cut a bone vertex of this piece: the plane stays outside every ring vertex (so the bone faces between
        # them stay inside the convex piece as well)
        keep = max((p - loc).dot(n) for p in ring_pts) + 0.0001
        if not B.clip_halfspace(bm, loc + n * max(offset, keep), n):
            break
        cuts += 1
    return cuts


def partition(costs, count, last):
    """G38 partition: minimise the largest outward bulge, then the total squared bulge (ranges share end rings)."""
    states = {(0, 0): (0., 0., [])}
    for k in range(1, count + 1):
        for end in range(1, last + 1):
            options = []
            for start in range(max(0, end - 5), end):
                old = states.get((k - 1, start))
                if old is None or (start, end) not in costs:
                    continue
                value = costs[start, end]
                options.append((max(old[0], value), old[1] + value * value, old[2] + [(start, end)]))
            if options:
                states[k, end] = min(options, key=lambda r: (r[0], r[1]))
    return states[count, last]


# ------------------------------------------------------------------------------------------------ contract checks
def planes(ob, transform=None):
    mw = (transform or Matrix.Identity(4)) @ ob.matrix_world
    me = ob.data
    vs = np.array([list(mw @ v.co) for v in me.vertices])
    ns, ds = [], []
    for p in me.polygons:
        a, b, c = (vs[i] for i in p.vertices[:3])
        n = np.cross(b - a, c - a)
        ln = np.linalg.norm(n)
        if ln < 1e-14:
            continue
        n /= ln
        ns.append(n)
        ds.append(n @ a)
    return np.array(ns), np.array(ds)


def outside_bone_mm(part, bone_mesh, spacing=0.00025):
    worst, n = 0.0, 0
    pm = M.Mesh(part)
    for s in M.surface_samples(pm, spacing):
        n += 1
        loc, nrm, _, d = bone_mesh.bvh.find_nearest(Vector(s))
        if d > worst and (Vector(s) - loc).dot(nrm) > 0:
            worst = d
    return worst * 1000, n


def uncovered_mm(rib, parts, spacing=0.00025):
    bone = M.Mesh(rib)
    pl = [planes(p) for p in parts]
    pms = [M.Mesh(p) for p in parts]
    pts = np.array(list(M.surface_samples(bone, spacing)))
    covered = np.zeros(len(pts), bool)
    for ns, ds in pl:
        covered |= np.all(pts @ ns.T - ds <= 1e-6, axis=1)
    worst = 0.0
    for p in pts[~covered]:
        worst = max(worst, min(pm.bvh.find_nearest(Vector(p))[3] for pm in pms))
    return worst * 1000, int((~covered).sum()), len(pts)


def main():
    if DRY is not None:
        DRY.mkdir(parents=True, exist_ok=True)
    skins = [trunk_mesh(PATIENT, False), trunk_mesh(TABLE_REST, True)]
    anatomy = {o.name: M.Mesh(o) for o in bpy.data.objects if o.type == "MESH" and o.name.startswith(("ORGAN_", "VESSELS_", "DIAPHRAGM", "AIRWAY_"))}
    REPORT["before_worst_skin_mm"] = {}
    rebuilt = {}
    organs = [m.bvh for m in anatomy.values()]
    for name in RIBS:
        ob = bpy.data.objects[name]
        tag = name.split("_")[1]
        opened_T = B.opened(tag)
        before = ring_needs(rings_world(ob), [Vector()] * 32, skins, organs, opened_T)
        REPORT["before_worst_skin_mm"][name] = round(min(x[1] for x in before) * 1000, 2)
        REPORT.setdefault("before_worst_organ_mm", {})[name] = round(min(x[2] for x in before) * 1000, 2)
        r = SHORTEN.get(name, 0)
        if r:
            shorten(ob, r)
            bpy.context.view_layer.update()
        disp, skin_after, org_after, iters = solve_bend(ob, skins, organs, opened_T)
        moved = [k for k in range(len(disp)) if disp[k].length > 5e-5]
        inv3 = ob.matrix_world.inverted().to_3x3()
        for k in range(len(disp)):
            dl = inv3 @ disp[k]
            for v in ob.data.vertices[k * 10:(k + 1) * 10]:
                v.co += dl
        ob.data.update()
        REPORT.setdefault("bend", {})[name] = {"tip_rings_removed": r, "rings_moved": moved, "max_translation_mm": round(max(d.length for d in disp) * 1000, 2),
                                               "translation_mm_per_ring": [round(d.length * 1000, 2) for d in disp],
                                               "worst_skin_mm_after": min(skin_after), "worst_organ_mm_after_closed_open35": min(org_after),
                                               "iterations": iters}
        log(name, "skin before", REPORT["before_worst_skin_mm"][name], "after", min(skin_after), "| organ before",
            REPORT["before_worst_organ_mm"][name], "after", min(org_after), "| moved rings", moved, "max mm",
            REPORT["bend"][name]["max_translation_mm"], "iters", iters)
        assert min(skin_after) >= 2.0, (name, skin_after)
        # rebuild the UCX pieces over moved rings: re-partition that stretch (same piece count) with the G38 min-max bulge rule
        bpy.context.view_layer.update()
        rw = rings_world(ob)
        inv = ob.matrix_world.inverted()
        parts = RING_RANGES_V03D[name]["parts"]
        # old ring numbers: removed tip rings 0..r-1, moved ring k (new) = old k + r
        touched = set(range(r)) | {k + r for k in moved}
        aff = [p for p in parts if any(p["first_ring"] <= k <= p["last_ring"] for k in touched)]
        assert aff and aff[0]["first_ring"] == 0, aff
        E, K = aff[-1]["last_ring"] - r, len(aff)
        bone = M.Mesh(ob)
        costs = {}
        for a in range(E):
            for z in range(a + 1, min(a + 5, E) + 1):
                bm = B.make_hull([p for k in range(a, z + 1) for p in rw[k]])
                costs[a, z] = estimate_outside(bm, bone)
                bm.free()
        score, total, ranges = partition(costs, K, E)
        log(name, "re-partition rings 0..%d into %d pieces:" % (E, K), ranges, "coarse max bulge mm", round(score * 1000, 3))
        tmp = bpy.data.collections.new("_tmp_ucx")
        sc.collection.children.link(tmp)
        for part, (a, z) in zip(aff, ranges):
            bm = B.make_hull([p for k in range(a, z + 1) for p in rw[k]])
            shaved = shave_to_bone(bm, bone, [p for k in range(a, z + 1) for p in rw[k]])
            cuts, unresolved = B.trim_to_obstacles(bm, tag, {n: m.bvh for n, m in anatomy.items()}, margin=.00315)
            old = bpy.data.objects[part["name"]]
            new = B.create_collision(part["name"] + "_new", ob, bm, inv, tmp, 0 if a < 24 else 1)
            old_me = old.data
            old.data = new.data
            old.data.name = old.name
            old["part_material_index"] = 0 if a < 24 else 1
            bpy.data.objects.remove(new, do_unlink=True)
            bpy.data.meshes.remove(old_me)
            rebuilt[old.name] = {"rib": name, "rings": [a, z], "rings_v03d": [part["first_ring"], part["last_ring"]],
                                 "tip_rings_removed": r, "bulge_shave_cuts": shaved, "organ_cuts": cuts, "unresolved_cuts": unresolved}
        bpy.data.collections.remove(tmp)
    bpy.context.view_layer.update()
    log("rebuilt", sorted(rebuilt))

    # ---- contract checks on the rebuilt pieces (+ rib gaps and coverage of the four ribs)
    checks = {}
    for pname, info in rebuilt.items():
        part = bpy.data.objects[pname]
        rib = bpy.data.objects[info["rib"]]
        health = M.mesh_health(part)
        out_mm, samples = outside_bone_mm(part, M.Mesh(rib))
        tag = info["rib"].split("_")[1]
        dmin = {}
        for pose, T in (("closed", Matrix.Identity(4)), ("open35", B.opened(tag))):
            pm = M.Mesh(part, T)
            best = (9e9, None)
            for an, am in anatomy.items():
                d, hit = M.distance(pm, am, upper=best[0])
                if d < best[0]:
                    best = (d, an)
            dmin[pose] = {"organ_min_mm": round(best[0] * 1000, 3), "nearest_organ": best[1]}
        checks[pname] = dict(info, vertices=health["vertices"], triangles=health["triangles"], convex=health["convex"],
                             closed=health["nonmanifold_edges"] == 0 and health["components"] == 1,
                             outside_sample_max_mm=round(out_mm, 3), outside_certified_mm=round(out_mm + 0.25, 3), samples=samples,
                             clearance=dmin)
        log(pname, "verts", health["vertices"], "convex", health["convex"], "outside(cert) mm", round(out_mm + 0.25, 3),
            "organ closed", dmin["closed"], "open35", dmin["open35"])
    cover = {}
    for name in RIBS:
        rib = bpy.data.objects[name]
        parts = [o for o in rib.children if o.name.startswith("UCX_")]
        unc, n_unc, n = uncovered_mm(rib, parts)
        cover[name] = {"uncovered_sample_max_mm": round(unc, 3), "uncovered_certified_mm": round(unc + 0.25, 3), "uncovered_samples": n_unc,
                       "samples": n}
        log(name, "uncovered(cert) mm", round(unc + 0.25, 3))
    gaps = {}
    for tag in ("L", "R"):
        for a, b in (("02", "03"), ("03", "04")):
            pa = [M.Mesh(o) for o in bpy.data.objects[f"RIB_{tag}_{a}"].children if o.name.startswith("UCX_")]
            pb_ = [M.Mesh(o) for o in bpy.data.objects[f"RIB_{tag}_{b}"].children if o.name.startswith("UCX_")]
            best = 9e9
            for x in pa:
                for y in pb_:
                    best = min(best, M.distance(x, y, upper=best)[0])
            gaps[f"RIB_{tag}_{a} / RIB_{tag}_{b}"] = round(best * 1000, 3)
    log("rib gaps mm", gaps)
    ok = (all(c["convex"] and c["closed"] and c["vertices"] <= 64 and c["outside_certified_mm"] <= 2.0
              and c["clearance"]["closed"]["organ_min_mm"] >= 3.0 and c["clearance"]["open35"]["organ_min_mm"] >= 3.0
              and not c["unresolved_cuts"] for c in checks.values())
          and all(c["uncovered_certified_mm"] <= 1.0 for c in cover.values()) and all(g >= 8.0 for g in gaps.values()))
    REPORT.update({"rebuilt_parts": checks, "coverage": cover, "rib_gaps_mm": gaps, "contract_pass": ok})
    log("CONTRACT PASS" if ok else "CONTRACT FAIL")
    assert ok
    write_outputs(checks, skins)


def write_outputs(checks, skins):
    out = DRY or OUT
    # manifest: update the rebuilt pieces
    mpath = OUT / "G38_collisions_manifest_v04.json"
    m = json.loads(mpath.read_text(encoding="utf-8"))
    for tname, t in m["objects"].items():
        for part in t["ucx_parts"]:
            if part["name"] not in checks:
                continue
            ob = bpy.data.objects[part["name"]]
            c = checks[part["name"]]
            co = [v.co for v in ob.data.vertices]
            wc = [ob.matrix_world @ v for v in co]
            part.update({"vertex_count": c["vertices"], "triangle_count": c["triangles"],
                         "bounds_target_local_m": [[min(v[i] for v in co) for i in range(3)], [max(v[i] for v in co) for i in range(3)]],
                         "bounds_rest_world_m": [[min(v[i] for v in wc) for i in range(3)], [max(v[i] for v in wc) for i in range(3)]],
                         "fit": {"sample_max_outside_mm": c["outside_sample_max_mm"], "certified_upper_outside_mm": c["outside_certified_mm"],
                                 "grid_cover_radius_mm": 0.25, "samples": c["samples"], "pass_2mm": c["outside_certified_mm"] <= 2.0},
                         "clearance": {pose: dict(v) for pose, v in c["clearance"].items()},
                         "rebuilt_v04_rib_trim": {"rings": c["rings"], "organ_cuts": c["organ_cuts"]}})
    m["v04_rib_trim"] = {"what": "posterior tips of RIB_L/R_03 and RIB_L/R_04 bent inward (ring translations only) so the bone stays "
                                 ">= 2 mm inside the back skin in rest and TABLE_REST; only the UCX pieces over moved rings rebuilt "
                                 "with G38's recipe and re-checked against the G38 contract",
                         "bend": REPORT["bend"], "before_worst_skin_mm": REPORT["before_worst_skin_mm"],
                         "coverage": REPORT["coverage"], "rib_gaps_mm": REPORT["rib_gaps_mm"], "contract_pass": REPORT["contract_pass"]}
    allparts = [p for t in m["objects"].values() for p in t["ucx_parts"]]
    m["collision_results"]["min_organ_clearance_closed_mm"] = min(p["clearance"]["closed"]["organ_min_mm"] for p in allparts)
    m["collision_results"]["min_organ_clearance_open_mm"] = min(p["clearance"]["open35"]["organ_min_mm"] for p in allparts)
    m["collider_fit_results"]["maximum_outside_bound_mm"] = max(p["fit"]["certified_upper_outside_mm"] for p in allparts)
    (out / "G38_collisions_manifest_v04.json").write_text(json.dumps(m, indent=1), encoding="utf-8")
    # rib entries in organs_v04_build.json and ORGANS_LAYOUT_v04.json
    bpath = OUT / "organs_v04_build.json"
    b = json.loads(bpath.read_text(encoding="utf-8"))
    lay = json.loads(LAYOUT.read_text(encoding="utf-8"))
    for name in RIBS + tuple(checks):
        ob = bpy.data.objects[name]
        co = [v.co for v in ob.data.vertices]
        if name.startswith("UCX_"):
            b["objects"][name].update({"vertices": len(co), "tris": sum(len(p.vertices) - 2 for p in ob.data.polygons)})
            continue
        mn = [round(min(v[i] for v in co), 4) for i in range(3)]
        mx = [round(max(v[i] for v in co), 4) for i in range(3)]
        for d in (b["objects"][name], lay["ribcage"][name]):
            d.update({"local_bounds_min": mn, "local_bounds_max": mx, "size_m_xyz": [round(mx[i] - mn[i], 4) for i in range(3)],
                      "largest_dimension_m": round(max(mx[i] - mn[i] for i in range(3)), 4), "v04_rib_trim": REPORT["bend"][name]})
    b["v04_rib_trim"] = m["v04_rib_trim"]
    lay["v03d_to_v04"]["rib_trim"] = {"ribs": list(RIBS), "summary": "posterior tips bent inward >= 2 mm under the back skin; 12 UCX "
                                      "pieces rebuilt (G38 contract re-checked)", "contract_pass": REPORT["contract_pass"]}
    (out / "organs_v04_build.json").write_text(json.dumps(b, indent=1), encoding="utf-8")
    (out / "ORGANS_LAYOUT_v04.json" if DRY else LAYOUT).write_text(json.dumps(lay, indent=1), encoding="utf-8")
    # exports
    kw = dict(use_selection=True, object_types={"MESH", "EMPTY"}, axis_forward="-Z", axis_up="Y", apply_unit_scale=True,
              apply_scale_options="FBX_SCALE_UNITS", use_mesh_modifiers=False, bake_anim=False, add_leaf_bones=False,
              use_custom_props=True, mesh_smooth_type="FACE")

    def select(objs):
        bpy.ops.object.select_all(action="DESELECT")
        for o in objs:
            o.hide_set(False)
            o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]

    root = bpy.data.objects["ORGANS_v04_ROOT"]
    select([root] + list(root.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(out / "Organs_InBody_v04.fbx"), **kw)
    th = bpy.data.objects["SOCKET_THORAX"]
    mb = th.matrix_basis.copy()
    th.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    rc = bpy.data.objects["RIBCAGE"]
    (out / "FBX").mkdir(exist_ok=True)
    select([th, rc] + list(rc.children_recursive))
    bpy.ops.export_scene.fbx(filepath=str(out / "FBX" / "RIBCAGE_v04.fbx"), **kw)
    th.matrix_basis = mb
    bpy.context.view_layer.update()
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "Organs_v04.blend"), copy=True)
    (out / "trim_back_ribs_v04_report.json").write_text(json.dumps(REPORT, indent=1), encoding="utf-8")
    log("written to", out)


main()
