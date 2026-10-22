"""Shared sub-assemblies for M2 props (statue figure, pallets, flowers, hedge)."""
import math
import bpy
from mathutils import Matrix, Vector

# ------------------------------------------------------------------ cartoon leader figure (skin modifier body)
_SKEL = [  # (x, y, z, rx, ry)  unit figure, ~0.97 tall, front = -Y, figure's right hand = -X (raised)
    (0, 0, .36, .13, .11), (0, -.025, .46, .19, .18), (0, 0, .57, .165, .135), (0, 0, .655, .07, .07),
    (-.075, 0, .34, .075, .075), (-.085, -.01, .19, .065, .065), (-.085, 0, .065, .055, .055), (-.09, -.085, .04, .05, .04),
    (.075, 0, .34, .075, .075), (.085, -.01, .19, .065, .065), (.085, 0, .065, .055, .055), (.09, -.085, .04, .05, .04),
    (-.15, 0, .6, .065, .065), (-.245, -.01, .705, .052, .052), (-.27, -.03, .855, .042, .042),
    (.15, 0, .6, .065, .065), (.215, -.05, .48, .05, .05), (.12, -.15, .445, .04, .04),
]
_EDGES = [(0, 1), (1, 2), (2, 3), (0, 4), (4, 5), (5, 6), (6, 7), (0, 8), (8, 9), (9, 10), (10, 11),
          (2, 12), (12, 13), (13, 14), (2, 15), (15, 16), (16, 17)]


def _skin_body(lod):
    me = bpy.data.meshes.new('tmp_skel')
    me.from_pydata([s[:3] for s in _SKEL], _EDGES, [])
    ob = bpy.data.objects.new('tmp_skel', me)
    bpy.context.scene.collection.objects.link(ob)
    sk = ob.modifiers.new('skin', 'SKIN')
    sk.use_smooth_shade = True
    for i, s in enumerate(_SKEL):
        d = me.skin_vertices[0].data[i]
        d.radius = (s[3], s[4])
        d.use_root = (i == 0)
    sub = ob.modifiers.new('sub', 'SUBSURF'); sub.levels = 1 if lod == 0 else 0; sub.render_levels = sub.levels
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), depsgraph=dg)
    bpy.data.objects.remove(ob); bpy.data.meshes.remove(me)
    return out


def figure(A, scale, loc=(0, 0, 0), col='gold', dark='gold_dark'):
    """Chubby cartoon leader in a suit, round glasses, hair tuft, right arm raised in a wave, left hand on the belly.
    Parody without likeness to any real person. ~0.97*scale tall, feet at loc, faces Blender -Y."""
    S = Matrix.Translation(Vector(loc)) @ Matrix.Diagonal((scale, scale, scale, 1))
    body = _skin_body(A.lod)
    A.add_mesh(body, col, S)
    bpy.data.meshes.remove(body)
    def P(x, y, z):
        return (loc[0] + x * scale, loc[1] + y * scale, loc[2] + z * scale)
    s = scale
    A.sphere(.138 * s, P(0, 0, .79), col, seg=16, rings=10, scale=(1, .95, 1.02))
    A.sphere(.032 * s, P(0, -.132, .775), col, seg=8, rings=6)                                   # nose
    for x in (-.135, .135):
        A.sphere(.032 * s, P(x, 0, .785), col, seg=8, rings=5, scale=(.6, 1, 1.1), detail=True)  # ears
    for x in (-.052, .052):
        A.torus(.042 * s, .008 * s, P(x, -.126, .805), dark, n=12, m=4, rot=(90, 0, 0))          # glasses
    A.beam(P(-.012, -.13, .808), P(.012, -.13, .808), .006 * s, dark, n=4)
    for x in (-.13, .13):
        A.beam(P(x * .72, -.125, .81), P(x, -.03, .81), .006 * s, dark, n=4, detail=True)
    A.sweep([P(-.05, -.105, .735), P(0, -.118, .722), P(.05, -.105, .735)], .007 * s, dark, n=4, detail=True)  # smile
    for k, (dx, dy, h, lean) in enumerate(((0, -.02, .1, -.04), (-.04, .01, .075, -.06), (.04, .01, .075, .05))):  # hair tuft
        A.lathe([(.035 * s, 0), (.03 * s, h * .5 * s), (.001 * s, h * s)], P(dx, dy, .9), col, n=8,
                rot=(math.degrees(lean) * 4, math.degrees(dx) * 6, 0))
    # right hand (raised, open) and left hand (on the belly)
    A.sphere(.05 * s, P(-.275, -.035, .915), col, seg=10, rings=6, scale=(1, .5, 1.15))
    A.beam(P(-.235, -.04, .89), P(-.215, -.045, .93), .014 * s, col, n=5)                       # thumb
    A.sphere(.045 * s, P(.105, -.17, .445), col, seg=10, rings=6, scale=(1, .8, .8))
    # suit: jacket hem, lapels, tie, buttons
    A.lathe([(.205 * s, .30 * s), (.195 * s, .40 * s)], P(0, -.01, 0), col, n=16, cap_top=False, cap_bottom=False)
    A.box((.04 * s, .012 * s, .15 * s), P(0, -.168, .545), dark, rot=(-12, 0, 0), bevel=0)
    for sx in (-1, 1):
        A.box((.05 * s, .012 * s, .14 * s), P(sx * .045, -.152, .575), col, rot=(-10, 0, sx * 25), bevel=0, detail=True)
    for z in (.47, .41):
        A.sphere(.012 * s, P(.02, -.205, z), dark, seg=6, rings=4, detail=True)


