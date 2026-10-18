"""Procedural stylised heart for the v03 organ set (organ-local frame: +X patient left, +Y head, +Z anterior).

Real adult heart ~12 x 8.5 x 6 cm; Buddy size factor 0.9 -> ~10.8 cm base-to-apex. The body is a smooth union of
ellipsoids (ventricle egg, right-ventricle bulge, both atria, auricles), ray-marched onto an icosphere, so it reads as a
soft glossy "jam" organ. Coronary vessels and a fat strip are swept along the surface. Short great-vessel stubs with cut
ends (dark lumen) stick out; the in-body VESSELS_* tubes start exactly at these stub ends (STUBS below).
"""
import math

import bmesh
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

import organs_v03_lib as L

# stub: (start inside the heart, end outside, radius, kind)  kind: 'artery' | 'vein'
STUBS = {
    "AORTA": ((0.002, 0.008, 0.002), (-0.001, 0.052, 0.006), 0.0098, "artery"),
    "PULMONARY_TRUNK": ((0.010, 0.008, 0.017), (0.017, 0.047, 0.012), 0.0094, "vein"),
    "SVC": ((-0.031, 0.026, 0.000), (-0.033, 0.058, -0.004), 0.0082, "vein"),
    "IVC": ((-0.026, 0.008, -0.008), (-0.028, -0.020, -0.016), 0.0090, "vein"),
    "PV_L_SUP": ((0.012, 0.028, -0.022), (0.046, 0.033, -0.026), 0.0050, "artery"),
    "PV_L_INF": ((0.012, 0.019, -0.024), (0.046, 0.015, -0.028), 0.0050, "artery"),
    "PV_R_SUP": ((0.000, 0.028, -0.026), (-0.042, 0.034, -0.032), 0.0050, "artery"),
    "PV_R_INF": ((0.000, 0.019, -0.027), (-0.042, 0.014, -0.034), 0.0050, "artery"),
}


BODY_TRIS = 2200
STUB_SLEEVE = 1.05


def _axis_rot(d, hint=(1, 0, 0)):
    d = np.asarray(d, float)
    d /= np.linalg.norm(d)
    e1 = np.asarray(hint, float) - d * np.dot(hint, d)
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    return np.array([e1, d, e2])          # rows: local x, local y (= axis), local z


def heart_sdf(p):
    # ventricle egg, long axis toward the apex (down, patient-left, a little forward)
    d = np.array([0.62, -1.0, 0.30])          # ~32 deg off vertical: the heart lies on the diaphragm
    d /= np.linalg.norm(d)
    cv = np.array([0.010, -0.010, 0.004])
    q = p - cv
    t = q @ d
    perp = q - t[:, None] * d
    e1 = np.array([1.0, 0, 0]) - d * d[0]
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(d, e1)
    a = np.where(t > 0, 0.050, 0.030)
    s = 1.0 - 0.40 * np.clip(t / 0.050, 0, 1) ** 1.3
    u = np.stack([t / a, (perp @ e1) / (0.034 * s), (perp @ e2) / (0.027 * s)], axis=1)
    f = (np.linalg.norm(u, axis=1) - 1.0) * 0.028
    # right ventricle bulge on the front-right
    f = L.smin(f, L.sd_ellipsoid(p, (-0.008, -0.004, 0.012), (0.024, 0.033, 0.019), _axis_rot((0.75, -1, 0.10))), 0.010)
    # atria and the base
    f = L.smin(f, L.sd_ellipsoid(p, (-0.031, 0.019, 0.000), (0.019, 0.023, 0.019)), 0.008)
    f = L.smin(f, L.sd_ellipsoid(p, (0.006, 0.024, -0.018), (0.026, 0.015, 0.016)), 0.008)
    f = L.smin(f, L.sd_ellipsoid(p, (-0.002, 0.018, 0.002), (0.026, 0.016, 0.020)), 0.010)
    # auricles (little ears at the top front)
    f = L.smin(f, L.sd_ellipsoid(p, (-0.026, 0.032, 0.016), (0.011, 0.008, 0.007), _axis_rot((0.3, 1, 0.6))), 0.005)
    f = L.smin(f, L.sd_ellipsoid(p, (0.030, 0.026, 0.013), (0.010, 0.007, 0.008), _axis_rot((-0.4, 1, 0.5))), 0.005)
    return f


def surface_path(bvh, pts, lift):
    """Project a rough path onto the heart surface (nearest point) and lift it along the normal."""
    out = []
    for p in L.resample(L.catmull(pts, 6), 0.005):
        loc, n, _, _ = bvh.find_nearest(Vector(p))
        out.append(loc + n * lift)
    return out


def build(mats):
    """mats: dict with 'muscle', 'fat', 'artery', 'vein', 'lumen'. Returns a bmesh in the heart-local frame,
    material order [muscle, fat, artery, vein, lumen]."""
    bm = L.sdf_surface(heart_sdf, (0.0, -0.004, 0.0), subdiv=5, rmax=0.12)
    L.relax(bm, 1, 0.3)
    bm = L.decimate_bm(bm, BODY_TRIS)
    bm.normal_update()
    for f in bm.faces:
        f.material_index = 0
        f.smooth = True
    bvh = BVHTree.FromBMesh(bm)

    # fat strip + coronary vessels in the anterior interventricular and right atrioventricular grooves
    anterior = [(0.006, 0.020, 0.030), (0.016, 0.000, 0.034), (0.028, -0.018, 0.030), (0.040, -0.034, 0.024), (0.048, -0.046, 0.016)]
    right_av = [(-0.006, 0.016, 0.030), (-0.024, 0.012, 0.026), (-0.040, 0.004, 0.012), (-0.044, -0.004, -0.006)]
    left_side = [(0.034, 0.014, 0.014), (0.050, -0.002, 0.006), (0.060, -0.020, -0.002), (0.058, -0.040, 0.000)]
    back = [(0.004, 0.004, -0.030), (0.020, -0.016, -0.030), (0.036, -0.034, -0.020)]
    for path, w in ((anterior, 0.0050), (right_av, 0.0046)):
        sp = surface_path(bvh, path, -0.0004)
        L.tube(bm, sp, w, segs=6, flat=0.38, mat=1, radius_fn=lambda i, n: 0.75 + 0.25 * math.sin(i * 1.3) ** 2)
    for path, kind, r in ((anterior, 2, 0.0021), (right_av, 2, 0.0020), (left_side, 3, 0.0018), (back, 3, 0.0018)):
        sp = surface_path(bvh, path, 0.0013 if kind == 2 else 0.0008)
        L.tube(bm, sp, r, segs=6, mat=kind)

    # great-vessel stubs with cut ends
    for name, (a, b, r, kind) in STUBS.items():
        a, b = Vector(a), Vector(b)
        path = L.resample([a, a.lerp(b, 0.5), b], 0.007)
        # the stub is a 5 % thicker sleeve, so the VESSELS_* tube that starts inside it never z-fights with it
        L.tube(bm, path, r * STUB_SLEEVE, segs=12, cap0="round", cap1="cut", mat=2 if kind == "artery" else 3, cap_mat=4, lumen=0.22)
    return bm


def stub_end(name):
    a, b, r, kind = STUBS[name]
    a, b = Vector(a), Vector(b)
    return b, (b - a).normalized(), r, kind
