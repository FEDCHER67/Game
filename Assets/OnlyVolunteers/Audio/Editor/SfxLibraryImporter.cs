using System;
using System.Collections.Generic;
using System.IO;
using OnlyVolunteers.Audio;
using UnityEditor;
using UnityEngine;

namespace OnlyVolunteers.Audio.EditorTools
{
    // Builds the offline SFX layer's assets.
    // 1) "Import SFX_GEN v01 + fill library": copies ArtSource/Audio/SFX_GEN/Out/v01/*.wav (outside the import tree) into
    //    Assets/OnlyVolunteers/Audio/SFX_GEN (a file that is already there with the same size is skipped, so .meta GUIDs
    //    stay), sets short-SFX import settings, then 2).
    // 2) "Refill library": for every event in Events, the clips whose file name is the prefix or prefix_NN. Clips under
    //    Assets/OnlyVolunteers/Audio/Final (real sounds, any subfolder) replace the SFX_GEN placeholders of that event.
    //    Entries keep hand-tuned volume/pitch/3D settings; Locked entries also keep their clips. Missing entries are made
    //    with the defaults below. The library is Audio/Resources/SfxLibrary.asset (Sfx loads it from Resources).
    public static class SfxLibraryImporter
    {
        private const string SourceDir = "ArtSource/Audio/SFX_GEN/Out/v01";
        private const string AudioRoot = "Assets/OnlyVolunteers/Audio";
        private const string PlaceholderDir = AudioRoot + "/SFX_GEN";
        private const string FinalDir = AudioRoot + "/Final";
        private const string LibraryPath = AudioRoot + "/Resources/SfxLibrary.asset";

        private readonly struct Def
        {
            public readonly string Id, Prefix;
            public readonly Vector2 Volume, Pitch;
            public readonly float MaxDistance, Cooldown;
            public readonly int Priority;

            public Def(string id, string prefix, float volume, float pitchLow, float pitchHigh, float maxDistance, float cooldown, int priority)
            {
                Id = id;
                Prefix = prefix;
                Volume = new Vector2(volume * 0.85f, volume);
                Pitch = new Vector2(pitchLow, pitchHigh);
                MaxDistance = maxDistance;
                Cooldown = cooldown;
                Priority = priority;
            }
        }

        // id, file prefix, volume, pitch range, max distance, cooldown, priority (0 most important). First guesses:
        // balance by ear in Play mode, then edit the asset (a refill keeps the edits).
        private static readonly Def[] Events =
        {
            new(SfxIds.HitHead, "punch_bonk", 1f, 1.08f, 1.2f, 30f, 0.05f, 40),
            new(SfxIds.HitTorso, "punch_bonk", 0.9f, 0.88f, 0.98f, 30f, 0.05f, 40),
            new(SfxIds.HitLimb, "slap", 0.85f, 0.95f, 1.1f, 25f, 0.05f, 45),
            new(SfxIds.ThudGround, "body_thud_ground", 0.9f, 0.9f, 1.1f, 25f, 0.12f, 70),
            new(SfxIds.ThudVan, "body_thud_van_floor", 0.9f, 0.9f, 1.1f, 25f, 0.12f, 70),
            new(SfxIds.DoorFrontOpen, "van_door_open", 0.8f, 0.97f, 1.03f, 25f, 0.1f, 60),
            new(SfxIds.DoorFrontClose, "van_door_close", 0.85f, 0.97f, 1.03f, 30f, 0.1f, 60),
            new(SfxIds.DoorFrontSlam, "van_door_slam", 1f, 0.95f, 1.05f, 40f, 0.1f, 55),
            new(SfxIds.DoorRearOpen, "rear_door_open", 0.8f, 0.97f, 1.03f, 25f, 0.1f, 60),
            new(SfxIds.DoorRearClose, "rear_door_close", 0.85f, 0.97f, 1.03f, 30f, 0.1f, 60),
            new(SfxIds.DoorRearSlam, "van_door_slam", 1f, 0.88f, 0.96f, 40f, 0.1f, 55),
            new(SfxIds.DoorSlideOpen, "slide_door_open", 0.85f, 0.97f, 1.03f, 30f, 0.1f, 60),
            new(SfxIds.DoorSlideClose, "slide_door_close", 0.9f, 0.97f, 1.03f, 30f, 0.1f, 60),
            new(SfxIds.StepAsphalt, "footstep_asphalt", 0.45f, 0.92f, 1.08f, 15f, 0.15f, 150),
            new(SfxIds.StepGrass, "footstep_grass", 0.45f, 0.92f, 1.08f, 15f, 0.15f, 150),
            new(SfxIds.StepSand, "footstep_sand", 0.45f, 0.92f, 1.08f, 15f, 0.15f, 150),
            new(SfxIds.StepMetal, "footstep_metal_floor", 0.5f, 0.92f, 1.08f, 15f, 0.15f, 150),
            new(SfxIds.NpcScream, "npc_scream", 1f, 0.9f, 1.15f, 45f, 0.3f, 50),
            new(SfxIds.NpcMumble, "npc_mumble_gibberish", 0.7f, 0.9f, 1.15f, 18f, 0.2f, 110),
            new(SfxIds.NpcWhimper, "npc_whimper", 0.7f, 0.92f, 1.12f, 15f, 0.2f, 110),
            new(SfxIds.NpcGasp, "npc_gasp", 0.8f, 0.92f, 1.12f, 20f, 0.2f, 100),
            new(SfxIds.OrganSquish, "organ_squish", 0.9f, 0.9f, 1.1f, 15f, 0.05f, 60),
            new(SfxIds.PoliceSiren, "police_siren_short", 1f, 1f, 1f, 120f, 0.5f, 30),
            new(SfxIds.PhoneBuzz, "phone_buzz", 0.8f, 1f, 1f, 10f, 0.3f, 30),
            new(SfxIds.CashRegister, "cash_register", 0.9f, 0.98f, 1.02f, 20f, 0.3f, 60),
        };

