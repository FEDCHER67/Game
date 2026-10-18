"""Общая карта v58 (TASK-000782, Вадим): больше деревьев в середине луга и на въезде в Неблагополучный; Даунтаун и Неблагополучный ещё дальше от холма B — Даунтаун (с пляжем и Элитом)
+20 м правее и −28 м ниже, Неблагополучный (с северным берегом и погранпостом) +22 м выше; холст вырос на 25 м вверх
(море), мир y -> пиксель py = 3500 − 5y + 1250, высота 950 м (post_shift_v58). Координаты в скрипте — до сдвига.
Ранее v57 (TASK-000781, Вадим): луг между Стройкой и Неблагополучным снова открытый — редкие рощи, бугры,
у забора Неблагополучного полоса деревьев (граница света); дороги Стройка -> Неблагополучный нет; Горный хребет продлён
вдоль северного берега до северо-западного угла Неблагополучного; там бухточка, каменный пирс с забором и погранпост
(военное положение — выезд запрещён); Даунтаун (с пляжем и Элитом) ниже на 15 м, Неблагополучный выше на 10 м —
дальше от холма B и выездов тоннеля (post_shift_v58). Элит меньше/круглее и дома вразнобой — на этапе детализации.
Ранее v56 (TASK-000775, Вадим): между Стройкой, холмом B и Неблагополучным — относительно густой лес
(проехать можно, но тяжело), дороги Стройка -> Неблагополучный больше нет; в Неблагополучный — дорога вдоль реки от Хутора
(перемычка y 572 и дуга, как v54), тоннель и Порт; Даунтаун, пляж и Элит — на 20 м правее (растровый сдвиг post_shift_v58,
все координаты в скрипте — ДО сдвига); у тоннеля длиннее подъезды, выезд не упирается в дом.
Ранее v55 (TASK-000767, Вадим; канон §72 — Heat по секторам, отрыв от погони): луг между Стройкой и
Неблагополучным стал «рощей отрыва» — светлый проезжаемый лес с грунтовками и полянами, гуще и темнее к северу (от
солнечной Стройки к пасмурному Неблагополучному), место скинуть полицию; серпантин VIEW B остаётся, холм B выше (38 -> 50 м); холм +12 м у Неблагополучного
и дорога вдоль реки на север (с перемычкой и дугой к району) убраны; объездная Хутора — только до его грунтовки; тоннель
остаётся.
Ранее v54 (TASK-000754, Вадим): переезд через реку (природная перемычка) опущен ниже — с y 663 на y 572;
от него к юго-западному перекрёстку Неблагополучного идёт дорога как прежняя дуга: прямо на восток, плавный
подъём на северо-восток и снова на восток в перекрёсток; старая линия объездной из мастера (hamlet_bypass_*) убрана, объездная Хутора
вдоль реки стала короче.
Ранее v53 (TASK-000752, Вадим): дорога Хутор -> Неблагополучный больше не идёт дугой параллельно западной
стороне района к верхнему углу — она прямо входит в нижний (юго-западный) перекрёсток района, где сходятся дорога от
Стройки и кольцо; западная сторона кольца остаётся одной дорогой — получается прямоугольник.
Ранее v52 (TASK-000749, Вадим): луг у Стройки — только трава и рощи (пруд, грунтовки, валуны, цветы убраны);
мост из растра Хутора через реку убран; объездная Хутора одной плавной линией; рощи между Неблагополучным и Портом;
плавный переход пляжа к берегу Элитного холма (пальмы и зелень дюн продолжаются по дуге).
Ранее v51 (TASK-000748, Вадим): луг между рекой, дорогой Хутор -> Неблагополучный и дорогой Стройка ->
Неблагополучный заполнен проезжаемой природой: рощи-островки, пруд с камышом, валуны, поваленное дерево, цветущий луг,
полевая грунтовка от дороги к пруду и к реке.
Ранее v50 (TASK-000746, Вадим): восточный край городского пляжа одной дугой переходит в песчаный берег у
Элитного холма; остаток устья старого канала закрыт песком.
Ранее v49 (TASK-000745, Вадим): Даунтаун — план v27 (прямая набережная вдоль пляжа, полные нижние кварталы,
перекрёстки на всех улицах); заплатки v48 и отдельная прямая дорога больше не нужны.
Ранее v48 (TASK-000744, Вадим): неровный пляж (широкий у пирса, уже к краям); нижний ряд кварталов слит с
соседними: обрывки старой нижней улицы (y 270) убраны, улицы x 954 и x 1238 продлены до прямой набережной.
Ранее v47 (TASK-000742, Вадим): Даунтаун v26 как утверждён, рамки по краям нет — прямая только нижняя улица
вдоль пляжа; пляж Майами с парковками.
Ранее v46 (TASK-000741, Вадим): Даунтаун снова план v26 (площадь с золотой статуей) — без замены на v16; по
краям прямые дороги-рамка; парковки у въездов бусика на пляж.
Ранее v45 (TASK-000740, Вадим, референсы Майами-Бич): пляж полосами от города к морю — южная улица Даунтауна,
пальмовый парк с извилистой дорожкой (закрывает море от города), полоса дюн с кустами и деревянными проходами, широкий
белый песок со спасательными вышками, зонтиками рядами, волейболом и двумя барами, пирс по оси площади; въезды для бусика
на песок по двум улицам города.
Ранее v44 (TASK-000738, Вадим): Даунтаун по плану v16 (прямоугольник, прямые дороги со всех четырёх сторон);
тоннель ещё на 40 м левее, серпантин VIEW B на 50 м левее (дальше от карниза VIEW C).
Ранее v43 (TASK-000736, Вадим): тоннель из центра — от северной улицы Даунтауна у площади к середине южной
стороны Неблагополучного; серпантин VIEW B на восточной части холма (вид на бухту и Порт); холм B чуть шире влево, западный
холм у реки убран; ровная дорога от главной у Стройки на север прямо в Неблагополучный (как у Феди).
Ранее v42 (TASK-000731, Вадим): река прямее — вдоль восточного края Тихой долины прямо вниз в море (водопад у
воды); скальный массив меньше, только у долины, до Даунтауна не доходит.
Ранее v41 (TASK-000730, Вадим): сам пляж западной частью загибается дугой в море и вниз (по рисунку Вадима);
между пляжем и Тихой долиной — высокие серые скалы, через них ущельем течёт река (между Хутором и Стройкой) и водопадом
выходит на пляж и в море. Бухты у Тихой долины и косы больше нет.
Ранее v40 (TASK-000728, Вадим): запад ровный как у Феди — от объездной Хутора (где дорога в Тихую долину) прямая
дорога на восток в Даунтаун, Стройка сразу слева (севернее), гора H и перевал убраны; Даунтаун, пляж, Элитный холм, Порт и Трамдуро на 60 м правее;
Неблагополучный на 40 м левее и на 30 м выше; между Даунтауном и Неблагополучным один высокий широкий холм B: тоннель под
ним и живописный серпантин через него (VIEW B); пляж — дуга-бухта только влево к Тихой долине.
Ранее v39 (TASK-000727, Вадим): водопад с прудом внутри Тихой долины убран; река у Тихой долины в конце падает
водопадом со скалы прямо в море (вместо лагуны).
Ранее v38 (TASK-000726, Вадим): канала вдоль города больше нет — река у Тихой долины уходит вниз в море
(восточная граница долины, устье с лагуной); мостов к пляжу нет: нижняя улица Даунтауна прямая (Ocean Drive, y 246) по всей
ширине, ниже сразу пальмы, песок и море; улицы города прямо выходят на пляжную дорогу.
Ранее v37 (TASK-000720, Вадим): от v35 — западный блок (Хутор, лес, Тихая долина, гора H, река, горы СЗ) на 70 м
вправо, город и всё восточнее на месте: гора H упирается в западный край Даунтауна, пустых карманов нет; Стройка вместе с
блоком, уже (x 0.82); спуск с перевала VIEW H петлями прямо к мосту в улицу Хутора; спуск в город — короткая выемка, на
выезде город перед тобой, один широкий поворот к въезду; лишние холмы и расщелины у города убраны.
Ранее v35 (TASK-000698, Вадим): горы ниже и открытее (H ~32 м, гряда ~14 м, над тоннелем ~24 м), лес рощами
вместо сплошного, больше равнин; между Тихой долиной и пляжем — дюны с грунтовкой (можно срезать на бусике), острые скалы
только полосой у воды.
Ранее v34 (TASK-000697, Вадим): пляж уже по вертикали (море ближе, ~55 м песка), третий мост через канал
к пляжу (по улице x 948); у Хутора вместо двух мостов — природные перемычки (река уходит под землю и выходит с другой
стороны, по зелёной перемычке идёт дорога); гряда между Неблагополучным и Даунтауном и гора над тоннелем ниже; справа
от Тихой долины — серые острые скалы (не проехать).
Ранее v33 (TASK-000689, Вадим): тоннель с полукруглым сводом от юго-западного угла Неблагополучного к
северо-западному углу Даунтауна (~110 м); сплошной лесистый хребет: гора H (+50) -> седловина за Стройкой -> гора над
тоннелем -> гряда RD (срезать между Стройкой и горой незачем и негде); предгорья и рощи вместо пустого луга, две
расщелины; спуск с перевала VIEW H — коридор (отрог слева, холм справа). Дорога-перевал через гряду остаётся («тайная»).
Ранее v32 (TASK-000681, Вадим): гора H выше (+45 м), дорога в город поднимается к ней серпантином (2 петли)
на перевал в скальной выемке (VIEW H, ~+24 м), оттуда открывается город, длинный спуск к Даунтауну.
Ранее v31 (TASK-000681, Вадим, по рисунку): объездная Хутора дальше на север, мост через реку у y 663,
дорога в Неблагополучный: прямо на восток, поворот налево вверх, снова прямо в середину западной стороны района;
Стройка — большая площадка справа под этой дорогой (~170 x 115 м), контур неправильный, по местности.
Ранее v30 (TASK-000681, Вадим): v29 + мост из Хутора через реку выше (y 642); дорога в Неблагополучный: прямо
на восток, плавный поворот налево, снова прямо; Стройка вдоль первого прямого участка (справа), подальше от Неблагополучного.
Ранее v29 (TASK-000681, Вадим): v28 + дорога Хутор -> Неблагополучный почти прямая (без полукруга),
Стройка больше (164 x 97 м) и ниже по склону.
Ранее v28 (TASK-000680, Вадим): v27 +
  - Стройка — длинная полоса вдоль дороги Хутор -> Неблагополучный (справа от неё), повёрнута по дороге (27°);
    планировка переложена: постройки и техника группами переставлены по полосе (без искажения), грунт растянут;
  - верх острова: за горами и над Неблагополучным — море и скалистый берег;
  - подписи видов и высот в отдельной группе (в чистом рендере для макета их нет).
Ранее v27 (TASK-000679, Вадим): v25 +
  - дорога Хутор -> Неблагополучный выше по карте: заходит в середину западной стороны района и поворачивает направо
    (внутрь района), Стройка (меньше, 0.8) стоит справа от неё; холм VIEW H (+35 м) свободный, через него дорога в город;
  - Порт горизонтальный (1.25 x 0.8), правая сторона слегка выпуклая; карниз C вливается в дорогу через середину Порта
    (из Неблагополучного к мосту на Трамдуро); Трамдуро на 20 м правее.
Ранее v25 (TASK-000675, Вадим): v24 +
  - Порт и Стройка не прямоугольники: другой контур (Порт — скошенные стороны и пирс в бухту, Стройка — неправильный
    многоугольник с забором), Стройка ниже (на 60 м) на холме прямо у дороги Хутор -> Неблагополучный;
  - Порт и Трамдуро ещё на 40 м правее; карниз C заходит в южные ворота Порта.
Ранее v24 (TASK-000671, Вадим): от v22, вариант «одна большая гора»:
  - Стройка переезжает на север (к Неблагополучному, южнее гор); на её старом месте между Хутором и Даунтауном —
    большая живописная гора H (+40 м), главная дорога Хутор -> Даунтаун переваливает её: с плеча видно и долину
    Хутора, и весь город;
  - Неблагополучный правее (+150 м) и чуть выше (+45 м), ближе к Порту; между ним и Даунтауном большая гора RD;
  - Порт с Трамдуро — вместе с Неблагополучным (+150, +45), т. е. ниже, чем в v23;
  - карниз C: от северо-восточного угла Даунтауна к Порту, выгнут влево (вглубь суши) вокруг бухточки, гора-мыс слева;
  - даунтаун, пляж, Элитный холм +80 м на восток (растяжение в полосе x 575-615).
Деформация MASTER_v22.svg (как v23): постоянный сдвиг внутри районов, растяжение между ними; Стройка — жёсткий перенос
группы D03. Все дороги, которые будут в итоге, нарисованы и соединены."""
import math
import os
import random
import re
import subprocess
from urllib.parse import unquote

