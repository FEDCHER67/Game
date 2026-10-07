"""Review sheets and MP4 previews from rendered frames (system Python + Pillow + ffmpeg).

  python make_previews.py grid <frames_dir> <out.png> [--cols 8] [--size 200] [--title T]
      one labelled row-major grid per view sub-folder (frame names f0001.00.png from build_crowd.py)
  python make_previews.py mp4 <frames_dir> <out_stem> [--loops 3]
      <out_stem>_<view>.mp4 per view sub-folder (frames named s0000.png, i.e. build_crowd.py --seq --every 1);
      for loops the duplicated last frame is dropped and the clip is repeated --loops times
Refuses to overwrite existing outputs.
"""
import sys, re, argparse, subprocess, tempfile, shutil
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=('grid', 'mp4'))
ap.add_argument('src')
ap.add_argument('out')
ap.add_argument('--cols', type=int, default=8)
ap.add_argument('--size', type=int, default=200)
ap.add_argument('--title', default='')
ap.add_argument('--fps', type=float, default=30.0)
ap.add_argument('--loops', type=int, default=1)
a = ap.parse_args()
src = Path(a.src)
font = ImageFont.load_default()
BG = (35, 39, 46)


def frame_of(p):
    m = re.search(r'f(\d+(?:\.\d+)?)', p.stem)
    return float(m.group(1)) if m else 0.0


views = [d.name for d in sorted(src.iterdir()) if d.is_dir()]
if a.mode == 'grid':
    out = Path(a.out)
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    blocks = []
    for v in views:
        files = sorted((src / v).glob('f*.png'), key=frame_of)
        rows = (len(files) + a.cols - 1) // a.cols
        s = a.size
        img = Image.new('RGB', (a.cols * s, 16 + rows * (s + 14)), BG)
        d = ImageDraw.Draw(img)
        d.text((4, 2), '%s | %s' % (a.title, v), fill='white', font=font)
        for i, f in enumerate(files):
            x, y = (i % a.cols) * s, 16 + (i // a.cols) * (s + 14)
            img.paste(Image.open(f).convert('RGB').resize((s, s), Image.LANCZOS), (x, y))
            fr = frame_of(f)
            d.text((x + 3, y + s + 1), 'f%g %.2fs' % (fr, (fr - 1) / a.fps), fill='white', font=font)
        blocks.append(img)
    W = max(b.width for b in blocks)
    sheet = Image.new('RGB', (W, sum(b.height for b in blocks)), BG)
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height
    sheet.save(out)
    print(out)
else:
    for v in views:
        dst = Path('%s_%s.mp4' % (a.out, v))
        if dst.exists():
            sys.exit('Refusing overwrite: %s' % dst)
        files = sorted((src / v).glob('s*.png'))
        if a.loops > 1:
            files = files[:-1] * a.loops
        tmp = Path(tempfile.mkdtemp())
        for i, f in enumerate(files):
            shutil.copy(f, tmp / ('i%05d.png' % i))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-n', '-framerate', str(a.fps), '-i', str(tmp / 'i%05d.png'),
                        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', '-movflags', '+faststart', str(dst)], check=True)
        shutil.rmtree(tmp)
        print(dst)
