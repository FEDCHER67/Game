"""Previews from rendered frames (system Python + Pillow; ffmpeg for the MP4s). Refuses to overwrite outputs.

  python make_previews_forest.py grid  <frames_dir> <out.png> [--cols 10] [--size 180] [--title T] [--every 3]
      labelled grid per view sub-folder from frames named s0000.png (build_forest.py --seq --every 1), every Nth
  python make_previews_forest.py mp4   <frames_dir> <out_stem> [--loops 3] [--ffmpeg <exe>]
      <out_stem>_<view>.mp4 per view sub-folder; loops drop the duplicated last frame and repeat --loops times
  python make_previews_forest.py gif   <frames_dir>/<view> <out.gif> [--width 480] [--fps 15] [--max-mb 4] [--loop-clip] [--src-fps 30]
      looping GIF (shared palette, shrinks itself until it fits the size limit; --loop-clip drops the duplicated last
      frame of a loop clip)
  python make_previews_forest.py sheet <out.png> <clip=frames_dir/view> [<clip=...> ...] [--rows 6] [--size 240] [--src-fps 30]
      one contact sheet, the clips side by side (one column per clip, evenly spaced frames down the column)

ffmpeg: --ffmpeg, else $FFMPEG, else ffmpeg on PATH, else Krita's bundled ffmpeg.exe. Codec: libx264 when the build
has it, else libopenh264.
"""
import sys, os, re, argparse, shutil, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

BG = (35, 39, 46)
FONT = ImageFont.load_default()


def seq(folder):
    return sorted(Path(folder).glob('s*.png'))


def find_ffmpeg(arg):
    for c in (arg, os.environ.get('FFMPEG'), shutil.which('ffmpeg'),
              str(Path.home() / 'Krita (x64)' / 'bin' / 'ffmpeg.exe')):
        if c and Path(c).exists():
            return c
    sys.exit('ffmpeg not found (pass --ffmpeg)')


