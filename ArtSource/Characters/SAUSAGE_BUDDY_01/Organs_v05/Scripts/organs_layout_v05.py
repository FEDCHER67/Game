"""ORGANS LAYOUT v05 (Fedya's playtest of v04, 2026-10-18): the chest must sit well inside a bigger, lower opening and the
intestines come back.

v04 -> v05 (rest frame, metres):
  * the chest + liver block (ribcage incl. UCX/BREAK/hinges, heart, lungs, vessels, airway, diaphragm, liver) moves down
    SHIFT_CHEST; it is rigid, so every organ<->collider distance inside it is unchanged;
  * the kidneys move by SHIFT_KIDNEY (slightly up and back) so the v03-size intestine coil fits below them in the lower belly;
    their ureter stubs are shortened (they reached the posed hip skin);
  * the patient's trunks become low-rise (waistband rest z 0.800 -> WAISTBAND_Z) so the opening can reach the bottom of
    the belly; the opening is wider at the chest (fuller top) and longer.
Imported by build_organs_v05.py, Patient_v05/build_patient_v05.py and TABLE-ASTRA-001/v05/Scripts/build_*_v05.py.
"""
import math
import sys
from pathlib import Path

V04 = Path(r"C:/Dev/Game/ArtSource/Characters/SAUSAGE_BUDDY_01/Organs_v04/Scripts")
if str(V04) not in sys.path:
    sys.path.insert(0, str(V04))
import organs_layout_v04 as V4  # noqa: E402

SHIFT_CHEST = (0.0, 0.0, -0.028)
SHIFT_KIDNEY = (0.0, +0.004, +0.012)   # kidneys 1.2 cm up and 4 mm further back (clear of the lowered liver)
KIDNEY_SOCKETS = ("SOCKET_KIDNEY_L", "SOCKET_KIDNEY_R")
URETER_KEEP = 0.40             # ureter stub (kidney tube below the bean) compressed to 40 % of its length
WAISTBAND_Z = 0.772            # low-rise trunks: top of the waistband (v01..v04: 0.800)
SIZE_FACTOR = V4.SIZE_FACTOR
ORGANS = V4.ORGANS


def add(p, d):
    return (p[0] + d[0], p[1] + d[1], p[2] + d[2])


SOCKETS = {k: dict(v, pos=add(v["pos"], SHIFT_KIDNEY if k in KIDNEY_SOCKETS else SHIFT_CHEST)) for k, v in V4.SOCKETS.items()}
# abdominal aorta / IVC: head end joins the chest vessels (moves with the chest), pubic end stays near the kidneys
GREAT_VESSELS = {k: dict(v, z=(v["z"][0] + SHIFT_CHEST[2], v["z"][1] + SHIFT_KIDNEY[2])) for k, v in V4.GREAT_VESSELS.items()}
RIBCAGE_HINGE = dict(V4.RIBCAGE_HINGE, pos_left=add(V4.RIBCAGE_HINGE["pos_left"], SHIFT_CHEST))
CHEST = {k: v + SHIFT_CHEST[2] for k, v in V4.CHEST.items()}
CHIN_Z = V4.CHIN_Z
chin_z = V4.chin_z

# v05 opening: just under the chin (1.112) down to the bottom of the belly (0.787, above the low-rise waistband),
# wider and with a broad, full top (p 3.0 / q 0.30) so the lungs and heart are framed, same rim as v03/v04.
OPENING = {"centre_z": 0.9495, "half_length_top": 0.1625, "half_length_bottom": 0.1625, "half_width": 0.134,
           "lens_p_top": 3.0, "lens_q_top": 0.30, "lens_p": 2.0, "lens_q_bottom": 0.50,
           "flap_limit_top_rest_z": "chin_z(x) - 0.004", "flap_limit_bottom_rest_z": WAISTBAND_Z + 0.002}
GUIDE = {"start_z": 1.100, "end_z": 0.800}
# v03-size intestine coil (tube radius 10.8 mm, 4 rows) in the lower belly, in front of / below the kidneys
INTESTINE_ROWS = [(-0.112, 0.098, 0.100), (-0.127, 0.092, 0.094), (-0.141, 0.084, 0.086), (-0.154, 0.068, 0.064)]
INTESTINE_RADIUS = 0.0108
INTESTINE_DEPTH = -0.056


def outline_xy(op, seg=128, wobble=True):
    """Opening outline in INC_ABDOMEN-local XY: asymmetric superellipse-lens |x| = W (1 - |t|^p)^q with the v02 wobble."""
    W = op["half_width"]
    pts = []
    for k in range(seg):
        th = 2 * math.pi * k / seg
        t = math.sin(th)
        top = t > 0
        H = op["half_length_top"] if top else op["half_length_bottom"]
        p = op.get("lens_p_top", op["lens_p"]) if top else op["lens_p"]
        q = op["lens_q_top"] if top else op["lens_q_bottom"]
        w = W * (1 - abs(t) ** p) ** q
        x = math.copysign(w, math.cos(th)) if abs(math.cos(th)) > 1e-9 else 0.0
        y = H * t
        wob = (0.018 * math.sin(3 * th + 0.7) + 0.014 * math.sin(7 * th + 2.1) + 0.008 * math.sin(13 * th + 0.4)) if wobble else 0.0
        pts.append((x * (1 + wob), y * (1 + 0.35 * wob)))
    return pts
