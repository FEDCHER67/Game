"""Сдвиги v76 (TASK-000832) = как v75 (TASK-000828) = как v74 (TASK-000827) = как v73 (TASK-000802, полоса Неблагополучного по x слева — широкая 430..540; как v63; правый край полосы Неблагополучного 1090..1130; как v59; как v58, полоса Неблагополучного по x — 505..520, западнее продолжения хребта), растровая деформация готовой картинки 5 px/м (все координаты скрипта карты — ДО сдвига).
Холст растёт на GROW_TOP_M = 25 м вверх (новые ряды — море): мир y -> пиксель py = 3500 - 5 y + 1250 (было + 1125), высота 950 м.
Смещение точки (м):
  юго-восток (Даунтаун, пляж, Элит): dx = +20, dy = -28 (правее и ниже, дальше от холма B), маска m1 = r(x, 690, 770) * (1 - r(y, 470, 560));
  Неблагополучный, его северный берег, пирс погранпоста: dy = +22 (выше, дальше от холма B), маска m2 = r(x, 430, 540) * (1 - r(x, 1090, 1130)) * r(y, 560, 650).
Запад, холм B (кроме подножий), Порт и Трамдуро не двигаются. Без numpy: PIL MESH."""
from PIL import Image

GROW_TOP_M = 25.0
SEA = (171, 211, 225)


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shift_m(x, y):
    m1 = r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))
    m2 = r(x, 430.0, 540.0) * (1.0 - r(x, 1090.0, 1130.0)) * r(y, 560.0, 650.0)   # широкая полоса — без вытянутых деревьев
    return 20.0 * m1, -28.0 * m1 + 22.0 * m2


def shift_image(im, top_px=1125, cell=20):
    """im: картинка 5 px/м, мир y = (3500 + top_px - py) / 5. Возвращает картинку выше на GROW_TOP_M (top_px + 125)."""
    W, H = im.size
    grow = int(GROW_TOP_M * 5)
    new_top = top_px + grow

    def src(X, Y):
        xm, ym = X / 5.0, (3500.0 + new_top - Y) / 5.0
        dx, dy = shift_m(xm, ym)
        return X - dx * 5.0, 3500.0 + top_px - (ym - dy) * 5.0

    mesh = []
    for y0 in range(0, H + grow, cell):
        y1 = min(H + grow, y0 + cell)
        for x0 in range(0, W, cell):
            x1 = min(W, x0 + cell)
            ul, ll, lr, ur = src(x0, y0), src(x0, y1), src(x1, y1), src(x1, y0)
            mesh.append(((x0, y0, x1, y1), (ul[0], ul[1], ll[0], ll[1], lr[0], lr[1], ur[0], ur[1])))
    out = im.convert('RGB').transform((W, H + grow), Image.MESH, mesh, Image.BILINEAR, fillcolor=SEA)
    # v62: над Неблагополучным степь до края — верхние ряды без данных (сдвиг 22 < рост 25) заполнить рядом ниже
    # v66: север — степь: пустые верхние ряды (море из fillcolor) над сушей x 60..1382 залить первым непустым рядом столбца
    px = out.load()
    for X in range(60 * 5, 1100 * 5):
        Y = 0
        while Y < grow + 6 and all(abs(c - d) < 3 for c, d in zip(px[X, Y], SEA)):
            Y += 1
        if 0 < Y < grow + 6:
            c = px[X, Y + 1]
            for k in range(Y + 1):
                px[X, k] = c
    return out


# --- деревья в полосах растяжения: убрать из растра и нарисовать кругами поверх уже сдвинутой картинки (не вытягиваются)
import os
import re
import subprocess

TREE_STROKES = ('#86A274', '#6F915E', '#5F8452', '#4E7A4A', '#3F6343')
CHROME = r'C:\Program Files\Google\Chrome\Application\chrome.exe'


def _stretch(x, y, h=1.0):
    dx0, dy0 = shift_m(x, y)
    a = shift_m(x + h, y)
    b = shift_m(x, y + h)
    return max(abs(a[0] - dx0), abs(a[1] - dy0), abs(b[0] - dx0), abs(b[1] - dy0)) / h


