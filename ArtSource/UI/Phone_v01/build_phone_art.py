# Phone UI art v01: app icons, wallpaper, screen crack and PayMarket store app icons.
# Run: python build_phone_art.py  (Pillow). Writes PNG + Unity .meta into
# Assets/OnlyVolunteers/UI/Phone/Resources/Phone and a contact sheet into Previews.
import math
import os
import random
import uuid

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
OUT = os.path.join(ROOT, "Assets", "OnlyVolunteers", "UI", "Phone", "Resources", "Phone")
PREVIEW = os.path.join(HERE, "Previews")
FONT_BLACK = "C:/Windows/Fonts/seguibl.ttf"


def hexc(value, alpha=255):
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4)) + (alpha,)


def gradient(width, height, stops):
    """Vertical gradient; stops = [(t, '#rrggbb'), ...]."""
    img = Image.new("RGBA", (width, height))
    px = img.load()
    cols = [(t, hexc(c)) for t, c in stops]
    for y in range(height):
        t = y / max(1, height - 1)
        for i in range(len(cols) - 1):
            if cols[i][0] <= t <= cols[i + 1][0]:
                a, ca = cols[i]
                b, cb = cols[i + 1]
                k = (t - a) / max(1e-6, b - a)
                row = tuple(int(ca[j] + (cb[j] - ca[j]) * k) for j in range(4))
                break
        for x in range(width):
            px[x, y] = row
    return img


def shadowed(base, glyph, blur=22, offset=18, alpha=70):
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    mask = glyph.split()[3].point(lambda v: v * alpha // 255)
    shadow.putalpha(mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(blur))
    moved = Image.new("RGBA", base.size, (0, 0, 0, 0))
    moved.paste(shadow, (0, offset))
    base.alpha_composite(moved)
    base.alpha_composite(glyph)
    return base


def tile(top, bottom, size=1024):
    grad = gradient(size, size, [(0, top), (1, bottom)])
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size - 1, size - 1), radius=236, fill=255)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    img.paste(grad, (0, 0), mask)
    shine = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(shine).ellipse((-200, -620, size + 200, 330), fill=(255, 255, 255, 34))
    shine.putalpha(Image.composite(shine.split()[3], Image.new("L", (size, size), 0), mask))
    img.alpha_composite(shine)
    return img


def layer(size=1024):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def icon_messages():
    base = tile("#6EE07E", "#25A14A")
    g, d = layer()
    d.ellipse((170, 220, 854, 700), fill="white")
    d.polygon([(310, 610), (230, 820), (470, 680)], fill="white")
    for x in (362, 512, 662):
        d.ellipse((x - 50, 410, x + 50, 510), fill=hexc("#25A14A"))
    return shadowed(base, g)


def icon_camera():
    base = tile("#6A7079", "#2B2F35")
    g, d = layer()
    d.rounded_rectangle((380, 240, 644, 370), radius=48, fill="white")
    d.rounded_rectangle((160, 320, 864, 780), radius=120, fill="white")
    d.ellipse((512 - 185, 550 - 185, 512 + 185, 550 + 185), fill=hexc("#2B2F35"))
    d.ellipse((512 - 128, 550 - 128, 512 + 128, 550 + 128), fill=hexc("#3D74B5"))
    d.ellipse((512 - 70, 550 - 70, 512 + 70, 550 + 70), fill=hexc("#1C3F6E"))
    d.ellipse((440, 470, 500, 530), fill=(255, 255, 255, 220))
    d.ellipse((740, 380, 800, 440), fill=hexc("#FFB020"))
    return shadowed(base, g)


