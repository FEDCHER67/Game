# Fedya: all binary TerrainData files in git are corrupted (no ground, falling through on other PCs)

**Symptom on Vadim's PC (clean pull of 60b6c41, Unity 6000.5.11f1):** in `Map_Look_v19_Play_i04_vanpaint` there is no ground and the player falls through. Editor.log:
- `Unknown error occurred while loading 'Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset'.`
- then `Terrain has no valid TerrainData!` (many times).

**Cause:** `.gitattributes` has `*.asset unity-yaml` (= `eol=lf`), so git treats every `.asset` as text. TerrainData is saved in Unity's binary format, and on `git add` git replaced every CR LF byte pair with LF. Bytes are missing: the Unity header stores the real file size, and the blobs in git are shorter.

Your working copies are still intact, which is why everything works for you. Everyone who clones gets broken files.

## Broken files (header size minus real size)

| Bytes missing | File |
|---|---|
| 65 | `Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset` (used by `Map_Look_v19_Play_i04_vanpaint`) |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v02/Finish_v03/Terrain_finish_v03.asset` |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v03/Finish_v03/Terrain_finish_v03.asset` |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v04/Finish_v03/Terrain_finish_v03.asset` |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v05/Finish_v03/Terrain_finish_v03.asset` |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v06/Finish_v03/Terrain_finish_v03.asset` |
| 65 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Full_v07/Finish_v03/Terrain_finish_v03.asset` |
| 89 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v01/Terrain_palette.asset` |
| 88 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v02/Terrain_palette.asset` |
| 88 | `Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v03/Terrain_fog_v03.asset` |

No binary Unity file in the repo is intact (checked all of `Assets`, LFS files excluded).

How to check: bytes 24..31 of a Unity binary file hold the file size (int64, big endian). It must equal the real size.

## Fix (only on your PC; your local files are the only intact copies)

Do **not** run checkout, reset or stash on these files first. That would overwrite your intact copies with the broken versions from git.

1. In `.gitattributes`, after the `Generated/**/*.asset lfs` line, add these lines. LFS stores the bytes as they are, with no line-ending conversion.
   ```
   # Binary-serialized TerrainData (eol=lf corrupted them)
   Assets/OnlyVolunteers/Art/Trees/v03/SceneData/Terrain_v19_i01_trees.asset lfs
   Assets/OnlyVolunteers/Map/LookV3/Palette19/**/Finish_v03/Terrain_finish_v03.asset lfs
   Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v0*/Terrain_palette.asset lfs
   Assets/OnlyVolunteers/Map/LookV3/Palette19/Test_v03/Terrain_fog_v03.asset lfs
   ```
2. `git add .gitattributes`
3. For the 10 files above: `git rm --cached <file>`, then `git add <file>`.
4. Check:
   - `git lfs ls-files` must list all 10;
   - the size of each file in LFS must equal the size written in its header.
5. Commit and push.

For new binary assets, either store them in LFS straight away, or switch Unity to Force Text serialization.
