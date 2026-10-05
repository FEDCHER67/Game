using System;
using System.Collections.Generic;
using UnityEngine;

namespace OnlyVolunteers.Audio
{
    public enum SfxSurface : byte { Asphalt, Grass, Sand, Metal }

    // What a foot stands on, for footstep sounds. The van (layers Vehicle / VehicleInterior) is metal; a Terrain is
    // read from its splat map (the strongest layer at that point, by the terrain layer's name: TL_meadow, TL_sand...);
    // anything else from its renderer's material name (Look_mat_ground_asphalt__..., Look_mat_road_dirt__...).
    // Names are matched by keyword, once per collider / terrain layer, and cached. The only per-step allocation is the
    // 1x1 splat sample on a Terrain (TerrainData.GetAlphamaps has no non-allocating form).
    public static class SfxSurfaces
    {
        private static readonly Dictionary<Collider, SfxSurface> ByCollider = new();
        private static readonly Dictionary<TerrainData, SfxSurface[]> ByTerrainLayers = new();
        private static int _vehicleLayer = -2, _vehicleInteriorLayer = -2;

        // Checked in this order: the first group with a keyword in the name wins; no keyword = Asphalt.
        private static readonly string[] MetalWords = { "metal", "iron", "steel", "rust", "van", "rail", "corrugated", "cargo" };
        private static readonly string[] SandWords = { "sand", "beach", "gravel", "ballast" };
        private static readonly string[] GrassWords = { "grass", "meadow", "lawn", "field", "forest", "hedge", "leaves", "dirt", "moss", "soil", "mud" };

        public static string StepId(SfxSurface surface) => surface switch
        {
            SfxSurface.Grass => SfxIds.StepGrass,
            SfxSurface.Sand => SfxIds.StepSand,
            SfxSurface.Metal => SfxIds.StepMetal,
            _ => SfxIds.StepAsphalt,
        };

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
            SfxSurface surface = Classify(material != null ? material.name : ground.gameObject.name);
            ByCollider[key] = surface;
            return surface;
        }

        /// <summary>Surface from a material / terrain layer / object name, by keyword.</summary>
        public static SfxSurface Classify(string name)
        {
            if (string.IsNullOrEmpty(name)) return SfxSurface.Asphalt;
            if (HasAny(name, MetalWords)) return SfxSurface.Metal;
            if (HasAny(name, SandWords)) return SfxSurface.Sand;
            if (HasAny(name, GrassWords)) return SfxSurface.Grass;
            return SfxSurface.Asphalt;
        }

        private static SfxSurface OnTerrain(Terrain terrain, TerrainCollider collider, Vector3 point)
        {
            TerrainData data = terrain.terrainData;
            if (data == null || data.alphamapLayers == 0) return Classify(collider.sharedMaterial != null ? collider.sharedMaterial.name : null);
            TerrainData key = data;
            if (!ByTerrainLayers.TryGetValue(key, out SfxSurface[] layers) || layers.Length != data.alphamapLayers)
            {
                TerrainLayer[] source = data.terrainLayers;
                layers = new SfxSurface[data.alphamapLayers];
                for (int i = 0; i < layers.Length; i++)
                    layers[i] = Classify(i < source.Length && source[i] != null ? source[i].name : null);
                ByTerrainLayers[key] = layers;
            }
            Vector3 local = point - terrain.transform.position;
            int x = Mathf.Clamp(Mathf.FloorToInt(local.x / data.size.x * data.alphamapWidth), 0, data.alphamapWidth - 1);
            int z = Mathf.Clamp(Mathf.FloorToInt(local.z / data.size.z * data.alphamapHeight), 0, data.alphamapHeight - 1);
            float[,,] weights = data.GetAlphamaps(x, z, 1, 1);
            int best = 0;
            for (int i = 1; i < layers.Length; i++)
                if (weights[0, 0, i] > weights[0, 0, best]) best = i;
            return layers[best];
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
            ByTerrainLayers.Clear();
            _vehicleLayer = _vehicleInteriorLayer = -2;
        }
    }
}
