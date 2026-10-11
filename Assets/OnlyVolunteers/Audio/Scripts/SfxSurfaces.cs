using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace OnlyVolunteers.Audio
{
    public enum SfxSurface : byte { Asphalt, Grass, Sand, Metal, Gravel, Mud, Dirt }

    // What a foot stands on, for footstep sounds. The van (layers Vehicle / VehicleInterior) is metal; a Terrain is
    // read from its splat map (the strongest layer at that point, by the terrain layer's name: TL_meadow, TL_sand...);
    // anything else from its renderer's material name (Look_mat_ground_asphalt__..., Look_mat_road_dirt__...).
    // Names and each terrain's dominant splat layer are cached at scene entry: no per-footfall splat allocation.
    public static class SfxSurfaces
    {
        private static readonly Dictionary<Collider, SfxSurface> ByCollider = new();
        private sealed class TerrainSurfaces
        {
            public int Width, Height;
            public SfxSurface[] Cells;
        }
        private static readonly Dictionary<TerrainData, TerrainSurfaces> ByTerrain = new();
        private static int _vehicleLayer = -2, _vehicleInteriorLayer = -2;

        // Checked in this order: the first group with a keyword in the name wins; no keyword = Asphalt.
        private static readonly string[] MetalWords = { "metal", "iron", "steel", "rust", "van", "rail", "corrugated", "cargo" };
        private static readonly string[] MudWords = { "mud" };
        private static readonly string[] GravelWords = { "gravel", "ballast" };
        private static readonly string[] DirtWords = { "dirt", "soil" };
        private static readonly string[] SandWords = { "sand", "beach" };
        private static readonly string[] GrassWords = { "grass", "meadow", "lawn", "field", "forest", "hedge", "leaves", "moss" };

        public static string StepId(SfxSurface surface) => surface switch
        {
            SfxSurface.Grass => SfxIds.StepGrass,
            SfxSurface.Sand => SfxIds.StepSand,
            SfxSurface.Gravel => SfxIds.StepSand,
            SfxSurface.Mud => SfxIds.StepGrass,
            SfxSurface.Dirt => SfxIds.StepGrass,
            SfxSurface.Metal => SfxIds.StepMetal,
            _ => SfxIds.StepAsphalt,
        };

        /// <summary>Water overrides the dry surface; deep water suppresses discrete steps (the walker owns its loop).</summary>
        public static string StepId(Collider ground, Vector3 foot, bool running)
        {
            float depth = WaterQuery.FootDepth(foot);
            if (depth > 0.4f) return null;
            if (depth >= 0.03f) return running ? SfxIds.StepWaterRun : SfxIds.StepWater;
            return StepId(At(ground, foot));
        }

        /// <summary>Surface of 'ground' at the world 'point' (null ground: asphalt).</summary>
        public static SfxSurface At(Collider ground, Vector3 point)
        {
            if (ground == null) return SfxSurface.Asphalt;
            if (IsVan(ground.gameObject.layer)) return SfxSurface.Metal;
            if (ground is TerrainCollider terrainCollider && ground.TryGetComponent(out Terrain terrain))
                return OnTerrain(terrain, terrainCollider, point);
            Collider key = ground;
            if (ByCollider.TryGetValue(key, out SfxSurface cached)) return cached;
            Renderer renderer = ground.TryGetComponent(out Renderer own) ? own : ground.GetComponentInParent<Renderer>();
            Material material = renderer != null ? renderer.sharedMaterial : null;
            string name = material != null ? material.name :
                ground.sharedMaterial != null ? ground.sharedMaterial.name : ground.gameObject.name;
            SfxSurface surface = Classify(name);
            ByCollider[key] = surface;
            return surface;
        }

        /// <summary>Surface from a material / terrain layer / object name, by keyword.</summary>
        public static SfxSurface Classify(string name)
        {
            if (string.IsNullOrEmpty(name)) return SfxSurface.Asphalt;
            if (HasAny(name, MetalWords)) return SfxSurface.Metal;
            if (HasAny(name, MudWords)) return SfxSurface.Mud;
            if (HasAny(name, GravelWords)) return SfxSurface.Gravel;
            if (HasAny(name, DirtWords)) return SfxSurface.Dirt;
            if (HasAny(name, SandWords)) return SfxSurface.Sand;
            if (HasAny(name, GrassWords)) return SfxSurface.Grass;
            return SfxSurface.Asphalt;
        }

        private static SfxSurface OnTerrain(Terrain terrain, TerrainCollider collider, Vector3 point)
        {
            TerrainData data = terrain.terrainData;
            if (data == null || data.alphamapLayers == 0) return Classify(collider.sharedMaterial != null ? collider.sharedMaterial.name : null);
            TerrainData key = data;
            if (!ByTerrain.TryGetValue(key, out TerrainSurfaces surfaces)) surfaces = CacheTerrain(data);
            Vector3 local = point - terrain.transform.position;
            int x = Mathf.Clamp(Mathf.FloorToInt(local.x / data.size.x * data.alphamapWidth), 0, data.alphamapWidth - 1);
            int z = Mathf.Clamp(Mathf.FloorToInt(local.z / data.size.z * data.alphamapHeight), 0, data.alphamapHeight - 1);
            return surfaces.Cells[z * surfaces.Width + x];
        }

        private static TerrainSurfaces CacheTerrain(TerrainData data)
        {
            TerrainLayer[] source = data.terrainLayers;
            var layers = new SfxSurface[data.alphamapLayers];
            for (int i = 0; i < layers.Length; i++)
                layers[i] = Classify(i < source.Length && source[i] != null ? source[i].name : null);
            var surfaces = new TerrainSurfaces { Width = data.alphamapWidth, Height = data.alphamapHeight };
            surfaces.Cells = new SfxSurface[surfaces.Width * surfaces.Height];
            float[,,] weights = data.GetAlphamaps(0, 0, surfaces.Width, surfaces.Height);
            for (int z = 0; z < surfaces.Height; z++)
                for (int x = 0; x < surfaces.Width; x++)
                {
                    int best = 0;
                    for (int i = 1; i < layers.Length; i++)
                        if (weights[z, x, i] > weights[z, x, best]) best = i;
                    surfaces.Cells[z * surfaces.Width + x] = layers[best];
                }
            ByTerrain[data] = surfaces;
            return surfaces;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void WarmTerrains()
        {
            SceneManager.sceneLoaded -= SceneLoaded;
            SceneManager.sceneLoaded += SceneLoaded;
            SceneLoaded(default, LoadSceneMode.Single);
        }

        private static void SceneLoaded(Scene scene, LoadSceneMode mode)
        {
            foreach (Terrain terrain in Terrain.activeTerrains)
                if (terrain.terrainData != null && terrain.terrainData.alphamapLayers > 0 && !ByTerrain.ContainsKey(terrain.terrainData))
                    CacheTerrain(terrain.terrainData);
        }

        private static bool IsVan(int layer)
        {
            if (_vehicleLayer == -2)
            {
                _vehicleLayer = LayerMask.NameToLayer("Vehicle");
                _vehicleInteriorLayer = LayerMask.NameToLayer("VehicleInterior");
            }
            return layer >= 0 && (layer == _vehicleLayer || layer == _vehicleInteriorLayer);
        }

        private static bool HasAny(string name, string[] words)
        {
            foreach (string word in words)
                if (name.IndexOf(word, StringComparison.OrdinalIgnoreCase) >= 0)
                    return true;
            return false;
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.SubsystemRegistration)]
        private static void ResetStatics()
        {
            ByCollider.Clear();
            SceneManager.sceneLoaded -= SceneLoaded;
            ByTerrain.Clear();
            _vehicleLayer = _vehicleInteriorLayer = -2;
        }
    }
}