def grid(a):
    src, out = Path(a.src), Path(a.out)
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    blocks = []
    for v in [d.name for d in sorted(src.iterdir()) if d.is_dir()]:
        files = seq(src / v)
        idx = list(range(0, len(files), a.every))
        if idx[-1] != len(files) - 1:
            idx.append(len(files) - 1)
        rows = (len(idx) + a.cols - 1) // a.cols
        s = a.size
        img = Image.new('RGB', (a.cols * s, 16 + rows * (s + 14)), BG)
        d = ImageDraw.Draw(img)
        d.text((4, 2), '%s | %s' % (a.title, v), fill='white', font=FONT)
        for k, i in enumerate(idx):
            x, y = (k % a.cols) * s, 16 + (k // a.cols) * (s + 14)
            img.paste(Image.open(files[i]).convert('RGB').resize((s, s), Image.LANCZOS), (x, y))
            d.text((x + 3, y + s + 1), 'f%d %.2fs' % (i + 1, i / 30.0), fill='white', font=FONT)
        blocks.append(img)
    W = max(b.width for b in blocks)
    sheet = Image.new('RGB', (W, sum(b.height for b in blocks)), BG)
    y = 0
    for b in blocks:
        sheet.paste(b, (0, y))
        y += b.height
    sheet.save(out)
    print(out)


def mp4(a):
    src = Path(a.src)
    exe = find_ffmpeg(a.ffmpeg)
    enc = subprocess.run([exe, '-hide_banner', '-encoders'], capture_output=True, text=True).stdout
    codec = ['-c:v', 'libx264', '-crf', '18'] if 'libx264' in enc else ['-c:v', 'libopenh264', '-b:v', '3M']
    for v in [d.name for d in sorted(src.iterdir()) if d.is_dir()]:
        dst = Path('%s_%s.mp4' % (a.out, v))
        if dst.exists():
            sys.exit('Refusing overwrite: %s' % dst)
        files = seq(src / v)
        if a.loops > 1:
            files = files[:-1] * a.loops
        tmp = Path(tempfile.mkdtemp())
        for i, f in enumerate(files):
            shutil.copy(f, tmp / ('i%05d.png' % i))
        subprocess.run([exe, '-loglevel', 'error', '-n', '-framerate', '30', '-i', str(tmp / 'i%05d.png')] + codec +
                       ['-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(dst)], check=True)
        shutil.rmtree(tmp)
        print(dst)


def gif(a):
    src, out = Path(a.src), Path(a.out)
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    files = seq(src)
    if a.loop_clip:
        files = files[:-1]                      # loops: the last frame duplicates the first
    width, fps, colors = a.width, a.fps, 128
    for attempt in range(8):
        step = max(1, round(a.src_fps / fps))
        pick = files[::step]
        frames = []
        for f in pick:
            im = Image.open(f).convert('RGB')
            h = round(im.height * width / im.width)
            frames.append(im.resize((width, h), Image.LANCZOS))
        sample = Image.new('RGB', (width, h * 4))
        for i in range(4):
            sample.paste(frames[i * (len(frames) - 1) // 3], (0, h * i))
        pal = sample.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        q = [fr.quantize(palette=pal, dither=Image.Dither.NONE) for fr in frames]
        tmp = out.with_suffix('.tmp.gif')
        q[0].save(tmp, save_all=True, append_images=q[1:], duration=round(1000 * step / a.src_fps), loop=0, optimize=True,
                  disposal=1)
        mb = tmp.stat().st_size / 1e6
        print('gif try %d: %d px, %d fps, %d colours -> %.2f MB' % (attempt, width, round(a.src_fps / step), colors, mb))
        if mb <= a.max_mb:
            tmp.replace(out)
            print(out)
            return
        tmp.unlink()
        if colors > 64:
            colors = 64
        elif fps > 12:
            fps = 12
        else:
            width = int(width * 0.85)
    sys.exit('could not fit the GIF under %.1f MB' % a.max_mb)


def sheet(a):
    out = Path(a.out)
    if out.exists():
        sys.exit('Refusing overwrite: %s' % out)
    cols = []
    for spec in a.items:
        name, folder = spec.split('=', 1)
        cols.append((name, seq(folder)))
    s, rows = a.size, a.rows
    head = 22
    img = Image.new('RGB', (s * len(cols), head + rows * (s + 14)), BG)
    d = ImageDraw.Draw(img)
    for c, (name, files) in enumerate(cols):
        d.text((c * s + 6, 5), name, fill='white', font=FONT)
        n = len(files) - 1
        for r in range(rows):
            i = round(r * n / (rows - 1))
            x, y = c * s, head + r * (s + 14)
            img.paste(Image.open(files[i]).convert('RGB').resize((s, s), Image.LANCZOS), (x, y))
            d.text((x + 4, y + s + 1), '%.2f s' % (i / a.src_fps), fill='white', font=FONT)
    img.save(out)
    print(out)


ap = argparse.ArgumentParser()
ap.add_argument('mode', choices=('grid', 'mp4', 'gif', 'sheet'))
ap.add_argument('src')
ap.add_argument('out', nargs='?')
ap.add_argument('items', nargs='*')
ap.add_argument('--cols', type=int, default=10)
ap.add_argument('--size', type=int, default=180)
ap.add_argument('--every', type=int, default=3)
ap.add_argument('--title', default='')
ap.add_argument('--loops', type=int, default=1)
ap.add_argument('--ffmpeg', default='')
ap.add_argument('--width', type=int, default=480)
ap.add_argument('--fps', type=int, default=15)
ap.add_argument('--src-fps', dest='src_fps', type=float, default=30.0)
ap.add_argument('--max-mb', dest='max_mb', type=float, default=4.0)
ap.add_argument('--loop-clip', dest='loop_clip', action='store_true')
ap.add_argument('--rows', type=int, default=6)
a = ap.parse_args()
if a.mode == 'sheet':                       # sheet <out.png> <clip=dir> ...
    a.items = [a.out] + a.items if a.out else a.items
    a.out = a.src
{'grid': grid, 'mp4': mp4, 'gif': gif, 'sheet': sheet}[a.mode](a)
