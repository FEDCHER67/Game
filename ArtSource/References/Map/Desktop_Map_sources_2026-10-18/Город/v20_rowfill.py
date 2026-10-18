def rowfill(x0, y0, x1, y1, street, gaps=(), wmin=38, wmax=86):
    """v20: сплошная стена узких домов вдоль улицы, без щелей: фасады и задние стены ровные, остаток ряда
    отдаётся последнему дому. street — сторона улицы (N/S/E/W). gaps — проёмы под переулки вдоль ряда."""
    horiz = street in ('N', 'S')
    a0, a1 = (x0, x1) if horiz else (y0, y1)
    cuts = sorted(g for g in gaps if a0 < g[1] and g[0] < a1)
    spans, pos = [], a0
    for g0, g1 in cuts:
        if g0 > pos:
            spans.append((pos, g0))
        pos = max(pos, g1)
    if pos < a1:
        spans.append((pos, a1))
    for s0, s1 in spans:
        edges = [s0]
        while s1 - edges[-1] > wmax:
            edges.append(edges[-1] + _hr.uniform(wmin, wmax))
        if len(edges) > 1 and s1 - edges[-1] < wmin * 0.7:
            edges.pop()                                              # короткий остаток — к соседнему дому
        edges.append(s1)
        for p0, p1 in zip(edges[:-1], edges[1:]):
            if horiz:
                hx0, hx1, hy0, hy1 = p0, p1, y0, y1
            else:
                hx0, hx1, hy0, hy1 = x0, x1, p0, p1
            col = pick_col()
            tower = None
            if _hr.random() < 0.3 and (hx1 - hx0) > 26 and (hy1 - hy0) > 26:
                tower = (_hr.uniform(hx0 + 10, hx1 - 10), _hr.uniform(hy0 + 10, hy1 - 10))
            house(hx0, hy0, hx1, hy1, col, tower=tower, h=_hr.choice((9, 11, 13, 15, 17)))
            if _hr.random() < 0.38:
                if street == 'N':
                    fire_escape((hx0 + 6, hy0), (min(hx1 - 6, hx0 + 40), hy0), (0, -1))
                elif street == 'S':
                    fire_escape((hx0 + 6, hy1), (min(hx1 - 6, hx0 + 40), hy1), (0, 1))
                elif street == 'W':
                    fire_escape((hx0, hy0 + 6), (hx0, min(hy1 - 6, hy0 + 40)), (-1, 0))
                else:
                    fire_escape((hx1, hy0 + 6), (hx1, min(hy1 - 6, hy0 + 40)), (1, 0))