from PIL import Image

MAP = r'C:\Users\chern_0eqkb03\Desktop\Map'
OUTD = os.path.join(MAP, 'Итоговая карта')
ASSETS = os.path.join(MAP, '00_Сборка_общей_карты', 'v58_assets')
SRC = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v22.svg')
SVG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_MASTER_v58.svg')
PNG_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_FINAL_v58.png')
PRE_OUT = os.path.join(OUTD, 'VOLUNTEERS_MAP_PREVIEW_v58.png')
Image.MAX_IMAGE_PIXELS = None
os.makedirs(ASSETS, exist_ok=True)

GROW_X, GROW_Y = 270.0, 85.0
CONSTR_OLD = (425, 330, 560, 485)                  # Стройка в v22 (x0, y0, x1, y1)
CONSTR_D = (70.0, 85.0)                            # перенос Стройки, м -> (495..630, 415..570): на холме слева от дороги через VIEW H


def r(t, a, b):
    t = min(1.0, max(0.0, (t - a) / (b - a)))
    return t * t * (3 - 2 * t)


def warp_m(x, y):
    """Метры мира v22 -> v24."""
    if y >= 838:                                    # верхний край холста тянется к новому краю
        y2 = y + GROW_Y + 10
    else:
        y2 = None
    sy = r(y, 505, 575 - 35 * r(x, 880, 940))       # юг (Даунтаун и всё южнее) -> север (Неблагополучный, Порт)
    rn = r(x, 520, 545)
    dx = (1 - sy) * (70 + 70 * r(x, 575, 615)) + sy * (70 * (1 - rn) + rn * (110 + 140 * r(x, 880, 940) + 20 * r(x, 1088, 1110)))   # запад +70, город +140, Неблагополучный +110, Порт +250
    dy = sy * rn * (75 - 30 * r(x, 880, 940))                    # Неблагополучный +75, Порт +45
    return x + dx, (y2 if y2 is not None else y + dy)


def to_m(px, py):
    return (px + 350) / 5.0, (3500 - py) / 5.0


def to_u(xm, ym):
    return xm * 5 - 350, 3500 - ym * 5


def warp_u(px, py):
    return to_u(*warp_m(*to_m(px, py)))


NUM = r'-?\d+(?:\.\d+)?(?:e-?\d+)?'


def f1(v):
    return ('%.1f' % v).rstrip('0').rstrip('.')


def warp_pairs(txt, ox, oy):
    out, pos = [], 0
    for m in re.finditer(r'(%s)(\s*,\s*|\s+)(%s)' % (NUM, NUM), txt):
        out.append(txt[pos:m.start()])
        X, Y = warp_u(float(m.group(1)) + ox, float(m.group(3)) + oy)
        out.append(f1(X - ox) + m.group(2) + f1(Y - oy))
        pos = m.end()
    out.append(txt[pos:])
    return ''.join(out)


def pairs_m(txt, ox, oy):
    n = [float(v) for v in re.findall(NUM, txt)]
    return [to_m(x + ox, y + oy) for x, y in zip(n[0::2], n[1::2])]


def attr(tag, name):
    m = re.search(r'\s%s="(%s)"' % (name, NUM), tag)
    return float(m.group(1)) if m else None


def set_attr(tag, name, val):
    return re.sub(r'(\s%s=")(%s)(")' % (name, NUM), lambda m: m.group(1) + f1(val) + m.group(3), tag, count=1)


def chaikin(p, n=3):
    for _ in range(n):
        q = [p[0]]
        for a, b in zip(p[:-1], p[1:]):
            q += [(a[0] * .75 + b[0] * .25, a[1] * .75 + b[1] * .25), (a[0] * .25 + b[0] * .75, a[1] * .25 + b[1] * .75)]
        q.append(p[-1])
        p = q
    return p


def seg_d(p, a, b):
    ax, ay = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * ax + (p[1] - a[1]) * ay) / (ax * ax + ay * ay or 1)))
    return math.hypot(a[0] + ax * t - p[0], a[1] + ay * t - p[1])


def pl_d(p, pl):
    return min(seg_d(p, a, b) for a, b in zip(pl[:-1], pl[1:]))


def inside(p, poly):
    c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > p[1]) != (y2 > p[1]) and p[0] < (x2 - x1) * (p[1] - y1) / (y2 - y1) + x1:
            c = not c
    return c


# ---------------------------------------------------------------- новое (метры мира v24)
CONSTR_NEW = (CONSTR_OLD[0] + CONSTR_D[0], CONSTR_OLD[1] + CONSTR_D[1], CONSTR_OLD[2] + CONSTR_D[0], CONSTR_OLD[3] + CONSTR_D[1])
VIEWS = {'B': (1010, 594), 'C': (1194, 532)}
# главная дорога Хутор -> Даунтаун через гору H (от моста у ущелья до западного въезда в Даунтаун x 726)
# Хутор -> Даунтаун через гору H: от моста в улицу Хутора петлями вверх на перевал, выемка, открытие, один поворот к въезду
ROAD_H = [(496, 348), (530, 347), (600, 348), (700, 348), (786, 348)]   # как у Феди: от объездной Хутора прямо на восток в Даунтаун, Стройка слева
BRIDGE_H = [(470, 466), (497, 466)]                               # мост через реку прямо в улицу Хутора
ROAD_VALLEY = [(530, 347), (541, 336), (543, 322)]    # от объездной Хутора к Тихой долине
# карниз: от северо-восточного угла Даунтауна, выгнут влево вокруг бухточки, к южным воротам Порта
ROAD_C = chaikin([(1222, 438), (1219, 462), (1210, 485), (1199, 508), VIEWS['C'], (1202, 556), (1222, 572), (1244, 582),
                  (1258, 596), (1263, 616), (1263, 633)])          # до середины Порта, на дорогу Неблагополучный -> мост на Трамдуро
# Хутор -> Неблагополучный: выше по карте, в середину западной стороны района, там поворот направо (внутрь района)
def _arc(a, c, b, n=10):
    return [((1 - t) ** 2 * a[0] + 2 * t * (1 - t) * c[0] + t * t * b[0], (1 - t) ** 2 * a[1] + 2 * t * (1 - t) * c[1] + t * t * b[1])
            for t in [i / n for i in range(n + 1)]]


# Хутор -> Неблагополучный: мост через реку у y 642, прямо на восток, поворот налево (R 60 м), прямо в середину западной стороны
ROAD_R = chaikin([(505, 572), (555, 573), (590, 581), (612, 598), (630, 624), (646, 644), (658, 651)], 3) + [(666, 652)]   # от перемычки y 572 дугой в нижний перекрёсток
BYP_PTS = [(496, 348), (481, 348), (467, 357), (463, 392), (461, 480), (461, 534), (463, 555), (469, 567), (482, 572), (505, 572)]
ROAD_BN = chaikin(BYP_PTS, 3)                                     # вся объездная поверх BYP (без колец на стыках)   # объездная Хутора -> мост
BRIDGE_N = [(468, 663), (500, 663)]
ROAD_RING = [(686, 766), (676, 766), (666, 766), (666, 652)]                              # от въезда вниз к западной стороне кольца района
ROAD_CONSTR = [(0.0, 0.0), (0.0, 0.0)]                           # ворота Стройки (задаются ниже, после контура)
TUN = [(748, 627), (770, 604), (805, 568), (838, 532), (855, 516)]   # v56: порталы у подножия, подъезды ~25 и ~40 м               # ось тоннеля (порталы: север (708, 604), юг (731, 494))
TUN_N = [(748, 652), (748, 640), (748, 627)]   # выезд в проём между базой 3 и корпусом, не в стену                          # подъезд к северному порталу от угла Неблагополучного
TUN_S = [(855, 516), (859, 497), (860, 477)]   # выезд на улицу Даунтауна x 860                        # от южного портала к углу Даунтауна
RAVINES = []
ROAD_S = [(945, 650)] + chaikin([(952, 636), (938, 618), (962, 604), VIEWS['B'], (1038, 584), (1020, 566), (1044, 550), (1068, 540),
                                 (1056, 522), (1070, 500)], 3) + [(1070, 477)]   # серпантин через восточную часть холма B (бухта, Порт, город)
ROAD_W = chaikin([(690, 348), (691, 420), (692, 480), (684, 560), (670, 620), (666, 652)], 2)   # как у Феди: от главной у Стройки на север в Неблагополучный
ROAD_N = [(666, 766), (663, 782), (662, 860), (662, 897)]          # v57: от угла Неблагополучного на север к пирсу погранпоста
MT_E = [(512, 772), (535, 778), (565, 794), (596, 812), (622, 832), (640, 856), (646, 884), (636, 904), (600, 914), (556, 912), (540, 873), (512, 872)]   # v57: продолжение хребта
NEWROADS = [ROAD_H, ROAD_VALLEY, ROAD_C, ROAD_CONSTR, ROAD_R, ROAD_RING, ROAD_BN, TUN_N, TUN_S, ROAD_S, ROAD_N]   # v56: без ROAD_W (Стройка -> Неблагополучный)
# горы: (имя, гребень, полуширина, высота)
MOUNTS = [
    ('B', [(752, 556), (840, 574), (920, 590), (1000, 586), (1080, 574), (1150, 562)], 58, 50),
]
COVE = None                                                       # бухточка у карниза — вычисляется ниже


def _cove():
    pts = []
    for i in range(1, len(ROAD_C) - 1):
        a, b = ROAD_C[i - 1], ROAD_C[i + 1]
        p = ROAD_C[i]
        if not 488 < p[1] < 580:
            continue
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        off = 15 + 4 * math.sin(i * 0.7)
        pts.append((p[0] + dy / L * off, p[1] - dx / L * off))
    return pts + [(1350, pts[-1][1] - 6), (1350, pts[0][1] + 6)]


COVE = _cove()


def in_mount_core(p):
    return any(pl_d(p, crest) < hw * 0.8 for _, crest, hw, _ in MOUNTS)


def in_constr(p):
    return inside(p, CONSTR_POLY) or pl_d(p, CONSTR_POLY + CONSTR_POLY[:1]) < 6


# контур Стройки (локальные единицы группы D03: прямоугольник был 74..790 x 60..850)
CONSTR_CLIP_LOCAL = [(105, 200), (430, 93), (716, 260), (692, 693), (290, 694), (105, 560)]
CONSTR_LC = (410.0, 393.0)                                        # центр содержимого (локальные единицы D03)
CONSTR_SXY = (1.15, 0.95)                                         # площадка ~140 x 115 м (уже)
CONSTR_ROT = 0.0                                                  # вдоль прямого участка дороги (на восток)
CONSTR_G = (604.0, 418.0)                                         # центр площадки, м: справа под дорогой, зазор ~12 м
# контур Стройки в метрах мира (неправильный, по местности: верх вдоль дороги, правый край волной), -> локальные единицы D03
CONSTR_SHAPE_W = [(604 + (x - 564) * 0.82, y - 186) for x, y in [(482, 652), (500, 659), (545, 659), (585, 667), (617, 674), (640, 666), (650, 640), (642, 612),
                                          (649, 586), (636, 562), (608, 550), (570, 547), (530, 552), (500, 561), (486, 581), (479, 616)]]
CONSTR_CLIP_LOCAL = [(CONSTR_LC[0] + (x - CONSTR_G[0]) * 5, CONSTR_LC[1] - (y - CONSTR_G[1]) * 5) for x, y in CONSTR_SHAPE_W]


def constr_world(lx, ly):
    a = math.radians(-CONSTR_ROT)
    vx, vy = lx - CONSTR_LC[0], ly - CONSTR_LC[1]
    gx, gy = to_u(*CONSTR_G)
    return to_m(gx + vx * math.cos(a) - vy * math.sin(a), gy + vx * math.sin(a) + vy * math.cos(a))