def icon_gallery():
    base = tile("#FFD45A", "#FF7F3A")
    g, d = layer()
    d.rounded_rectangle((210, 210, 814, 830), radius=60, fill="white")
    photo, pd = layer()
    pd.rectangle((0, 0, 1024, 1024), fill=hexc("#8ED3FF"))
    pd.ellipse((600, 300, 720, 420), fill=hexc("#FFE06A"))
    pd.polygon([(250, 680), (420, 430), (540, 580), (640, 470), (780, 680)], fill=hexc("#FF8A3D"))
    pd.polygon([(420, 430), (470, 505), (440, 520), (400, 470)], fill="white")
    mask = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(mask).rounded_rectangle((260, 260, 764, 680), radius=26, fill=255)
    g.paste(photo, (0, 0), mask)
    d.rounded_rectangle((330, 730, 690, 770), radius=20, fill=hexc("#E7E2D8"))
    g = g.rotate(-8, resample=Image.BICUBIC, center=(512, 512))
    return shadowed(base, g)


def icon_map():
    base = tile("#8BE3D2", "#2E9C8E")
    g, d = layer()
    d.polygon([(160, 300), (395, 250), (395, 760), (160, 800)], fill=hexc("#FFF4D6"))
    d.polygon([(395, 250), (630, 300), (630, 800), (395, 760)], fill=hexc("#E9D9B0"))
    d.polygon([(630, 300), (864, 250), (864, 760), (630, 800)], fill=hexc("#FFF4D6"))
    road = [(190, 690), (300, 610), (430, 640), (540, 540), (690, 560), (830, 430)]
    d.line(road, fill=hexc("#7AC7A0"), width=34, joint="curve")
    d.ellipse((200, 360, 330, 470), fill=hexc("#9ED8B0"))
    d.ellipse((690, 620, 820, 720), fill=hexc("#9ED8B0"))
    d.ellipse((580 - 110, 300, 580 + 110, 520), fill=hexc("#E5383B"))
    d.polygon([(482, 450), (678, 450), (580, 660)], fill=hexc("#E5383B"))
    d.ellipse((580 - 46, 364, 580 + 46, 456), fill="white")
    return shadowed(base, g)


def icon_bank():
    base = tile("#4E5FD0", "#22307F")
    g, d = layer()
    d.ellipse((190, 190, 834, 834), fill=hexc("#F59E0B"))
    d.ellipse((222, 222, 802, 802), fill=hexc("#FFD25E"))
    d.ellipse((262, 262, 762, 762), outline=hexc("#F2B33A"), width=14)
    # Sunglasses: a shady bank.
    d.rounded_rectangle((300, 400, 500, 520), radius=50, fill=hexc("#1B1B22"))
    d.rounded_rectangle((524, 400, 724, 520), radius=50, fill=hexc("#1B1B22"))
    d.rectangle((480, 420, 544, 446), fill=hexc("#1B1B22"))
    d.line([(300, 420), (255, 395)], fill=hexc("#1B1B22"), width=22)
    d.line([(724, 420), (769, 395)], fill=hexc("#1B1B22"), width=22)
    d.ellipse((330, 418, 380, 450), fill=(255, 255, 255, 120))
    d.ellipse((554, 418, 604, 450), fill=(255, 255, 255, 120))
    d.arc((420, 540, 640, 690), start=20, end=150, fill=hexc("#8A5300"), width=26)
    return shadowed(base, g)


