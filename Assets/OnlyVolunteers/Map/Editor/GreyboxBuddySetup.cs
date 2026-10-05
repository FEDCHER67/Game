using System.Collections.Generic;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;

namespace OnlyVolunteers.Map
{
    // Turns the Sausage Buddy FBX exports (copied from ArtSource/Characters/SAUSAGE_BUDDY_01) into grey-box prefabs:
    // named looping clips, one Animator Controller (Idle / Run / TurnFlee) and a prefab per variant.
    public static class GreyboxBuddySetup
    {
        private const string Dir = "Assets/OnlyVolunteers/Characters/SausageBuddy";
        private const string ControllerPath = Dir + "/SausageBuddy_Greybox.controller";
        private static readonly string[] Variants = { "A", "B" };

        public static GameObject[] EnsurePrefabs()
        {
            foreach (string v in Variants)
                ConfigureImporter(FbxPath(v));
            AnimatorController controller = BuildController(FbxPath("A"));
            var prefabs = new List<GameObject>();
            foreach (string v in Variants)
            {
                var root = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(FbxPath(v)));
                PrefabUtility.UnpackPrefabInstance(root, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
                root.name = $"SausageBuddy_{v}";
                if (!root.TryGetComponent(out Animator animator))
                    animator = root.AddComponent<Animator>();
                animator.runtimeAnimatorController = controller;
                animator.applyRootMotion = false;
                // The FBX rest pose sits ~11 m below the root, so culled Animators never move the bones into view.
                animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
                prefabs.Add(PrefabUtility.SaveAsPrefabAsset(root, $"{Dir}/SausageBuddy_{v}.prefab"));
                Object.DestroyImmediate(root);
            }
            return prefabs.ToArray();
        }

        private static string FbxPath(string variant) => $"{Dir}/SAUSAGE_BUDDY_{variant}_v04.fbx";

        private static void ConfigureImporter(string path)
        {
            var importer = (ModelImporter)AssetImporter.GetAtPath(path);
            // Without a generic Avatar the Animator cannot bind the clips and the skin collapses at the rest pose.
            importer.animationType = ModelImporterAnimationType.Generic;
            importer.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
            var clips = new List<ModelImporterClipAnimation>();
            foreach (ModelImporterClipAnimation clip in importer.defaultClipAnimations)
            {
                // The Mixamo source take keeps the original rig far from the origin; the Buddy's own clips do not.
                if (clip.takeName.Contains("mixamo.com")) continue;
                clip.name = clip.takeName.Substring(clip.takeName.LastIndexOf('|') + 1);
                clip.loopTime = clip.name == "Idle" || clip.name == "Panic_Run_Loop";
                clips.Add(clip);
            }
            importer.clipAnimations = clips.ToArray();
            importer.SaveAndReimport();
        }

        private static AnimatorController BuildController(string fbx)
        {
            // Reuse the asset: deleting and recreating it in the same pass left prefabs pointing at a dead controller.
            AnimatorController controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath)
                ?? AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            AnimatorStateMachine machine = controller.layers[0].stateMachine;
            foreach (ChildAnimatorState child in machine.states)
                machine.RemoveState(child.state);
            var clips = new Dictionary<string, AnimationClip>();
            foreach (Object asset in AssetDatabase.LoadAllAssetsAtPath(fbx))
                if (asset is AnimationClip clip && !clip.name.StartsWith("__preview"))
                    clips[clip.name] = clip;
            AnimatorState idle = machine.AddState("Idle");
            idle.motion = clips["Idle"];
            machine.AddState("Run").motion = clips["Panic_Run_Loop"];
            machine.AddState("TurnFlee").motion = clips["Panic_TurnFlee"];
            machine.defaultState = idle;
            EditorUtility.SetDirty(controller);
            AssetDatabase.SaveAssets();
            return controller;
        }
    }
}
