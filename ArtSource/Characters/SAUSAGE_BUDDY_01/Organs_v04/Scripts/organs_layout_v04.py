"""ORGANS LAYOUT v04 = the accepted v03d organ block moved DOWN as one rigid piece + the bigger chest/belly opening.
(4.5 cm straight down; see SHIFT.)

Fedya 2026-10-18: the chin/neck of the lying patient hid the chest from the top table camera. v04 moves every organ,
the ribcage (ribs, sternum halves, spine, hinges, BREAK empties, the 96 UCX colliders), vessels, airway and diaphragm
by the same translation SHIFT (no relative change), and replaces the belly opening with one that frames chest + belly.

SHIFT choice (rest frame): measured on the TABLE_REST body from the top game camera, the chin starts to cover the trunk
skin at rest z 1.120 on the midline (1.125 at |x| 0.06, 1.14 at |x| 0.10). v03d's heart body reached 1.157 and the sternum
top 1.178. Down: heart body top <= ~1.112 needs dz <= -0.045; the right kidney (centre 0.885) must stay in the torso and in
reach of an opening whose lower edge cannot pass the trunks' waistband (rest z 0.800): dz >= -0.045 (at -0.050 the right
kidney's ureter stub touches the posed hip skin). Chosen: (0, 0, -0.045), a pure downward move.
Known, inherited from G38's thick ribs: in v03d ribs 1-2 poked up to 4.6 mm out of the chest skin at the neck and rib 4 up
to 2.3 mm out of the back. After the move the front is clean (<= 0.1 mm, 2 vertices of rib 1 in TABLE_REST) but rib 4's
posterior angle pokes up to 4.6 mm out of the back (rib 3: 0.9 mm). A forward component trades this back against the
front again (dy -3 mm: front 3.0 mm under the chin, back 2.0 mm); only trimming RIB_*_04 (render mesh + UCX) removes it.
Imported by build_organs_v04.py, Patient_v04/build_patient_v04.py and TABLE-ASTRA-001/v04/Scripts/build_abdomen_v04.py.
"""
import math
import sys
from pathlib import Path

V03 = Path(r"C:/Dev/Game/ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v03/Scripts")
if str(V03) not in sys.path:
    sys.path.insert(0, str(V03))
import organs_layout_v03 as V3  # noqa: E402

SHIFT_Y = 0.0
SHIFT_Z = -0.045
SHIFT = (0.0, SHIFT_Y, SHIFT_Z)
SIZE_FACTOR = V3.SIZE_FACTOR
ORGANS = V3.ORGANS


def shifted(p):
    return (p[0] + SHIFT[0], p[1] + SHIFT[1], p[2] + SHIFT[2])


SOCKETS = {k: dict(v, pos=shifted(v["pos"])) for k, v in V3.SOCKETS.items()}
GREAT_VESSELS = {k: dict(v, y=v["y"] + SHIFT_Y, z=(v["z"][0] + SHIFT_Z, v["z"][1] + SHIFT_Z)) for k, v in V3.GREAT_VESSELS.items()}
RIBCAGE_HINGE = dict(V3.RIBCAGE_HINGE, pos_left=shifted(V3.RIBCAGE_HINGE["pos_left"]))
CHEST = {k: v + SHIFT_Z for k, v in V3.CHEST.items()}

# Chin line of the lying patient (TABLE_REST) in rest z of the trunk skin, measured from the top game camera.
CHIN_Z = {0.0: 1.120, 0.03: 1.122, 0.06: 1.127, 0.10: 1.142}


def chin_z(x):
    xs = sorted(CHIN_Z)
    ax = min(abs(x), xs[-1])
    for a, b in zip(xs, xs[1:]):
        if a <= ax <= b:
            return CHIN_Z[a] + (CHIN_Z[b] - CHIN_Z[a]) * (ax - a) / (b - a)
    return CHIN_Z[xs[-1]]


# v04 opening: one lens from just under the chin (top edge rest z 1.112) to just above the trunks' waistband (0.808),
# fuller at the top so it frames the ribcage, centre (= INC_ABDOMEN) at rest z 0.958.
OPENING = {"centre_z": 0.958, "half_length_top": 0.154, "half_length_bottom": 0.150, "half_width": 0.124,
           "lens_p": 2.0, "lens_q_top": 0.45, "lens_q_bottom": 0.60,
           "flap_limit_top_rest_z": "chin_z(x) - 0.004 (flaps squeezed under the chin)", "flap_limit_bottom_rest_z": 0.801}
GUIDE = {"start_z": 1.100, "end_z": 0.822}


def outline_xy(op, seg=128, wobble=True):
    """The opening outline in INC_ABDOMEN-local XY (same lens + natural wobble formula as v02/v03)."""
    W, p = op["half_width"], op["lens_p"]
    pts = []
    for k in range(seg):
        th = 2 * math.pi * k / seg
        t = math.sin(th)
        H = op["half_length_top"] if t > 0 else op["half_length_bottom"]
        q = op["lens_q_top"] if t > 0 else op["lens_q_bottom"]
        w = W * (1 - abs(t) ** p) ** q
        x = math.copysign(w, math.cos(th)) if abs(math.cos(th)) > 1e-9 else 0.0
        y = H * t
        wob = (0.018 * math.sin(3 * th + 0.7) + 0.014 * math.sin(7 * th + 2.1) + 0.008 * math.sin(13 * th + 0.4)) if wobble else 0.0
        pts.append((x * (1 + wob), y * (1 + 0.35 * wob)))
    return pts