def icon_market():
    base = tile("#323844", "#16191F")
    g, d = layer()
    mask = Image.new("L", (1024, 1024), 0)
    ImageDraw.Draw(mask).polygon([(330, 230), (330, 794), (830, 512)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(28)).point(lambda v: 255 if v > 150 else 0)
    g.paste(gradient(1024, 1024, [(0, "#FFC23D"), (0.5, "#FF7A45"), (1, "#FF3D7F")]), (0, 0), mask)
    font = ImageFont.truetype(FONT_BLACK, 210)
    tag, td = layer()
    td.rounded_rectangle((560, 640, 860, 860), radius=60, fill="white")
    td.text((710, 742), "$", font=font, fill=hexc("#16191F"), anchor="mm")
    g.alpha_composite(tag.rotate(12, resample=Image.BICUBIC, center=(710, 750)))
    return shadowed(base, g, alpha=110)


def wallpaper(width=1200, height=2460):
    img = gradient(width, height, [(0, "#1D1A4A"), (0.38, "#5C3A8C"), (0.62, "#E0697A"),
                                   (0.78, "#FBAE6E"), (1, "#FBAE6E")])
    rnd = random.Random(7)
    d = ImageDraw.Draw(img)
    for _ in range(140):
        x, y = rnd.randrange(width), rnd.randrange(int(height * 0.45))
        r = rnd.choice((2, 2, 3, 4))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randrange(90, 230)))
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(glow).ellipse((600 - 420, 1520 - 420, 600 + 420, 1520 + 420), fill=hexc("#FFD9A0", 120))
    img.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    d = ImageDraw.Draw(img)
    d.ellipse((600 - 240, 1520 - 240, 600 + 240, 1520 + 240), fill=hexc("#FFE2B0"))
    back = [(0, 1720), (140, 1600), (300, 1690), (470, 1560), (640, 1680), (820, 1580),
            (1000, 1700), (1200, 1610), (1200, height), (0, height)]
    d.polygon(back, fill=hexc("#7A3E7E"))
    front = [(0, 1900), (220, 1800), (430, 1880), (700, 1790), (930, 1870), (1200, 1800),
             (1200, height), (0, height)]
    d.polygon(front, fill=hexc("#43204F"))
    d.polygon([(0, 2140), (1200, 2010), (1200, 2120), (0, 2280)], fill=hexc("#2C1538"))
    # The van: rule zero of every wallpaper.
    van = hexc("#1A0D22")
    d.rounded_rectangle((420, 1890, 800, 2050), radius=36, fill=van)
    d.polygon([(800, 1930), (880, 1990), (880, 2050), (800, 2050)], fill=van)
    d.rounded_rectangle((470, 1915, 560, 1965), radius=10, fill=hexc("#FBAE6E", 200))
    d.rounded_rectangle((590, 1915, 680, 1965), radius=10, fill=hexc("#FBAE6E", 200))
    d.polygon([(810, 1945), (862, 1990), (810, 1990)], fill=hexc("#FBAE6E", 200))
    for cx in (500, 780):
        d.ellipse((cx - 50, 2010, cx + 50, 2110), fill=hexc("#0D0612"))
        d.ellipse((cx - 20, 2040, cx + 20, 2080), fill=hexc("#5C3A8C"))
    return img.resize((width // 2, height // 2), Image.LANCZOS)


def crack(width=1200, height=2460):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    rnd = random.Random(42)
    ox, oy = 150, 230
    rays = []
    for i in range(10):
        angle = math.radians(-35 + i * 17 + rnd.uniform(-6, 6))
        length = rnd.uniform(160, 760)
        pts = [(ox, oy)]
        x, y, a, travelled = ox, oy, angle, 0.0
        while travelled < length:
            step = rnd.uniform(30, 70)
            a += math.radians(rnd.uniform(-14, 14))
            x += math.cos(a) * step
            y += math.sin(a) * step
            travelled += step
            pts.append((x, y))
        rays.append(pts)
    for ring in (2, 4):
        for i in range(len(rays) - 1):
            if len(rays[i]) > ring and len(rays[i + 1]) > ring and rnd.random() < 0.75:
                d.line([rays[i][ring], rays[i + 1][ring]], fill=(255, 255, 255, 130), width=3)
    for pts in rays:
        d.line([(x + 2, y + 2) for x, y in pts], fill=(0, 0, 0, 70), width=5)
        d.line(pts, fill=(255, 255, 255, 190), width=4)
    d.ellipse((ox - 18, oy - 18, ox + 18, oy + 18), fill=(255, 255, 255, 120))
    return img.resize((width // 2, height // 2), Image.LANCZOS)


def icon_taxi():
    base = tile("#FFE15A", "#F5B400")
    g, d = layer()
    for i in range(8):
        col = hexc("#1B1B22") if i % 2 == 0 else hexc("#FFF6CC")
        d.rectangle((192 + i * 80, 170, 272 + i * 80, 230), fill=col)
    d.rounded_rectangle((170, 420, 854, 690), radius=90, fill=hexc("#1B1B22"))
    d.polygon([(300, 430), (380, 300), (644, 300), (724, 430)], fill=hexc("#1B1B22"))
    d.polygon([(330, 420), (395, 325), (500, 325), (500, 420)], fill=hexc("#9ED8FF"))
    d.polygon([(524, 420), (524, 325), (629, 325), (694, 420)], fill=hexc("#9ED8FF"))
    d.rounded_rectangle((400, 250, 624, 300), radius=16, fill="white")
    for cx in (330, 694):
        d.ellipse((cx - 90, 610, cx + 90, 790), fill=hexc("#2B2B30"))
        d.ellipse((cx - 40, 660, cx + 40, 740), fill=hexc("#C9CED3"))
    d.ellipse((200, 500, 270, 560), fill=hexc("#FFE15A"))
    d.ellipse((754, 500, 824, 560), fill=hexc("#FFE15A"))
    return shadowed(base, g)


def icon_shop():
    base = tile("#FF8FB1", "#E0457B")
    g, d = layer()
    d.arc((370, 170, 654, 470), start=180, end=360, fill="white", width=46)
    d.rounded_rectangle((210, 320, 814, 830), radius=80, fill="white")
    d.ellipse((350, 400, 400, 450), fill=hexc("#E0457B"))
    d.ellipse((624, 400, 674, 450), fill=hexc("#E0457B"))
    font = ImageFont.truetype(FONT_BLACK, 250)
    d.text((512, 640), "$", font=font, fill=hexc("#E0457B"), anchor="mm")
    return shadowed(base, g)


def icon_news():
    base = tile("#9AA3B5", "#4A5468")
    g, d = layer()
    d.rounded_rectangle((180, 200, 844, 830), radius=50, fill="white")
    font = ImageFont.truetype(FONT_BLACK, 120)
    d.text((512, 300), "NEWS", font=font, fill=hexc("#1B1B22"), anchor="mm")
    d.rectangle((230, 370, 794, 384), fill=hexc("#1B1B22"))
    # A tiny "missing" poster on the front page.
    d.rounded_rectangle((240, 420, 500, 760), radius=20, fill=hexc("#FFE9A8"))
    d.ellipse((310, 470, 430, 590), fill=hexc("#C68B6B"))
    d.rounded_rectangle((290, 600, 450, 700), radius=40, fill=hexc("#C68B6B"))
    for y in (440, 510, 580, 650, 720):
        d.rounded_rectangle((540, y, 794, y + 30), radius=15, fill=hexc("#C9CED3"))
    return shadowed(base, g)


TEXTURE_META = """fileFormatVersion: 2
guid: {guid}
TextureImporter:
  internalIDToNameTable: []
  externalObjects: {{}}
  serializedVersion: 13
  mipmaps:
    mipMapMode: 0
    enableMipMap: 0
    sRGBTexture: 1
    linearTexture: 0
    fadeOut: 0
    borderMipMap: 0
    mipMapsPreserveCoverage: 0
    alphaTestReferenceValue: 0.5
    mipMapFadeDistanceStart: 1
    mipMapFadeDistanceEnd: 3
  bumpmap:
    convertToNormalMap: 0
    externalNormalMap: 0
    heightScale: 0.25
    normalMapFilter: 0
    flipGreenChannel: 0
  isReadable: 0
  streamingMipmaps: 0
  streamingMipmapsPriority: 0
  vTOnly: 0
  ignoreMipmapLimit: 0
  grayScaleToAlpha: 0
  generateCubemap: 6
  cubemapConvolution: 0
  seamlessCubemap: 0
  textureFormat: 1
  maxTextureSize: 2048
  textureSettings:
    serializedVersion: 2
    filterMode: 1
    aniso: 1
    mipBias: 0
    wrapU: 1
    wrapV: 1
    wrapW: 1
  nPOTScale: 0
  lightmap: 0
  compressionQuality: 50
  spriteMode: 1
  spriteExtrude: 1
  spriteMeshType: 0
  alignment: 0
  spritePivot: {{x: 0.5, y: 0.5}}
  spritePixelsToUnits: 100
  spriteBorder: {{x: 0, y: 0, z: 0, w: 0}}
  spriteGenerateFallbackPhysicsShape: 0
  alphaUsage: 1
  alphaIsTransparency: 1
  spriteTessellationDetail: -1
  textureType: 8
  textureShape: 1
  singleChannelComponent: 0
  flipbookRows: 1
  flipbookColumns: 1
  maxTextureSizeSet: 0
  compressionQualitySet: 0
  textureFormatSet: 0
  ignorePngGamma: 0
  applyGammaDecoding: 0
  swizzle: 50462976
  cookieLightType: 0
  platformSettings:
  - serializedVersion: 4
    buildTarget: DefaultTexturePlatform
    maxTextureSize: 2048
    resizeAlgorithm: 0
    textureFormat: -1
    textureCompression: 0
    compressionQuality: 50
    crunchedCompression: 0
    allowsAlphaSplitting: 0
    overridden: 0
    ignorePlatformSupport: 0
    androidETC2FallbackOverride: 0
    forceMaximumCompressionQuality_BC6H_BC7: 0
  spriteSheet:
    serializedVersion: 2
    sprites: []
    outline: []
    customData:
    physicsShape: []
    bones: []
    spriteID: {sprite_id}
    internalID: 0
    vertices: []
    indices:
    edges: []
    weights: []
    secondaryTextures: []
    spriteCustomMetadata:
      entries: []
    nameFileIdTable: {{}}
  mipmapLimitGroupName:
  pSDRemoveMatte: 0
  userData:
  assetBundleName:
  assetBundleVariant:
"""


def save(img, name, results):
    path = os.path.join(OUT, name + ".png")
    meta = path + ".meta"
    if not os.path.exists(meta):  # keep the GUID stable on reruns
        with open(meta, "w", newline="\n") as f:
            f.write(TEXTURE_META.format(guid=uuid.uuid4().hex, sprite_id=uuid.uuid4().hex))
    img.save(path, optimize=True)
    results.append((name, img))


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(PREVIEW, exist_ok=True)
    results = []
    icons = {"app_messages": icon_messages, "app_camera": icon_camera, "app_gallery": icon_gallery,
             "app_map": icon_map, "app_bank": icon_bank, "app_market": icon_market}
    for name, fn in icons.items():
        save(fn().resize((256, 256), Image.LANCZOS), name, results)
    save(wallpaper(), "wallpaper", results)
    save(crack(), "screen_crack", results)
    store = {"app_taxi": icon_taxi, "app_shop": icon_shop, "app_news": icon_news}
    for name, fn in store.items():
        save(fn().resize((256, 256), Image.LANCZOS), name, results)

    sheet = Image.new("RGBA", (1400, 760), hexc("#2A2D33"))
    x = 20
    for name, img in results[:6]:
        sheet.alpha_composite(img.resize((180, 180), Image.LANCZOS), (x, 20))
        x += 200
    wp = results[6][1].resize((300, 615), Image.LANCZOS)
    cr = results[7][1].resize((300, 615), Image.LANCZOS)
    sheet.alpha_composite(wp, (20, 225))
    sheet.alpha_composite(wp, (340, 225))
    sheet.alpha_composite(cr, (340, 225))
    x = 680
    for name, img in results[8:]:
        sheet.alpha_composite(img.resize((180, 180), Image.LANCZOS), (x, 240))
        x += 200
    sheet.convert("RGB").save(os.path.join(PREVIEW, "phone_art_v01.png"))
    print("wrote", len(results), "textures to", OUT)


if __name__ == "__main__":
    main()