CONSTR_POLY = [constr_world(x, y) for x, y in CONSTR_CLIP_LOCAL]
_gate = (600.0, 363.0)
ROAD_CONSTR[:] = [_gate, (_gate[0], 349.0)]                                 # ворота Стройки на дорогу в Неблагополучный
CONSTR_BOX = (min(p[0] for p in CONSTR_POLY), min(p[1] for p in CONSTR_POLY), max(p[0] for p in CONSTR_POLY), max(p[1] for p in CONSTR_POLY))
CONSTR_LABEL_D = (90.0, -158.0)                                    # подпись Стройки — под ней
# Порт: масштаб вокруг центра, контур в итоговых координатах
PORT_C = (1261, 636.0)
PORT_SCALE = (1.25, 0.8)
PORT_SHAPE = [(1178, 672), (1176, 611), (1191, 599), (1320, 598), (1341, 609), (1352, 637), (1344, 664), (1325, 677), (1191, 679)]


def port_pre(p):
    return PORT_C[0] + (p[0] - PORT_C[0]) / PORT_SCALE[0], PORT_C[1] + (p[1] - PORT_C[1]) / PORT_SCALE[1]
# контур Порта (метры v25): скошенные углы; пирс отдельно
PORT_SHIFT = (190.0, 45.0)
PORT_POLY = [(1134, 686), (1134, 622), (1156, 587), (1236, 586), (1268, 606), (1270, 662), (1252, 686)]
PIER = [(1274, 677), (1298, 677), (1300, 714), (1290, 721), (1278, 716)]
ROUGH_LABEL_D = (235.0, 80.0)                                    # подпись Неблагополучного — к его новому углу


def old_rough_label(p):
    return 455 <= p[0] <= 620 and 800 <= p[1] <= 832


def old_in_constr(p):
    x0, y0, x1, y1 = CONSTR_OLD
    return x0 - 2 <= p[0] <= x1 + 2 and y0 - 2 <= p[1] <= y1 + 2


# ---------------------------------------------------------------- растровые вставки
def place_image(tag, ox, oy):
    x, y, w, h = attr(tag, 'x') + ox, attr(tag, 'y') + oy, attr(tag, 'width'), attr(tag, 'height')
    xm0, xm1 = to_m(x, 0)[0], to_m(x + w, 0)[0]
    ym0, ym1 = to_m(0, y + h)[1], to_m(0, y)[1]
    href = re.search(r'href="file:///([^"]+)"', tag)
    if href and xm0 < 423 < xm1 < 460:                          # план Хутора: в растре был кусок Стройки — убрать
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        cut = int((423 - xm0) / (xm1 - xm0) * im.width)
        a = im.getchannel('A')
        a.paste(0, (cut, 0, im.width, im.height))
        bx0 = int((400 - xm0) / (xm1 - xm0) * im.width)                # мост через реку у восточного края растра
        by0, by1 = int((ym1 - 588) / (ym1 - ym0) * im.height), int((ym1 - 558) / (ym1 - ym0) * im.height)
        a.paste(0, (bx0, by0, cut, by1))
        px_, ap_ = im.load(), a.load()                                 # старая дорога вдоль реки в растре (её заменяет объездная BYP)
        for i_ in range(int(im.width * 0.78), cut):
            for j_ in range(im.height):
                r_, g_, b_, _ = px_[i_, j_]
                if r_ < 130 and g_ < 135 and b_ < 140 and abs(r_ - b_) < 22 and abs(g_ - r_) < 16:
                    ap_[i_, j_] = 0
        im.putalpha(a)
        dst = os.path.join(ASSETS, 'C_' + os.path.basename(srcf))
        im.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
    if href and xm0 < 520 < xm1 and ym1 > 575:                  # план через полосу растяжения на севере — по столбцам
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        sc = im.width / w
        yc = to_m(0, y + h / 2)[1]
        X0, X1 = warp_u(x, y + h / 2)[0], warp_u(x + w, y + h / 2)[0]
        nw = int(round((X1 - X0) * sc))
        out = Image.new('RGBA', (nw, im.height))
        fw = [warp_m(to_m(x + i / sc, 0)[0], yc)[0] for i in range(im.width + 1)]
        k = 0
        for c in range(nw):
            X = to_m(X0 + (c + .5) / sc, 0)[0]
            while k < len(fw) - 2 and fw[k + 1] < X:
                k += 1
            out.paste(im.crop((min(im.width - 1, k), 0, min(im.width - 1, k) + 1, im.height)), (c, 0))
        dst = os.path.join(ASSETS, 'W_' + os.path.basename(srcf))
        out.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
        Y0 = warp_u(x, y + h / 2)[1] - h / 2
        return set_attr(set_attr(set_attr(tag, 'x', X0 - ox), 'width', X1 - X0), 'y', Y0 - oy)
    cx, cy = x + w / 2, y + h / 2
    X, Y = warp_u(cx, cy)
    if href and 900 < xm0 < 930 and 1100 < xm1 < 1125:                  # план Порта: контур не прямоугольный
        from PIL import ImageChops, ImageDraw, ImageFilter
        srcf = unquote(href.group(1)).replace('/', os.sep)
        im = Image.open(srcf).convert('RGBA')
        sc = im.width / w
        pc = to_u(*PORT_C)
        wx0, wy0 = X - w / 2, Y - h / 2                                    # картинка после сдвига (+190, +45)
        nx0, ny0 = pc[0] + (wx0 - pc[0]) * PORT_SCALE[0], pc[1] + (wy0 - pc[1]) * PORT_SCALE[1]
        nw_, nh_ = w * PORT_SCALE[0], h * PORT_SCALE[1]
        im = im.resize((int(round(im.width * PORT_SCALE[0])), int(round(im.height * PORT_SCALE[1]))), Image.LANCZOS)
        mk = Image.new('L', im.size, 0)
        ImageDraw.Draw(mk).polygon([((to_u(*p)[0] - nx0) * sc, (to_u(*p)[1] - ny0) * sc) for p in PORT_SHAPE], fill=255)
        mk = mk.filter(ImageFilter.GaussianBlur(2))
        im.putalpha(ImageChops.multiply(im.getchannel('A'), mk))
        dst = os.path.join(ASSETS, 'P_' + os.path.basename(srcf))
        im.save(dst)
        tag = tag.replace(href.group(1), dst.replace(os.sep, '/'))
        tag = set_attr(set_attr(tag, 'width', nw_), 'height', nh_)
        return set_attr(set_attr(tag, 'x', nx0 - ox), 'y', ny0 - oy)
    return set_attr(set_attr(tag, 'x', x + X - cx - ox), 'y', y + Y - cy - oy)


# ---------------------------------------------------------------- дороги: что убрать / заменить
def drop_polyline(gids, pts_old):
    """Старые дороги, которых больше нет (по координатам v22)."""
    xs, ys = [p[0] for p in pts_old], [p[1] for p in pts_old]
    if 'L05b_bridges' in gids and abs(pts_old[0][0] - 408) < 2 and abs(pts_old[0][1] - 348) < 2:
        return True                                    # мост главной дороги у Хутора -> природная перемычка
    if 'L05b_bridges' in gids and abs(pts_old[0][0] - 411) < 2 and abs(pts_old[0][1] - 571) < 2:
        return True                                    # старый мост из Хутора (новый — выше, у y 642)
    if abs(pts_old[0][0] - 812) < 3 and abs(pts_old[0][1] - 574) < 3 and max(xs) < 950:
        return True                                    # старая дорога-перевал Неблагополучный -> Даунтаун (теперь серпантин через холм B)
    if 'R18_links' in gids and abs(pts_old[0][0] - 1082) < 3 and abs(pts_old[0][1] - 438) < 3:
        return True                                    # старый карниз v22
    if min(xs) > 548 and max(xs) < 568 and max(ys) - min(ys) > 40 and min(ys) > 340:
        return True                                    # Стройка -> Неблагополучный по x 556-563 (Стройки там больше нет)
    if min(xs) >= 565 and max(xs) <= 650 and all(340 < v < 356 for v in ys):
        return True                                    # главная Стройка -> Даунтаун (заменена дорогой через гору H)
    if abs(pts_old[0][0] - 425) < 2 and abs(pts_old[0][1] - 574) < 2 and max(xs) < 540:
        return True                                    # старая Хутор -> Неблагополучный (заменена дорогой мимо Стройки)
    if 'd03_roads' in gids or 'd03_terrain' in gids:
        return True                                    # дороги и река внутри плана Стройки (план переезжает без них)
    return False


# ---------------------------------------------------------------- проход по тегам
s = open(SRC, encoding='utf-8').read()


def _bbox(tag, name):
    if name == 'circle':
        cx, cy, rr = attr(tag, 'cx'), attr(tag, 'cy'), attr(tag, 'r') or 1
        return cx - rr, cy - rr, cx + rr, cy + rr
    if name == 'text':
        return attr(tag, 'x') - 10, attr(tag, 'y') - 10, attr(tag, 'x') + 10, attr(tag, 'y') + 10
    if name == 'rect':
        x, y = attr(tag, 'x'), attr(tag, 'y')
        return x, y, x + attr(tag, 'width'), y + attr(tag, 'height')
    src = re.search(r'(?:points|\sd)="([^"]*)"', tag)
    if not src:
        return None
    n = [float(v) for v in re.findall(NUM, src.group(1))]
    return min(n[0::2]), min(n[1::2]), max(n[0::2]), max(n[1::2])


# Стройка: элементы зданий, техники и номеров — кластерами по пересечению рамок; каждый кластер переставляется целиком
_d0, _d1 = s.index('<g id="D03"'), s.index('<g id="D09"')
_items, _grp = [], []
for q in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', s[_d0:_d1]):
    cl, nm, tg = q.group(1), q.group(2), q.group(0)
    if nm == 'g':
        if cl:
            _grp.pop()
        else:
            gi = re.search(r'id="([^"]+)"', tg)
            _grp.append(gi.group(1) if gi else '')
            if q.group(4):
                _grp.pop()
        continue
    if cl or nm in ('clipPath', 'defs', 'tspan'):
        continue
    sub = next((g for g in reversed(_grp) if g.startswith('d03_')), '')
    bb = _bbox(tg, nm)
    if bb:
        _items.append((_d0 + q.start(), sub, bb))
_par = list(range(len(_items)))


def _find(i):
    while _par[i] != i:
        _par[i] = _par[_par[i]]
        i = _par[i]
    return i


_movable = [i for i, (_, sub, _) in enumerate(_items) if sub in ('d03_buildings', 'd03_objects', 'd03_numbers')]
for ai in range(len(_movable)):
    a_ = _items[_movable[ai]][2]
    for bi in range(ai + 1, len(_movable)):
        b_ = _items[_movable[bi]][2]
        if a_[0] - 2 <= b_[2] and b_[0] - 2 <= a_[2] and a_[1] - 2 <= b_[3] and b_[1] - 2 <= a_[3]:
            _par[_find(_movable[ai])] = _find(_movable[bi])
_cl = {}
for i in _movable:
    _cl.setdefault(_find(i), []).append(i)
RELAYOUT = {}
for root, members in _cl.items():
    x0 = min(_items[i][2][0] for i in members); y0 = min(_items[i][2][1] for i in members)
    x1 = max(_items[i][2][2] for i in members); y1 = max(_items[i][2][3] for i in members)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    d = (CONSTR_LC[0] + (cx - CONSTR_LC[0]) * CONSTR_SXY[0] - cx, CONSTR_LC[1] + (cy - CONSTR_LC[1]) * CONSTR_SXY[1] - cy)
    for i in members:
        RELAYOUT[_items[i][0]] = d
for off, sub, bb in _items:
    if sub == 'd03_trees':
        cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
        RELAYOUT[off] = (CONSTR_LC[0] + (cx - CONSTR_LC[0]) * CONSTR_SXY[0] - cx, CONSTR_LC[1] + (cy - CONSTR_LC[1]) * CONSTR_SXY[1] - cy)
_MAT = 'matrix(%s 0 0 %s %s %s)' % (CONSTR_SXY[0], CONSTR_SXY[1], f1(CONSTR_LC[0] * (1 - CONSTR_SXY[0])), f1(CONSTR_LC[1] * (1 - CONSTR_SXY[1])))


def relayout(tag, off, gids, name):
    if name in ('clipPath', 'defs', 'tspan') or tag.startswith('</'):
        return tag
    if off in RELAYOUT:
        dx_, dy_ = RELAYOUT[off]
        return tag.replace('<' + name, '<%s transform="translate(%s %s)"' % (name, f1(dx_), f1(dy_)), 1)
    if 'd03_terrain' in gids or 'd03_paths' in gids:
        return tag.replace('<' + name, '<%s transform="%s"' % (name, _MAT), 1)
    return tag
