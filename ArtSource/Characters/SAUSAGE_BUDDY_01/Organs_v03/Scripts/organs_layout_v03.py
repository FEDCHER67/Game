"""ORGANS LAYOUT v03: the single source of truth for organ sockets (patient REST frame, metres, Z up, faces -Y,
patient's left = +X). Imported by build_organs_v03.py, Patient_v03/build_patient_v03.py and build_abdomen_v03.py.

v02 -> v03 (Fedya 2026-10-18): the liver moves 4 cm and both kidneys ~6.8 cm lower; the freed upper torso gets a chest:
heart, two lungs, a ribcage (separate rib segments, split sternum) and the great vessels that tie the heart to the body.

Sizes: one size factor vs a real adult (x0.9) for widths/depths, as in v02. Buddy's trunk is short (axilla->crotch
0.34 m vs ~0.51 m real, x0.67), so organs whose real height exceeds the room (lungs 25 cm) get a height factor of ~0.62.
"""
import math

SIZE_FACTOR = 0.9

# Organ sockets: position (rest), long axis (+Y local, toward the head), anterior axis (+Z local, organ front).
SOCKETS = {
    "SOCKET_HEART": {"pos": (0.006, -0.040, 1.115), "y": (0, 0, 1), "z": (0, -1, 0)},
    "SOCKET_LUNG_L": {"pos": (0.089, -0.002, 1.113), "y": (0, 0, 1), "z": (0, -1, 0)},
    "SOCKET_LUNG_R": {"pos": (-0.085, -0.004, 1.110), "y": (0, 0, 1), "z": (0, -1, 0)},
    # liver: long axis is local +X (toward the left lobe), raised 4 deg (v02: 8), its big right lobe turned 10 deg toward the back
    "SOCKET_LIVER": {"pos": (-0.023, -0.048, 0.992), "y": (-math.sin(math.radians(4)), 0, math.cos(math.radians(4))),
                     "z": (-math.sin(math.radians(10)), -math.cos(math.radians(10)), 0)},   # right lobe 10 deg back
    # kidneys: upper pole 15 deg toward the spine and 10 deg back; front face turned 25 deg lateral (hilum antero-medial)
    "SOCKET_KIDNEY_L": {"pos": (0.080, 0.004, 0.908), "y": (-math.sin(math.radians(15)), math.sin(math.radians(10)), 1.0),
                        "z": (math.sin(math.radians(25)), -math.cos(math.radians(25)), 0)},
    "SOCKET_KIDNEY_R": {"pos": (-0.080, 0.004, 0.885), "y": (math.sin(math.radians(15)), math.sin(math.radians(10)), 1.0),
                        "z": (-math.sin(math.radians(25)), -math.cos(math.radians(25)), 0)},
    # static chest anatomy (ribcage halves, spine, vessels, airway, diaphragm) is authored in this frame
    "SOCKET_THORAX": {"pos": (0.0, 0.0, 1.100), "y": (0, 0, 1), "z": (0, -1, 0)},
}

ORGANS = {   # object name -> socket, real size (cm, long x wide x thick), source
    "ORGAN_HEART": {"socket": "SOCKET_HEART", "real_cm": (12, 8.5, 6), "source": "procedural (heart_v03.py)"},
    "ORGAN_LUNG_L": {"socket": "SOCKET_LUNG_L", "real_cm": (25, 11, 17),
                     "source": "LUNGS-ASTRA-001_recolour_v01: Lungs_Lobe_R + Lungs_BranchFront_R + Lungs_BranchRear_R "
                               "(the model names its pair from the viewer; its +X lobe is the patient-left lung)"},
    "ORGAN_LUNG_R": {"socket": "SOCKET_LUNG_R", "real_cm": (25, 12, 17),
                     "source": "LUNGS-ASTRA-001_recolour_v01: Lungs_Lobe_L + Lungs_BranchFront_L"},
    "ORGAN_LIVER": {"socket": "SOCKET_LIVER", "real_cm": (25, 15, 8),
                    "source": "LIVER-ASTRA-001_recolour_v01 (mesh 'LIVER-ASTRA-001 | clean organ body')"},
    "ORGAN_KIDNEY_L": {"socket": "SOCKET_KIDNEY_L", "real_cm": (11, 6, 3),
                       "source": "KIDNEY-ASTRA-001_recolour_v01 (mesh 'R_Kidney and descending tube' = patient-left kidney)"},
    "ORGAN_KIDNEY_R": {"socket": "SOCKET_KIDNEY_R", "real_cm": (11, 6, 3),
                       "source": "KIDNEY-ASTRA-001_recolour_v01 (mesh 'L_Kidney and descending tube')"},
}