        [MenuItem("OnlyVolunteers/Audio/Import SFX_GEN v01 + fill library")]
        public static void ImportAndFill()
        {
            string projectRoot = Path.GetDirectoryName(Application.dataPath);
            string source = Path.Combine(projectRoot, SourceDir);
            if (!Directory.Exists(source))
            {
                Debug.LogError($"[Sfx] {SourceDir} not found.");
                return;
            }
            Directory.CreateDirectory(Path.Combine(projectRoot, PlaceholderDir));
            int copied = 0, skipped = 0, lfs = 0;
            var imported = new List<string>();
            foreach (string file in Directory.GetFiles(source, "*.wav"))
            {
                // A Git LFS pointer instead of the sound (git lfs pull not run): a ~130-byte text file.
                if (new FileInfo(file).Length < 1024 && IsLfsPointer(file))
                {
                    lfs++;
                    continue;
                }
                string assetPath = PlaceholderDir + "/" + Path.GetFileName(file);
                string target = Path.Combine(projectRoot, assetPath);
                imported.Add(assetPath);
                if (File.Exists(target) && new FileInfo(target).Length == new FileInfo(file).Length)
                {
                    skipped++;
                    continue;
                }
                File.Copy(file, target, true); // overwriting keeps the .meta next to it, so references survive
                copied++;
            }
            AssetDatabase.Refresh();
            foreach (string assetPath in imported) ApplyImportSettings(assetPath);
            if (lfs > 0)
                Debug.LogWarning($"[Sfx] {lfs} WAV files in {SourceDir} are Git LFS pointers: run 'git lfs pull' and import again.");
            Debug.Log($"[Sfx] Copied {copied}, unchanged {skipped} into {PlaceholderDir}.");
            Fill();
        }

