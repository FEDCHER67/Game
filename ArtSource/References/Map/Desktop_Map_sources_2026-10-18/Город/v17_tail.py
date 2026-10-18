
# ------------------------------------------------------------------ разметка, переходы, светофоры (v17)
def crossing_legs(j, names):
    all_legs = [(n, v, L) for n in names for v, L in legs(n, j)]
    if len(all_legs) < 3:
        return []
    keep = []
    for name, v, L in all_legs:
        probe = vadd(j, vmul(v, 60))
        if not inside_poly(probe, DISTRICT) and name not in ('AX', 'B'):
            continue
        keep.append((name, v, L))
    return keep


def crosswalks(out):
    for j, names in JUN:
        for name, v, L in crossing_legs(j, names):
            s = ST[name]
            dz = cross_dist(name, j, v, names, lambda t: t.sw * 0.5)
            if dz <= 0 or L < dz + 12:
                continue
            c = vadd(j, vmul(v, dz))
            nrm = (-v[1], v[0])
            k = -s.road / 2.0 + 4
            while k <= s.road / 2.0 - 3:
                out.append(poly(rr(vadd(c, vmul(nrm, k)), 16, 4, ang_of(v)), MARK))
                k += 7.5


def lights_and_stops(out):
    """Светофоры на штангах — на перекрёстках с бульваром и осью к площади; на остальных — знаки «стоп»."""
    for j, names in JUN:
        n_legs = len([1 for n in names for _ in legs(n, j)])
        if n_legs < 3:
            continue
        hw = max(ST[n].road / 2.0 + ST[n].sw for n in names) - 3
        main = 'B' in names or 'AX' in names
        for dx, dy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            p = (j[0] + dx * hw, j[1] + dy * hw)
            if main:
                out.append(rect(p[0] - 3.2, p[1] - 3.2, p[0] + 3.2, p[1] + 3.2, '#2E3238', '#1A1D20', 0.6))
                out.append(circle(p, 1.6, '#F2C230'))
            elif (dx + dy) == 0:
                out.append(circle(p, 2.6, '#C8372D', '#7A1E18', 0.6))


def centre_dashes(out):
    for name, s in ST.items():
        for a, b in zip(s.pts[:-1], s.pts[1:]):
            u = vunit(vsub(b, a))
            L = vlen(vsub(b, a))
            zones = []
            for j, names in JUN:
                if name not in names or seg_dist(j, a, b) > 1.5:
                    continue
                t = vdot(vsub(j, a), u)
                r = max(cross_dist(name, j, u, names, lambda st: st.sw + 14),
                        cross_dist(name, j, (-u[0], -u[1]), names, lambda st: st.sw + 14))
                zones.append((t - r, t + r))
            zones.append((-30, 24))
            zones.append((L - 24, L + 30))
            k = 6.0
            while k < L - 4:
                k2 = min(L - 2, k + 12)
                if not any(z0 < k2 and k < z1 for z0, z1 in zones):
                    out.append(line([vadd(a, vmul(u, k)), vadd(a, vmul(u, k2))], MARK, 1.4, 'butt'))
                k += 24


DRIVEWAYS = [R(281, 1010, 317, 1031),                                  # 10 стоянка полиции → Hsw
             R(1860, 420, 1881, 456),                                  # 12 стоянка таксопарка → Vd
             R(749, 905, 770, 945),                                    # 07 площадка магазина → L3
             R(40, 866, 61, 890), R(579, 866, 600, 890),               # 28 сквозной переулок
             R(1500, 780, 1522, 801), R(1500, 989, 1522, 1010),        # 31 сквозной переулок
             R(1450, 1169, 1472, 1190), R(1799, 586, 1820, 608), R(2100, 919, 2122, 940)]   # глухие 32, 33, 34


def render_png(svg, png, w, h):
    import subprocess
    chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
    html = svg[:-4] + '_render.html'
    io.open(html, 'w', encoding='utf-8').write(
        '<html><body style="margin:0">' + io.open(svg, encoding='utf-8').read() + '</body></html>')
    subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--screenshot=' + png,
                    '--window-size=%d,%d' % (w, h), 'file:///' + html.replace('\\', '/')], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html)
    return png


