# CLAUDE.md — VOLUNTEERS ONLY

Read these before working in this repository:

1. AGENTS.md — project rules and the AI team.
2. docs/AgentRules.md — shared agent rules (verification, one bridge per category, versions/licences, .meta, safety, first-loop focus).
3. docs/CURRENT_STATE.md and docs/ARCHITECTURE.md — before gameplay work; docs/Progress.md and docs/NextAction.md for the current loop.

Project skills: `.claude/skills/fc-*`. Field Clinic kit: `Tools/FieldClinicBrief/` (start with 00_AUTOSTART.md).

## New models, textures and places: order (Vadim, 2026-10-27)

1. References first in ChatGPT, never by Claude itself: prompt folder `Desktop\ПРОМПТ_ChatGPT\NN_name` + zip; Claude sends it via computer use to the ChatGPT app (chat «Референсы Work Chat»), results land in `Desktop\NN_name_v01`, Claude watches the folder and opens them itself.
2. Vadim picks a reference.
3. Textures: a labelled texture sheet for Vadim's «да».
4. Only then the model (Blender script) / the place in Unity, built from the chosen reference and texture.
No model or map build before steps 1–3: it wastes Claude tokens and gets redone.

## Map rebuild quality (Vadim, 2026-10-25)

Every time the map is changed or rebuilt, check it before the build and before showing it:

- Nothing floats in the air or sinks into the ground: props, rocks, rock faces, trees, grass, piers, boats.
- Mountains and rocks never push onto roads, sidewalks, beaches or paths; roads, beaches, piers and shores join cleanly, with no steps, gaps or holes.
- Every surface is textured to match what it is: rock looks like rock, sand like sand. No sand texture on cliffs, no bare stretched ground.
- Everything looks natural and of a piece. Nothing artificial: no abrupt mountain ends, lone sharp rock spikes, straight edges, boxes or flat plates in nature, and no land poking out of the sea without water around it.
- Drivable places (beaches, roads, yards) stay smooth enough for the van.
- Look at a top view and at least one ground-level view of every changed place (before and after); fix anything off first.

Mistakes Vadim has already pointed out — never repeat them:

- Overwriting existing land with a generated profile (flat plateaus, straight edges, the old coast wiped). Change only what was asked and blend from the original heights.
- Land pushed into the sea, or ground lowered into the sea where Fedya's sea mesh has no water quads (blocky sand shows): add the missing sea quads.
- Boats standing on land bumps; little islands left in a marina; loungers and umbrellas on a cliff face; piers running into a cliff or hanging over a step instead of starting flush on the sand.
- Terrain teeth or rock poking through walls, deck skirts sticking out, green blobs of old terrain, rock-face shards left floating after the ground moved.
- Trees or grass on sidewalks, roads or rock; lamps lying on their side (FBX base rotation); props not standing level or straight.
- Roads that end nowhere, gaps or kinks at junctions, a road not leading straight into its gate; zoom in on every junction.
- Z-fighting and flicker (coplanar faces); invisible walls, net walls or stripes left in the world.
- Fog and haze: no giant fake land behind it, no wall of fog rising high over the map, nothing beyond it but water.
- Mountains too big or too soft when a narrow stone ridge was asked for; a ridge that stops short or ends abruptly; scattered rock pieces on grass fields.
- A request lost after a context reset: every request goes into WORK_SYNC.md; re-read the open TASKs before saying something is done.
- Showing or building before checking: renders first (top + ground), then screenshots to Vadim, then the build.
- Shore ground that is neither sand nor mountain; a mountain in two colours (beige rock faces over brown dirt). A mountain is one plain grey stone all over.
- Beach props anyhow: loungers must face the sea in pairs with an umbrella beside them, little randomness; piers start at the water line, not on the sand; boats sit on the left of their pier and never on each other.

Lessons from these mistakes (why they happened, what to do instead):

- Two colours on one mountain: a cliff is two different things, Fedya's rock-face meshes (URP Lit) on the steep part and the terrain rock layer on the rest. The same texture and tint look different on the two shaders. Whenever one changes, change both and check them side by side in one render until they read as one colour.
- A cliff dropping into the sand at 90°: cutting the ground down to beach level under a cliff leaves the rock-face shell standing as a vertical wall. At every cliff foot build a scree slope (a few metres wide) that runs into the sand, and remove the rock-face pieces below it.
- Textures: agree a texture with Vadim first (a texture sheet or a quick render of the real place), then apply it. Never apply a texture and build the game without his yes.
- Stretched textures (smeared vertical streaks on slopes): terrain textures are projected straight down, so on steep ground (over ~22°) they stretch. No texture may ever be stretched: every steep rock surface gets a box-projected rock skin (VadimHillApply.SkinOver, the same technique as Fedya's rock faces) down to where the slope flattens into sand or grass, and every mesh uses UVs at the texture's normal scale (no stretched or squashed UVs). Check slopes and cliff feet close up in the ground-level render.
