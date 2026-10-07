"""Assemble preview media from rendered walk frames (system Python 3 with Pillow, plus ffmpeg on PATH).

  python make_previews_v03.py [--frames Previews/frames_v03] [--stem Walk_v03] [--loops 6]

Writes into Previews/ (refuses to overwrite): <stem>_side.mp4, <stem>_threequarter.mp4 (30 fps,
several in-place cycles), <stem>_side_threequarter.mp4 (both views side by side) and
<stem>_contact_sheet.png (contact / down / passing / up for both steps, both views).
"""
from pathlib import Path
import argparse
import subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('--frames', default=str(HERE / 'Previews' / 'frames_v03'))
ap.add_argument('--stem', default='Walk_v03')
ap.add_argument('--loops', type=int, default=6)
ap.add_argument('--cycle', type=int, default=20)
# Key poses of the cycle (1-based frames): left step then right step.
ap.add_argument('--poses', default='1:Contact L,3:Down,6:Passing,8:Up,11:Contact R,13:Down,16:Passing,18:Up')
a = ap.parse_args()
frames = Path(a.frames)
out = HERE / 'Previews'
targets = [out / f'{a.stem}_{n}' for n in ('side.mp4', 'threequarter.mp4', 'side_threequarter.mp4', 'contact_sheet.png')]
for t in targets:
    assert not t.exists(), f'Refusing to overwrite {t}'
extra = a.cycle * (a.loops - 1)


def encode(view, target):
    subprocess.run(['ffmpeg', '-v', 'error', '-framerate', '30', '-i', str(frames / view / 'f%03d.png'),
                    '-vf', f'loop=loop={a.loops - 1}:size={a.cycle}:start=0', '-r', '30',
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', str(target)], check=True)


encode('side', targets[0])
encode('threequarter', targets[1])
subprocess.run(['ffmpeg', '-v', 'error', '-i', str(targets[0]), '-i', str(targets[1]),
                '-filter_complex', 'hstack=inputs=2', '-r', '30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                '-crf', '18', str(targets[2])], check=True)

poses = [(int(p.split(':')[0]), p.split(':')[1]) for p in a.poses.split(',')]
sample = Image.open(frames / 'side' / 'f001.png')
w, h = sample.size
scale = 0.5
tw, th = int(w * scale), int(h * scale)
pad, label_h = 6, 26
sheet = Image.new('RGB', (len(poses) * (tw + pad) + pad, 2 * (th + label_h + pad) + pad), (40, 42, 48))
draw = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype('arial.ttf', 16)
except OSError:
    font = ImageFont.load_default()
for row, view in enumerate(('side', 'threequarter')):
    for col, (f, name) in enumerate(poses):
        img = Image.open(frames / view / f'f{f:03}.png').convert('RGB').resize((tw, th), Image.LANCZOS)
        x = pad + col * (tw + pad)
        y = pad + row * (th + label_h + pad)
        draw.text((x + 4, y + 4), f'{name}  f{f}', fill=(235, 235, 235), font=font)
        sheet.paste(img, (x, y + label_h))
sheet.save(targets[3])
print('PREVIEWS', *[t.name for t in targets])