def _render(html_body, out_png, W, H, transparent=False):
    html = out_png + '.html'
    bg = 'transparent' if transparent else '#ffffff'
    open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0;background:%s">' % bg + html_body + '</body></html>')
    args = [CHROME, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files',
            '--screenshot=' + out_png, '--window-size=%d,%d' % (W, H)]
    if transparent:
        args.append('--default-background-color=00000000')
    subprocess.run(args + ['file:///' + html.replace(chr(92), '/')], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    os.remove(html)


def _group_span(svg, gid):
    a = svg.index('<g id="%s"' % gid)
    depth, pos = 0, a
    for m in re.finditer(r'<(/?)g\b[^>]*?(/?)>', svg[a:]):
        if m.group(1):
            depth -= 1
        elif not m.group(2):
            depth += 1
        if depth == 0:
            return a, a + m.end()
    return a, len(svg)


def render_shifted(svg, out_png, W, H, top_px=1125, min_stretch=0.02, frame_gid='L12_title_legend'):
    """Рендер svg (W x H, 5 px/м), сдвиг shift_image; деревья и подписи полос растяжения — поверх, без искажения;
    рамка/заголовок/легенда — поверх, растянуты на новый холст. Возвращает картинку."""
    grow = int(GROW_TOP_M * 5)
    frame = ''
    if frame_gid and ('<g id="%s"' % frame_gid) in svg:
        fa, fb = _group_span(svg, frame_gid)
        frame, svg = svg[fa:fb], svg[:fa] + svg[fb:]
    picks, stack = [], []
    for m in re.finditer(r'<(/?)g\b([^>]*)>|<circle\b([^>]*)>|<text\b([^>]*)>(.*?)</text>', svg, re.S):
        tag = m.group(0)
        if tag.startswith('<g') or tag.startswith('</g'):
            if m.group(1):
                if stack:
                    stack.pop()
            elif not (m.group(2) or '').rstrip().endswith('/'):
                f = re.search(r'filter="([^"]+)"', m.group(2) or '')
                tr = re.search(r'transform="([^"]+)"', m.group(2) or '')
                tt = re.fullmatch(r'\s*translate\(\s*([-\d.]+)[\s,]+([-\d.]+)\s*\)\s*', tr.group(1)) if tr else None
                stack.append((bool(tr) and not tt, f.group(1) if f else None, (float(tt.group(1)), float(tt.group(2))) if tt else (0.0, 0.0)))
            continue
        if any(t[0] for t in stack):
            continue
        ox, oy = sum(t[2][0] for t in stack), sum(t[2][1] for t in stack)
        if tag.startswith('<circle'):
            attrs = m.group(3)
            st = re.search(r'stroke="(#\w+)"', attrs)
            if not st or st.group(1) not in TREE_STROKES:
                continue
            kx, ky = 'cx', 'cy'
        else:
            attrs = m.group(4)
            kx, ky = 'x', 'y'
        mx, my = re.search(r'\b%s="([-\d.]+)"' % kx, attrs), re.search(r'\b%s="([-\d.]+)"' % ky, attrs)
        if not (mx and my):
            continue
        px, py = float(mx.group(1)) + ox, float(my.group(1)) + oy
        x, y = (px + 350) / 5.0, (3500 - py) / 5.0
        span = (-25.0, -12.0, 0.0, 12.0, 25.0) if kx == 'x' else (0.0,)   # подпись широкая: проверяем по её длине
        if max(_stretch(x + e, y) for e in span) < min_stretch:
            continue
        dx, dy = shift_m(x, y)
        moved = tag.replace(mx.group(0), '%s="%.1f"' % (kx, px + dx * 5), 1).replace(my.group(0), '%s="%.1f"' % (ky, py - dy * 5), 1)
        filt = next((t[1] for t in reversed(stack) if t[1]), None)
        picks.append((m.start(), m.end(), moved, filt))
    base, pos = [], 0
    for a, b, *_ in picks:
        base.append(svg[pos:a])
        pos = b
    base.append(svg[pos:])
    tmp = out_png + '.base.png'
    _render(''.join(base), tmp, W, H)
    im = shift_image(Image.open(tmp), top_px).convert('RGBA')
    os.remove(tmp)
    if picks or frame:
        head = re.search(r'<svg[^>]*>', svg).group(0)
        head = re.sub(r'height="\d+"', 'height="%d"' % (H + grow), head)
        vb = re.search(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"', head)
        top_u = float(vb.group(2))
        head = head.replace(vb.group(0), 'viewBox="%s %s %s %s"' % (vb.group(1), top_u - grow, vb.group(3), float(vb.group(4)) + grow))
        defs = re.search(r'<defs>.*?</defs>', svg, re.S).group(0)
        body, cur = [], None
        for _, _, moved, filt in picks:
            if filt != cur or not body:
                if body:
                    body.append('</g>')
                body.append('<g filter="%s">' % filt if filt else '<g>')
                cur = filt
            body.append(moved)
        if body:
            body.append('</g>')
        if frame:
            k = (H + grow) / float(H)
            body.append('<g transform="translate(0 %s) scale(1 %s) translate(0 %s)">' % (top_u - grow, k, -top_u) + frame + '</g>')
        tmp = out_png + '.over.png'
        _render(head + defs + ''.join(body) + '</svg>', tmp, W, H + grow, transparent=True)
        ov = Image.open(tmp).convert('RGBA')
        os.remove(tmp)
        im = Image.alpha_composite(im, ov)
    print('redrawn over the shift bands:', len(picks), 'items; frame overlay:', bool(frame))
    return im.convert('RGB')
