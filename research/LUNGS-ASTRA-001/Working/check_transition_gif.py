from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
gif=Image.open(ROOT/'Previews'/'12_good_to_bad_transition.gif')
assert gif.n_frames==75
durations=[];samples=[]
for index in range(gif.n_frames):
    gif.seek(index)
    durations.append(gif.info.get('duration',0))
    if index in (0,15,30,45,60,74):samples.append(gif.convert('RGB').resize((240,240)))
sheet=Image.new('RGB',(240*len(samples),240))
for index,sample in enumerate(samples):sheet.paste(sample,(240*index,0))
out=ROOT/'Working'/'transition_contact_sheet.png'
sheet.save(out)
print('FRAMES',gif.n_frames,'DURATION_MS',sum(durations),'SAMPLE_DURATIONS',sorted(set(durations)),'CONTACT_SHEET',out)
