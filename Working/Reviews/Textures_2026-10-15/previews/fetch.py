import re, urllib.request, ssl, os
ctx=ssl.create_default_context()
items=[
("B09 Асфальт тёмный Asphalt014","https://ambientcg.com/view?id=Asphalt014"),
("B09 Асфальт старый Asphalt006","https://ambientcg.com/view?id=Asphalt006"),
("A09 Кирпич Bricks051","https://ambientcg.com/view?id=Bricks051"),
("A13 Черепица RoofingTiles014A","https://ambientcg.com/view?id=RoofingTiles014A"),
("A14 Сланец RoofingTiles004","https://ambientcg.com/view?id=RoofingTiles004"),
("B19 Резина Rubber004","https://ambientcg.com/view?id=Rubber004"),
("B20 Плитка бассейна Tiles020","https://ambientcg.com/view?id=Tiles020"),
("A11 Бетон Concrete034","https://ambientcg.com/view?id=Concrete034"),
("B13 Штукатурка Smooth Stucco","https://proctexture.com/textures/plaster/troweled/smooth-stucco"),
("B11 Плитка площади Square Tile","https://proctexture.com/textures/tile/ceramic/square-tile"),
("B18 Ткань Cotton Duck","https://proctexture.com/textures/fabric/woven/cotton-duck"),
("B21 Доски Whitewashed Oak","https://proctexture.com/textures/wood/boards/whitewashed-oak"),
("A16 Доски Maple Plank","https://proctexture.com/textures/wood/boards/maple-plank"),
("A12 Блок Painted Block","https://proctexture.com/textures/brick/concrete-block/painted-block"),
("B05 Песок Desert Sand","https://proctexture.com/textures/ground/granular/desert-sand"),
("B06 Скала Slate Slab","https://proctexture.com/textures/stone/block/slate-slab"),
("A20 Кора Pine Bark","https://proctexture.com/textures/nature/bark/pine-bark"),
("B01 ориентир Dry Grass","https://proctexture.com/textures/nature/grass/dry-grass"),
("B02 ориентир Grass Turf","https://proctexture.com/textures/nature/grass/grass-turf"),
("B10 Бетон Smooth Concrete","https://proctexture.com/textures/stone/concrete/smooth-concrete"),
("B16 Профлист Corrugated Metal Panel 01","https://www.cgbookcase.com/textures/corrugated-metal-panel-01"),
("A07 Плитка Grey Matte Tiles 01","https://www.cgbookcase.com/textures/grey-matte-tiles-01"),
("B15 Штукатурка White Stucco Wall 02","https://www.cgbookcase.com/textures/white-stucco-wall-02"),
("B05 Мокрый песок Damp Beach Sand","https://polyhaven.com/a/damp_beach_sand"),
("A04 Гравий Gravel Floor 02","https://polyhaven.com/a/gravel_floor_02"),
("B04 ориентир Farm Furrows","https://polyhaven.com/a/farm_furrows"),
("A08 Брусчатка Cobblestone 001","https://3dtextures.me/2018/04/13/cobblestone-001/"),
]
for i,(name,url) in enumerate(items):
    out="%02d.jpg"%i
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
        html=urllib.request.urlopen(req,context=ctx,timeout=30).read().decode('utf-8','ignore')
        m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',html) or re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',html)
        img=m.group(1) if m else None
        if img and img.startswith('/'): img=re.match(r'https?://[^/]+',url).group(0)+img
        data=urllib.request.urlopen(urllib.request.Request(img,headers={'User-Agent':'Mozilla/5.0'}),context=ctx,timeout=30).read()
        open(out,'wb').write(data); print(i,'ok',len(data),img[:90])
    except Exception as e:
        print(i,'FAIL',name,e)
open('names.txt','w',encoding='utf-8').write('\n'.join(n for n,_ in items))
