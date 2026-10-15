using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using FishNet.Managing;
using FishNet.Managing.Object;
using FishNet.Object;
using GameKit.Dependencies.Utilities;
using OnlyVolunteers.Clinic;
using OnlyVolunteers.Inventory;
using OnlyVolunteers.Network;
using OnlyVolunteers.Player;
using UnityEditor;
using UnityEditor.Animations;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace OnlyVolunteers.Operation.Stage1.Editor
{
    /// <summary>Builds operations stage 1 v02: patient / tool / merchandise prefabs, the placeholder gurney + instrument
    /// stand (until the props agent's OperatingTableAstra_v02 / InstrumentStand_v01 exist), the patient animator
    /// contract, a placeholder lying clip, the normal NetworkPlayer with NetworkInventory and the dev scene
    /// Operation_Net_Stage1_v02. G25's v01 files are left untouched.</summary>
    public static class OperationStage1BuilderV02
    {
        public const string Root = "Assets/OnlyVolunteers/Operation/Stage1";
        public const string Prefabs = Root + "/Prefabs";
        public const string Data = Root + "/Data";
        public const string Art = Root + "/Art";
        public const string Anim = Root + "/Animations";
        public const string ScenePath = "Assets/OnlyVolunteers/Scenes/Dev/Operation_Net_Stage1_v02.unity";
        public const string ControllerPath = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Patient_Operation.controller";
        public const string PatientFbx = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/SAUSAGE_BUDDY_PATIENT_v01.fbx";
        public const string PropsTable = Root + "/Prefabs/OperatingTableAstra_v02.prefab";
        public const string PropsIncisions = Root + "/Art/OperationIncisions_v01.fbx";
        public const string PropsTableRest = "Assets/OnlyVolunteers/Characters/SausageBuddy/Patient/Animations/Patient_TableRest_v01.fbx";
        private const string NetworkRoot = "Assets/OnlyVolunteers/Network/Prefabs/";
        private static readonly List<NetworkObject> made = new();
        private static readonly List<string> report = new();

        [MenuItem("OnlyVolunteers/Operation/Build Network Stage 1 v02")]
        public static void BuildMenu() => Debug.Log(Build());

        /// <summary>Edit-mode render of the table + posed patient from the CameraAnchor (layout check, no play mode).</summary>
        public static string Preview(string file, int width, int height)
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            var prior = SceneManager.GetActiveScene();
            SceneManager.SetActiveScene(scene);
            try
            {
                var light = new GameObject("Sun").AddComponent<Light>(); light.type = LightType.Directional; light.transform.rotation = Quaternion.Euler(52, -35, 0); light.intensity = 1.2f;
                var floor = GameObject.CreatePrimitive(PrimitiveType.Plane); floor.transform.localScale = Vector3.one * 2;
                string tablePath = File.Exists(PropsTable) ? PropsTable : Prefabs + "/Stage1_Table_Placeholder_v02.prefab";
                var table = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(tablePath), scene);
                var rest = FindDeep(table.transform, "PatientRest");
                var patient = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(Prefabs + "/Stage1_Patient_v02.prefab"), scene);
                patient.transform.SetPositionAndRotation(rest.position, rest.rotation);
                var animator = patient.GetComponentInChildren<Animator>();
                var clip = (animator.runtimeAnimatorController as AnimatorController).layers[0].stateMachine.states[0].state.motion as AnimationClip;
                clip.SampleAnimation(animator.gameObject, 0f);
                var anchor = FindDeep(table.transform, "CameraAnchor");
                var cam = new GameObject("Cam").AddComponent<Camera>(); cam.transform.SetPositionAndRotation(anchor.position, anchor.rotation); cam.fieldOfView = 50f;
                var rt = new RenderTexture(width, height, 24); cam.targetTexture = rt; cam.Render();
                var prev = RenderTexture.active; RenderTexture.active = rt;
                var tex = new Texture2D(width, height, TextureFormat.RGB24, false); tex.ReadPixels(new Rect(0, 0, width, height), 0, 0); tex.Apply();
                RenderTexture.active = prev; File.WriteAllBytes(file, tex.EncodeToPNG());
                cam.targetTexture = null; Object.DestroyImmediate(rt); Object.DestroyImmediate(tex);
                return "preview " + file + " clip=" + clip.name;
            }
            finally { SceneManager.SetActiveScene(prior); EditorSceneManager.CloseScene(scene, true); }
        }

        public static string Build()
        {
            if (EditorApplication.isPlaying || EditorApplication.isCompiling) throw new InvalidOperationException("Editor must be idle.");
            made.Clear(); report.Clear();
            foreach (var d in new[] { Prefabs, Data, Art, Anim, "Assets/OnlyVolunteers/Scenes/Dev" }) Directory.CreateDirectory(d);
            AssetDatabase.Refresh();
            var tuning = Tuning();
            var clip = TableRestClip();
            var controller = Controller(clip);
            var patient = BuildPatient(controller, clip);
            var bagModel = BagModel();
            var bagDefinition = BagDefinition(bagModel);
            var kidneyDef = AssetDatabase.LoadAssetAtPath<ItemDefinition>("Assets/OnlyVolunteers/Inventory/Items/Item_Kidney.asset");
            var liverDef = AssetDatabase.LoadAssetAtPath<ItemDefinition>("Assets/OnlyVolunteers/Inventory/Items/Item_Liver.asset");
            var merchandise = new[] { Merchandise("Stage1_Item_Kidney_v02", kidneyDef, tuning, 0.13f, true), Merchandise("Stage1_Item_Liver_v02", liverDef, tuning, 0.2f, false), Merchandise("Stage1_Item_BloodBag_v02", bagDefinition, tuning, 0.24f, false) };
            var tools = new[] { Tool("Stage1_Tool_Anesthesia_v02", OperationToolKind.Syringe), Tool("Stage1_Tool_Blood_v02", OperationToolKind.BloodSyringe), Tool("Stage1_Tool_Scalpel_v02", OperationToolKind.Scalpel) };
            var stand = Stand();
            var table = Table(tuning, patient, tools, merchandise, new[] { kidneyDef, liverDef, bagDefinition }, stand, bagModel, clip);
            PlayerPrefab();
            BuildScene(table);
            AssetDatabase.SaveAssets();
            report.Add("BUILT scene=" + ScenePath + " prefabs=" + made.Count);
            return string.Join("\n", report);
        }

        // ---------- data ----------
        private static OperationTuning Tuning()
        {
            string path = Data + "/OperationStage1_v02.asset";
            var fresh = ScriptableObject.CreateInstance<OperationTuning>();
            var existing = AssetDatabase.LoadAssetAtPath<OperationTuning>(path);
            if (existing == null) { AssetDatabase.CreateAsset(fresh, path); return fresh; }
            EditorUtility.CopySerialized(fresh, existing); EditorUtility.SetDirty(existing); Object.DestroyImmediate(fresh);
            return existing;
        }
        private static GameObject BagModel()
        {
            string path = Art + "/BLOOD_BAG_ASTRA_001_v04.fbx";
            if (!File.Exists(path))
            {
                File.Copy("ArtSource/Props/BLOOD-BAG-ASTRA-001/BLOOD_BAG_ASTRA_001_v04.fbx", path);
                AssetDatabase.ImportAsset(path, ImportAssetOptions.ForceSynchronousImport);
            }
            return AssetDatabase.LoadAssetAtPath<GameObject>(path);
        }
        private static ItemDefinition BagDefinition(GameObject model)
        {
            string path = Data + "/Item_BloodBagStage1_v02.asset";
            var item = AssetDatabase.LoadAssetAtPath<ItemDefinition>(path);
            if (item == null) { item = ScriptableObject.CreateInstance<ItemDefinition>(); AssetDatabase.CreateAsset(item, path); }
            var so = new SerializedObject(item);
            so.FindProperty("id").intValue = 110; so.FindProperty("displayName").stringValue = "Пакет крови"; so.FindProperty("shortLabel").stringValue = "КРВ";
            so.FindProperty("baseValue").intValue = 50; so.FindProperty("worldModel").objectReferenceValue = model; so.FindProperty("worldModelSize").floatValue = 0.24f;
            so.FindProperty("dropMass").floatValue = 0.5f;
            so.ApplyModifiedPropertiesWithoutUndo();
            return item;
        }

        // ---------- animation ----------
        private static Transform Bone(Transform root, string name) => root.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == "mixamorig:" + name);
        /// <summary>The props agent's TableRest clip when it exists, else a generated flat lying pose (head toward model -Z,
        /// face up, arms along the body) recorded as constant bone curves. The animation agent replaces clips later.</summary>
        private static AnimationClip TableRestClip()
        {
            if (File.Exists(PropsTableRest))
            {
                var c = AssetDatabase.LoadAllAssetsAtPath(PropsTableRest).OfType<AnimationClip>().FirstOrDefault(x => !x.name.StartsWith("__preview"));
                // Usable only when its curves bind to the patient's hierarchy (Buddy_Rig_Mixamo65/...), i.e. after the
                // props import settings (preserve hierarchy, copy avatar from A_v04) are applied.
                int bound = c != null ? AnimationUtility.GetCurveBindings(c).Count(b => b.path.StartsWith("Buddy_Rig_Mixamo65/mixamorig:Hips")) : 0;
                if (bound > 0) { report.Add("clip: props TableRest " + c.name + " bindings=" + bound); return c; }
                report.Add("clip: props TableRest present but does not bind to Buddy_Rig_Mixamo65/... (import settings pending) -> placeholder");
            }
            string path = Anim + "/Patient_TableRest_Placeholder_v01.anim";
            var model = (GameObject)Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(PatientFbx));
            try
            {
                PoseLying(model.transform);
                var clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(path);
                if (clip == null) { clip = new AnimationClip { name = "Patient_TableRest_Placeholder_v01" }; AssetDatabase.CreateAsset(clip, path); }
                clip.ClearCurves();
                var rig = model.transform.Find("Buddy_Rig_Mixamo65");
                foreach (var t in rig.GetComponentsInChildren<Transform>(true))
                {
                    if (!t.name.StartsWith("mixamorig:")) continue;
                    string p = AnimationUtility.CalculateTransformPath(t, model.transform);
                    var q = t.localRotation;
                    Set(clip, p, "m_LocalRotation.x", q.x); Set(clip, p, "m_LocalRotation.y", q.y); Set(clip, p, "m_LocalRotation.z", q.z); Set(clip, p, "m_LocalRotation.w", q.w);
                    if (t.name == "mixamorig:Hips")
                    { var v = t.localPosition; Set(clip, p, "m_LocalPosition.x", v.x); Set(clip, p, "m_LocalPosition.y", v.y); Set(clip, p, "m_LocalPosition.z", v.z); }
                }
                var settings = AnimationUtility.GetAnimationClipSettings(clip); settings.loopTime = true; AnimationUtility.SetAnimationClipSettings(clip, settings);
                EditorUtility.SetDirty(clip);
                report.Add("clip: generated placeholder " + path);
                return clip;
            }
            finally { Object.DestroyImmediate(model); }
        }
        private static void Set(AnimationClip clip, string path, string property, float value)
        {
            var curve = new AnimationCurve(new Keyframe(0f, value), new Keyframe(1f, value));
            AnimationUtility.SetEditorCurve(clip, EditorCurveBinding.FloatCurve(path, typeof(Transform), property), curve);
        }
        private static void PoseLying(Transform model)
        {
            var hips = Bone(model, "Hips");
            hips.rotation = Quaternion.Euler(-90f, 0f, 0f) * hips.rotation;
            hips.position = new Vector3(0f, 0.112f, 0f);
            var armL = Bone(model, "LeftArm"); var armR = Bone(model, "RightArm");
            armL.rotation = Quaternion.AngleAxis(9f, Vector3.right) * Quaternion.AngleAxis(81f, Vector3.up) * armL.rotation;
            armR.rotation = Quaternion.AngleAxis(9f, Vector3.right) * Quaternion.AngleAxis(-81f, Vector3.up) * armR.rotation;
            var foreL = Bone(model, "LeftForeArm"); var foreR = Bone(model, "RightForeArm");
            foreL.rotation = Quaternion.AngleAxis(-6f, Vector3.up) * foreL.rotation;
            foreR.rotation = Quaternion.AngleAxis(6f, Vector3.up) * foreR.rotation;
            var neck = Bone(model, "Neck");
            neck.rotation = Quaternion.AngleAxis(16f, Vector3.right) * neck.rotation;
            var legL = Bone(model, "LeftUpLeg"); var legR = Bone(model, "RightUpLeg");
            legL.rotation = Quaternion.AngleAxis(-3f, Vector3.up) * legL.rotation;
            legR.rotation = Quaternion.AngleAxis(3f, Vector3.up) * legR.rotation;
        }

        private static AnimatorController Controller(AnimationClip clip)
        {
            var controller = AssetDatabase.LoadAssetAtPath<AnimatorController>(ControllerPath);
            bool fresh = controller == null;
            if (fresh) controller = AnimatorController.CreateAnimatorControllerAtPath(ControllerPath);
            var layer = controller.layers[0];
            var sm = layer.stateMachine;
            if (!fresh && sm.states.Length >= 7)
            {
                // Keep the existing contract (the animation agent may have replaced clips); only fill empty motions.
                foreach (var s in sm.states)
                    if (s.state.motion == null || s.state.motion.name.Contains("TableRest")) s.state.motion = clip;
                EditorUtility.SetDirty(controller);
                return controller;
            }
            foreach (var p in controller.parameters.ToArray()) controller.RemoveParameter(p);
            controller.AddParameter("OpState", AnimatorControllerParameterType.Int);
            controller.AddParameter("ShockDeath", AnimatorControllerParameterType.Trigger);
            foreach (var s in sm.states.ToArray()) sm.RemoveState(s.state);
            foreach (var t in sm.anyStateTransitions.ToArray()) sm.RemoveAnyStateTransition(t);
            string[] names = { "TableAwake", "TableAsleep", "Struggle", "Panic", "Dead", "EscapeFall", "KnockedOut" };
            var states = new AnimatorState[names.Length];
            for (int i = 0; i < names.Length; i++)
            {
                states[i] = sm.AddState(names[i], new Vector3(300 + (i % 4) * 220, 60 + (i / 4) * 120, 0));
                states[i].motion = clip;
                var t = sm.AddAnyStateTransition(states[i]);
                t.AddCondition(AnimatorConditionMode.Equals, i, "OpState");
                t.duration = 0.15f; t.hasExitTime = false; t.canTransitionToSelf = false;
            }
            var shock = sm.AddAnyStateTransition(states[4]);
            shock.AddCondition(AnimatorConditionMode.If, 0, "ShockDeath");
            shock.duration = 0.1f; shock.hasExitTime = false; shock.canTransitionToSelf = false;
            sm.defaultState = states[6];
            EditorUtility.SetDirty(controller);
            report.Add("controller: " + ControllerPath + " OpState 0-6 + ShockDeath");
            return controller;
        }

        // ---------- prefabs ----------
        private static GameObject NetBody(string name)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(NetworkRoot + "NetworkPhysicsBody.prefab"));
            PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.Completely, InteractionMode.AutomatedAction);
            go.name = name;
            foreach (var r in go.GetComponentsInChildren<Renderer>()) Object.DestroyImmediate(r);
            foreach (var f in go.GetComponentsInChildren<MeshFilter>()) Object.DestroyImmediate(f);
            foreach (var c in go.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity); go.transform.localScale = Vector3.one;
            return go;
        }
        private static GameObject Save(GameObject go, string name)
        {
            string path = Prefabs + "/" + name + ".prefab";
            var nob = go.GetComponent<NetworkObject>();
            if (nob != null)
            {
                var hashText = new System.Text.StringBuilder();
                foreach (char c in (path + name).Trim().ToLowerInvariant()) if ((c >= 'a' && c <= 'z') || (c >= '0' && c <= '9')) hashText.Append(c);
                nob.SetAssetPathHash(hashText.ToString().GetStableHashU64());
            }
            var prefab = PrefabUtility.SaveAsPrefabAsset(go, path);
            if (prefab.TryGetComponent(out NetworkObject saved)) made.Add(saved);
            Object.DestroyImmediate(go);
            return prefab;
        }
        private static Bounds LocalBounds(Transform space, IEnumerable<Renderer> renderers)
        {
            bool any = false; var b = new Bounds();
            foreach (var r in renderers)
            {
                if (r == null || !r.enabled || !r.gameObject.activeInHierarchy) continue;
                Bounds w;
                if (r is SkinnedMeshRenderer skin)
                {
                    var mesh = new Mesh(); skin.BakeMesh(mesh, true);
                    foreach (var v in mesh.vertices) { var p = space.InverseTransformPoint(skin.transform.TransformPoint(v)); if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p); }
                    Object.DestroyImmediate(mesh);
                    continue;
                }
                w = r.bounds;
                for (int k = 0; k < 8; k++)
                {
                    var corner = new Vector3((k & 1) == 0 ? w.min.x : w.max.x, (k & 2) == 0 ? w.min.y : w.max.y, (k & 4) == 0 ? w.min.z : w.max.z);
                    var p = space.InverseTransformPoint(corner);
                    if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
                }
            }
            return b;
        }
        private static void Set(Object obj, string key, Object value) { var so = new SerializedObject(obj); so.FindProperty(key).objectReferenceValue = value; so.ApplyModifiedPropertiesWithoutUndo(); }
        private static void SetArray<T>(Object obj, string key, T[] values) where T : Object
        { var so = new SerializedObject(obj); var p = so.FindProperty(key); p.arraySize = values.Length; for (int i = 0; i < values.Length; i++) p.GetArrayElementAtIndex(i).objectReferenceValue = values[i]; so.ApplyModifiedPropertiesWithoutUndo(); }

        private static NetworkPhysicsBody BuildPatient(AnimatorController controller, AnimationClip clip)
        {
            var go = NetBody("Stage1_Patient_v02");
            var body = go.GetComponent<Rigidbody>(); body.mass = 12f; body.constraints = RigidbodyConstraints.FreezeRotation;
            var nt = new SerializedObject(go.GetComponent<FishNet.Component.Transforming.NetworkTransform>());
            nt.FindProperty("_synchronizeScale").boolValue = true; nt.ApplyModifiedPropertiesWithoutUndo();
            var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(PatientFbx), go.transform);
            model.name = "PATIENT model";
            if (!model.TryGetComponent(out Animator animator)) animator = model.AddComponent<Animator>();
            animator.avatar = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/OnlyVolunteers/Characters/SausageBuddy/SAUSAGE_BUDDY_A_v04.fbx").GetComponent<Animator>().avatar;
            animator.runtimeAnimatorController = controller; animator.cullingMode = AnimatorCullingMode.AlwaysAnimate; animator.applyRootMotion = false;
            // Physics collider fitted to the lying pose (the floor and carrying use it; on the table it is off).
            var sampler = (GameObject)Object.Instantiate(model);
            Bounds lying;
            try
            {
                clip.SampleAnimation(sampler, 0f);
                lying = LocalBounds(sampler.transform, sampler.GetComponentsInChildren<SkinnedMeshRenderer>());
            }
            finally { Object.DestroyImmediate(sampler); }
            var box = go.AddComponent<BoxCollider>();
            box.center = lying.center; box.size = new Vector3(Mathf.Min(lying.size.x, 0.6f), Mathf.Max(0.2f, lying.size.y), lying.size.z);
            report.Add($"patient lying bounds center={lying.center} size={lying.size}");
            var anchors = go.AddComponent<OperationPatientAnchors>();
            string[] names = { "INC_KIDNEY_L", "INC_KIDNEY_R", "INC_LIVER" };
            var markers = names.Select(n => model.GetComponentsInChildren<Transform>(true).FirstOrDefault(t => t.name == n)).ToArray();
            if (markers.Any(m => m == null)) throw new InvalidOperationException("Patient marker missing");
            SetArray(anchors, "incisions", markers);
            var rig = go.AddComponent<OperationPatientRig>();
            Set(rig, "animator", animator);
            Set(rig, "face", model.GetComponentsInChildren<SkinnedMeshRenderer>(true).First(s => s.name == "Face"));
            Set(rig, "physicsCollider", box);
            return Save(go, "Stage1_Patient_v02").GetComponent<NetworkPhysicsBody>();
        }

        private static OperationTool Tool(string name, OperationToolKind kind)
        {
            var go = new GameObject(name);
            go.AddComponent<NetworkObject>();
            var body = go.AddComponent<Rigidbody>(); body.mass = 0.15f; body.isKinematic = true; body.useGravity = false;
            body.interpolation = RigidbodyInterpolation.Interpolate; body.collisionDetectionMode = CollisionDetectionMode.ContinuousSpeculative;
            var visual = new GameObject("Visual").transform; visual.SetParent(go.transform, false);
            bool syringe = kind != OperationToolKind.Scalpel;
            var src = AssetDatabase.LoadAssetAtPath<GameObject>(syringe ? Art + "/SYRINGE-ASTRA-001.fbx" : "Assets/OnlyVolunteers/Props/ScalpelAstra/Model/SCALPEL-ASTRA-001.fbx");
            var model = (GameObject)PrefabUtility.InstantiatePrefab(src, visual);
            foreach (var c in model.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            Transform liquid = null; var plunger = new List<Transform>();
            if (syringe)
            {
                visual.localScale = Vector3.one * 0.85f;
                foreach (var t in model.GetComponentsInChildren<Transform>(true))
                {
                    if (t.name.StartsWith("SM_Plunger") || t.name.StartsWith("SM_Stopper") || t.name == "SM_ThumbPad") plunger.Add(t);
                    if (t.name.StartsWith("SM_BloodVolume")) t.gameObject.SetActive(false);
                }
                Color tint = kind == OperationToolKind.Syringe ? new Color(0.2f, 0.55f, 1f) : new Color(0.85f, 0.08f, 0.14f);
                var mat = LitAsset(kind == OperationToolKind.Syringe ? "AnesthesiaLiquid" : "BloodLiquid", tint);
                var cyl = GameObject.CreatePrimitive(PrimitiveType.Cylinder); Object.DestroyImmediate(cyl.GetComponent<Collider>());
                cyl.name = "Liquid"; cyl.transform.SetParent(visual, false); cyl.transform.localScale = new Vector3(0.027f, 0.03f, 0.027f); cyl.transform.localPosition = new Vector3(0, 0.11f, 0);
                cyl.GetComponent<Renderer>().sharedMaterial = mat; liquid = cyl.transform;
                var band = GameObject.CreatePrimitive(PrimitiveType.Cylinder); Object.DestroyImmediate(band.GetComponent<Collider>());
                band.name = "Marking"; band.transform.SetParent(visual, false); band.transform.localScale = new Vector3(0.038f, 0.006f, 0.038f); band.transform.localPosition = new Vector3(0, 0.068f, 0);
                band.GetComponent<Renderer>().sharedMaterial = LitAsset(kind == OperationToolKind.Syringe ? "AnesthesiaMark" : "BloodMark", tint);
                var cap = GameObject.CreatePrimitive(PrimitiveType.Sphere); Object.DestroyImmediate(cap.GetComponent<Collider>());
                cap.name = "MarkingDot"; cap.transform.SetParent(visual, false); cap.transform.localScale = Vector3.one * 0.03f; cap.transform.localPosition = new Vector3(0, 0.192f, 0);
                cap.GetComponent<Renderer>().sharedMaterial = band.GetComponent<Renderer>().sharedMaterial;
            }
            else
            {
                visual.localScale = Vector3.one * 1.0f;
                model.transform.localPosition = new Vector3(-0.069f, -0.007f, 0f);
            }
            // Colliders: hover trigger always; a solid one only while loose (server).
            var b = LocalBounds(go.transform, go.GetComponentsInChildren<Renderer>());
            var hover = go.AddComponent<BoxCollider>(); hover.isTrigger = true; hover.center = b.center; hover.size = b.size + Vector3.one * 0.03f;
            var solid = go.AddComponent<BoxCollider>(); solid.center = b.center; solid.size = b.size; solid.enabled = false;
            // Dock pose: lay flat along the slot frame's +X (= the table's length), middle on the slot, resting on it.
            Quaternion lay = syringe ? Quaternion.Euler(0, 0, -90) * Quaternion.Euler(0, 90, 0) : Quaternion.Euler(90, 180, 0);
            var probe = new GameObject("probe").transform;
            go.transform.SetPositionAndRotation(Vector3.zero, lay);
            var lb = LocalBounds(probe, go.GetComponentsInChildren<Renderer>());
            go.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
            Object.DestroyImmediate(probe.gameObject);
            Vector3 dockOffset = -lb.center + Vector3.up * (lb.extents.y + 0.003f);
            var tool = go.AddComponent<OperationTool>();
            var so = new SerializedObject(tool);
            so.FindProperty("kind").enumValueIndex = (int)kind;
            so.FindProperty("visual").objectReferenceValue = visual;
            so.FindProperty("hoverCollider").objectReferenceValue = hover;
            so.FindProperty("solidCollider").objectReferenceValue = solid;
            so.FindProperty("dockOffset").vector3Value = dockOffset;
            so.FindProperty("dockEuler").vector3Value = lay.eulerAngles;
            if (syringe)
            {
                var arr = so.FindProperty("plunger"); arr.arraySize = plunger.Count;
                for (int i = 0; i < plunger.Count; i++) arr.GetArrayElementAtIndex(i).objectReferenceValue = plunger[i];
                so.FindProperty("liquid").objectReferenceValue = liquid;
                so.FindProperty("plungerTravel").floatValue = 0.056f;
                so.FindProperty("liquidBottom").floatValue = 0.081f;
                so.FindProperty("liquidLength").floatValue = 0.058f;
            }
            so.ApplyModifiedPropertiesWithoutUndo();
            return Save(go, name).GetComponent<OperationTool>();
        }

        private static Material LitAsset(string name, Color color)
        {
            string path = Data + "/" + name + "_v02.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Lit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", color); mat.color = color; mat.SetFloat("_Smoothness", 0.45f);
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static Material UnlitAsset(string name, Color color)
        {
            string path = Data + "/" + name + "_v02.mat";
            var mat = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (mat == null) { mat = new Material(Shader.Find("Universal Render Pipeline/Unlit")); AssetDatabase.CreateAsset(mat, path); }
            mat.SetColor("_BaseColor", color); mat.color = color;
            EditorUtility.SetDirty(mat);
            return mat;
        }

        private static OperationPhysicalItem Merchandise(string name, ItemDefinition definition, OperationTuning tuning, float size, bool oneKidney)
        {
            var go = NetBody(name);
            var holder = new GameObject(ItemWorldModel.ChildName).transform; holder.SetParent(go.transform, false);
            var model = (GameObject)PrefabUtility.InstantiatePrefab(definition.WorldModel, holder);
            foreach (var c in model.GetComponentsInChildren<Collider>()) Object.DestroyImmediate(c);
            if (oneKidney) OperationPresentation.KeepOneKidney(model.transform, true);
            OperationPresentation.LayFlat(model.transform, holder);
            var b = LocalBounds(holder, model.GetComponentsInChildren<Renderer>());
            float k = size / Mathf.Max(0.0001f, Mathf.Max(b.size.x, b.size.y, b.size.z));
            model.transform.localScale *= k;
            b = LocalBounds(holder, model.GetComponentsInChildren<Renderer>());
            model.transform.localPosition -= b.center;
            var box = holder.gameObject.AddComponent<BoxCollider>(); box.size = b.size; box.center = Vector3.zero;
            go.GetComponent<Rigidbody>().mass = Mathf.Max(0.3f, definition.DropMass);
            var world = go.AddComponent<WorldItem>(); Set(world, "definition", definition);
            var item = go.AddComponent<OperationPhysicalItem>(); Set(item, "tuning", tuning);
            return Save(go, name).GetComponent<OperationPhysicalItem>();
        }

        // ---------- stand ----------
        /// <summary>The props agent's InstrumentStand_v01.fbx (slots included) wrapped with colliders and hover zones;
        /// a box placeholder only if that FBX is missing. Its InstrumentStand_v01.prefab wins when it exists.</summary>
        private static GameObject Stand()
        {
            var go = new GameObject("InstrumentStand_Placeholder_v02");
            string fbx = Art + "/InstrumentStand_v01.fbx";
            float floor = 0.692f;
            if (File.Exists(fbx))
            {
                var model = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(fbx), go.transform);
                model.name = "InstrumentStand_v01";
                report.Add("stand visual: props " + fbx);
            }
            else
            {
                var steel = LitAsset("StandSteel", new Color(0.62f, 0.68f, 0.72f));
                Cube("Tray", go.transform, new Vector3(0, floor - 0.012f, 0), new Vector3(0.42f, 0.024f, 0.54f), LitAsset("StandTray", new Color(0.8f, 0.84f, 0.87f)), false);
                Cube("Pole", go.transform, new Vector3(0, floor * 0.5f, 0), new Vector3(0.035f, floor - 0.03f, 0.035f), steel, false);
                Cube("Foot", go.transform, new Vector3(0, 0.015f, 0), new Vector3(0.32f, 0.03f, 0.5f), steel, false);
                for (int r = 0; r < 3; r++)
                {
                    Slot(go.transform, new[] { "SLOT_SYRINGE_ANESTHESIA", "SLOT_SYRINGE_BLOOD", "SLOT_SCALPEL" }[r], new Vector3(0.135f, floor, 0.165f - r * 0.165f), Quaternion.identity);
                    Slot(go.transform, "SLOT_BLOODBAG_" + (r + 1), new Vector3(0f, floor, 0.165f - r * 0.165f), Quaternion.identity);
                    Slot(go.transform, "SLOT_ORGAN_" + (r + 1), new Vector3(-0.135f, floor, 0.165f - r * 0.165f), Quaternion.identity);
                }
                report.Add("stand visual: box placeholder");
            }
            // Physics: the tray floor and low rims (it moves with the gurney as part of its compound collider).
            var physics = new GameObject("StandColliders").transform; physics.SetParent(go.transform, false);
            Box(physics, "TrayFloor", new Vector3(0, floor - 0.012f, 0), new Vector3(0.42f, 0.024f, 0.54f), false);
            Box(physics, "RimL", new Vector3(-0.215f, floor + 0.012f, 0), new Vector3(0.012f, 0.03f, 0.54f), false);
            Box(physics, "RimR", new Vector3(0.215f, floor + 0.012f, 0), new Vector3(0.012f, 0.03f, 0.54f), false);
            Box(physics, "RimF", new Vector3(0, floor + 0.012f, -0.275f), new Vector3(0.42f, 0.03f, 0.012f), false);
            Box(physics, "RimB", new Vector3(0, floor + 0.012f, 0.275f), new Vector3(0.42f, 0.03f, 0.012f), false);
            var zone = Box(physics, "Hit_Tray", new Vector3(0, floor + 0.03f, 0), new Vector3(0.44f, 0.06f, 0.56f), true);
            var zt = zone.gameObject.AddComponent<OperationTargetTag>(); zt.kind = TargetKind.Tray; zt.index = 0;
            string path = Prefabs + "/Stage1_InstrumentStand_Placeholder_v02.prefab";
            var prefab = PrefabUtility.SaveAsPrefabAsset(go, path);
            Object.DestroyImmediate(go);
            return prefab;
        }
        private static Transform Box(Transform parent, string name, Vector3 center, Vector3 size, bool trigger)
        {
            var t = new GameObject(name).transform; t.SetParent(parent, false);
            var c = t.gameObject.AddComponent<BoxCollider>(); c.center = center; c.size = size; c.isTrigger = trigger;
            return t;
        }
        private static Transform Slot(Transform parent, string name, Vector3 position, Quaternion rotation)
        {
            var t = new GameObject(name).transform; t.SetParent(parent, false); t.localPosition = position; t.localRotation = rotation; return t;
        }
        private static GameObject Cube(string name, Transform parent, Vector3 position, Vector3 scale, Material mat, bool collider)
        {
            var go = GameObject.CreatePrimitive(PrimitiveType.Cube); go.name = name;
            if (!collider) Object.DestroyImmediate(go.GetComponent<Collider>());
            go.transform.SetParent(parent, false); go.transform.localPosition = position; go.transform.localScale = scale;
            go.GetComponent<Renderer>().sharedMaterial = mat;
            return go;
        }

        // ---------- table ----------
        private static NetworkOperationTable Table(OperationTuning tuning, NetworkPhysicsBody patient, OperationTool[] tools, OperationPhysicalItem[] merchandise, ItemDefinition[] defs, GameObject stand, GameObject bagModel, AnimationClip clip)
        {
            bool props = File.Exists(PropsTable);
            string name = props ? "OperatingTableAstra_v02" : "Stage1_Table_Placeholder_v02";
            GameObject go;
            if (props)
            {
                go = PrefabUtility.LoadPrefabContents(PropsTable);
                report.Add("table: props prefab " + PropsTable);
                AddTrayColliders(go.transform);
            }
            else
            {
                go = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(NetworkRoot + "NetworkTableAstra.prefab"));
                PrefabUtility.UnpackPrefabInstance(go, PrefabUnpackMode.OutermostRoot, InteractionMode.AutomatedAction);
                go.name = name;
                foreach (var t in go.GetComponentsInChildren<Transform>(true)) if (t.name.StartsWith("GEO_Strap_")) t.gameObject.SetActive(false);
                var rest = Child(go.transform, "PatientRest", tuning.patientRest, Quaternion.Euler(0, 180, 0));
                Child(go.transform, "CameraAnchor", tuning.cameraPosition, Quaternion.LookRotation(tuning.cameraLookAt - tuning.cameraPosition));
                Child(go.transform, "TrayAnchor", tuning.trayPosition, Quaternion.identity);
                PlaceholderStraps(go.transform, rest, clip);
                report.Add("table: placeholder " + name + " (props OperatingTableAstra_v02 not found)");
            }
            var tray = FindDeep(go.transform, "TrayAnchor");
            if (tray != null && FindDeep(tray, "SLOT_SCALPEL") == null && FindDeep(go.transform, "SLOT_SCALPEL") == null)
            {
                var standPath = File.Exists(Prefabs + "/InstrumentStand_v01.prefab") ? Prefabs + "/InstrumentStand_v01.prefab" : AssetDatabase.GetAssetPath(stand);
                var inst = (GameObject)PrefabUtility.InstantiatePrefab(AssetDatabase.LoadAssetAtPath<GameObject>(standPath), tray);
                inst.transform.localPosition = Vector3.zero; inst.transform.localRotation = Quaternion.identity;
                report.Add("stand: " + standPath);
            }
            if (!go.TryGetComponent(out NetworkOperationTable table)) table = go.AddComponent<NetworkOperationTable>();
            if (!go.TryGetComponent(out PatientRegistry registry)) registry = go.AddComponent<PatientRegistry>();
            Set(table, "tuning", tuning); Set(table, "patientPrefab", patient); Set(table, "registry", registry);
            SetArray(table, "toolPrefabs", tools); SetArray(table, "merchandisePrefabs", merchandise); SetArray(table, "merchandiseDefinitions", defs);
            if (!go.TryGetComponent(out OperationTableView view)) view = go.AddComponent<OperationTableView>();
            Set(view, "table", table);
            if (!go.TryGetComponent(out OperationPresentation pres)) pres = go.AddComponent<OperationPresentation>();
            Set(pres, "table", table);
            SetArray(pres, "organModels", new[] { defs[0].WorldModel, defs[1].WorldModel });
            Set(pres, "bagModel", bagModel);
            Set(pres, "litTemplate", LitAsset("OpsLitTemplate", Color.white));
            Set(pres, "unlitTemplate", UnlitAsset("OpsUnlitTemplate", Color.white));
            if (File.Exists(PropsIncisions)) Set(pres, "incisionPieces", AssetDatabase.LoadAssetAtPath<GameObject>(PropsIncisions));
            if (props)
            {
                PrefabUtility.SaveAsPrefabAsset(go, PropsTable);
                PrefabUtility.UnloadPrefabContents(go);
                var p = AssetDatabase.LoadAssetAtPath<GameObject>(PropsTable);
                made.Add(p.GetComponent<NetworkObject>());
                return p.GetComponent<NetworkOperationTable>();
            }
            return Save(go, name).GetComponent<NetworkOperationTable>();
        }
        /// <summary>The props stand is visual only: add the tray floor, low rims and the tray hover zone (gameplay wiring)
        /// under TrayAnchor, fitted to the SLOT_* markers.</summary>
        private static void AddTrayColliders(Transform table)
        {
            var tray = FindDeep(table, "TrayAnchor");
            if (tray == null || FindDeep(tray, "StandColliders") != null) return;
            bool any = false; var b = new Bounds();
            foreach (var t in tray.GetComponentsInChildren<Transform>(true))
            {
                if (!t.name.StartsWith("SLOT_")) continue;
                var p = tray.InverseTransformPoint(t.position);
                if (!any) { b = new Bounds(p, Vector3.zero); any = true; } else b.Encapsulate(p);
            }
            if (!any) return;
            float floor = b.min.y;
            var size = new Vector3(b.size.x + 0.15f, 0.024f, b.size.z + 0.21f);
            var c = new Vector3(b.center.x, floor - 0.012f, b.center.z);
            var physics = new GameObject("StandColliders").transform; physics.SetParent(tray, false);
            Box(physics, "TrayFloor", c, size, false);
            Box(physics, "RimL", c + new Vector3(-size.x * 0.5f, 0.024f, 0), new Vector3(0.012f, 0.03f, size.z), false);
            Box(physics, "RimR", c + new Vector3(size.x * 0.5f, 0.024f, 0), new Vector3(0.012f, 0.03f, size.z), false);
            Box(physics, "RimF", c + new Vector3(0, 0.024f, -size.z * 0.5f), new Vector3(size.x, 0.03f, 0.012f), false);
            Box(physics, "RimB", c + new Vector3(0, 0.024f, size.z * 0.5f), new Vector3(size.x, 0.03f, 0.012f), false);
            var zone = Box(physics, "Hit_Tray", c + Vector3.up * 0.042f, new Vector3(size.x + 0.02f, 0.06f, size.z + 0.02f), true);
            var zt = zone.gameObject.AddComponent<OperationTargetTag>(); zt.kind = TargetKind.Tray; zt.index = 0;
            report.Add($"tray colliders added under TrayAnchor: floor y={floor:F3} size={size}");
        }
        private static Transform FindDeep(Transform root, string name)
        {
            if (root.name == name) return root;
            for (int i = 0; i < root.childCount; i++) { var r = FindDeep(root.GetChild(i), name); if (r != null) return r; }
            return null;
        }
        private static Transform Child(Transform parent, string name, Vector3 position, Quaternion rotation)
        {
            var t = new GameObject(name).transform; t.SetParent(parent, false); t.localPosition = position; t.localRotation = rotation; return t;
        }

        /// <summary>Five hinged bands over the lying pose: hinge +X along the pad edge, +Y inward, +Z up; rotating +X opens.</summary>
        private static void PlaceholderStraps(Transform table, Transform rest, AnimationClip clip)
        {
            var model = (GameObject)Object.Instantiate(AssetDatabase.LoadAssetAtPath<GameObject>(PatientFbx));
            var verts = new List<Vector3>();
            try
            {
                clip.SampleAnimation(model, 0f);
                model.transform.SetPositionAndRotation(rest.position, rest.rotation);
                foreach (var skin in model.GetComponentsInChildren<SkinnedMeshRenderer>())
                {
                    var mesh = new Mesh(); skin.BakeMesh(mesh, true);
                    foreach (var v in mesh.vertices) verts.Add(table.InverseTransformPoint(skin.transform.TransformPoint(v)));
                    Object.DestroyImmediate(mesh);
                }
                // Same pivots as the props contract (table_rest_contract_v01.json) so the swap keeps the layout.
                var mat = LitAsset("StrapBand", new Color(0.16f, 0.18f, 0.2f));
                var buckle = LitAsset("StrapBuckle", new Color(0.75f, 0.78f, 0.8f));
                var hinges = new Transform[5];
                (Vector3 c, float side, float reach, string name)[] defs =
                {
                    (new Vector3(0, 0, 0.045f), 1f, 0.17f, "STRAP_ARM_L"), (new Vector3(0, 0, 0.045f), -1f, 0.17f, "STRAP_ARM_R"),
                    (new Vector3(0, 0, -0.62f), 1f, 0.27f, "STRAP_LEG_L"), (new Vector3(0, 0, -0.62f), -1f, 0.27f, "STRAP_LEG_R"),
                    (new Vector3(0, 0, -0.055f), 1f, 0.305f, "STRAP_TORSO"),
                    (new Vector3(0, 0, -0.055f), -1f, 0.305f, "STRAP_TORSO_B"),
                };
                Transform second = null;
                for (int i = 0; i < defs.Length; i++)
                {
                    var d = defs[i];
                    float edge = 0.305f * d.side;
                    float inner = edge - d.side * d.reach;
                    float minX = Mathf.Min(edge, inner), maxX = Mathf.Max(edge, inner);
                    float top = 0.66f;
                    foreach (var v in verts) if (v.x >= minX && v.x <= maxX && Mathf.Abs(v.z - d.c.z) < 0.045f) top = Mathf.Max(top, v.y);
                    top += 0.012f;
                    var hinge = new GameObject(d.name).transform; hinge.SetParent(table, false);
                    hinge.localPosition = new Vector3(edge, top, d.c.z);
                    hinge.localRotation = Quaternion.LookRotation(Vector3.up, new Vector3(-d.side, 0, 0));
                    var band = Cube("Band", hinge, new Vector3(0, d.reach * 0.5f, 0), new Vector3(0.075f, d.reach, 0.012f), mat, false);
                    Cube("Buckle", hinge, new Vector3(0, d.reach * 0.62f, 0.008f), new Vector3(0.085f, 0.04f, 0.02f), buckle, false);
                    var post = Cube("Post_" + d.name, table, new Vector3(edge + d.side * 0.01f, (top + 0.6f) * 0.5f, d.c.z), new Vector3(0.02f, top - 0.6f, 0.06f), mat, false);
                    if (i < 5) hinges[i] = hinge;
                    else { second = hinge; hinge.name = "STRAP_TORSO_SecondHalf"; }
                }
                var straps = table.gameObject.AddComponent<OperationStrapsPlaceholder>();
                SetArray(straps, "hinges", hinges);
                Set(straps, "torsoSecond", second);
            }
            finally { Object.DestroyImmediate(model); }
        }

        // ---------- player ----------
        private static void PlayerPrefab()
        {
            string path = NetworkRoot + "NetworkPlayer.prefab";
            var go = PrefabUtility.LoadPrefabContents(path);
            try
            {
                bool changed = false;
                var inventory = go.GetComponent<NetworkInventory>();
                if (inventory == null) { inventory = go.AddComponent<NetworkInventory>(); changed = true; }
                Set(inventory, "database", AssetDatabase.LoadAssetAtPath<ItemDatabase>("Assets/OnlyVolunteers/Inventory/Items/ItemDatabase.asset"));
                Set(inventory, "reachOrigin", go.GetComponent<KccFirstPersonInput>().Character.Motor.transform);
                var input = go.GetComponent<InventoryInput>();
                if (input == null) { input = go.AddComponent<InventoryInput>(); changed = true; }
                Set(input, "inventorySource", inventory); Set(input, "viewCamera", go.GetComponentInChildren<Camera>(true));
                PrefabUtility.SaveAsPrefabAsset(go, path);
                report.Add("NetworkPlayer.prefab: NetworkInventory + InventoryInput " + (changed ? "added" : "present"));
            }
            finally { PrefabUtility.UnloadPrefabContents(go); }
        }

        // ---------- scene ----------
        private static void BuildScene(NetworkOperationTable table)
        {
            var prior = SceneManager.GetActiveScene().path;
            var source = EditorSceneManager.OpenScene("Assets/OnlyVolunteers/Scenes/NetworkTest.unity", OpenSceneMode.Single);
            EditorSceneManager.SaveScene(source, ScenePath, true);
            var scene = EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
            NetworkSession session = null; Camera menu = null; Light sun = null;
            foreach (var root in scene.GetRootGameObjects())
            {
                if (root.TryGetComponent(out NetworkSession found)) { session = found; continue; }
                if (root.TryGetComponent(out Camera cam)) { menu = cam; continue; }
                if (root.TryGetComponent(out Light light) && light.type == LightType.Directional) { sun = light; continue; }
                Object.DestroyImmediate(root);
            }
            if (session == null || menu == null) throw new InvalidOperationException("NetworkTest composition missing");
            if (sun == null) sun = new GameObject("Directional Light").AddComponent<Light>();
            sun.type = LightType.Directional; sun.intensity = 1.15f; sun.shadows = LightShadows.Soft; sun.transform.rotation = Quaternion.Euler(52, -35, 0);
            RenderSettings.ambientMode = UnityEngine.Rendering.AmbientMode.Trilight;
            RenderSettings.ambientSkyColor = new Color(0.62f, 0.66f, 0.72f); RenderSettings.ambientEquatorColor = new Color(0.45f, 0.47f, 0.5f); RenderSettings.ambientGroundColor = new Color(0.25f, 0.24f, 0.24f);
            menu.transform.SetPositionAndRotation(new Vector3(-3.2f, 2.6f, -3.2f), Quaternion.LookRotation(new Vector3(3.2f, -1.9f, 3.2f)));
            var room = new GameObject("Operation room").transform;
            Cube("Floor", room, new Vector3(0, -0.1f, 0), new Vector3(10, 0.2f, 10), LitAsset("RoomFloor", new Color(0.36f, 0.4f, 0.4f)), true);
            Cube("Wall_N", room, new Vector3(0, 1.6f, 3.6f), new Vector3(10, 3.2f, 0.2f), LitAsset("RoomWall", new Color(0.55f, 0.62f, 0.6f)), true);
            Cube("Wall_E", room, new Vector3(3.8f, 1.6f, 0), new Vector3(0.2f, 3.2f, 10), LitAsset("RoomWall", new Color(0.55f, 0.62f, 0.6f)), true);
            Cube("Wall_S", room, new Vector3(0, 1.6f, -4.2f), new Vector3(10, 3.2f, 0.2f), LitAsset("RoomWall", new Color(0.55f, 0.62f, 0.6f)), true);
            Cube("Tiles", room, new Vector3(0, 0.002f, 0), new Vector3(4.2f, 0.004f, 4.6f), LitAsset("RoomTiles", new Color(0.66f, 0.72f, 0.72f)), false);
            var lampGo = new GameObject("Operation lamp"); lampGo.transform.SetParent(room, false);
            lampGo.transform.SetPositionAndRotation(new Vector3(0.1f, 2.9f, -0.1f), Quaternion.Euler(90, 0, 0));
            var lamp = lampGo.AddComponent<Light>(); lamp.type = LightType.Spot; lamp.range = 6f; lamp.spotAngle = 70f; lamp.intensity = 6f; lamp.color = new Color(1f, 0.97f, 0.9f); lamp.shadows = LightShadows.Soft;
            var composition = new SerializedObject(session);
            composition.FindProperty("playerPrefab").objectReferenceValue = AssetDatabase.LoadAssetAtPath<NetworkPlayer>(NetworkRoot + "NetworkPlayer.prefab");
            composition.FindProperty("bodyPrefab").objectReferenceValue = null;
            composition.FindProperty("tablePrefab").objectReferenceValue = null;
            composition.FindProperty("scalpelPrefab").objectReferenceValue = null;
            var spawns = composition.FindProperty("playerSpawns"); spawns.arraySize = 4;
            Vector3[] spots = { new(-2.3f, 0.05f, -0.9f), new(-2.3f, 0.05f, 0.7f), new(-1.2f, 0.05f, -2.2f), new(-1.2f, 0.05f, 2.0f) };
            for (int i = 0; i < 4; i++)
            {
                var at = new GameObject("Player spawn " + i).transform;
                at.position = spots[i]; at.rotation = Quaternion.LookRotation(Vector3.ProjectOnPlane(new Vector3(0, 0, 0) - spots[i], Vector3.up));
                spawns.GetArrayElementAtIndex(i).objectReferenceValue = at;
            }
            composition.ApplyModifiedPropertiesWithoutUndo();
            // FishNet spawnables: the project defaults plus the v02 prefabs.
            var manager = session.GetComponent<NetworkManager>();
            string listPath = Data + "/OperationSpawnables_v02.asset";
            var defaults = AssetDatabase.LoadAssetAtPath<SinglePrefabObjects>("Assets/DefaultPrefabObjects.asset");
            var list = AssetDatabase.LoadAssetAtPath<SinglePrefabObjects>(listPath);
            if (list == null) { list = ScriptableObject.CreateInstance<SinglePrefabObjects>(); AssetDatabase.CreateAsset(list, listPath); }
            list.Clear();
            for (int i = 0; i < defaults.GetObjectCount(); i++) list.AddObject(defaults.GetObject(true, i), true, false);
            foreach (var nob in made) if (nob != null) list.AddObject(nob, true, false);
            list.AddObject(AssetDatabase.LoadAssetAtPath<NetworkObject>(NetworkRoot + "NetworkPlayer.prefab"), true, false);
            EditorUtility.SetDirty(list);
            var mso = new SerializedObject(manager); mso.FindProperty("_spawnablePrefabs").objectReferenceValue = list; mso.ApplyModifiedPropertiesWithoutUndo();
            var spawner = new GameObject("Operation table spawner").AddComponent<OperationStage1Spawner>();
            spawner.transform.position = new Vector3(0f, 0.02f, 0f);
            Set(spawner, "tablePrefab", table);
            new GameObject("Operation dev driver").AddComponent<OperationNetworkProbe>();
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);
            report.Add("scene saved " + ScenePath + " spawnables=" + list.GetObjectCount());
            if (!string.IsNullOrEmpty(prior) && prior != ScenePath && File.Exists(prior)) EditorSceneManager.OpenScene(prior, OpenSceneMode.Single);
        }

        // ---------- standalone build for the two-process run ----------
        public static string BuildPlayer(string folder)
        {
            Directory.CreateDirectory(folder);
            var result = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = Path.Combine(folder, "OperationsStage1v02.exe"),
                target = BuildTarget.StandaloneWindows64,
                options = BuildOptions.Development
            });
            return result.summary.result + " errors=" + result.summary.totalErrors + " warnings=" + result.summary.totalWarnings + " size=" + result.summary.totalSize;
        }
    }
}
