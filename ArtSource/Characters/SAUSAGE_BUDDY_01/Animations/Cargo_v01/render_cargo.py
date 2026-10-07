"""Render the saved deliverables; no animation is regenerated or source saved."""
from pathlib import Path
import sys,argparse,importlib.util
sys.dont_write_bytecode=True
import bpy
HERE=Path(__file__).resolve().parent
argv=sys.argv[:];sys.argv=[argv[0]]
spec=importlib.util.spec_from_file_location('cargo',HERE/'build_cargo_v07.py')
C=importlib.util.module_from_spec(spec);spec.loader.exec_module(C);sys.argv=argv
ap=argparse.ArgumentParser();ap.add_argument('--revision',type=int,default=2)
ap.add_argument('--clip',default='all');ap.add_argument('--movies',action='store_true')
args=ap.parse_args(argv[argv.index('--')+1:] if '--' in argv else [])
C.VERSION=f'v{args.revision:02}';C.args.final=True
for name,period in C.CLIPS.items():
    if args.clip not in ('all',name):continue
    stem=name+'_'+C.VERSION
    bpy.ops.wm.open_mainfile(filepath=str(HERE/(stem+'.blend')))
    C.scene=bpy.context.scene;C.rig=bpy.data.objects['Buddy_Rig_Mixamo65']
    C.preview(name,period)
    if args.movies:
        scene=C.scene;scene.render.engine='BLENDER_EEVEE'
        if hasattr(scene,'eevee') and hasattr(scene.eevee,'taa_render_samples'):
            scene.eevee.taa_render_samples=16
        scene.render.resolution_x=384;scene.render.resolution_y=384
        scene.render.resolution_percentage=100
        folder=HERE/'Previews'/stem/name/'motion_frames';folder.mkdir(parents=True,exist_ok=True)
        for i in range(period):
            path=folder/f'f{i:04}.png';assert not path.exists(),'Refusing movie frame overwrite'
            scene.frame_set(1+i);scene.render.filepath=str(path)
            bpy.ops.render.render(write_still=True)
            print('MOVIE_FRAME',stem,i,flush=True)
