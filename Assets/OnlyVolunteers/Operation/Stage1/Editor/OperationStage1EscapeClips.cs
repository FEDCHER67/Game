using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Round 4: one click wires the Escape_v01 clips (docs/reviews/escape_anims_v01/CONTRACT.md) into gameplay:
    /// copies the FBX from ArtSource into Assets, imports them like the Operation_v01 clips (Generic, Copy From Other Avatar =
    /// the avatar of Op_Dead_v01, Preserve Hierarchy as Op_Dead_v01, compression Off, Loop Time only on *_Loop_v01), adds one state per clip to
    /// Patient_Operation.controller (state name = OperationEscape.Clips[i].name, no transitions: the presentation enters
    /// them directly) and switches the stage-1 tuning to the clip-driven escape (escapeClips, escapeMissingClips).
    /// Clips that are not in ArtSource (the v01b FBX need a local bpy rebuild, see the contract) are listed as missing; the
    /// gameplay then uses his right exit and Esc_Slump_Sit. Run it again after rebuilding them. Never overwrites a copy.</summary>
    public static class OperationStage1EscapeClips
    {
        public const string Source = "ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_v01/";
        public const string Target = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Escape_v01";
        private const string Template = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Op_Dead_v01.fbx";
        private const string TuningPath = "Assets/OnlyVolunteers/Operation/Stage1/Data/OperationStage1_v02.asset";

        [MenuItem("OnlyVolunteers/Operation/Integrate escape clips v01 (Escape_v01 -> Patient_Operation)")]
        public static void Menu() => Debug.Log("[OPS] " + Integrate());

        public static string Integrate()
        {
            var template = AssetImporter.GetAtPath(Template) as ModelImporter;
            if (template == null || template.sourceAvatar == null) return "template importer/avatar missing: " + Template;
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(OperationStage1BuilderV02.ControllerPath);
            if (controller == null) return "controller missing: " + OperationStage1BuilderV02.ControllerPath;
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(TuningPath);
            if (tuning == null) return "tuning missing: " + TuningPath;
            if (!AssetDatabase.IsValidFolder(Target)) AssetDatabase.CreateFolder(Path.GetDirectoryName(Target).Replace('\\', '/'), Path.GetFileName(Target));

            string root = Path.GetDirectoryName(Application.dataPath);
            var clips = new AnimationClip[OperationEscape.V01Count];
            int missing = 0, copied = 0;
            var missingNames = new List<string>();
            for (int i = 0; i < OperationEscape.V01Count; i++) // K10: the panic v02 variants have their own menu item below
            {
                string file = OperationEscape.Clips[i].name + "_v01.fbx";
                string asset = Target + "/" + file;
                string source = Path.Combine(root, Source + file);
                if (!File.Exists(Path.Combine(root, asset)))
                {
                    // An LFS pointer (not pulled) is a few hundred bytes of text, never a clip.
                    if (!File.Exists(source) || new FileInfo(source).Length < 1024) { missing |= 1 << i; missingNames.Add(OperationEscape.Clips[i].name); continue; }
                    File.Copy(source, Path.Combine(root, asset));
                    AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
                    copied++;
                }
                Configure(asset, template, OperationEscape.Clips[i]);
                foreach (var o in AssetDatabase.LoadAllAssetsAtPath(asset))
                    if (o is AnimationClip c && !c.name.StartsWith("__preview__")) { clips[i] = c; break; }
                if (clips[i] == null) { missing |= 1 << i; missingNames.Add(OperationEscape.Clips[i].name); }
            }

            var sm = controller.layers[0].stateMachine;
            bool writeDefaults = true;
            foreach (var child in sm.states) if (child.state.name == "TableAwake") writeDefaults = child.state.writeDefaultValues;
            int added = 0;
            for (int i = 0; i < OperationEscape.V01Count; i++)
            {
                if (clips[i] == null) continue;
                string name = OperationEscape.Clips[i].name;
                AnimatorState state = null;
                foreach (var child in sm.states) if (child.state.name == name) state = child.state;
                if (state == null) { state = sm.AddState(name, new Vector3(300 + (i % 5) * 230, 420 + (i / 5) * 70, 0)); added++; }
                state.motion = clips[i];
                state.speed = 1f; // gameplay sets Animator.speed = tuning.escapeSpeed while an escape clip plays
                state.writeDefaultValues = writeDefaults;
            }
            EditorUtility.SetDirty(controller);

            // The core chain (his right exit) must be complete; the left side, the edge slumps and the stumbles are optional.
            int core = (1 << OperationEscape.UnbuckleArmRByL) | (1 << OperationEscape.UnbuckleArmLByR) | (1 << OperationEscape.SitUp) |
                (1 << OperationEscape.UnbuckleLegL) | (1 << OperationEscape.UnbuckleLegR) | (1 << OperationEscape.UnbuckleLegsBoth) |
                (1 << OperationEscape.SwingOffR) | (1 << OperationEscape.HopRunR) | (1 << OperationEscape.SlumpSit) |
                (1 << OperationEscape.SlumpLieReachR) | (1 << OperationEscape.SlumpLieReachL);
            tuning.escapeMissingClips = missing;
            tuning.escapeClips = (missing & core) == 0;
            EditorUtility.SetDirty(tuning);
            AssetDatabase.SaveAssets();
            return $"escape clips v01: {copied} copied, {added} states added, escapeClips={tuning.escapeClips}, escapeSpeed={tuning.escapeSpeed}, " +
                   $"missing [{string.Join(", ", missingNames)}]";
        }

        // ---------- K10 (Fedya 29.10): the panic v02 variants ----------

        public const string PanicManifest = "escape_clips_manifest_v02.json";
        public const string PanicSource = "ArtSource/Characters/SAUSAGE_BUDDY_01/Animations/Escape_Panic_v02/";
        public const string PanicTarget = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Escape_Panic_v02";

        [MenuItem("OnlyVolunteers/Operation/Integrate escape panic clips v02 (K10: Escape_v01/*_Panic_v02 -> Patient_Operation)")]
        public static void PanicMenu() => Debug.Log("[OPS] " + IntegratePanic(false));

        /// <summary>K10: wires the panic v02 variants (the Blender agent's *_Panic_v02 / *_BellyClutch_v02 FBX next to the v01 ones in
        /// ArtSource, escape_clips_manifest_v02.json) exactly like the v01 clips: copied into the same Assets folder, imported
        /// with the Op_Dead_v01 avatar, one state each in Patient_Operation.controller named OperationEscape.Clips[id].name
        /// ("&lt;v01 name&gt;_Panic" / "_BellyClutch"); then the tuning gets which variants exist (escapePanicMissing) and their
        /// authored timings (escapePanicTiming: duration and StrapOpen times from the manifest, else the clip length with the
        /// v01 StrapOpen times scaled to it). Missing variants stay v01 in gameplay. dryRun: only report what would be wired.
        /// Never overwrites a copy.</summary>
        public static string IntegratePanic(bool dryRun)
        {
            var template = AssetImporter.GetAtPath(Template) as ModelImporter;
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(OperationStage1BuilderV02.ControllerPath);
            var tuning = AssetDatabase.LoadAssetAtPath<OperationTuning>(TuningPath);
            if (!dryRun && (template == null || template.sourceAvatar == null || controller == null || tuning == null)) return "template / controller / tuning missing";
            string root = Path.GetDirectoryName(Application.dataPath);
            string sourceDir = Path.Combine(root, PanicSource);
            string manifestPath = Path.Combine(sourceDir, PanicManifest);
            if (!dryRun && !AssetDatabase.IsValidFolder(PanicTarget))
                AssetDatabase.CreateFolder(Path.GetDirectoryName(PanicTarget).Replace('\\', '/'), Path.GetFileName(PanicTarget));
            string manifest = File.Exists(manifestPath) ? File.ReadAllText(manifestPath) : null;
            var files = Directory.Exists(sourceDir) ? Directory.GetFiles(sourceDir, "*_v02.fbx") : new string[0];
            int missing = 0, copied = 0, added = 0;
            var timing = new float[OperationEscape.PanicCount * 3];
            var found = new List<string>(); var missingNames = new List<string>();
            var sm = controller != null ? controller.layers[0].stateMachine : null;
            bool writeDefaults = true;
            if (sm != null) foreach (var child in sm.states) if (child.state.name == "TableAwake") writeDefaults = child.state.writeDefaultValues;
            for (int k = 0; k < OperationEscape.PanicCount; k++)
            {
                int id = OperationEscape.FirstPanic + k;
                var clip = OperationEscape.Clips[id];
                var v01 = OperationEscape.Clips[OperationEscape.BaseOf(id)];
                string file = FindPanicFile(files, v01.name, OperationEscape.IsHopRun(id));
                if (file == null || new FileInfo(file).Length < 1024) { missing |= 1 << k; missingNames.Add(clip.name); continue; }
                string fileName = Path.GetFileName(file);
                found.Add(clip.name + " <- " + fileName);
                if (dryRun) continue;
                string asset = PanicTarget + "/" + fileName;
                if (!File.Exists(Path.Combine(root, asset)))
                {
                    File.Copy(file, Path.Combine(root, asset));
                    AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
                    copied++;
                }
                Configure(asset, template, clip);
                AnimationClip motion = null;
                foreach (var o in AssetDatabase.LoadAllAssetsAtPath(asset))
                    if (o is AnimationClip c && !c.name.StartsWith("__preview__")) { motion = c; break; }
                if (motion == null) { missing |= 1 << k; missingNames.Add(clip.name + " (no take)"); continue; }
                AnimatorState state = null;
                foreach (var child in sm.states) if (child.state.name == clip.name) state = child.state;
                if (state == null) { state = sm.AddState(clip.name, new Vector3(300 + (k % 5) * 230, 700 + (k / 5) * 70, 0)); added++; }
                state.motion = motion; state.speed = 1f; state.writeDefaultValues = writeDefaults;
                // Timings: the manifest entry of this file, else the imported length with the v01 StrapOpen times scaled to it.
                float seconds = ManifestNumber(manifest, Path.GetFileNameWithoutExtension(fileName), "duration_s");
                if (seconds <= 0.05f) seconds = motion.length;
                float scale = seconds / Mathf.Max(0.01f, v01.seconds);
                float openA = ManifestStrapOpen(manifest, Path.GetFileNameWithoutExtension(fileName), v01.strapA);
                float openB = ManifestStrapOpen(manifest, Path.GetFileNameWithoutExtension(fileName), v01.strapB);
                timing[k * 3] = seconds;
                timing[k * 3 + 1] = v01.strapA >= 0 ? (openA > 0f ? openA : v01.openA * scale) : 0f;
                timing[k * 3 + 2] = v01.strapB >= 0 ? (openB > 0f ? openB : v01.openB * scale) : 0f;
            }
            // The doomed runner's field run loop: imported the same way, not a table state (CaptureNpc plays it on the field NPC).
            string runFile = Path.Combine(sourceDir, OperationEscape.RunClutchLoop + "_v02.fbx");
            AnimationClip runLoop = null;
            if (File.Exists(runFile) && new FileInfo(runFile).Length >= 1024)
            {
                found.Add(OperationEscape.RunClutchLoop + " <- " + Path.GetFileName(runFile) + " (field run)");
                if (!dryRun)
                {
                    string asset = PanicTarget + "/" + Path.GetFileName(runFile);
                    if (!File.Exists(Path.Combine(root, asset)))
                    {
                        File.Copy(runFile, Path.Combine(root, asset));
                        AssetDatabase.ImportAsset(asset, ImportAssetOptions.ForceSynchronousImport);
                        copied++;
                    }
                    Configure(asset, template, new OperationEscape.Clip { name = OperationEscape.RunClutchLoop, loop = true });
                    foreach (var o in AssetDatabase.LoadAllAssetsAtPath(asset))
                        if (o is AnimationClip c && !c.name.StartsWith("__preview__")) { runLoop = c; break; }
                }
            }
            else missingNames.Add(OperationEscape.RunClutchLoop + " (field run: procedural clutch on his run)");
            if (!dryRun)
            {
                EditorUtility.SetDirty(controller);
                tuning.escapePanicMissing = missing;
                tuning.escapePanicTiming = timing;
                tuning.escapeRunClutchClip = runLoop;
                EditorUtility.SetDirty(tuning);
                AssetDatabase.SaveAssets();
            }
            return $"escape panic clips v02{(dryRun ? " (dry run)" : "")}: manifest={(manifest != null)}, {found.Count} found, {copied} copied, " +
                   $"{added} states added; found [{string.Join("; ", found)}]; missing (v01 used) [{string.Join(", ", missingNames)}]";
        }

        /// <summary>The v02 FBX of a panic variant: starts with the v01 name (without "_Loop"), says Panic (HopRun: BellyClutch).</summary>
        private static string FindPanicFile(string[] files, string v01Name, bool hopRun)
        {
            string stem = v01Name.Replace("_Loop", "");
            foreach (string f in files)
            {
                string n = Path.GetFileName(f);
                if (!n.StartsWith(stem + "_") || !n.EndsWith("_v02.fbx")) continue;
                if (n.Contains(hopRun ? "BellyClutch" : "Panic")) return f;
            }
            return null;
        }

        private const string Q = "\"";
        private const string NumberAfterColon = @"\s*:\s*([0-9.eE+-]+)";

        /// <summary>The span of one clip entry ("name": { ... }) in the manifest text, or null.</summary>
        private static string ManifestEntry(string manifest, string clipName)
        {
            if (string.IsNullOrEmpty(manifest)) return null;
            // The entry itself ("name": {), inside "clips": the chaining notes and "next" lists mention names too.
            int clips = manifest.IndexOf(Q + "clips" + Q, System.StringComparison.Ordinal);
            var key = new System.Text.RegularExpressions.Regex(System.Text.RegularExpressions.Regex.Escape(Q + clipName + Q) + @"\s*:\s*\{");
            var hit = key.Match(manifest, Mathf.Max(0, clips));
            if (!hit.Success) return null;
            int open = hit.Index + hit.Length - 1;
            int depth = 0;
            for (int i = open; i < manifest.Length; i++)
            {
                if (manifest[i] == '{') depth++;
                else if (manifest[i] == '}' && --depth == 0) return manifest.Substring(open, i - open + 1);
            }
            return null;
        }
        private static float ManifestNumber(string manifest, string clipName, string key)
        {
            string entry = ManifestEntry(manifest, clipName);
            if (entry == null) return -1f;
            var m = System.Text.RegularExpressions.Regex.Match(entry, Q + key + Q + NumberAfterColon);
            return m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v) ? v : -1f;
        }
        /// <summary>The "t" of the StrapOpen event of a strap (0 arm L, 1 arm R, 2 leg L, 3 leg R) in a manifest entry.</summary>
        private static float ManifestStrapOpen(string manifest, string clipName, int strap)
        {
            if (strap < 0) return -1f;
            string entry = ManifestEntry(manifest, clipName);
            if (entry == null) return -1f;
            string strapName = strap == 0 ? "STRAP_ARM_L" : strap == 1 ? "STRAP_ARM_R" : strap == 2 ? "STRAP_LEG_L" : "STRAP_LEG_R";
            foreach (System.Text.RegularExpressions.Match e in System.Text.RegularExpressions.Regex.Matches(entry, @"\{[^{}]*\}"))
            {
                string ev = e.Value;
                if (!ev.Contains(Q + "StrapOpen" + Q) || !ev.Contains(Q + strapName + Q)) continue;
                var m = System.Text.RegularExpressions.Regex.Match(ev, Q + "t" + Q + NumberAfterColon);
                if (m.Success && float.TryParse(m.Groups[1].Value, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out float v)) return v;
            }
            return -1f;
        }

        private static void Configure(string asset, ModelImporter template, OperationEscape.Clip clip)
        {
            var importer = AssetImporter.GetAtPath(asset) as ModelImporter;
            if (importer == null) return;
            // W86 fix: the Escape_v01 FBX hold only the armature, a single root. Without preserveHierarchy Unity made that
            // armature the model root, so the curve paths lost their "Buddy_Rig_Mixamo65/" prefix: on the patient the
            // armature's own keys (scale 100, -90 deg X) moved the Animator object and no bone was animated (the escape
            // was never seen). The Op_*_v01 clips keep the armature as a child; so must these.
            bool dirty = importer.animationType != template.animationType || importer.avatarSetup != template.avatarSetup ||
                importer.sourceAvatar != template.sourceAvatar || importer.animationCompression != ModelImporterAnimationCompression.Off ||
                importer.preserveHierarchy != template.preserveHierarchy ||
                importer.importAnimation == false || importer.clipAnimations == null || importer.clipAnimations.Length != 1 ||
                importer.clipAnimations[0].name != clip.name || importer.clipAnimations[0].loopTime != clip.loop;
            if (!dirty) return;
            importer.animationType = template.animationType;
            importer.avatarSetup = template.avatarSetup;
            importer.sourceAvatar = template.sourceAvatar;
            importer.preserveHierarchy = template.preserveHierarchy;
            importer.importAnimation = true;
            importer.animationCompression = ModelImporterAnimationCompression.Off;
            importer.SaveAndReimport();
            var defaults = importer.defaultClipAnimations;
            if (defaults == null || defaults.Length == 0) return;
            var take = defaults[0];
            take.name = clip.name;
            take.loopTime = clip.loop;
            take.lockRootRotation = false; take.lockRootHeightY = false; take.lockRootPositionXZ = false;
            importer.clipAnimations = new[] { take };
            importer.SaveAndReimport();
        }
    }
}
