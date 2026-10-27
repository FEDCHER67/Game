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
            var clips = new AnimationClip[OperationEscape.Count];
            int missing = 0, copied = 0;
            var missingNames = new List<string>();
            for (int i = 0; i < OperationEscape.Count; i++)
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
            for (int i = 0; i < OperationEscape.Count; i++)
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
