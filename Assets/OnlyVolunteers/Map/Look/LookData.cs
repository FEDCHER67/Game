using System;

namespace OnlyVolunteers.Map.Look
{
    // look_vNN_flat.json as written by ArtSource/References/Map/Look/flatten_look.py (schema look_v1).
    // Plan (x, y) metres map to Unity (x, height, y); angles are Unity yaw (90 - plan angle); polylines and polygons are
    // flat x,y float pairs; polygons and tris are plan-CCW, so every triangle is reversed before it goes into a mesh.
    // Plain System types only, so the height model can be tested outside Unity.
    [Serializable]
    public sealed class LookData
    {
        public string schema, revision, source_plan, source_dressing;
        public int seed;
        public string angle_convention, winding;
        public string[] soft_layers, hard_mats;
        public string ground_default;
        public LookTerrain terrain;
        public LookBoundary boundary;
        public LookDistrict[] districts;
        public LookHill[] hills;
        public LookBuilding[] buildings;
        public LookRoad[] roads;
        public LookJunction[] junctions;
        public LookCrossing[] crossings;
        public LookSidewalk[] sidewalks;
        public LookMarking[] markings;
        public LookParking[] parking;
        public LookYard[] yards;
        public LookGround[] ground;
        public LookWater[] water;
        public LookSea sea;
        public LookBeach beach;
        public LookRail rail;
        public LookEliteFence[] elite_fence;
        public LookBlocker[] blockers;
        public LookRock[] rocks;
        public LookTree[] trees;
        public LookFurniture[] furniture;
        public LookPipe[] pipes;
        public LookDecal[] decals;
        public LookVehicle[] vehicles;
        public LookLandmark[] landmarks;
        public LookExit[] exits;
        public LookPoint[] points;
        public string[] warnings;

        // JsonUtility leaves missing arrays null; the builders expect empty ones.
        public void Normalise()
        {
            soft_layers ??= new string[0];
            hard_mats ??= new string[0];
            terrain ??= new LookTerrain();
            terrain.layers ??= new string[0];
            boundary ??= new LookBoundary();
            boundary.pts ??= new float[0];
            boundary.coast ??= new int[0];
            districts ??= new LookDistrict[0];
            hills ??= new LookHill[0];
            buildings ??= new LookBuilding[0];
            roads ??= new LookRoad[0];
            junctions ??= new LookJunction[0];
            crossings ??= new LookCrossing[0];
            sidewalks ??= new LookSidewalk[0];
            markings ??= new LookMarking[0];
            parking ??= new LookParking[0];
            yards ??= new LookYard[0];
            ground ??= new LookGround[0];
            water ??= new LookWater[0];
            sea ??= new LookSea();
            sea.pts ??= new float[0];
            sea.tris ??= new float[0];
            beach ??= new LookBeach();
            beach.pts ??= new float[0];
            beach.tris ??= new float[0];
            beach.land ??= new float[0];
            beach.sea ??= new float[0];
            rail ??= new LookRail();
            rail.pts ??= new float[0];
            rail.crossings ??= new LookRailCrossing[0];
            elite_fence ??= new LookEliteFence[0];
            blockers ??= new LookBlocker[0];
            rocks ??= new LookRock[0];
            trees ??= new LookTree[0];
            furniture ??= new LookFurniture[0];
            pipes ??= new LookPipe[0];
            decals ??= new LookDecal[0];
            vehicles ??= new LookVehicle[0];
            landmarks ??= new LookLandmark[0];
            exits ??= new LookExit[0];
            points ??= new LookPoint[0];
            warnings ??= new string[0];
            foreach (LookBuilding b in buildings)
            {
                b.fp ??= new float[0];
                b.tris ??= new float[0];
                b.rects ??= new float[0];
                b.ent ??= new float[0];
                b.sign_text ??= "";
                b.prop_key ??= "";
                b.district ??= "";
            }
            foreach (LookRoad r in roads) r.pts ??= new float[0];
            foreach (LookJunction j in junctions)
            {
                j.pts ??= new float[0];
                j.tris ??= new float[0];
                j.roads ??= new string[0];
            }
            foreach (LookYard y in yards)
            {
                y.pts ??= new float[0];
                y.gaps ??= new float[0];
                y.tris ??= new float[0];
            }
            foreach (LookGround g in ground)
            {
                g.pts ??= new float[0];
                g.tris ??= new float[0];
            }
            foreach (LookParking p in parking)
            {
                p.pts ??= new float[0];
                p.tris ??= new float[0];
                p.stalls ??= new float[0];
                p.access ??= new float[0];
            }
            foreach (LookWater w in water)
            {
                w.pts ??= new float[0];
                w.tris ??= new float[0];
            }
            foreach (LookEliteFence f in elite_fence)
            {
                f.pts ??= new float[0];
                f.gaps ??= new float[0];
            }
            foreach (LookExit e in exits)
            {
                e.barriers ??= new LookPolyline[0];
                e.trigger ??= new float[0];
                foreach (LookPolyline p in e.barriers) p.pts ??= new float[0];
            }
            foreach (LookDecal d in decals)
            {
                d.pts ??= new float[0];
                d.tris ??= new float[0];
            }
        }
    }