CLIP_OFS = {'clip_d03': (1700.0, 1042.0), 'clip_d05': (2820.0, 1000.0)}
out, pos, stack, clip, gids = [], 0, [], None, []
dropped = {'roads': 0, 'trees': 0, 'rocks': 0}
for m in re.finditer(r'<(/?)(\w+)([^>]*?)(/?)>', s):
    out.append(s[pos:m.start()])
    pos = m.end()
    tag = m.group(0)
    closing, name = m.group(1), m.group(2)
    if name == 'g':
        if closing:
            stack.pop()
            gids.pop()
        else:
            t = re.search(r'transform="translate\((%s)[ ,]+(%s)\)"' % (NUM, NUM), tag)
            base = stack[-1] if stack else (0.0, 0.0)
            gid = re.search(r'id="([^"]+)"', tag)
            gid = gid.group(1) if gid else ''
            if gid == 'D03':                            # Стройка: жёсткий перенос всей группы
                tx, ty = float(t.group(1)), float(t.group(2))
                gu = to_u(*CONSTR_G)
                tag = tag.replace(t.group(0), 'transform="translate(%s %s) rotate(%s) translate(%s %s)"' % (
                    f1(gu[0]), f1(gu[1]), f1(-CONSTR_ROT), f1(-CONSTR_LC[0]), f1(-CONSTR_LC[1])))
            if gid == 'D06':                            # Порт: шире и ниже (масштаб вокруг центра)
                cu = to_u(*PORT_C)
                tag = tag.replace('transform="', 'transform="translate(%s %s) scale(%s %s) translate(%s %s) ' % (
                    f1(cu[0]), f1(cu[1]), PORT_SCALE[0], PORT_SCALE[1], f1(-cu[0]), f1(-cu[1])), 1)
            stack.append((base[0] + float(t.group(1)), base[1] + float(t.group(2))) if t else base)
            gids.append(gid)
            if m.group(4):
                gids.pop()
                stack.pop()
        out.append(tag)
        continue
    if name == 'clipPath':
        clip = None if closing else re.search(r'id="([^"]+)"', tag).group(1)
        out.append(tag)
        continue
    if closing or name in ('svg', 'defs', 'filter', 'feGaussianBlur', 'feDropShadow', 'title', 'clipPath', 'tspan'):
        out.append(tag)
        continue
    ox, oy = stack[-1] if stack else (0.0, 0.0)
    if clip:
        ox, oy = CLIP_OFS.get(clip, (0.0, 0.0))
        if clip == 'clip_d03':                          # клип Стройки: неправильный многоугольник вместо прямоугольника
            out.append('<polygon points="%s"/>' % ' '.join('%s,%s' % p for p in CONSTR_CLIP_LOCAL) if name == 'rect' else tag)
            continue
    in_d03 = 'D03' in gids
    if in_d03 and name != 'polyline':                   # содержимое Стройки: группой + перестановка по полосе
        out.append(relayout(tag, m.start(), gids, name))
        continue
    if name in ('polygon', 'polyline', 'path'):
        src = re.search(r'(?:points|\sd)="([^"]*)"', tag)
        old = pairs_m(src.group(1), ox, oy) if src else []
        if 'D08' in gids and (re.search(r'fill="#9FD0E2"', tag) or 'points="408,286' in tag or 'points="470,252' in tag
                              or re.search(r'stroke="#F4FAFC"', tag) or re.search(r'stroke="#8E938A" stroke-width="1.2"', tag)):
            continue                                     # водопад с прудом внутри Тихой долины убран
        if name == 'polyline' and old and 'L04_water' in gids and min(p_[0] for p_ in old) >= 556 and max(p_[1] for p_ in old) < 290:
            continue                                     # конец старой реки к каналу — река теперь падает в бухту у Тихой долины
        if name == 'text' and '>Canal<' in s[m.end():m.end() + 12]:
            out.append(tag.replace('<text', '<text visibility="hidden"', 1))
            continue
        if name in ('polyline', 'polygon') and old and ('L06a_canal' in gids or 'D05' in gids and re.search(r'stroke="#(?:B9B09C|8FC3D9)"', tag)
                                                    and max(p_[1] for p_ in old) < 245):
            dropped['roads'] += 1                        # канал вдоль города убран (река уходит в море у Тихой долины)
            continue
        if name == 'polyline' and old and drop_polyline(gids, old):
            dropped['roads'] += 1
            continue
        if name == 'polyline' and old and 'L05_roads' in gids and len(old) > 3 and abs(old[0][0] - 411) < 2 and abs(old[0][1] - 571) < 2:
            _k = next((i_ for i_, p_ in enumerate(old) if p_[0] <= 396), 1)        # весь хвост к старому мосту
            tag = re.sub(r'points="[^"]*"', 'points="%s"' % ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in old[_k:]), tag, count=1)
        if name == 'polyline' and old and 'D04' in gids and abs(old[0][0] - 500) < 2 and abs(old[0][1] - 611) < 2:
            keep = [p for p in old if p[0] >= 552]               # западный хвост — к новой дороге мимо Стройки
            tag = re.sub(r'points="[^"]*"', 'points="%s"' % ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in keep), tag, count=1)
        if in_d03:
            out.append(relayout(tag, m.start(), gids, name))
            continue
        if name in ('polygon', 'path') and old and any(g.startswith(('L03', 'coast_rocks', 'outcrop', 'islet')) for g in gids):
            if any(x_ > 880 and 500 < y_ < 545 for x_, y_ in old) and 'coast_rocks_island' not in gids:
                dropped['rocks'] += 1                    # береговые камни в полосе сдвига растянулись бы
                continue
    if name in ('polygon', 'polyline') and 'D06' in gids and re.search(r'points="30,40 690,40 700,520 40,530(?: 30,330)?"', tag):
        ring = [port_pre(p) for p in PORT_SHAPE]                               # площадка Порта: новый контур (до масштаба)
        ring = ring + (ring[:1] if name == 'polyline' else [])
        tag = re.sub(r'points="[^"]*"', 'points="%s"' % ' '.join('%s,%s' % (f1(to_u(*p)[0] - ox), f1(to_u(*p)[1] - oy)) for p in ring), tag, count=1)
        out.append(tag)
        continue
    if name in ('polygon', 'polyline'):
        tag = re.sub(r'points="([^"]*)"', lambda q: 'points="%s"' % warp_pairs(q.group(1), ox, oy), tag)
    elif name == 'path':
        tag = re.sub(r'\sd="([^"]*)"', lambda q: ' d="%s"' % warp_pairs(q.group(1), ox, oy), tag)
    elif name in ('circle', 'ellipse'):
        cx0, cy0 = attr(tag, 'cx') + ox, attr(tag, 'cy') + oy
        if 'L11_labels' in gids and old_in_constr(to_m(cx0, cy0 + 60)):
            X, Y = cx0 + CONSTR_LABEL_D[0] * 5, cy0 - CONSTR_LABEL_D[1] * 5
        elif 'L11_labels' in gids and old_rough_label(to_m(cx0, cy0)):
            X, Y = cx0 + ROUGH_LABEL_D[0] * 5, cy0 - ROUGH_LABEL_D[1] * 5
        else:
            X, Y = warp_u(cx0, cy0)
        if 'L08_vegetation' in gids:
            p = to_m(X, Y)
            if in_mount_core(p) or in_constr(p) or inside(p, COVE) or inside(p, MT_E) or any(pl_d(p, rd) < 9 for rd in NEWROADS):
                dropped['trees'] += 1
                continue
        tag = set_attr(set_attr(tag, 'cx', X - ox), 'cy', Y - oy)
    elif name == 'text':
        x0, y0 = attr(tag, 'x') + ox, attr(tag, 'y') + oy
        if 'L11_labels' in gids and old_in_constr(to_m(x0, y0 + 60)) and float(attr(tag, 'font-size') or 0) >= 24:
            X, Y = x0 + CONSTR_LABEL_D[0] * 5, y0 - CONSTR_LABEL_D[1] * 5
        elif 'L11_labels' in gids and old_rough_label(to_m(x0, y0)):
            X, Y = x0 + ROUGH_LABEL_D[0] * 5, y0 - ROUGH_LABEL_D[1] * 5
        else:
            X, Y = warp_u(x0, y0)
        tag = set_attr(set_attr(tag, 'x', X - ox), 'y', Y - oy)
    elif name == 'rect':
        x, y, w, h = attr(tag, 'x'), attr(tag, 'y'), attr(tag, 'width'), attr(tag, 'height')
        if w >= 7000:
            gx, gy = GROW_X * 5, GROW_Y * 5
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', x), 'y', y - gy), 'width', w + gx), 'height', h + gy)
        else:
            X0, Y0 = warp_u(x + ox, y + oy)
            X1, Y1 = warp_u(x + w + ox, y + h + oy)
            if abs((X1 - X0) - w) < 2 and abs((Y1 - Y0) - h) < 2:
                X1, Y1 = X0 + w, Y0 + h
            tag = set_attr(set_attr(set_attr(set_attr(tag, 'x', X0 - ox), 'y', Y0 - oy), 'width', X1 - X0), 'height', Y1 - Y0)
    elif name == 'image':
        tag = place_image(tag, ox, oy)
        tag = re.sub(r'href="file:///[^"]*downtown_v26_world\.png"', 'href="file:///%s"' % os.path.join(
            MAP, '00_Сборка_общей_карты', 'v49_assets', 'downtown_v27_world.png').replace(os.sep, '/'), tag)   # Даунтаун v27
    out.append(tag)
out.append(s[pos:])
s = ''.join(out)
print('dropped', dropped)

s = s.replace('width="7370" height="4200" viewBox="-350 -700 7370 4200"',
              'width="%d" height="%d" viewBox="-350 %d %d %d"' % (7370 + GROW_X * 5, 4200 + GROW_Y * 5, -700 - GROW_Y * 5, 7370 + GROW_X * 5, 4200 + GROW_Y * 5), 1)


def fix_title_legend(g):
    g = re.sub(r'(<(?:rect|text)\b[^>]*?\sy=")(%s)(")' % NUM,
               lambda q: q.group(1) + f1(float(q.group(2)) - GROW_Y * 5) + q.group(3)
               if float(q.group(2)) < -400 and 'x="-348"' not in q.group(0) and 'x="-314"' not in q.group(0) else q.group(0), g)
    # легенда, масштаб, стрелка севера (справа внизу) — к новому правому краю (+70 м сверх сдвига Даунтауна)
    def shift(q):
        v = float(q.group(2))
        return q.group(1) + f1(v + 650) + q.group(3) if v > 5000 else q.group(0)
    g = re.sub(r'(\s(?:x|cx|x1|x2)=")(%s)(")' % NUM, shift, g)
    g = re.sub(r'(points=")([^"]*)(")', lambda q: q.group(1) + re.sub(r'(%s)(,)' % NUM, lambda z: (f1(float(z.group(1)) + 650) if float(z.group(1)) > 5000 else z.group(1)) + ',', q.group(2)) + q.group(3), g)
    return g


a = s.index('<g id="L12_title_legend"')
s = s[:a] + fix_title_legend(s[a:])

# ---------------------------------------------------------------- горы, лес, скалы, бухточка, дороги
rnd = random.Random(24)


def buffer_poly(crest, hw, seed):
    """Замкнутая горизонталь: точки на расстоянии ~hw от гребня (лучи из центра гребня, бинарный поиск)."""
    c = chaikin(crest, 3)
    cx = sum(p[0] for p in c) / len(c)
    cy = sum(p[1] for p in c) / len(c)
    rr = random.Random(seed)
    ph = [rr.uniform(0, 6.28) for _ in range(2)]
    pts = []
    for k in range(96):
        a = k * 2 * math.pi / 96
        d = hw * (1 + 0.06 * math.sin(3 * a + ph[0]) + 0.035 * math.sin(7 * a + ph[1]))
        lo, hi = 0.0, 2000.0
        for _ in range(28):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if pl_d(q, c) < d:
                lo = mid
            else:
                hi = mid
        pts.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return pts


def ptxt(pts):
    return ' '.join('%s,%s' % tuple(f1(v) for v in to_u(*p)) for p in pts)


def rock(q, R):
    n = rnd.randint(6, 9)
    pts = [(q[0] + R * (0.7 + 0.5 * rnd.random()) * math.cos(t * 6.283 / n), q[1] + R * 0.8 * (0.7 + 0.5 * rnd.random()) * math.sin(t * 6.283 / n)) for t in range(n)]
    return '<polygon points="%s" fill="#C4C5B7" stroke="#8E938A" stroke-width="2" stroke-linejoin="round"/>' % ptxt(pts)