        [MenuItem("OnlyVolunteers/Audio/Refill library from Audio folders")]
        public static void Fill()
        {
            SfxLibrary library = LoadOrCreateLibrary();
            List<(string name, AudioClip clip)> placeholders = Clips(PlaceholderDir);
            List<(string name, AudioClip clip)> finals = Clips(FinalDir);
            Undo.RecordObject(library, "Fill SFX library");
            var report = new List<string>();
            foreach (Def def in Events)
            {
                SfxLibrary.Entry entry = library.Entries.Find(e => e != null && e.Id == def.Id);
                if (entry == null)
                {
                    entry = new SfxLibrary.Entry
                    {
                        Id = def.Id, Volume = def.Volume, Pitch = def.Pitch, MaxDistance = def.MaxDistance,
                        Cooldown = def.Cooldown, Priority = def.Priority,
                    };
                    library.Entries.Add(entry);
                }
                if (entry.Locked)
                {
                    report.Add($"{def.Id}: locked, {entry.Clips?.Length ?? 0} clips kept");
                    continue;
                }
                AudioClip[] clips = Matching(finals, def.Prefix);
                string from = "Final";
                if (clips.Length == 0)
                {
                    clips = Matching(placeholders, def.Prefix);
                    from = "SFX_GEN";
                }
                entry.Clips = clips;
                report.Add(clips.Length == 0 ? $"{def.Id}: NO CLIPS for '{def.Prefix}'" : $"{def.Id}: {clips.Length} from {from} ({def.Prefix})");
            }
            library.Rebuild();
            EditorUtility.SetDirty(library);
            AssetDatabase.SaveAssets();
            Debug.Log($"[Sfx] Library {LibraryPath}:\n" + string.Join("\n", report), library);
        }

        private static SfxLibrary LoadOrCreateLibrary()
        {
            var library = AssetDatabase.LoadAssetAtPath<SfxLibrary>(LibraryPath);
            if (library != null) return library;
            Directory.CreateDirectory(Path.Combine(Path.GetDirectoryName(Application.dataPath), Path.GetDirectoryName(LibraryPath)));
            AssetDatabase.Refresh();
            library = ScriptableObject.CreateInstance<SfxLibrary>();
            AssetDatabase.CreateAsset(library, LibraryPath);
            return library;
        }

        // Every AudioClip under 'folder' (recursive), with its file name.
        private static List<(string, AudioClip)> Clips(string folder)
        {
            var result = new List<(string, AudioClip)>();
            if (!AssetDatabase.IsValidFolder(folder)) return result;
            foreach (string guid in AssetDatabase.FindAssets("t:AudioClip", new[] { folder }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                var clip = AssetDatabase.LoadAssetAtPath<AudioClip>(path);
                if (clip != null) result.Add((Path.GetFileNameWithoutExtension(path), clip));
            }
            result.Sort((a, b) => string.CompareOrdinal(a.Item1, b.Item1));
            return result;
        }

        private static AudioClip[] Matching(List<(string name, AudioClip clip)> clips, string prefix)
        {
            var result = new List<AudioClip>();
            foreach ((string name, AudioClip clip) in clips)
                if (MatchesPrefix(name, prefix))
                    result.Add(clip);
            return result.ToArray();
        }

        /// <summary>'name' is 'prefix' itself or 'prefix_' plus digits (punch_bonk_02), case-insensitive. So
        /// footstep_sand_03 is footstep_sand's, and van_door_open never catches van_door_open_slow.</summary>
        public static bool MatchesPrefix(string name, string prefix)
        {
            if (string.Equals(name, prefix, StringComparison.OrdinalIgnoreCase)) return true;
            if (name.Length <= prefix.Length + 1 || !name.StartsWith(prefix + "_", StringComparison.OrdinalIgnoreCase)) return false;
            for (int i = prefix.Length + 1; i < name.Length; i++)
                if (!char.IsDigit(name[i]))
                    return false;
            return true;
        }

        // Short one-shots: mono, decompressed on load (no decode at play time), ADPCM in memory, preloaded.
        private static void ApplyImportSettings(string assetPath)
        {
            if (AssetImporter.GetAtPath(assetPath) is not AudioImporter importer) return;
            AudioImporterSampleSettings settings = importer.defaultSampleSettings;
            bool changed = !importer.forceToMono || settings.loadType != AudioClipLoadType.DecompressOnLoad ||
                           settings.compressionFormat != AudioCompressionFormat.ADPCM || !settings.preloadAudioData;
            if (!changed) return;
            importer.forceToMono = true;
            settings.loadType = AudioClipLoadType.DecompressOnLoad;
            settings.compressionFormat = AudioCompressionFormat.ADPCM;
            settings.preloadAudioData = true;
            importer.defaultSampleSettings = settings;
            importer.SaveAndReimport();
        }

        private static bool IsLfsPointer(string file)
        {
            using var reader = new StreamReader(file);
            string first = reader.ReadLine();
            return first != null && first.StartsWith("version https://git-lfs", StringComparison.Ordinal);
        }
    }
}
