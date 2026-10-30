using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Art.Editor
{
    /// <summary>
    /// Global gloss reduction v01 for the .mat assets of the live game (Fedya 30.10: all models ~67 % less shiny; factor in
    /// OvGlossV01). The manifest (gloss_manifest_v01.json, keyed by asset path) records each material's smoothness BEFORE the
    /// reduction (baseline) and the value it must have now (target = baseline x factor). Applying it is idempotent:
    ///  - current == target: nothing to do;
    ///  - current == baseline (a builder or an import rewrote the old value): set back to target;
    ///  - anything else (someone re-authored the material on purpose): left alone and reported as drift.
    /// So the factor is applied once from a known baseline and never compounds, whoever runs it how often.
    /// Capture only ADDS materials the manifest does not know yet; once the manifest exists it skips the folders whose
    /// builders apply OvGlossV01 themselves (workshop, pharmacy, W86 vehicles), so their new materials are never reduced twice.
    /// The player's sausage and hands are excluded (their own fully matte pass).
    /// FBX-embedded materials are not listed here: GlossFbxPostprocessorV01 reduces them at import.
    /// </summary>
    public static class GlossReductionV01
    {
        public const string ManifestPath = "Assets/OnlyVolunteers/Art/Gloss/gloss_manifest_v01.json";
        const float Eps = 0.0005f;

        /// <summary>Never touched (another owner makes them fully matte).</summary>
        public static readonly string[] ExcludedRoots =
        {
            "Assets/OnlyVolunteers/Characters/PlayerSausage_W86/",
            "Assets/OnlyVolunteers/Player/Hands/",
        };

        /// <summary>Builders that apply OvGlossV01 themselves when they (re)create their materials.</summary>
        public static readonly string[] BuilderRoots =
        {
            "Assets/OnlyVolunteers/Art/Buildings/Workshop_W86/",   // W85PlayIntegrator (workshop materials)
            "Assets/OnlyVolunteers/Art/Buildings/Pharmacy_W86/",   // W85PlayIntegrator.Pharmacy
            "Assets/OnlyVolunteers/Art/Vehicles/W86_v01/",         // W86VehiclesV01.EnsureMaterial
        };

        /// <summary>Shaders whose _Smoothness is the gloss control (URP PBR lighting: smoothness = the scalar, or the scalar
        /// x the metallic/mask map's A channel). Terrain, water, sky, fog, particles, unlit, grass and foliage shaders have no
        /// smoothness of a model surface and are not listed.</summary>
        public static readonly string[] GlossShaders =
        {
            "Universal Render Pipeline/Lit", "Universal Render Pipeline/Complex Lit", "Universal Render Pipeline/Simple Lit",
            "OnlyVolunteers/StyleV3/Palette19", "OnlyVolunteers/StyleV3/Surface", "OnlyVolunteers/W86/T1_ChainLinkVeil",
            "OnlyVolunteers/StyleV3/GlassAerial19V01",
        };

        [Serializable] public class Entry { public string path, guid, name, shader, family; public float baseline, target; }
        [Serializable] public class Manifest
        {
            public string note = "Gloss reduction v01 (Fedya 30.10): target = baseline x factor (glass: x glassFactor). Applied by " +
                                 "GlossReductionV01; absolute, idempotent. Report: docs/reports/GLOSS_REDUCTION_2026-10-30_RU.md";
            public float factor = OvGlossV01.Factor, glassFactor = OvGlossV01.GlassFactor;
            public List<Entry> materials = new List<Entry>();
        }

        public static bool Excluded(string path, string materialName)
        {
            path = path.Replace('\\', '/');
            if (ExcludedRoots.Any(r => path.StartsWith(r, StringComparison.OrdinalIgnoreCase))) return true;
            return materialName != null && materialName.StartsWith("PLAYER_", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>The eyes keep their wet highlight (eye white, pupil, the shine dot), as on the player (SausageMatteV01):
        /// a few pixels of a character's readability, not a shiny surface.</summary>
        public static readonly string[] KeepShine = { "Eye_White", "Pupil", "Eye_Shine" };
        public static bool Kept(string materialName) => materialName != null && KeepShine.Any(k => materialName.Contains(k));

        static readonly string[] GlassKeys = { "glass", "window", "windshield", "windscreen", "lens" };
        static readonly string[] MetalKeys = { "metal", "steel", "chrome", "galv", "tin", "iron", "alu", "brass", "gold", "silver", "copper", "rail" };
        static readonly string[] SkinKeys = { "skin", "flesh", "body", "face", "lip" };
        static readonly string[] ClothKeys = { "cloth", "fabric", "canvas", "shirt", "pant", "trouser", "jacket", "coat", "hood", "sock", "dress", "jean", "tarp", "rag", "textile", "uniform", "vest", "cap", "hat", "scarf" };
        static readonly string[] RubberKeys = { "rubber", "tyre", "tire", "sole", "boot", "shoe", "sneaker" };

        public static bool IsGlass(string name) => Has(name, GlassKeys) && !Has(name, NotGlassKeys);
        static readonly string[] NotGlassKeys = { "frame" }; // window frames are paint / metal
        static bool Has(string name, string[] keys) { string n = (name ?? "").ToLowerInvariant(); return keys.Any(k => n.Contains(k)); }

        /// <summary>The material family (for the report and for the glass factor).</summary>
        public static string Family(string path, string name)
        {
            if (IsGlass(name)) return "glass";
            if (Has(name, RubberKeys)) return "rubber";
            if (Has(name, MetalKeys)) return "metal";
            if (Has(name, SkinKeys)) return "skin";
            if (Has(name, ClothKeys)) return "cloth";
            string p = path.ToLowerInvariant();
            if (p.Contains("/characters/")) return "character";
            if (p.Contains("/vehicles/")) return "vehicle";
            if (p.Contains("/buildings/") || p.Contains("maptextures") || p.Contains("texturetest") || p.Contains("/w85build/") || p.Contains("/lookv3/")) return "building";
            return "prop";
        }

        public static float FactorFor(string name) => IsGlass(name) ? OvGlossV01.GlassFactor : OvGlossV01.Factor;

        public static Manifest Load()
        {
            if (!File.Exists(ManifestPath)) return null;
            return JsonUtility.FromJson<Manifest>(File.ReadAllText(ManifestPath));
        }

        static void Save(Manifest m)
        {
            m.materials.Sort((a, b) => string.CompareOrdinal(a.path, b.path));
            File.WriteAllText(ManifestPath, JsonUtility.ToJson(m, true));
            AssetDatabase.ImportAsset(ManifestPath);
            GlossMatGuardV01.Invalidate();
        }

        /// <summary>The scenes of the build (the live game) plus their whole dependency tree (prefabs spawned by the scenes'
        /// components included).</summary>
        public static string[] LiveScenes() => EditorBuildSettings.scenes.Where(s => s.enabled && File.Exists(s.path)).Select(s => s.path).ToArray();

        /// <summary>Adds the live materials the manifest does not list yet (baseline = their value now) and applies it.</summary>
        [MenuItem("OnlyVolunteers/Art/Gloss v01: capture new live materials + apply")]
        public static void MenuCaptureAndApply() => Debug.Log(CaptureAndApply());

        [MenuItem("OnlyVolunteers/Art/Gloss v01: re-apply manifest (idempotent)")]
        public static void MenuApply() => Debug.Log(Apply(null));

        public static string CaptureAndApply()
        {
            var m = Load();
            bool first = m == null;
            m ??= new Manifest();
            var known = new HashSet<string>(m.materials.Select(e => e.path));
            int added = 0, skippedShader = 0, skippedExcluded = 0, skippedBuilder = 0;
            var otherShaders = new SortedDictionary<string, int>();
            foreach (string path in AssetDatabase.GetDependencies(LiveScenes(), true).Where(p => p.EndsWith(".mat", StringComparison.OrdinalIgnoreCase)))
            {
                if (known.Contains(path) || !path.StartsWith("Assets/")) continue; // package materials are read-only
                var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (!mat || !mat.shader) continue;
                if (Excluded(path, mat.name) || Kept(mat.name)) { skippedExcluded++; continue; }
                if (!GlossShaders.Contains(mat.shader.name) || !mat.HasProperty("_Smoothness"))
                {
                    skippedShader++; otherShaders.TryGetValue(mat.shader.name, out int c); otherShaders[mat.shader.name] = c + 1; continue;
                }
                if (!first && BuilderRoots.Any(r => path.StartsWith(r))) { skippedBuilder++; continue; }
                float b = mat.GetFloat("_Smoothness");
                m.materials.Add(new Entry
                {
                    path = path, guid = AssetDatabase.AssetPathToGUID(path), name = mat.name, shader = mat.shader.name,
                    family = Family(path, mat.name), baseline = b, target = (float)Math.Round(b * FactorFor(mat.name), 4),
                });
                added++;
            }
            Save(m);
            var sb = new StringBuilder($"gloss v01 capture: +{added} materials (manifest {m.materials.Count}); skipped: {skippedExcluded} excluded (player / eyes), " +
                                       $"{skippedBuilder} builder-owned new, {skippedShader} without a model gloss control");
            foreach (var kv in otherShaders) sb.Append($"\n  not a gloss shader: {kv.Key} x{kv.Value}");
            sb.Append('\n').Append(Apply(null, m));
            return sb.ToString();
        }

        /// <summary>After a change of OvGlossV01.Factor / GlassFactor: recomputes every target from its recorded baseline (never
        /// from the current value, so nothing compounds) and moves the materials that sit on their old target or their baseline.</summary>
        [MenuItem("OnlyVolunteers/Art/Gloss v01: re-target from baselines (after a factor change)")]
        public static void MenuRetarget() => Debug.Log(Retarget());

        public static string Retarget()
        {
            var m = Load(); if (m == null) return "gloss v01: no manifest";
            int moved = 0, changed = 0, drift = 0; var notes = new StringBuilder();
            foreach (var e in m.materials)
            {
                e.family = Family(e.path, e.name);
                float t = (float)Math.Round(e.baseline * FactorFor(e.name), 4);
                if (Mathf.Abs(t - e.target) < Eps) continue;
                changed++;
                var mat = AssetDatabase.LoadAssetAtPath<Material>(e.path);
                if (mat && mat.HasProperty("_Smoothness"))
                {
                    float cur = mat.GetFloat("_Smoothness");
                    if (Mathf.Abs(cur - e.target) < Eps || Mathf.Abs(cur - e.baseline) < Eps)
                    { mat.SetFloat("_Smoothness", t); EditorUtility.SetDirty(mat); AssetDatabase.SaveAssetIfDirty(mat); moved++; }
                    else { drift++; notes.Append("\n  drift (left as is): ").Append(e.path).Append(" = ").Append(cur.ToString("0.###")); }
                }
                e.target = t;
            }
            m.factor = OvGlossV01.Factor; m.glassFactor = OvGlossV01.GlassFactor;
            Save(m);
            return $"gloss v01 re-target: {changed} targets changed, {moved} materials moved, {drift} drift" + notes;
        }

        /// <summary>Puts every listed material (or only the given paths) on its target. Returns a one-line summary + drift.</summary>
        public static string Apply(ICollection<string> onlyPaths, Manifest m = null)
        {
            m ??= Load();
            if (m == null) return "gloss v01: no manifest";
            int set = 0, ok = 0, drift = 0, missing = 0; var notes = new StringBuilder();
            foreach (var e in m.materials)
            {
                if (onlyPaths != null && !onlyPaths.Contains(e.path)) continue;
                var mat = AssetDatabase.LoadAssetAtPath<Material>(e.path);
                if (!mat || !mat.HasProperty("_Smoothness")) { missing++; continue; }
                float cur = mat.GetFloat("_Smoothness");
                if (Mathf.Abs(cur - e.target) < Eps) { ok++; continue; }
                if (Mathf.Abs(cur - e.baseline) < Eps)
                {
                    mat.SetFloat("_Smoothness", e.target); EditorUtility.SetDirty(mat); AssetDatabase.SaveAssetIfDirty(mat); set++;
                    continue;
                }
                drift++; notes.Append($"\n  drift (left as is): {e.path} = {cur:0.###} (baseline {e.baseline:0.###}, target {e.target:0.###})");
            }
            return $"gloss v01 apply: {set} set, {ok} already on target, {drift} drift, {missing} missing" + notes;
        }
    }

    /// <summary>Re-asserts the manifest when a listed .mat is (re)imported, e.g. after a map/prop builder rewrote it with its old
    /// constant. Only listed materials whose value equals the recorded baseline are touched, so it converges after one write.
    /// Runs inside the import callback (no delayCall: an editor driven in the background by tools does not tick it).</summary>
    public sealed class GlossMatGuardV01 : AssetPostprocessor
    {
        static Dictionary<string, GlossReductionV01.Entry> byPath;

        public static void Invalidate() => byPath = null;

        static void OnPostprocessAllAssets(string[] imported, string[] deleted, string[] moved, string[] movedFrom)
        {
            List<string> hits = null;
            foreach (string p in imported)
            {
                if (p == GlossReductionV01.ManifestPath) { byPath = null; continue; }
                if (!p.EndsWith(".mat", StringComparison.OrdinalIgnoreCase)) continue;
                if (byPath == null)
                {
                    var m = GlossReductionV01.Load();
                    byPath = m == null ? new Dictionary<string, GlossReductionV01.Entry>() : m.materials.GroupBy(e => e.path).ToDictionary(g => g.Key, g => g.First());
                }
                if (byPath.ContainsKey(p)) (hits ??= new List<string>()).Add(p);
            }
            if (hits == null) return;
            string r = GlossReductionV01.Apply(hits);
            if (!r.Contains(" 0 set,") || r.Contains("drift (")) Debug.Log("[GlossMatGuardV01] " + r);
        }
    }

    /// <summary>FBX-embedded materials (crowd NPC types, patients, mechanic, W86 props and cars, organs...): the importer's
    /// smoothness (URP: sqrt(FBX Shininess / 100), i.e. 1 - Blender roughness) x OvGlossV01.Factor (glass: GlassFactor).
    /// Every import starts again from the FBX, so the reduction is applied exactly once per import and never compounds.
    /// Remapped (external .mat) materials are not affected here (the manifest handles them). Player sausage + hands excluded,
    /// the eyes keep their shine (KeepShine).</summary>
    public sealed class GlossFbxPostprocessorV01 : AssetPostprocessor
    {
        public override uint GetVersion() => 4; // 3: glass/lens names take OvGlossV01.GlassFactor; 4: window frames are not glass
        public override int GetPostprocessOrder() => 1000; // after URP's FBX material description preprocessor (-980)

        // ImportViaMaterialDescription (crowd NPCs, mechanic, W86 props/cars...): Unity does not call OnPostprocessMaterial in
        // this mode; the material is built by the description preprocessors, URP's first (it sets _Smoothness), then this one.
        void OnPreprocessMaterialDescription(UnityEditor.AssetImporters.MaterialDescription description, Material material, AnimationClip[] clips) =>
            Reduce(material, string.IsNullOrEmpty(material ? material.name : null) ? description.materialName : material.name);

        // ImportStandard (legacy) models: the classic callback, only when the description path above did not run
        void OnPostprocessMaterial(Material material)
        {
            if (assetImporter is ModelImporter mi && mi.materialImportMode == ModelImporterMaterialImportMode.ImportViaMaterialDescription) return;
            Reduce(material, material ? material.name : null);
        }

        void Reduce(Material material, string name)
        {
            if (!material || !assetPath.StartsWith("Assets/", StringComparison.Ordinal)) return;
            if (GlossReductionV01.Excluded(assetPath, name) || GlossReductionV01.Kept(name)) return;
            if (!material.HasProperty("_Smoothness")) return;
            material.SetFloat("_Smoothness", material.GetFloat("_Smoothness") * GlossReductionV01.FactorFor(name));
        }
    }
}