def Fbm2(p):
    return 0.5 + 0.25 * math.sin(p[0] / 23.0 + 1.7) * math.sin(p[1] / 19.0 + 0.4) + 0.25 * math.sin(p[0] / 9.0) * math.cos(p[1] / 11.0)


def coast_y(x):
    return 908 + 7 * math.sin(x / 41.0) + 5 * math.sin(x / 13.0 + 1.3) if 540 <= x <= 1060 else 9999


# все дороги, с которых убираем деревья (новые + старые асфальт и грунт после деформации, без групп со сдвигом)
KEEP_CLEAR = list(NEWROADS)
for gname in ('L05_roads', 'D04'):
    a = s.index('<g id="%s"' % gname)
    seg = s[a:a + 400000]
    seg = seg[:seg.index('<g id="', 20)] if '<g id="' in seg[20:] else seg
    for pl in re.findall(r'<polyline[^>]*stroke="#(?:D3D2C3|E5D2A4)"[^>]*/>', seg):
        KEEP_CLEAR.append(pairs_m(re.search(r'points="([^"]*)"', pl).group(1), 0, 0))

HILLS, TREES, ROCKS = ['<g id="R24_mountains">'], ['<g id="R24_forest" filter="url(#tshadow)">'], ['<g id="R24_rocks">']
for k, (nm, crest, hw, hgt) in enumerate(MOUNTS):
    for lvl in range(5):
        f = 1 - lvl * 0.19
        HILLS.append('<polygon points="%s" fill="%s" fill-opacity="%.2f" stroke="#93A979" stroke-width="3" stroke-opacity="0.6"/>'
                     % (ptxt(buffer_poly(crest, hw * f, k * 10 + lvl)), ('#C9D6B4', '#BFD0A8', '#B4C79C', '#A9BE91', '#9EB585')[lvl], 0.55 + lvl * 0.09))
    cc = chaikin(crest, 3)
    xs, ys = [p[0] for p in cc], [p[1] for p in cc]
    L = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(cc[:-1], cc[1:]))
    for _ in range(int(hw * L / 40)):
        p = (rnd.uniform(min(xs) - hw, max(xs) + hw), rnd.uniform(min(ys) - hw, max(ys) + hw))
        if pl_d(p, cc) > hw * 0.84 or any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or in_constr(p) or Fbm2(p) < 0.47:
            continue
        if any(math.hypot(p[0] - v[0], p[1] - v[1]) < 34 for v in VIEWS.values()):
            continue
        TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                     % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 14.5)), rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74', '#9DBB83'))))
    for j in range(len(cc) // 6):                       # скалы у вершины
        q = cc[rnd.randrange(len(cc))]
        q = (q[0] + rnd.uniform(-hw * .3, hw * .3), q[1] + rnd.uniform(-hw * .3, hw * .3))
        if not any(pl_d(q, r_) < 14 for r_ in KEEP_CLEAR):
            ROCKS.append(rock(q, rnd.uniform(4, 9)))
    mid = cc[len(cc) // 2]
    HILLS.append('<text x="%s" y="%s" font-size="32" font-style="italic" fill="#5E7149" text-anchor="middle">+%d m</text>'
                 % (f1(to_u(*mid)[0]), f1(to_u(*mid)[1]), hgt))
# гора-мыс у карниза (слева от дороги) — часть RD; лес по её склону к бухточке
for _ in range(260):
    p = (rnd.uniform(1060, 1140), rnd.uniform(500, 585))
    if any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or inside(p, COVE) or math.hypot(p[0] - VIEWS['C'][0], p[1] - VIEWS['C'][1]) < 30:
        continue
    TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 13)), rnd.choice(('#7FA36A', '#86A971', '#93B47B'))))
for _ in range(9):                                                # перелески у дороги Хутор - Неблагополучный
    c0 = (rnd.uniform(440, 640), rnd.uniform(600, 700))
    for _ in range(26):
        p = (c0[0] + rnd.gauss(0, 13), c0[1] + rnd.gauss(0, 10))
        if any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or in_constr(p) or abs(p[0] - 415) < 14:
            continue
        TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                     % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 13)), rnd.choice(('#86A971', '#93B47B', '#9DBB83', '#A7C48C'))))
# скалы обрыва вдоль карниза и бухточки
for q in COVE[:-2]:
    ROCKS.append(rock((q[0] + rnd.uniform(-2, 3), q[1] + rnd.uniform(-2, 2)), rnd.uniform(5, 9)))
# северный берег над Неблагополучным: море, камни, полоса леса
coast = [(x, coast_y(x)) for x in range(540, 1061, 6)]
SEA_N = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(540, 1000)] + coast + [(1060, 1000)])
for x, y in coast[::3]:
    ROCKS.append(rock((x, y - 2), rnd.uniform(3, 6)))
for _ in range(220):
    p = (rnd.uniform(560, 1040), rnd.uniform(856, 876))
    if p[1] > coast_y(p[0]) - 7:
        continue
    TREES.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(8, 12)), rnd.choice(('#86A971', '#93B47B', '#9DBB83'))))
HILLS.append('</g>')
TREES.append('</g>')
ROCKS.append('</g>')

COVE_SVG = '<polygon points="%s" fill="#B4D9E5" filter="url(#soft_s)"/>' % ptxt(COVE)


def poly_ring(poly, d):
    cx = sum(p[0] for p in poly) / len(poly)
    cy = sum(p[1] for p in poly) / len(poly)
    closed = poly + poly[:1]
    pts = []
    for k in range(90):
        a = k * 2 * math.pi / 90
        lo, hi = 0.0, 600.0
        for _ in range(26):
            mid = (lo + hi) / 2
            q = (cx + mid * math.cos(a), cy + mid * math.sin(a))
            if inside(q, poly) or pl_d(q, closed) < d * (1 + 0.08 * math.sin(3 * a)):
                lo = mid
            else:
                hi = mid
        pts.append((cx + lo * math.cos(a), cy + lo * math.sin(a)))
    return pts


CHILL = ''.join('<polygon points="%s" fill="%s" fill-opacity="0.75" stroke="#93A979" stroke-width="3" stroke-opacity="0.6"/>'
                % (ptxt(poly_ring(CONSTR_POLY, d)), col) for d, col in ((26, '#C9D6B4'), (13, '#BFD0A8')))
CHILL_LABEL = '<text x="%s" y="%s" font-size="30" font-style="italic" fill="#5E7149">+8 m</text>' % (f1(to_u(668, 640)[0]), f1(to_u(668, 640)[1]))
_cx = sum(p[0] for p in CONSTR_POLY) / len(CONSTR_POLY)
_cy = sum(p[1] for p in CONSTR_POLY) / len(CONSTR_POLY)
for _ in range(1600):                                             # лес по склонам холма Стройки
    p = (rnd.uniform(_cx - 160, _cx + 160), rnd.uniform(_cy - 160, _cy + 160))
    if inside(p, CONSTR_POLY):
        continue
    d = pl_d(p, CONSTR_POLY + CONSTR_POLY[:1])
    if d < 9 or d > 26 or any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR):
        continue
    if rnd.random() > 0.55:
        continue
    TREES.insert(-1, '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                 % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 14)), rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74'))))
FENCE = '<polygon points="%s" fill="none" stroke="#6E8AA6" stroke-width="4"/>' % ptxt(CONSTR_POLY)
PIER_SVG = ('<polygon points="%s" fill="#C9CBC4" stroke="#8E938A" stroke-width="3"/>' % ptxt(PIER) +
            ''.join('<circle cx="%s" cy="%s" r="4" fill="#5F666C"/>' % tuple(f1(v) for v in to_u(1217, yy)) for yy in (697, 707, 717)))
# --- луг у Стройки: природа, по которой можно ехать
MW = ['<g id="R51_meadow">']
POND = (0.0, 0.0, 0.1, 0.1)
TRACK_M, TRACK_R = [(0, 0), (0.1, 0)], [(0, 0), (0.1, 0)]
GROVES = [((622, 545), 9, 12, 'oak'), ((652, 560), 6, 8, 'birch'), ((520, 585), 7, 10, 'birch'), ((618, 625), 8, 11, 'oak'),
          ((655, 640), 6, 7, 'pine'), ((505, 628), 6, 8, 'pine'), ((585, 572), 4, 5, 'birch'),
          ((545, 576), 7, 9, 'oak'), ((560, 532), 8, 11, 'birch'), ((518, 528), 6, 8, 'oak'), ((598, 526), 7, 9, 'pine')]
for (gx, gy), sp, n, kind in GROVES:
    for _ in range(n):
        q = (gx + rnd.gauss(0, sp * 0.6), gy + rnd.gauss(0, sp * 0.45))
        if any(pl_d(q, tr) < 6 for tr in (TRACK_M, TRACK_R)) or ((q[0] - POND[0]) / (POND[2] * 1.5)) ** 2 + ((q[1] - POND[1]) / (POND[3] * 1.6)) ** 2 < 1:
            continue
        col_ = {'oak': ('#7FA36A', '#86A971', '#93B47B'), 'birch': ('#B5CF8E', '#C2D89C', '#A9C784'), 'pine': ('#5E8A5A', '#4F7D50', '#6A9663')}[kind]
        MW.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>' % (
            f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(8, 12.5)), rnd.choice(col_)))
GROVES2 = [((568, 598), 8, 11, 'oak'), ((540, 610), 6, 7, 'birch'), ((636, 600), 7, 9, 'oak'), ((600, 585), 5, 6, 'pine'),
           ((1060, 735), 10, 14, 'pine'), ((1100, 748), 9, 12, 'oak'), ((1140, 732), 8, 10, 'pine'), ((1080, 712), 6, 7, 'birch'),
           ((1035, 752), 7, 9, 'oak'), ((1160, 754), 6, 7, 'birch')]          # + луг у Стройки и рощи между Неблагополучным и Портом
for (gx, gy), sp, n, kind in GROVES2:
    for _ in range(n):
        q = (gx + rnd.gauss(0, sp * 0.6), gy + rnd.gauss(0, sp * 0.45))
        if any(pl_d(q, r_) < 9 for r_ in KEEP_CLEAR):
            continue
        col_ = {'oak': ('#7FA36A', '#86A971', '#93B47B'), 'birch': ('#B5CF8E', '#C2D89C', '#A9C784'), 'pine': ('#5E8A5A', '#4F7D50', '#6A9663')}[kind]
        MW.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>' % (
            f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(8, 12.5)), rnd.choice(col_)))
# --- роща отрыва между Стройкой и Неблагополучным (v55): проезжаемый лес, грунтовки, поляны; к северу гуще и темнее
# --- открытый неровный луг между Стройкой и Неблагополучным (v57): бугры, редкие рощи; у забора Неблагополучного полоса деревьев
_hillB = [c for nm, c, hw, h in MOUNTS if nm == 'B'][0]
for (kx, ky), (rx, ry) in (((560, 520), (22, 14)), ((640, 545), (28, 16)), ((600, 590), (18, 12)), ((720, 520), (20, 13)),
                           ((535, 470), (14, 10)), ((700, 450), (24, 14)), ((660, 600), (16, 10))):
    for dx_, dy_, col_, op_ in ((1.2, -1.2, '#B5C69C', 0.45), (0, 0, '#DCE8C6', 0.75)):   # тень и светлая макушка бугра
        c_ = to_u(kx + dx_ * rx * 0.25, ky + dy_ * ry * 0.25)
        MW.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s" fill-opacity="%s"/>' % (f1(c_[0]), f1(c_[1]), f1(rx * 5), f1(ry * 5), col_, op_))
_gc = to_u(680, 650)
MW.append('<defs><radialGradient id="grove_dry"><stop offset="0" stop-color="#B3AC7C" stop-opacity="0.45"/><stop offset="0.6" stop-color="#B3AC7C" stop-opacity="0.2"/>'
          '<stop offset="1" stop-color="#B3AC7C" stop-opacity="0"/></radialGradient></defs>'
          '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="url(#grove_dry)"/>' % (f1(_gc[0]), f1(_gc[1]), f1(130 * 5), f1(40 * 5)))
CLUMPS = [((520, 540), 6), ((585, 548), 7), ((690, 560), 6), ((625, 500), 5), ((745, 470), 6), ((548, 600), 5), ((708, 410), 5), ((760, 540), 4)]