def build():
    make_city()
    o = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="%d 0 %d %d">' % (
        (XMAX - XMIN) * PX, H * PX, XMIN, XMAX - XMIN, H)]
    o.append(rect(XMIN, 0, XMAX, H, 'white'))
    ter = [rect(XMIN, 0, XMAX, H, LAWN)]
    ter.append(poly(offset_pl(CANAL, -40) + [(XMAX + 5, H + 5), (XMIN - 5, H + 5)], SAND))
    ter.append(poly([(XMIN - 5, 1246), (XMAX + 5, 1246)] + offset_pl(CANAL, 40)[::-1], PROM))
    ter.append(line(CANAL, WALL, 84, 'butt'))
    ter.append(line(CANAL, WATER, 72, 'butt'))
    for pl in BLK.values():
        ter.append(poly(pl, YARD))
    o += group('terrain', ter)
    rd = []
    for s in ST.values():
        rd.append(line(s.pts, '#BFC3C4', s.road + 2 * s.sw + 2, s.cap))      # бордюр
    for s in ST.values():
        rd.append(line(s.pts, WALK, s.road + 2 * s.sw, s.cap))
    for s in ST.values():
        rd.append(line(s.pts, ASPH, s.road, s.cap))
    for pl in DRIVEWAYS:
        rd.append(poly(pl, '#B3B9BD'))
    for x in (AXIS - 36, AXIS + 36):
        rd.append(line([(x, 1294), (x, 1390)], '#5E5A50', 1.8, 'butt'))
    centre_dashes(rd)
    crosswalks(rd)
    lights_and_stops(rd)
    o += group('roads', rd)
    o += group('squares_and_lots', PAVE0 + LAWNS + PAVE + LOTS)
    o += group('paths', [line(p, '#5E8FBF', 2.2, extra=' stroke-dasharray="6 5"') for p in BLUE])
    o += group('shadows', SHADOW)
    o += group('buildings', BLD + SPEC)
    trs = [circle(p, r, '#B9D19F', '#86A274', 1) for p, r in TREES]
    avoid = list(BLK.values()) + [R(1460, 0, 2160, 80)]
    scatter_trees(trs, 16, (XMIN, 0, XMAX, 50), avoid)
    scatter_trees(trs, 6, (XMIN, 120, -30, 600), avoid)
    scatter_trees(trs, 8, (2290, 120, XMAX, 600), avoid)
    for x in range(int(XMIN) + 70, int(XMAX), 170):
        if abs(x - AXIS) > 70:
            trs.append(circle((x, 1428), 8, '#A9C98A', '#7E9E62', 1))
    o += group('trees', trs)
    ob = []
    hydrants(ob)
    for p in LAMPS:
        ob.append(circle(p, 4, '#FFFDF4', '#BA8442', 1.5))
    for p, a in BENCH:
        ob.append(poly(rr(p, 16, 4, a), '#B08D5E', '#6E5A3A', 0.6))
    x = XMIN + 72.0
    while x < XMAX:
        if abs(x - AXIS) > 64:
            ob.append(poly(rr((x, 1288), 16, 4, 0), '#B08D5E', '#6E5A3A', 0.6))
        x += 168
    o += group('objects', ob)
    nb = []
    for s, (x, y) in NUMS:
        nb.append(circle((x, y), 13, '#FFFFFF', INK, 1.6))
        nb.append(text(x, y + 0.5, s, 12, 700, INK, 'middle'))
    o += group('numbers', nb)
    tt = [rect(1480, 8, 2420, 70, '#FFFFFF', '#8FA9B1', 1.2, ' fill-opacity="0.94"')]
    tt.append(text(1496, 32, 'ГОРОД / DOWNTOWN · план v17 (спецификация 15.10.2026)', 20, 700))
    tt.append(text(1496, 56, 'Заломы крайних улиц · улицы 8,5 м, тротуары 4 м · без деревьев вдоль улиц · башни-близнецы + паркинг · 1 ед. = 0,2 м',
                   11.5, 400, '#6D7A80'))
    for x, y, s, anc in ((150, 40, '↖ Неблагополучный район', 'start'),
                         (XMIN + 6, 690, '← Интернацио-', 'start'), (XMIN + 6, 708, 'нальная стройка', 'start'),
                         (XMAX - 6, 790, 'Элитный холм →', 'end'), (AXIS + 50, 1446, '↓ Городской пляж', 'start')):
        tt.append(text(x, y, s, 13, 700, '#5F6E75', anc))
    for i in range(5):
        tt.append(rect(140 + i * 50, 1426, 190 + i * 50, 1435, INK if i % 2 == 0 else '#FFFFFF', INK, 1))
    tt.append(text(140, 1414, '0', 11, 600, INK, 'middle'))
    tt.append(text(390, 1414, '50 м', 11, 600, INK, 'middle'))
    o += group('title', tt)
    o.append('</svg>')
    return '\n'.join(o)


def straight_runs():
    """Длина каждого прямого куска крайних улиц, м."""
    out = []
    for n in RING:
        for a, b in zip(ST[n].pts[:-1], ST[n].pts[1:]):
            out.append((n, vlen(vsub(b, a)) * 0.2))
    return out


if __name__ == '__main__':
    if os.path.exists(OUT_SVG) or os.path.exists(OUT_PNG):
        raise SystemExit('v17 outputs exist')
    io.open(OUT_SVG, 'w', encoding='utf-8').write(build())
    print('wrote', OUT_SVG)
    print('ring runs, m:', ', '.join('%s %.0f' % r for r in straight_runs()))
    print('trees:', len(TREES), 'parks:', len([n for n in NUMS if n[0] in ('20', '21', '23', '27')]))
    print(render_png(OUT_SVG, OUT_PNG, int((XMAX - XMIN) * PX), int(H * PX)))
