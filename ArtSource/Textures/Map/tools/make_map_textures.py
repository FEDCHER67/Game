#!/usr/bin/env python3
"""Generate the VOLUNTEERS ONLY map texture set (numpy + Pillow only).

    python ArtSource/Textures/Map/tools/make_map_textures.py            # everything
    python ArtSource/Textures/Map/tools/make_map_textures.py --only facade_panel_slab
    python ArtSource/Textures/Map/tools/make_map_textures.py --category roofs
    python ArtSource/Textures/Map/tools/make_map_textures.py --manifest-only

Output: <out>/<category>/<name>_{albedo,normal,roughness,mask[,emission]}.png,
<out>/previews/preview_<category>.png, <out>/previews/preview_all.png and
<out>/map_textures_manifest.json. Output is deterministic for a given font set.
"""
import argparse
import json
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from registry import TEXTURES, map_files, unity_settings  # noqa: E402
import texlib  # noqa: E402
import gen_facades  # noqa: E402,F401
import gen_windows  # noqa: E402,F401
import gen_roofs  # noqa: E402,F401
import gen_ground  # noqa: E402,F401
import gen_signage  # noqa: E402,F401

DEFAULT_OUT = os.path.normpath(os.path.join(HERE, ".."))
CATEGORY_ORDER = ["facades", "windows", "roofs", "ground", "signage"]


def manifest(entries):
    items = []
    for t in entries:
        files = {k: f"{t['category']}/{v}" for k, v in map_files(t).items()}
        item = {
            "name": t["name"], "category": t["category"], "kind": t["kind"],
            "size": t["size"], "tiling": t["tiling"], "world_size_m": t["world_m"],
            "maps": files, "unity": unity_settings(t, files), "notes": t["notes"],
        }
        if t["atlas"]:
            item["atlas"] = t["atlas"]
        items.append(item)
    return {
        "generator": "ArtSource/Textures/Map/tools/make_map_textures.py",
        "conventions": {
            "albedo": "sRGB; RGBA for decals (alpha = coverage)",
            "normal": "tangent space, OpenGL (+Y up) as Unity expects",
            "roughness": "linear grey, 1 = rough",
            "mask": "URP Metallic map: R metallic, G painted AO, B unused, A smoothness (1 - roughness)",
            "emission": "sRGB, only lit windows / signs",
        },
        "fonts": "Rubik ExtraBold/Medium + PT Sans Narrow Bold (OFL, Google Fonts); DejaVu fallback",
        "textures": items,
    }


def thumb(path, size, tiles):
    img = Image.open(path).convert("RGBA")
    if tiles > 1:
        big = Image.new("RGBA", (img.width * tiles, img.height * tiles))
        for i in range(tiles):
            for j in range(tiles):
                big.paste(img, (i * img.width, j * img.height))
        img = big
    img.thumbnail((size, size), Image.LANCZOS)
    bg = Image.new("RGBA", img.size, (120, 120, 120, 255))
    checker = Image.new("RGBA", img.size, (150, 150, 150, 255))
    m = Image.new("L", img.size, 0)
    d = ImageDraw.Draw(m)
    for y in range(0, img.height, 16):
        for x in range((y // 16) % 2 * 16, img.width, 32):
            d.rectangle([x, y, x + 15, y + 15], fill=255)
    bg.paste(checker, (0, 0), m)
    bg.alpha_composite(img)
    return bg.convert("RGB")


def preview_sheet(out_dir, entries, path, fonts, cell=256):
    cols = min(6, len(entries))
    rows = (len(entries) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * (cell + 22)), (34, 34, 38))
    d = ImageDraw.Draw(sheet)
    font = texlib.load_font(fonts["label"], 14)
    for i, t in enumerate(entries):
        x, y = (i % cols) * cell, (i // cols) * (cell + 22)
        p = os.path.join(out_dir, t["category"], map_files(t)["albedo"])
        if not os.path.exists(p):
            continue
        tiles = 2 if t["tiling"] == "both" else 1
        im = thumb(p, cell - 6, tiles)
        sheet.paste(im, (x + 3 + (cell - 6 - im.width) // 2, y + 3 + (cell - 6 - im.height) // 2))
        d.text((x + 4, y + cell + 2), t["name"], fill=(230, 230, 230), font=font)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sheet.save(path, optimize=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=DEFAULT_OUT, help="output folder (default: ArtSource/Textures/Map)")
    ap.add_argument("--only", default="", help="comma-separated texture names")
    ap.add_argument("--category", default="", help="comma-separated categories")
    ap.add_argument("--offline", action="store_true", help="do not download fonts, use DejaVu")
    ap.add_argument("--manifest-only", action="store_true", help="only write the JSON manifest")
    ap.add_argument("--list", action="store_true", help="list texture names and exit")
    a = ap.parse_args()

    entries = sorted(TEXTURES, key=lambda t: CATEGORY_ORDER.index(t["category"]))
    if a.list:
        for t in entries:
            print(f"{t['category']:8s} {t['name']:34s} {t['size'][0]}x{t['size'][1]}")
        return
    sel = [t for t in entries
           if (not a.only or t["name"] in a.only.split(","))
           and (not a.category or t["category"] in a.category.split(","))]
    os.makedirs(a.out, exist_ok=True)
    man_path = os.path.join(a.out, "map_textures_manifest.json")
    if a.manifest_only:
        with open(man_path, "w", encoding="utf-8") as f:
            json.dump(manifest(entries), f, ensure_ascii=False, indent=2)
        print(f"manifest: {man_path} ({len(entries)} textures)")
        return

    fonts = texlib.ensure_fonts(os.path.join(a.out, "_fonts"), offline=a.offline)
    print(f"fonts: {fonts['source']}")
    ctx = {"fonts": fonts}
    for t in sel:
        t0 = time.time()
        w, h = t["size"]
        s = t["fn"](t["name"], (h, w), texlib.rng_for(t["name"]), ctx)
        if t["emission"] and s.emission is None:
            s.emission = np.zeros((h, w, 3), np.float32)
        files = texlib.write_surface(os.path.join(a.out, t["category"]), t["name"], s,
                                     t["normal_strength"], *t["ao"])
        print(f"  {t['category']:8s} {t['name']:34s} {w}x{h}  {time.time() - t0:5.1f}s  -> {', '.join(files)}")

    prev = os.path.join(a.out, "previews")
    for cat in CATEGORY_ORDER:
        group = [t for t in entries if t["category"] == cat]
        if any(t in sel for t in group):
            preview_sheet(a.out, group, os.path.join(prev, f"preview_{cat}.png"), fonts)
    preview_sheet(a.out, entries, os.path.join(prev, "preview_all.png"), fonts, cell=192)
    with open(man_path, "w", encoding="utf-8") as f:
        json.dump(manifest(entries), f, ensure_ascii=False, indent=2)
    print(f"done. previews in {prev}, manifest {man_path}")


if __name__ == "__main__":
    main()
