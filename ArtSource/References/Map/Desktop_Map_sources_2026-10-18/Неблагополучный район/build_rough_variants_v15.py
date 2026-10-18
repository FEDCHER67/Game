"""Неблагополучный район — 3 схемы перепланировки v15 A/B/C (TASK-000578).
Район чуть больше и плотнее нынешнего (~340×210 м против ~255×150 м в v11, ~22 дома), собран из «жилых групп» как в советских микрорайонах: длинные дома вдоль проездов,
короткие поперёк торцами, дворы внутри, проходы в углах; общее ядро (клуб, коробка, кооператив, сквер).
Только планировка, блоками, без деталей. Единицы — метры, y вниз (север сверху). Не перезаписывает.
Запуск: python build_rough_variants_v15.py -> Неблагополучный_район_v15A/B/C.png
"""
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
S = 4.6                      # px на метр
OX, OY = 40, 42              # отступ района на холсте, м
F = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 15)
FS = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf', 14)
FT = ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf', 22)
GREY, GREY_OUT = (150, 152, 152), (70, 72, 74)
GCOLS = ((122, 98, 82), (96, 112, 124), (112, 120, 100), (130, 110, 92), (104, 104, 108), (140, 90, 70))


class Plan:
    def __init__(self, name, title, sub, exits):
        self.name, self.title, self.sub, self.exits = name, title, sub, exits
        self.img = Image.new('RGB', (int((340 + 2 * OX) * S), int((210 + OY + 45) * S)), (206, 210, 198))
        self.dr = ImageDraw.Draw(self.img, 'RGBA')
        self.nums = []
        self.gi = 0
        self.road()

    def P(self, x, y):
        return ((x + OX) * S, (y + OY) * S)

    def rect(self, x, y, w, h, fill, out=None, wd=1):
        self.dr.rectangle([self.P(x, y), self.P(x + w, y + h)], fill=fill, outline=out, width=wd)

    def line(self, pts, col, wm):
        self.dr.line([self.P(*p) for p in pts], fill=col, width=max(1, int(wm * S)), joint='curve')

    def road(self):
        u = [(-12, -30), (-12, 222), (352, 222), (352, -30)]
        legs = [u]
        for side, v in self.exits:
            if side == 'W':
                legs.append([(-12, v), (-38, v)])
            elif side == 'S':
                legs.append([(v, 222), (v, 240)])
            elif side == 'E':
                legs.append([(352, v), (375, v)])
        for pts in legs:
            self.line(pts, (176, 176, 170), 12)
        for pts in legs:
            self.line(pts, (92, 96, 100), 8)

    def house(self, x, y, w, h):
        self.rect(x + 1.2, y + 1.6, w, h, (60, 64, 66, 70))
        self.rect(x, y, w, h, GREY, GREY_OUT, 2)

    def H(self, x, y, L=90):
        self.house(x, y, L, 12)

    def V(self, x, y, L=60):
        self.house(x, y, 12, L)

    def arch(self, x, y, w, h, lab=None):
        self.rect(x, y, w, h, (190, 188, 180))
        if lab:
            self.num(lab, x + w / 2, y + h + 7)

    def garages(self, x, y, n, face, vertical=False):
        for k in range(n):
            col = GCOLS[(self.gi + k * 5) % len(GCOLS)]
            if not vertical:
                gx = x + k * 3.3
                self.rect(gx, y, 3.3, 6, col, (60, 60, 60))
                dy = y + 5.4 if face == 'S' else y
                self.rect(gx + 0.4, dy, 2.5, 0.6, (50, 52, 54))
            else:
                gy = y + k * 3.3
                self.rect(x, gy, 6, 3.3, col, (60, 60, 60))
                dx = x + 5.4 if face == 'E' else x
                self.rect(dx, gy + 0.4, 0.6, 2.5, (50, 52, 54))
        self.gi += 1

    def coop(self, x, y, n, lab='07', vertical=False):
        """07 кооператив: 2 ряда лицом друг к другу, проезд 7 м, глухой конец."""
        L = n * 3.3
        if not vertical:
            self.garages(x, y, n, 'S'); self.garages(x, y + 13, n, 'N')
            self.rect(x, y + 6, L, 7, (150, 146, 136)); self.rect(x + L - 1, y + 6, 1.5, 7, (60, 60, 60))
            self.num(lab, x + L / 2, y + 9.5)
        else:
            self.garages(x, y, n, 'E', True); self.garages(x + 13, y, n, 'W', True)
            self.rect(x + 6, y, 7, L, (150, 146, 136)); self.rect(x + 6, y + L - 1, 7, 1.5, (60, 60, 60))
            self.num(lab, x + 9.5, y + L / 2)

    def place(self, x, y, w, h, fill, out, lab):
        self.rect(x, y, w, h, fill, out, 2)
        self.num(lab, x + w / 2, y + h / 2)

    def club(self, x, y, w=26, h=15):
        self.place(x, y, w, h, (146, 126, 118), (70, 56, 50), '05')

    def box(self, x, y, w=40, h=20):
        self.rect(x - 1.5, y - 1.5, w + 3, h + 3, (120, 96, 70))
        self.rect(x, y, w, h, (108, 140, 96), (230, 232, 226), 2)
        if w > h:
            self.line([(x + w / 2, y), (x + w / 2, y + h)], (230, 232, 226), 0.5)
        else:
            self.line([(x, y + h / 2), (x + w, y + h / 2)], (230, 232, 226), 0.5)
        self.num('04', x + w / 2, y + h / 2)

    def shop(self, x, y, w=20, h=10):
        self.place(x, y, w, h, (186, 120, 96), (90, 50, 40), '03')

    def shawarma(self, x, y):
        self.place(x, y, 6, 6, (190, 110, 80), (90, 50, 30), '06')

    def square(self, x, y, w=28, h=24):
        self.place(x, y, w, h, (176, 186, 160), (120, 130, 110), '17')

    def playground(self, x, y, w=24, h=18):
        self.place(x, y, w, h, (196, 186, 150), (140, 130, 100), '19')

    def nook(self, x, y, w, h, lab):
        self.place(x, y, w, h, (84, 86, 90, 230), (40, 42, 46), lab)

    def base(self, yard, gate, row18):
        """01 база в Г-доме: ворота в фасаде, 02 дворик, 18 ряд гаражей прикрывает."""
        x, y, w, h = yard
        self.rect(x, y, w, h, (166, 164, 156), (130, 128, 120))
        self.rect(x + w / 2 - 6, y + h / 2 - 3, 12, 6, None, (40, 60, 90), 2)
        self.num('02', x + w / 2, y + h / 2)
        self.rect(*gate, (60, 64, 68))
        self.num('01', gate[0] + gate[2] / 2, gate[1] + 8)
        gx, gy, n = row18
        self.garages(gx, gy, n, 'N')
        self.num('18', gx + n * 3.3 / 2, gy - 6)

    def num(self, lab, x, y):
        self.nums.append((lab, x, y))

    def save(self):
        dr = self.dr
        for lab, x, y in self.nums:
            px, py = self.P(x, y)
            dr.ellipse([px - 13, py - 13, px + 13, py + 13], fill=(255, 255, 255), outline=(40, 52, 70), width=2)
            dr.text((px, py), lab, font=F, fill=(40, 52, 70), anchor='mm')
        W = self.img.size[0]
        dr.rectangle([12, 10, W - 12, 92], fill=(255, 255, 255), outline=(140, 160, 170))
        dr.text((24, 16), self.title, font=FT, fill=(40, 52, 70))
        dr.text((24, 46), self.sub, font=FS, fill=(90, 100, 106))
        dr.text((24, 68), '01 база (гараж в Г-доме) · 02 дворик бусика · 18 гаражи у базы · 03 магазин · 04 коробка · 05 клуб · '
                '06 шаурма · 07 кооператив · 09 колодец · 10 арка · 15 закуток · 17 мини-сквер · 19 детская площадка',
                font=FS, fill=(90, 100, 106))
        x0, y0 = self.P(0, 238)
        dr.rectangle([x0, y0, x0 + 50 * S, y0 + 6], fill=(40, 52, 70))
        dr.text((x0 + 50 * S + 10, y0 + 3), '50 м · район ~340×210 м (v11 ~255×150 м)', font=FS, fill=(40, 52, 70), anchor='lm')
        out = os.path.join(HERE, 'Неблагополучный_район_v15%s.png' % self.name)
        if os.path.exists(out):
            raise SystemExit(os.path.basename(out) + ' exists')
        self.img.save(out)
        print('ok', out)


