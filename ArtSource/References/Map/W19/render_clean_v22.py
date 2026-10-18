"""Чистый рендер карты v22 для сборки макета в Unity: без подписей, легенды и заголовка (5 px/м, как FINAL_v22)."""
import os
import re
import subprocess

OUTD = r'C:\Users\chern_0eqkb03\Desktop\Map\Итоговая карта'
HERE = os.path.dirname(os.path.abspath(__file__))
s = open(os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v22.svg'), encoding='utf-8').read()
for gid in ('L11_labels', 'L12_title_legend'):
    s = s.replace('<g id="%s"' % gid, '<g visibility="hidden" id="%s"' % gid, 1)
s = re.sub(r'<rect x="-348" y="[-\d]+" width="7366" height="\d+"[^>]*/>', '', s)
s = re.sub(r'<rect x="-314" y="[-\d]+" width="7298" height="\d+"[^>]*/>', '', s)
out = os.path.join(HERE, 'MAP_v22_clean_5pxm.png')
html = os.path.join(HERE, '_clean_render.html')
open(html, 'w', encoding='utf-8').write('<html><head><meta charset="utf-8"></head><body style="margin:0">' + s + '</body></html>')
chrome = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
subprocess.run([chrome, '--headless=new', '--disable-gpu', '--hide-scrollbars', '--allow-file-access-from-files', '--screenshot=' + out,
                '--window-size=7370,4200', 'file:///' + html.replace(chr(92), '/')], check=True,
               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
os.remove(html)
print('ok', out)