    [Serializable]
    public sealed class LookTerrain
    {
        public float x0, y0, sx = 1280f, sy = 1024f, heightmap = 1025f, splatmap = 1024f, pixel_error = 3f;
        public string[] layers;
        public string @default = "meadow";
    }

    [Serializable]
    public sealed class LookBoundary
    {
        public float[] pts;
        public int[] coast;
        public float band = 5f, berm_h = 2.5f, blocker_h = 6f;
    }

    [Serializable]
    public sealed class LookDistrict
    {
        public string id, name, color, @base;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookHill
    {
        public string id;
        public float x, y, rx, ry, h;
    }

    [Serializable]
    public sealed class LookBuilding
    {
        public string id, kind, type, district, label, style, roof;
        public int floors;
        public float floor_h, h, front_deg, x, y;
        public float[] fp, tris, rects, ent;
        public string wall, trim, roof_col, sign_text;
        public int sign_side = -1;
        public int seed;
        public string prop_key, access;
    }

    [Serializable]
    public sealed class LookRoad
    {
        public string id, road, cls;
        public float w;
        public int lanes;
        public bool van;
        public string surface, district;
        public float[] pts;
        public float trim_start, trim_end, length;
    }

    [Serializable]
    public sealed class LookJunction
    {
        public string id;
        public float x, y, r;
        public int arms;
        public string[] roads;
        public float[] pts, tris;
    }

    [Serializable]
    public sealed class LookCrossing
    {
        public string id, road, water, kind;
        public float x, y, a, len, w;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookSidewalk
    {
        public string road, side;
        public float w, verge, curb;
        public string district;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookMarking
    {
        public string kind, road;
        public float w, dash, gap;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookParking
    {
        public string id, building, mat;
        public float[] pts, tris, stalls, access;
        public float access_w;
    }

    [Serializable]
    public sealed class LookYard
    {
        public string id, kind, district, fence;
        public float h;
        public float[] pts, gaps, tris;
        public float perimeter;
        public string ground;
    }

    [Serializable]
    public sealed class LookGround
    {
        public string mat;
        public int prio;
        public bool soft;
        public float edge;
        public string ctx;
        public float[] pts, tris;
    }

    [Serializable]
    public sealed class LookWater
    {
        public string id, kind;
        public float level, depth, w, wet_w, bank;
        public string bank_mat;
        public float[] pts, tris;
    }

    [Serializable]
    public sealed class LookSea
    {
        public string id;
        public float level = -0.6f, apron = 60f, bed = -4f;
        public float[] pts, tris;
    }

    [Serializable]
    public sealed class LookBeach
    {
        public string id;
        public float w, dry = 40f, surf = 14f;
        public float[] pts, tris, land, sea;
    }

    [Serializable]
    public sealed class LookRail
    {
        public float[] pts;
        public float w = 3f;
        public LookRailCrossing[] crossings;
    }

    [Serializable]
    public sealed class LookRailCrossing
    {
        public float x, y;
        public string road, kind;
    }

    [Serializable]
    public sealed class LookEliteFence
    {
        public string id;
        public float h;
        public float[] pts, gaps;
        public float length;
        public string[] gate_roads;
    }

    [Serializable]
    public sealed class LookBlocker
    {
        public string id, kind;
        public float h;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookRock
    {
        public string k;
        public float x, y, sx, sy, sz, a;
    }

    [Serializable]
    public sealed class LookTree
    {
        public string sp;
        public float x, y, h;
    }

    [Serializable]
    public sealed class LookFurniture
    {
        public string type;
        public float x, y, a;
    }

    [Serializable]
    public sealed class LookPipe
    {
        public string id;
        public float d;
        public string mode;
        public float h;
        public bool collide;
        public string color;
        public float[] pts;
    }

    [Serializable]
    public sealed class LookDecal
    {
        public string type;
        public float x, y, a, sx, sy;
        public string color;
        public float alpha;
        public float[] pts, tris;
    }

    // Parked vehicle (extras_v12_kits.py): prefab prop/<type> at the exact Unity yaw a - no builder jitter.
    [Serializable]
    public sealed class LookVehicle
    {
        public string type, district, spot;
        public float x, y, a;
    }

    // Landmark kit piece. mount: "ground" (z above the terrain), "roof" / "facade" / "belfry" (z above the pad of `building`),
    // "tower" (free-standing: shaft_w x shaft_w x shaft_h brick shaft on the terrain, the kit top at z). s = uniform scale;
    // `replaces` names the ProceduralBuilding stand-in to skip (see ProceduralBuilding Ctx.Kit).
    [Serializable]
    public sealed class LookLandmark
    {
        public string type, mount, building, district, replaces, spot;
        public float x, y, z, a, s = 1f, shaft_w, shaft_h;
    }

    [Serializable]
    public sealed class LookPolyline
    {
        public float[] pts;
    }

    [Serializable]
    public sealed class LookExit
    {
        public string id, post, type, road;
        public float x, y, px, py, h;
        public LookPolyline[] barriers;
        public float[] trigger;
    }

    [Serializable]
    public sealed class LookPoint
    {
        public string id, label, cat, district;
        public float x, y;
    }
}