def _tree(q, pal):
    MW.append('<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#5F8452" stroke-width="1"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(9, 13)), rnd.choice(pal)))


def _free(q):
    return not (pl_d(q, _hillB) < 46 or pl_d(q, TUN) < 14 or in_constr(q) or any(pl_d(q, r_) < 9 for r_ in KEEP_CLEAR) or (q[0] > 772 and q[1] < 506)
                or (q[1] < 470 and 528 < q[0] < 690))


for (gx, gy), n in CLUMPS:                                        # редкие рощицы
    for _ in range(n * 2):
        q = (gx + rnd.gauss(0, 6), gy + rnd.gauss(0, 4.5))
        if _free(q) and rnd.random() < 0.6:
            _tree(q, ('#7FA36A', '#86A971', '#93B47B'))
for (gx, gy), (sx_, sy_), n in (((668, 545), (22, 17), 46), ((652, 628), (9, 6), 12), ((688, 632), (7, 5), 8)):   # v58: середина луга и въезд в Неблагополучный
    for _ in range(n):
        q = (gx + rnd.gauss(0, sx_), gy + rnd.gauss(0, sy_))
        if _free(q):
            _tree(q, ('#7FA36A', '#86A971', '#93B47B', '#6F9660'))
for _ in range(70):                                               # одиночные деревья
    q = (rnd.uniform(500, 780), rnd.uniform(380, 610))
    if _free(q):
        _tree(q, ('#86A971', '#93B47B', '#9DBB83'))
for _ in range(1400):                                             # полоса деревьев у забора Неблагополучного (граница света)
    q = (rnd.uniform(560, 780), rnd.uniform(622, 648))
    if 636 < q[0] < 664:
        continue                                                   # v58: разрыв на полосе сдвига Неблагополучного (без ступеньки)
    if _free(q) and rnd.random() < 0.55:
        _tree(q, ('#5E8A5A', '#4F7D50', '#6A8458'))
BYP = chaikin(BYP_PTS, 3)
MW_ROADS = ''.join('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="round"/>' % (ptxt(BYP), c_, w_)
                   for c_, w_ in (('#D3D2C3', 46), ('#5F666C', 32)))
MW.append('</g>')
s = s.replace('<g id="L06a_canal"', ''.join(MW) + '<g id="L06a_canal"', 1)
s = s.replace('<g id="L08_vegetation"', '<g id="R52_bypass">' + MW_ROADS + '</g><g id="L08_vegetation"', 1)
# --- v57: Горный хребет продлён вдоль северного берега до северо-западного угла Неблагополучного; бухточка, пирс, погранпост
MTN = ['<g id="R57_mountain_ext">']
_pal = ('#EDEDE4', '#E4E5DA', '#DADBCF', '#D0D2C5', '#C6C8BA', '#BCBFB0', '#B3B6A7')
for gy_ in range(766, 920, 9):
    for gx_ in range(506, 652, 9):
        p0 = (gx_ + rnd.uniform(-3, 3), gy_ + rnd.uniform(-3, 3))
        q1, q2 = (p0[0] + 9 + rnd.uniform(-2, 2), p0[1] + rnd.uniform(-2, 2)), (p0[0] + rnd.uniform(-2, 2), p0[1] + 9 + rnd.uniform(-2, 2))
        q3 = (p0[0] + 9 + rnd.uniform(-2, 2), p0[1] + 9 + rnd.uniform(-2, 2))
        for tri in ((p0, q1, q2), (q1, q3, q2)):
            cx_, cy_ = sum(t[0] for t in tri) / 3, sum(t[1] for t in tri) / 3
            if not inside((cx_, cy_), MT_E):
                continue
            hi = min(1.0, max(0.0, (cy_ - 780) / 110.0))         # к берегу выше и светлее, у подножия темнее
            col_ = _pal[min(6, max(0, int(rnd.uniform(0, 3) + (1 - hi) * 4)))]
            MTN.append('<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.8" stroke-linejoin="round"/>' % (ptxt(list(tri)), col_, col_))
_bay = chaikin([(630, coast_y(630) + 3), (640, 906), (650, 899), (662, 896), (674, 899), (684, 906), (692, coast_y(692) + 3)], 3)
MTN.append('<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(630, 1000)] + _bay + [(692, 1000)]))
for q in _bay[::4]:
    MTN.append(rock((q[0], q[1] - 1.5), rnd.uniform(2.5, 4.5)))
PIER_B = [(658, 897), (666, 897), (666, 924), (658, 924)]       # каменный пирс 8 x 27 м
MTN.append('<polygon points="%s" fill="#A9A79C" stroke="#7E7C72" stroke-width="3"/>' % ptxt(PIER_B))
for sx_ in (658.6, 665.4):                                       # забор по краям пирса
    MTN.append('<polyline points="%s" fill="none" stroke="#4E555A" stroke-width="3" stroke-dasharray="10 6"/>' % ptxt([(sx_, 899), (sx_, 923)]))
MTN.append('<polygon points="%s" fill="#6F7F5B" stroke="#3F4A36" stroke-width="2"/>' % ptxt([(667, 893), (673, 893), (673, 899), (667, 899)]))   # будка погранпоста
for k_ in range(4):                                              # шлагбаум в полоску
    MTN.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="5"/>' % (ptxt([(658 + k_ * 2, 899.5), (660 + k_ * 2, 899.5)]), ('#D23C2E', '#FFFFFF')[k_ % 2]))
_bl = to_u(675, 906)
MTN.append('<text x="%s" y="%s" font-size="22" font-weight="bold" fill="#34424B">Border post</text>' % (f1(_bl[0]), f1(_bl[1])))
MTN.append('</g>')
s = s.replace('<g id="L08_vegetation"', ''.join(MTN) + '<g id="L08_vegetation"', 1)
ROADS = ['<g id="R24_roads">']
pass                                                               # моста в улицу Хутора больше нет: въезд по объездной
for col, w in (('#D3D2C3', 46), ('#5F666C', 32)):                 # сначала все обочины, потом всё полотно — стыки без колец
    for rd in NEWROADS:
        ROADS.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="round"/>' % (ptxt(rd), col, w))
for rd in (ROAD_H, ROAD_C):                               # осевая разметка
    ROADS.append('<polyline points="%s" fill="none" stroke="#F4F1E6" stroke-width="2.5" stroke-dasharray="18 22"/>' % ptxt(rd))
LABELS = ['<g id="R24_labels">', '<text x="%s" y="%s" font-size="26" font-weight="bold" fill="#34424B">TUNNEL</text>' % (
    f1(to_u(800, 600)[0]), f1(to_u(800, 600)[1]))]
for nm, v in VIEWS.items():
    X, Y = to_u(*v)
    LABELS.append('<circle cx="%s" cy="%s" r="20" fill="#FFFFFF" stroke="#34424B" stroke-width="4"/><circle cx="%s" cy="%s" r="7" fill="#34424B"/>'
                 '<text x="%s" y="%s" font-size="26" font-weight="bold" fill="#34424B">VIEW %s</text>' % (f1(X), f1(Y), f1(X), f1(Y), f1(X + 28), f1(Y - 22), nm))
ROADS.append('</g>')
LABELS += [h for h in HILLS if h.startswith('<text')]
HILLS = [h for h in HILLS if not h.startswith('<text')]
LABELS.append('</g>')

SEA_W = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(-80, 455), (40, 462), (60, 500), (72, 560), (74, 700), (72, 990), (-80, 990)])   # запад: блок сдвинут на 70 м
s = s.replace('<g id="L02_mountains"', SEA_N + SEA_W + '<g id="L02_mountains"', 1)
coast_w = [(x, 872 + 6 * math.sin(x / 37.0) + 4 * math.sin(x / 11.0 + 0.7)) for x in range(-80, 561, 6)]
SEA_NW = '<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(-80, 1000)] + coast_w + [(560, 1000)])
ROCKS_NW = ''.join(rock((x, y - 3), rnd.uniform(4, 8)) for x, y in coast_w[::2])
s = s.replace('<g id="L03_relief_coast"', SEA_NW + ROCKS_NW + '<g id="L03_relief_coast"', 1)
# расщелины: тёмная трещина со скалами по краям
RAV = ['<g id="R33_ravines">']
for rv in RAVINES:
    rc = chaikin(rv, 3)
    RAV.append('<polyline points="%s" fill="none" stroke="#9AA58C" stroke-width="44" stroke-linecap="round" stroke-linejoin="round" opacity="0.7"/>' % ptxt(rc))
    RAV.append('<polyline points="%s" fill="none" stroke="#6B735F" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>' % ptxt(rc))
    for i_ in range(1, len(rc) - 1, 3):
        a_, b_ = rc[i_ - 1], rc[i_ + 1]
        dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]
        L_ = math.hypot(dx_, dy_) or 1
        for sd in (-1, 1):
            RAV.append(rock((rc[i_][0] + sd * dy_ / L_ * 6, rc[i_][1] - sd * dx_ / L_ * 6), rnd.uniform(2.5, 4.5)))
RAV.append('</g>')
# предгорья и рощи там, где был пустой луг: запад (между рекой и горой H) и восток (под перевалом)
FILL_ZONES = []
for zone in FILL_ZONES:
    xs_ = [p[0] for p in zone]; ys_ = [p[1] for p in zone]
    for _ in range(520):
        p = (rnd.uniform(min(xs_), max(xs_)), rnd.uniform(min(ys_), max(ys_)))
        if not inside(p, zone) or Fbm2(p) < 0.52:
            continue
        if any(pl_d(p, r_) < 10 for r_ in KEEP_CLEAR) or any(pl_d(p, rv) < 9 for rv in RAVINES) or in_constr(p):
            continue
        if any(math.hypot(p[0] - v[0], p[1] - v[1]) < 34 for v in VIEWS.values()):
            continue
        TREES.insert(-1, '<circle cx="%s" cy="%s" r="%s" fill="%s" stroke="#6F915E" stroke-width="1"/>'
                     % (f1(to_u(*p)[0]), f1(to_u(*p)[1]), f1(rnd.uniform(9, 14)), rnd.choice(('#7FA36A', '#86A971', '#93B47B', '#8AAE74', '#9DBB83'))))
    for _ in range(6):
        q = (rnd.uniform(min(xs_), max(xs_)), rnd.uniform(min(ys_), max(ys_)))
        if inside(q, zone) and not any(pl_d(q, r_) < 14 for r_ in KEEP_CLEAR):
            ROCKS.insert(-1, rock(q, rnd.uniform(4, 8)))
# тоннель: пунктирные стенки и порталы
TUNNEL_SVG = ['<g id="R33_tunnel">']
tc = TUN
for sd in (-1, 1):
    off = []
    for i_, p in enumerate(tc):
        a_, b_ = tc[max(0, i_ - 1)], tc[min(len(tc) - 1, i_ + 1)]
        dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]
        L_ = math.hypot(dx_, dy_) or 1
        off.append((p[0] + sd * dy_ / L_ * 4.8, p[1] - sd * dx_ / L_ * 4.8))
    TUNNEL_SVG.append('<polyline points="%s" fill="none" stroke="#5F666C" stroke-width="4" stroke-dasharray="14 10"/>' % ptxt(off))
TUNNEL_SVG.append('<polyline points="%s" fill="none" stroke="#5F666C" stroke-width="32" stroke-opacity="0.18"/>' % ptxt(tc))
for (px_, py_), (qx_, qy_) in ((tc[0], tc[1]), (tc[-1], tc[-2])):
    dx_, dy_ = qx_ - px_, qy_ - py_
    L_ = math.hypot(dx_, dy_)
    nx_, ny_ = -dy_ / L_, dx_ / L_
    a_ = (px_ + nx_ * 6.5, py_ + ny_ * 6.5); b_ = (px_ - nx_ * 6.5, py_ - ny_ * 6.5)
    TUNNEL_SVG.append('<polyline points="%s" fill="none" stroke="#7A7F82" stroke-width="12" stroke-linecap="square"/>' % ptxt([a_, b_]))
TUNNEL_SVG.append('</g>')
s = s.replace('<g id="L04_water"', ''.join(HILLS) + CHILL + COVE_SVG + ''.join(ROCKS) + ''.join(RAV) + '<g id="L04_water"', 1)
s = s.replace('<g id="L06a_canal"', FENCE + PIER_SVG + '<g id="L06a_canal"', 1)