# ------------------------------------------------------------------ pallets
def pallet(A, loc, rot_z=0.0, col='wood_pallet', top=True, dx=1.2, dy=1.0, bottom=True):
    """EUR-like pallet (dx along X), base at loc. Simplified: deck + 3 stringers (+ top boards when top)."""
    x, y, z = loc
    R = (0, 0, rot_z)
    def L(px, py, pz):
        c, s = math.cos(math.radians(rot_z)), math.sin(math.radians(rot_z))
        return (x + px * c - py * s, y + px * s + py * c, z + pz)
    for py in (-dy / 2 + .05, 0, dy / 2 - .05):
        A.box((dx, .1, .1), L(0, py, .07), col if py else 'wood_weathered', rot=R, bevel=0)
    if bottom:
        A.box((dx, dy, .022), L(0, 0, .011), 'wood_weathered', rot=R, bevel=0)
    if top and not A.lod:
        for k in range(5):
            py = -dy / 2 + .07 + k * (dy - .14) / 4
            A.box((dx, .14, .022), L(0, py, .133), col, rot=R, bevel=0)
    else:
        A.box((dx, dy, .022), L(0, 0, .133), col, rot=R, bevel=0)
    return z + .144


def pallet_stack(A, loc, n, rot_z=0.0, jitter=.03, dx=1.2, dy=1.0):
    z = loc[2]
    for i in range(n):
        j = (A.rng.uniform(-jitter, jitter), A.rng.uniform(-jitter, jitter))
        z = pallet(A, (loc[0] + j[0], loc[1] + j[1], z), rot_z + A.rng.uniform(-2, 2), top=(i == n - 1), dx=dx, dy=dy, bottom=(i == 0))
    return z


# ------------------------------------------------------------------ flowers / hedge
def flower_mound(A, r, z0, cols, n=14, leaf='leaf', h=.45):
    """Planted bed: a soft green mound covered with round flower clusters."""
    A.mound(r, r, h, (0, 0, z0 - .02), leaf, rings=3, segs=16, noise=.06, power=.5, facet=False)
    for i in range(n):
        a = i * 2.4; rr = r * .92 * math.sqrt((i + .5) / n)
        x, y = rr * math.cos(a), rr * math.sin(a)
        zc = z0 - .02 + h * (1 - (rr / r) ** 2) ** .5
        A.ico(.16 * r / 1.45 + .03, (x, y, zc), cols[i % len(cols)], subdiv=2 if i % 4 == 0 else 1,
              scale=(1, 1, .6), noise=.1, facet=False, detail=(i % 3 == 2))


def hedge(A, L, W, H, kerb=.15, step=.4):
    """Trimmed boxwood on a low stone planter kerb: flat top, soft corners, leafy surface (jittered grid)."""
    import bmesh
    from mathutils import Vector
    A.box((L, W, kerb), (0, 0, kerb / 2), 'stone_warm', bevel=.02)
    bl, bw, bh = L - .1, W - .12, H - kerb
    pb = bmesh.new(); bmesh.ops.create_cube(pb, size=1.0)
    for v in pb.verts:
        v.co.x *= bl; v.co.y *= bw; v.co.z *= bh
    st = step * (2 if A.lod else 1)
    nx = max(1, int(bl / st))
    cuts = [(-bl / 2 + bl * k / nx, (1, 0, 0)) for k in range(1, nx)]
    cuts += [(bw * (k / 3 - .5), (0, 1, 0)) for k in (1, 2)] if not A.lod else []
    cuts += [(bh * (k / 3 - .5), (0, 0, 1)) for k in (1, 2)] if not A.lod else [(0, (0, 0, 1))]
    for d, n in cuts:
        geom = pb.verts[:] + pb.edges[:] + pb.faces[:]
        bmesh.ops.bisect_plane(pb, geom=geom, plane_co=Vector(n) * d, plane_no=n)
    for v in pb.verts:
        if v.co.z > -bh / 2 + 1e-4:
            ex = abs(abs(v.co.x) - bl / 2) < 1e-4; ey = abs(abs(v.co.y) - bw / 2) < 1e-4; ez = abs(v.co.z - bh / 2) < 1e-4
            j = A.rng.uniform(-.018, .018)
            if ex: v.co.x += j * (1 if v.co.x > 0 else -1)
            if ey: v.co.y += j * (1 if v.co.y > 0 else -1)
            if ez: v.co.z += A.rng.uniform(-.012, .012)
            if (ex or ey) and ez:                      # soften the top edges
                v.co.z -= .03
                if ey: v.co.y -= .025 * (1 if v.co.y > 0 else -1)
                if ex: v.co.x -= .025 * (1 if v.co.x > 0 else -1)
    for f in pb.faces:
        f.smooth = True
    A._add(pb, 'hedge', __import__('m2lib')._mat((0, 0, kerb + bh / 2)), 0, facet=False)
