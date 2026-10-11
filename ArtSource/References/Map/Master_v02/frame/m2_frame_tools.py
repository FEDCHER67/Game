#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Helpers for M2 tracers: convert between crop pixels, master pixels and metres using m2_frame.json.
python -B m2_frame_tools.py <crop_key> <cx> <cy>       -> metres
python -B m2_frame_tools.py --m <crop_key> <x_m> <y_m>  -> crop pixels"""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
FRAME = json.loads((Path(__file__).resolve().parent/'m2_frame.json').read_text(encoding='utf-8'))
S = FRAME['transform']['metres_per_px']
X0, Y0 = FRAME['transform']['origin_px']


def src_to_m(u, v):
    """Continuous master-pixel coordinates (pixel i centre = i+0.5) -> metres."""
    return round((u-X0)*S, 3), round((Y0-v)*S, 3)


def m_to_src(x, y):
    return round(X0+x/S, 3), round(Y0-y/S, 3)


def crop_to_m(key, cx, cy):
    a = FRAME['crops'][key]['crop_px_to_m']
    return round(a['ax']*cx+a['bx'], 3), round(a['ay']*cy+a['by'], 3)


def m_to_crop(key, x, y):
    a = FRAME['crops'][key]['crop_px_to_m']
    return round((x-a['bx'])/a['ax'], 2), round((y-a['by'])/a['ay'], 2)


def poly_crop_to_m(key, pts):
    return [list(crop_to_m(key, cx, cy)) for cx, cy in pts]


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--m':
        print(m_to_crop(args[1], float(args[2]), float(args[3])))
    elif len(args) == 3:
        print(crop_to_m(args[0], float(args[1]), float(args[2])))
    else:
        print(__doc__)
