"""Чистый рендер карты v33 для сборки макета в Unity: без подписей, легенды, заголовка, видовых точек и высот (5 px/м)."""
import os
import re
import subprocess

OUTD = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта'
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v33.svg'), encoding='utf-8').read()
for gid in ('L11_labels', 'L12_title_legend', 'R24_labels', 'R33_tunnel'):
    s = s.replace('<g id="%s"' % gid, '<g visibility="hidden" id="%s"' % gid, 1)
s = re.sub(r'<rect x="-348" y="[-\d.]+" width="[\d.]+" height="[\d.]+"[^>]*/>', '', s)
s = re.sub(r'<rect x="-314" y="[-\d.]+" width="[\d.]+" height="[\d.]+"[^>]*/>', '', s)
m = re.search(r'<svg[^>]*width="(\d+)" height="(\d+)"', s)
W, H = m.group(1), m.group(2)
out = os.path.join(HERE, 'MAP_v33_clean_5pxm.png')
html = os.path.join(HERE, '_clean_render.html')
open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0">' + s + '</body></html>')
chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files', '--screenshot=' + out,
                '--window-size=%s,%s' % (W, H), 'file:///' + html.replace(chr(92), '/')], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.remove(html)
print('ok', out, W, H)
