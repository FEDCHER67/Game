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
    // 2) "Refill library": for every event, the first folder that has clips for it wins:
    //    Assets/OnlyVolunteers/Audio/Library_v1 (recorded sounds named <event id>_NN, any subfolder; LICENSES.md there),
    //    then Assets/OnlyVolunteers/Audio/Final (file name = the prefix below, or prefix_NN), then the SFX_GEN placeholders.
    //    Library_v1 clips get their import settings here (loops in world/ and vehicle/, and the siren: Vorbis compressed in memory; the
    //    rest: one-shots decompressed on load, Vorbis 0.8). Entries keep hand-tuned volume/pitch/3D settings; Locked
    //    entries also keep their clips. Missing entries are made with the defaults below. The library is
    //    Audio/Resources/SfxLibrary.asset (Sfx loads it from Resources).
    // 3) "Refill library + reset tuning": 2), then every entry's volume, pitch, 3D, cooldown and priority back to the
    //    defaults below (after a retune of this table; it overwrites hand tuning).
    // 24 Library_v1 files hold Mixkit audio and stay out of git (.gitignore): on a clone without them those ids simply
    // have fewer clips.
    public static class SfxLibraryImporter
    {
        private const string SourceDir = "ArtSource/Audio/SFX_GEN/Out/v01";
        private const string AudioRoot = "Assets/OnlyVolunteers/Audio";
        private const string PlaceholderDir = AudioRoot + "/SFX_GEN";
        private const string FinalDir = AudioRoot + "/Final";
        private const string RecordedDir = AudioRoot + "/Library_v1";
        private const string VehicleDir = RecordedDir + "/vehicle";
        private const string LibraryPath = AudioRoot + "/Resources/SfxLibrary.asset";

        private readonly struct Def
        {
            public readonly string Id, Prefix;
            public readonly Vector2 Volume, Pitch;
            public readonly float MinDistance, MaxDistance, SpatialBlend, Cooldown;
            public readonly int Priority;
            public readonly string RecordedFolder;
            public readonly bool Loop;

            public Def(string id, string prefix, float volume, float pitchLow, float pitchHigh, float minDistance, float maxDistance,
                       float cooldown, int priority, float spatialBlend = 1f, string recordedFolder = null, bool loop = false)
            {
                Id = id;
                Prefix = prefix;
                Volume = new Vector2(volume * 0.85f, volume);
                Pitch = new Vector2(pitchLow, pitchHigh);
                MinDistance = minDistance;
                MaxDistance = maxDistance;
                SpatialBlend = spatialBlend;
                Cooldown = cooldown;
                Priority = priority;
                RecordedFolder = recordedFolder;
                Loop = loop;
            }
        }

        // id, SFX_GEN/Final file prefix, volume, pitch range, min/max distance, cooldown, priority (0 most important), 2D/3D.
        // Tuned for Library_v1 (2026-10-07): Library_v1 files are loudness-matched per group (hits about -13, voices -15,
        // doors -18..-21, slaps -21, steps -22..-25 LUFS short-term), so these volumes balance the groups. Pitch: small
        // spread for steps and hits, brighter for NPC voices (1.0-1.12, the comedy pass). Rolloff is logarithmic: at
        // MinDistance full volume, at 2x half (-6 dB) and so on; beyond MaxDistance it stops falling.
        private static readonly Def[] Events =
        {
            new(SfxIds.HitHead, "punch_bonk", 0.85f, 0.95f, 1.05f, 2f, 30f, 0.05f, 40),
            new(SfxIds.HitTorso, "punch_bonk", 0.8f, 0.92f, 1.02f, 2f, 30f, 0.05f, 40),
            new(SfxIds.HitLimb, "slap", 1f, 0.95f, 1.08f, 2f, 25f, 0.05f, 45),
            new(SfxIds.ThudGround, "body_thud_ground", 0.9f, 0.92f, 1.06f, 2f, 28f, 0.12f, 70),
            new(SfxIds.ThudVan, "body_thud_van_floor", 0.9f, 0.92f, 1.06f, 2f, 28f, 0.12f, 70),
            new(SfxIds.DoorFrontOpen, "van_door_open", 0.85f, 0.97f, 1.03f, 2f, 25f, 0.1f, 60),
            new(SfxIds.DoorFrontClose, "van_door_close", 0.9f, 0.97f, 1.03f, 2f, 30f, 0.1f, 60),
            new(SfxIds.DoorFrontSlam, "van_door_slam", 1f, 0.95f, 1.05f, 3f, 40f, 0.1f, 55),
            new(SfxIds.DoorRearOpen, "rear_door_open", 0.85f, 0.97f, 1.03f, 2f, 25f, 0.1f, 60),
            new(SfxIds.DoorRearClose, "rear_door_close", 0.9f, 0.97f, 1.03f, 2f, 30f, 0.1f, 60),
            new(SfxIds.DoorRearSlam, "van_door_slam", 1f, 0.95f, 1.03f, 3f, 40f, 0.1f, 55),
            new(SfxIds.DoorSlideOpen, "slide_door_open", 0.9f, 0.98f, 1.02f, 2f, 30f, 0.1f, 60),
            new(SfxIds.DoorSlideClose, "slide_door_close", 0.95f, 0.98f, 1.02f, 2f, 30f, 0.1f, 60),
            new(SfxIds.VanEngineIdle, "van_engine_idle", 1f, 1f, 1f, 4f, 40f, 0f, 70, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanEngineLow, "van_engine_low", 1f, 1f, 1f, 4f, 40f, 0f, 70, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanEngineHigh, "van_engine_high", 1f, 1f, 1f, 4f, 40f, 0f, 70, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanDriveDirt, "van_drive_dirt", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanDriveGrass, "van_drive_grass", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanBodyRattle, "van_body_rattle", 0.85f, 0.95f, 1.05f, 4f, 40f, 0.35f, 75, recordedFolder: VehicleDir),
            new(SfxIds.VanEngineStart, "van_engine_start", 0.9f, 0.98f, 1.02f, 4f, 40f, 0f, 65, recordedFolder: VehicleDir),
            new(SfxIds.VanEngineStop, "van_engine_stop", 0.9f, 0.98f, 1.02f, 4f, 40f, 0f, 65, recordedFolder: VehicleDir),
            new(SfxIds.VanHandbrake, "van_handbrake", 0.85f, 0.97f, 1.03f, 4f, 40f, 0.2f, 75, recordedFolder: VehicleDir),
            new(SfxIds.PoliceEngineIdle, "police_engine_idle", 1f, 1f, 1f, 4f, 60f, 0f, 60, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.PoliceEngineLow, "police_engine_low", 1f, 1f, 1f, 4f, 60f, 0f, 60, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.PoliceEngineHigh, "police_engine_high", 1f, 1f, 1f, 4f, 60f, 0f, 60, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.PoliceEngineStart, "police_engine_start", 0.9f, 0.98f, 1.02f, 4f, 60f, 0f, 55, recordedFolder: VehicleDir),
            new(SfxIds.VanTireSkid, "van_tire_skid", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanTireChirp, "van_tire_chirp", 0.85f, 0.97f, 1.04f, 4f, 40f, 0.8f, 75, recordedFolder: VehicleDir),
            new(SfxIds.VanBrakeSqueak, "van_brake_squeak", 0.7f, 0.98f, 1.03f, 4f, 40f, 0.2f, 75, recordedFolder: VehicleDir),
            new(SfxIds.VanHitMetalLight, "van_hit_metal_light", 0.85f, 0.96f, 1.04f, 3f, 45f, 0.05f, 55, recordedFolder: VehicleDir),
            new(SfxIds.VanHitMetalHeavy, "van_hit_metal_heavy", 0.95f, 0.94f, 1.03f, 4f, 55f, 0.05f, 45, recordedFolder: VehicleDir),
            new(SfxIds.VanHitWood, "van_hit_wood", 0.85f, 0.95f, 1.05f, 3f, 45f, 0.05f, 55, recordedFolder: VehicleDir),
            new(SfxIds.VanHitConcrete, "van_hit_concrete", 0.9f, 0.94f, 1.03f, 4f, 50f, 0.05f, 50, recordedFolder: VehicleDir),
            new(SfxIds.VanHitPlastic, "van_hit_plastic", 0.7f, 0.97f, 1.06f, 2f, 30f, 0.05f, 70, recordedFolder: VehicleDir),
            new(SfxIds.VanHitGlass, "van_hit_glass", 0.85f, 0.97f, 1.04f, 3f, 40f, 0.05f, 60, recordedFolder: VehicleDir),
            new(SfxIds.VanHitFoliage, "van_hit_foliage", 0.55f, 0.96f, 1.06f, 2f, 25f, 0.05f, 80, recordedFolder: VehicleDir),
            // The player's own feet are ~1.7 m under the listener: MinDistance 2 plays them at full volume.
            new(SfxIds.StepAsphalt, "footstep_asphalt", 0.40f, 0.95f, 1.06f, 2f, 20f, 0.15f, 150),
            new(SfxIds.StepGrass, "footstep_grass", 0.42f, 0.95f, 1.06f, 2f, 18f, 0.15f, 150),
            new(SfxIds.StepSand, "footstep_sand", 0.42f, 0.95f, 1.06f, 2f, 18f, 0.15f, 150),
            new(SfxIds.StepMetal, "footstep_metal_floor", 0.45f, 0.95f, 1.06f, 2f, 20f, 0.15f, 150),
            new(SfxIds.NpcScream, "npc_scream", 0.9f, 1f, 1.1f, 3f, 50f, 0.3f, 50),
            new(SfxIds.NpcMumble, "npc_mumble_gibberish", 0.6f, 1f, 1.12f, 1.5f, 15f, 0.2f, 110),
            new(SfxIds.NpcWhimper, "npc_whimper", 0.55f, 1f, 1.12f, 1.5f, 15f, 0.2f, 110),
            new(SfxIds.NpcGasp, "npc_gasp", 0.7f, 1f, 1.12f, 2f, 20f, 0.2f, 100),
            new(SfxIds.NpcHurt, "npc_hurt", 0.75f, 1f, 1.12f, 2f, 25f, 0.15f, 60),
            new(SfxIds.OrganSquish, "organ_squish", 0.9f, 0.92f, 1.08f, 1.5f, 15f, 0.05f, 60),
            new(SfxIds.PoliceSiren, "police_siren_short", 1f, 1f, 1f, 6f, 160f, 0.5f, 30), // clip only: PoliceUnit loops it on its own AudioSource
            new(SfxIds.PoliceWhistle, "police_whistle", 0.85f, 0.98f, 1.03f, 4f, 60f, 0.5f, 40),
            new(SfxIds.VanHorn, "van_horn", 0.9f, 1f, 1f, 5f, 80f, 0.5f, 40),
            new(SfxIds.PhoneBuzz, "phone_buzz", 0.8f, 1f, 1f, 1f, 10f, 0.3f, 30, 0f),
            new(SfxIds.CashRegister, "cash_register", 0.8f, 0.98f, 1.02f, 1f, 20f, 0.3f, 60, 0f),
            new(SfxIds.UiPickup, "ui_pickup", 0.6f, 0.97f, 1.03f, 1f, 10f, 0.05f, 30, 0f),
            new(SfxIds.UiError, "ui_error", 0.6f, 1f, 1f, 1f, 10f, 0.15f, 30, 0f),
            // Operation table (OperationSfx plays these on its own AudioSource; volume multiplies its call's volume).
            new(SfxIds.OperationStrap, "operation_strap", 1f, 0.95f, 1.05f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationTick, "operation_tick", 0.5f, 0.95f, 1.08f, 1f, 10f, 0.03f, 80, 0f),
            new(SfxIds.OperationSlit, "operation_slit", 1f, 0.95f, 1.08f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationYelp, "operation_yelp", 0.45f, 1f, 1.12f, 1f, 10f, 0.1f, 50, 0f),
            new(SfxIds.OperationBoing, "operation_boing", 0.7f, 0.95f, 1.08f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationPop, "operation_pop", 0.7f, 0.95f, 1.1f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationRip, "operation_rip", 0.9f, 0.95f, 1.05f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationTape, "operation_tape", 1f, 0.95f, 1.05f, 1f, 10f, 0.05f, 60, 0f),
            new(SfxIds.OperationCoolerLid, "operation_cooler_lid", 1f, 0.97f, 1.03f, 1f, 10f, 0.1f, 60, 0f),
            new(SfxIds.OperationHeartbeat, "operation_heartbeat", 0.6f, 0.98f, 1.02f, 1f, 10f, 0.2f, 70, 0f),
            new(SfxIds.VanSkidGravel, "van_skid_gravel", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanSkidGrass, "van_skid_grass", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanSkidSand, "van_skid_sand", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanSkidMud, "van_skid_mud", 1f, 1f, 1f, 4f, 40f, 0f, 80, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanGravelSpray, "van_gravel_spray", 0.85f, 0.96f, 1.04f, 4f, 40f, 0.12f, 85, recordedFolder: VehicleDir),
            new(SfxIds.StepWater, "step_water", 0.42f, 0.95f, 1.06f, 2f, 18f, 0.15f, 150, recordedFolder: RecordedDir + "/footsteps"),
            new(SfxIds.StepWaterRun, "step_water_run", 0.44f, 0.95f, 1.06f, 2f, 20f, 0.12f, 150, recordedFolder: RecordedDir + "/footsteps"),
            new(SfxIds.WaterWade, "water_wade", 1f, 1f, 1f, 3f, 30f, 0f, 110, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.AmbStream, "amb_stream", 1f, 1f, 1f, 5f, 70f, 0f, 160, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.AmbRiver, "amb_river", 1f, 1f, 1f, 6f, 90f, 0f, 160, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.AmbWaterfall, "amb_waterfall", 1f, 1f, 1f, 8f, 120f, 0f, 155, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.AmbLakeShore, "amb_lake_shore", 1f, 1f, 1f, 5f, 80f, 0f, 160, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.SplashSmall, "splash_small", 0.8f, 0.95f, 1.05f, 2f, 28f, 0.08f, 85, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.SplashBig, "splash_big", 0.9f, 0.95f, 1.05f, 3f, 45f, 0.1f, 75, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.WaterJumpIn, "water_jump_in", 0.9f, 0.96f, 1.04f, 3f, 45f, 0.1f, 80, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.WaterGetOut, "water_get_out", 0.8f, 0.96f, 1.04f, 2f, 28f, 0.1f, 100, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.WaterDrip, "water_drip", 0.65f, 0.95f, 1.05f, 2f, 18f, 0.06f, 140, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.SwimStroke, "swim_stroke", 0.8f, 0.95f, 1.05f, 2f, 25f, 0.12f, 110, recordedFolder: RecordedDir + "/water"),
            new(SfxIds.SwimLoop, "swim_loop", 1f, 1f, 1f, 2f, 30f, 0f, 110, recordedFolder: RecordedDir + "/world", loop: true),
            new(SfxIds.VanWaterEnter, "van_water_enter", 0.9f, 0.96f, 1.04f, 4f, 45f, 0.1f, 80, recordedFolder: VehicleDir),
            new(SfxIds.VanWaterDrive, "van_water_drive", 1f, 1f, 1f, 4f, 40f, 0f, 90, recordedFolder: VehicleDir, loop: true),
            new(SfxIds.VanPuddle, "van_puddle", 0.85f, 0.95f, 1.05f, 4f, 40f, 0.12f, 100, recordedFolder: VehicleDir),
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
        public static void Fill() => Fill(false);

        [MenuItem("OnlyVolunteers/Audio/Refill library + reset tuning to defaults")]
        public static void FillAndResetTuning() => Fill(true);

        private static void Fill(bool resetTuning)
        {
            SfxLibrary library = LoadOrCreateLibrary();
            ApplyRecordedImportSettings();
            List<(string name, AudioClip clip)> recorded = Clips(RecordedDir);
            List<(string name, AudioClip clip)> vehicle = Clips(VehicleDir);
            List<(string name, AudioClip clip)> placeholders = Clips(PlaceholderDir);
            List<(string name, AudioClip clip)> finals = Clips(FinalDir);
            Undo.RecordObject(library, "Fill SFX library");
            var report = new List<string>();
            foreach (Def def in Events)
            {
                SfxLibrary.Entry entry = library.Entries.Find(e => e != null && e.Id == def.Id);
                if (entry == null)
                {
                    entry = new SfxLibrary.Entry { Id = def.Id };
                    Tune(entry, def);
                    library.Entries.Add(entry);
                }
                else if (resetTuning)
                {
                    Tune(entry, def);
                }
                if (entry.Locked)
                {
                    report.Add($"{def.Id}: locked, {entry.Clips?.Length ?? 0} clips kept");
                    continue;
                }
                AudioClip[] clips = Matching(def.RecordedFolder == VehicleDir ? vehicle : recorded, def.Id);
                string from = "Library_v1", by = def.Id;
                if (clips.Length == 0)
                {
                    clips = Matching(finals, def.Prefix);
                    from = "Final";
                    by = def.Prefix;
                }
                if (clips.Length == 0)
                {
                    clips = Matching(placeholders, def.Prefix);
                    from = "SFX_GEN";
                }
                entry.Clips = clips;
                report.Add(clips.Length == 0 ? $"{def.Id}: NO CLIPS for '{def.Id}' / '{def.Prefix}'" : $"{def.Id}: {clips.Length} from {from} ({by})");
            }
            library.Rebuild();
            EditorUtility.SetDirty(library);
            AssetDatabase.SaveAssets();
            Debug.Log($"[Sfx] Library {LibraryPath}{(resetTuning ? " (tuning reset to defaults)" : "")}:\n" + string.Join("\n", report), library);
        }

        private static void Tune(SfxLibrary.Entry entry, Def def)
        {
            entry.Volume = def.Volume;
            entry.Pitch = def.Pitch;
            entry.SpatialBlend = def.SpatialBlend;
            entry.MinDistance = def.MinDistance;
            entry.MaxDistance = def.MaxDistance;
            entry.Cooldown = def.Cooldown;
            entry.Priority = def.Priority;
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

        // SFX_GEN placeholders, short one-shots: mono, decompressed on load (no decode at play time), ADPCM, preloaded.
        private static void ApplyImportSettings(string assetPath) =>
            SetImport(assetPath, true, AudioClipLoadType.DecompressOnLoad, AudioCompressionFormat.ADPCM, 1f, true, false);

        // Library_v1: ambience loops (world/) keep their channels (the fountains are mono files: point sources); the
        // siren and vehicle loops are mono. All loops use Vorbis 0.7 compressed in memory and load in the background. Every
        // other clip is a mono one-shot, decompressed on load from Vorbis 0.8: no ADPCM hiss on soft voices and steps.
        private static void ApplyRecordedImportSettings()
        {
            if (!AssetDatabase.IsValidFolder(RecordedDir)) return;
            int changed = 0;
            foreach (string guid in AssetDatabase.FindAssets("t:AudioClip", new[] { RecordedDir }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                bool ambience = path.Contains("/world/");
                bool siren = Path.GetFileName(path).StartsWith("police_siren", StringComparison.OrdinalIgnoreCase);
                bool vehicleLoop = false;
                if (path.StartsWith(VehicleDir + "/", StringComparison.OrdinalIgnoreCase))
                {
                    string name = Path.GetFileNameWithoutExtension(path);
                    foreach (Def def in Events)
                        if (def.Loop && MatchesPrefix(name, def.Id)) { vehicleLoop = true; break; }
                }
                bool done = ambience || siren || vehicleLoop
                    ? SetImport(path, siren || vehicleLoop, AudioClipLoadType.CompressedInMemory, AudioCompressionFormat.Vorbis, 0.7f, false, true)
                    : SetImport(path, true, AudioClipLoadType.DecompressOnLoad, AudioCompressionFormat.Vorbis, 0.8f, true, false);
                if (done) changed++;
            }
            if (changed > 0) Debug.Log($"[Sfx] Import settings set on {changed} clips in {RecordedDir}.");
        }

        // True when the importer had to change (and reimported the clip).
        private static bool SetImport(string assetPath, bool mono, AudioClipLoadType loadType, AudioCompressionFormat format,
                                      float quality, bool preload, bool loadInBackground)
        {
            if (AssetImporter.GetAtPath(assetPath) is not AudioImporter importer) return false;
            AudioImporterSampleSettings settings = importer.defaultSampleSettings;
            bool changed = importer.forceToMono != mono || importer.loadInBackground != loadInBackground ||
                           settings.loadType != loadType || settings.compressionFormat != format ||
                           settings.preloadAudioData != preload ||
                           (format == AudioCompressionFormat.Vorbis && Mathf.Abs(settings.quality - quality) > 0.005f);
            if (!changed) return false;
            importer.forceToMono = mono;
            importer.loadInBackground = loadInBackground;
            settings.loadType = loadType;
            settings.compressionFormat = format;
            settings.preloadAudioData = preload;
            if (format == AudioCompressionFormat.Vorbis) settings.quality = quality;
            importer.defaultSampleSettings = settings;
            importer.SaveAndReimport();
            return true;
        }

        private static bool IsLfsPointer(string file)
        {
            using var reader = new StreamReader(file);
            string first = reader.ReadLine();
            return first != null && first.StartsWith("version https://git-lfs", StringComparison.Ordinal);
        }
    }
}