# --- природные перемычки у Хутора: зелёная полоса поверх реки, тёмные устья и скалы на входе и выходе
NAT = ['<g id="R34_land_bridges">']
for (bx, by) in ((484, 349), (488, 572)):
    NAT.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#D7E3C2" stroke="#B7C9A1" stroke-width="3"/>' % (
        f1(to_u(bx, by)[0]), f1(to_u(bx, by)[1]), f1(14 * 5), f1(15 * 5)))
    for sd in (-1, 1):
        mx_, my_ = bx, by + sd * 13
        NAT.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#4E5A55"/>' % (f1(to_u(mx_, my_)[0]), f1(to_u(mx_, my_)[1]), f1(4.5 * 5), f1(2.2 * 5)))
        for k_ in range(4):
            NAT.append(rock((mx_ + rnd.uniform(-8, 8), my_ + sd * rnd.uniform(1, 4)), rnd.uniform(2.5, 4.5)))
NAT.append('</g>')
s = s.replace('<g id="R52_bypass"', ''.join(NAT) + '<g id="R52_bypass"', 1)   # поверх реки (ручей из горного озера рисуется выше L05)

# --- пляж уже: море ближе (линия воды ~y 142), мокрый песок, пена; новый пирс от воды
coast_b = [(642, 62), (650, 76), (654, 90), (664, 116), (684, 146), (712, 168), (750, 182), (800, 186), (860, 178), (900, 170), (960, 163), (1020, 157), (1060, 161), (1100, 169), (1140, 178), (1190, 186), (1225, 191), (1250, 193), (1268, 201), (1283, 214), (1297, 229), (1313, 243), (1336, 254), (1362, 260), (1400, 266), (1440, 271), (1475, 276)]
cb = chaikin(coast_b, 3)
SEA_B = ('<polygon points="%s" fill="#ABD3E1"/>' % ptxt([(600, -60)] + cb + [(1480, 258), (1510, 250), (1510, -60)]) +
         '<polyline points="%s" fill="none" stroke="#C3E3EC" stroke-width="60" stroke-opacity="0.8"/>' % ptxt([(x, y - 7) for x, y in cb]) +
         '<polyline points="%s" fill="none" stroke="#E7DFC4" stroke-width="22"/>' % ptxt([(x, y + 2) for x, y in cb]) +
         '<polyline points="%s" fill="none" stroke="#FFFFFF" stroke-width="5" stroke-opacity="0.7"/>' % ptxt(cb))
# --- пляж Майами (под морем: линия воды обрежет песок)
PARK_TOP, PARK_BOT, DUNE_BOT = 246.3, 229.0, 221.0
LOTS = [(902.0, 936.0), (1149.0, 1183.0)]                         # парковки у въездов бусика (x0, x1), y 231..247
X0B, X1B = 786.0, 1240.0
STREETS = (895.0, 1012.0, 1142.0)                                  # улицы города, упирающиеся в пляж
VAN_IN = (895.0, 1142.0)                                           # въезды бусика на песок
BEACH = ['<g id="R45_miami_beach">']
BEACH.append('<polygon points="%s" fill="#F7F2E0"/>' % ptxt([(X0B - 12, PARK_TOP + 2), (1262, PARK_TOP + 2), (1282, 252), (1300, 259), (1322, 264), (1350, 268),
                                                              (1400, 272), (1440, 276), (1440, 120), (X0B - 40, 120)]))   # песок: дугой до Элитного холма
BEACH.append('<polygon points="%s" fill="#BFD69E"/>' % ptxt([(X0B, PARK_TOP), (X1B, PARK_TOP), (X1B, PARK_BOT), (X0B, PARK_BOT)]))           # парк
BEACH.append('<polygon points="%s" fill="#A9C38A"/>' % ptxt([(X0B, PARK_BOT), (X1B, PARK_BOT)] +
             [(x_, DUNE_BOT + 1.5 * math.sin(x_ / 9.0)) for x_ in range(int(X1B), int(X0B) - 1, -6)]))                                   # дюны