# source model -> organ local: centre offset (model space), scale per MODEL axis (x width, y depth, z height)
SOURCE_FIT = {
    "ORGAN_LIVER": {"centre": (0.0, 0.0, 0.0), "scale": (1.08, 1.08, 0.88)},
    "ORGAN_KIDNEY_L": {"centre": (0.0702, 0.0, -0.0008), "scale": (0.9, 0.9, 0.9)},
    "ORGAN_KIDNEY_R": {"centre": (-0.0713, 0.0, 0.0012), "scale": (0.9, 0.9, 0.9)},
    # lungs: width x1.08, depth x1.45 (the source lobes are flat), height x0.93 -> ~10 x 10 x 15.5 cm
    "ORGAN_LUNG_L": {"centre": None, "scale": (1.08, 1.45, 0.93)},
    "ORGAN_LUNG_R": {"centre": None, "scale": (1.08, 1.45, 0.93)},
}

# Rib i (1..9): posterior head z, shape scale, costochondral junction (x, y, z) for the LEFT side, cartilage target.
# Cartilage target: ('sternum', z) for true ribs, ('rib', k, t) joins rib k's cartilage at parameter t.
RIBS = {
    1: {"zp": 1.188, "s": 0.72, "junction": (0.060, -0.074, 1.168), "to": ("sternum", 1.168)},
    2: {"zp": 1.170, "s": 0.86, "junction": (0.078, -0.082, 1.140), "to": ("sternum", 1.152)},
    3: {"zp": 1.151, "s": 0.95, "junction": (0.090, -0.086, 1.115), "to": ("sternum", 1.137)},
    4: {"zp": 1.132, "s": 1.00, "junction": (0.098, -0.086, 1.093), "to": ("sternum", 1.122)},
    5: {"zp": 1.112, "s": 1.00, "junction": (0.104, -0.084, 1.071), "to": ("sternum", 1.108)},
    6: {"zp": 1.092, "s": 1.00, "junction": (0.110, -0.080, 1.050), "to": ("sternum", 1.094)},
    7: {"zp": 1.072, "s": 1.00, "junction": (0.118, -0.073, 1.030), "to": ("sternum", 1.081)},
    8: {"zp": 1.052, "s": 1.00, "junction": (0.132, -0.058, 1.009), "to": ("rib", 7, 0.55)},
    9: {"zp": 1.032, "s": 0.98, "junction": (0.146, -0.036, 0.990), "to": ("rib", 8, 0.55)},
}
STERNUM = {"y": -0.0935, "top": 1.178, "xiphoid": 1.058, "half_width_top": 0.022, "half_width_body": 0.0135, "thick": 0.0075}
SPINE = {"y": 0.036, "z_top": 1.205, "z_bottom": 0.985, "levels": 11}
# Ribcage halves open like a clamshell after the sternum is split on the midline (mallet + osteotome).
RIBCAGE_HINGE = {"pos_left": (0.105, 0.080, 1.100), "axis": "local +Y (head axis)", "open_deg": 35}

# Abdominal opening v03 (INC_ABDOMEN frame, see build_abdomen_v03.py): shorter at the head end so it stays below the
# xiphoid and between the costal arches.
OPENING = {"centre_z": 0.950, "half_length_top": 0.095, "half_length_bottom": 0.128, "half_width": 0.120,
           "lens_p": 2.0, "lens_q_top": 0.8, "lens_q_bottom": 0.6}
GUIDE = {"start_z": 1.038, "end_z": 0.840}
# Future chest opening (sternotomy line) on the skin.
CHEST = {"centre_z": 1.110, "guide_start_z": 1.150, "guide_end_z": 1.062}

# Highest point of the abdominal cavity (OperationAbdomen_v03, rest frame) as a function of y (depth), measured from the
# v03 cavity mesh with a margin; at |x| the top falls by 5 x^2. The diaphragm and every chest organ stay above it.
CAVITY_TOP_Y = [(-0.10, 1.052), (-0.035, 1.052), (-0.02, 1.040), (0.0, 1.020), (0.02, 1.010), (0.04, 0.985), (0.06, 0.960)]


def cavity_top(x, y):
    pts = CAVITY_TOP_Y
    if y <= pts[0][0]:
        z = pts[0][1]
    elif y >= pts[-1][0]:
        z = pts[-1][1]
    else:
        for (y0, z0), (y1, z1) in zip(pts, pts[1:]):
            if y0 <= y <= y1:
                z = z0 + (z1 - z0) * (y - y0) / (y1 - y0)
                break
    return z - 5.0 * x * x


GREAT_VESSELS = {   # abdominal segments (OperationAbdomen_v03): x, y, radius, z (head end, pubic end)
    "aorta": {"x": 0.014, "y": -0.0015, "r": 0.0085, "z": (1.030, 0.850)},
    "vena_cava": {"x": -0.016, "y": 0.0072, "r": 0.0100, "z": (1.030, 0.850)},
}
