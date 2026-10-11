import sys
from PIL import Image, ImageDraw
src, out, x0, y0, x1, y1, scale = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:8])
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1))
im = im.resize(((x1-x0)*scale, (y1-y0)*scale), Image.NEAREST)
d = ImageDraw.Draw(im)
step = 10 if (x1-x0) <= 300 else 50
for x in range((x0//step+1)*step, x1, step):
    X = (x-x0)*scale; d.line([(X,0),(X,im.height)], fill=(255,0,255) if x%50==0 else (255,180,255), width=1)
    if x % 50 == 0: d.text((X+2, 2), str(x), fill=(255,0,255))
for y in range((y0//step+1)*step, y1, step):
    Y = (y-y0)*scale; d.line([(0,Y),(im.width,Y)], fill=(0,200,255) if y%50==0 else (160,230,255), width=1)
    if y % 50 == 0: d.text((2, Y+2), str(y), fill=(0,120,255))
im.save(out)