# ======================================================================= A — сетка групп + центральная полоса
a = Plan('A', 'Вариант A — «сетка групп»: одинаковые жилые группы рядами, между рядами — полоса общего ядра',
         'Группа ~92×52 м: 2 длинных горизонтальных дома + 1 поперечный, двор ~28 м, проходы в углах. Северный ряд из 3 групп, ядро по центру, южный ряд зеркально.',
         [('W', 60), ('S', 105), ('S', 225), ('E', 58)])
for x0 in (0, 120, 240):                                        # северный ряд групп
    a.H(x0, 0, 70); a.H(x0, 40, 70); a.V(x0 + 80, 6, 40)
a.playground(145, 18, 20, 12)
a.coop(8, 70, 12); a.shawarma(50, 74)                          # ядро
a.club(66, 84); a.nook(92, 88, 6, 8, '15')
a.box(116, 80); a.square(170, 82, 24, 18)
a.garages(206, 112, 3, 'S')
a.H(240, 64, 92); a.H(240, 122, 40); a.H(292, 122, 40)          # 09 колодец с аркой
a.V(240, 76, 46); a.V(320, 76, 46); a.arch(280, 122, 12, 12, '10'); a.num('09', 286, 98)
a.V(0, 146, 52); a.H(0, 198, 70)                                # база в Г-доме
a.base((14, 166, 34, 30), (26, 196, 8, 2), (14, 158, 10))
a.shop(80, 198)
a.V(110, 150, 48); a.H(130, 150, 70); a.H(130, 198, 70)          # южный ряд зеркально
a.garages(208, 200, 3, 'S')
a.H(240, 150, 70); a.H(240, 198, 70); a.V(320, 156, 40)
a.save()

