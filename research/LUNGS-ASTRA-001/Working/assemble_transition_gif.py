"""Assemble the Blender transition frames at their sampled 15 fps cadence."""
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
paths=sorted((ROOT/'Working'/'TransitionFrames').glob('frame_*.png'))
assert len(paths)==75,len(paths)
rgb=[Image.open(path).convert('RGB') for path in paths]
palette=rgb[0].quantize(colors=192,method=Image.Quantize.MEDIANCUT)
frames=[im.quantize(palette=palette) for im in rgb]
out=ROOT/'Previews'/'12_good_to_bad_transition.gif'
durations=[60 if i%3==0 else 70 for i in range(len(frames))]
frames[0].save(out,save_all=True,append_images=frames[1:],duration=durations,loop=0,disposal=2,optimize=False)
print(out, out.stat().st_size, 'bytes', len(frames), 'frames')
