from pathlib import Path
import json,math,textwrap
from PIL import Image,ImageDraw,ImageFont
r=Path(r'C:\Dev\Game\ArtSource\Vehicles_W86');review=Path(r'C:\Dev\Game\Working\Reviews\W86Polish_2026-10-25');stats=json.loads((r/'selected_models_v01.json').read_text());cells=r/'tools/review_cells_v01';pre=r/'previews';pre.mkdir(exist_ok=True)
fontpath=r'C:\Windows\Fonts\arial.ttf';boldpath=r'C:\Windows\Fonts\arialbd.ttf'
def font(n,b=False):return ImageFont.truetype(boldpath if b else fontpath,n)
def text(d,xy,s,n=23,color='#E8EDF1',bold=False):d.text(xy,s,font=font(n,bold),fill=color)
meta={x['name']:x for x in json.loads((cells/'comparison_meta_v01.json').read_text())}
cur={'SEDAN':'car_sedan_blue · 1260 tris','COMPACT':'car_hatchback · 952 tris','DISPLAY_COUPE':'car_sedan_beige · 1260 tris · предложение Downtown','DISPLAY_GT':'car_sedan_green · 1260 tris · предложение Downtown','DUMP_TRUCK':'MW86_DumpTruck · 1380 tris · 03-dump-truck','CONTAINER_TRUCK':'MW86_TruckContainer · 3492 tris · 06-07-truck','ASTRA_STATIC_VAN':'Astra van v02 · 2514 tris · эталон исходного кузова'}
W=2700;RH=650;head=180;im=Image.new('RGB',(W,head+RH*len(stats)+150),'#202A33');d=ImageDraw.Draw(im)
text(d,(30,20),'[G47] W86 · автомобили окружения · лист превью v01',44,bold=True)
text(d,(30,82),'Этап 1: Blender. В Unity ничего не импортировано. В каждой строке — одинаковый масштаб камеры.',27)
for x,s in [(25,'ВЫБРАННЫЙ ВАРИАНТ'),(925,'ТЕКУЩАЯ МОДЕЛЬ / БАЗА СРАВНЕНИЯ'),(1825,'УТВЕРЖДЁННЫЙ ASTRA · МАСШТАБ / СТИЛЬ')]:text(d,(x,132),s,25,'#82B6C7',True)
for i,p in enumerate(stats):
 y=head+i*RH;name=p['name'];rev=p['revision'];source='Quaternius · CC0' if name in ['SEDAN','COMPACT','DISPLAY_COUPE','DISPLAY_GT'] else 'Only Volunteers + колёса Kenney · CC0 на колёса' if 'TRUCK' in name else 'Only Volunteers · утверждённый проектный ассет'
 text(d,(25,y+8),f'{name}  v{rev:02}  |  LOD0/1/2: '+ ' / '.join(map(str,p['lod_triangles'])),26,bold=True)
 text(d,(25,y+43),source,23)
 text(d,(925,y+8),cur[name],23,bold=True)
 text(d,(1825,y+8),'FRIDGE-ASTRA-001 v02 · проектный ассет',24,bold=True)
 new=next((cells/(name+s) for s in ['_new_approved_candidate.png','_new_final.png','_new.png'] if (cells/(name+s)).exists()))
 for col,f in enumerate([new,cells/(name+'_current.png'),cells/(name+'_astra.png')]):im.paste(Image.open(f).convert('RGB'),(col*900,y+80))
 dims=p['dimensions_m'];text(d,(25,y+611),f'Ш × Д × В: {dims[0]:.2f} × {dims[1]:.2f} × {dims[2]:.2f} м · {p["ucx_count"]} UCX',22)
 if name in ['DISPLAY_COUPE','DISPLAY_GT']:s='Смена обычной парковочной машины на витринную — только после согласования.'
 elif name=='ASTRA_STATIC_VAN':s='Статический вариант для мира; размещение предлагается отдельно. Исходный фургон игрока сохранён.'
 else:s='Сравнение геометрии в Blender; одинаковые камера, свет и масштаб в строке.'
 text(d,(925,y+611),s,19)
foot=head+RH*len(stats);text(d,(30,foot+20),'Единый материал и палитра. CC0 проверена по страницам авторов и лицензиям внутри архивов.',25)
text(d,(30,foot+65),'Ожидает решения Феди. Для импорта использовать только selected_models_v01.json; предыдущие ревизии сохранены.',25,'#E2C68E')
assert not (review/'vehicles_v01.png').exists();im.save(review/'vehicles_v01.png')
# Label the six-side geometry and LOD inspection without retaining a screenshot for each camera.
raw=Image.open(r/'tools/technical_views_raw_v02.png').convert('RGB');out=Image.new('RGB',(raw.width+270,raw.height+100),'#202A33');out.paste(raw,(270,100));dd=ImageDraw.Draw(out)
allnames=['SEDAN','COMPACT','DISPLAY_COUPE','DISPLAY_GT','PANEL_VAN (отклонён)','DUMP_TRUCK','CONTAINER_TRUCK','ASTRA_STATIC_VAN']
for i,n in enumerate(['ФРОНТ','СЗАДИ','СБОКУ +X','СБОКУ -X','СВЕРХУ','СНИЗУ','LOD1','LOD2']):text(dd,(280+i*360,25),n,21)
for i,n in enumerate(allnames):text(dd,(10,110+i*240),n,20)
out.save(pre/'technical_views_v01.png')