# ======================================================================= B — ядро в центре, дома по периметру
b = Plan('B', 'Вариант B — «ядро в центре»: длинные дома стеной вдоль внешней дороги, внутри поперечные, в середине клуб и коробка',
         'По периметру дома вдоль дороги (на юге горизонтальные, на западе и востоке вертикальные), внутри дома поперёк гребёнкой, колодец с аркой у центра.',
         [('W', 92), ('S', 80), ('S', 333), ('E', 87)])
b.garages(20, 2, 14, 'S'); b.garages(230, 2, 14, 'S')           # гаражи по северному краю
b.V(0, 14, 60); b.V(0, 110, 88); b.H(0, 198, 70)                # запад + база в Г
b.base((14, 160, 34, 36), (26, 196, 8, 2), (14, 152, 10))
b.H(22, 22, 50); b.H(22, 58, 50); b.playground(30, 37, 20, 14)  # внутренний запад — поперёк
b.H(92, 198, 60); b.shop(156, 198); b.H(180, 198, 60); b.H(250, 198, 70)   # юг — стена вдоль дороги
b.V(328, 14, 60); b.V(328, 100, 70)                              # восток
b.H(268, 22, 50); b.H(268, 58, 50)                               # внутренний восток
b.V(100, 140, 46); b.V(220, 140, 46); b.V(300, 135, 50)          # внутренний юг — гребёнка
b.H(125, 118, 80); b.V(125, 130, 32); b.V(193, 130, 32)          # 09 колодец с аркой
b.H(125, 162, 35); b.H(172, 162, 33); b.arch(160, 162, 12, 12, '10'); b.num('09', 165, 146)
b.coop(90, 20, 14); b.shawarma(140, 24)                          # ядро
b.club(150, 62); b.nook(176, 66, 6, 8, '15')
b.box(200, 60); b.square(215, 90, 24, 20)
b.playground(200, 22, 20, 14)
b.save()

# ======================================================================= C — каре на западе, ядро-полоса, гребёнка на востоке
c = Plan('C', 'Вариант C — «каре + гребёнка»: запад — замкнутые кварталы, центр — полоса ядра с севера на юг, восток — ряды со сдвигом',
         'Запад: каре с колодцем и аркой + квартал базы. Центр: кооператив, клуб, коробка, сквер одной полосой. Восток: горизонтальные ряды со сдвигом, торцевые дома закрывают дворы.',
         [('W', 90), ('S', 135), ('S', 202), ('E', 75)])
c.H(0, 0, 60); c.H(70, 0, 60); c.V(0, 12, 56); c.V(118, 12, 56)  # каре-колодец
c.H(0, 68, 60); c.H(70, 68, 60); c.rect(60, 68, 10, 12, GREY, GREY_OUT, 2)
c.arch(60, 68, 10, 12, '10'); c.num('09', 65, 30); c.playground(40, 42, 20, 14)
c.V(0, 104, 94); c.H(0, 198, 70); c.H(24, 100, 60); c.V(100, 116, 50)   # квартал базы
c.base((14, 160, 34, 36), (26, 196, 8, 2), (14, 152, 10))
c.shop(80, 198)
c.coop(146, 4, 12, vertical=True); c.shawarma(170, 6)           # ядро-полоса
c.club(146, 56, 15, 26); c.nook(146, 82, 15, 6, '15')
c.box(170, 54, 20, 40); c.square(148, 104, 24, 20); c.garages(150, 140, 3, 'S')
c.H(210, 0, 60); c.H(280, 0, 60)                                 # восток: ряды со сдвигом
c.H(225, 40, 70); c.V(328, 30, 40)
c.H(210, 80, 60); c.H(280, 80, 48)
c.H(230, 120, 70); c.V(210, 112, 48)
c.H(210, 198, 60); c.H(280, 198, 60)
c.playground(290, 150, 20, 14)
c.save()
