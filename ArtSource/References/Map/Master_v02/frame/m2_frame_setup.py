#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""M2 digitizing frame for Fedya's Master v02 (REF_FEDYA_MASTER_v02_map.png).
Measures the 0-100 m scale bar, finds the frame / sea / land bbox, defines the pixel -> metre transform
(x east, y north, origin = bottom-left of the land bbox) and cuts Lanczos-upscaled crops per district plus a
whole-map crop, each with a clean and a metre-gridded version. Writes m2_frame.json next to this script.
Reads only the master PNG; writes only into the scratchpad. Run with python -B."""
import json
import sys
from pathlib import Path
sys.dont_write_bytecode = True
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

SRC = Path(r'C:\Dev\Game\ArtSource\References\Map\REF_FEDYA_MASTER_v02_map.png')
OUT = Path(__file__).resolve().parent
FONT = r'C:\Windows\Fonts\arial.ttf'

# source-pixel boxes [x0, y0, x1, y1] (continuous edges, x right, y down), upscale factor, title
CROPS = {
    'whole':       ([6, 0, 1227, 714], 2, 'Whole master: coast, sea, bay, river, mountain edge, full road network'),
    '01_forest':   ([6, 370, 380, 690], 3, '01 FOREST (SW): wagon on rails at the coast, ponds, forest, SW coast'),
    '02_hamlet':   ([40, 160, 430, 450], 3, '02 HAMLET (W): houses, fields, ponds, church-like building, dirt roads'),
    '03_crossing': ([315, 160, 610, 480], 3, '03 CROSSING (centre-west): road hub, buildings, pond, river and bridges'),
    '04_rough':    ([585, 95, 905, 315], 3, '04 ROUGH DISTRICT (N): panel blocks, courtyards, pitch, garages'),
    '05_downtown': ([515, 280, 845, 470], 3, '05 DOWNTOWN (centre): grid blocks, central square with fountain'),
    '06_port':     ([845, 35, 1195, 285], 3, '06 INDUSTRIAL PORT (NE): walled port, pier, outfall'),
    '07_elite':    ([785, 255, 1135, 625], 3, '07 ELITE HILL (E): oval hill, mansions, pools, loop road; SE coast and bay for the marina'),
    '08_valley':   ([335, 435, 585, 680], 3, '08 QUIET VALLEY (S-centre-west): big building, pond, road to the small beach'),
    '09_beach':    ([525, 435, 835, 680], 3, '09 CITY BEACH (S): sand, umbrellas, long pier, river mouth'),
    'legend':      ([940, 570, 1222, 700], 4, 'Legend, scale bar and north arrow (reference only, no grid)'),
}
GRID = {2: (50, 100), 3: (10, 50), 4: None}   # upscale -> (minor m, major m)


def load():
    return np.asarray(Image.open(SRC).convert('RGB')).astype(int)


def measure_scale_bar(im):
    """Scale bar: five alternating dark/white 20 m segments on rows 595-596, x 945-1070."""
    L = im.mean(axis=2)
    prof = L[595:597, 945:1070].mean(axis=0)
    light = prof[30:45].mean()
    lvl = (prof.min()+light)/2
    edges = []
    for i in range(len(prof)-1):
        a, b = prof[i], prof[i+1]
        if (a-lvl)*(b-lvl) < 0:
            edges.append(945+i+(lvl-a)/(b-a)+0.5)      # continuous coordinate (pixel i centre = i+0.5)
    assert len(edges) == 6, edges
    metres = np.array([0, 20, 40, 60, 80, 100], float)
    px = np.array(edges)
    slope, icpt = np.polyfit(metres, px, 1)            # px per metre
    resid = px-(slope*metres+icpt)
    return dict(row_px=[595, 596], edges_px=[round(e, 2) for e in edges], marks_m=metres.tolist(),
                fit_px_per_m=round(float(slope), 5), fit_residual_max_px=round(float(abs(resid).max()), 3),
                end_to_end_px=round(float(px[-1]-px[0]), 2))


def frame_and_land(im):
    L = im.mean(axis=2)
    cm = L.mean(axis=0)
    # frame: columns that are not the dark viewer margin (~32)
    cols = np.where(cm > 100)[0]
    fx0, fx1 = int(cols.min()), int(cols.max())+1
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    water = (b-r > 28) & (b >= g-2)
    water[:, :fx0] = False
    water[:, fx1:] = False
    lab, _ = ndi.label(water)
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    sea = lab == int(sizes.argmax())
    land = np.zeros_like(sea)
    land[:, fx0:fx1] = True
    land &= ~sea
    land[555:, 940:] = False                           # legend / scale bar / north arrow overlay on the sea
    lab2, _ = ndi.label(land)
    s2 = np.bincount(lab2.ravel())
    s2[0] = 0
    main = lab2 == int(s2.argmax())
    ys, xs = np.where(main)
    return dict(frame_px=[fx0, 0, fx1, im.shape[0]],
                land_bbox_px=[int(xs.min()), int(ys.min()), int(xs.max())+1, int(ys.max())+1],
                sea_px=int(sea.sum()), land_px=int(main.sum()))


class Frame:
    def __init__(self, s, x0, y0):
        self.s, self.x0, self.y0 = s, x0, y0

    def src_to_m(self, u, v):
        return ((u-self.x0)*self.s, (self.y0-v)*self.s)

    def m_to_src(self, x, y):
        return (self.x0+x/self.s, self.y0-y/self.s)

    def crop_affine(self, box, k):
        # crop pixel (cx, cy) -> source u = box0 + (cx+0.5)/k, v = box1 + (cy+0.5)/k
        ax = self.s/k
        bx = (box[0]+0.5/k-self.x0)*self.s
        ay = -self.s/k
        by = (self.y0-box[1]-0.5/k)*self.s
        return ax, bx, ay, by


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except OSError:
        return ImageFont.load_default()


def draw_grid(img, fr, box, k, minor, major):
    over = Image.new('RGBA', img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    ax, bx, ay, by = fr.crop_affine(box, k)
    W, H = img.size
    xm0, xm1 = bx, ax*(W-1)+bx
    ym1, ym0 = by, ay*(H-1)+by
    f = font(15 if k >= 3 else 16)
    for gx in np.arange(np.ceil(xm0/minor)*minor, xm1+1e-6, minor):
        cx = (gx-bx)/ax
        maj = abs(gx/major-round(gx/major)) < 1e-6
        d.line([(cx, 0), (cx, H)], fill=(220, 0, 0, 150) if maj else (220, 60, 60, 60), width=2 if maj else 1)
        if maj:
            t = f'x{int(round(gx))}'
            d.rectangle([cx+2, 2, cx+4+f.getlength(t), 20], fill=(255, 255, 255, 200))
            d.text((cx+3, 3), t, fill=(180, 0, 0, 255), font=f)
    for gy in np.arange(np.ceil(ym0/minor)*minor, ym1+1e-6, minor):
        cy = (gy-by)/ay
        maj = abs(gy/major-round(gy/major)) < 1e-6
        d.line([(0, cy), (W, cy)], fill=(0, 0, 220, 150) if maj else (60, 60, 220, 60), width=2 if maj else 1)
        if maj:
            t = f'y{int(round(gy))}'
            d.rectangle([2, cy+2, 4+f.getlength(t), cy+20], fill=(255, 255, 255, 200))
            d.text((3, cy+3), t, fill=(0, 0, 170, 255), font=f)
    return Image.alpha_composite(img.convert('RGBA'), over).convert('RGB')


def main():
    im = load()
    sb = measure_scale_bar(im)
    fl = frame_and_land(im)
    s = 1/sb['fit_px_per_m']                          # metres per source pixel
    lb = fl['land_bbox_px']
    fr = Frame(s, float(lb[0]), float(lb[3]))         # origin = bottom-left corner of the land bbox
    src = Image.open(SRC).convert('RGB')
    crops = {}
    for key, (box, k, title) in CROPS.items():
        w, h = box[2]-box[0], box[3]-box[1]
        c = src.resize((w*k, h*k), Image.LANCZOS, box=tuple(box))
        name = f'm2_crop_{key}.png'
        c.save(OUT/name)
        ax, bx, ay, by = fr.crop_affine(box, k)
        rec = dict(file=name, title=title, source_box_px=box, upscale=k, filter='PIL LANCZOS (box resize)',
                   size_px=[w*k, h*k], m_per_crop_px=round(s/k, 6),
                   crop_px_to_m=dict(formula='x_m = ax*cx + bx ; y_m = ay*cy + by  (cx right, cy down, pixel index; centre convention)',
                                     ax=round(ax, 6), bx=round(bx, 4), ay=round(ay, 6), by=round(by, 4)),
                   m_to_crop_px=dict(formula='cx = (x_m - bx)/ax ; cy = (y_m - by)/ay'),
                   extent_m=[round(bx, 2), round(ay*(h*k-1)+by, 2), round(ax*(w*k-1)+bx, 2), round(by, 2)])
        if GRID.get(k):
            mi, ma = GRID[k]
            g = draw_grid(c, fr, box, k, mi, ma)
            gname = f'm2_crop_{key}_grid.png'
            g.save(OUT/gname)
            rec.update(grid_file=gname, grid_minor_m=mi, grid_major_m=ma,
                       grid_note='red verticals = x (east) in metres, blue horizontals = y (north) in metres; labels on major lines')
        crops[key] = rec
    # self-test: scale bar ends 100 m apart; round trips
    e = sb['edges_px']
    p0, p1 = fr.src_to_m(e[0], 595.5), fr.src_to_m(e[-1], 595.5)
    rt = []
    for key, rec in crops.items():
        a = rec['crop_px_to_m']
        for cx, cy in ((0, 0), (rec['size_px'][0]-1, rec['size_px'][1]-1), (123, 45)):
            x, y = a['ax']*cx+a['bx'], a['ay']*cy+a['by']
            u, v = rec['source_box_px'][0]+(cx+.5)/rec['upscale'], rec['source_box_px'][1]+(cy+.5)/rec['upscale']
            x2, y2 = fr.src_to_m(u, v)
            rt.append(max(abs(x-x2), abs(y-y2)))
    badges_px = {  # confirmed visually (dark rounded "player base key" badges); text unreadable at this resolution
        '01_forest (wagon on rails)': [146.5, 520.5], '02_hamlet (building W of the junction)': [144.5, 272.0],
        '04_rough (SW block, L-shaped panel)': [654.5, 275.0], '05_downtown (SW block, green building)': [570.5, 427.0],
        '08_valley (blue building N of the pond)': [497.5, 485.0]}
    land_m = [0.0, 0.0, round((lb[2]-lb[0])*s, 2), round((lb[3]-lb[1])*s, 2)]
    fx = fl['frame_px']
    frame_m = [round(v, 2) for v in (*fr.src_to_m(fx[0], fx[3]), *fr.src_to_m(fx[2], fx[1]))]
    play_px = [60, 55, 1170, 668]
    play_m = [round(v, 1) for v in (*fr.src_to_m(play_px[0], play_px[3]), *fr.src_to_m(play_px[2], play_px[1]))]
    out = dict(
        id='M2_FRAME_MASTER_v02', date='2026-10-07',
        source=dict(file=str(SRC), size_px=[im.shape[1], im.shape[0]], note=(
            'Fedya Master v02 (06.10.2026), north up. The PNG is a 1280x714 downscaled screenshot: the right 53 px are a dark '
            'viewer margin and the left 6 px a dark edge; top and bottom of the map are cut by the frame. Object-key and base-key '
            'texts (2-3 px tall) are not readable even at 3-4x. The subtitle seems to say "1 unit = 0.2 m" (illegible; not used).')),
        units='metre', axes=dict(x='east', y='north', unity_mapping='(x, terrain_height, y)'),
        scale_bar=sb,
        transform=dict(
            metres_per_px=round(s, 6), px_per_metre=sb['fit_px_per_m'],
            uncertainty=f'about +-0.5 percent (bar edges anti-aliased; fit residual max {sb["fit_residual_max_px"]} px over '
                        f'{sb["end_to_end_px"]} px)',
            origin_px=[fr.x0, fr.y0], origin_definition='bottom-left corner of the land bbox (land = frame minus the connected sea; '
            'mountains count as land). Source-pixel coordinates are continuous: pixel (i, j) covers [i, i+1) x [j, j+1); its centre is (i+0.5, j+0.5).',
            src_px_to_m='x_m = (u - %.1f) * %.6f ; y_m = (%.1f - v) * %.6f' % (fr.x0, s, fr.y0, s),
            m_to_src_px='u = %.1f + x_m / %.6f ; v = %.1f - y_m / %.6f' % (fr.x0, s, fr.y0, s),
            crop_px_to_src_px='u = box_x0 + (cx + 0.5)/upscale ; v = box_y0 + (cy + 0.5)/upscale',
            selftest=dict(scale_bar_length_m=round(p1[0]-p0[0], 3), crop_roundtrip_max_err_m=round(max(rt), 6))),
        extents=dict(
            frame_px=fx, frame_m=frame_m, land_bbox_px=lb, land_bbox_m=land_m,
            land_note='land bbox includes the mountain ridge (world edge) and runs to the frame on the W and N sides; '
                      'sea south of y=0 has negative y',
            approx_playable_bbox_px=play_px, approx_playable_bbox_m=play_m,
            approx_playable_note='hand estimate, +-10 m: mountain foot ~x60 px on the W, ~y55-195 px on the N; S coast ~y668 px; '
                                 'E to the port pier/outfall ~x1170 px. About 1.12 km E-W x 0.62 km N-S: wider than v14 (971 x 672 m) '
                                 'and over v14\'s "playable extent <= 1000 m" check -> lead/Fedya decision (scale bar taken as truth).',
            overlays_to_ignore_px=dict(title_box=[15, 8, 280, 54], legend_scale_north=[940, 555, 1227, 700])),
        v14_comparison=dict(v14_extent_m=[971.558, 671.718], v14_frame='1000 x 1000 m, origin bottom-left',
                            note='Master v02 replaces the v14 layout; no v14 coordinates carry over except the marina geometry '
                                 '(transplant MAP_PLAN_R01_v14.json "marina" by a rigid transform onto the elite coast).'),
        player_base_badges_px=badges_px,
        player_base_badges_m={k: [round(c, 1) for c in fr.src_to_m(*v)] for k, v in badges_px.items()},
        badges_note='5 dark player-base badges confirmed; none found yet in 03, 06, 07, 09 (may be lighter or absent). Texts unreadable.',
        district_number_circles_px={'01': [150, 499], '02': [228, 278], '03': [446, 306], '04': [628, 137], '05': [626, 346],
                                    '06': [954, 255], '07': [825, 346], '08': [381, 518], '09': [716, 517]},
        crops=crops,
        tracer_rules=[
            'Trace in the *_grid.png (or compute from the clean crop with crop_px_to_m); write metres rounded to 0.1 m.',
            'Polygons counter-clockwise, not closed (first point not repeated), >=3 points; polylines in travel order.',
            'Widths come from the road class table, not from the blurry pixels (asphalt 2 lanes max).',
            'Record uncertainty instead of guessing: put doubtful items in the fragment "questions_ru".'],
    )
    (OUT/'m2_frame.json').write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(dict(scale=sb, frame=fl, metres_per_px=round(s, 6), origin_px=[fr.x0, fr.y0],
                          land_m=land_m, frame_m=frame_m, play_m=play_m, selftest=out['transform']['selftest'],
                          crops={k: (v['size_px'], v['extent_m']) for k, v in crops.items()}), indent=1))


if __name__ == '__main__':
    main()