path = chaikin([(X0B + 4, 240)] + [(x_, 240 + 6 * math.sin((x_ - X0B) / 31.0)) for x_ in range(int(X0B) + 20, int(X1B) - 10, 20)] + [(X1B - 4, 240)], 2)
BEACH.append('<polyline points="%s" fill="none" stroke="#EFE6CF" stroke-width="18" stroke-linejoin="round"/>' % ptxt(path))         # дорожка парка
def palm(q, R):
    a0 = rnd.uniform(0, 6.28)
    pts = []
    for k_ in range(12):
        ang = a0 + k_ * math.pi / 6
        rr = R if k_ % 2 == 0 else R * 0.38
        pts.append((q[0] + rr * math.cos(ang), q[1] + rr * math.sin(ang)))
    return ('<polygon points="%s" fill="%s" stroke="#3F6E3E" stroke-width="1.2" stroke-linejoin="round"/>' % (ptxt(pts), rnd.choice(('#5E9A5E', '#6FA86C', '#4F8A50'))) +
            '<circle cx="%s" cy="%s" r="4" fill="#8A7A55"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1])))


for row, y_ in enumerate((249.0, 243.0, 236.0, 231.5)):                                                                          # пальмы парка (густо)
    for x_ in range(int(X0B) + 5 + (row % 2) * 4, int(X1B) - 3, 8):
        if any(abs(x_ - sx) < 9 for sx in STREETS) or abs(y_ - 240 - 6 * math.sin((x_ - X0B) / 31.0)) < 3.5 or any(l0 - 3 < x_ < l1 + 3 for l0, l1 in LOTS):
            continue
        BEACH.append(palm((x_ + rnd.uniform(-1.5, 1.5), y_ + rnd.uniform(-1.5, 1.5)), rnd.uniform(3.6, 4.8)))
for q in ((947, 214), (963, 214), (1060, 214), (1076, 214), (800, 205), (1235, 204)):                                            # пальмы у баров
    BEACH.append(palm(q, 4.2))
for _ in range(220):                                                                                                                 # кусты на дюнах
    q = (rnd.uniform(X0B, X1B), rnd.uniform(DUNE_BOT + 0.5, PARK_BOT - 0.5))
    if any(abs(q[0] - sx) < 7 for sx in STREETS):
        continue
    BEACH.append('<circle cx="%s" cy="%s" r="%s" fill="#8DAE6B"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(3, 5))))
for sx in STREETS:                                                                                                                   # проходы к воде
    if sx in VAN_IN:
        for col, w in (('#E3D7B4', 46), ('#EADFC2', 38)):                                                                            # въезд бусика на песок
            BEACH.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linecap="butt"/>' % (ptxt([(sx, PARK_TOP + 2), (sx, DUNE_BOT - 6)]), col, w))
    else:
        BEACH.append('<polygon points="%s" fill="#EDE4CD"/>' % ptxt([(sx - 14, PARK_TOP), (sx + 14, PARK_TOP), (sx + 14, PARK_BOT), (sx - 14, PARK_BOT)]))   # площадь у пирса
        BEACH.append('<polyline points="%s" fill="none" stroke="#B8A58A" stroke-width="30" stroke-linecap="butt"/>' % ptxt([(sx, PARK_BOT), (sx, DUNE_BOT - 4)]))
for x_ in range(int(X0B) + 30, int(X1B) - 20, 55):                                                                                   # деревянные дорожки через дюны
    if any(abs(x_ - sx) < 20 for sx in STREETS):
        continue
    BEACH.append('<polyline points="%s" fill="none" stroke="#C9B48E" stroke-width="12" stroke-linecap="butt"/>' % ptxt([(x_, PARK_BOT + 1), (x_, DUNE_BOT - 3)]))
for l0, l1 in LOTS:                                                                                                                  # парковки
    BEACH.append('<polygon points="%s" fill="#C9CBC4" stroke="#9EA29C" stroke-width="2"/>' % ptxt([(l0, 247.5), (l1, 247.5), (l1, 231), (l0, 231)]))
    for row_y in (243.5, 235.0):
        for k_ in range(int((l1 - l0) / 3.0)):
            x_ = l0 + 1.5 + k_ * 3.0
            BEACH.append('<polyline points="%s" fill="none" stroke="#FFFFFF" stroke-width="1.5"/>' % ptxt([(x_, row_y - 3), (x_, row_y + 3)]))
            if rnd.random() < 0.65:
                BEACH.append('<rect x="%s" y="%s" width="%s" height="%s" rx="2" fill="%s"/>' % (
                    f1(to_u(x_ + 0.3, 0)[0]), f1(to_u(0, row_y + 2.3)[1]), f1(2.4 * 5), f1(4.6 * 5), rnd.choice(('#C0504D', '#4F7FB5', '#E2B13B', '#5E8F6A', '#EEEEEE', '#3A4247'))))
TOWERS = [(830, 200, '#F2B2C8'), (905, 191, '#F4D35E'), (968, 184, '#7FC8D8'), (1062, 184, '#F29B6B'), (1150, 196, '#9BD08A'), (1218, 203, '#C9A2E0')]
for x_, y_, col in TOWERS:                                                                                                           # вышки спасателей
    BEACH.append('<polygon points="%s" fill="%s" stroke="#5E5A50" stroke-width="2"/>' % (ptxt([(x_ - 3, y_ - 3), (x_ + 3, y_ - 3), (x_ + 3, y_ + 3), (x_ - 3, y_ + 3)]), col))
    BEACH.append('<polyline points="%s" fill="none" stroke="#5E5A50" stroke-width="3"/>' % ptxt([(x_, y_ - 3), (x_, y_ - 7)]))
UMB = ('#4F8FD8', '#F2C14E', '#E86F5C', '#FFFFFF', '#6CC3A0')
for bx, by, nx, ny in ((808, 213, 6, 2), (925, 213, 7, 2), (1040, 213, 8, 2), (1170, 213, 6, 2)):                                     # зонтики рядами + лежаки
    col = rnd.choice(UMB)
    for i_ in range(nx):
        for j_ in range(ny):
            q = (bx + i_ * 6.5, by - j_ * 6.5)
            BEACH.append('<rect x="%s" y="%s" width="%s" height="%s" fill="#FFFFFF" stroke="#C8C1AE" stroke-width="1"/>' % (
                f1(to_u(*q)[0] - 6), f1(to_u(*q)[1] + 4), f1(12), f1(6)))
            BEACH.append('<circle cx="%s" cy="%s" r="9" fill="%s" stroke="#7A7363" stroke-width="1"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1]), col))
for _ in range(60):                                                                                                                  # одиночные полотенца/зонтики
    q = (rnd.uniform(X0B, X1B), rnd.uniform(184, 205))
    if abs(q[0] - 1012) < 10:
        continue
    BEACH.append('<circle cx="%s" cy="%s" r="5" fill="%s"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1]), rnd.choice(UMB)))
for cx_ in (1100.0, 1124.0):                                                                                                         # волейбол
    BEACH.append('<polygon points="%s" fill="none" stroke="#D9A441" stroke-width="2.5"/>' % ptxt([(cx_ - 8, 186), (cx_ + 8, 186), (cx_ + 8, 194), (cx_ - 8, 194)]))
    BEACH.append('<polyline points="%s" fill="none" stroke="#5E5A50" stroke-width="2"/>' % ptxt([(cx_, 185), (cx_, 195)]))
for bx in (955.0, 1068.0):                                                                                                           # бары у дюн
    BEACH.append('<polygon points="%s" fill="#F2E3C6" stroke="#8E7B5A" stroke-width="2"/>' % ptxt([(bx - 8, DUNE_BOT - 1), (bx + 8, DUNE_BOT - 1), (bx + 8, DUNE_BOT - 9), (bx - 8, DUNE_BOT - 9)]))
    BEACH.append('<polygon points="%s" fill="#7FC8D8"/>' % ptxt([(bx - 8, DUNE_BOT - 1), (bx + 8, DUNE_BOT - 1), (bx + 8, DUNE_BOT - 3), (bx - 8, DUNE_BOT - 3)]))
# переход к берегу Элитного холма: пальмы и зелень дюн продолжаются по дуге и редеют
ARC = [(1240, 196), (1252, 198), (1266, 205), (1280, 216), (1293, 229), (1308, 242), (1330, 253), (1356, 260), (1390, 266)]
for i_, (ax_, ay_) in enumerate(ARC[:-1]):
    bx_, by_ = ARC[i_ + 1]
    dx_, dy_ = bx_ - ax_, by_ - ay_
    L_ = math.hypot(dx_, dy_) or 1
    nx_, ny_ = -dy_ / L_, dx_ / L_
    t_ = i_ / (len(ARC) - 1)
    BEACH.append('<polygon points="%s" fill="#A9C38A" fill-opacity="%.2f"/>' % (ptxt([
        (ax_ + nx_ * 18, ay_ + ny_ * 18), (bx_ + nx_ * 18, by_ + ny_ * 18), (bx_ + nx_ * (26 - 6 * t_), by_ + ny_ * (26 - 6 * t_)),
        (ax_ + nx_ * (26 - 6 * t_), ay_ + ny_ * (26 - 6 * t_))]), 0.9 - 0.6 * t_))
    for _ in range(int(7 - 5 * t_)):
        u_ = rnd.random()
        off = rnd.uniform(16, 32)
        BEACH.append(palm((ax_ + dx_ * u_ + nx_ * off, ay_ + dy_ * u_ + ny_ * off), rnd.uniform(3.4, 4.6)))
BEACH.append('</g>')
# третий мост через канал: по улице x 948 от южной улицы Даунтауна к набережной
BR3 = [(948, 257), (948, 201)]
pass                                                               # мостов к пляжу нет (канала нет)
s = s.replace('<g id="R18_plans"', '<g id="R34_beach_sea">' + ''.join(BEACH) + SEA_B + '</g>' + '<g id="R18_plans"', 1)
_r18a = s.index('<g id="R18_plans"')
_r18b = s.index('</g>', s.index('<image', _r18a)) if False else None
# пляжный план (картинка в R18_plans) лежит выше моря — поднимаем море над ним: переносим группу моря сразу после R18_plans
_g = s[s.index('<g id="R34_beach_sea">'):s.index('<g id="R18_plans"')]
s = s.replace(_g, '', 1)
_p0 = s.index('<g id="R18_plans"')
_depth, _i = 0, _p0
for _m in re.finditer(r'<(/?)g\b[^>]*?(/?)>', s[_p0:]):
    if _m.group(2):
        continue
    _depth += -1 if _m.group(1) else 1
    if _depth == 0:
        _i = _p0 + _m.end()
        break
s = s[:_i] + _g + s[_i:]

# --- серые острые скалы справа от Тихой долины (не проехать)
RIV = chaikin([warp_m(556, 284), (636, 282), (646, 266), (650, 230), (652, 190), (654, 150), (656, 116), (657, 96)], 3)
SAND_IN = [(632, 84), (634, 104), (645, 138), (668, 170), (700, 196), (745, 212), (800, 216), (850, 214), (900, 206)]   # внутренний край песка дуги
ROCKZ = [(616, 88), (632, 84), (634, 104), (645, 138), (668, 170), (688, 190), (698, 214), (692, 246), (674, 276), (652, 292), (638, 268),
         (630, 205), (628, 140), (620, 90)]
SH = ['<g id="R34_sharp_rocks">']
SH.append('<polygon points="%s" fill="#F7F2E0"/>' % ptxt([(p_[0] + 2, p_[1] - 2) for p_ in coast_b[:9]] + SAND_IN[::-1]))   # песок дуги
SH.append('<polygon points="%s" fill="#B9BCB4" stroke="#8E938A" stroke-width="3"/>' % ptxt(ROCKZ))                                 # скальный массив
for _ in range(900):
    p = (rnd.uniform(612, 700), rnd.uniform(84, 296))
    if not inside(p, ROCKZ) or pl_d(p, RIV) < 10:
        continue
    w_, h_ = rnd.uniform(9, 20), rnd.uniform(14, 32)
    tip = (p[0] + rnd.uniform(-3, 3), p[1] + h_ * 0.55)
    pts = [(p[0] - w_ / 2, p[1] - h_ * 0.35), tip, (p[0] + w_ / 2, p[1] - h_ * 0.3), (p[0] + w_ * 0.1, p[1] - h_ * 0.45)]
    SH.append('<polygon points="%s" fill="%s" stroke="#7E827B" stroke-width="2" stroke-linejoin="round"/>' % (ptxt(pts), rnd.choice(('#C9CBC4', '#B9BCB4', '#A9ADA5', '#D5D6CF'))))
    SH.append('<polyline points="%s" fill="none" stroke="#EEEFEA" stroke-width="2" stroke-opacity="0.8"/>' % ptxt([pts[0], tip]))
SH.append('</g>')
s = s.replace('<g id="L06a_canal"', ''.join(SH) + '<g id="L06a_canal"', 1)

TRAIL_D = [(800, 230), (801, 230)]
DUNES = []
DN = ['<g id="R35_dunes">']
for (cx_, cy_), rx_, ry_ in DUNES:
    for f_, col_ in ((1.0, '#F4EEDA'), (0.62, '#F7F2E0')):
        pts = [(cx_ + rx_ * f_ * (1 + 0.08 * math.sin(3 * a_)) * math.cos(a_), cy_ + ry_ * f_ * (1 + 0.08 * math.cos(2 * a_)) * math.sin(a_))
               for a_ in [k_ * 2 * math.pi / 40 for k_ in range(40)]]
        DN.append('<polygon points="%s" fill="%s" stroke="#E2D6B4" stroke-width="2"/>' % (ptxt(pts), col_))
    for _ in range(9):                                              # кусты и трава на дюнах
        q = (cx_ + rnd.uniform(-rx_, rx_) * 0.8, cy_ + rnd.uniform(-ry_, ry_) * 0.8)
        if pl_d(q, TRAIL_D) > 6:
            DN.append('<circle cx="%s" cy="%s" r="%s" fill="#9DBB83" stroke="#86A274" stroke-width="1"/>' % (
                f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(4, 7))))
for col_, w_ in (('#BEB18F', 31), ('#E5D2A4', 27)):
    DN.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="round"/>' % (ptxt(TRAIL_D), col_, w_))
DN.append('</g>')
s = s.replace('<g id="L06a_canal"', ''.join(DN) + '<g id="L06a_canal"', 1)
s = s.replace('<g id="L11_labels"', ''.join(TUNNEL_SVG) + '<g id="L11_labels"', 1)

pass                                                               # река задана выше (через ущелье в скалах)
RV = ['<g id="R38_river_mouth">']
RV.append('<polyline points="%s" fill="none" stroke="#C3DCCB" stroke-width="70" stroke-linecap="round" stroke-linejoin="round"/>' % ptxt(RIV))
RV.append('<polyline points="%s" fill="none" stroke="#97C8DC" stroke-width="50" stroke-linecap="round" stroke-linejoin="round"/>' % ptxt(RIV))
for i_ in range(0, len(RIV) - 4, 4):                              # стены ущелья
    a_, b_ = RIV[i_], RIV[i_ + 1]
    dx_, dy_ = b_[0] - a_[0], b_[1] - a_[1]
    L_ = math.hypot(dx_, dy_) or 1
    for sd in (-1, 1):
        RV.append(rock((a_[0] + sd * dy_ / L_ * 9, a_[1] - sd * dx_ / L_ * 9), rnd.uniform(3.5, 6)))
for k_ in range(5):                                                # водопад у моря
    y_ = 112 - k_ * 2.4
    RV.append('<polyline points="%s" fill="none" stroke="#F4FAFC" stroke-width="3" stroke-opacity="0.9"/>' % ptxt([(650, y_), (663, y_)]))
RV.append('<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="#FFFFFF" fill-opacity="0.7"/>' % (f1(to_u(657, 94)[0]), f1(to_u(657, 94)[1]), f1(8 * 5), f1(4 * 5)))
RV.append('</g>')
s = s.replace('<g id="L06a_canal"', ''.join(RV) + '<g id="L06a_canal"', 1)   # над скалами

FR = ['<g id="R46_downtown_frame">']
VERGE = [[(778.6, 352), (784.4, 352), (784.4, 474), (778.6, 474)],                         # запад: между старой улицей и рамкой
         [(778.6, 478.6), (862, 478.6), (862, 485.4), (778.6, 485.4)],                    # север-запад
         [(1013, 478.6), (1145, 478.6), (1145, 502), (1013, 502)],                       # север: выступ квартала убран, газон
         [(1147, 442.6), (1237.4, 442.6), (1237.4, 485.4), (1147, 485.4)],               # северо-восточный угол: сквер
         [(1230.6, 353), (1237.4, 353), (1237.4, 486), (1230.6, 486)]]                   # восток
for vg in []:
    FR.append('<polygon points="%s" fill="#DCE8C8"/>' % ptxt(vg))
for _ in range(0):
    q = (rnd.uniform(1150, 1234), rnd.uniform(446, 483))
    FR.append('<circle cx="%s" cy="%s" r="%s" fill="#93B47B" stroke="#86A274" stroke-width="1"/>' % (f1(to_u(*q)[0]), f1(to_u(*q)[1]), f1(rnd.uniform(5, 9))))
RECT = [(774, 254.5), (774.5, 254.5)]                                 # только нижняя прямая вдоль пляжа
for x0_, x1_ in ():                         # нижний ряд кварталов слит с соседними (старая улица y 270 убрана)
    FR.append('<polygon points="%s" fill="#E3E1D9"/>' % ptxt([(x0_, 266.2), (x1_, 266.2), (x1_, 278.6), (x0_, 278.6)]))
for x0_, x1_ in ():                          # улицы продлены до набережной
    FR.append('<polygon points="%s" fill="#5F666C"/>' % ptxt([(x0_, 257.6), (x1_, 257.6), (x1_, 279), (x0_, 279)]))
STUBS = []
for col, w in ():
    for pl in [RECT] + STUBS:
        FR.append('<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="miter" stroke-linecap="square"/>' % (ptxt(pl), col, w))
pass
FR.append('</g>')
s = s.replace('<g id="L11_labels"', ''.join(FR) + '<g id="L11_labels"', 1)
OD = ['<g id="R38_ocean_drive">']
OD.append('<polygon points="%s" fill="#B8A58A" stroke="#7E6F5C" stroke-width="3"/>' % ptxt([(1007, 221), (1017, 221), (1017, 128), (1007, 128)]))   # пирс по оси
OD.append('<polygon points="%s" fill="#B8A58A" stroke="#7E6F5C" stroke-width="3"/>' % ptxt([(997, 128), (1027, 128), (1027, 116), (997, 116)]))
OD.append('</g>')
s = s.replace('<g id="L11_labels"', ''.join(OD) + '<g id="L11_labels"', 1)
s = s.replace('<g id="L08_vegetation"', ''.join(ROADS) + '<g id="L08_vegetation"', 1)
s = s.replace('<g id="R18_plans"', ''.join(TREES) + '<g id="R18_plans"', 1)
_in_port = [p for p in ROAD_C if 590 <= p[1] < 624] + [(1263, 633.0)]                       # карниз внутри Порта — поверх плана Порта, до средней дороги
_in_port = [(ROAD_C[ROAD_C.index(_in_port[0]) - 1])] + _in_port
s = s.replace('<g id="L11_labels"', ''.join(LABELS[:-1]) + CHILL_LABEL + '</g>' + '<g id="R27_cornice_in_port">' + ''.join(
    '<polyline points="%s" fill="none" stroke="%s" stroke-width="%d" stroke-linejoin="round" stroke-linecap="butt"/>' % (ptxt(_in_port[:-1] + [(_in_port[-1][0], end_)]), c_, w_)
    for c_, w_, end_ in (('#D3D2C3', 46, 629.0), ('#5F666C', 32, 634.0))) + '</g><g id="L11_labels"', 1)
s = s.replace('World map v22 · 16.10.2026 ·', 'World map v58 · 17.10.2026 · Downtown and Rough further from hill B, open meadow with knolls, ridge to Rough NW + border post pier, Downtown lower/east, Rough higher, hill B 50 m, tunnel approaches, Downtown v27, Miami beach joined to Elite, groves, Hamlet bypass fixed, tunnel, serpentine VIEW B ·')
s = re.sub(r'<polyline id="hamlet_bypass_(?:edge|surface)_\d+"[^>]*>', '', s)   # старая объездная мастера (её заменяет BYP)
open(SVG_OUT, 'w', encoding='utf-8').write(s)
print('svg ok', len(s))

if os.environ.get('NORENDER') != '1':
    from post_shift_v58 import render_shifted
    W, H = int(7370 + GROW_X * 5), int(4200 + GROW_Y * 5)
    im = render_shifted(s, PNG_OUT, W, H)                         # v58: Даунтаун +20 вправо/-28 вниз, Неблагополучный +22 вверх, холст +25 м вверх
    im.save(PNG_OUT)
    W, H = im.size
    im.resize((W // 5, H // 5), Image.LANCZOS).save(PRE_OUT)
    print('ok', im.size)
