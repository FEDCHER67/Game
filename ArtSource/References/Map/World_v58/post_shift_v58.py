"""Сдвиги v58 (TASK-000782), растровая деформация готовой картинки 5 px/м (все координаты скрипта карты — ДО сдвига).
Холст растёт на GROW_TOP_M = 25 м вверх (новые ряды — море): мир y -> пиксель py = 3500 - 5 y + 1250 (было + 1125), высота 950 м.
Смещение точки (м):
  юго-восток (Даунтаун, пляж, Элит): dx = +20, dy = -28 (правее и ниже, дальше от холма B), маска m1 = r(x, 690, 770) * (1 - r(y, 470, 560));
  Неблагополучный, его северный берег, пирс погранпоста: dy = +22 (выше, дальше от холма B), маска m2 = r(x, 642, 660) * (1 - r(x, 1000, 1040)) * r(y, 560, 650).
Запад, холм B (кроме подножий), Порт и Трамдуро не двигаются. Без numpy: PIL MESH."""
from PIL import Image

GROW_TOP_M = 25.0
SEA = (171, 211, 225)


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def shift_m(x, y):
    m1 = r(x, 690.0, 770.0) * (1.0 - r(y, 470.0, 560.0))
    m2 = r(x, 642.0, 660.0) * (1.0 - r(x, 1000.0, 1040.0)) * r(y, 560.0, 650.0)   # широкая полоса — без вытянутых деревьев
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
    return im.convert('RGB').transform((W, H + grow), Image.MESH, mesh, Image.BILINEAR, fillcolor=SEA)


# --- деревья в полосах растяжения: убрать из растра и нарисовать кругами поверх уже сдвинутой картинки (не вытягиваются)
import os
import re
import subprocess

TREE_STROKES = ('#86A274', '#6F915E', '#5F8452', '#4E7A4A')
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


def render_shifted(svg, out_png, W, H, top_px=1125, min_stretch=0.02):
    """Рендер svg (W x H, 5 px/м), сдвиг shift_image, деревья полос растяжения — поверх кругами. Возвращает картинку."""
    grow = int(GROW_TOP_M * 5)
    picks, stack = [], []
    for m in re.finditer(r'<(/?)(g|circle)\b([^>]*)>', svg):
        close, name, attrs = m.groups()
        if name == 'g':
            if close:
                if stack:
                    stack.pop()
            elif not attrs.rstrip().endswith('/'):
                f = re.search(r'filter="([^"]+)"', attrs)
                stack.append(('transform=' in attrs, f.group(1) if f else None))
            continue
        st = re.search(r'stroke="(#\w+)"', attrs)
        if not st or st.group(1) not in TREE_STROKES or any(t for t, _ in stack):
            continue
        cx, cy = float(re.search(r'cx="([-\d.]+)"', attrs).group(1)), float(re.search(r'cy="([-\d.]+)"', attrs).group(1))
        x, y = (cx + 350) / 5.0, (3500 - cy) / 5.0
        if _stretch(x, y) < min_stretch:
            continue
        filt = next((f for _, f in reversed(stack) if f), None)
        picks.append((m.start(), m.end(), cx, cy, x, y, attrs, filt))
    base, pos = [], 0
    for a, b, *_ in picks:
        base.append(svg[pos:a])
        pos = b
    base.append(svg[pos:])
    tmp = out_png + '.base.png'
    _render(''.join(base), tmp, W, H)
    im = shift_image(Image.open(tmp), top_px).convert('RGBA')
    os.remove(tmp)
    if picks:
        head = re.search(r'<svg[^>]*>', svg).group(0)
        head = re.sub(r'height="\d+"', 'height="%d"' % (H + grow), head)
        head = re.sub(r'viewBox="([-\d.]+) ([-\d.]+) ([\d.]+) ([\d.]+)"',
                      lambda q: 'viewBox="%s %s %s %s"' % (q.group(1), float(q.group(2)) - grow, q.group(3), float(q.group(4)) + grow), head)
        defs = re.search(r'<defs>.*?</defs>', svg, re.S).group(0)
        body, cur = [], 'none'
        for _, _, cx, cy, x, y, attrs, filt in picks:
            if (filt or 'none') != cur:
                if cur != 'none' or body:
                    body.append('</g>')
                body.append('<g filter="%s">' % filt if filt else '<g>')
                cur = filt or 'none'
            dx, dy = shift_m(x, y)
            a2 = re.sub(r'cx="[-\d.]+"', 'cx="%.1f"' % (cx + dx * 5), attrs)
            a2 = re.sub(r'cy="[-\d.]+"', 'cy="%.1f"' % (cy - dy * 5), a2)
            body.append('<circle%s>' % a2)
        body.append('</g>')
        tmp = out_png + '.trees.png'
        _render(head + defs + ''.join(body) + '</svg>', tmp, W, H + grow, transparent=True)
        ov = Image.open(tmp).convert('RGBA')
        os.remove(tmp)
        im = Image.alpha_composite(im, ov)
    print('trees redrawn over the shift bands:', len(picks))
    return im.convert('RGB')
