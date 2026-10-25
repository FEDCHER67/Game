import bpy,sys
from pathlib import Path
sys.path.insert(0,r'C:\Dev\Game\ArtSource\Vehicles_W86\tools');import blender_runner_v01 as R
from render_review_v01 import assetmesh,clear_helpers
R.clean();assetmesh(Path(r'C:\Dev\Game\Assets\OnlyVolunteers\Art\Map\Prefabs\Meshes\car_wrecked.asset'));clear_helpers();R.render(R.ROOT/'tools/current_previews_v01/car_wrecked.png',600,380)
