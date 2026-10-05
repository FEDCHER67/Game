#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Deterministic cartoon placeholders. Dependency: NumPy only (plus stdlib).

Run: python -B gen_sfx.py. Recheck saved PCM: python -B gen_sfx.py --validate-only.
No samples, voice recordings, external tools or downloaded sound assets used.
"""
import argparse
import hashlib
import json
import math
import struct
import wave
import zlib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'Out' / 'v01'
SR = 44100
PEAK = 10 ** (-1 / 20)
SEED = 510512
GROUPS = [
    ('punch_bonk', 3), ('slap', 2), ('body_thud_ground', 3),
    ('body_thud_van_floor', 2), ('van_door_open', 1), ('van_door_close', 1),
    ('van_door_slam', 1), ('slide_door_open', 1), ('slide_door_close', 1),
    ('rear_door_open', 1), ('rear_door_close', 1),
    ('footstep_asphalt', 4), ('footstep_grass', 4), ('footstep_sand', 4),
    ('footstep_metal_floor', 4), ('npc_scream', 4), ('npc_mumble_gibberish', 4),
    ('npc_whimper', 2), ('npc_gasp', 2), ('police_siren_short', 1),
    ('phone_buzz', 1), ('cash_register', 1), ('organ_squish', 3),
]


def timebase(seconds):
    return np.arange(round(seconds * SR), dtype=np.float64) / SR


def osc(t, frequency):
    f = np.broadcast_to(frequency, t.shape)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def fade(x, attack=.006, release=.024):
    x = x.copy()
    a, b = min(len(x), round(attack * SR)), min(len(x), round(release * SR))
    x[:a] *= np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    x[-b:] *= np.sin(np.linspace(np.pi / 2, 0, b)) ** 2
    x[0] = x[-1] = 0
    return x


def noise(t, rng, low=50, high=6000):
    """Smooth FFT band shaping; no SciPy dependency."""
    spectrum = np.fft.rfft(rng.normal(size=len(t)))
    f = np.fft.rfftfreq(len(t), 1 / SR)
    shape = (1 - np.exp(-(f / low) ** 4)) * np.exp(-(f / high) ** 4)
    x = np.fft.irfft(spectrum * shape, n=len(t))
    return x / max(np.std(x), 1e-9)


def impact(t, rng, pitch=130, decay=.07, metal=False):
    body = osc(t, pitch * (1 + 1.3 * np.exp(-t * 36))) * np.exp(-t / decay)
    tick = noise(t, rng, 300, 8500) * np.exp(-t / .014)
    x = body + .22 * tick
    if metal:
        for f, a in [(423, .3), (917, .2), (1743, .11)]:
            x += a * np.sin(2 * np.pi * f * t) * np.exp(-t / (.15 + f / 14000))
    return fade(x, .0015, .025)


def place(dst, sample, at):
    start = round(at * SR)
    end = min(len(dst), start + len(sample))
    dst[start:end] += sample[:end-start]


def voice(t, pitch, formants, breath, rng):
    """Harmonic source filtered by moving Gaussian vowel formants.

    Formants and fundamental are sample-varying; formant centres actually sweep,
    independently of pitch. Harmonics are capped below Nyquist.
    """
    f0 = np.broadcast_to(pitch, t.shape)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    x = np.zeros_like(t)
    for harmonic in range(1, min(100, int(18000 / np.max(f0))) + 1):
        hz = harmonic * f0
        gain = .05 / harmonic
        for center, width, level in zip(formants, [110, 180, 260], [1, .65, .3]):
            gain = gain + level * np.exp(-.5 * ((hz - center) / width) ** 2) / harmonic ** .45
        x += gain * np.sin(harmonic * phase)
    return x + breath * noise(t, rng, 450, 5200)


def synth(name, variant, rng):
    v = variant - 1
    stretch = 1 + .07 * v
    if name == 'punch_bonk':
        t = timebase(.36 * stretch)
        x = impact(t, rng, 170 - 18*v, .055)
        x += .5 * osc(t, 520 * np.exp(-t * 4) + 140) * np.exp(-t * 12)
    elif name == 'slap':
        t = timebase(.23 * stretch)
        x = noise(t, rng, 650, 8200) * np.exp(-t / .021)
        x += .4 * osc(t, 340 - 50*v) * np.exp(-t / .04)
        place(x, fade(noise(timebase(.055), rng, 850, 6300) * np.exp(-timebase(.055)*65), .002, .015), .025)
    elif name.startswith('body_thud'):
        t = timebase(.43 * stretch)
        metal = name.endswith('van_floor')
        x = impact(t, rng, 74 + 9*v, .085, metal)
        x += .38 * noise(t, rng, 35, 380) * np.exp(-t / .11)
        place(x, impact(timebase(.15), rng, 105, .045, metal) * .23, .115 + v*.009)
    elif 'door' in name:
        sliding = name.startswith('slide')
        opening = name.endswith('open')
        slam = name.endswith('slam')
        seconds = .9 if sliding else (.62 if opening else (.48 if slam else .56))
        t = timebase(seconds)
        x = np.zeros_like(t)
        travel = np.sin(np.pi * np.clip(t / (seconds-.12), 0, 1)) ** 2
        if sliding:
            x += .18 * noise(t, rng, 450, 3300) * travel
            x += .2 * osc(t, 70 + 45*np.sin(np.pi*t/seconds)) * travel
            x += .08 * np.sin(2*np.pi*1100*t) * travel * (1+np.sin(2*np.pi*18*t))
        elif opening:
            x += .18 * osc(t, 540 + 280*np.sin(np.pi*t/seconds)) * travel
            x += .07 * osc(t, 811 + 130*np.sin(2*np.pi*t/seconds)) * travel
        else:
            x += .08 * noise(t, rng, 120, 1700) * travel
        place(x, impact(timebase(.12), rng, 850, .025, True)*.24, .012)
        tail = .28 if slam else .18
        hit = impact(timebase(tail), rng, 80 if slam else (115 if name.startswith('rear') else 150), .07, True)
        place(x, hit * (1.5 if slam else .65), seconds-tail)
    elif name.startswith('footstep'):
        surface = name[9:]
        t = timebase((.26 if surface != 'sand' else .34) * stretch)
        settings = {'asphalt': (140, 6800, .035), 'grass': (320, 3300, .075),
                    'sand': (180, 2200, .095), 'metal_floor': (280, 7500, .025)}
        low, high, decay = settings[surface]
        x = .5 * noise(t, rng, low, high) * np.exp(-t / decay)
        x += impact(t, rng, 90+v*13, .035, surface == 'metal_floor') * (.7 if surface == 'metal_floor' else .3)
        if surface in ('grass', 'sand'):
            x *= .4 + .6*np.sin(np.pi*np.minimum(t/.10,1))**2
        place(x, impact(timebase(.09), rng, 120+v*5, .019)*.18, .065+v*.006)
    elif name == 'npc_scream':
        t = timebase(.85 * stretch)
        u = t / t[-1]
        f0 = 230+32*v + 220*np.sin(np.pi*u) + 12*np.sin(2*np.pi*(6+v)*t)
        x = voice(t, f0, [650+450*u, 1400+1000*u, 2900-600*u], .08, rng)
        x *= np.sin(np.pi*u)**.6
    elif name == 'npc_mumble_gibberish':
        t = timebase(1.12 * stretch)
        x = np.zeros_like(t)
        for j in range(5+v%2):
            seconds = rng.uniform(.10,.17)
            st = timebase(seconds)
            f0 = rng.uniform(100,180) + 25*np.sin(2*np.pi*st/seconds)
            vowels = rng.choice([350,550,750]), rng.choice([950,1500,2200]), 2700
            syllable = voice(st, f0, vowels, .025, rng)
            place(x, fade(syllable, .025, .035), .03+j*.18)
    elif name == 'npc_whimper':
        t = timebase(.8 * stretch)
        f0 = 200+v*50+65*np.sin(2*np.pi*3*t)+10*np.sin(2*np.pi*11*t)
        x = voice(t, f0, [380+180*t, 1300-300*t, 2400], .045, rng)
        x *= (.25+.75*np.sin(np.pi*3*t)**2)*np.sin(np.pi*t/t[-1])
    elif name == 'npc_gasp':
        t = timebase(.38 * stretch)
        env = (t/.04)*np.exp(-t/.045)
        x = noise(t, rng, 700, 5500) * env
        x += .12*voice(t, 290+v*60, [850,1700,2800], 0, rng)*env
    elif name == 'police_siren_short':
        t = timebase(1.8)
        f0 = 610+290*(.5+.5*np.sin(2*np.pi*1.8*t-np.pi/2))
        x = osc(t, f0) + .23*osc(t, f0*3) + .08*osc(t, f0*5)
    elif name == 'phone_buzz':
        t = timebase(.8)
        x = np.zeros_like(t)
        st = timebase(.22)
        buzz = osc(st, 145)*(1+.3*np.sin(2*np.pi*29*st))
        buzz += .27*osc(st,290)+.1*noise(st,rng,80,650)
        for at in [.02,.31,.58]:
            place(x, fade(buzz,.016,.026),at)
    elif name == 'cash_register':
        t = timebase(.8)
        x = np.zeros_like(t)
        for at in [.005,.075,.135]:
            place(x, impact(timebase(.10),rng,500,.025,True)*.25,at)
        st = timebase(.58)
        bell = sum(a*np.sin(2*np.pi*f*st)*np.exp(-st/d) for f,a,d in [(1320,1,.18),(2643,.3,.15),(3564,.15,.12)])
        place(x,fade(bell,.003,.045),.2)
    elif name == 'organ_squish':
        t = timebase(.46 * stretch)
        u = t/t[-1]
        x = noise(t,rng,100,1600)*np.sin(np.pi*u)**2*.5
        x += osc(t,280*np.exp(-t*9)+65+v*14)*np.exp(-t*8)
        for at in [.08,.19,.29]:
            st = timebase(.09)
            bubble = osc(st,600*np.exp(-st*25)+90)*np.sin(np.pi*st/st[-1])**2
            place(x,bubble*.32,at)
    else:
        raise ValueError(name)
    x = x - np.mean(x)
    x = fade(x, .008 if name.startswith('npc') else .006, .035)
    assert np.isfinite(x).all() and np.max(np.abs(x)) > 0
    return np.rint(x * PEAK / np.max(np.abs(x)) * 32767).astype('<i2')


# Tiny built-in 5x7 font: keeps contact-sheet rendering NumPy-only too.
FONT = dict(zip('abcdefghijklmnopqrstuvwxyz0123456789_.-', [
    '0e11111f111111','1e11111e11111e','0f10101010100f','1e11111111111e',
    '1f10101e10101f','1f10101e101010','0f10101311110f','1111111f111111',
    '0e04040404040e','0101010111110e','11121418141211','1010101010101f',
    '111b1515111111','11191513111111','0e11111111110e','1e11111e101010',
    '0e11111115120d','1e11111e141211','0f10100e01011e','1f040404040404',
    '1111111111110e','11111111110a04','11111115151b11','11110a040a1111',
    '11110a04040404','1f01020408101f','0e11131519110e','040c040404040e',
    '0e11010204081f','1e01010e01011e','02060a121f0202','1f10101e01011e',
    '0e10101e11110e','1f010204080808','0e11110e11110e','0e11110f01010e',
    '0000000000001f','00000000000c0c','0000001f000000']))


def label(img, x, y, string, color=(188,202,218)):
    for c in string.lower():
        bits = FONT.get(c, '00000000000000')
        for row in range(7):
            value = int(bits[row*2:row*2+2],16)
            for col in range(5):
                if value & (1 << (4-col)):
                    img[y+row*2:y+row*2+2,x+col*2:x+col*2+2] = color
        x += 12


def write_png(path, rgb):
    def chunk(kind, data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    h,w,_ = rgb.shape
    rows = b''.join(b'\x00'+row.tobytes() for row in rgb)
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',w,h,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(rows,9))+chunk(b'IEND',b''))


def contact_sheet(clips):
    cols, cw, ch = 3, 490, 126
    rows = math.ceil(len(clips)/cols)
    img = np.full((rows*ch+64, cols*cw, 3), (19,25,34),dtype=np.uint8)
    label(img,18,18,'cartoon sfx v01 - 51 clips - 44100 hz - mono')
    for index,(name,pcm) in enumerate(clips):
        x,y = (index%cols)*cw,(index//cols)*ch+60
        img[y:y+ch-5,x+5:x+cw-5] = (29,37,48)
        label(img,x+15,y+9,name.removesuffix('.wav'))
        label(img,x+15,y+30,f'{len(pcm)/SR:.3f}s -1dbfs')
        left,mid,width = x+15,y+85,cw-30
        img[mid,left:left+width] = (69,81,92)
        # Min/max envelope retains short transients even at contact-sheet scale.
        for col, block in enumerate(np.array_split(pcm,width)):
            lo = mid-round(float(np.max(block))/32767*30)
            hi = mid-round(float(np.min(block))/32767*30)
            img[lo:hi+1,left+col] = (88,211,184)
    write_png(ROOT/'waveforms_v01.png',img)


def validate():
    expected = [f'{name}_{i:02d}.wav' if count>1 else f'{name}.wav'
                for name,count in GROUPS for i in range(1,count+1)]
    assert sorted(p.name for p in OUT.glob('*.wav')) == sorted(expected)
    records, hashes = [], set()
    for name in expected:
        path = OUT/name
        with wave.open(str(path),'rb') as w:
            assert (w.getframerate(),w.getnchannels(),w.getsampwidth(),w.getcomptype()) == (SR,1,2,'NONE')
            raw = w.readframes(w.getnframes())
        pcm = np.frombuffer(raw,dtype='<i2')
        digest = hashlib.sha256(raw).hexdigest()
        assert digest not in hashes, name
        hashes.add(digest)
        peak_db = 20*np.log10(np.max(np.abs(pcm.astype(float)))/32767)
        assert abs(peak_db+1)<.001 and pcm[0]==pcm[-1]==0, name
        assert np.max(np.abs(pcm[:44].astype(float)))<32767*.15, name
        assert np.max(np.abs(pcm[-44:].astype(float)))<32767*.02, name
        records.append(dict(file=name,duration_s=round(len(pcm)/SR,6),frames=len(pcm),peak_dbfs=round(float(peak_db),6),sha256=digest))
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--validate-only',action='store_true')
    args = parser.parse_args()
    if not args.validate_only:
        OUT.mkdir(parents=True,exist_ok=True)
        clips = []
        for group_index,(name,count) in enumerate(GROUPS):
            for i in range(1,count+1):
                filename = f'{name}_{i:02d}.wav' if count>1 else f'{name}.wav'
                pcm = synth(name,i,np.random.default_rng(SEED+group_index*101+i))
                with wave.open(str(OUT/filename),'wb') as w:
                    w.setparams((1,2,SR,len(pcm),'NONE','not compressed'))
                    w.writeframes(pcm.tobytes())
                clips.append((filename,pcm))
        contact_sheet(clips)
    records = validate()
    if not args.validate_only:
        (ROOT/'validation_v01.json').write_text(json.dumps(dict(sample_rate=SR,channels=1,bits=16,seed=SEED,checks='51 unique PCM files; -1 dBFS; zero endpoints; faded first/last millisecond',files=records),indent=2)+'\n',encoding='utf-8')
        lines = ['# Мультяшные SFX v01', '', '51 процедурная заглушка; оригинальная синтезированная генерация, без чужих сэмплов и записи голосов.',
                 'WAV: 44 100 Гц, моно, PCM 16 бит; пик −1 dBFS; плавные края. Тембр: упругий, комичный, слегка преувеличенный.',
                 'Повтор: Python 3.13 + NumPy; `python -B gen_sfx.py`; проверка: `--validate-only`.',
                 'Файлы: `Out/v01/`; превью: `waveforms_v01.png`; длительности/хеши: `validation_v01.json`.',
                 'Варианты различаются зерном шума, высотой и/или длительностью. Голоса — бессмысленные синтетические вокализации; scream использует движущиеся форманты.',
                 'Технические проверки пройдены; художественная оценка и баланс громкости требуют прослушивания в игре.', '', '| Файл | Секунды |', '|---|---:|']
        lines += [f"| {r['file']} | {r['duration_s']:.3f} |" for r in records]
        (ROOT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(f'Validated {len(records)} unique 44.1 kHz mono PCM16 clips, all -1 dBFS and faded.')


if __name__ == '__main__':
    main()
